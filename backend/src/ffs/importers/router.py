"""Content-based dispatch for reference PDFs: UL Product iQ printouts, Isolatek charts, other.

Manufacturer sites file UL printouts and their own charts in the same folders, so the file path
is not a reliable signal. The first page's text is.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class RouteResult:
    path: str
    kind: str  # ul_design / isolatek_chart / chart_xref / design_text / scanned / error
    design: str | None
    rows: int
    tables: int
    equations: int
    notes: int
    out: str | None
    error: str | None = None


def sniff(path: str | Path) -> tuple[str, str]:
    import pymupdf

    doc = pymupdf.open(path)
    try:
        first = doc[0].get_text("text") if len(doc) else ""
        all_text = first if len(doc) == 1 else first + "\n" + doc[1].get_text("text")
    finally:
        doc.close()
    if not first.strip():
        return "scanned", first
    if re.search(r"UL Product iQ|BXUV\.[A-Z]{1,3}-?\d{3,4}|Design No\.\s*[A-Z]", first):
        from ffs.importers.ul_design import find_design_no

        # a UL design printout carries a BXUV design number (X649, N653, ...); a UL certificate
        # or notice that merely mentions "Design No." or Product iQ does not, and is not a design
        if find_design_no(all_text):
            return "ul_design", all_text
        return "other", all_text
    if re.search(r"Use Design\s+[A-Z]{1,2}-?\d{3,4}", first):
        return "chart_xref", all_text
    if re.search(
        r"(?:ASTM|AISC)\s*Desig|Joist\s*\n\s*Designation|\d-Hour|Hour\s*$", first, re.MULTILINE
    ) and re.search(r"CAFCO|ISOLATEK|Albi\s*DriClad", first):
        return "isolatek_chart", all_text
    if re.search(r"Design No\.|Rating", first) and re.search(r"ISOLATEK|CAFCO", first):
        return "design_text", all_text
    return "other", all_text


def route_file(path: str | Path, out_dir: str | Path) -> RouteResult:
    from ffs.importers.isolatek_chart import parse_chart_pdf, write_chart
    from ffs.importers.ul_design import parse_design_pdf, write_record

    path = Path(path)
    out_dir = Path(out_dir)
    try:
        kind, _ = sniff(path)
    except Exception as ex:  # noqa: BLE001
        return RouteResult(
            str(path), "error", None, 0, 0, 0, 0, None, f"{type(ex).__name__}: {ex}"[:200]
        )
    try:
        if kind == "ul_design":
            rec = parse_design_pdf(path)
            p = write_record(rec, out_dir / "ul_designs")
            rows = sum(len(t.rows) for t in rec.tables)
            return RouteResult(
                str(path),
                kind,
                rec.design_no,
                rows,
                len(rec.tables),
                len(rec.equations),
                len(rec.unparsed),
                str(p),
            )
        if kind in ("isolatek_chart", "chart_xref"):
            rec = parse_chart_pdf(path)
            rec.source_file = path.parent.name + "__" + path.name
            p = write_chart(rec, out_dir / "charts")
            k = "chart_xref" if (not rec.rows and rec.cross_reference_designs) else kind
            return RouteResult(
                str(path),
                k,
                rec.design,
                len(rec.rows),
                1 if rec.rows else 0,
                0,
                len(rec.notes),
                str(p),
            )
        return RouteResult(str(path), kind, None, 0, 0, 0, 0, None)
    except Exception as ex:  # noqa: BLE001
        return RouteResult(
            str(path), "error", None, 0, 0, 0, 0, None, f"{type(ex).__name__}: {ex}"[:200]
        )


def route_manifest(
    manifest: str | Path, library: str | Path, out_dir: str | Path, url_filter: str = ""
) -> list[RouteResult]:
    manifest, library, out_dir = Path(manifest), Path(library), Path(out_dir)
    stored: dict[str, dict] = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if r.get("status") in ("fetched", "unchanged") and r.get("stored_path") and r.get("url"):
            stored[r["url"]] = r
    results = []
    for url, r in sorted(stored.items()):
        if url_filter and url_filter not in url:
            continue
        if not r["stored_path"].lower().endswith(".pdf"):
            continue
        res = route_file(library / r["stored_path"], out_dir)
        res.path = url
        results.append(res)
    (out_dir / "route_report.jsonl").parent.mkdir(parents=True, exist_ok=True)
    with (out_dir / "route_report.jsonl").open("w", encoding="utf-8") as f:
        for res in results:
            f.write(json.dumps(asdict(res)) + "\n")
    return results
