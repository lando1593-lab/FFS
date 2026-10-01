import pytest

from ffs.core.assertions import Assertion, AssertionKind, SourceRef
from ffs.db.assign import (
    assign,
    assign_design,
    current,
    ensure_base_scenario,
    freeze_stage,
    new_scenario,
    open_review_items,
    resolution_meter,
)
from ffs.db.models import (
    AssertionRow,
    AuditEvent,
    DesignAssignment,
    MemberInterpretation,
    Project,
    RatingAssignment,
    session,
)
from ffs.db.store import save_members
from ffs.design.thickness import Candidate, Resolution, ThicknessQuery
from ffs.takeoff.model import Evidence, new_member


@pytest.fixture
def db(tmp_path):
    s = session(f"sqlite:///{tmp_path}/t.sqlite")
    prj = Project(name="t")
    s.add(prj)
    s.commit()
    m = new_member(
        level="ROOF",
        sheet_no="S102",
        member_mark="W12X26",
        canonical_section="W12X26",
        family="W",
        member_type="beam",
        status="new",
        length_in=240.0,
        length_source="geometry",
        start_xy=(0, 0),
        end_xy=(240, 0),
        start_grid="A",
        end_grid="B",
        orientation_deg=0,
        confidence_id=0.95,
        confidence_geom=0.9,
        confidence_length=0.9,
        confidence_level=0.9,
        review_state="unreviewed",
    )
    m.evidence.append(
        Evidence("plan_label", "S102.pdf", 1, "S102", (0, 0, 10, 10), "W12X26", "pdf_text", 0.95)
    )
    save_members(s, prj, [m])
    member = s.get(
        type(
            s.scalars(
                __import__("sqlalchemy").select(
                    __import__("ffs.db.models", fromlist=["MemberInstance"]).MemberInstance
                )
            ).first()
        ),
        m.id,
    )
    return s, prj, member


def _cand(thk, method="chart_table", kind="FACT", **src):
    base = {
        "document": "isolatek-s721__abc.pdf",
        "design": "S721",
        "chart_date": "10/3/2013",
        "page": 6,
        "row": "W12 x 26",
        "column": "1 Hr",
        "via": "P723 → S721",
        "products": "CAFCO 400",
    }
    base.update(src)
    return Candidate(
        thk,
        None,
        method,
        kind,
        6 if method == "chart_table" else 2,
        "P723",
        base,
        {"ratio_kind": "W/D", "ratio": 0.61},
    )


def test_base_scenario_and_superseding_assignments(db):
    s, prj, member = db
    scn = ensure_base_scenario(s, prj)
    assert scn.is_current and ensure_base_scenario(s, prj).id == scn.id
    a1 = assign(
        s,
        prj,
        member,
        scn,
        MemberInterpretation,
        Assertion(AssertionKind.INTERPRETATION, "role", "beam", 0.9, "plan label context"),
        "engine",
        role="beam",
        status="new",
        scope_class="likely_in",
        scope_reason="roof framing",
    )
    a2 = assign(
        s,
        prj,
        member,
        scn,
        MemberInterpretation,
        Assertion(
            AssertionKind.HUMAN_OVERRIDE,
            "scope_class",
            "in",
            1.0,
            "estimator: in scope",
            verified_by="sam",
        ),
        "sam",
        reason="confirmed on walk",
        role="beam",
        status="new",
        scope_class="in",
    )
    cur = current(s, MemberInterpretation, member.id, scn.id)
    assert cur.id == a2.id and a2.supersedes_id == a1.id and cur.scope_class == "in"
    assert s.get(MemberInterpretation, a1.id).scope_class == "likely_in"  # never mutated
    kinds = [a.kind for a in s.query(AssertionRow).filter_by(member_id=member.id)]
    assert "HUMAN_OVERRIDE" in kinds and "INTERPRETATION" in kinds
    acts = [e.action for e in s.query(AuditEvent)]
    assert acts.count("member_interpretations.assign") == 2


def test_resolved_design_is_stored_with_its_source(db):
    s, prj, member = db
    scn = ensure_base_scenario(s, prj)
    q = ThicknessQuery("P723", "W12X26", 1.0, "unrestrained", "CAFCO 400")
    c = _cand(0.5)
    res = Resolution(q, [c], "resolved", c, [])
    row, item = assign_design(s, prj, member, scn, res)
    assert item is None and row.thickness_in == 0.5 and row.resolution_status == "resolved"
    assert (
        row.design == "P723" and row.product == "CAFCO 400" and row.design_revision == "10/3/2013"
    )
    assert row.thickness_source["via"] == "P723 → S721" and row.section_factor_value == 0.61
    a = s.get(AssertionRow, row.assertion_id)
    assert (
        a.kind == "FACT" and a.value == 0.5 and a.source_ref["document"] == "isolatek-s721__abc.pdf"
    )
    assert "S721@10/3/2013" in a.source_ref["rule_id"]


def test_conflict_opens_review_item_and_override_resolves_it(db):
    s, prj, member = db
    scn = ensure_base_scenario(s, prj)
    q = ThicknessQuery("X790", "HSS5X5X3/8", 1.0, None, "CAFCO 400")
    tbl = _cand(0.4375, design="X790", row="ST 5 x 5 x 3/8", via=None)
    eq = _cand(
        0.5625,
        method="ul_equation",
        kind="CALCULATION",
        design="X790",
        form="h = R / (a*(A/P) + b)",
        equation="R h = 188 (A/P) + 45",
        document="UL_X790.pdf",
        last_updated="2019-10-09",
    )
    res = Resolution(q, [eq, tbl], "conflict", None, ["sources disagree"])
    row, item = assign_design(s, prj, member, scn, res)
    assert row.thickness_in is None and row.resolution_status == "conflict"
    assert item is not None and item.kind == "conflict" and item.category == "design"
    assert sorted(o["thickness_in"] for o in item.options) == [0.4375, 0.5625]
    assert item.known == ["design X790", "rating 1.0 h", "product CAFCO 400"]
    assert len(open_review_items(s, prj, scn)) == 1
    meter = resolution_meter(s, prj, scn)
    assert meter["designs_unresolved"] == 1 and meter["open_by_category"] == {"design": 1}
    # the estimator picks the equation route
    row2, _ = assign_design(
        s,
        prj,
        member,
        scn,
        res,
        actor="sam",
        choice=eq,
        choice_reason="company practice: equation for tubes",
    )
    assert (
        row2.thickness_in == 0.5625
        and row2.resolution_status == "override"
        and row2.supersedes_id == row.id
    )
    a = s.get(AssertionRow, row2.assertion_id)
    assert (
        a.kind == "HUMAN_OVERRIDE"
        and a.verified_by == "sam"
        and a.method == "h = R / (a*(A/P) + b)"
    )
    assert a.inputs["chosen_candidate"]["method"] == "ul_equation"
    assert open_review_items(s, prj, scn) == []
    assert resolution_meter(s, prj, scn)["designs_unresolved"] == 0


def test_scenarios_keep_separate_assignments_and_stage_freezes_them(db):
    s, prj, member = db
    base = ensure_base_scenario(s, prj)
    alt = new_scenario(s, prj, "Alt 1: Monokote", "alternate", base, "sam")
    assign(
        s,
        prj,
        member,
        base,
        RatingAssignment,
        Assertion(
            AssertionKind.FACT,
            "rating_hours",
            1.0,
            0.95,
            "code summary sheet",
            SourceRef("G001.pdf", 1),
        ),
        "engine",
        rating_hours=1.0,
        element_category="roof",
        rule_ref="IBC 2021 T601",
        rule_edition="2021",
    )
    c = _cand(0.5)
    assign_design(
        s,
        prj,
        member,
        base,
        Resolution(
            ThicknessQuery("P723", "W12X26", 1.0, "unrestrained", "CAFCO 400"),
            [c],
            "resolved",
            c,
            [],
        ),
    )
    g = _cand(
        0.625,
        design="D739",
        document="gcp-d739__x.pdf",
        chart_date="3/15/2021",
        via=None,
        products="MK-6/HY",
    )
    assign_design(
        s,
        prj,
        member,
        alt,
        Resolution(
            ThicknessQuery("D739", "W12X26", 1.0, "unrestrained", "MK-6/HY"), [g], "resolved", g, []
        ),
    )
    assert current(s, DesignAssignment, member.id, base.id).thickness_in == 0.5
    assert current(s, DesignAssignment, member.id, alt.id).thickness_in == 0.625
    assert current(s, RatingAssignment, member.id, alt.id) is None  # not inherited implicitly
    st = freeze_stage(s, prj, base, "estimated", "sam")
    snap = st.snapshot["members"][member.id]
    assert snap["design"]["thickness_in"] == 0.5 and snap["rating"]["rating_hours"] == 1.0
    assert snap["exposure"] is None
    # a later change does not alter the frozen snapshot
    assign_design(
        s,
        prj,
        member,
        base,
        Resolution(
            ThicknessQuery("P723", "W12X26", 1.0, "unrestrained", "CAFCO 400"),
            [g],
            "resolved",
            g,
            [],
        ),
    )
    assert s.get(type(st), st.id).snapshot["members"][member.id]["design"]["thickness_in"] == 0.5
