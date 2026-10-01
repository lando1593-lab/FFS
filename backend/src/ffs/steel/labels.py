"""Find designation labels on a page and classify their context.

Context classes (FR-STEEL-03): plan_label, schedule_entry, legend, note, detail_annotation,
callout. Classification is heuristic and carries confidence; a wrong class is a review item, not
a silent error.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from enum import StrEnum

from ffs.ingest.pdf import PageData, TextSpan
from ffs.steel.aisc import ShapeDatabase
from ffs.steel.designation import ParsedDesignation, find_designations


class LabelContext(StrEnum):
    PLAN_LABEL = "plan_label"
    SCHEDULE_ENTRY = "schedule_entry"
    LEGEND = "legend"
    NOTE = "note"
    DETAIL_ANNOTATION = "detail_annotation"
    CALLOUT = "callout"
    UNKNOWN = "unknown"


@dataclass
class MemberLabel:
    span: TextSpan
    parsed: ParsedDesignation
    context: LabelContext
    context_confidence: float
    id_confidence: float
    validated: bool
    status: str  # new / existing / demo / unknown
    typical: bool = False
    notes: list[str] = field(default_factory=list)

    @property
    def canonical(self) -> str:
        return self.parsed.canonical


_TABLE_WORDS = re.compile(r"\b(SCHEDULE|LEGEND|TABLE)\b", re.IGNORECASE)
_NOTE_WORDS = re.compile(r"\b(NOTE|NOTES|TYP\.?|TYPICAL|U\.?N\.?O\.?|UNLESS)\b", re.IGNORECASE)
_TYP = re.compile(r"\bTYP(?:ICAL)?\.?\b", re.IGNORECASE)


def _column_clusters(spans: list[TextSpan], x_tol: float = 2.0) -> dict[int, list[TextSpan]]:
    """Group spans that form a *dense* left-aligned stack (same rotation, row pitch ≤ 3× font
    size) — the signature of a schedule or legend. Labels on a regular framing grid also align,
    but their pitch is a bay width, so the density rule keeps them out."""
    buckets: dict[tuple[float, int], list[TextSpan]] = defaultdict(list)
    for s in spans:
        key = (round(s.bbox[0] / x_tol), int(s.rotation_deg))
        buckets[key].append(s)
    out: dict[int, list[TextSpan]] = {}
    for members in buckets.values():
        if len(members) < 3:
            continue
        members = sorted(members, key=lambda s: s.bbox[1])
        run: list[TextSpan] = [members[0]]
        for prev, cur in zip(members, members[1:], strict=False):
            pitch = cur.bbox[1] - prev.bbox[1]
            if pitch <= max(prev.size, cur.size) * 3.0:
                run.append(cur)
            else:
                if len(run) >= 3:
                    for m in run:
                        out[id(m)] = run
                run = [cur]
        if len(run) >= 3:
            for m in run:
                out[id(m)] = run
    return out


def _neighbors_text(page: PageData, span: TextSpan, radius: float) -> str:
    cx, cy = span.center
    parts = []
    for s in page.spans:
        sx, sy = s.center
        if abs(sx - cx) <= radius and abs(sy - cy) <= radius:
            parts.append(s.text)
    return " ".join(parts)


def find_member_labels(page: PageData, shapes: ShapeDatabase | None = None) -> list[MemberLabel]:
    cands: list[tuple[TextSpan, ParsedDesignation]] = []
    for sp in page.spans:
        for pd in find_designations(sp.text):
            cands.append((sp, pd))
    if not cands:
        return []

    aligned = _column_clusters([sp for sp, _ in cands])
    page_text_has_schedule = bool(_TABLE_WORDS.search(page.text()))

    labels: list[MemberLabel] = []
    for sp, pd in cands:
        notes = list(pd.notes)
        line_text = " ".join(
            s.text for s in page.spans if s.block == sp.block and s.line == sp.line
        )
        near = _neighbors_text(page, sp, radius=max(60.0, sp.size * 6))
        context, cconf = LabelContext.PLAN_LABEL, 0.7
        if id(sp) in aligned and page_text_has_schedule:
            context, cconf = LabelContext.SCHEDULE_ENTRY, 0.75
            if _TABLE_WORDS.search(near) and "LEGEND" in near.upper():
                context = LabelContext.LEGEND
        elif id(sp) in aligned:
            context, cconf = LabelContext.SCHEDULE_ENTRY, 0.55
            notes.append("column-aligned with other designations; schedule/legend suspected")
        elif _NOTE_WORDS.search(line_text) and len(line_text) > len(pd.raw) + 12:
            context, cconf = LabelContext.NOTE, 0.7
        elif (
            sp.rotation_deg in (0.0, 90.0, 180.0, 270.0)
            and len(line_text.strip()) <= len(pd.raw) + 6
        ):
            context, cconf = LabelContext.PLAN_LABEL, 0.8
        typical = bool(_TYP.search(line_text)) or bool(_TYP.search(near))

        status = {"E": "existing", "N": "new", "D": "demo"}.get(pd.prefix or "", "unknown")
        if status == "unknown":
            status = "new"  # drawing convention: unprefixed = new; recorded as such with a note
            notes.append("status assumed NEW (no (E)/(D) prefix)")

        validated = False
        id_conf = pd.confidence
        if shapes is not None:
            if pd.canonical in shapes:
                validated = True
                id_conf = min(1.0, id_conf + 0.03)
            else:
                id_conf = min(id_conf, 0.5)
                notes.append(f"{pd.canonical} not found in shape database {shapes.source}")
        else:
            id_conf = min(id_conf, 0.9)
            notes.append("no shape database loaded; syntactic parse only")

        labels.append(
            MemberLabel(
                span=sp,
                parsed=pd,
                context=context,
                context_confidence=cconf,
                id_confidence=id_conf,
                validated=validated,
                status=status,
                typical=typical,
                notes=notes,
            )
        )
    return labels
