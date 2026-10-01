"""Importer for "Spray Report" PDFs exported from The EDGE (report id ``xrSprayReport``).

Observed layout (one report = pairs of pages per contract sheet):
  * TABLE PAGE (portrait): header ``Spray Report - <sheet> - <title>``; Bid Date / Estimator /
    Market Sector / Status at top right; product line
    ``<CODE> - <Manufacturer Product> - <Density> - <Base> - <Report variant>``; zero or more
    design lines ``<design> - <rating>[ - <note>]``; then three sections ``Linear Spray Items``,
    ``Area Spray Items``, ``Count Spray Items``, each a table with columns Color | Member | Type |
    Inches / Mils. The Color cell is a vector swatch: a solid stroke or a run of filled dashes.
    The Member cell is ``<label> - <thickness decimal>"``; Type is ``Beam - 3 Side`` /
    ``Column - 4 Side``; the last cell is the thickness as a fraction (``1/2 inch``) or mils.
  * PLAN PAGE (landscape): same header, then the coloured-up plan as horizontal raster strips.

Everything extracted is a FACT about the report (it is the estimator's own historical output).
It is NOT authoritative design/thickness data for any other project (ADR-0004); the importer
records values exactly as printed and cross-checks the decimal and fraction thickness columns.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from fractions import Fraction
from pathlib import Path

import pymupdf

from ffs.steel.designation import find_designations

_HEADER_RE = re.compile(r"^Spray Report\s*-\s*(?P<sheet>\S+)\s*-\s*(?P<title>.*)$")
_DESIGN_RE = re.compile(
    r"^(?P<design>[A-Z]{1,3}-?\d{2,4}[A-Z]?)\s*-\s*(?P<rating>\d+(?:\.\d+)?)\s*HRS?(?:\s*-\s*(?P<note>.+))?$",
    re.IGNORECASE,
)
_MEMBER_CELL_RE = re.compile(
    r"^(?P<label>.+?)\s*-\s*(?P<dec>\d*\.\d+|\d+)\s*(?P<unit>\"|”|in|mils?)\s*$", re.IGNORECASE
)
_THK_CELL_RE = re.compile(
    r"^(?P<val>\d+(?:\s+\d+/\d+)?|\d+/\d+|\d*\.\d+)\s*(?P<unit>inch(?:es)?|in|\"|mils?)$",
    re.IGNORECASE,
)
_TYPE_CELL_RE = re.compile(r"^(?P<role>[A-Za-z ]+?)\s*-\s*(?P<sides>\d)\s*Side", re.IGNORECASE)
_LEVEL_RE = re.compile(
    r"\b(ROOF|PENTHOUSE|MEZZ(?:ANINE)?|BASEMENT|FOUNDATION|LEVEL\s*\d+|\d+(?:ST|ND|RD|TH)\s+FLOOR)\b",
    re.IGNORECASE,
)

SECTIONS = ("Linear Spray Items", "Area Spray Items", "Count Spray Items")
COL_COLOR = (15.0, 145.0)
COL_MEMBER = (145.0, 450.0)
COL_TYPE = (450.0, 522.0)
COL_THK = (522.0, 600.0)


@dataclass
class Swatch:
    rgb_hex: str
    pattern: str  # solid / dashed / unknown


@dataclass
class SprayItem:
    section: str  # linear / area / count
    member_label: str  # as printed, e.g. "W12X26" or 'Type Ⅰ 1 ½"'
    canonical_section: str | None
    role: str | None  # beam / column / ...
    sides: int | None
    thickness_in: float | None  # from the decimal in the member cell
    thickness_display: str  # the fraction/mils cell as printed
    thickness_unit: str  # inch / mils
    thickness_consistent: bool | None  # decimal vs fraction agree within 1/64"
    swatch: Swatch | None
    row_y: float
    notes: list[str] = field(default_factory=list)


@dataclass
class SheetReport:
    sheet_no: str
    title: str
    level_guess: str | None
    bid_date: str | None
    estimator: str | None
    market_sector: str | None
    status: str | None
    product_code: str | None
    product_name: str | None
    density: str | None
    base: str | None
    report_variant: str | None
    designs: list[dict]
    items: list[SprayItem]
    table_page: int
    plan_page: int | None
    plan_image_count: int
    qa_notes: list[str] = field(default_factory=list)


@dataclass
class SprayReport:
    source: str
    pdf_title: str | None
    pdf_author: str | None
    created: str | None
    sheets: list[SheetReport]

    def to_dict(self) -> dict:
        return asdict(self)


def _spans(page: pymupdf.Page) -> list[dict]:
    out = []
    for b in page.get_text("dict").get("blocks", []):
        for line in b.get("lines", []):
            for s in line.get("spans", []):
                if s["text"].strip():
                    out.append({"text": s["text"], "bbox": s["bbox"], "size": s["size"]})
    return out


def _rows(spans: list[dict], tol: float = 2.0) -> list[list[dict]]:
    rows: list[list[dict]] = []
    for s in sorted(spans, key=lambda s: (s["bbox"][1], s["bbox"][0])):
        if rows and abs(rows[-1][0]["bbox"][1] - s["bbox"][1]) <= tol:
            rows[-1].append(s)
        else:
            rows.append([s])
    for r in rows:
        r.sort(key=lambda s: s["bbox"][0])
    return rows


def _cell(row: list[dict], col: tuple[float, float]) -> str:
    return "".join(s["text"] for s in row if col[0] <= s["bbox"][0] < col[1]).strip()


def _hex(rgb: tuple[float, float, float] | None) -> str:
    if rgb is None:
        return "#000000"
    r, g, b = (int(round(c * 255)) for c in rgb[:3])
    return f"#{r:02x}{g:02x}{b:02x}"


def _swatches(page: pymupdf.Page) -> list[tuple[float, Swatch]]:
    """(center_y, Swatch) for every coloured mark in the Color column."""
    out = []
    for d in page.get_drawings():
        r = d["rect"]
        if not (COL_COLOR[0] <= r.x0 and r.x1 <= COL_COLOR[1] + 2):
            continue
        col = d.get("color")
        fill = d.get("fill")
        if d["type"] == "s" and col and col != (0, 0, 0):
            out.append(
                (
                    (r.y0 + r.y1) / 2,
                    Swatch(
                        _hex(col), "solid" if d.get("dashes") in (None, "[] 0", "") else "dashed"
                    ),
                )
            )
        elif (
            d["type"] in ("f", "fs") and fill and fill not in ((0, 0, 0),) and len(d["items"]) >= 8
        ):
            # grey table rules are fills too; skip near-grey
            if max(fill[:3]) - min(fill[:3]) < 0.05:
                continue
            out.append(((r.y0 + r.y1) / 2, Swatch(_hex(fill), "dashed")))
    return out


def _parse_thickness(dec: str, unit: str) -> tuple[float | None, str]:
    u = "mils" if unit.lower().startswith("mil") else "inch"
    try:
        v = float(dec)
    except ValueError:
        return None, u
    return v, u


def _frac_to_in(val: str) -> float | None:
    val = val.strip()
    try:
        if " " in val:
            w, f = val.split()
            return float(w) + float(Fraction(f))
        if "/" in val:
            return float(Fraction(val))
        return float(val)
    except (ValueError, ZeroDivisionError):
        return None


def _parse_table_page(page: pymupdf.Page, page_index: int) -> SheetReport | None:
    spans = _spans(page)
    text_rows = _rows(spans)
    joined = [" ".join(s["text"] for s in r) for r in text_rows]
    if not any("Linear Spray Items" in j for j in joined):
        return None
    # --- header: title lines are the large-font spans at the left
    big = [s for s in spans if s["size"] >= 14 and s["bbox"][0] < 100]
    header = " ".join(s["text"].strip() for s in sorted(big, key=lambda s: s["bbox"][1]))
    m = _HEADER_RE.match(header)
    sheet_no, title = (m.group("sheet"), m.group("title").strip(" -")) if m else ("?", header)

    def kv(label: str) -> str | None:
        for r in text_rows:
            t = " ".join(s["text"] for s in r)
            if label in t and "-" in t:
                return t.split("-", 1)[1].strip() or None
        return None

    product_line = " ".join(
        s["text"].strip()
        for s in sorted(
            (s for s in spans if 11 <= s["size"] < 14 and s["bbox"][0] < 100),
            key=lambda s: s["bbox"][1],
        )
    )
    parts = [p.strip() for p in product_line.split(" - ")]
    parts = [p for p in parts if p]
    product_code = parts[0] if parts else None
    product_name = parts[1] if len(parts) > 1 else None
    density = parts[2] if len(parts) > 2 else None
    base = parts[3] if len(parts) > 3 else None
    variant = parts[4] if len(parts) > 4 else None

    designs = []
    for s in spans:
        if 9 <= s["size"] < 11 and s["bbox"][0] < 100:
            dm = _DESIGN_RE.match(s["text"].strip())
            if dm:
                designs.append(
                    {
                        "design": dm.group("design").upper(),
                        "rating_hr": float(dm.group("rating")),
                        "note": (dm.group("note") or "").strip() or None,
                        "as_printed": s["text"].strip(),
                    }
                )

    swatches = _swatches(page)
    items: list[SprayItem] = []
    section = None
    for r in text_rows:
        t = " ".join(s["text"] for s in r).strip()
        if t in SECTIONS:
            section = t.split()[0].lower()
            continue
        if section is None or t.startswith("Color") or r[0]["size"] > 8:
            continue
        member_cell = _cell(r, COL_MEMBER)
        if not member_cell:
            continue
        type_cell = _cell(r, COL_TYPE)
        thk_cell = _cell(r, COL_THK)
        y = (r[0]["bbox"][1] + r[0]["bbox"][3]) / 2
        notes: list[str] = []
        mm = _MEMBER_CELL_RE.match(member_cell)
        if mm:
            label = mm.group("label").strip()
            thk, unit = _parse_thickness(mm.group("dec"), mm.group("unit"))
        else:
            label, thk, unit = member_cell, None, "inch"
            notes.append("member cell did not match '<label> - <thickness>' pattern")
        des = find_designations(label)
        canonical = des[0].canonical if len(des) == 1 else None
        if len(des) > 1:
            notes.append("multiple designations in member cell")
        role = sides = None
        tm = _TYPE_CELL_RE.match(type_cell)
        if tm:
            role, sides = tm.group("role").strip().lower(), int(tm.group("sides"))
        elif type_cell:
            role = type_cell.lower()
        consistent = None
        disp_unit = unit
        tk = _THK_CELL_RE.match(thk_cell)
        if tk and thk is not None:
            v = _frac_to_in(tk.group("val"))
            disp_unit = "mils" if tk.group("unit").lower().startswith("mil") else "inch"
            if v is not None:
                consistent = abs(v - thk) <= (1 / 64 if disp_unit == "inch" else 0.5)
                if not consistent:
                    notes.append(f"decimal {thk} vs printed '{thk_cell}' disagree")
        sw = min(swatches, key=lambda s: abs(s[0] - y), default=None)
        swatch = sw[1] if sw and abs(sw[0] - y) <= 6 else None
        if swatch is None:
            notes.append("no colour swatch found for row")
        items.append(
            SprayItem(
                section,
                label,
                canonical,
                role,
                sides,
                thk,
                thk_cell,
                disp_unit,
                consistent,
                swatch,
                round(y, 1),
                notes,
            )
        )

    rep = SheetReport(
        sheet_no=sheet_no,
        title=title,
        level_guess=(lambda m: m.group(0).upper() if m else None)(_LEVEL_RE.search(title)),
        bid_date=kv("Bid Date"),
        estimator=kv("Estimator"),
        market_sector=kv("Market Sector"),
        status=kv("Status"),
        product_code=product_code,
        product_name=product_name,
        density=density,
        base=base,
        report_variant=variant,
        designs=designs,
        items=items,
        table_page=page_index + 1,
        plan_page=None,
        plan_image_count=0,
    )
    # --- QA: same swatch used for different thickness/section within a sheet
    # (a linear swatch and an area hatch of the same colour are distinguishable on the plan,
    # so the key includes the section)
    seen: dict[tuple[str, str, str], SprayItem] = {}
    for it in items:
        if it.swatch is None:
            continue
        k = (it.section, it.swatch.rgb_hex, it.swatch.pattern)
        prev = seen.get(k)
        if prev is not None and (prev.thickness_in != it.thickness_in or prev.sides != it.sides):
            rep.qa_notes.append(
                f"colour {k[1]} {k[2]} reused within {it.section} items: {prev.member_label} "
                f"({prev.thickness_display}) and {it.member_label} ({it.thickness_display}) "
                "— plan legend is ambiguous"
            )
        seen.setdefault(k, it)
    if not designs:
        rep.qa_notes.append("no listed design printed for this sheet")
    return rep


def parse_spray_report(path: str | Path) -> SprayReport:
    path = Path(path)
    doc = pymupdf.open(path)
    meta = doc.metadata or {}
    sheets: list[SheetReport] = []
    pending: SheetReport | None = None
    for i, page in enumerate(doc):
        rep = _parse_table_page(page, i)
        if rep is not None:
            sheets.append(rep)
            pending = rep
            continue
        imgs = page.get_images(full=True)
        if imgs and pending is not None and pending.plan_page is None:
            pending.plan_page = i + 1
            pending.plan_image_count = len(imgs)
    doc.close()
    return SprayReport(
        source=path.name,
        pdf_title=meta.get("title") or None,
        pdf_author=meta.get("author") or None,
        created=meta.get("creationDate") or None,
        sheets=sheets,
    )


def extract_plan_images(path: str | Path, out_dir: str | Path) -> list[Path]:
    """Stitch each plan page's raster strips (top-to-bottom) into one PNG per sheet."""
    path, out_dir = Path(path), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rep = parse_spray_report(path)
    doc = pymupdf.open(path)
    written: list[Path] = []
    for sh in rep.sheets:
        if sh.plan_page is None:
            continue
        page = doc[sh.plan_page - 1]
        strips = []
        for img in page.get_images(full=True):
            rects = page.get_image_rects(img[0])
            if not rects:
                continue
            pix = pymupdf.Pixmap(doc, img[0])
            if pix.n - pix.alpha >= 4:
                pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
            strips.append((rects[0].y0, pix))
        if not strips:
            continue
        strips.sort(key=lambda t: t[0])
        width = max(p.width for _, p in strips)
        height = sum(p.height for _, p in strips)
        canvas = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, width, height), False)
        canvas.clear_with(255)
        y = 0
        for _, p in strips:
            if p.alpha:
                p = pymupdf.Pixmap(p, 0)
            p.set_origin(0, y)
            canvas.copy(p, pymupdf.IRect(0, y, p.width, y + p.height))
            y += p.height
        out = out_dir / f"{sh.sheet_no}_plan.png"
        canvas.save(out)
        written.append(out)
    doc.close()
    return written


def write_outputs(rep: SprayReport, out_dir: str | Path) -> None:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "spray_report.json").write_text(
        json.dumps(rep.to_dict(), indent=1, ensure_ascii=False)
    )
    import csv

    with (out_dir / "spray_items.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "sheet_no",
                "title",
                "level_guess",
                "product_code",
                "designs",
                "section",
                "member_label",
                "canonical_section",
                "role",
                "sides",
                "thickness_in",
                "thickness_display",
                "unit",
                "consistent",
                "color",
                "pattern",
                "notes",
            ]
        )
        for sh in rep.sheets:
            dz = "; ".join(d["as_printed"] for d in sh.designs)
            for it in sh.items:
                w.writerow(
                    [
                        sh.sheet_no,
                        sh.title,
                        sh.level_guess,
                        sh.product_code,
                        dz,
                        it.section,
                        it.member_label,
                        it.canonical_section,
                        it.role,
                        it.sides,
                        it.thickness_in,
                        it.thickness_display,
                        it.thickness_unit,
                        it.thickness_consistent,
                        it.swatch.rgb_hex if it.swatch else "",
                        it.swatch.pattern if it.swatch else "",
                        " | ".join(it.notes),
                    ]
                )
