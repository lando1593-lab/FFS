"""End-to-end: synthetic golden sheet → pipeline → scored against truth."""

import json

import pytest

from ffs.ingest.pdf import load_pdf
from ffs.steel.labels import LabelContext
from ffs.synth import generate, score
from ffs.takeoff.aggregate import summarize
from ffs.takeoff.pipeline import run_page


@pytest.fixture(scope="module")
def synthetic(tmp_path_factory):
    d = tmp_path_factory.mktemp("gp0")
    pdf = generate(d)
    page = load_pdf(pdf)[0]
    info, members, labels = run_page(page)
    return d, page, info, members, labels


def test_sheet_info(synthetic):
    _, page, info, _, _ = synthetic
    assert page.has_text_layer and page.has_vector_graphics and not page.likely_scanned
    assert info.sheet_no == "S-202"
    assert info.level == "LEVEL 02"
    assert info.scale is not None and info.scale.label.startswith("1/8")
    labels = {g.label for g in info.grids}
    assert {"1", "2", "3", "4", "5", "A", "B", "C", "D"} <= labels


def test_label_contexts(synthetic):
    _, _, _, _, labels = synthetic
    ctx = {}
    for lab in labels:
        ctx.setdefault(lab.context, []).append(lab.canonical)
    assert LabelContext.NOTE in ctx and "W8X10" in ctx[LabelContext.NOTE]
    assert len(ctx.get(LabelContext.SCHEDULE_ENTRY, [])) == 4
    assert "W8X10" not in ctx.get(LabelContext.PLAN_LABEL, [])


def test_scores(synthetic):
    d, _, _, members, _ = synthetic
    res = score(d / "truth.json", [m.to_dict() for m in members])
    assert res["recall"] == 1.0, res
    assert res["precision"] == 1.0, res
    assert res["duplicates"] == 0
    assert res["length_p95_err"] is not None and res["length_p95_err"] <= 0.005, res


def test_every_member_has_provenance(synthetic):
    _, _, _, members, _ = synthetic
    for m in members:
        assert m.evidence, m.id
        kinds = {a.kind.value for a in m.assertions}
        assert "FACT" in kinds and "CALCULATION" in kinds
        length_calc = next(a for a in m.assertions if a.key == "length_in")
        assert length_calc.method == "chain_length_x_scale"
        assert "scale" in length_calc.inputs


def test_grid_refs_on_girders(synthetic):
    _, _, _, members, _ = synthetic
    girders = [m for m in members if m.canonical_section == "W24X76"]
    assert len(girders) == 16
    assert all(m.start_grid and m.end_grid for m in girders), [
        (m.start_grid, m.end_grid) for m in girders
    ]
    assert any(m.start_grid == "A/1" and m.end_grid == "A/2" for m in girders)


def test_summary_and_json(synthetic):
    _, _, _, members, _ = synthetic
    rows = summarize(members)
    by = {r.canonical_section: r for r in rows}
    assert by["W24X76"].count == 16
    assert by["W24X76"].total_lf == pytest.approx(16 * 30.0, rel=0.005)
    json.dumps([m.to_dict() for m in members])  # serializable


def test_store_rejects_members_without_evidence(tmp_path):
    from ffs.db.models import Project, session
    from ffs.db.store import ProvenanceError, save_members
    from ffs.takeoff.model import new_member

    s = session(f"sqlite:///{tmp_path}/t.sqlite")
    prj = Project(name="t")
    s.add(prj)
    s.commit()
    bad = new_member(
        level="L1",
        sheet_no=None,
        member_mark="W18X35",
        canonical_section="W18X35",
        family="W",
        member_type="beam",
        status="new",
        length_in=None,
        length_source="none",
        start_xy=None,
        end_xy=None,
        start_grid=None,
        end_grid=None,
        orientation_deg=None,
        confidence_id=0.9,
        confidence_geom=0,
        confidence_length=0,
        confidence_level=0,
        review_state="unreviewed",
    )
    with pytest.raises(ProvenanceError):
        save_members(s, prj, [bad])


def test_store_roundtrip(synthetic, tmp_path):
    from ffs.db.models import MemberInstance, Project, session
    from ffs.db.store import save_members

    _, _, _, members, _ = synthetic
    s = session(f"sqlite:///{tmp_path}/rt.sqlite")
    prj = Project(name="gp0")
    s.add(prj)
    s.commit()
    n = save_members(s, prj, members)
    assert n == len(members)
    row = s.get(MemberInstance, members[0].id)
    assert row is not None and row.evidence and row.assertions
