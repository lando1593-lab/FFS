"""Importer for manufacturer thickness workbooks (Excel), e.g. Isolatek's intumescent estimating
programs.

Two layouts are recognised per sheet:

* **long**: one row per (member, rating): ``Designation | [Restraint] | Rating | W/D or A/P |
  Mils | sq ft factor``. Design and condition come from the sheet name (``N614 - NW``), product
  from the workbook name or ``--product``.
* **wide**: one row per member with a block of rating columns per product/variant:
  ``Designation | [Restraint] | W/D | SF/LF | 1 Hr | 1.5 Hr | … | 1 Hr | …`` with product and
  variant labels in the rows above the header. If the workbook has an ``indexes`` sheet mapping
  section → product/variant → UL design, the design is attached from it.

Every emitted row carries workbook, sheet, row and column so a value can be traced to its cell.
Values are the manufacturer's (authority level 6); the importer never derives or interpolates.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ffs.steel.designation import find_designations

_RATING_HDR = re.compile(r"^\s*(?P<r>\d(?:\.\d)?|\d-1/2|1/2)\s*-?\s*Hr\.?\s*$", re.IGNORECASE)
_DESIG_HDR = re.compile(r"desig|steel size|^des$|^astm", re.IGNORECASE)
_RESTRAINT_HDR = re.compile(r"restrain", re.IGNORECASE)
_WD_HDR = re.compile(r"w\s*/\s*d|a\s*/\s*p", re.IGNORECASE)
_SF_HDR = re.compile(r"sf\s*/\s*lf|sq\.?\s*ft|factor|^sf$", re.IGNORECASE)
_RATING_COL_HDR = re.compile(r"^rating$", re.IGNORECASE)
_MILS_HDR = re.compile(r"^mils?\s*$", re.IGNORECASE)
_DESIGN_TOKEN = re.compile(r"\b([DNPSXY]\d{3,4})\b")
_VARIANT = re.compile(r"\b(NW|LW|PTF|MW)\b")
_SECTION_WORDS = [
    ("non standard", "Non Standard"),
    ("non-standard", "Non Standard"),
    ("misc", "Misc"),
    ("hss", "HSS"),
    ("wf", "WF Columns"),
    ("wide flange", "WF Columns"),
    ("column", "WF Columns"),
    ("roof", "Roofs"),
    ("floor", "Floors"),
]


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s).lower().replace("®", ""))


def _hours(s: str) -> float | None:
    m = _RATING_HDR.match(str(s))
    if not m:
        return None
    r = m.group("r")
    if r == "1/2":
        return 0.5
    if "-1/2" in r:
        return float(r.split("-")[0]) + 0.5
    return float(r)


@dataclass
class ThicknessRow:
    workbook: str
    sheet: str
    row: int
    col: int
    product: str | None
    variant: str | None  # NW / LW / PTF / MW / None
    design: str | None
    section: str | None  # Floors / Roofs / HSS / WF Columns / Misc / Non Standard
    member_label: str
    canonical: str | None
    section_factor: float | None
    section_factor_kind: str | None  # "W/D" or "A/P"
    sf_per_lf: float | None
    restraint: str | None
    rating_hr: float
    thickness_as_printed: str
    thickness_mils: float | None
    not_rated: bool
    notes: list[str] = field(default_factory=list)


@dataclass
class WorkbookImport:
    workbook: str
    product_default: str | None
    rows: list[ThicknessRow]
    sheets_parsed: dict[str, str]  # sheet → layout
    sheets_skipped: list[str]
    design_index: dict[str, dict[str, str]]
    notes: list[str] = field(default_factory=list)


def _design_index(ws) -> dict[str, dict[str, str]]:
    """Parse an 'indexes' sheet: row 1 section names, row 2 'UL Designs' + design per column,
    row 3 product/variant label per column."""
    rows = list(ws.iter_rows(values_only=True, max_row=4))
    if len(rows) < 3:
        return {}
    sec_row, des_row, prod_row = rows[0], rows[1], rows[2]
    out: dict[str, dict[str, str]] = {}
    section = None
    for c in range(max(len(sec_row), len(des_row), len(prod_row))):
        s = sec_row[c] if c < len(sec_row) else None
        if s:
            section = str(s).strip()
        d = des_row[c] if c < len(des_row) else None
        p = prod_row[c] if c < len(prod_row) else None
        if section and d and p and _DESIGN_TOKEN.search(str(d)):
            out.setdefault(section, {})[_norm(p)] = _DESIGN_TOKEN.search(str(d)).group(1)
    return out


def _section_for(sheet: str) -> str | None:
    s = sheet.lower()
    for word, sec in _SECTION_WORDS:
        if word in s:
            return sec
    return None


def _num(v) -> float | None:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).strip())
    except ValueError:
        return None


def _parse_wide(
    ws, name: str, workbook: str, product_default: str | None, index: dict
) -> list[ThicknessRow] | None:
    rows = list(ws.iter_rows(values_only=True, max_row=12))
    hdr_i = None
    for i, r in enumerate(rows):
        if r and sum(1 for v in r if v is not None and _hours(str(v)) is not None) >= 2:
            hdr_i = i
            break
    if hdr_i is None:
        return None
    hdr = rows[hdr_i]
    desig_c = next(
        (c for c, v in enumerate(hdr) if v is not None and _DESIG_HDR.search(str(v))), None
    )
    if desig_c is None:
        # unlabeled designation column: the first column whose data cells are member-like strings
        sample = list(ws.iter_rows(values_only=True, min_row=hdr_i + 2, max_row=hdr_i + 8))
        for c in range(min(6, len(hdr))):
            vals = [r[c] for r in sample if c < len(r) and isinstance(r[c], str) and r[c].strip()]
            if len(vals) >= 3 and all(
                find_designations(v) or re.search(r"[A-Za-z]", v) for v in vals
            ):
                desig_c = c
                break
        if desig_c is None:
            return None
    restr_c = next(
        (c for c, v in enumerate(hdr) if v is not None and _RESTRAINT_HDR.search(str(v))), None
    )
    wd_c = next((c for c, v in enumerate(hdr) if v is not None and _WD_HDR.search(str(v))), None)
    sf_c = next((c for c, v in enumerate(hdr) if v is not None and _SF_HDR.search(str(v))), None)
    wd_kind = None
    if wd_c is not None:
        wd_kind = "A/P" if re.search(r"a\s*/\s*p", str(hdr[wd_c]), re.IGNORECASE) else "W/D"
    rating_cols = [
        (c, _hours(str(v)))
        for c, v in enumerate(hdr)
        if v is not None and _hours(str(v)) is not None
    ]
    # group labels above the header, forward-filled across columns
    above = rows[:hdr_i]
    labels: dict[int, tuple[str | None, str | None]] = {}
    last_prod, last_var = None, None
    for c, _ in rating_cols:
        prod = var = None
        for r in above:
            v = r[c] if c < len(r) else None
            if v is None or str(v).strip() == "":
                continue
            t = str(v).strip()
            if re.fullmatch(r"\d+", t) or _hours(t) is not None:
                continue
            if re.fullmatch(r"(NW|LW|PTF|MW)", t, re.IGNORECASE):
                var = t.upper()
            elif len(t) > 2:
                m = _VARIANT.search(
                    t.replace("SBLW", "SB LW")
                    .replace("SBNW", "SB NW")
                    .replace("3LW", "3 LW")
                    .replace("3NW", "3 NW")
                    .replace("4LW", "4 LW")
                    .replace("4NW", "4 NW")
                    .replace("5LW", "5 LW")
                    .replace("5NW", "5 NW")
                )
                prod = t
                if m and var is None:
                    var = m.group(1).upper()
                    prod = re.sub(
                        r"\s*(NW|LW|PTF|MW)$",
                        "",
                        t.replace("SBLW", "SB")
                        .replace("SBNW", "SB")
                        .replace("3LW", "3")
                        .replace("3NW", "3")
                        .replace("4LW", "4")
                        .replace("4NW", "4")
                        .replace("5LW", "5")
                        .replace("5NW", "5"),
                    ).strip()
        if prod is None:
            prod, var = last_prod, (var or last_var)
        labels[c] = (prod, var)
        last_prod, last_var = prod, var
    section = _section_for(name)
    sec_index = index.get(section or "", {}) if index else {}
    out: list[ThicknessRow] = []
    empty = 0
    for r_i, r in enumerate(ws.iter_rows(values_only=True, min_row=hdr_i + 2), start=hdr_i + 2):
        label = r[desig_c] if desig_c < len(r) else None
        if label is None or str(label).strip() == "":
            empty += 1
            if empty > 8:
                break
            continue
        empty = 0
        label = str(label).strip()
        des = find_designations(label)
        canonical = des[0].canonical if len(des) == 1 else None
        wd = _num(r[wd_c]) if wd_c is not None and wd_c < len(r) else None
        sf = _num(r[sf_c]) if sf_c is not None and sf_c < len(r) else None
        restraint = (
            str(r[restr_c]).strip().lower()
            if restr_c is not None and restr_c < len(r) and r[restr_c]
            else None
        )
        for c, hours in rating_cols:
            v = r[c] if c < len(r) else None
            if v is None or str(v).strip() == "":
                continue
            prod, var = labels.get(c, (None, None))
            prod = prod or product_default
            design = None
            notes: list[str] = []
            if sec_index:
                key = _norm((prod or "") + (var or ""))
                design = sec_index.get(key) or sec_index.get(_norm(prod or ""))
                if design is None:
                    notes.append("no design mapping in indexes sheet for this product/variant")
            txt = str(v).strip()
            nr = txt.upper() in ("NR", "N/R", "NA", "N/A", "—", "-")
            mils = None if nr else _num(v)
            if mils is None and not nr:
                notes.append("unparsed thickness cell")
            out.append(
                ThicknessRow(
                    workbook,
                    name,
                    r_i,
                    c + 1,
                    prod,
                    var,
                    design,
                    section,
                    label,
                    canonical,
                    wd,
                    wd_kind,
                    sf,
                    restraint,
                    hours,
                    txt,
                    mils,
                    nr,
                    notes,
                )
            )
    return out


def _parse_long(
    ws, name: str, workbook: str, product_default: str | None
) -> list[ThicknessRow] | None:
    rows = list(ws.iter_rows(values_only=True, max_row=3))
    if not rows or not rows[0]:
        return None
    hdr = rows[0]
    cols = {}
    for c, v in enumerate(hdr):
        if v is None:
            continue
        t = str(v)
        if _DESIG_HDR.search(t) and "desig" not in cols:
            cols["desig"] = c
        elif _RESTRAINT_HDR.search(t):
            cols["restraint"] = c
        elif _RATING_COL_HDR.match(t.strip()):
            cols["rating"] = c
        elif _WD_HDR.search(t):
            cols["wd"] = c
            cols["wd_kind"] = "A/P" if re.search(r"a\s*/\s*p", t, re.IGNORECASE) else "W/D"
        elif _MILS_HDR.match(t):
            cols["mils"] = c
        elif _SF_HDR.search(t) and "sf" not in cols:
            cols["sf"] = c
    if not {"desig", "rating", "mils"} <= cols.keys():
        return None
    designs = _DESIGN_TOKEN.findall(name.upper())
    design = "/".join(dict.fromkeys(designs)) or None
    var = _VARIANT.search(name.upper())
    variant = var.group(1) if var else None
    section = _section_for(name)
    out: list[ThicknessRow] = []
    for r_i, r in enumerate(ws.iter_rows(values_only=True, min_row=2), start=2):
        label = r[cols["desig"]] if cols["desig"] < len(r) else None
        if label is None or str(label).strip() == "":
            continue
        label = str(label).strip()
        rating = _num(r[cols["rating"]]) if cols["rating"] < len(r) else None
        if rating is None:
            continue
        des = find_designations(label)
        v = r[cols["mils"]] if cols["mils"] < len(r) else None
        txt = "" if v is None else str(v).strip()
        nr = txt.upper() in ("NR", "N/R", "NA", "N/A")
        out.append(
            ThicknessRow(
                workbook,
                name,
                r_i,
                cols["mils"] + 1,
                product_default,
                variant,
                design,
                section,
                label,
                des[0].canonical if len(des) == 1 else None,
                _num(r[cols["wd"]]) if "wd" in cols and cols["wd"] < len(r) else None,
                cols.get("wd_kind"),
                _num(r[cols["sf"]]) if "sf" in cols and cols["sf"] < len(r) else None,
                (
                    str(r[cols["restraint"]]).strip().lower()
                    if "restraint" in cols and cols["restraint"] < len(r) and r[cols["restraint"]]
                    else None
                ),
                rating,
                txt,
                None if nr else _num(v),
                nr,
                [] if (nr or _num(v) is not None) else ["unparsed thickness cell"],
            )
        )
    return out


def import_workbook(path: str | Path, product: str | None = None) -> WorkbookImport:
    import openpyxl

    path = Path(path)
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    index = {}
    if "indexes" in wb.sheetnames:
        index = _design_index(wb["indexes"])
    result = WorkbookImport(path.name, product, [], {}, [], index)
    try:
        for ws in wb.worksheets:
            if ws.title.lower() in ("indexes", "dropdowns", "total"):
                continue
            rows = _parse_wide(ws, ws.title, path.name, product, index)
            layout = "wide"
            if rows is None:
                rows = _parse_long(ws, ws.title, path.name, product)
                layout = "long"
            if rows is None:
                result.sheets_skipped.append(ws.title)
                continue
            result.sheets_parsed[ws.title] = layout
            result.rows.extend(rows)
    finally:
        wb.close()
    return result


def write_outputs(imp: WorkbookImport, out_dir: str | Path) -> None:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(imp.workbook).stem
    with (out_dir / f"{stem}.thickness.jsonl").open("w", encoding="utf-8") as f:
        for r in imp.rows:
            f.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")
    cols = [
        "workbook",
        "sheet",
        "row",
        "col",
        "product",
        "variant",
        "design",
        "section",
        "member_label",
        "canonical",
        "section_factor",
        "section_factor_kind",
        "sf_per_lf",
        "restraint",
        "rating_hr",
        "thickness_as_printed",
        "thickness_mils",
        "not_rated",
        "notes",
    ]
    with (out_dir / f"{stem}.thickness.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in imp.rows:
            d = asdict(r)
            w.writerow([("; ".join(d[c]) if isinstance(d[c], list) else d[c]) for c in cols])
    (out_dir / f"{stem}.import.json").write_text(
        json.dumps(
            {
                "workbook": imp.workbook,
                "rows": len(imp.rows),
                "sheets_parsed": imp.sheets_parsed,
                "sheets_skipped": imp.sheets_skipped,
                "design_index": imp.design_index,
                "notes": imp.notes,
            },
            indent=1,
        )
    )
