"""Assertion classes and provenance records.

Every statement the system stores about a project is an :class:`Assertion` with a class from
:class:`AssertionKind`, a confidence, a source reference, and a reasoning path. See ADR-0002.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class AssertionKind(StrEnum):
    FACT = "FACT"  # extracted directly from a source document, with location
    INTERPRETATION = "INTERPRETATION"  # a reading of facts a reasonable estimator could dispute
    CALCULATION = "CALCULATION"  # deterministic math over inputs with a stated method
    ASSUMPTION = "ASSUMPTION"  # chosen in the absence of evidence; always flagged
    CODE_PRODUCT_RULE = "CODE_PRODUCT_RULE"  # code / listing / manufacturer rule with revision
    HUMAN_OVERRIDE = "HUMAN_OVERRIDE"  # estimator decision superseding the above


class ExtractionPath(StrEnum):
    PDF_TEXT = "pdf_text"
    PDF_VECTOR = "pdf_vector"
    OCR = "ocr"
    MANUAL = "manual"
    SCHEDULE = "schedule"


@dataclass(frozen=True)
class SourceRef:
    """Where a piece of evidence lives. All fields optional except ``document``."""

    document: str
    page: int | None = None
    sheet_no: str | None = None
    bbox: tuple[float, float, float, float] | None = None  # PDF points, page space
    revision: str | None = None
    rule_id: str | None = None  # for CODE_PRODUCT_RULE: e.g. "IBC2021:T601" or "UL:N-xxx@2024-03"

    def short(self) -> str:
        parts = [self.document]
        if self.sheet_no:
            parts.append(self.sheet_no)
        elif self.page is not None:
            parts.append(f"p{self.page}")
        if self.bbox:
            x0, y0, x1, y1 = self.bbox
            parts.append(f"@({x0:.0f},{y0:.0f},{x1:.0f},{y1:.0f})")
        return " ".join(parts)


@dataclass
class Assertion:
    kind: AssertionKind
    key: str
    value: Any
    confidence: float
    reasoning: str
    source: SourceRef | None = None
    method: str | None = None
    inputs: dict[str, Any] = field(default_factory=dict)
    verified_by: str | None = None
    verified_at: str | None = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence out of range: {self.confidence}")
        if self.kind is AssertionKind.FACT and self.source is None:
            raise ValueError("FACT assertions must carry a SourceRef")
        if self.kind is AssertionKind.CALCULATION and not self.method:
            raise ValueError("CALCULATION assertions must name a method")

    @property
    def needs_review(self) -> bool:
        return self.kind is AssertionKind.ASSUMPTION or self.confidence < 0.8


UNKNOWN_REVIEW_REQUIRED = "UNKNOWN — REVIEW REQUIRED"
