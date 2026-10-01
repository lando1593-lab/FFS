"""Service layer: the only sanctioned way to write members (enforces evidence + audit)."""

from __future__ import annotations

from dataclasses import asdict

from sqlalchemy.orm import Session

from ffs.db.models import AssertionRow, AuditEvent, MemberEvidence, MemberInstance, Project
from ffs.takeoff.model import MemberRecord


class ProvenanceError(ValueError):
    pass


def save_members(
    db: Session,
    project: Project,
    members: list[MemberRecord],
    actor: str = "pipeline",
    sheet_id: str | None = None,
) -> int:
    n = 0
    for m in members:
        if not m.evidence:
            raise ProvenanceError(f"member {m.id} has no evidence; refusing to store")
        row = MemberInstance(
            id=m.id,
            project_id=project.id,
            sheet_id=sheet_id,
            level=m.level,
            member_mark=m.member_mark,
            canonical_section=m.canonical_section,
            family=m.family,
            member_type=m.member_type,
            status=m.status,
            length_in=m.length_in,
            length_source=m.length_source,
            start_x=None if m.start_xy is None else m.start_xy[0],
            start_y=None if m.start_xy is None else m.start_xy[1],
            end_x=None if m.end_xy is None else m.end_xy[0],
            end_y=None if m.end_xy is None else m.end_xy[1],
            start_grid=m.start_grid,
            end_grid=m.end_grid,
            orientation_deg=m.orientation_deg,
            confidence_id=m.confidence_id,
            confidence_geom=m.confidence_geom,
            confidence_length=m.confidence_length,
            confidence_level=m.confidence_level,
            review_state=m.review_state,
        )
        db.add(row)
        for ev in m.evidence:
            db.add(
                MemberEvidence(
                    member_id=m.id,
                    sheet_id=sheet_id,
                    kind=ev.kind,
                    document=ev.document,
                    page=ev.page,
                    bbox=list(ev.bbox),
                    raw_text=ev.raw_text,
                    extraction_path=ev.extraction_path,
                    confidence=ev.confidence,
                )
            )
        for a in m.assertions:
            db.add(
                AssertionRow(
                    member_id=m.id,
                    kind=a.kind.value,
                    key=a.key,
                    value=a.value,
                    method=a.method,
                    inputs=a.inputs or None,
                    reasoning=a.reasoning,
                    source_ref=asdict(a.source) if a.source else None,
                    confidence=a.confidence,
                )
            )
        db.add(
            AuditEvent(
                project_id=project.id,
                actor=actor,
                action="member.create",
                subject_type="member",
                subject_id=m.id,
                before=None,
                after=m.to_dict(),
                reason="takeoff pipeline",
            )
        )
        n += 1
    db.commit()
    return n
