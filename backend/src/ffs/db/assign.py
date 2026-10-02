"""Assignment services (ADR-0005): the only sanctioned way to write interpretation rows.

Every write creates a new row that supersedes the previous one for the same (member,
scenario); nothing is updated in place. Every row carries the assertion that justifies it,
and every engine outcome that is not a clean resolution becomes a ReviewItem.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from typing import TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from ffs.core.assertions import Assertion, AssertionKind, SourceRef
from ffs.db.models import (
    AssertionRow,
    AuditEvent,
    ConditionAssignment,
    DesignAssignment,
    ExposureAssignment,
    MemberInstance,
    MemberInterpretation,
    Project,
    RatingAssignment,
    ReviewItem,
    Scenario,
    Stage,
)
from ffs.design.thickness import Candidate, Resolution

T = TypeVar("T")
ASSIGNMENT_TABLES = {
    "interpretation": MemberInterpretation,
    "rating": RatingAssignment,
    "exposure": ExposureAssignment,
    "condition": ConditionAssignment,
    "design": DesignAssignment,
}


def ensure_base_scenario(db: Session, project: Project, actor: str = "system") -> Scenario:
    cur = db.scalar(select(Scenario).where(Scenario.project_id == project.id, Scenario.is_current))
    if cur:
        return cur
    scn = Scenario(project_id=project.id, name="Base bid", kind="base_bid", is_current=True)
    db.add(scn)
    db.flush()
    _audit(db, project.id, actor, "scenario.create", "scenario", scn.id, None, {"name": scn.name})
    db.commit()
    return scn


def new_scenario(
    db: Session, project: Project, name: str, kind: str, parent: Scenario | None, actor: str
) -> Scenario:
    scn = Scenario(
        project_id=project.id,
        name=name,
        kind=kind,
        parent_scenario_id=parent.id if parent else None,
    )
    db.add(scn)
    db.flush()
    _audit(db, project.id, actor, "scenario.create", "scenario", scn.id, None, {"name": name})
    db.commit()
    return scn


def current(db: Session, table: type[T], member_id: str, scenario_id: str) -> T | None:
    """The newest row for (member, scenario) that no other row supersedes."""
    rows = db.scalars(
        select(table).where(table.member_id == member_id, table.scenario_id == scenario_id)
    ).all()
    superseded = {r.supersedes_id for r in rows if r.supersedes_id}
    live = [r for r in rows if r.id not in superseded]
    return max(live, key=lambda r: r.created_at) if live else None


def _store_assertion(db: Session, member_id: str, a: Assertion) -> AssertionRow:
    row = AssertionRow(
        member_id=member_id,
        kind=a.kind.value,
        key=a.key,
        value=a.value,
        method=a.method,
        inputs=a.inputs or None,
        reasoning=a.reasoning,
        source_ref=asdict(a.source) if a.source else None,
        confidence=a.confidence,
        verified_by=a.verified_by,
    )
    db.add(row)
    db.flush()
    return row


def _audit(db, project_id, actor, action, subject_type, subject_id, before, after, reason=None):
    db.add(
        AuditEvent(
            project_id=project_id,
            actor=actor,
            action=action,
            subject_type=subject_type,
            subject_id=subject_id,
            before=before,
            after=after,
            reason=reason,
        )
    )


def assign(
    db: Session,
    project: Project,
    member: MemberInstance,
    scenario: Scenario,
    table: type[T],
    assertion: Assertion,
    actor: str,
    reason: str | None = None,
    **fields,
) -> T:
    """Write a new assignment row of ``table`` superseding the current one."""
    prev = current(db, table, member.id, scenario.id)
    arow = _store_assertion(db, member.id, assertion)
    row = table(
        member_id=member.id,
        scenario_id=scenario.id,
        assertion_id=arow.id,
        actor=actor,
        supersedes_id=prev.id if prev else None,
        **fields,
    )
    db.add(row)
    db.flush()
    _audit(
        db,
        project.id,
        actor,
        f"{table.__tablename__}.assign",
        table.__tablename__,
        row.id,
        _public(prev) if prev else None,
        _public(row),
        reason,
    )
    db.commit()
    return row


def _public(row) -> dict:
    return {
        c.name: getattr(row, c.name)
        for c in row.__table__.columns
        if c.name not in ("created_at",) and not isinstance(getattr(row, c.name), datetime)
    }


def _candidate_assertion(c: Candidate, member: MemberInstance, q) -> Assertion:
    revision = c.source.get("chart_date") or c.source.get("last_updated")
    src = SourceRef(
        document=str(c.source.get("document")),
        page=c.source.get("page"),
        revision=revision,
        rule_id=f"{c.source.get('design')}@{revision}",
    )
    reasoning = (
        f"{member.canonical_section} under {q.design} at {q.rating_hours} h"
        + (f", {q.restraint}" if q.restraint else "")
        + (f", {q.product}" if q.product else "")
        + f": {c.method} {c.source.get('row')} / {c.source.get('column')}"
        + (f" via {c.source['via']}" if c.source.get("via") else "")
    )
    if c.assertion_kind == "CALCULATION":
        return Assertion(
            AssertionKind.CALCULATION,
            "thickness_in",
            c.thickness_in,
            0.95,
            reasoning,
            src,
            method=c.source.get("form") or "equation",
            inputs=dict(c.inputs),
        )
    return Assertion(AssertionKind.FACT, "thickness_in", c.thickness_in, 0.98, reasoning, src)


def assign_design(
    db: Session,
    project: Project,
    member: MemberInstance,
    scenario: Scenario,
    res: Resolution,
    actor: str = "design-engine",
    choice: Candidate | None = None,
    choice_reason: str | None = None,
) -> tuple[DesignAssignment, ReviewItem | None]:
    """Persist a thickness resolution. A clean resolution stores the selected candidate's
    thickness with its assertion. Anything else stores an assignment with thickness None and
    opens a ReviewItem listing every candidate; a human ``choice`` resolves it as a
    HUMAN_OVERRIDE that cites the chosen candidate."""
    q = res.query
    picked = choice or (res.selected if res.status == "resolved" else None)
    if picked is None:
        a = Assertion(
            AssertionKind.ASSUMPTION,
            "thickness_in",
            None,
            0.0,
            f"no single printed value applies ({res.status}): " + "; ".join(res.reasons[-2:]),
        )
        status = res.status
    elif choice is not None:
        base = _candidate_assertion(choice, member, q)
        a = Assertion(
            AssertionKind.HUMAN_OVERRIDE,
            "thickness_in",
            choice.thickness_in,
            1.0,
            f"estimator chose {choice.method} {choice.thickness_in} in: "
            f"{choice_reason or 'no reason given'}",
            base.source,
            method=base.method,
            inputs={"chosen_candidate": {"method": choice.method, "source": choice.source}},
            verified_by=actor,
        )
        status = "override"
    else:
        a = _candidate_assertion(picked, member, q)
        status = "resolved"
    row = assign(
        db,
        project,
        member,
        scenario,
        DesignAssignment,
        a,
        actor,
        choice_reason,
        design=q.design,
        design_revision=(picked.source.get("last_updated") or picked.source.get("chart_date"))
        if picked
        else None,
        product=q.product,
        product_revision=picked.source.get("chart_date") if picked else None,
        rating_hours=q.rating_hours,
        section_factor_method=(picked.inputs.get("ratio_kind") if picked else None),
        section_factor_value=(picked.inputs.get("ratio") if picked else None),
        thickness_in=picked.thickness_in if picked else None,
        thickness_source=picked.source if picked else None,
        resolution_status=status,
    )
    item = None
    if picked is None:
        item = ReviewItem(
            project_id=project.id,
            scenario_id=scenario.id,
            kind="conflict" if res.status == "conflict" else "unknown",
            category="design",
            subject_type="member",
            subject_id=member.id,
            title=(
                f"{member.canonical_section}: thickness under {q.design} {q.rating_hours} h "
                f"is {res.status}"
            ),
            known=[f"design {q.design}", f"rating {q.rating_hours} h"]
            + ([f"product {q.product}"] if q.product else [])
            + ([f"restraint {q.restraint}"] if q.restraint else []),
            likely=[f"{c.thickness_in} in by {c.method}" for c in res.candidates if c.thickness_in],
            why="; ".join(res.reasons),
            missing=[] if res.candidates else ["a printed table row or an applicable equation"],
            options=[
                {
                    "thickness_in": c.thickness_in,
                    "method": c.method,
                    "kind": c.assertion_kind,
                    "source": c.source,
                }
                for c in res.candidates
            ],
            actor=actor,
        )
        db.add(item)
        db.commit()
    elif choice is not None:
        for it in db.scalars(
            select(ReviewItem).where(
                ReviewItem.subject_id == member.id,
                ReviewItem.scenario_id == scenario.id,
                ReviewItem.category == "design",
                ReviewItem.status == "open",
            )
        ):
            it.status = "resolved"
            it.resolution_assertion_id = row.assertion_id
            it.resolved_at = datetime.now(UTC)
        db.commit()
    return row, item


def open_review_items(
    db: Session, project: Project, scenario: Scenario | None = None
) -> list[ReviewItem]:
    stmt = select(ReviewItem).where(
        ReviewItem.project_id == project.id, ReviewItem.status == "open"
    )
    if scenario:
        stmt = stmt.where(ReviewItem.scenario_id == scenario.id)
    return list(db.scalars(stmt))


def resolution_meter(db: Session, project: Project, scenario: Scenario) -> dict:
    """Counts the vision's meter needs: members, open review items by category, and how many
    members have each assignment in this scenario. Derived from rows, never estimated."""
    members = list(
        db.scalars(select(MemberInstance).where(MemberInstance.project_id == project.id))
    )
    open_items = open_review_items(db, project, scenario)
    by_cat: dict[str, int] = {}
    for it in open_items:
        by_cat[it.category] = by_cat.get(it.category, 0) + 1
    assigned = {}
    for name, table in ASSIGNMENT_TABLES.items():
        assigned[name] = sum(
            1 for m in members if current(db, table, m.id, scenario.id) is not None
        )
    unresolved_designs = sum(
        1
        for m in members
        if (d := current(db, DesignAssignment, m.id, scenario.id)) is not None
        and d.thickness_in is None
    )
    return {
        "members": len(members),
        "members_needing_physical_review": sum(1 for m in members if m.review_state != "accepted"),
        "open_review_items": len(open_items),
        "open_by_category": by_cat,
        "assigned": assigned,
        "designs_unresolved": unresolved_designs,
    }


def freeze_stage(db: Session, project: Project, scenario: Scenario, name: str, actor: str) -> Stage:
    """Snapshot every current assignment of the scenario under a stage name."""
    members = list(
        db.scalars(select(MemberInstance).where(MemberInstance.project_id == project.id))
    )
    snap = {"scenario": scenario.id, "members": {}}
    for m in members:
        entry = {}
        for key, table in ASSIGNMENT_TABLES.items():
            row = current(db, table, m.id, scenario.id)
            entry[key] = _public(row) if row else None
        snap["members"][m.id] = entry
    stage = Stage(
        project_id=project.id, scenario_id=scenario.id, name=name, snapshot=snap, actor=actor
    )
    db.add(stage)
    db.flush()
    _audit(db, project.id, actor, "stage.freeze", "stage", stage.id, None, {"name": name})
    db.commit()
    return stage


def assign_designs_for_project(
    db: Session,
    project: Project,
    scenario: Scenario,
    lib,
    design: str,
    rating_hours: float,
    product: str | None,
    restraint: str | None,
    role: str | None = None,
    application: str = "contour",
    condition: str | None = None,
    actor: str = "design-engine",
) -> dict:
    """Resolve and persist a thickness for every member of the project (optionally one role)
    under one design/rating/product. Returns counts by resolution status."""
    from ffs.design.thickness import ThicknessQuery, resolve

    counts: dict[str, int] = {}
    members = list(
        db.scalars(select(MemberInstance).where(MemberInstance.project_id == project.id))
    )
    for m in members:
        if role and m.member_type != role:
            continue
        q = ThicknessQuery(
            design,
            m.canonical_section,
            rating_hours,
            restraint,
            product,
            application=application,
            condition=condition,
        )
        res = resolve(lib, q)
        assign_design(db, project, m, scenario, res, actor=actor)
        counts[res.status] = counts.get(res.status, 0) + 1
    return counts


def quantities_for_project(
    db: Session,
    project: Project,
    scenario: Scenario,
    aisc=None,
    waste_pct: float | None = None,
    waste_source: str | None = None,
    yield_bdft_per_bag: float | None = None,
    yield_source: str | None = None,
    workbook_sf: dict | None = None,
):
    """Member quantities from the current design and condition assignments of a scenario."""
    from ffs.design.quantities import aggregate, member_quantity

    rows = []
    members = list(
        db.scalars(select(MemberInstance).where(MemberInstance.project_id == project.id))
    )
    for m in members:
        d = current(db, DesignAssignment, m.id, scenario.id)
        c = current(db, ConditionAssignment, m.id, scenario.id)
        sides, sides_source = (
            (c.sides, "condition_assignment") if c and c.sides else (None, "assumed")
        )
        src = d.thickness_source if d else None
        inputs = None
        if d and d.section_factor_method and d.section_factor_value is not None:
            inputs = {"ratio": d.section_factor_value, "ratio_kind": d.section_factor_method}
        rows.append(
            member_quantity(
                m.id,
                m.canonical_section,
                m.level,
                m.member_type,
                m.length_in,
                d.thickness_in if d else None,
                d.design if d else None,
                d.product if d else None,
                src,
                inputs,
                sides,
                sides_source,
                aisc,
                workbook_sf,
            )
        )
    return aggregate(rows, scenario.id, waste_pct, waste_source, yield_bdft_per_bag, yield_source)
