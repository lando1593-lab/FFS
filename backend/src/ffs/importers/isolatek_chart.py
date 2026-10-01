"""Importer for Isolatek "Designs & Thicknesses" chart PDFs (isolatek.com/storage/designs_thickness/…).

Layout (text-extractable, several pages): a header block with the design number, the deck /
concrete condition, the products the chart covers and the chart date; then a table with
columns ``ASTM Desig. | W/D | Metric Desig. | M/D | Hp/A | 1-Hour | 1-1/2 Hour | 2-Hour |
3-Hour | 4-Hour`` (column sets vary: column charts use W/D only, tube charts A/P). Rows carry
the depth family forward: ``W44 x 335`` is followed by ``290``, ``262`` … meaning W44 x 290,
W44 x 262. Section markers such as ``Unrestrained Beam`` switch the restraint condition for the
rows that follow.

Every row records page, the family label it was derived from, W/D (and Hp/A, M/D when present),
and the thickness per rating exactly as printed plus parsed inches. Values are manufacturer data
(authority level 6) tied to a design; nothing is interpolated here.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ffs.importers.ul_design import frac_in
from ffs.steel.designation import find_designations

_DESIGN_LINE = re.compile(
    r"^(?:DESIGN\s+)?(?P<d>[A-Z]{1,2}-?\d{3,4}[a-z]?)(?:\s*(?:-|&|and)\s*(?P<d2>[A-Z]{1,2}-?\d{3,4}[a-z]?))?\b",
    re.IGNORECASE,
)
_DATE = re.compile(r"\b(\d{1,2}/\d{1,2}/\d{2,4})\b")
_RATING_HDR = re.compile(r"^(?P<r>\d(?:-\d/\d)?)\s*-?\s*Hour\s*$", re.IGNORECASE)
_FAMILY = re.compile(
    r"^(?P<fam>W|HP|M|S|C|MC|WT|L|HSS|PIPE|ST|SP|RT|TS)\s*(?P<depth>\d+(?:\.\d+)?)\s*x\s*(?P<rest>.+)$",
    re.IGNORECASE,
)
_WEIGHT_ONLY = re.compile(r"^\d+(?:\.\d+)?$")
_FRACTION = re.compile(r"^(?:\d+(?:-\d+/\d+)?|\d+/\d+|NR|N/R|—|-)$", re.IGNORECASE)
_SECTION = re.compile(
    r"^(?P<s>(?:Un)?restrained\s+(?:Beam|Column|Assembly)s?|Columns?|Beams?|Joists?)\s*$",
    re.IGNORECASE,
)


@dataclass
class ChartRow:
    page: int
    section: str | None  # restraint / member section marker in force
    member_label: str  # reconstructed, e.g. "W44 x 290"
    canonical: str | None
    family_label: str  # the family row this one derives from, e.g. "W44 x 335"
    wd: float | None
    metric_label: str | None
    md: float | None
    hp_a: float | None
    thickness_as_printed: list[str]
    thickness_in: list[float | None]
    not_rated: list[bool]


@dataclass
class ChartRecord:
    source_file: str
    design: str | None
    title_lines: list[str]
    condition: str | None
    products: str | None
    chart_date: str | None
    rating_columns: list[str]
    rows: list[ChartRow]
    notes: list[str] = field(default_factory=list)
    cross_reference: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _floatish(s: str) -> bool:
    return bool(re.fullmatch(r"\d+(?:\.\d+)?", s.strip()))


def _page_lines(page) -> list[str]:
    return [ln.strip() for ln in page.get_text("text").split("\n")]


def parse_chart_pdf(path: str | Path) -> ChartRecord:
    import pymupdf

    path = Path(path)
    doc = pymupdf.open(path)
    rec = ChartRecord(path.name, None, [], None, None, None, [], [])
    try:
        first = _page_lines(doc[0])
        head = [ln for ln in first[:16] if ln]
        rec.title_lines = head[:8]
        for ln in head:
            m = _DESIGN_LINE.match(ln)
            if m and rec.design is None:
                rec.design = m.group("d").upper() + (
                    f"/{m.group('d2').upper()}" if m.group("d2") else ""
                )
        dm = _DATE.search(" ".join(first[:6]))
        rec.chart_date = dm.group(1) if dm else None
        cond = [
            ln
            for ln in head
            if re.search(
                r"deck|concrete|column|joist|beam|tube|pipe|flange|angle|channel", ln, re.IGNORECASE
            )
            and not re.search(r"CAFCO|ISOLATEK", ln)
        ]
        rec.condition = " ".join(cond[:3]) or None
        prods = [ln for ln in head if re.search(r"CAFCO|ISOLATEK", ln)]
        rec.products = " ".join(prods) or None
        xref = [ln for ln in first if re.search(r"^For (Beams|Joists|Columns): Use Design", ln)]
        if xref:
            rec.cross_reference = " | ".join(xref)
        for pi in range(len(doc)):
            lines = _page_lines(doc[pi])
            hdr_idx = [i for i, ln in enumerate(lines) if _RATING_HDR.match(ln)]
            if not hdr_idx:
                continue
            cols = [_RATING_HDR.match(lines[i]).group("r") + " Hr" for i in hdr_idx]
            if not rec.rating_columns:
                rec.rating_columns = cols
            n = len(cols)
            pre = lines[: hdr_idx[0]]
            has_metric = any(re.search(r"Metric", ln) for ln in pre)
            has_md = any(re.fullmatch(r"M/D", ln) for ln in pre)
            has_hpa = any(re.fullmatch(r"Hp/A", ln, re.IGNORECASE) for ln in pre)
            has_wd = any(re.fullmatch(r"(W/D|A/P)", ln, re.IGNORECASE) for ln in pre)
            i = hdr_idx[-1] + 1
            section = None
            family: str | None = None
            fam_prefix: str | None = None
            while i < len(lines):
                ln = lines[i]
                if not ln:
                    i += 1
                    continue
                sm = _SECTION.match(ln)
                if sm:
                    section = sm.group("s")
                    i += 1
                    continue
                fm = _FAMILY.match(ln)
                if fm:
                    family = ln
                    fam_prefix = f"{fm.group('fam').upper()}{fm.group('depth')} x "
                    label = ln
                elif (
                    _WEIGHT_ONLY.match(ln)
                    and fam_prefix
                    and i + 1 < len(lines)
                    and _floatish(lines[i + 1])
                ):
                    label = fam_prefix + ln
                else:
                    i += 1
                    continue
                j = i + 1
                wd = md = hpa = None
                metric = None
                if has_wd and j < len(lines) and _floatish(lines[j]):
                    wd = float(lines[j])
                    j += 1
                if (
                    has_metric
                    and j < len(lines)
                    and (_FAMILY.match(lines[j]) or _WEIGHT_ONLY.match(lines[j]))
                ):
                    metric = lines[j]
                    j += 1
                if has_md and j < len(lines) and _floatish(lines[j]):
                    md = float(lines[j])
                    j += 1
                if has_hpa and j < len(lines) and _floatish(lines[j]):
                    hpa = float(lines[j])
                    j += 1
                vals: list[str] = []
                while j < len(lines) and len(vals) < n and _FRACTION.match(lines[j]):
                    vals.append(lines[j])
                    j += 1
                if len(vals) < n:
                    rec.notes.append(
                        f"p{pi + 1}: row '{label}' has {len(vals)} of {n} thickness cells"
                    )
                    i = j
                    continue
                des = find_designations(label.replace(" x ", "X").replace(" ", ""))
                rec.rows.append(
                    ChartRow(
                        pi + 1,
                        section,
                        label,
                        des[0].canonical if len(des) == 1 else None,
                        family or label,
                        wd,
                        metric,
                        md,
                        hpa,
                        vals,
                        [None if v.upper().startswith("N") else frac_in(v) for v in vals],
                        [v.upper().startswith("N") for v in vals],
                    )
                )
                i = j
    finally:
        doc.close()
    return rec


def write_chart(rec: ChartRecord, out_dir: str | Path) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(rec.source_file).stem
    (out_dir / f"{stem}.json").write_text(json.dumps(rec.to_dict(), indent=1, ensure_ascii=False))
    with (out_dir / f"{stem}.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "design",
                "condition",
                "products",
                "chart_date",
                "page",
                "section",
                "member",
                "canonical",
                "wd",
                "hp_a",
                *rec.rating_columns,
            ]
        )
        for r in rec.rows:
            w.writerow(
                [
                    rec.design,
                    rec.condition,
                    rec.products,
                    rec.chart_date,
                    r.page,
                    r.section,
                    r.member_label,
                    r.canonical,
                    r.wd,
                    r.hp_a,
                    *r.thickness_as_printed,
                ]
            )
    return out_dir / f"{stem}.json"
