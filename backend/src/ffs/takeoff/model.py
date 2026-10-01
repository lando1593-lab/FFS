"""In-memory takeoff records produced by the M1 pipeline. Persisted via ``ffs.db``."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from ffs.core.assertions import Assertion, AssertionKind, SourceRef
from ffs.core.ids import new_id
from ffs.core.units import inches_to_ft_in


@dataclass
class Evidence:
    kind: str  # plan_label / schedule_row / ...
    document: str
    page: int
    sheet_no: str | None
    bbox: tuple[float, float, float, float]
    raw_text: str
    extraction_path: str
    confidence: float


@dataclass
class MemberRecord:
    id: str
    level: str
    sheet_no: str | None
    member_mark: str
    canonical_section: str
    family: str
    member_type: str  # beam / column / brace / joist / misc / unknown
    status: str  # new / existing / demo
    length_in: float | None
    length_source: str  # geometry / dimension_text / schedule / manual / none
    start_xy: tuple[float, float] | None
    end_xy: tuple[float, float] | None
    start_grid: str | None
    end_grid: str | None
    orientation_deg: float | None
    confidence_id: float
    confidence_geom: float
    confidence_length: float
    confidence_level: float
    review_state: str  # unreviewed / accepted / edited / excluded / conflict
    evidence: list[Evidence] = field(default_factory=list)
    assertions: list[Assertion] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def length_ft(self) -> float | None:
        return None if self.length_in is None else self.length_in / 12.0

    @property
    def length_display(self) -> str:
        return (
            "UNKNOWN — REVIEW REQUIRED"
            if self.length_in is None
            else inches_to_ft_in(self.length_in)
        )

    @property
    def status_color(self) -> str:
        """green=verified, yellow=uncertain, red=conflict, gray=excluded (per product spec)."""
        if self.review_state == "excluded":
            return "gray"
        if self.review_state == "conflict":
            return "red"
        if self.review_state == "accepted":
            return "green"
        if min(self.confidence_id, self.confidence_geom, self.confidence_length) >= 0.8:
            return "green"
        return "yellow"

    @property
    def needs_review(self) -> bool:
        return self.status_color in ("yellow", "red")

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["length_display"] = self.length_display
        d["status_color"] = self.status_color
        d["assertions"] = [
            {**asdict(a), "kind": a.kind.value, "source": (asdict(a.source) if a.source else None)}
            for a in self.assertions
        ]
        return d


def new_member(**kw: Any) -> MemberRecord:
    return MemberRecord(id=new_id("mem"), **kw)


def fact(key: str, value: Any, src: SourceRef, conf: float, reasoning: str) -> Assertion:
    return Assertion(AssertionKind.FACT, key, value, conf, reasoning, source=src)


def calc(
    key: str, value: Any, method: str, inputs: dict[str, Any], conf: float, reasoning: str
) -> Assertion:
    return Assertion(
        AssertionKind.CALCULATION, key, value, conf, reasoning, method=method, inputs=inputs
    )


def interp(
    key: str, value: Any, conf: float, reasoning: str, src: SourceRef | None = None
) -> Assertion:
    return Assertion(AssertionKind.INTERPRETATION, key, value, conf, reasoning, source=src)


def assumption(key: str, value: Any, reasoning: str) -> Assertion:
    return Assertion(AssertionKind.ASSUMPTION, key, value, 0.5, reasoning)
