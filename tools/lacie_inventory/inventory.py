#!/usr/bin/env python3
"""LaCie reference-library inventory — READ ONLY.

Walks a library root, opens every file read-only, and writes a catalog OUTSIDE the library:
  <out>/catalog.sqlite   full catalog (one row per file + classification + extracted hints)
  <out>/catalog.jsonl    same rows, one JSON object per line
  <out>/catalog.csv      flat summary for Excel
  <out>/summary.md       counts by document type, manufacturer, decade, top folders, and a
                         list of files the classifier could not place

Safety:
  * Never writes inside the library root (refuses an --out path under it).
  * Opens files with read-only handles; never renames, moves, touches mtimes, or deletes.
  * Stores at most a short text snippet per file (default 600 chars) — no full-text copies.

Classification is heuristic keyword scoring with a confidence in [0, 1]. It is a *map* of the
library for humans to review; it is never an authority on current code or product compliance
(ADR-0004).

Usage:
  python inventory.py --find                       # list candidate LaCie mount points
  python inventory.py /Volumes/LaCie --out ./out   # inventory (macOS)
  python inventory.py E:\\ --out .\\out               # inventory (Windows)
  python inventory.py <root> --out ./out --max-files 500 --dry-run
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sqlite3
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------------------------
# Domain vocab (keywords only; nothing here is a thickness/design value)
# ---------------------------------------------------------------------------------------------
MANUFACTURERS = {
    "isolatek": ["isolatek", "cafco", "blaze-shield", "blaze shield", "fendolite", "sprayfilm"],
    "gcp/grace": ["monokote", "mk-6", "mk6", "z-146", "z146", "z-156", "z156", "z-106", "w.r. grace", "grace construction", "gcp applied"],
    "carboline": ["carboline", "pyrocrete", "pyrolite", "thermo-sorb", "thermosorb", "thermo-lag", "pyroclad", "southwest type"],
    "sherwin-williams": ["firetex", "sherwin"],
    "ppg": ["pitt-char", "steelguard", "ppg "],
    "akzonobel/international": ["interchar", "chartek", "akzo", "international paint"],
    "hilti": ["hilti", "cfp-sp"],
    "nullifire": ["nullifire"],
    "promat": ["promat"],
    "hempel": ["hempel"],
    "jotun": ["jotun", "steelmaster"],
}
DOC_TYPES = {
    "ul_design": ["bxuv", "design no", "design number", "fire resistance rating", "restrained assembly rating", "unrestrained beam rating", "ul 263", "astm e119"],
    "thickness_chart": ["thickness", "w/d", "heated perimeter", "thickness schedule", "thickness table"],
    "spray_chart": ["spray chart", "color up", "color-up", "spray schedule", "fireproofing schedule"],
    "shop_drawing": ["shop drawing", "fireproofing plan", "fp-", "fp1.", "fp2.", "legend", "key plan"],
    "submittal": ["submittal", "transmittal", "approved as noted", "revise and resubmit", "no exceptions taken", "reviewed"],
    "product_data": ["product data", "data sheet", "technical data", "pds", "tds", "physical properties", "packaging"],
    "sds": ["safety data sheet", "sds", "msds", "hazard"],
    "specification": ["section 07 81", "07 81 00", "07 81 16", "07 81 23", "078100", "078116", "078123", "07810", "sprayed fire-resistive", "part 1 - general", "part 2 - products"],
    "estimate": ["estimate", "takeoff", "take-off", "bid", "proposal", "recap", "board feet", "bd ft", "bags", "unit price"],
    "application_guide": ["application guide", "application instructions", "applicator", "mixing", "pump"],
    "yield_chart": ["yield", "coverage", "bd ft/bag", "board feet per bag", "sq ft per gallon"],
    "technical_bulletin": ["technical bulletin", "bulletin", "technical note"],
    "field_drawing": ["field", "foreman", "crew", "no spray", "do not spray"],
    "inspection": ["inspection", "astm e605", "e605", "density", "bond", "cohesion", "adhesion", "special inspection"],
    "structural_drawing": ["framing plan", "beam schedule", "column schedule", "structural", "s-1", "s-2", "s1.", "s2."],
    "architectural_drawing": ["floor plan", "reflected ceiling", "wall section", "finish schedule", "code summary", "a-1", "a1."],
    "correspondence": ["dear", "regards", "re:", "rfi", "request for information", "change order"],
}
RATING_RE = re.compile(r"\b([1-4])\s*-?\s*(?:hr|hour)s?\b", re.IGNORECASE)
UL_DESIGN_RE = re.compile(r"\b(?:BXUV\.)?([DNPSXYGJKAL]-?\d{3,4}|XR-?\d{3})\b")
UL_DESIGN_LOOSE_RE = re.compile(r"design\s*(?:no\.?|number|#)?\s*:?\s*([A-Z]{1,2}-?\d{3,4})", re.IGNORECASE)
YEAR_RE = re.compile(r"\b(19[89]\d|20[0-4]\d)\b")
DATE_RE = re.compile(r"\b(\d{1,2}[/-]\d{1,2}[/-](?:19|20)?\d{2})\b|\b((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{4})\b", re.IGNORECASE)
MEMBER_RE = re.compile(r"\b(W\d{1,2}X\d{1,3}|HSS\d|WT\d|C\d{1,2}X|L\d(?:X|-)|PIPE|JOIST|GIRDER|COLUMN|BEAM|DECK)\b", re.IGNORECASE)
FP_TYPE = {
    "sfrm": ["sfrm", "spray-applied", "spray applied", "cementitious", "fibrous", "monokote", "cafco", "blaze-shield", "pyrocrete"],
    "intumescent": ["intumescent", "thin film", "thin-film", "dft", "mils", "firetex", "interchar", "thermo-sorb", "sprayfilm", "pyroclad"],
    "board/other": ["board", "wrap", "mineral wool", "gypsum", "membrane"],
}
PROJECT_HINT_RE = re.compile(r"\b(project|job)\s*(?:name|no\.?|number|#)?\s*:?\s*([A-Za-z0-9][^\n]{3,60})", re.IGNORECASE)

TEXT_EXT = {".txt", ".csv", ".md", ".rtf"}
PDF_EXT = {".pdf"}
XLS_EXT = {".xlsx", ".xlsm", ".xls"}
DOC_EXT = {".docx", ".doc"}
IMG_EXT = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".gif", ".heic"}
CAD_EXT = {".dwg", ".dxf", ".dwf", ".rvt", ".ifc", ".skp"}
SKIP_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini", ".Spotlight-V100", ".Trashes", ".fseventsd", "$RECYCLE.BIN", "System Volume Information"}


@dataclass
class Entry:
    path: str
    rel_path: str
    folder: str
    filename: str
    ext: str
    size_bytes: int
    mtime_iso: str
    sha256: str | None
    file_class: str  # pdf / excel / word / image / cad / text / other
    pages: int | None = None
    has_text_layer: bool | None = None
    likely_scanned: bool | None = None
    title_meta: str | None = None
    author_meta: str | None = None
    created_meta: str | None = None
    snippet: str = ""
    doc_type: str = "unclassified"
    doc_type_confidence: float = 0.0
    doc_type_scores: dict[str, int] = field(default_factory=dict)
    manufacturer: str | None = None
    products: list[str] = field(default_factory=list)
    fireproofing_type: str | None = None
    ratings: list[str] = field(default_factory=list)
    ul_designs: list[str] = field(default_factory=list)
    member_terms: list[str] = field(default_factory=list)
    years_seen: list[int] = field(default_factory=list)
    dates_seen: list[str] = field(default_factory=list)
    project_hint: str | None = None
    current_or_historical: str = "historical"  # everything on the drive defaults to historical
    error: str | None = None


# ---------------------------------------------------------------------------------------------
def find_candidate_mounts() -> list[str]:
    cands: list[str] = []
    roots = ["/Volumes", "/media", "/mnt", "/run/media"]
    for r in roots:
        p = Path(r)
        if p.is_dir():
            for child in p.iterdir():
                try:
                    if child.is_dir():
                        cands.append(str(child))
                except OSError:
                    pass
            for child in p.glob("*/*"):
                try:
                    if child.is_dir() and "lacie" in child.name.lower():
                        cands.append(str(child))
                except OSError:
                    pass
    if os.name == "nt":
        import string

        for letter in string.ascii_uppercase:
            d = f"{letter}:\\"
            if os.path.exists(d):
                cands.append(d)
    lacie = [c for c in cands if "lacie" in c.lower()]
    return lacie + [c for c in cands if c not in lacie]


def sha256_of(path: Path, limit_mb: int) -> str | None:
    h = hashlib.sha256()
    try:
        with path.open("rb") as f:
            read = 0
            while True:
                chunk = f.read(1 << 20)
                if not chunk:
                    break
                h.update(chunk)
                read += len(chunk)
                if limit_mb and read > limit_mb << 20:
                    return "partial:" + h.hexdigest()
        return h.hexdigest()
    except OSError:
        return None


def read_pdf(path: Path, e: Entry, max_pages: int, snippet_len: int) -> str:
    import pymupdf

    text_parts: list[str] = []
    with path.open("rb") as f:
        data = f.read()
    doc = pymupdf.open(stream=data, filetype="pdf")
    try:
        e.pages = len(doc)
        meta = doc.metadata or {}
        e.title_meta = (meta.get("title") or None) or None
        e.author_meta = (meta.get("author") or None) or None
        e.created_meta = (meta.get("creationDate") or None) or None
        text_pages = 0
        img_heavy = 0
        for i in range(min(len(doc), max_pages)):
            pg = doc[i]
            t = pg.get_text("text") or ""
            if t.strip():
                text_pages += 1
            if pg.get_images():
                img_heavy += 1
            text_parts.append(t)
        e.has_text_layer = text_pages > 0
        e.likely_scanned = text_pages == 0 and img_heavy > 0
    finally:
        doc.close()
    full = "\n".join(text_parts)
    e.snippet = re.sub(r"\s+", " ", full)[:snippet_len]
    return full


def read_xlsx(path: Path, e: Entry, snippet_len: int) -> str:
    import openpyxl

    with path.open("rb") as f:
        data = f.read()
    import io

    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    parts: list[str] = []
    try:
        e.pages = len(wb.sheetnames)
        e.title_meta = "; ".join(wb.sheetnames)[:200]
        for name in wb.sheetnames[:12]:
            ws = wb[name]
            parts.append(name)
            for r, row in enumerate(ws.iter_rows(values_only=True)):
                if r >= 60:
                    break
                parts.append(" ".join(str(v) for v in row if v is not None))
    finally:
        wb.close()
    full = "\n".join(parts)
    e.snippet = re.sub(r"\s+", " ", full)[:snippet_len]
    return full


def read_docx(path: Path, e: Entry, snippet_len: int) -> str:
    try:
        import docx  # python-docx
    except ImportError:
        e.error = "python-docx not installed; docx text skipped"
        return ""
    import io

    with path.open("rb") as f:
        data = f.read()
    d = docx.Document(io.BytesIO(data))
    parts = [p.text for p in d.paragraphs[:400]]
    for t in d.tables[:10]:
        for row in t.rows[:40]:
            parts.append(" ".join(c.text for c in row.cells))
    full = "\n".join(parts)
    e.snippet = re.sub(r"\s+", " ", full)[:snippet_len]
    return full


def classify(e: Entry, text: str) -> None:
    hay = (e.filename + "\n" + e.folder + "\n" + text).lower()
    scores: dict[str, int] = {}
    for dt, kws in DOC_TYPES.items():
        s = 0
        for kw in kws:
            n = hay.count(kw)
            if n:
                s += min(n, 5) + (3 if kw in e.filename.lower() else 0)
        if s:
            scores[dt] = s
    e.doc_type_scores = dict(sorted(scores.items(), key=lambda kv: -kv[1])[:5])
    if scores:
        best, bs = max(scores.items(), key=lambda kv: kv[1])
        second = sorted(scores.values(), reverse=True)[1] if len(scores) > 1 else 0
        e.doc_type = best
        e.doc_type_confidence = round(min(0.95, 0.4 + 0.1 * bs - 0.05 * second), 2)
        if e.doc_type_confidence < 0.45:
            e.doc_type = "unclassified"
    for mf, kws in MANUFACTURERS.items():
        hits = [kw for kw in kws if kw in hay]
        if hits:
            if e.manufacturer is None:
                e.manufacturer = mf
            e.products.extend(h for h in hits if h not in e.products)
    for ft, kws in FP_TYPE.items():
        if any(kw in hay for kw in kws):
            e.fireproofing_type = ft if e.fireproofing_type is None else e.fireproofing_type
    e.ratings = sorted({f"{m.group(1)} HR" for m in RATING_RE.finditer(text)})[:8]
    designs = {m.group(1).upper().replace("-", "") for m in UL_DESIGN_RE.finditer(text)}
    designs |= {m.group(1).upper().replace("-", "") for m in UL_DESIGN_LOOSE_RE.finditer(text)}
    e.ul_designs = sorted(designs)[:30]
    e.member_terms = sorted({m.group(1).upper() for m in MEMBER_RE.finditer(text)})[:20]
    e.years_seen = sorted({int(y) for y in YEAR_RE.findall(text)})[:12]
    e.dates_seen = sorted({(a or b) for a, b in DATE_RE.findall(text)})[:8]
    m = PROJECT_HINT_RE.search(text)
    if m:
        e.project_hint = m.group(2).strip()[:80]


def inventory(root: Path, out: Path, max_files: int | None, hash_limit_mb: int, max_pages: int,
              snippet_len: int, dry_run: bool) -> list[Entry]:
    entries: list[Entry] = []
    n = 0
    t0 = time.time()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_NAMES and not d.startswith(".")]
        for fn in filenames:
            if fn in SKIP_NAMES or fn.startswith("._") or fn.startswith("~$"):
                continue
            p = Path(dirpath) / fn
            if max_files and n >= max_files:
                return entries
            n += 1
            try:
                st = p.stat()
            except OSError as ex:
                entries.append(Entry(str(p), str(p.relative_to(root)), str(Path(dirpath).relative_to(root)), fn,
                                     p.suffix.lower(), 0, "", None, "other", error=str(ex)))
                continue
            ext = p.suffix.lower()
            fclass = ("pdf" if ext in PDF_EXT else "excel" if ext in XLS_EXT else "word" if ext in DOC_EXT
                      else "image" if ext in IMG_EXT else "cad" if ext in CAD_EXT else "text" if ext in TEXT_EXT else "other")
            e = Entry(
                path=str(p), rel_path=str(p.relative_to(root)), folder=str(Path(dirpath).relative_to(root)),
                filename=fn, ext=ext, size_bytes=st.st_size,
                mtime_iso=datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
                sha256=None if dry_run else sha256_of(p, hash_limit_mb), file_class=fclass,
            )
            text = ""
            if not dry_run:
                try:
                    if fclass == "pdf":
                        text = read_pdf(p, e, max_pages, snippet_len)
                    elif fclass == "excel" and ext != ".xls":
                        text = read_xlsx(p, e, snippet_len)
                    elif fclass == "word" and ext == ".docx":
                        text = read_docx(p, e, snippet_len)
                    elif fclass == "text":
                        with p.open("rb") as f:
                            text = f.read(200_000).decode("utf-8", "ignore")
                        e.snippet = re.sub(r"\s+", " ", text)[:snippet_len]
                except Exception as ex:  # noqa: BLE001 - we want the inventory to keep going
                    e.error = f"{type(ex).__name__}: {ex}"[:300]
            classify(e, text)
            entries.append(e)
            if n % 50 == 0:
                print(f"  {n} files, {time.time() - t0:.0f}s, last: {e.rel_path[:70]}", file=sys.stderr)
    return entries


def write_outputs(entries: list[Entry], out: Path, root: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    with (out / "catalog.jsonl").open("w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(asdict(e), ensure_ascii=False) + "\n")
    cols = ["rel_path", "filename", "ext", "file_class", "size_bytes", "mtime_iso", "pages", "has_text_layer",
            "likely_scanned", "doc_type", "doc_type_confidence", "manufacturer", "fireproofing_type", "ratings",
            "ul_designs", "years_seen", "project_hint", "title_meta", "sha256", "error"]
    with (out / "catalog.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for e in entries:
            d = asdict(e)
            w.writerow([("; ".join(map(str, d[c])) if isinstance(d[c], list) else d[c]) for c in cols])
    db = out / "catalog.sqlite"
    if db.exists():
        db.unlink()
    con = sqlite3.connect(db)
    con.execute(
        "CREATE TABLE files (rel_path TEXT PRIMARY KEY, filename TEXT, folder TEXT, ext TEXT, file_class TEXT, "
        "size_bytes INTEGER, mtime_iso TEXT, sha256 TEXT, pages INTEGER, has_text_layer INTEGER, likely_scanned INTEGER, "
        "title_meta TEXT, author_meta TEXT, created_meta TEXT, snippet TEXT, doc_type TEXT, doc_type_confidence REAL, "
        "doc_type_scores TEXT, manufacturer TEXT, products TEXT, fireproofing_type TEXT, ratings TEXT, ul_designs TEXT, "
        "member_terms TEXT, years_seen TEXT, dates_seen TEXT, project_hint TEXT, current_or_historical TEXT, error TEXT)"
    )
    con.executemany(
        "INSERT OR REPLACE INTO files VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [(e.rel_path, e.filename, e.folder, e.ext, e.file_class, e.size_bytes, e.mtime_iso, e.sha256, e.pages,
          e.has_text_layer, e.likely_scanned, e.title_meta, e.author_meta, e.created_meta, e.snippet, e.doc_type,
          e.doc_type_confidence, json.dumps(e.doc_type_scores), e.manufacturer, json.dumps(e.products),
          e.fireproofing_type, json.dumps(e.ratings), json.dumps(e.ul_designs), json.dumps(e.member_terms),
          json.dumps(e.years_seen), json.dumps(e.dates_seen), e.project_hint, e.current_or_historical, e.error)
         for e in entries],
    )
    con.commit()
    con.close()

    def count(key):
        c: dict[str, int] = {}
        for e in entries:
            v = key(e) or "(none)"
            c[v] = c.get(v, 0) + 1
        return sorted(c.items(), key=lambda kv: -kv[1])

    lines = [f"# LaCie library inventory — {datetime.now():%Y-%m-%d %H:%M}", "",
             f"Root: `{root}`  Files: {len(entries)}  Total size: {sum(e.size_bytes for e in entries) / 1e9:.2f} GB", "",
             "## By file class", *[f"- {k}: {v}" for k, v in count(lambda e: e.file_class)], "",
             "## By document type (heuristic)", *[f"- {k}: {v}" for k, v in count(lambda e: e.doc_type)], "",
             "## By manufacturer (keyword hit)", *[f"- {k}: {v}" for k, v in count(lambda e: e.manufacturer)], "",
             "## By fireproofing type", *[f"- {k}: {v}" for k, v in count(lambda e: e.fireproofing_type)], "",
             "## By earliest year mentioned", *[f"- {k}: {v}" for k, v in sorted(count(lambda e: str(e.years_seen[0] // 10 * 10) + "s" if e.years_seen else None))], "",
             "## Top folders", *[f"- {k}: {v}" for k, v in count(lambda e: e.folder.split(os.sep)[0] if e.folder else "(root)")[:40]], "",
             "## Scanned PDFs (no text layer) — OCR candidates", f"- {sum(1 for e in entries if e.likely_scanned)}", "",
             "## Errors", *[f"- {e.rel_path}: {e.error}" for e in entries if e.error][:100], "",
             "## Unclassified (first 200)", *[f"- {e.rel_path}" for e in entries if e.doc_type == 'unclassified'][:200]]
    (out / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", nargs="?", help="library root (the LaCie mount or a folder on it)")
    ap.add_argument("--out", default="./out", help="output directory (must be OUTSIDE the root)")
    ap.add_argument("--find", action="store_true", help="list candidate mount points and exit")
    ap.add_argument("--max-files", type=int, default=None)
    ap.add_argument("--hash-limit-mb", type=int, default=256, help="hash only the first N MB of large files (0 = all)")
    ap.add_argument("--max-pages", type=int, default=4, help="PDF pages to read for classification")
    ap.add_argument("--snippet", type=int, default=600, help="max chars of text snippet stored per file")
    ap.add_argument("--dry-run", action="store_true", help="walk and stat only; do not open file contents")
    a = ap.parse_args()
    if a.find:
        for c in find_candidate_mounts():
            print(c)
        return 0
    if not a.root:
        ap.error("root is required (or use --find)")
    root = Path(a.root).resolve()
    out = Path(a.out).resolve()
    if not root.is_dir():
        print(f"root is not a directory: {root}", file=sys.stderr)
        return 2
    if out == root or root in out.parents:
        print(f"refusing to write output inside the library root: {out}", file=sys.stderr)
        return 2
    print(f"inventorying {root} (read-only) → {out}", file=sys.stderr)
    entries = inventory(root, out, a.max_files, a.hash_limit_mb, a.max_pages, a.snippet, a.dry_run)
    write_outputs(entries, out, root)
    print(f"done: {len(entries)} files. See {out / 'summary.md'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
