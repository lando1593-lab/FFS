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
    r"\n?(?P<snap>\d{1,2}/\d{1,2}/\d{4})\s*\nFIRE-RESISTANCE RATINGS - ANSI/UL 263\s*(?:\|\s*)?\n?\s*UL Product iQ\s*\n"
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
    r"^(?P<kind>(?:Restrained|Unrestrained)?\s*(?:Assembly|Beam)?\s*Ratings?(?:\s*&\s*Unrestrained Beam Ratings?)?)\s*—\s*(?P<hours>[^\n(]+?)(?:\s*\((?P<see>See [^)]*)\))?\s*\.?\s*$",
    re.MULTILINE,
)  # noqa: E501
_ITEM = re.compile(r"^(?P<no>\d{1,2}[A-Z]?)\.\s+(?P<title>[^\n]+?)\s+—\s+(?P<rest>.*)$")
_ITEM_PLAIN = re.compile(r"^(?P<no>\d{1,2}[A-Z]?)\.\s+(?P<title>[^\n]+)$")
_SUBITEM = re.compile(r"^(?P<letter>[A-Z])\.\s+(?P<text>.+)$")
_MFR = re.compile(
    r"^(?P<name>[A-Z][A-Z0-9 ,&'./-]{2,}?(?:\s+(?:L L C|LLC|INC|CORP|CO|LTD|LLP|S A|GMBH|AG|PLC))?)\s+—\s+(?P<text>.+)$"
)  # noqa: E501
_EQUATION = re.compile(
    r"R\s*\n\s*h\s*=\s*\n\s*(?P<a>\d+(?:\.\d+)?)\s*\(W/D\)\s*\+\s*(?P<b>\d+(?:\.\d+)?)"
)
_WD_RANGE = re.compile(r"W/D\s*=\s*(?P<lo>\d+(?:\.\d+)?)\s*(?:to|-|–)\s*(?P<hi>\d+(?:\.\d+)?)")
_H_RANGE = re.compile(
    r"thickness in the range\s*(?P<lo>\d+(?:\.\d+)?)\s*-\s*(?P<hi>\d+(?:\.\d+)?)\s*in"
)
_RATING_COL = re.compile(r"^(?P<r>\d(?:-\d/\d{1,2})?|\d/\d|1/2)\s*Hr\.?$")
_RATING_CELL = re.compile(
    r"^(?P<a>\d(?:-\d/\d{1,2})?|\d/\d)(?:\s*(?:or|,)\s*(?P<b>\d(?:-\d/\d{1,2})?|\d/\d))?$"
)
_THK_CELL = re.compile(
    r"^(?P<v>\d+(?:-\d+/\d+)?|\d+/\d+|—|-|–|\d+\.\d+)(?P<note>\s*\(\s*[\d/ -]+\)|\*+)?$"
)
_FLOAT = re.compile(r"^\d+\.\d+$")
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
    wd: float | None = None
    values_in: list[float | None] = field(default_factory=list)  # thickness cells parsed
    note: str | None = None


@dataclass
class ThicknessTable:
    item_no: str | None
    kind: str  # "size_wd" (member × W/D × ratings) | "rating_rows" (rating columns + value columns)
    headers: list[str]
    rating_columns: list[str] = field(default_factory=list)  # for size_wd: "1 Hr", ...
    rating_fields: int = 0  # for rating_rows: how many rating cells lead each row
    value_columns: list[str] = field(default_factory=list)  # for rating_rows
    condition: str | None = None  # e.g. "flange tips reduced to one-half"
    rows: list[TableRow] = field(default_factory=list)


@dataclass
class Equation:
    item_no: str | None
    form: str  # "h = R / (a*(W/D) + b)"
    a: float
    b: float
    wd_range: tuple[float, float] | None
    h_range_in: tuple[float, float] | None
    as_printed: str


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
    for tok in re.findall(r"\d(?:-\d/\d{1,2})?|\d/\d", s):
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


def _parse_size_wd_table(
    lines: list[str],
    i: int,
    rating_cols: list[str],
    item_no: str | None,
    headers: list[str],
    condition: str | None,
) -> tuple[ThicknessTable, int]:
    tbl = ThicknessTable(
        item_no, "size_wd", headers, rating_columns=rating_cols, condition=condition
    )
    n = len(rating_cols)
    while i < len(lines):
        ln = lines[i].strip()
        des = find_designations(ln.lstrip("*"))
        if not des or len(ln) > 20:
            break
        label = ln
        j = i + 1
        wd = None
        if j < len(lines) and _FLOAT.match(lines[j].strip()):
            wd = float(lines[j].strip())
            j += 1
        vals: list[str] = []
        while j < len(lines) and len(vals) < n and _THK_CELL.match(lines[j].strip()):
            vals.append(lines[j].strip())
            j += 1
        if len(vals) < n:
            break
        row = TableRow(
            cells=[label] + ([f"{wd}"] if wd is not None else []) + vals,
            label=label.lstrip("*"),
            canonical=des[0].canonical,
            wd=wd,
            values_in=[frac_in(_THK_CELL.match(v).group("v")) for v in vals],
            note="*" if label.startswith("*") else None,
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
        rat = [lines[i + t].strip() for t in range(k)]
        vals = [lines[i + k + t].strip() for t in range(m)]
        if not all(_RATING_CELL.match(r) for r in rat) or not all(_THK_CELL.match(v) for v in vals):
            break
        tbl.rows.append(
            TableRow(
                cells=rat + vals,
                values_in=[frac_in(_THK_CELL.match(v).group("v")) for v in vals],
                note=" ".join(v for v in vals if "*" in v or "(" in v) or None,
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
            while j < len(lines) and _RATING_COL.match(lines[j].strip()):
                cols.append(lines[j].strip())
                j += 1
            hdr = [x.strip() for x in lines[max(0, i - 6) : i] if x.strip()]
            tbl, j2 = _parse_size_wd_table(
                lines, j, cols, cur.no if cur else None, hdr, pending_condition
            )
            last_rating_cols = cols
            pending_condition = None
            if tbl.rows:
                tables.append(tbl)
                i = j2
                continue
            i = j
            continue
        # a continuation size table after a "table below" sentence, reusing the last rating columns
        if (
            last_rating_cols
            and find_designations(s.lstrip("*"))
            and len(s) <= 12
            and i + 1 < len(lines)
            and _FLOAT.match(lines[i + 1].strip())
        ):
            tbl, j2 = _parse_size_wd_table(
                lines, i, last_rating_cols, cur.no if cur else None, [], pending_condition
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
                else:
                    tables.append(tbl)
                pending_condition = None
                i = j2
                continue
        # rating-rows table header: "Rating Hr" lines, then value-column lines ending in "In."
        if (
            cur is not None
            and "—" not in s
            and (
                re.search(r"Ratings?\s*Hr\.?$", s)
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
                if re.search(r"Ratings?\s*Hr\.?$", t):
                    k += 1 + (
                        1
                        if "&" in buf
                        and "Unrestrained" in buf
                        and "Restrained" in buf
                        and k == 0
                        and False
                        else 0
                    )
                    buf = ""
                elif re.search(r"In\.\s*\*?$", t) or t.endswith("In."):
                    vcols.append(buf)
                    buf = ""
                j += 1
            if k and vcols and j < len(lines):
                tbl, j2 = _parse_rating_rows_table(lines, j, k, vcols, cur.no if cur else None, hdr)
                if tbl.rows:
                    tables.append(tbl)
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
        wd_before = list(_WD_RANGE.finditer(before))
        hr_before = list(_H_RANGE.finditer(before))
        wd = wd_before[-1] if wd_before else _WD_RANGE.search(after)
        hr = hr_before[-1] if hr_before else _H_RANGE.search(after)
        owner = None
        for it in items:
            if it.text and em.group(0).split("\n")[0] in it.text:
                owner = it.no
        equations.append(
            Equation(
                owner,
                "h = R / (a*(W/D) + b)",
                float(em.group("a")),
                float(em.group("b")),
                (float(wd.group("lo")), float(wd.group("hi"))) if wd else None,
                (float(hr.group("lo")), float(hr.group("hi"))) if hr else None,
                re.sub(r"\s+", " ", em.group(0)),
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
