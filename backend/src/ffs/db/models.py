"""SQLAlchemy models — Milestone-1 subset of the data model in docs/04-data-model.md.

PostgreSQL in production, SQLite in tests. JSON columns hold evidence detail; FK columns hold
the relationships that queries and QA checks need. Every table has a ULID primary key.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, Float, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship

from ffs.core.ids import new_id


def _now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("prj"))
    name: Mapped[str] = mapped_column(String(200))
    number: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(default=_now)
    documents: Mapped[list[ProjectDocument]] = relationship(back_populates="project")
    members: Mapped[list[MemberInstance]] = relationship(back_populates="project")


class ProjectDocument(Base):
    __tablename__ = "project_documents"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("doc"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    filename: Mapped[str] = mapped_column(String(300))
    sha256: Mapped[str | None] = mapped_column(String(64))
    discipline: Mapped[str | None] = mapped_column(String(10))
    revision: Mapped[str | None] = mapped_column(String(50))
    issued_date: Mapped[str | None] = mapped_column(String(20))
    project: Mapped[Project] = relationship(back_populates="documents")
    sheets: Mapped[list[Sheet]] = relationship(back_populates="document")


class Sheet(Base):
    __tablename__ = "sheets"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("sht"))
    document_id: Mapped[str] = mapped_column(ForeignKey("project_documents.id"))
    page_number: Mapped[int] = mapped_column(Integer)
    sheet_no: Mapped[str | None] = mapped_column(String(30))
    title: Mapped[str | None] = mapped_column(String(300))
    level: Mapped[str | None] = mapped_column(String(100))
    level_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    scale_label: Mapped[str | None] = mapped_column(String(60))
    inches_per_point: Mapped[float | None] = mapped_column(Float)
    scale_source: Mapped[str | None] = mapped_column(String(30))
    scale_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    extraction_path: Mapped[str] = mapped_column(String(20), default="pdf_text")
    grids_json: Mapped[list | None] = mapped_column(JSON)
    document: Mapped[ProjectDocument] = relationship(back_populates="sheets")


class SteelShape(Base):
    """Reference table (project-independent). Populated from the AISC database file."""

    __tablename__ = "steel_shapes"
    label: Mapped[str] = mapped_column(String(40), primary_key=True)
    shape_type: Mapped[str] = mapped_column(String(10))
    weight_plf: Mapped[float | None] = mapped_column(Float)
    depth_in: Mapped[float | None] = mapped_column(Float)
    bf_in: Mapped[float | None] = mapped_column(Float)
    tw_in: Mapped[float | None] = mapped_column(Float)
    tf_in: Mapped[float | None] = mapped_column(Float)
    area_in2: Mapped[float | None] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(100))


class MemberInstance(Base):
    __tablename__ = "member_instances"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    sheet_id: Mapped[str | None] = mapped_column(ForeignKey("sheets.id"))
    level: Mapped[str] = mapped_column(String(100))
    zone: Mapped[str | None] = mapped_column(String(100))
    member_mark: Mapped[str] = mapped_column(String(60))
    canonical_section: Mapped[str] = mapped_column(String(40))
    shape_label: Mapped[str | None] = mapped_column(ForeignKey("steel_shapes.label"))
    family: Mapped[str] = mapped_column(String(15))
    member_type: Mapped[str] = mapped_column(String(15))
    status: Mapped[str] = mapped_column(String(10))
    length_in: Mapped[float | None] = mapped_column(Float)
    length_source: Mapped[str] = mapped_column(String(20))
    start_x: Mapped[float | None] = mapped_column(Float)
    start_y: Mapped[float | None] = mapped_column(Float)
    end_x: Mapped[float | None] = mapped_column(Float)
    end_y: Mapped[float | None] = mapped_column(Float)
    start_grid: Mapped[str | None] = mapped_column(String(20))
    end_grid: Mapped[str | None] = mapped_column(String(20))
    orientation_deg: Mapped[float | None] = mapped_column(Float)
    confidence_id: Mapped[float] = mapped_column(Float)
    confidence_geom: Mapped[float] = mapped_column(Float)
    confidence_length: Mapped[float] = mapped_column(Float)
    confidence_level: Mapped[float] = mapped_column(Float)
    review_state: Mapped[str] = mapped_column(String(15), default="unreviewed")
    created_from_revision: Mapped[str | None] = mapped_column(String(50))
    superseded_by_id: Mapped[str | None] = mapped_column(ForeignKey("member_instances.id"))
    created_at: Mapped[datetime] = mapped_column(default=_now)
    project: Mapped[Project] = relationship(back_populates="members")
    evidence: Mapped[list[MemberEvidence]] = relationship(back_populates="member")
    assertions: Mapped[list[AssertionRow]] = relationship(back_populates="member")


class MemberEvidence(Base):
    __tablename__ = "member_evidence"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("evd"))
    member_id: Mapped[str] = mapped_column(ForeignKey("member_instances.id"))
    sheet_id: Mapped[str | None] = mapped_column(ForeignKey("sheets.id"))
    kind: Mapped[str] = mapped_column(String(30))
    document: Mapped[str] = mapped_column(String(300))
    page: Mapped[int] = mapped_column(Integer)
    bbox: Mapped[list] = mapped_column(JSON)
    raw_text: Mapped[str] = mapped_column(Text)
    extraction_path: Mapped[str] = mapped_column(String(20))
    confidence: Mapped[float] = mapped_column(Float)
    member: Mapped[MemberInstance] = relationship(back_populates="evidence")


class AssertionRow(Base):
    __tablename__ = "assertions"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("ast"))
    member_id: Mapped[str | None] = mapped_column(ForeignKey("member_instances.id"))
    subject_type: Mapped[str] = mapped_column(String(30), default="member")
    kind: Mapped[str] = mapped_column(String(20))
    key: Mapped[str] = mapped_column(String(60))
    value: Mapped[object] = mapped_column(JSON)
    method: Mapped[str | None] = mapped_column(String(60))
    inputs: Mapped[dict | None] = mapped_column(JSON)
    reasoning: Mapped[str] = mapped_column(Text)
    source_ref: Mapped[dict | None] = mapped_column(JSON)
    confidence: Mapped[float] = mapped_column(Float)
    verified_by: Mapped[str | None] = mapped_column(String(100))
    verified_at: Mapped[datetime | None] = mapped_column()
    supersedes_id: Mapped[str | None] = mapped_column(ForeignKey("assertions.id"))
    created_at: Mapped[datetime] = mapped_column(default=_now)
    member: Mapped[MemberInstance | None] = relationship(back_populates="assertions")


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("aud"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    actor: Mapped[str] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(60))
    subject_type: Mapped[str] = mapped_column(String(30))
    subject_id: Mapped[str] = mapped_column(String(32))
    before: Mapped[dict | None] = mapped_column(JSON)
    after: Mapped[dict | None] = mapped_column(JSON)
    reason: Mapped[str | None] = mapped_column(Text)
    at: Mapped[datetime] = mapped_column(default=_now)


def make_engine(url: str = "sqlite:///ffs.sqlite"):
    eng = create_engine(url, future=True)
    Base.metadata.create_all(eng)
    return eng


def session(url: str = "sqlite:///ffs.sqlite") -> Session:
    return Session(make_engine(url))
