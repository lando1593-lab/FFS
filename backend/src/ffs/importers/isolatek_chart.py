"""Importer for Isolatek "Designs & Thicknesses" chart PDFs (isolatek.com/storage/designs_thickness/…).

Layout (text-extractable, several pages): a header block with the design number, the deck /
concrete / member condition, the products the chart covers and the chart date; then a table with
columns such as ``ASTM Desig. | [Wall Thk] | W/D or A/P | Metric Desig. | M/D | Hp/A | 1-Hour |
1-1/2 Hour | 2-Hour | 3-Hour | 4-Hour``. Rows carry the family forward:

* W-shapes: ``W44 x 335`` then ``290``, ``262`` … → W44 x 290, W44 x 262
* angles: ``L 8 x 8 x 1-1/8`` then ``x 1``, ``x 7/8`` … → L8 x 8 x 1, L8 x 8 x 7/8
* tubes (charts with a Wall Thk column): ``30 x 30`` + wall ``5/8`` then ``1/2``, ``3/8`` …

Section markers (``Unrestrained Beam``) switch the restraint condition for the rows that follow.
Every row records page, the family it derives from, W/D or A/P, metric label, M/D, Hp/A, and the
thickness per rating exactly as printed plus parsed inches. Values are manufacturer data
(authority level 6) tied to a design; nothing is interpolated here. Cross-reference pages
("Use Design S721 Table") are recorded as such.
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
_TUBE_FAMILY = re.compile(r"^(?P<a>\d+(?:\.\d+)?)\s*x\s*(?P<b>\d+(?:\.\d+)?)$")
_NUMBER = re.compile(r"^\d+(?:\.\d+)?$")
_FRAC_OR_DEC = re.compile(r"^(?:\d+/\d+|\d*\.\d+|\d+-\d+/\d+|\d+)$")
_X_CONT = re.compile(r"^x\s*(?P<v>\d+(?:-\d+/\d+)?|\d+/\d+|\d*\.\d+)$", re.IGNORECASE)
_THK = re.compile(r"^(?:\d+(?:[- ]+\d+/\d+)?|\d+/\d+|\d*\.\d+|NR|N/R|—|-)[+#*]*$", re.IGNORECASE)
_JOIST = re.compile(r"^\d{1,2}(?:K|LH|DLH|KCS)\d{1,2}$", re.IGNORECASE)
_FAMILY_OPEN = re.compile(
    r"^(?P<fam>W|HP|M|S|C|MC|WT|L|HSS)\s*(?P<depth>\d+(?:\.\d+)?)\s*x\s*$", re.IGNORECASE
)
_SECTION = re.compile(
    r"^(?P<s>(?:Un)?restrained\s+(?:Beam|Column|Assembly)s?|Columns?|Beams?|Joists?)\s*$",
    re.IGNORECASE,
)
_XREF = re.compile(r"Use Design\s+(?P<d>[A-Z]{1,2}-?\d{3,4}[a-z]?)", re.IGNORECASE)


@dataclass
class ChartRow:
    page: int
    section: str | None
    member_label: str
    canonical: str | None
    family_label: str
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
    factor_kind: str | None = None  # "W/D" or "A/P"
    notes: list[str] = field(default_factory=list)
    cross_reference: str | None = None
    cross_reference_designs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _floatish(s: str) -> bool:
    return bool(_NUMBER.fullmatch(s.strip()))


def _page_lines(page) -> list[str]:
    return [ln.strip() for ln in page.get_text("text").split("\n")]


def _family_prefix(label: str) -> str:
    """'W44 x 335' → 'W44'; 'L 8 x 8 x 1-1/8' → 'L8 x 8'; 'HSS 6 x 6 x 1/4' → 'HSS6 x 6'."""
    parts = [p.strip() for p in re.split(r"\s*x\s*", label, flags=re.IGNORECASE)]
    head = re.sub(r"^([A-Za-z]+)\s+", r"\1", parts[0])
    return " x ".join([head] + parts[1:-1])


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
                r"deck|concrete|column|joist|beam|tube|pipe|flange|angle|channel|shape",
                ln,
                re.IGNORECASE,
            )
            and not re.search(r"CAFCO|ISOLATEK|Use Design", ln)
        ]
        rec.condition = " ".join(cond[:3]) or None
        prods = [ln for ln in head if re.search(r"CAFCO|ISOLATEK", ln)]
        rec.products = " ".join(prods) or None
        xref = [ln for ln in first if _XREF.search(ln)]
        if xref:
            rec.cross_reference = " | ".join(xref)
            rec.cross_reference_designs = sorted({_XREF.search(x).group("d").upper() for x in xref})
        tube_prefix = (
            "ST"
            if re.search(r"square", rec.condition or "", re.IGNORECASE)
            else ("RT" if re.search(r"rect", rec.condition or "", re.IGNORECASE) else "TS")
        )
        for pi in range(len(doc)):
            lines = _page_lines(doc[pi])
            hdr_idx = [i for i, ln in enumerate(lines) if _RATING_HDR.match(ln)]
            if not hdr_idx:
                continue
            groups: list[list[int]] = [[hdr_idx[0]]]
            for ix in hdr_idx[1:]:
                if ix - groups[-1][-1] <= 3:
                    groups[-1].append(ix)
                else:
                    groups.append([ix])
            for g_no, group in enumerate(groups):
                block_end = groups[g_no + 1][0] if g_no + 1 < len(groups) else len(lines)
                self_lines = lines[:block_end]
                _parse_block(rec, self_lines, group, pi, tube_prefix)
    finally:
        doc.close()
    return rec


def _parse_block(
    rec: ChartRecord, lines: list[str], hdr_idx: list[int], pi: int, tube_prefix: str
) -> None:
    if True:
        if True:
            cols = [_RATING_HDR.match(lines[i]).group("r") + " Hr" for i in hdr_idx]
            if not rec.rating_columns:
                rec.rating_columns = cols
            n = len(cols)
            pre = lines[max(0, hdr_idx[0] - 14) : hdr_idx[0]]
            has_metric = any(re.search(r"Metric", ln) for ln in pre)
            has_md = any(re.fullmatch(r"M/D", ln) for ln in pre)
            has_hpa = any(re.fullmatch(r"Hp/A", ln, re.IGNORECASE) for ln in pre)
            wd_hdr = next((ln for ln in pre if re.fullmatch(r"(W/D|A/P)", ln, re.IGNORECASE)), None)
            has_wd = wd_hdr is not None
            if wd_hdr and not rec.factor_kind:
                rec.factor_kind = wd_hdr.upper()
            has_wall = any(re.fullmatch(r"Wall\s*Thk\.?", ln, re.IGNORECASE) for ln in pre)
            joist_layout = any(re.fullmatch(r"Joist", ln, re.IGNORECASE) for ln in pre) and any(
                re.search(r"Approx", ln) for ln in pre
            )
            has_desig = any(re.fullmatch(r"(?:ASTM\s*)?Desig\.?(?:\s*Weight)?", ln) for ln in pre)
            wd_indexed = has_wd and not has_desig and not has_wall and not joist_layout
            pipe_layout = has_wall and any(
                re.search(r"Nominal\s*Dia", ln, re.IGNORECASE) for ln in pre
            )
            pipe_prefix = (
                "XSP" if re.search(r"extra strong", " ".join(pre), re.IGNORECASE) else "SP"
            )
            i = hdr_idx[-1] + 1
            section = None
            family: str | None = None
            prefix: str | None = None
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
                j = i + 1
                label = None
                if joist_layout and _JOIST.match(ln):
                    label = ln.upper()
                    family = label
                    # joist charts: Depth (in.) and Approx. Wt columns precede the thicknesses
                    depth_v = float(lines[j]) if j < len(lines) and _floatish(lines[j]) else None
                    j += 1 if depth_v is not None else 0
                    wt_v = float(lines[j]) if j < len(lines) and _floatish(lines[j]) else None
                    j += 1 if wt_v is not None else 0
                    vals = []
                    while j < len(lines) and len(vals) < n and _THK.match(lines[j]):
                        vals.append(lines[j])
                        j += 1
                    if len(vals) < n:
                        rec.notes.append(
                            f"p{pi + 1}: row '{label}' has {len(vals)} of {n} thickness cells"
                        )
                        i = j
                        continue
                    rec.rows.append(
                        ChartRow(
                            pi + 1,
                            section,
                            label,
                            label,
                            label,
                            wt_v,
                            None,
                            depth_v,
                            None,
                            vals,
                            [
                                None
                                if v.upper().startswith("N")
                                else frac_in(v.rstrip("+#*").replace("  ", "-").replace(" ", "-"))
                                for v in vals
                            ],
                            [v.upper().startswith("N") for v in vals],
                        )
                    )
                    i = j
                    continue
                if wd_indexed and _floatish(ln) and j < len(lines):
                    # table keyed by W/D value: W/D | M/D | Hp/A | ratings
                    wd_v = float(ln)
                    md_v = (
                        float(lines[j])
                        if has_md and j < len(lines) and _floatish(lines[j])
                        else None
                    )
                    j += 1 if md_v is not None else 0
                    hpa_v = (
                        float(lines[j])
                        if has_hpa and j < len(lines) and _floatish(lines[j])
                        else None
                    )
                    j += 1 if hpa_v is not None else 0
                    vals = []
                    while j < len(lines) and len(vals) < n and _THK.match(lines[j]):
                        vals.append(lines[j])
                        j += 1
                    if len(vals) < n:
                        i = j if j > i + 1 else i + 1
                        continue
                    rec.rows.append(
                        ChartRow(
                            pi + 1,
                            section,
                            f"W/D {wd_v}",
                            None,
                            f"W/D {wd_v}",
                            wd_v,
                            None,
                            md_v,
                            hpa_v,
                            vals,
                            [
                                None if v.upper().startswith("N") else frac_in(v.rstrip("+#*"))
                                for v in vals
                            ],
                            [v.upper().startswith("N") for v in vals],
                        )
                    )
                    i = j
                    continue
                if (
                    pipe_layout
                    and _floatish(ln)
                    and j < len(lines)
                    and re.fullmatch(r"\d*\.\d+", lines[j])
                ):
                    family = f"{pipe_prefix} {ln}"
                    prefix = family
                    label = f"{prefix} x {lines[j]}"
                    j += 1
                elif has_wall and _TUBE_FAMILY.match(ln):
                    tf = _TUBE_FAMILY.match(ln)
                    family = f"{tube_prefix} {tf.group('a')} x {tf.group('b')}"
                    prefix = family
                    if j < len(lines) and _FRAC_OR_DEC.match(lines[j]) and not _floatish(lines[j]):
                        label = f"{prefix} x {lines[j]}"
                        j += 1
                    else:
                        label = f"{prefix} x ?"
                elif (
                    has_wall
                    and prefix
                    and _FRAC_OR_DEC.match(ln)
                    and not _floatish(ln)
                    and j < len(lines)
                    and _floatish(lines[j])
                ):
                    label = f"{prefix} x {ln}"
                elif _FAMILY_OPEN.match(ln) and j < len(lines) and _NUMBER.match(lines[j]):
                    fo = _FAMILY_OPEN.match(ln)
                    prefix = f"{fo.group('fam').upper()}{fo.group('depth')}"
                    family = f"{prefix} x {lines[j]}"
                    label = family
                    j += 1
                elif _FAMILY.match(ln):
                    family = ln
                    prefix = _family_prefix(ln)
                    label = re.sub(r"^([A-Za-z]+)\s+", r"\1", ln)
                elif _X_CONT.match(ln) and prefix:
                    label = f"{prefix} x {_X_CONT.match(ln).group('v')}"
                elif (
                    _NUMBER.match(ln)
                    and prefix
                    and not has_wall
                    and j < len(lines)
                    and _floatish(lines[j])
                ):
                    label = f"{prefix} x {ln}"
                else:
                    i += 1
                    continue
                wd = md = hpa = None
                metric = None
                if has_wd and j < len(lines) and _floatish(lines[j]):
                    wd = float(lines[j])
                    j += 1
                if has_metric and j < len(lines):
                    cand = lines[j]
                    if re.search(r"x", cand, re.IGNORECASE) or (
                        _NUMBER.match(cand) and float(cand) >= 10
                    ):
                        metric = cand
                        j += 1
                if has_md and j < len(lines) and _floatish(lines[j]):
                    md = float(lines[j])
                    j += 1
                if has_hpa and j < len(lines) and _floatish(lines[j]):
                    hpa = float(lines[j])
                    j += 1
                vals: list[str] = []
                while j < len(lines) and len(vals) < n and _THK.match(lines[j]):
                    vals.append(lines[j])
                    j += 1
                if len(vals) < n:
                    rec.notes.append(
                        f"p{pi + 1}: row '{label}' has {len(vals)} of {n} thickness cells"
                    )
                    i = j
                    continue
                des = (
                    []
                    if has_wall
                    else find_designations(label.replace(" x ", "X").replace(" ", ""))
                )
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
                        [
                            None
                            if v.upper().startswith("N")
                            else frac_in(re.sub(r"\s+", "-", v.rstrip("+#*")))
                            for v in vals
                        ],
                        [v.upper().startswith("N") for v in vals],
                    )
                )
                i = j


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
                "factor",
                "wd_or_ap",
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
                    rec.factor_kind,
                    r.wd,
                    r.hp_a,
                    *r.thickness_as_printed,
                ]
            )
    return out_dir / f"{stem}.json"
