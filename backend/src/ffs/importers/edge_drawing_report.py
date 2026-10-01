"""Importer for The EDGE "Fireproofing Drawing Report" and "Fireproofing Spray Chart" printouts.

These are the company's own shop-drawing submittals: a cover page per sheet, then a legend
page with (Description | Test | Hours | Thickness) rows beside the marked-up plan image. Each
row is a submitted decision: member, role, design code as EDGE prints it, rating and
thickness. Everything is kept as printed; the design code's suffix tokens ("NW", "LW", "C",
"P/T", "F", "B") are split off and recorded, never interpreted here.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ffs.importers.ul_design import frac_in
from ffs.steel.designation import find_designations

_DESIGN = re.compile(r"^([A-Z]{1,2}\d{3,4})([A-Z]?)\b\s*(.*)$")
_SIDES = re.compile(r"\b(\d)\s*Sides?\b", re.IGNORECASE)
_ROLE = re.compile(
    r"\b(PRIMARY BEAM|SECONDARY BEAM|COLUMN LENGTH|COLUMN|BRIDGING|JOIST|AM STD|STEEL DECK)\b",
    re.IGNORECASE,
)
_HOURS = re.compile(r"^\d+(?:\.\d+)?$")
_THK = re.compile(r'^(\d+(?:-\d+/\d+)?|\d+/\d+)"$')
_JOIST = re.compile(r'^JOIST\s+(\d+)"', re.IGNORECASE)
_DECK = re.compile(r"^STEEL DECK TYPE\s+(\S+)\s*\(([\d.]+)\s*Exp Factor\)", re.IGNORECASE)
_BAGS = re.compile(r"^Bags:\s*([\d.]+)$")


@dataclass
class LegendRow:
    page: int
    description: str
    member_label: str
    canonical: str | None
    role: (
        str | None
    )  # primary_beam / secondary_beam / column / angle / bridging / joist / channel / deck / hss
    sides: int | None
    design_code: str  # as printed: "N823 NW C"
    design: str | None  # "N823"
    design_suffix: str | None  # letter glued to the number: "F" in "P723F"
    design_tokens: list[str]  # the rest: ["NW", "C"]
    hours: float | None
    thickness_as_printed: str
    thickness_in: float | None
    swatch_rgb: tuple[int, int, int] | None
    extra: dict = field(default_factory=dict)


@dataclass
class ReportSheet:
    page: int
    sheet_label: str  # "ADD2-S121-Second Floor Area A"
    calc_label: str | None  # "Calcs Blaze Shield (Type II)"
    product_hint: str | None  # "Blaze Shield (Type II)"
    kind: str  # drawing_report / spray_chart
    rows: list[LegendRow] = field(default_factory=list)
    thickness_legend: list[str] = field(default_factory=list)  # spray chart colour legend
    bags: float | None = None


@dataclass
class DrawingReport:
    source_file: str
    report_name: str | None
    project: str | None
    print_date: str | None
    sheets: list[ReportSheet] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _rows_by_y(page) -> list[tuple[float, list[tuple[float, str]]]]:
    rows: dict[int, list[tuple[float, str]]] = {}
    for b in page.get_text("dict")["blocks"]:
        for ln in b.get("lines", []):
            for s in ln["spans"]:
                t = s["text"].strip()
                if t:
                    rows.setdefault(round(s["bbox"][1]), []).append((s["bbox"][0], t))
    out = []
    for y in sorted(rows):
        cells = sorted(rows[y])
        out.append((y, cells))
    return out


def _swatch_colors(page) -> list[tuple[float, tuple[int, int, int]]]:
    """Legend swatches are small images at the left margin; (y-centre, mean RGB) per image."""
    import pymupdf

    out = []
    for info in page.get_image_info(xrefs=True):
        x0, y0, x1, y1 = info["bbox"]
        if x0 > 100 or (x1 - x0) > 80 or (y1 - y0) > 40:
            continue  # the plan image, the logo
        try:
            pix = pymupdf.Pixmap(page.parent, info["xref"])
            if pix.n - pix.alpha >= 3:
                n = pix.width * pix.height
                r = g = b = 0
                step = max(1, n // 400)
                cnt = 0
                for i in range(0, n, step):
                    px = pix.pixel(i % pix.width, i // pix.width)
                    r += px[0]
                    g += px[1]
                    b += px[2]
                    cnt += 1
                out.append(((y0 + y1) / 2, (r // cnt, g // cnt, b // cnt)))
        except Exception:  # noqa: BLE001
            continue
    return out


def _canonical(label: str) -> str | None:
    text = re.sub(r"\s+", "", label.upper())
    text = re.sub(r"^C(\d)", r"C\1", text)
    des = find_designations(text)
    if len(des) == 1:
        return des[0].canonical
    return None


def _parse_description(desc: str) -> tuple[str, str | None, int | None, dict]:
    extra: dict = {}
    sides = None
    m = _SIDES.search(desc)
    if m:
        sides = int(m.group(1))
    role = None
    rm = _ROLE.search(desc)
    jm = _JOIST.match(desc)
    dm = _DECK.match(desc)
    if dm:
        role = "deck"
        extra = {"deck_type": dm.group(1), "exposure_factor": float(dm.group(2))}
        return desc, role, sides, extra
    if jm:
        role = "joist"
        extra = {"joist_depth_in": float(jm.group(1))}
        return desc, role, sides, extra
    if rm:
        word = rm.group(1).upper()
        role = {
            "PRIMARY BEAM": "primary_beam",
            "SECONDARY BEAM": "secondary_beam",
            "COLUMN LENGTH": "column",
            "COLUMN": "column",
            "BRIDGING": "bridging",
            "AM STD": "channel",
        }.get(word, word.lower())
        cm = re.search(r"\bCOLUMN\s+(C\d+)\b", desc, re.IGNORECASE)
        if cm:
            extra["column_mark"] = cm.group(1)
    label = re.split(r"\s+-\s+", desc)[0]
    label = _SIDES.sub("", label).strip()
    label = re.sub(r"\s+(Bridging|C\d+)$", "", label, flags=re.IGNORECASE).strip()
    if role is None:
        up = label.upper()
        role = "angle" if up.startswith("L ") else "hss" if up.startswith("HSS") else None
    return label, role, sides, extra


def parse_drawing_report(path: str | Path) -> DrawingReport:
    import pymupdf

    path = Path(path)
    doc = pymupdf.open(str(path))
    rep = DrawingReport(path.name, None, None, None)
    for pi, page in enumerate(doc):
        rows = _rows_by_y(page)
        texts = {t for _, cells in rows for _, t in cells}
        joined = {y: " | ".join(t for _, t in cells) for y, cells in rows}
        if rep.report_name is None:
            for _, cells in rows:
                for i, (_, t) in enumerate(cells):
                    if t == "Report Name:" and i + 1 < len(cells):
                        rep.report_name = cells[i + 1][1]
                    if t == "Bid:" and i + 1 < len(cells):
                        rep.project = cells[i + 1][1]
                    if t == "Print Date:" and i + 1 < len(cells):
                        rep.print_date = cells[i + 1][1]
        if "Section:" in texts or not any(t.startswith("Legend") for t in texts):
            continue  # cover page
        sheet_label = calc_label = None
        for _, cells in rows:
            for i, (_, t) in enumerate(cells):
                if t in ("Page:", "Page") and i + 1 < len(cells):
                    sheet_label = cells[i + 1][1]
                if t.startswith("Calcs"):
                    calc_label = t
            if sheet_label:
                break
        if sheet_label is None:
            for _, cells in rows:
                t = cells[0][1]
                if t.startswith("Page ") and len(cells) > 1:
                    sheet_label = t[5:].strip()
                    calc_label = next((x for _, x in cells if x.startswith("Calcs")), None)
                    break
        product_hint = None
        if calc_label:
            product_hint = re.sub(r"^Calcs\s+", "", calc_label)
            product_hint = re.sub(r"\s+-\s+(Roof|Floor)$", "", product_hint)
        kind = "drawing_report"
        header_y = next((y for y, cells in rows if cells[0][1] == "Legend"), None)
        is_spray = header_y is not None and not any(
            t == "Description" for _, cells in rows for _, t in cells
        )
        if is_spray:
            kind = "spray_chart"
        sheet = ReportSheet(pi + 1, sheet_label or f"page {pi + 1}", calc_label, product_hint, kind)
        swatches = _swatch_colors(page)

        def swatch_for(y: float, swatches=swatches) -> tuple[int, int, int] | None:
            best = min(swatches, key=lambda s: abs(s[0] - y), default=None)
            return best[1] if best and abs(best[0] - y) < 12 else None

        for y, cells in rows:
            if header_y is None or y <= header_y:
                continue
            texts_row = [t for _, t in cells]
            if kind == "spray_chart":
                for t in texts_row:
                    if _THK.match(t):
                        sheet.thickness_legend.append(t)
                    bm = _BAGS.match(t)
                    if bm:
                        sheet.bags = float(bm.group(1))
                continue
            if len(cells) < 4 or not (55 <= cells[0][0] <= 65):
                continue
            desc, code, hours, thk = texts_row[0], texts_row[1], texts_row[2], texts_row[-1]
            if not _THK.match(thk) or not _HOURS.match(hours):
                rep.notes.append(f"p{pi + 1}: unread legend row: {joined[y][:80]}")
                continue
            dm = _DESIGN.match(code)
            label, role, sides, extra = _parse_description(desc)
            sheet.rows.append(
                LegendRow(
                    pi + 1,
                    desc,
                    label,
                    _canonical(label) if role not in ("joist", "deck") else None,
                    role,
                    sides,
                    code,
                    dm.group(1) if dm else None,
                    (dm.group(2) or None) if dm else None,
                    dm.group(3).split() if dm and dm.group(3) else [],
                    float(hours),
                    thk,
                    frac_in(thk.rstrip('"')),
                    swatch_for(y + 8),
                    extra,
                )
            )
        rep.sheets.append(sheet)
    doc.close()
    return rep


def write_drawing_report(rep: DrawingReport, out_dir: str | Path) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(rep.source_file).stem
    js = out_dir / f"{stem}.json"
    js.write_text(json.dumps(asdict(rep), indent=1), encoding="utf-8")
    with (out_dir / f"{stem}.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "project",
                "sheet",
                "product_hint",
                "description",
                "member",
                "canonical",
                "role",
                "sides",
                "design_code",
                "design",
                "suffix",
                "tokens",
                "hours",
                "thickness",
                "thickness_in",
            ]
        )
        for sh in rep.sheets:
            for r in sh.rows:
                w.writerow(
                    [
                        rep.project,
                        sh.sheet_label,
                        sh.product_hint,
                        r.description,
                        r.member_label,
                        r.canonical,
                        r.role,
                        r.sides,
                        r.design_code,
                        r.design,
                        r.design_suffix,
                        " ".join(r.design_tokens),
                        r.hours,
                        r.thickness_as_printed,
                        r.thickness_in,
                    ]
                )
    return js
