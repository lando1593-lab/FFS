"""Importer for Isolatek "Designs & Thicknesses" chart PDFs (isolatek.com/storage/designs_thickness/…).

Layout (text-extractable, several pages): a header block with the design number, the deck /
concrete / member condition, the products the chart covers and the chart date; then a table with
columns such as ``ASTM Desig. | [Wall Thk] | W/D or A/P | Metric Desig. | M/D | Hp/A | 1-Hour |
1-1/2 Hour | 2-Hour | 3-Hour | 4-Hour``. Rows carry the family forward:

* W-shapes: ``W44 x 335`` then ``290``, ``262`` … → W44 x 290, W44 x 262; the metric designation
  alongside carries the same way: ``W1120 x 498`` then ``432`` → W1120 x 432
  (``metric_member_label``; ``metric_label`` keeps the cell as printed)
* angles: ``L 8 x 8 x 1-1/8`` then ``x 1``, ``x 7/8`` … → L8 x 8 x 1, L8 x 8 x 7/8
* tubes (charts with a Wall Thk column): ``30 x 30`` + wall ``5/8`` then ``1/2``, ``3/8`` …
* pipes (Nominal Dia + Wall Thk): ``3`` + wall ``0.216`` or ``20.00`` + wall ``1/2``, then
  wall-only rows ``3/8`` …
* joists: ``8K1 | 8 | 4.9`` (designation, depth in., approx. weight lbs/ft) then the thicknesses

Layout variants handled: several rating headers printed in one text span (``1-Hour+ 1-1/2 Hour+
2-Hour+``) or one header split over two lines (``2-1/2-`` / ``Hour``); footnote markers on a
rating header (``3-Hour+``, ``3-Hour++``), stripped from the column name, kept in
``rating_column_markers`` and tied to the marker's text line (``+Reduced thicknesses are available
when …``) in ``footnotes``; the Albi DriClad ``AISC Desig. | W/D | Metric Desig. | M/D | Hp/A``
charts whose continuation pages repeat the title but not the column header (the last header's
layout carries forward); a second table with its own rating columns (N759: ``2-1/2 Hour 3-1/2
Hour``), whose rows carry ``rating_columns`` of their own; product and date lines printed under
the table instead of above it. Footnote text is recorded exactly as printed, even when the source
page clips it.

A numeric cell of 10 in. or more is never read as a thickness: when a row's text layer lacks
cells, the next row's weight or section factor would otherwise be stored as a thickness. Such a
row is skipped with a note (``p6: row 'W10 x 30' has 1 of 3 thickness cells``), never padded.

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
# footnote markers that may trail a rating header ("3-Hour+", "3-Hour++") or open a note line
_MARKERS = re.escape("+#*†‡")
_RATING_TOK = re.compile(rf"(?P<r>\d(?:-\d/\d)?)\s*-?\s*Hour(?P<fn>[{_MARKERS}]*)", re.IGNORECASE)
# one or more rating headers in a single text span: "1-Hour", "3-Hour+", "1-Hour+ 1-1/2 Hour+ 2-Hour+"
_RATING_HDR = re.compile(rf"^(?:\d(?:-\d/\d)?\s*-?\s*Hour[{_MARKERS}]*\s*)+$", re.IGNORECASE)
# a rating header broken over two lines: "2-1/2-" then "Hour"
_RATING_SPLIT_A = re.compile(r"^\d(?:-\d/\d)?\s*-?$")
_RATING_SPLIT_B = re.compile(rf"^Hour[{_MARKERS}]*$", re.IGNORECASE)
# two thickness cells fused into one text span ("2     2-11/16", "NR  NR"); a joist mixed number
# ("1  3/16", whole + bare fraction) is one cell and is left alone
_CELL_TOK = rf"(?:\d+(?:-\d+/\d+)?|\d*\.\d+|NR)[{_MARKERS}]*"
_FUSED_CELLS = re.compile(rf"^(?P<a>{_CELL_TOK})\s+(?P<b>{_CELL_TOK})$", re.IGNORECASE)
_FOOTNOTE = re.compile(rf"^(?P<m>[{_MARKERS}]+)\s*(?=\S)")
_PRODUCT = re.compile(r"CAFCO|ISOLATEK|Albi\s*DriClad")
_PRODUCT_LINE = re.compile(r"^(?:CAFCO|ISOLATEK|Albi\s*DriClad)")
_CONDITION_KW = re.compile(
    r"deck|concrete|column|joist|beam|tube|pipe|flange|angle|channel|shape", re.IGNORECASE
)
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
    # metric designation with the family carried down ("W1120 x 498" then "432" → "W1120 x 432");
    # None when the chart has no metric column or the row's family printed no full metric label
    metric_member_label: str | None = None
    # joist charts only: Depth (in.) and Approx. Wt (lbs./ft.) as printed. (Joist rows also keep
    # the earlier convention of depth in ``md`` and weight in ``wd``.)
    depth_in: float | None = None
    approx_wt: float | None = None
    # set only when the row comes from a table whose rating columns differ from the record's
    # ``rating_columns`` (N759's 2-1/2 / 3-1/2 hour supplement); None means the record's columns
    rating_columns: list[str] | None = None


@dataclass
class ChartFootnote:
    marker: str  # "+", "++", "*", …
    text: str  # the note line as printed, marker included (may be clipped by the source page)
    columns: list[str]  # rating columns whose header carries this marker ([] for cell-level marks)
    page: int  # first page the note was read from


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
    notes: list[str] = field(default_factory=list)  # parser diagnostics, not chart text
    cross_reference: str | None = None
    cross_reference_designs: list[str] = field(default_factory=list)
    # footnote marker per rating column ("" when the header carries none), parallel to rating_columns
    rating_column_markers: list[str] = field(default_factory=list)
    footnotes: list[ChartFootnote] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class _Layout:
    """Column layout read from one rating-header group; reused by header-less continuation pages."""

    cols: list[str]
    markers: list[str]
    wd_hdr: str | None
    has_metric: bool
    has_md: bool
    has_hpa: bool
    has_wall: bool
    joist_layout: bool
    wd_indexed: bool
    pipe_layout: bool
    pipe_prefix: str

    @property
    def has_wd(self) -> bool:
        return self.wd_hdr is not None


def _floatish(s: str) -> bool:
    return bool(_NUMBER.fullmatch(s.strip()))


def _is_thk(s: str) -> bool:
    """A thickness cell: fraction / decimal / NR / dash, optionally marked. A numeric cell of
    10 in. or more is never a thickness; it is the next row's weight or section factor leaking
    into a row whose text layer lacks some cells, and accepting it would fabricate a row."""
    if not _THK.match(s):
        return False
    v = frac_in(re.sub(r"\s+", "-", s.rstrip("+#*")))
    return v is None or v < 10


def _page_lines(page) -> list[str]:
    return [ln.strip() for ln in page.get_text("text").split("\n")]


def _normalize_lines(lines: list[str]) -> list[str]:
    """Repair two text-layer artefacts: a rating header broken over two lines ("2-1/2-" /
    "Hour") is merged into the first line (the second becomes empty), and two thickness cells
    fused into one span ("2     2-11/16") are split into two lines."""
    out: list[str] = []
    skip = False
    for i, ln in enumerate(lines):
        if skip:
            out.append("")
            skip = False
            continue
        if i + 1 < len(lines) and _RATING_SPLIT_A.match(ln) and _RATING_SPLIT_B.match(lines[i + 1]):
            out.append(f"{ln} {lines[i + 1]}")
            skip = True
            continue
        fm = _FUSED_CELLS.match(ln)
        if fm:
            out.extend([fm.group("a"), fm.group("b")])
            continue
        out.append(ln)
    return out


def _family_prefix(label: str) -> str:
    """'W44 x 335' → 'W44'; 'L 8 x 8 x 1-1/8' → 'L8 x 8'; 'HSS 6 x 6 x 1/4' → 'HSS6 x 6'."""
    parts = [p.strip() for p in re.split(r"\s*x\s*", label, flags=re.IGNORECASE)]
    head = re.sub(r"^([A-Za-z]+)\s+", r"\1", parts[0])
    return " x ".join([head] + parts[1:-1])


def _rating_tokens(ln: str) -> list[tuple[str, str]]:
    """'1-Hour+ 1-1/2 Hour+ 2-Hour+' → [('1 Hr', '+'), ('1-1/2 Hr', '+'), ('2 Hr', '+')];
    [] when the line is not a rating header."""
    if not _RATING_HDR.match(ln):
        return []
    return [(m.group("r") + " Hr", m.group("fn")) for m in _RATING_TOK.finditer(ln)]


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
        if dm is None:
            # some layouts print "Page 1 | 10/7/2013" as a page footer instead
            dm = _DATE.search(" ".join([ln for ln in first if ln][-6:]))
        rec.chart_date = dm.group(1) if dm else None
        cond = [
            ln
            for ln in head
            if (
                _CONDITION_KW.search(ln)
                # "Restrained and Unrestrained" on its own line is a condition; a design line
                # such as "N873 - UNRESTRAINED" stays a title line
                or (re.search(r"restrained", ln, re.IGNORECASE) and not _DESIGN_LINE.match(ln))
            )
            and not _PRODUCT.search(ln)
            and not re.search(r"Use Design", ln)
        ]
        rec.condition = " ".join(cond[:3]) or None
        prods = [ln for ln in head if _PRODUCT.search(ln)]
        if not prods:
            # product line printed under the table (joist charts) or as a bare brand line
            # ("Albi DriClad") that the text stream emits after the rows; a note that merely
            # mentions a product ("Note: 2 in. CAFCO-BOARD shall …") is not a product line
            prods = list(
                dict.fromkeys(
                    ln for ln in first if _PRODUCT_LINE.match(ln) and not _XREF.search(ln)
                )
            )
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
        layout: _Layout | None = None
        for pi in range(len(doc)):
            lines = _normalize_lines(_page_lines(doc[pi]))
            hdr_idx = [i for i, ln in enumerate(lines) if _RATING_HDR.match(ln)]
            if not hdr_idx:
                if layout is not None:
                    # continuation page that repeats the title but not the column header
                    _parse_block(rec, lines, [], pi, tube_prefix, layout)
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
                layout = _parse_block(rec, self_lines, group, pi, tube_prefix)
    finally:
        doc.close()
    return rec


def _layout_from_header(lines: list[str], hdr_idx: list[int]) -> _Layout:
    toks = [t for i in hdr_idx for t in _rating_tokens(lines[i])]
    pre = lines[max(0, hdr_idx[0] - 14) : hdr_idx[0]]
    wd_hdr = next((ln for ln in pre if re.fullmatch(r"(W/D|A/P)", ln, re.IGNORECASE)), None)
    has_wall = any(re.fullmatch(r"Wall\s*Thk\.?", ln, re.IGNORECASE) for ln in pre)
    joist_layout = any(re.fullmatch(r"Joist", ln, re.IGNORECASE) for ln in pre) and any(
        re.search(r"Approx", ln) for ln in pre
    )
    has_desig = any(re.fullmatch(r"(?:(?:ASTM|AISC)\s*)?Desig\.?(?:\s*Weight)?", ln) for ln in pre)
    return _Layout(
        cols=[c for c, _ in toks],
        markers=[m for _, m in toks],
        wd_hdr=wd_hdr,
        has_metric=any(re.search(r"Metric", ln) for ln in pre),
        has_md=any(re.fullmatch(r"M/D", ln) for ln in pre),
        has_hpa=any(re.fullmatch(r"Hp/A", ln, re.IGNORECASE) for ln in pre),
        has_wall=has_wall,
        joist_layout=joist_layout,
        wd_indexed=wd_hdr is not None and not has_desig and not has_wall and not joist_layout,
        pipe_layout=has_wall and any(re.search(r"Nominal\s*Dia", ln, re.IGNORECASE) for ln in pre),
        pipe_prefix="XSP" if re.search(r"extra strong", " ".join(pre), re.IGNORECASE) else "SP",
    )


def _add_footnote(rec: ChartRecord, layout: _Layout, marker: str, text: str, page: int) -> None:
    if any(f.marker == marker and f.text == text for f in rec.footnotes):
        return
    cols = [c for c, m in zip(layout.cols, layout.markers, strict=True) if m == marker]
    rec.footnotes.append(ChartFootnote(marker, text, cols, page))


def _metric_under_ten_follows_layout(lines: list[str], j: int, layout: _Layout) -> bool:
    """A bare metric weight/wall under 10 ("9", "9.3") is only taken as the metric cell when the
    M/D and Hp/A cells and then a thickness cell follow it in their printed order."""
    if not (layout.has_md or layout.has_hpa):
        return False
    k = j + 1
    for present in (layout.has_md, layout.has_hpa):
        if present:
            if k >= len(lines) or not _floatish(lines[k]):
                return False
            k += 1
    return k < len(lines) and _is_thk(lines[k])


def _parse_block(
    rec: ChartRecord,
    lines: list[str],
    hdr_idx: list[int],
    pi: int,
    tube_prefix: str,
    layout: _Layout | None = None,
) -> _Layout:
    """Parse the rows under one rating-header group (``hdr_idx``). With an empty ``hdr_idx`` the
    page carries no column header and ``layout`` (from the previous header) is applied from the
    top of the page. Returns the layout in force."""
    if layout is None:
        layout = _layout_from_header(lines, hdr_idx)
    if not rec.rating_columns:
        rec.rating_columns = list(layout.cols)
        rec.rating_column_markers = list(layout.markers)
    if layout.wd_hdr and not rec.factor_kind:
        rec.factor_kind = layout.wd_hdr.upper()
    n = len(layout.cols)
    row_cols = None if layout.cols == rec.rating_columns else list(layout.cols)
    has_wd, has_metric, has_md, has_hpa, has_wall = (
        layout.has_wd,
        layout.has_metric,
        layout.has_md,
        layout.has_hpa,
        layout.has_wall,
    )
    i = hdr_idx[-1] + 1 if hdr_idx else 0
    section = None
    family: str | None = None
    prefix: str | None = None
    metric_prefix: str | None = None
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
        fm = _FOOTNOTE.match(ln)
        if fm and re.search(r"[A-Za-z]", ln) and not _THK.match(ln):
            _add_footnote(rec, layout, fm.group("m"), ln, pi + 1)
            i += 1
            continue
        j = i + 1
        label = None
        if layout.joist_layout and _JOIST.match(ln):
            label = ln.upper()
            family = label
            # joist charts: Depth (in.) and Approx. Wt columns precede the thicknesses
            depth_v = float(lines[j]) if j < len(lines) and _floatish(lines[j]) else None
            j += 1 if depth_v is not None else 0
            wt_v = float(lines[j]) if j < len(lines) and _floatish(lines[j]) else None
            j += 1 if wt_v is not None else 0
            vals = []
            while j < len(lines) and len(vals) < n and _is_thk(lines[j]):
                vals.append(lines[j])
                j += 1
            if len(vals) < n:
                rec.notes.append(f"p{pi + 1}: row '{label}' has {len(vals)} of {n} thickness cells")
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
                    depth_in=depth_v,
                    approx_wt=wt_v,
                    rating_columns=row_cols,
                )
            )
            i = j
            continue
        if layout.wd_indexed and _floatish(ln) and j < len(lines):
            # table keyed by W/D value: W/D | M/D | Hp/A | ratings
            wd_v = float(ln)
            md_v = float(lines[j]) if has_md and j < len(lines) and _floatish(lines[j]) else None
            j += 1 if md_v is not None else 0
            hpa_v = float(lines[j]) if has_hpa and j < len(lines) and _floatish(lines[j]) else None
            j += 1 if hpa_v is not None else 0
            vals = []
            while j < len(lines) and len(vals) < n and _is_thk(lines[j]):
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
                    [None if v.upper().startswith("N") else frac_in(v.rstrip("+#*")) for v in vals],
                    [v.upper().startswith("N") for v in vals],
                    rating_columns=row_cols,
                )
            )
            i = j
            continue
        new_family = False
        if (
            layout.pipe_layout
            and _floatish(ln)
            and j < len(lines)
            and (
                re.fullmatch(r"\d*\.\d+", lines[j])
                or (_FRAC_OR_DEC.match(lines[j]) and not _floatish(lines[j]))
            )
        ):
            # pipe family row: nominal diameter then the wall ("3" + "0.216", "20.00" + "1/2")
            family = f"{layout.pipe_prefix} {ln}"
            prefix = family
            label = f"{prefix} x {lines[j]}"
            j += 1
            new_family = True
        elif has_wall and _TUBE_FAMILY.match(ln):
            tf = _TUBE_FAMILY.match(ln)
            family = f"{tube_prefix} {tf.group('a')} x {tf.group('b')}"
            prefix = family
            if j < len(lines) and _FRAC_OR_DEC.match(lines[j]) and not _floatish(lines[j]):
                label = f"{prefix} x {lines[j]}"
                j += 1
            else:
                label = f"{prefix} x ?"
            new_family = True
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
            new_family = True
        elif _FAMILY.match(ln):
            family = ln
            prefix = _family_prefix(ln)
            label = re.sub(r"^([A-Za-z]+)\s+", r"\1", ln)
            new_family = True
        elif _X_CONT.match(ln) and prefix:
            label = f"{prefix} x {_X_CONT.match(ln).group('v')}"
        elif (
            _NUMBER.match(ln) and prefix and not has_wall and j < len(lines) and _floatish(lines[j])
        ):
            label = f"{prefix} x {ln}"
        else:
            i += 1
            continue
        if new_family:
            # the metric family is re-read from this row; a weight-only metric cell with no
            # preceding full metric label stays uncarried rather than guessed
            metric_prefix = None
        wd = md = hpa = None
        metric = None
        metric_full = None
        if has_wd and j < len(lines) and _floatish(lines[j]):
            wd = float(lines[j])
            j += 1
        if has_metric and j < len(lines):
            cand = lines[j]
            take = bool(re.search(r"x", cand, re.IGNORECASE)) or (
                _NUMBER.match(cand) is not None and float(cand) >= 10
            )
            if not take and _NUMBER.match(cand):
                take = _metric_under_ten_follows_layout(lines, j, layout)
            if take:
                metric = cand
                j += 1
                xc = _X_CONT.match(cand)
                if xc:
                    metric_full = f"{metric_prefix} x {xc.group('v')}" if metric_prefix else None
                elif _NUMBER.match(cand):
                    metric_full = f"{metric_prefix} x {cand}" if metric_prefix else None
                else:
                    metric_prefix = _family_prefix(cand)
                    metric_full = re.sub(r"^([A-Za-z]+)\s+", r"\1", cand)
        if has_md and j < len(lines) and _floatish(lines[j]):
            md = float(lines[j])
            j += 1
        if has_hpa and j < len(lines) and _floatish(lines[j]):
            hpa = float(lines[j])
            j += 1
        vals: list[str] = []
        while j < len(lines) and len(vals) < n and _is_thk(lines[j]):
            vals.append(lines[j])
            j += 1
        if len(vals) < n:
            rec.notes.append(f"p{pi + 1}: row '{label}' has {len(vals)} of {n} thickness cells")
            i = j
            continue
        des = [] if has_wall else find_designations(label.replace(" x ", "X").replace(" ", ""))
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
                metric_member_label=metric_full,
                rating_columns=row_cols,
            )
        )
        i = j
    return layout


def write_chart(rec: ChartRecord, out_dir: str | Path) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(rec.source_file).stem
    (out_dir / f"{stem}.json").write_text(json.dumps(rec.to_dict(), indent=1, ensure_ascii=False))
    # rows from a table with its own rating columns are written under those column names
    extra = [c for r in rec.rows if r.rating_columns for c in r.rating_columns]
    cols = rec.rating_columns + [c for c in dict.fromkeys(extra) if c not in rec.rating_columns]
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
                *cols,
            ]
        )
        for r in rec.rows:
            if r.rating_columns is None:
                cells = list(r.thickness_as_printed)
                cells += [""] * (len(cols) - len(cells))
            else:
                by_name = dict(zip(r.rating_columns, r.thickness_as_printed, strict=False))
                cells = [by_name.get(c, "") for c in cols]
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
                    *cells,
                ]
            )
    return out_dir / f"{stem}.json"
