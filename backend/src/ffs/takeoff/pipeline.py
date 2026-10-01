"""Milestone-1 pipeline: structural PDF page → MemberRecords with evidence and assertions."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ffs.core.assertions import SourceRef
from ffs.ingest.grids import GridLine, detect_grids
from ffs.ingest.pdf import PageData
from ffs.ingest.scale import ScaleCandidate, parse_scale_text
from ffs.steel.aisc import ShapeDatabase
from ffs.steel.designation import ShapeFamily
from ffs.steel.geometry import GeometryMatch, associate
from ffs.steel.labels import LabelContext, MemberLabel, find_member_labels
from ffs.takeoff.model import MemberRecord, assumption, calc, fact, interp, new_member

_SHEET_NO = re.compile(r"^(?:[A-Z]{1,2}[- ]?\d{1,3}(?:\.\d{1,2})?)$")
_LEVEL = re.compile(
    r"\b(?:(LEVEL|LVL|FLOOR|FLR)\s*(\d{1,2}|[A-Z]{1,2}\d?)|(ROOF|MEZZANINE|MEZZ|PENTHOUSE|BASEMENT|FOUNDATION)|"
    r"(\d{1,2})(?:ST|ND|RD|TH)\s+(?:FLOOR|LEVEL))\b",
    re.IGNORECASE,
)


@dataclass
class SheetInfo:
    sheet_no: str | None
    title: str | None
    level: str | None
    level_confidence: float
    scale: ScaleCandidate | None
    scale_candidates: list[ScaleCandidate]
    grids: list[GridLine]
    notes: list[str] = field(default_factory=list)


def _title_block_spans(page: PageData):
    """Spans in the right 22% / bottom 15% band — where title blocks usually live."""
    for s in page.spans:
        cx, cy = s.center
        if cx > page.width * 0.78 or cy > page.height * 0.85:
            yield s


def detect_sheet_info(page: PageData, scale_override: str | None = None) -> SheetInfo:
    notes: list[str] = []
    sheet_no = None
    title = None
    level = None
    lconf = 0.0
    tb = list(_title_block_spans(page))
    # sheet number: a lone span like S-201 / S201 / S2.01, largest font in title block wins
    cand = [s for s in tb if _SHEET_NO.match(s.text.strip().upper())]
    if cand:
        sheet_no = max(cand, key=lambda s: s.size).text.strip().upper()
    # level: look in title block first, then anywhere
    for pool, conf in ((tb, 0.85), (page.spans, 0.6)):
        for s in pool:
            m = _LEVEL.search(s.text)
            if m:
                level = m.group(0).upper().replace("LVL", "LEVEL").replace("FLR", "FLOOR")
                title = s.text.strip()
                lconf = conf
                break
        if level:
            break
    if level is None:
        notes.append("no level found on sheet; member level = UNKNOWN — REVIEW REQUIRED")
    scales: list[ScaleCandidate] = []
    for s in page.spans:
        sc = parse_scale_text(s.text)
        if sc:
            sc.bbox = s.bbox
            scales.append(sc)
    # prefer title-block scale text, else the first found
    chosen: ScaleCandidate | None = None
    if scale_override:
        chosen = parse_scale_text(scale_override)
        if chosen:
            chosen.source = "manual"
            chosen.confidence = 0.98
            chosen.evidence = f"operator override: {scale_override}"
    if chosen is None and scales:
        tb_ids = {id(s) for s in tb}
        tbs = [sc for sc in scales if any(sp.bbox == sc.bbox for sp in tb if id(sp) in tb_ids)]
        chosen = (tbs or scales)[0]
        distinct = {round(sc.inches_per_point, 6) for sc in scales}
        if len(distinct) > 1:
            notes.append(
                f"{len(distinct)} different scales found on sheet; multi-scale viewports likely"
            )
            chosen.confidence = min(chosen.confidence, 0.6)
    if chosen is None:
        notes.append("no scale found; lengths cannot be computed without calibration")
    grids = detect_grids(page)
    return SheetInfo(sheet_no, title, level, lconf, chosen, scales, grids, notes)


def _member_type(label: MemberLabel) -> tuple[str, float]:
    fam = label.parsed.family
    if fam in (ShapeFamily.JOIST, ShapeFamily.JOIST_GIRDER):
        return ("joist", 0.9)
    if fam in (ShapeFamily.W, ShapeFamily.HP, ShapeFamily.S, ShapeFamily.M):
        # On a framing plan, a labelled W-shape with a parallel line is a beam/girder; columns
        # appear as small squares/wide-flange symbols and are usually marked via schedules.
        return ("beam", 0.7)
    if fam in (ShapeFamily.HSS_RECT, ShapeFamily.HSS_ROUND, ShapeFamily.PIPE):
        return ("unknown", 0.4)  # HSS on plan: brace, column, or beam — needs review
    if fam in (ShapeFamily.C, ShapeFamily.MC, ShapeFamily.L, ShapeFamily.DOUBLE_L, ShapeFamily.WT):
        return ("misc", 0.6)
    return ("unknown", 0.3)


def run_page(
    page: PageData,
    shapes: ShapeDatabase | None = None,
    scale_override: str | None = None,
    level_override: str | None = None,
) -> tuple[SheetInfo, list[MemberRecord], list[MemberLabel]]:
    info = detect_sheet_info(page, scale_override)
    if level_override:
        info.level, info.level_confidence = level_override, 0.98
    labels = find_member_labels(page, shapes)
    plan_labels = [lab for lab in labels if lab.context == LabelContext.PLAN_LABEL]
    matches: list[GeometryMatch] = associate(page, plan_labels, info.scale, info.grids)
    members: list[MemberRecord] = []
    level = info.level or "UNKNOWN — REVIEW REQUIRED"
    for gm in matches:
        lab = gm.label
        src = SourceRef(page.document, page.page_number, info.sheet_no, lab.span.bbox)
        mtype, tconf = _member_type(lab)
        asserts = [
            fact("label_text", lab.span.text, src, 1.0, "text span extracted from PDF text layer"),
            interp(
                "canonical_section",
                lab.canonical,
                lab.id_confidence,
                "; ".join(["designation parser"] + lab.notes),
                src,
            ),
            interp("member_type", mtype, tconf, "family + plan context heuristic", src),
            interp(
                "status",
                lab.status,
                0.9 if lab.parsed.prefix else 0.6,
                "prefix (E)/(N)/(D) or assumed new",
                src,
            ),
        ]
        if info.level:
            asserts.append(
                interp(
                    "level",
                    info.level,
                    info.level_confidence,
                    f"from sheet title '{info.title}'",
                    src,
                )
            )
        else:
            asserts.append(assumption("level", level, "no level text found on sheet"))
        length_source = "none"
        if gm.chain is not None and gm.length_in is not None and info.scale is not None:
            length_source = "geometry"
            asserts.append(
                calc(
                    "length_in",
                    round(gm.length_in, 2),
                    "chain_length_x_scale",
                    {
                        "chain_pt": round(gm.chain.length, 2),
                        "inches_per_point": info.scale.inches_per_point,
                        "scale": info.scale.label,
                        "scale_source": info.scale.source,
                        "scale_confidence": info.scale.confidence,
                    },
                    gm.length_confidence,
                    gm.reasoning
                    + (f"; {gm.dimension_corroboration}" if gm.dimension_corroboration else ""),
                )
            )
        review = "unreviewed"
        notes = list(lab.notes)
        if gm.chain is None:
            notes.append("no member geometry found for label")
            review = "conflict"
        if lab.typical:
            notes.append("label marked TYP — may represent multiple members; review")
            review = "conflict"
        members.append(
            new_member(
                level=level,
                sheet_no=info.sheet_no,
                member_mark=lab.span.text.strip(),
                canonical_section=lab.canonical,
                family=lab.parsed.family.value,
                member_type=mtype,
                status=lab.status,
                length_in=None if gm.length_in is None else round(gm.length_in, 2),
                length_source=length_source,
                start_xy=None
                if gm.chain is None
                else (round(gm.chain.x0, 2), round(gm.chain.y0, 2)),
                end_xy=None if gm.chain is None else (round(gm.chain.x1, 2), round(gm.chain.y1, 2)),
                start_grid=gm.start_grid,
                end_grid=gm.end_grid,
                orientation_deg=None if gm.chain is None else round(gm.chain.angle_deg, 2),
                confidence_id=round(lab.id_confidence, 3),
                confidence_geom=gm.geometry_confidence,
                confidence_length=gm.length_confidence,
                confidence_level=info.level_confidence,
                review_state=review,
                evidence=[
                    __import__("ffs.takeoff.model", fromlist=["Evidence"]).Evidence(
                        kind="plan_label",
                        document=page.document,
                        page=page.page_number,
                        sheet_no=info.sheet_no,
                        bbox=lab.span.bbox,
                        raw_text=lab.span.text,
                        extraction_path=page.extraction_path.value,
                        confidence=lab.id_confidence,
                    )
                ],
                assertions=asserts,
                notes=notes,
            )
        )
    members = dedupe_same_page(members)
    return info, members, labels


def dedupe_same_page(members: list[MemberRecord], tol: float = 2.0) -> list[MemberRecord]:
    """Two labels on the same chain with the same section = one member, two evidence refs."""
    out: list[MemberRecord] = []
    for m in members:
        dup = None
        if m.start_xy and m.end_xy:
            for o in out:
                if (
                    o.canonical_section == m.canonical_section
                    and o.start_xy
                    and o.end_xy
                    and abs(o.start_xy[0] - m.start_xy[0]) <= tol
                    and abs(o.start_xy[1] - m.start_xy[1]) <= tol
                    and abs(o.end_xy[0] - m.end_xy[0]) <= tol
                    and abs(o.end_xy[1] - m.end_xy[1]) <= tol
                ):
                    dup = o
                    break
        if dup is None:
            out.append(m)
        else:
            dup.evidence.extend(m.evidence)
            dup.notes.append(f"duplicate label merged: '{m.member_mark}'")
    return out
