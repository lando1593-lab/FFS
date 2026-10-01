"""Parser for UL Product iQ design printouts (BXUV — Fire-Resistance Ratings, ANSI/UL 263).

Input: the PDF a user saves from iq.ulprospector.com (browser "print to PDF"), or its text.
Output: a :class:`DesignRecord` — header (design number, design date, "Last Updated on" date,
print/snapshot date, profile URL), rating lines, numbered items with sub-items, manufacturer
lines, thickness equations, and thickness tables, every value kept exactly as printed alongside
a parsed numeric form. Nothing is inferred: if a block does not parse it is kept verbatim in
``unparsed`` for a human. The record also carries UL's reproduction notice because UL permits
reproduction only in entirety and with attribution.

A design record is reference data (CODE_PRODUCT_RULE source). The "snapshot_date" (when the
printout was made) and "last_updated" (UL's own stamp) are what the authority rules use to decide
whether the record is current (NFR-VER-01). A 2019 printout is a 2019 snapshot, never "current".
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from fractions import Fraction
from pathlib import Path

from ffs.steel.designation import find_designations

# --- Product iQ page furniture -------------------------------------------------------------
_PAGE_HDR = re.compile(
    r"\n?(?P<snap>\d{1,2}/\d{1,2}/\d{4})\s*\n(?:FIRE-RESISTANCE RATINGS - ANSI/UL 263\s*)?(?:\|\s*)?\n?\s*UL Product iQ\s*\n"
    r"(?P<url>https://iq\.ulprospector\.com/en/profile\?e=\d+)\s*\n\d+/\d+\s*\n"
)  # noqa: E501
_PAGE_HDR_ALT = re.compile(
    r"\n?\d{1,2}/\d{1,2}/\d{4}\nFIRE-RESISTANCE RATINGS - ANSI/UL 263 \| UL Product iQ\n(?:https://[^\n]+\n)?\d+/\d+\n"
)
_DESIGN_NO = re.compile(r"^Design No\.\s*(?P<no>[A-Z]{1,3}-?\d{3,4}[A-Z]?)\s*$", re.MULTILINE)
_BXUV_TITLE = re.compile(r"BXUV\.(?P<no>[A-Z]{1,3}-?\d{3,4}[A-Z]?)\s*-\s*FIRE-RESISTANCE RATINGS")
_LAST_UPDATED = re.compile(r"Last Updated on (?P<d>\d{4}-\d{2}-\d{2})")
_DATE_LINE = re.compile(
    r"^(?P<d>(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4})\s*$",
    re.MULTILINE,
)
_RATING_LINE = re.compile(
    r"^(?P<kind>(?:Restrained|Unrestrained)?\s*(?:Assembly|Beam)?\s*Ratings?(?:\s*&\s*Unrestrained Beam Ratings?)?)\s*(?:—|-)\s*(?P<hours>[^\n(]+?)(?:\s*\((?P<see>See [^)]*)\))?\s*\.?\s*$",
    re.MULTILINE,
)  # noqa: E501
_ITEM = re.compile(r"^(?P<no>\d{1,2}[A-Z]?)\.\s+(?P<title>[^\n]+?)\s+—\s+(?P<rest>.*)$")
_ITEM_PLAIN = re.compile(r"^(?P<no>\d{1,2}[A-Z]?)\.\s+(?P<title>[^\n]+)$")
_SUBITEM = re.compile(r"^(?P<letter>[A-Z])\.\s+(?P<text>.+)$")
_MFR = re.compile(
    r"^(?P<name>[A-Z][A-Z0-9 ,&'./-]{2,}?(?:\s+(?:L L C|LLC|INC|CORP|CO|LTD|LLP|S A|GMBH|AG|PLC))?)\s+—\s+(?P<text>.+)$"
)  # noqa: E501
_EQUATION = re.compile(
    r"R\s*\n\s*h\s*=\s*\n\s*(?P<a>\d+(?:\.\d+)?)\s*\((?P<f>W/D|A/P)\)\s*\+\s*(?P<b>\d+(?:\.\d+)?)"
)
_WD_RANGE = re.compile(
    r"(?P<f>W/D|A/P|M/D)\s*(?:=|range of|ratio of|of)\s*(?P<lo>\d+(?:\.\d+)?)\s*(?:to|-|–)\s*(?P<hi>\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
_H_RANGE = re.compile(
    r"in the range(?: of)?\s*(?P<lo>\d+(?:\.\d+)?(?:-\d+/\d+)?|\d+/\d+)\s*(?:to|-|–)\s*"
    r"(?P<hi>\d+(?:\.\d+)?(?:-\d+/\d+)?|\d+/\d+)\s*(?P<u>in|mm)",
    re.IGNORECASE,
)
_R_UNITS = re.compile(
    r"R\s*=\s*(?:the\s+)?(?:Fire resistance rating(?: period)?|hourly rating)\s*(?:in)?\s*\(?\s*(?P<u>minutes|hours|hrs|min|h)\b",
    re.IGNORECASE,
)
# "1 Hr" / "Min Thkns In. 2 Hr" / "1 Hr Min" (intumescent tables print "1 Hr Min" over "Thickness, In.")
_RATING_COL = re.compile(
    r"^(?:[A-Za-z.]+\s+)*(?P<r>\d(?:-\d/\d{1,2})?|\d/\d|1/2)\s*Hr\.?(?:\s+Min\.?)?$"
)
# non-AISC member labels used in UL column tables: "SP 4x0.237" (std pipe), "ST 4x4x0.375", "ST20x20x0.75 in."
_TUBE_LABEL = re.compile(
    r"^(?:SP|ST|RT|HSS|PIPE|TS)\s?\d+(?:\.\d+)?(?:x\d+(?:\.\d+)?){1,2}(?:\s?in\.?)?$", re.IGNORECASE
)
_RATING_CELL = re.compile(
    r"^(?P<a>\d(?:-\d/\d{1,2})?|\d/\d)(?:\s*(?:or|,|and)\s*(?:\d(?:-\d/\d{1,2})?|\d/\d))*[*+#]*$"
)
_VALUE_CELL = re.compile(r"^(?:[A-Z]{1,3}\d{1,2}[xX]\d{1,3}(?:\.\d)?|\d{1,2}K\d{1,2})$")
# a thickness cell as printed: fraction, decimal, or a marker ("—", "NR", "N/A") kept verbatim
_THK_CELL = re.compile(
    r"^(?P<v>\d+(?:-\d+/\d+)?|\d+/\d+|—|-|–|\d+\.\d+|NR|N/A)(?P<note>\s*\(\s*[\d/ *-]+\)|[*+#]+)?$"
)
_NOTE_LINE = re.compile(r"^\(\s*[\d/ -]+\*{0,3}\)$")  # e.g. "(1-1/2**)" printed under a cell
_FLOAT = re.compile(r"^\d+\.\d+$")
_NUM = re.compile(r"^\d+(?:\.\d+)?$")
_RATIO_NAME = re.compile(
    r"^(?:W/D|A/P|M/D|Hp/A)$"
)  # the ratio column(s) printed before thicknesses
# "Rating, Hr." / "Rating Period (min)" followed by bare rating cells printed as column heads
_RATING_HDR = re.compile(
    r"^(?:[A-Za-z&/ ]+\s+)?Ratings?(?:\s+Period)?,?\s*\(?(?P<u>Hrs?|min(?:utes)?)\.?\)?:?$",
    re.IGNORECASE,
)
_BARE_RATING = re.compile(r"^(?:\d(?:-\d/\d{1,2})?|\d/\d|\d{2,3})$")  # "1", "1-1/2", "60", "120"
_BARE_HSS_LABEL = re.compile(
    r"^\d{1,2}x\d{1,2}x(?:\d+/\d+|0?\.\d+)$"
)  # "6x4x1/4" under "HSS Steel Size"
_SPLIT_LABEL_HEAD = re.compile(
    r"^[A-Z]{1,3}\s?\d{1,3}\s?[xX]$"
)  # "W16 x" with "100" on the next line
_LEGEND = re.compile(r"^(?P<m>NR|N/A|—|–|\*{1,3}|\+|#)\s*=\s*\S.*$")  # "NR = No Rating"
# a title line printed above a table that names what the table is for
_TABLE_TITLE = re.compile(
    r"^(?:.*\bRatings?:|.+\b(?:Columns?|Beams?|Joists?|Pipes?|Tubes?)\b.*,\s*Min\s+Thkns,?\s*(?:In|mm)\.?)$",
    re.IGNORECASE,
)
# intumescent "T = k/(W/D)" equations, inline ("for 1 hour ratings, in the W/D range of ...") or as
# an equation table ("Hourly Ratng | Thickness Equation | Thickness Range | W/D Ratio Range")
_T_EQUATION = re.compile(r"T\s*=\s*(?P<k>\d+(?:\.\d+)?)\s*/\s*\((?P<f>W/D|A/P|M/D)\)")
_FOR_RATING = re.compile(
    r"for\s+(?P<r>\d(?:-\d/\d{1,2})?|\d/\d)\s*(?:hour|hr\.?|h)\s+ratings?", re.IGNORECASE
)
_RANGE_LINE = re.compile(r"^(?P<lo>\d+(?:\.\d+)?)\s+to\s+(?P<hi>\d+(?:\.\d+)?)$")
_EQ_TABLE_THK_HDR = re.compile(r"Thickness\s+Range,?\s*(?P<u>in|mm)\b", re.IGNORECASE)
_EQ_TABLE_WD_HDR = re.compile(r"(?P<f>W/D|A/P|M/D)\s+Ratio\s+Range", re.IGNORECASE)
# dry-mix pipe/tube fraction layout: "R — 0.38" printed above "h =", "3.58 (A/P)" below it
_EQUATION_RC = re.compile(
    r"R\s*(?:—|–|-)\s*(?P<c>\d+(?:\.\d+)?)\s*\n\s*h\s*=\s*\n\s*(?P<k>\d+(?:\.\d+)?)\s*\((?P<f>W/D|A/P)\)\s*\n"
)
_H_MINMAX = re.compile(
    r"h\s*=\s*the thickness[^\n]*?\bmin\s*(?P<lo>\d+(?:\.\d+)?)\s*(?:-|–|—|to)\s*max\s*(?P<hi>\d+(?:\.\d+)?)\s*(?P<u>in|mm)",
    re.IGNORECASE,
)
_WD_SHALL_RANGE = re.compile(
    r"(?P<f>W/D|A/P|M/D)\s+ratio\b[^\n]*?\bshall range from\s+(?P<lo>\d+(?:\.\d+)?)\s+to\s+(?P<hi>\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
_SEE_TABLE_BELOW = re.compile(r"table below", re.IGNORECASE)
_REPRO = re.compile(r"UL permits the reproduction.*", re.DOTALL)


def frac_in(s: str) -> float | None:
    s = s.strip().replace("–", "-").replace("—", "-")
    if s in ("-", ""):
        return None
    try:
        if "-" in s and "/" in s:
            w, f = s.split("-", 1)
            return float(w) + float(Fraction(f))
        if "/" in s:
            return float(Fraction(s))
        return float(s)
    except (ValueError, ZeroDivisionError):
        return None


@dataclass
class TableRow:
    cells: list[str]  # as printed
    label: str | None = None  # member label for size tables, e.g. W8X10
    canonical: str | None = None
    wd: float | None = None  # first ratio column (W/D, A/P or M/D: see ThicknessTable.ratio_names)
    # thickness cells in inches: None for a marker cell (NR, N/A, —) and for a table printed in mm
    values_in: list[float | None] = field(default_factory=list)
    note: str | None = None
    ratios: list[float | None] = field(default_factory=list)  # every ratio column, e.g. [M/D, Hp/A]
    # thickness cells as numbers in the table's own units (ThicknessTable.units); None for markers
    values: list[float | None] = field(default_factory=list)


@dataclass
class ThicknessTable:
    item_no: str | None
    kind: str  # "size_wd" (member × W/D × ratings) | "rating_rows" (rating columns + value columns)
    headers: list[str]
    rating_columns: list[str] = field(
        default_factory=list
    )  # for size_wd: "1 Hr", ... / "60 min", ...
    rating_fields: int = 0  # for rating_rows: how many rating cells lead each row
    value_columns: list[str] = field(default_factory=list)  # for rating_rows
    condition: str | None = None  # e.g. "flange tips reduced to one-half"
    rows: list[TableRow] = field(default_factory=list)
    units: str | None = (
        None  # "in" | "mm" | "mils" as printed in the header; None if it does not say
    )
    ratio_names: list[str] = field(default_factory=list)  # e.g. ["W/D"], ["A/P"], ["M/D", "Hp/A"]
    notes: list[str] = field(
        default_factory=list
    )  # legend lines under the table, e.g. "NR = No Rating"


@dataclass
class Equation:
    item_no: str | None
    form: str  # "h = R / (a*(W/D) + b)" | "T = k / (W/D)" | "h = (R - c) / (k*(A/P))"
    a: float | None  # "h = R / (a*X + b)" only
    b: float | None
    wd_range: (
        tuple[float, float] | None
    )  # range of ``factor`` the equation is valid for, as printed
    h_range_in: tuple[float, float] | None  # thickness range when the design prints it in inches
    as_printed: str
    factor: str = "W/D"
    r_units: str | None = None  # "hours" | "minutes" as stated in the design
    k: float | None = None  # constant of "T = k / X" and of "h = (R - c) / (k*X)"
    c: float | None = None  # offset of "h = (R - c) / (k*X)"
    rating: str | None = (
        None  # the single rating the equation is restricted to, as printed ("1-1/2")
    )
    rating_hours: float | None = None
    h_range: tuple[float, float] | None = None  # thickness range as printed, in ``h_units``
    h_units: str | None = None  # "in" | "mm"
    notes: list[str] = field(default_factory=list)


@dataclass
class Manufacturer:
    item_no: str
    name: str
    text: str  # "Types 300, 300AC, ..." as printed


@dataclass
class Item:
    no: str
    title: str
    text: str
    sub_items: list[dict] = field(default_factory=list)  # {letter, text}
    manufacturers: list[Manufacturer] = field(default_factory=list)
    is_sfrm: bool = False
    is_intumescent: bool = False


@dataclass
class RatingLine:
    kind: str
    hours_as_printed: str
    hours: list[float]
    see: str | None


@dataclass
class DesignRecord:
    agency: str
    category: str
    design_no: str
    design_date: str | None
    last_updated: str | None
    snapshot_date: str | None
    source_url: str | None
    member_category_guess: str
    ratings: list[RatingLine]
    items: list[Item]
    equations: list[Equation]
    tables: list[ThicknessTable]
    sfrm_manufacturers: list[Manufacturer]
    reproduction_notice: str | None
    text_sha256: str
    source_file: str | None = None
    unparsed: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# (likely) BXUV prefix conventions; verify against the BXUV Guide Information before relying on it.
PREFIX_CATEGORY = {
    "X": "column (contour/box sprayed)",
    "Y": "column",
    "N": "floor beam (beam-only)",
    "S": "roof beam (beam-only)",
    "P": "roof-ceiling assembly",
    "D": "floor-ceiling assembly (steel deck)",
    "A": "floor-ceiling assembly",
    "G": "floor-ceiling assembly",
    "J": "floor-ceiling assembly",
    "K": "floor-ceiling assembly",
    "L": "floor-ceiling assembly",
    "U": "wall",
    "V": "wall",
    "XR": "column (UL 1709 hydrocarbon)",
}


def _hours(s: str) -> list[float]:
    out = []
    for tok in re.findall(r"\d-\d/\d{1,2}|\d/\d{1,2}|\d", s):  # mixed, fraction, then integer
        v = frac_in(tok)
        if v is not None:
            out.append(v)
    return out


def strip_page_furniture(text: str) -> tuple[str, str | None, str | None]:
    snap = url = None
    m = _PAGE_HDR.search(text)
    if m:
        snap, url = m.group("snap"), m.group("url")
    text = _PAGE_HDR.sub("\n", text)
    text = _PAGE_HDR_ALT.sub("\n", text)
    return text, snap, url


def find_design_no(text: str) -> str | None:
    """The BXUV design number printed in ``text`` ("Design No. X649" on its own line, or the
    "BXUV.X649 - FIRE-RESISTANCE RATINGS" title), normalised (upper case, hyphen dropped); None
    when the text carries no design number (a UL certificate or notice, for example)."""
    m = _DESIGN_NO.search(text) or _BXUV_TITLE.search(text)
    return m.group("no").upper().replace("-", "") if m else None


def _is_size_label(ln: str, bare_hss: bool = False) -> bool:
    core = ln.lstrip("*").strip()
    if len(core) > 24:
        return False
    if bare_hss and _BARE_HSS_LABEL.match(core):
        return True
    return bool(find_designations(core)) or bool(_TUBE_LABEL.match(core))


def _header_back(lines: list[str], i: int) -> list[int]:
    """Indices (document order) of the short header lines printed directly above ``lines[i]``:
    "Steel", "Size", "W/D", "HSS Steel Size", "Tube Steel Columns, Min Thkns, In.". Stops at
    sentence text, numbered items, cells and member labels."""
    out: list[int] = []
    k = i - 1
    while k >= 0 and i - k <= 10:
        t = lines[k].strip()
        if not t:
            k -= 1
            continue
        if (
            len(t) > 40
            or t[0].islower()
            or len(t.split()) > 6
            or _THK_CELL.match(t)
            or _BARE_RATING.match(t)
            or _FLOAT.match(t)
            or _RATING_COL.match(t)
            or _ITEM.match(t)
            or _ITEM_PLAIN.match(t)
            or _is_size_label(t, bare_hss=True)
        ):
            break
        out.append(k)
        k -= 1
    return out[::-1]


def _units_in(texts: list[str]) -> str | None:
    """Thickness units named in header text: "Min Thkns In." / "Thickness, mm" / "(mils)"."""
    blob = " ".join(texts)
    if re.search(r"\bmils\b", blob, re.IGNORECASE):
        return "mils"
    if re.search(r"\bmm\b", blob, re.IGNORECASE):
        return "mm"
    if re.search(r"\bin(?:ch|ches)?\b", blob, re.IGNORECASE):
        return "in"
    return None


def _legend_after(lines: list[str], j: int, tbl: ThicknessTable) -> None:
    """Attach a legend printed right under the table ("NR = No Rating") as a table note when its
    marker actually occurs in the table."""
    k = j
    while k < len(lines) and k < j + 3:
        t = lines[k].strip()
        if not t:
            k += 1
            continue
        lm = _LEGEND.match(t)
        if lm:
            mk = lm.group("m")
            cells = [c for r in tbl.rows for c in r.cells]
            if any(mk in c for c in cells) or any(r.note and mk in r.note for r in tbl.rows):
                tbl.notes.append(t)
        break


def _parse_size_wd_table(
    lines: list[str],
    i: int,
    rating_cols: list[str],
    item_no: str | None,
    headers: list[str],
    condition: str | None,
    ratio_names: list[str] | None = None,
    units: str | None = None,
    bare_hss: bool = False,
) -> tuple[ThicknessTable, int]:
    tbl = ThicknessTable(
        item_no,
        "size_wd",
        headers,
        rating_columns=rating_cols,
        condition=condition,
        units=units,
        ratio_names=list(ratio_names or []),
    )
    n = len(rating_cols)
    n_ratio = max(1, len(tbl.ratio_names))
    while i < len(lines):
        ln = lines[i].strip()
        if not ln:
            i += 1
            continue
        j = i + 1
        # a label wrapped over two lines: "W16 x" / "100"
        if (
            _SPLIT_LABEL_HEAD.match(ln)
            and j < len(lines)
            and re.fullmatch(r"\d{1,4}", lines[j].strip())
            and _is_size_label(ln + " " + lines[j].strip())
        ):
            ln = ln + " " + lines[j].strip()
            j += 1
        if not _is_size_label(ln, bare_hss):
            break
        core = ln.lstrip("*")
        des = find_designations(core)
        if not des and bare_hss and _BARE_HSS_LABEL.match(core):
            des = find_designations("HSS" + core)  # the header ("HSS Steel Size") names the family
        label = ln
        ratio_cells: list[str] = []
        if j < len(lines) and _FLOAT.match(lines[j].strip()):
            ratio_cells.append(lines[j].strip())
            j += 1
            # further ratio columns only when the header declares them ("M/D" then "Hp/A")
            while len(ratio_cells) < n_ratio and j < len(lines) and _NUM.match(lines[j].strip()):
                ratio_cells.append(lines[j].strip())
                j += 1
        vals: list[str] = []
        blanks = 0
        while j < len(lines) and len(vals) < n:
            t = lines[j].strip()
            if not t and blanks < 2:  # a page break inside the row leaves a blank line
                blanks += 1
                j += 1
                continue
            if not _THK_CELL.match(t):
                break
            vals.append(t)
            j += 1
        if len(vals) < n:
            break
        nums = [frac_in(_THK_CELL.match(v).group("v")) for v in vals]
        if units == "mils":
            values_in = [x / 1000 if x is not None else None for x in nums]
        elif units == "mm":
            values_in = [None] * len(nums)
        else:
            values_in = nums
        row = TableRow(
            cells=[label] + ratio_cells + vals,
            label=label.lstrip("*"),
            canonical=des[0].canonical if des else None,
            wd=float(ratio_cells[0]) if ratio_cells else None,
            values_in=values_in,
            note="*" if label.startswith("*") else None,
            ratios=[float(r) for r in ratio_cells],
            values=nums,
        )
        tbl.rows.append(row)
        i = j
    return tbl, i


def _parse_rating_rows_table(
    lines: list[str], i: int, k: int, value_cols: list[str], item_no: str | None, headers: list[str]
) -> tuple[ThicknessTable, int]:
    tbl = ThicknessTable(item_no, "rating_rows", headers, rating_fields=k, value_columns=value_cols)
    m = len(value_cols)
    while i + k + m <= len(lines):
        if tbl.rows and _NOTE_LINE.match(lines[i].strip()):
            tbl.rows[-1].note = ((tbl.rows[-1].note or "") + " " + lines[i].strip()).strip()
            i += 1
            continue
        rat = [lines[i + t].strip() for t in range(k)]
        vals = [lines[i + k + t].strip() for t in range(m)]
        if not all(_RATING_CELL.match(r) for r in rat) or not all(
            _THK_CELL.match(v) or _VALUE_CELL.match(v) for v in vals
        ):
            break
        tbl.rows.append(
            TableRow(
                cells=rat + vals,
                values_in=[
                    frac_in(_THK_CELL.match(v).group("v")) if _THK_CELL.match(v) else None
                    for v in vals
                ],
                note=" ".join(v for v in vals if re.search(r"[*+#(]", v)) or None,
            )
        )
        i += k + m
    return tbl, i


def parse_design_text(text: str, source_file: str | None = None) -> DesignRecord:
    raw_sha = hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()
    body, snap, url = strip_page_furniture(text)
    m = _DESIGN_NO.search(body) or _BXUV_TITLE.search(body)
    design_no = m.group("no").upper().replace("-", "") if m else "UNKNOWN"
    prefix = re.match(r"[A-Z]+", design_no).group(0) if design_no != "UNKNOWN" else ""
    last = _LAST_UPDATED.search(body)
    repro = _REPRO.search(body)
    # design date: the dated line right after "Design No."
    design_date = None
    if m:
        after = body[m.end() : m.end() + 80]
        dm = _DATE_LINE.search(after)
        if dm:
            design_date = dm.group("d")
    # body between "Design No." and "Last Updated"
    start = m.start() if m else 0
    end = last.start() if last else len(body)
    core = body[start:end]
    ratings = [
        RatingLine(
            r.group("kind").strip(),
            r.group("hours").strip(),
            _hours(r.group("hours")),
            r.group("see"),
        )
        for r in _RATING_LINE.finditer(core)
    ]
    items: list[Item] = []
    tables: list[ThicknessTable] = []
    equations: list[Equation] = []
    unparsed: list[str] = []
    lines = core.split("\n")
    cur: Item | None = None
    cur_sub: dict | None = None
    last_rating_cols: list[str] = []
    last_ratio_names: list[str] = []
    last_units: str | None = None
    last_table_end: int | None = None  # line index right after the last parsed table
    pending_condition: str | None = None
    i = 0
    while i < len(lines):
        ln = lines[i].rstrip()
        s = ln.strip()
        if not s:
            i += 1
            continue
        im = _ITEM.match(s) or _ITEM_PLAIN.match(s)
        if im and not (cur and cur.no == im.group("no")):
            cur = Item(im.group("no"), im.group("title").strip(" —-"), s)
            cur.is_sfrm = "spray-applied fire resistive" in cur.title.lower()
            cur.is_intumescent = "intumescent" in cur.title.lower() or "mastic" in cur.title.lower()
            cur_sub = None
            items.append(cur)
            i += 1
            continue
        sm = _SUBITEM.match(s) if cur else None
        if sm and len(s) > 12:
            cur_sub = {"letter": sm.group("letter"), "text": s}
            cur.sub_items.append(cur_sub)
            if "spray-applied fire resistive" in s.lower():
                cur.is_sfrm = True
            i += 1
            continue
        mm = _MFR.match(s)
        if (
            mm
            and cur
            and len(mm.group("name")) >= 4
            and mm.group("name").upper() == mm.group("name")
        ):
            cur.manufacturers.append(
                Manufacturer(cur.no, mm.group("name").strip(), mm.group("text").strip())
            )
            i += 1
            continue
        # size × W/D × rating-columns table header: a run of "N Hr" lines
        if _RATING_COL.match(s):
            cols = []
            j = i
            while j < len(lines):
                t = lines[j].strip()
                if _RATING_COL.match(t):
                    cols.append(_RATING_COL.match(t).group("r") + " Hr")
                    j += 1
                    continue
                # blank lines and digit-less label fragments ("Min Thkns") inside the run: skip
                # ahead if a rating line follows within the next few lines
                q = None
                for cand in range(j + 1, min(j + 5, len(lines))):
                    c = lines[cand].strip()
                    if _RATING_COL.match(c):
                        q = cand
                        break
                    if c and re.search(r"\d", c):
                        break
                if q is not None and (not t or not re.search(r"\d", t)):
                    j = q
                    continue
                break
            run_end = j
            # header fragments printed after the last rating line: "Thickness, In." / "mm"
            frags: list[str] = []
            while j < len(lines) and len(frags) < 3:
                t = lines[j].strip()
                if not t:
                    j += 1
                    continue
                if re.search(r"\d", t) or len(t) > 24:
                    break
                frags.append(t)
                j += 1
            hdr = [x.strip() for x in lines[max(0, i - 6) : i] if x.strip()]
            back_lines = [lines[b].strip() for b in _header_back(lines, i)]
            ratio_names = [t for t in back_lines if _RATIO_NAME.match(t)]
            units = _units_in(back_lines + [x.strip() for x in lines[i:j]])
            title = next((t for t in back_lines if _TABLE_TITLE.match(t)), None)
            tbl, j2 = _parse_size_wd_table(
                lines,
                j,
                cols,
                cur.no if cur else None,
                hdr,
                title or pending_condition,
                ratio_names=ratio_names,
                units=units,
            )
            if title and pending_condition:
                tbl.notes.append(f"introduced by: {pending_condition}")
            last_rating_cols = cols
            last_ratio_names, last_units = ratio_names, units
            pending_condition = None
            if tbl.rows:
                _legend_after(lines, j2, tbl)
                tables.append(tbl)
                last_table_end = j2
                i = j2
                continue
            i = run_end
            continue
        # a continuation size table after a "table below" sentence, reusing the last rating columns
        if (
            last_rating_cols
            and _is_size_label(s)
            and i + 1 < len(lines)
            and _FLOAT.match(lines[i + 1].strip())
        ):
            tbl, j2 = _parse_size_wd_table(
                lines,
                i,
                last_rating_cols,
                cur.no if cur else None,
                [],
                pending_condition,
                ratio_names=last_ratio_names,
                units=last_units,
            )
            if tbl.rows:
                prev = tables[-1] if tables else None
                if (
                    pending_condition is None
                    and prev is not None
                    and prev.kind == "size_wd"
                    and prev.rating_columns == last_rating_cols
                ):
                    prev.rows.extend(tbl.rows)  # continuation after a page break
                    _legend_after(lines, j2, prev)
                else:
                    _legend_after(lines, j2, tbl)
                    tables.append(tbl)
                pending_condition = None
                last_table_end = j2
                i = j2
                continue
        # "Rating, Hr." / "Rating Period (min)" followed by bare rating cells as column heads and
        # then size rows: a size_wd table whose rating columns are not printed as "N Hr" lines
        rh = _RATING_HDR.match(s) if cur is not None else None
        if rh:
            unit = "min" if rh.group("u").lower().startswith("min") else "Hr"
            j = i + 1
            raw_cols: list[str] = []
            while j < len(lines):
                t = lines[j].strip()
                if not t:
                    j += 1
                    continue
                if not _BARE_RATING.match(t):
                    break
                raw_cols.append(t)
                j += 1
            frags = []  # "Required Thickness (mils)" printed between the heads and the rows
            while len(raw_cols) >= 2 and j < len(lines) and len(frags) < 3:
                t = lines[j].strip()
                if not t:
                    j += 1
                    continue
                if re.search(r"\d", t) or len(t) > 40:
                    break
                frags.append(t)
                j += 1
            back = _header_back(lines, i)
            back_lines = [lines[b].strip() for b in back]
            bare_hss = any(re.search(r"\bHSS\b", t) for t in back_lines + frags)
            if len(raw_cols) >= 2 and j < len(lines) and _is_size_label(lines[j].strip(), bare_hss):
                cols = [f"{c} {unit}" for c in raw_cols]
                ratio_names = [t for t in back_lines if _RATIO_NAME.match(t)]
                units = _units_in(back_lines + [s] + frags)
                title = next((t for t in back_lines if _TABLE_TITLE.match(t)), None)
                hstart = back[0] if back else i
                tbl, j2 = _parse_size_wd_table(
                    lines,
                    j,
                    cols,
                    cur.no,
                    back_lines + [s] + raw_cols + frags,
                    title or pending_condition,
                    ratio_names=ratio_names,
                    units=units,
                    bare_hss=bare_hss,
                )
                if tbl.rows and title and pending_condition:
                    tbl.notes.append(f"introduced by: {pending_condition}")
                if tbl.rows:
                    prev = tables[-1] if tables else None
                    if (
                        tbl.condition is None
                        and prev is not None
                        and prev.kind == "size_wd"
                        and prev.item_no == tbl.item_no
                        and prev.condition
                        and last_table_end is not None
                        and not any(x.strip() for x in lines[last_table_end:hstart])
                    ):
                        # a second table (e.g. the metric copy) printed directly under the first
                        # with no heading of its own: the heading printed above both applies
                        tbl.condition = prev.condition
                        tbl.notes.append(
                            f"heading carried over from the table printed directly above: {prev.condition}"
                        )
                    _legend_after(lines, j2, tbl)
                    tables.append(tbl)
                    last_rating_cols = cols
                    last_ratio_names, last_units = ratio_names, units
                    pending_condition = None
                    last_table_end = j2
                    i = j2
                    continue
        # rating-rows table header: "Rating Hr" lines, then value-column lines ending in "In."
        if (
            cur is not None
            and "—" not in s
            and (
                re.search(r"Ratings?,?\s*Hr\.?$", s)
                or (
                    s.startswith(("Restrained", "Unrestrained"))
                    and i + 2 < len(lines)
                    and "Rating" in lines[i + 1] + lines[i + 2]
                )
            )
        ):
            j = i
            hdr: list[str] = []
            k = 0
            vcols: list[str] = []
            buf = ""
            extra: list[str] = []  # header lines after the rating columns that do not end in "In."
            while j < len(lines) and j < i + 24:
                t = lines[j].strip()
                if not t:
                    j += 1
                    continue
                if _RATING_CELL.match(t):  # first data cell
                    break
                hdr.append(t)
                if vcols and not buf and find_designations(t) and len(t) <= 10:
                    vcols[-1] += " " + t  # reference member printed under its column, e.g. W6x16
                    j += 1
                    continue
                buf = (buf + " " + t).strip()
                if re.search(r"Ratings?,?\s*Hr\.?$", t):
                    k += 1
                    buf = ""
                elif re.search(r"In\.\s*\*?$", t) or t.endswith("In."):
                    vcols.append(buf)
                    buf = ""
                elif k and re.fullmatch(
                    r"(?:Un)?restrained\s+(?:Beam|Assembly)s?|Beams?|Joists?|Columns?",
                    t,
                    re.IGNORECASE,
                ):
                    extra.append(t)
                    buf = ""
                elif k and re.fullmatch(
                    r"(?:Min\s+)?(?:Beam|Column|Joist)\s+Size", buf, re.IGNORECASE
                ):
                    vcols.append(buf)  # a text column such as "Min Beam Size"
                    buf = ""
                j += 1
            if k and not vcols and extra:
                vcols = extra  # e.g. "Rating, Hr | Restrained Beam | Unrestrained Beam"
            subs = []
            for a_i in range(len(hdr) - 1):
                nxt = hdr[a_i + 1]
                if (
                    hdr[a_i].strip().lower() == "on"
                    and nxt
                    and not re.search(r"Ratings?\s*Hr", nxt)
                ):
                    subs.append("on " + nxt.strip())
            if subs and vcols:
                parent = vcols[-1]
                vcols = vcols[:-1] + [f"{parent} {sname}" for sname in subs]
            if k and vcols and j < len(lines):
                tbl, j2 = _parse_rating_rows_table(lines, j, k, vcols, cur.no if cur else None, hdr)
                # a title line just above the header names the table's condition, e.g.
                # "Normal Weight Concrete, Fluted Floor and Form Units, Min Thkns In."
                for back in range(i - 1, max(-1, i - 3), -1):
                    prev_line = lines[back].strip() if back >= 0 else ""
                    if prev_line and (
                        prev_line.endswith("In.") or re.search(r"Concrete|Deck|Units", prev_line)
                    ):
                        tbl.condition = prev_line
                        break
                if tbl.rows:
                    if any(re.search(r"\bIn\.", v) for v in vcols):
                        tbl.units = "in"
                    tables.append(tbl)
                    last_table_end = j2
                    i = j2
                    continue
        if _SEE_TABLE_BELOW.search(s):
            # the introducing sentence may wrap onto following lines; keep it whole
            cond = s
            k = i + 1
            while not cond.rstrip().endswith((".", ":")) and k < len(lines) and k < i + 4:
                cond += " " + lines[k].strip()
                k += 1
            pending_condition = cond
        # otherwise: body text of the current item/sub-item
        if cur_sub is not None:
            cur_sub["text"] += " " + s
        elif cur is not None:
            cur.text += " " + s
        elif not ratings or i < 12:
            pass  # header region (ratings, disclaimers)
        else:
            unparsed.append(s)
        i += 1
    # equations (regex over the raw core; they span lines)
    for em in _EQUATION.finditer(core):
        before = core[max(0, em.start() - 350) : em.start()]
        after = core[em.end() : em.end() + 400]
        factor = em.group("f").upper()
        imm = _WD_RANGE.search(after[:120])  # "(for column W/D range of 0.33 to 2.51)" right after
        wd_before = [m for m in _WD_RANGE.finditer(before) if m.group("f").upper() == factor]
        if imm and imm.group("f").upper() == factor:
            wd = imm
        elif wd_before:
            wd = wd_before[-1]
        else:
            wd = _WD_RANGE.search(after)
        hr_before = list(_H_RANGE.finditer(before))
        hr = hr_before[-1] if hr_before else _H_RANGE.search(after)
        ru = _R_UNITS.search(after) or _R_UNITS.search(before)
        r_units = None
        if ru:
            r_units = "minutes" if ru.group("u").lower().startswith("min") else "hours"
        owner = None
        for it in items:
            if it.text and em.group(0).split("\n")[0] in it.text:
                owner = it.no
        h_rng = (frac_in(hr.group("lo")), frac_in(hr.group("hi"))) if hr else None
        h_units = hr.group("u").lower() if hr else None
        equations.append(
            Equation(
                owner,
                f"h = R / (a*({factor}) + b)",
                float(em.group("a")),
                float(em.group("b")),
                (frac_in(wd.group("lo")), frac_in(wd.group("hi"))) if wd else None,
                h_rng if h_units in (None, "in") else None,
                re.sub(r"\s+", " ", em.group(0)),
                factor=factor,
                r_units=r_units,
                h_range=h_rng,
                h_units=h_units,
            )
        )

    def _owner_of(first_line: str) -> str | None:
        own = None
        for it in items:
            if it.text and first_line in it.text:
                own = it.no
        return own

    # intumescent "T = k/(W/D)" equations: one record per (rating, equation)
    tms = list(_T_EQUATION.finditer(core))
    for idx, em in enumerate(tms):
        factor = em.group("f").upper()
        ls = core.rfind("\n", 0, em.start()) + 1
        le = core.find("\n", em.end())
        le = len(core) if le < 0 else le
        prev_end = tms[idx - 1].end() if idx else 0
        next_start = tms[idx + 1].start() if idx + 1 < len(tms) else len(core)
        before_full = core[max(0, ls - 800) : ls]
        before = core[max(prev_end, ls - 600) : ls]  # this equation's own sentence only
        after = core[le:next_start][:400]
        prev_lines = [t.strip() for t in before_full.split("\n") if t.strip()]
        after_lines = [t.strip() for t in after.split("\n") if t.strip()]
        notes: list[str] = []
        rating = h_units = None
        wd_rng = h_rng = None
        if (
            prev_lines
            and _BARE_RATING.match(prev_lines[-1])
            and len(after_lines) >= 2
            and all(_RANGE_LINE.match(t) for t in after_lines[:2])
        ):
            # equation table row: "1 | T = 0.0408/(W/D) | 0.021 to 0.093 | 0.44 to 3.00"; the two
            # range cells are assigned by the order of the column heads printed above the table
            rating = prev_lines[-1]
            thk_hdr = list(_EQ_TABLE_THK_HDR.finditer(before_full))
            wd_hdr = [
                m for m in _EQ_TABLE_WD_HDR.finditer(before_full) if m.group("f").upper() == factor
            ]
            if thk_hdr and wd_hdr:
                th, wh = thk_hdr[-1], wd_hdr[-1]
                r_thk, r_wd = after_lines[:2] if th.start() < wh.start() else after_lines[1::-1]
                mt, mw = _RANGE_LINE.match(r_thk), _RANGE_LINE.match(r_wd)
                h_rng = (float(mt.group("lo")), float(mt.group("hi")))
                wd_rng = (float(mw.group("lo")), float(mw.group("hi")))
                h_units = th.group("u").lower()
            else:
                notes.append(
                    f"range cells printed next to the equation ({after_lines[0]}; {after_lines[1]}) "
                    "not assigned: column heads not found"
                )
        else:
            fr = list(_FOR_RATING.finditer(before))
            if fr:
                rating = fr[-1].group("r")
            wds = [m for m in _WD_RANGE.finditer(before) if m.group("f").upper() == factor]
            if wds:
                wd_rng = (frac_in(wds[-1].group("lo")), frac_in(wds[-1].group("hi")))
            hm = _H_RANGE.search(after)
            if hm:
                h_rng = (frac_in(hm.group("lo")), frac_in(hm.group("hi")))
                h_units = hm.group("u").lower()
        if h_rng and None not in h_rng and h_rng[0] > h_rng[1]:
            notes.append(
                f"thickness range printed as {h_rng[0]} to {h_rng[1]} (low above high); kept as printed"
            )
        equations.append(
            Equation(
                _owner_of(core[ls:le].strip()),
                f"T = k / ({factor})",
                None,
                None,
                wd_rng,
                h_rng if h_units == "in" else None,
                re.sub(r"\s+", " ", em.group(0)),
                factor=factor,
                k=float(em.group("k")),
                rating=rating,
                rating_hours=frac_in(rating) if rating else None,
                h_range=h_rng,
                h_units=h_units,
                notes=notes,
            )
        )
    # dry-mix pipe/tube "h = (R - c) / (k*(A/P))" printed as a fraction
    for em in _EQUATION_RC.finditer(core):
        factor = em.group("f").upper()
        after = core[em.end() : em.end() + 600]
        ru = _R_UNITS.search(after)
        r_units = None
        if ru:
            r_units = "minutes" if ru.group("u").lower().startswith("min") else "hours"
        hm = _H_MINMAX.search(after)
        h_rng = (float(hm.group("lo")), float(hm.group("hi"))) if hm else None
        h_units = hm.group("u").lower() if hm else None
        wds = [m for m in _WD_SHALL_RANGE.finditer(after) if m.group("f").upper() == factor]
        wd_rng = (float(wds[-1].group("lo")), float(wds[-1].group("hi"))) if wds else None
        equations.append(
            Equation(
                _owner_of(em.group(0).split("\n")[0].strip()),
                f"h = (R - c) / (k*({factor}))",
                None,
                None,
                wd_rng,
                h_rng if h_units == "in" else None,
                re.sub(r"\s+", " ", em.group(0)).strip(),
                factor=factor,
                r_units=r_units,
                k=float(em.group("k")),
                c=float(em.group("c")),
                h_range=h_rng,
                h_units=h_units,
                notes=[
                    "read from the fraction layout: numerator 'R - c' printed above 'h =', "
                    f"denominator 'k ({factor})' below it"
                ],
            )
        )
    sfrm_mfrs = [mf for it in items if it.is_sfrm for mf in it.manufacturers]
    return DesignRecord(
        agency="UL",
        category="BXUV",
        design_no=design_no,
        design_date=design_date,
        last_updated=last.group("d") if last else None,
        snapshot_date=snap,
        source_url=url,
        member_category_guess=PREFIX_CATEGORY.get(prefix, "unknown"),
        ratings=ratings,
        items=items,
        equations=equations,
        tables=tables,
        sfrm_manufacturers=sfrm_mfrs,
        reproduction_notice=re.sub(r"\s+", " ", repro.group(0)) if repro else None,
        text_sha256=raw_sha,
        source_file=source_file,
        unparsed=unparsed[:50],
    )


def parse_design_pdf(path: str | Path) -> DesignRecord:
    import pymupdf

    path = Path(path)
    doc = pymupdf.open(path)
    try:
        text = "\n".join(p.get_text("text") for p in doc)
    finally:
        doc.close()
    return parse_design_text(text, source_file=path.name)


def write_record(rec: DesignRecord, out: str | Path) -> Path:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    p = out / f"UL_{rec.design_no}.json"
    p.write_text(json.dumps(rec.to_dict(), indent=1, ensure_ascii=False))
    return p
