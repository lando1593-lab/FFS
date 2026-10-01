"""Parser for GCP (MONOKOTE) per-design thickness charts ("BXUV.D739" … 6 pages each).

Layout (verified on D739, 3/15/2021): a header block (design, assembly description, restraint,
concrete fill, the GCP product types the chart covers), then a table whose rating columns are
printed in one or two groups ("NORMAL WEIGHT CONCRETE FILL" | "LIGHTWEIGHT CONCRETE FILL") with
the member columns ("Size x Wt." and "W/D") between the groups. Pages 2–6 repeat the header.
The text layer carries no row structure, so cells are assigned to columns by x position against
the printed header row. Cells are stored as printed; "NR" is a marker, never a number; a blank
cell stays blank and is noted. Nothing is inferred from neighbouring rows.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ffs.importers.ul_design import frac_in
from ffs.steel.designation import find_designations

_RATING_HDR = re.compile(r"^(\d+(?:\.\d+)?)\s*-?\s*(?:hrs?|hours?)\.?$", re.IGNORECASE)
_DESIGN = re.compile(r"BXUV\.([A-Z]{1,2}\d{3,4}[A-Z]?)")
_DATE = re.compile(r"\b\d{1,2}/\d{1,2}/\d{4}\b")
_PAGE = re.compile(r"Page\s+(\d+)\s+of\s+(\d+)", re.IGNORECASE)
_PRODUCT_LINE = re.compile(r"GCP\s+APPLIED\s+TECHNOLOGIES", re.IGNORECASE)
_VALUE_COL = re.compile(r"^(W/D|A/P|M/D|Hp/A|Wall|Thk\.?)$", re.IGNORECASE)
_THK = re.compile(r"^(?:\d+(?:\s+\d+/\d+)?|\d+/\d+|NR|NA|N/A|—|-)$", re.IGNORECASE)
_ROW_TOL = 3.0  # pt: spans within this vertical distance are one row
_COL_TOL = 24.0  # pt: a cell belongs to the nearest column centre within this distance


@dataclass
class GcpChartGroup:
    title: str | None
    rating_columns: list[str]


@dataclass
class GcpChartRow:
    page: int
    group: str | None
    member_label: str
    canonical: str | None
    # "printed" when the canonical designation comes from the printed label (W4 x 13), "derived"
    # when it is composed from a printed nominal tube size and wall ("4 x 3" + "1/4" → HSS4X3X1/4);
    # None when there is no canonical designation
    canonical_source: str | None
    member_values: dict[str, str]
    wd: float | None  # the printed section-factor value (see ratio_name), None when not numeric
    ratio_name: str | None
    thickness_as_printed: list[str]
    thickness_in: list[float | None]
    not_rated: list[bool]


@dataclass
class GcpChartRecord:
    source_file: str
    design: str | None
    header_lines: list[str]
    assembly: str | None
    restraint: str | None
    concrete: str | None
    products: str | None
    chart_date: str | None
    pages: int
    groups: list[GcpChartGroup]
    member_columns: list[str]
    rows: list[GcpChartRow] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class _Span:
    y: float
    x0: float
    x1: float
    text: str

    @property
    def xc(self) -> float:
        return (self.x0 + self.x1) / 2


@dataclass
class _Col:
    name: str
    xc: float
    kind: str  # "thk" / "label" / "value"
    group: int  # group index for thk columns, -1 otherwise


def _spans(page) -> list[_Span]:
    out: list[_Span] = []
    for b in page.get_text("dict")["blocks"]:
        for ln in b.get("lines", []):
            for sp in ln["spans"]:
                t = sp["text"].replace("\xa0", " ").strip()
                if not t:
                    continue
                x0, y0, x1, y1 = sp["bbox"]
                yc = (y0 + y1) / 2
                parts = re.split(r"\s{2,}", t)
                if len(parts) != 2 or not re.match(r"^\d+(?:\.\d+)?$", parts[1]):
                    out.append(_Span(yc, x0, x1, t))
                    continue
                # two cells printed in one span ("Other   0.370"): place each part by its share
                # of the span width, in printed order
                width = x1 - x0
                total = sum(len(pt) for pt in parts) + 2 * (len(parts) - 1)
                cur = x0
                for pt in parts:
                    w = width * len(pt) / total
                    out.append(_Span(yc, cur, cur + w, pt))
                    cur += w + width * 2 / total
    out.sort(key=lambda s: (s.y, s.x0))
    return out


def _rows(spans: list[_Span]) -> list[list[_Span]]:
    rows: list[list[_Span]] = []
    for s in spans:
        if rows and abs(rows[-1][-1].y - s.y) <= _ROW_TOL:
            rows[-1].append(s)
        else:
            rows.append([s])
    for r in rows:
        r.sort(key=lambda s: s.x0)
    return rows


def _row_text(r: list[_Span]) -> str:
    """Join a row's spans; a wide gap (two cells on one line) becomes a double space."""
    out = ""
    for i, s in enumerate(r):
        if i:
            out += "  " if s.x0 - r[i - 1].x1 > 20 else " "
        out += s.text
    return out


def _header_row(rows: list[list[_Span]]) -> int | None:
    for i, r in enumerate(rows):
        if sum(1 for s in r if _RATING_HDR.match(s.text)) >= 2:
            return i
    return None


_LABEL_COL = re.compile(r"Size|Wt\.?|Diameter|Dia\.?|^x$", re.IGNORECASE)
_BAND = 14.0  # pt: header words within this distance of the rating-header row belong to it


def _columns(rows: list[list[_Span]], hi: int) -> tuple[list[_Col], list[GcpChartGroup], float]:
    """Columns from the header band around the rating-header row ``hi``.

    Returns (columns, groups, y of the last header-band row). Member column names may be stacked
    over two lines ("Wall" / "Thickness") or printed under the rating row ("Size x Wt. | W/D");
    stacked words are merged by x overlap.
    """
    hdr = rows[hi]
    hy = hdr[0].y
    thk = [s for s in hdr if _RATING_HDR.match(s.text)]

    def over_thk(s: _Span) -> bool:
        return any(s.x0 - 2 <= t.xc <= s.x1 + 2 for t in thk)

    def is_data_row(r: list[_Span]) -> bool:
        return any(re.match(r"^\d", s.text) for s in r)

    # header band: the rating row, the rows just above it that are not group titles (titles sit
    # over the thickness columns), and the rows below it up to the first data row (member column
    # names may be stacked over three lines: "Nominal" / "Pipe" / "Diameter")
    band_rows = [rows[hi]]
    for r in reversed(rows[:hi]):
        if hy - r[0].y > _BAND or any(over_thk(s) for s in r):
            break
        band_rows.insert(0, r)
    for r in rows[hi + 1 :]:
        if is_data_row(r) or r[0].y - hy > 60:
            break
        band_rows.append(r)
    band = [s for r in band_rows for s in r]
    # column groups: a "Member" word between the rating headers separates two groups (NWC | LWC,
    # full | half flange tip); otherwise a restart of the hour sequence ("… 4 hr | 1 hr …") does
    member = [s for s in band if s.text.lower() == "member"]
    groups: list[list[_Span]] = []
    if member:
        mx = member[0].xc
        left = [s for s in thk if s.xc < mx]
        right = [s for s in thk if s.xc > mx]
        groups = [g for g in (left, right) if g]
    else:
        last = -1.0
        for s in thk:
            hours = float(_RATING_HDR.match(s.text).group(1))
            if not groups or hours <= last:
                groups.append([])
            groups[-1].append(s)
            last = hours
    cols: list[_Col] = []
    for gi, g in enumerate(groups):
        for s in g:
            cols.append(_Col(s.text, s.xc, "thk", gi))
    words = [s for s in band if not _RATING_HDR.match(s.text) and s.text.lower() != "member"]
    words.sort(key=lambda s: (s.x0, s.y))
    merged: list[list[_Span]] = []
    for w in words:
        for m in merged:
            if min(m[-1].x1, w.x1) - max(m[0].x0, w.x0) > 2:  # x overlap: stacked words
                m.append(w)
                break
        else:
            merged.append([w])
    for m in merged:
        m.sort(key=lambda s: s.y)
        name = " ".join(s.text for s in m)
        xc = sum(s.xc for s in m) / len(m)
        kind = "label" if _LABEL_COL.search(name) and not _VALUE_COL.match(name) else "value"
        cols.append(_Col(name, xc, kind, -1))
    # group titles: uppercase words (no digits) in the last row above the band, sitting over a
    # group's columns ("NORMAL WEIGHT CONCRETE FILL", "FULL FLANGE TIP THICKNESS (in.)"); product
    # lines and their wrapped continuations carry digits or lowercase and are never titles
    titles: list[str | None] = [None] * len(groups)
    above = [r for r in rows[:hi] if r not in band_rows]
    if above and hy - above[-1][0].y <= _BAND + 24:
        for s in above[-1]:
            if not _is_title(s.text):
                continue
            for gi, g in enumerate(groups):
                lo = min(x.xc for x in g) - 40
                hi_x = max(x.xc for x in g) + 40
                if lo <= s.xc <= hi_x and titles[gi] is None:
                    titles[gi] = s.text
    last_y = max(r[0].y for r in band_rows)
    return (
        cols,
        [GcpChartGroup(titles[i], [s.text for s in g]) for i, g in enumerate(groups)],
        last_y,
    )


def _is_title(text: str) -> bool:
    core = re.sub(r"\(.*?\)", "", text).strip()
    return bool(core) and core == core.upper() and not re.search(r"\d", core)


def _nearest(cols: list[_Col], s: _Span) -> _Col | None:
    best = min(cols, key=lambda c: abs(c.xc - s.xc))
    return best if abs(best.xc - s.xc) <= _COL_TOL else None


def parse_gcp_chart_pdf(path: str | Path) -> GcpChartRecord:
    import pymupdf

    path = Path(path)
    doc = pymupdf.open(str(path))
    rec = GcpChartRecord(path.name, None, [], None, None, None, None, None, len(doc), [], [])
    cols: list[_Col] = []
    for pi, page in enumerate(doc):
        rows = _rows(_spans(page))
        hi = _header_row(rows)
        if hi is None:
            if not cols or not rows:
                rec.notes.append(f"p{pi + 1}: no rating header row")
                continue
            # a continuation page printed without the header: the previous page's columns apply
            band_end = 0.0
            hi = -1
        else:
            prev_member = [c for c in cols if c.kind != "thk"]
            cols, groups, band_end = _columns(rows, hi)
            if prev_member and not any(c.kind != "thk" for c in cols):
                # a later page repeats the rating header but not the member column names: the
                # same template, so page 1's member columns apply
                cols.extend(prev_member)
        if hi >= 0 and (pi == 0 or not rec.groups):
            rec.groups = groups
            rec.member_columns = [c.name for c in cols if c.kind != "thk"]
            for r in rows[:hi]:
                if abs(r[0].y - rows[hi][0].y) <= _BAND and r[0].y >= rows[hi][0].y - _BAND:
                    if not any(len(s.text) > 3 for s in r) or r[0].y >= rows[hi][0].y:
                        continue
                titles = {g.title for g in groups if g.title}
                if titles and all(s.text in titles for s in r):
                    continue
                rec.header_lines.append(_row_text(r))
            _read_header(rec)
        elif hi >= 0 and [g.rating_columns for g in groups] != [
            g.rating_columns for g in rec.groups
        ]:
            rec.notes.append(f"p{pi + 1}: rating columns differ from page 1; page skipped")
            continue
        thk_cols = [c for c in cols if c.kind == "thk"]
        value_cols = [c for c in cols if c.kind == "value"]
        for r in rows:
            if r[0].y <= band_end + 2:
                continue
            text = " ".join(s.text for s in r)
            if any(len(s.text) > 30 for s in r):
                continue  # prose (disclaimer paragraphs), never table cells
            for s in r:
                dm = _DATE.search(s.text)
                if dm and (len(s.text) <= 12 or s.text.lower().startswith("revised")):
                    rec.chart_date = rec.chart_date or dm.group(0)
            if _PAGE.search(text):
                break
            if _PRODUCT_LINE.search(text) or "Disclaimer" in text:
                continue
            cells: dict[int, _Span] = {}
            label_parts: list[str] = []
            values: dict[str, str] = {}
            stray: list[str] = []
            for s in r:
                c = _nearest(cols, s)
                if c is None:
                    stray.append(s.text)
                elif c.kind == "thk":
                    cells[cols.index(c)] = s
                elif c.kind == "label":
                    label_parts.append(s.text)
                else:
                    values[c.name] = (values[c.name] + " " + s.text) if c.name in values else s.text
            label = " ".join(label_parts).strip()
            if not label:
                # generic rows print "Other" in a value column (D739 p4 "Other 0.370",
                # X794 pipes "Other" under Wall Thickness) or where a later page prints no
                # label column at all: the printed word is the row's identity
                words = [v for v in list(values.values()) + stray if not re.match(r"^[\d./ ]+$", v)]
                label = " ".join(words)
                stray = [v for v in stray if v not in words]
            if not label and not cells:
                continue
            if not label:
                rec.notes.append(f"p{pi + 1}: thickness cells without a member label: {text[:60]}")
                continue
            if stray:
                rec.notes.append(f"p{pi + 1}: '{label}': unassigned cells {stray}")
            ratio_col = next(
                (c for c in value_cols if re.match(r"^(W/D|A/P|M/D|Hp/A)$", c.name, re.IGNORECASE)),
                None,
            )
            wd = None
            if ratio_col and ratio_col.name in values:
                try:
                    wd = float(values[ratio_col.name])
                except ValueError:
                    wd = None
            des = find_designations(label.replace(" x ", "X").replace(" ", ""))
            canonical, canonical_source = (
                (des[0].canonical, "printed") if len(des) == 1 else (None, None)
            )
            if canonical is None:
                derived = _tube_canonical(label, values)
                if derived:
                    canonical, canonical_source = derived, "derived"
            for gi, g in enumerate(rec.groups):
                gcols = [c for c in thk_cols if c.group == gi]
                printed = [
                    cells[cols.index(c)].text if cols.index(c) in cells else "" for c in gcols
                ]
                if not any(printed):
                    continue
                if "" in printed:
                    rec.notes.append(
                        f"p{pi + 1}: '{label}' {g.title or ''}: blank cell(s) {printed}"
                    )
                bad = [v for v in printed if v and not _THK.match(v)]
                if bad:
                    rec.notes.append(
                        f"p{pi + 1}: '{label}': not thickness cells {bad}; row skipped"
                    )
                    continue
                inches = [
                    None
                    if (not v or v.upper().startswith("N") or v in ("—", "-"))
                    else frac_in(re.sub(r"\s+", "-", v))
                    for v in printed
                ]
                if any(x is not None and x > 5 for x in inches):
                    # a cell over 5 in. is a mis-assigned section factor, not a thickness; the
                    # row is noted and never stored (storing it would manufacture a value)
                    rec.notes.append(
                        f"p{pi + 1}: '{label}' {g.title or ''}: implausible cell {printed}; "
                        "row skipped"
                    )
                    continue
                rec.rows.append(
                    GcpChartRow(
                        pi + 1,
                        g.title,
                        label,
                        canonical,
                        canonical_source,
                        dict(values),
                        wd,
                        ratio_col.name if ratio_col else None,
                        printed,
                        inches,
                        [bool(v) and v.upper().startswith("N") for v in printed],
                    )
                )
    doc.close()
    return rec


_TUBE_SIZE = re.compile(r"^(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)$", re.IGNORECASE)
_WALL = re.compile(r"^\d+/\d+$|^\d*\.\d+$")


def _tube_canonical(label: str, values: dict[str, str]) -> str | None:
    """HSS designation composed from a printed rectangular/square nominal size and wall.

    Only when both are printed as the chart's own cells: a "4 x 3" size under a size column and
    a fractional or decimal wall under a wall column. Pipes (one diameter) and "Other" rows get
    nothing. The result goes through the designation module so the spelling matches member
    records; the row records that it is derived, not printed.
    """
    m = _TUBE_SIZE.match(label.strip())
    wall = next((v for k, v in values.items() if re.search(r"wall", k, re.IGNORECASE)), None)
    if not m or not wall or not _WALL.match(wall.strip()):
        return None
    des = find_designations(f"HSS{m.group(1)}X{m.group(2)}X{wall.strip()}")
    return des[0].canonical if len(des) == 1 else None


def _read_header(rec: GcpChartRecord) -> None:
    lines = rec.header_lines
    for ln in lines:
        m = _DESIGN.search(ln) or re.match(r"^([A-Z]{1,2}\d{3,4}[A-Z]?)$", ln)
        if m:
            rec.design = m.group(1)
            break
    body = [ln for ln in lines if ln != rec.design and not _DESIGN.search(ln)]
    prod: list[str] = []
    for ln in body:
        if _PRODUCT_LINE.search(ln) or prod:
            # the product line and every header line wrapped after it (titles are not here)
            prod.append(ln)
            continue
        if re.search(r"\b(Unrestrained|Restrained)\b", ln) and rec.restraint is None:
            parts = re.split(r"\s{2,}", ln)
            rec.restraint = parts[0]
            if len(parts) > 1:
                rec.concrete = " ".join(parts[1:])
            continue
        if rec.assembly is None:
            rec.assembly = ln
            continue
        if rec.concrete is None and "Concrete" in ln:
            rec.concrete = ln
    if prod:
        rec.products = " ".join(prod)


def write_gcp_chart(rec: GcpChartRecord, out_dir: str | Path) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(rec.source_file).stem
    js = out_dir / f"{stem}.json"
    js.write_text(json.dumps(asdict(rec), indent=1), encoding="utf-8")
    cols = sorted({k for r in rec.rows for k in r.member_values})
    ratings = rec.groups[0].rating_columns if rec.groups else []
    with (out_dir / f"{stem}.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            ["design", "page", "group", "member_label", "canonical", "canonical_source", *cols]
            + [f"{c} as printed" for c in ratings]
            + [f"{c} in" for c in ratings]
        )
        for r in rec.rows:
            w.writerow(
                [rec.design, r.page, r.group, r.member_label, r.canonical, r.canonical_source]
                + [r.member_values.get(c, "") for c in cols]
                + r.thickness_as_printed
                + ["" if v is None else v for v in r.thickness_in]
            )
    return js
