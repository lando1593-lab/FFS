"""Coverage report over the fetched + parsed reference library.

Answers "what do we actually hold?" per manufacturer: documents fetched, how the router
classified them, which UL designs parsed with thickness tables or equations and which did
not, and how many chart rows exist per product line. Everything is counted from the files
on disk (manifest, route report, parsed JSON); nothing is inferred.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from urllib.parse import urlparse


@dataclass
class ManufacturerCoverage:
    manufacturer: str
    documents: int = 0
    by_kind: dict[str, int] = field(default_factory=dict)
    designs_with_tables: list[str] = field(default_factory=list)
    designs_without_tables: list[str] = field(default_factory=list)
    chart_designs: list[str] = field(default_factory=list)
    chart_rows: int = 0
    charts_without_rows: list[str] = field(default_factory=list)
    rows_by_product: dict[str, int] = field(default_factory=dict)
    cross_reference_designs: list[str] = field(default_factory=list)


def _read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _manufacturer_for(url: str, stored_path: str | None) -> str:
    if stored_path and "/" in stored_path:
        return stored_path.split("/", 1)[0]
    host = urlparse(url).netloc.lower()
    return host.removeprefix("www.") or "unknown"


def build_coverage(library: str | Path, parsed: str | Path) -> dict[str, ManufacturerCoverage]:
    library, parsed = Path(library), Path(parsed)
    manifest = _read_jsonl(library / "manifest.jsonl")
    stored: dict[str, dict] = {}
    for r in manifest:
        if (
            r.get("status") in ("fetched", "unchanged", "manual")
            and r.get("url")
            and r.get("stored_path")
        ):
            stored[r["url"]] = r
    report: dict[str, ManufacturerCoverage] = {}
    for url, r in stored.items():
        m = _manufacturer_for(url, r.get("stored_path"))
        report.setdefault(m, ManufacturerCoverage(m)).documents += 1

    with_tables: dict[str, set[str]] = defaultdict(set)
    without_tables: dict[str, set[str]] = defaultdict(set)
    chart_designs: dict[str, set[str]] = defaultdict(set)
    xref: dict[str, set[str]] = defaultdict(set)
    kinds: dict[str, Counter] = defaultdict(Counter)
    products: dict[str, Counter] = defaultdict(Counter)

    for res in _read_jsonl(parsed / "route_report.jsonl"):
        url = res.get("path") or ""
        m = _manufacturer_for(url, stored.get(url, {}).get("stored_path"))
        cov = report.setdefault(m, ManufacturerCoverage(m))
        kind = res.get("kind") or "unknown"
        kinds[m][kind] += 1
        design = res.get("design")
        if kind == "ul_design" and design:
            if res.get("tables") or res.get("equations"):
                with_tables[m].add(design)
            else:
                without_tables[m].add(design)
        elif kind == "isolatek_chart":
            rows = int(res.get("rows") or 0)
            cov.chart_rows += rows
            if rows == 0:
                cov.charts_without_rows.append(url.rsplit("/", 1)[-1])
            if design:
                chart_designs[m].add(design)
            out = res.get("out")
            if out and Path(out).exists():
                try:
                    chart = json.loads(Path(out).read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    chart = {}
                prod = chart.get("products")
                if isinstance(prod, list):
                    prod = " / ".join(prod)
                products[m][prod or "(product line not printed on chart)"] += rows
        elif kind == "chart_xref":
            out = res.get("out")
            if out and Path(out).exists():
                try:
                    chart = json.loads(Path(out).read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    chart = {}
                for d in chart.get("cross_reference_designs") or []:
                    xref[m].add(str(d))
            if design:
                chart_designs[m].add(design)

    for m, cov in report.items():
        cov.by_kind = dict(sorted(kinds[m].items()))
        # a design counts as "with tables" if any of its printouts parsed with tables
        cov.designs_with_tables = sorted(with_tables[m])
        cov.designs_without_tables = sorted(without_tables[m] - with_tables[m])
        cov.chart_designs = sorted(chart_designs[m])
        cov.rows_by_product = dict(products[m].most_common())
        cov.cross_reference_designs = sorted(xref[m])
    return report


def render_markdown(report: dict[str, ManufacturerCoverage]) -> str:
    head = (
        "| Manufacturer | Documents | Routed | UL designs with tables/equations "
        "| UL designs without | Charts: designs / rows |"
    )
    lines = [head]
    lines.append("|---|---|---|---|---|---|")
    for m in sorted(report):
        c = report[m]
        routed = ", ".join(f"{k} {v}" for k, v in c.by_kind.items()) or "—"
        lines.append(
            f"| {m} | {c.documents} | {routed} | {len(c.designs_with_tables)} | "
            f"{len(c.designs_without_tables)} | {len(c.chart_designs)} / {c.chart_rows} |"
        )
    for m in sorted(report):
        c = report[m]
        lines.append("")
        lines.append(f"### {m}")
        if c.designs_with_tables:
            lines.append(
                f"- UL designs with tables or equations: {', '.join(c.designs_with_tables)}"
            )
        if c.designs_without_tables:
            without = ", ".join(c.designs_without_tables)
            lines.append(f"- UL designs parsed without tables or equations: {without}")
        if c.chart_designs:
            lines.append(f"- Chart designs: {', '.join(c.chart_designs)}")
        if c.cross_reference_designs:
            lines.append(f"- Cross-reference targets: {', '.join(c.cross_reference_designs)}")
        for prod, n in c.rows_by_product.items():
            lines.append(f"- {n} chart rows: {prod}")
        if c.charts_without_rows:
            lines.append(f"- Charts with no rows parsed: {', '.join(c.charts_without_rows)}")
    return "\n".join(lines) + "\n"


def write_coverage(
    report: dict[str, ManufacturerCoverage], out_dir: str | Path
) -> tuple[Path, Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    js = out_dir / "coverage.json"
    md = out_dir / "coverage.md"
    js.write_text(
        json.dumps({m: asdict(c) for m, c in sorted(report.items())}, indent=2), encoding="utf-8"
    )
    md.write_text(render_markdown(report), encoding="utf-8")
    return js, md
