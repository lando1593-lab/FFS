"""``ffs`` command line — the Phase 0 / Milestone 1 vertical slice."""

from __future__ import annotations

import json
from pathlib import Path

import typer

app = typer.Typer(no_args_is_help=True, help="FFS fireproofing takeoff platform — M1 tools")
golden_app = typer.Typer(help="Golden project tools")
app.add_typer(golden_app, name="golden")


@app.command()
def inspect(
    pdf: Path, pages: str = typer.Option(None, help="1-based page list, e.g. 1,3-5")
) -> None:
    """Report per-page text/vector/scan status, sheet number, level, scale candidates, grids."""
    from ffs.ingest.pdf import load_pdf
    from ffs.takeoff.pipeline import detect_sheet_info

    idxs = _parse_pages(pages)
    for pg in load_pdf(pdf, idxs):
        info = detect_sheet_info(pg)
        typer.echo(
            f"p{pg.page_number}: {pg.width:.0f}x{pg.height:.0f}pt rot={pg.rotation} "
            f"spans={len(pg.spans)} segments={len(pg.segments)} circles={len(pg.circles)} "
            f"img={pg.image_coverage:.0%} path={pg.extraction_path.value}"
            f"{' LIKELY SCANNED' if pg.likely_scanned else ''}"
        )
        typer.echo(
            f"   sheet={info.sheet_no} level={info.level} ({info.level_confidence:.2f}) title={info.title!r}"
        )
        for sc in info.scale_candidates:
            flag = " <chosen>" if info.scale is sc else ""
            typer.echo(
                f"   scale {sc.label} conf={sc.confidence:.2f} src={sc.source} ev={sc.evidence!r}{flag}"
            )
        typer.echo(
            f"   grids: {', '.join(g.label + ('|' if g.axis == 'x' else '—') for g in info.grids) or 'none'}"
        )
        for n in info.notes:
            typer.echo(f"   ! {n}")


@app.command()
def takeoff(
    pdf: Path,
    out: Path = typer.Option(Path("out"), help="output directory"),
    pages: str = typer.Option(None, help="1-based page list"),
    scale: str = typer.Option(None, help="override scale, e.g. '1/8\"=1'-0\"'"),
    level: str = typer.Option(None, help="override level for all pages"),
    aisc: Path = typer.Option(None, help="AISC shapes database .xlsx/.csv"),
    overlay: bool = typer.Option(True, help="write overlay PDFs"),
    db: str = typer.Option(None, help="SQLAlchemy URL to persist, e.g. sqlite:///project.sqlite"),
) -> None:
    """Run the structural takeoff: members, counts, LF, CSV/XLSX/JSON, overlay PDFs."""
    from ffs.ingest.pdf import load_pdf
    from ffs.render.overlay import write_overlay
    from ffs.steel.aisc import ShapeDatabase
    from ffs.takeoff.aggregate import summarize, write_members_csv, write_summary_csv, write_xlsx
    from ffs.takeoff.pipeline import run_page

    out.mkdir(parents=True, exist_ok=True)
    shapes = ShapeDatabase.load(aisc)
    if shapes is None:
        typer.secho(
            "no AISC shape database loaded — identification confidence capped at 0.90", fg="yellow"
        )
    all_members = []
    report = {"document": pdf.name, "pages": []}
    for pg in load_pdf(pdf, _parse_pages(pages)):
        info, members, labels = run_page(pg, shapes, scale, level)
        all_members.extend(members)
        ctx = {}
        for lab in labels:
            ctx[lab.context.value] = ctx.get(lab.context.value, 0) + 1
        report["pages"].append(
            {
                "page": pg.page_number,
                "sheet_no": info.sheet_no,
                "level": info.level,
                "scale": None
                if info.scale is None
                else {
                    "label": info.scale.label,
                    "source": info.scale.source,
                    "confidence": info.scale.confidence,
                },
                "grids": [g.label for g in info.grids],
                "label_contexts": ctx,
                "members": len(members),
                "needs_review": sum(1 for m in members if m.needs_review),
                "notes": info.notes,
                "extraction_path": pg.extraction_path.value,
            }
        )
        if overlay:
            write_overlay(pdf, pg.page_index, members, out / f"overlay_p{pg.page_number}.pdf")
        typer.echo(
            f"p{pg.page_number} {info.sheet_no or '?'} {info.level or 'LEVEL?'}: "
            f"{len(members)} members, {sum(1 for m in members if m.needs_review)} need review; contexts={ctx}"
        )
    rows = summarize(all_members)
    write_members_csv(all_members, out / "members.csv")
    write_summary_csv(rows, out / "summary.csv")
    write_xlsx(all_members, rows, out / "takeoff.xlsx")
    (out / "members.json").write_text(
        json.dumps([m.to_dict() for m in all_members], indent=1, default=str)
    )
    (out / "report.json").write_text(json.dumps(report, indent=1))
    typer.echo("")
    typer.echo(f"{'LEVEL':<28}{'SECTION':<16}{'COUNT':>6}{'LF':>10}{'?LEN':>6}{'REVIEW':>8}")
    for r in rows:
        typer.echo(
            f"{r.level:<28}{r.canonical_section:<16}{r.count:>6}{r.total_lf:>10.1f}{r.unknown_lengths:>6}{r.needs_review:>8}"
        )
    if db:
        from ffs.db.models import Project, session
        from ffs.db.store import save_members

        s = session(db)
        prj = Project(name=pdf.stem)
        s.add(prj)
        s.commit()
        n = save_members(s, prj, all_members)
        typer.echo(f"persisted {n} members with evidence + assertions to {db} (project {prj.id})")
    typer.echo(f"outputs in {out}/")


@app.command()
def explain(members_json: Path, member_id: str) -> None:
    """Print the full evidence and assertion chain for one member (the 'click a quantity' view)."""
    data = json.loads(members_json.read_text())
    m = next((x for x in data if x["id"] == member_id or x["id"].endswith(member_id)), None)
    if not m:
        raise typer.Exit(code=1)
    typer.echo(
        f"{m['id']}  {m['canonical_section']}  {m['level']}  {m['length_display']}  [{m['status_color']}]"
    )
    typer.echo("evidence:")
    for e in m["evidence"]:
        typer.echo(
            f"  {e['kind']}: {e['document']} p{e['page']} {e['sheet_no']} bbox={e['bbox']} text={e['raw_text']!r} via {e['extraction_path']} ({e['confidence']})"
        )
    typer.echo("assertions:")
    for a in m["assertions"]:
        src = a.get("source") or {}
        where = f" @ {src.get('document')} {src.get('sheet_no') or ''}".rstrip() if src else ""
        meth = f" method={a['method']} inputs={a['inputs']}" if a.get("method") else ""
        typer.echo(
            f"  [{a['kind']}] {a['key']} = {a['value']!r} ({a['confidence']}){where}{meth}\n      {a['reasoning']}"
        )
    if m["notes"]:
        typer.echo("notes: " + " | ".join(m["notes"]))


@app.command("import-spray-report")
def import_spray_report(
    pdf: Path,
    out: Path = typer.Option(Path("out_spray"), help="output directory"),
    plans: bool = typer.Option(True, help="also stitch the coloured plan rasters to PNG"),
) -> None:
    """Import an EDGE 'Spray Report' PDF into structured JSON/CSV (historical takeoff data)."""
    from ffs.importers.edge_spray_report import (
        extract_plan_images,
        parse_spray_report,
        write_outputs,
    )

    rep = parse_spray_report(pdf)
    write_outputs(rep, out)
    for sh in rep.sheets:
        typer.echo(
            f"{sh.sheet_no}  {sh.title}  level≈{sh.level_guess}  product={sh.product_code}  "
            f"designs={[d['as_printed'] for d in sh.designs]}  items={len(sh.items)}  plan_page={sh.plan_page}"
        )
        for it in sh.items:
            sw = f"{it.swatch.rgb_hex} {it.swatch.pattern}" if it.swatch else "no swatch"
            flag = "" if it.thickness_consistent in (True, None) else "  !! inconsistent"
            typer.echo(
                f"   {it.section:<6} {it.member_label:<22} {it.canonical_section or '-':<14} "
                f"{(it.role or '-'):<7} {it.sides or '-'} side  {it.thickness_display:<10} [{sw}]{flag}"
            )
        for n in sh.qa_notes:
            typer.secho(f"   QA: {n}", fg="yellow")
    if plans:
        for p in extract_plan_images(pdf, out):
            typer.echo(f"plan image: {p}")
    typer.echo(f"outputs in {out}/")


@app.command("import-ul-design")
def import_ul_design(
    pdfs: list[Path],
    out: Path = typer.Option(Path("out_ul"), help="output directory for UL_<design>.json"),
) -> None:
    """Parse UL Product iQ design printouts (BXUV) into structured, versioned design records."""
    from ffs.importers.ul_design import parse_design_pdf, write_record

    for pdf in pdfs:
        rec = parse_design_pdf(pdf)
        p = write_record(rec, out)
        typer.echo(
            f"{rec.design_no}  {rec.member_category_guess}  design date={rec.design_date}  "
            f"last updated={rec.last_updated}  snapshot={rec.snapshot_date}"
        )
        for r in rec.ratings:
            typer.echo(
                f"   rating: {r.kind} — {r.hours_as_printed}" + (f" ({r.see})" if r.see else "")
            )
        for e in rec.equations:
            typer.echo(
                f"   equation item {e.item_no}: {e.as_printed}  [{e.form}]"
                + (f"  rating {e.rating}" if e.rating else "")
                + f"  {e.factor} {e.wd_range}  h {e.h_range} {e.h_units or ''}"
            )
        for t in rec.tables:
            typer.echo(
                f"   table item {t.item_no} [{t.kind}] cols={t.rating_columns or t.value_columns} rows={len(t.rows)}"
                + (f"  condition: {t.condition[:60]}" if t.condition else "")
            )
            for row in t.rows[:3]:
                typer.echo(f"      {row.cells}")
        for mf in rec.sfrm_manufacturers:
            typer.echo(f"   SFRM mfr (item {mf.item_no}): {mf.name} — {mf.text[:70]}")
        if rec.unparsed:
            typer.secho(f"   {len(rec.unparsed)} unparsed lines kept in record", fg="yellow")
        typer.echo(f"   → {p}")


@app.command("import-thickness-workbook")
def import_thickness_workbook(
    xlsx: Path,
    out: Path = typer.Option(Path("out_thk"), help="output directory"),
    product: str = typer.Option(None, help="product name when the workbook does not label columns"),
) -> None:
    """Import a manufacturer thickness workbook (long or wide layout) into traceable rows."""
    from collections import Counter

    from ffs.importers.thickness_workbook import import_workbook, write_outputs

    imp = import_workbook(xlsx, product)
    write_outputs(imp, out)
    typer.echo(
        f"{imp.workbook}: {len(imp.rows)} rows; sheets parsed={imp.sheets_parsed}; skipped={imp.sheets_skipped}"
    )
    by = Counter((r.product, r.variant, r.design) for r in imp.rows)
    for (prod, var, des), n in sorted(by.items(), key=lambda kv: -kv[1])[:40]:
        typer.echo(f"   {n:>6}  product={prod}  variant={var}  design={des}")
    unmapped = sum(1 for r in imp.rows if r.design is None)
    if unmapped:
        typer.secho(f"   {unmapped} rows without a design mapping", fg="yellow")
    typer.echo(f"outputs in {out}/")


@app.command("fetch-sources")
def fetch_sources(
    library: Path = typer.Option(
        Path("../data/reference_library/fetched"), help="where documents are stored"
    ),
    registry: Path = typer.Option(None, help="registry JSON (default: built-in)"),
    only: list[str] = typer.Option(None, help="source ids to fetch (repeatable)"),
) -> None:
    """Fetch PUBLIC reference documents listed in the registry (allowed hosts only, robots honoured)."""
    from ffs.sources.fetch import fetch_all, load_registry

    reg = load_registry(registry)
    results = fetch_all(library, reg, only or None)
    for r in results:
        flag = {
            "fetched": "+",
            "unchanged": "=",
            "skipped_no_url": "?",
            "refused_host": "!",
            "robots_disallow": "!",
            "error": "x",
        }[r.status]
        typer.echo(
            f" {flag} {r.id:<36} {r.status:<16} {r.http_status or ''} {r.stored_path or r.error or ''}"
            + ("  CHANGED since last fetch" if r.changed else "")
        )
    n_url = sum(1 for r in results if r.status != "skipped_no_url")
    typer.echo(
        f"{len(results)} sources, {n_url} with confirmed URLs; manifest at {library}/manifest.jsonl"
    )


@app.command("crawl-sources")
def crawl_sources(
    seeds: list[str],
    registry: Path = typer.Option(None, help="registry JSON to update (default: built-in)"),
    out: Path = typer.Option(Path("../data/reference_library/crawl_report.json")),
    max_pages: int = typer.Option(200),
    max_depth: int = typer.Option(3),
    delay: float = typer.Option(1.0, help="seconds between page requests"),
    write_registry: bool = typer.Option(True, help="append discovered documents to the registry"),
) -> None:
    """Discover public documents (PDF/XLSX/DOCX) on allowed manufacturer/listing sites."""
    from ffs.sources.crawl import crawl, merge_into_registry, write_report
    from ffs.sources.fetch import REGISTRY_PATH, load_registry

    reg_path = registry or REGISTRY_PATH
    reg = load_registry(reg_path)
    rep = crawl(
        seeds, reg["allowed_hosts"], max_pages=max_pages, max_depth=max_depth, delay_s=delay
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    write_report(rep, out)
    typer.echo(
        f"visited {rep.pages_visited} pages; {len(rep.documents)} documents; "
        f"{len(rep.robots_blocked)} robots-blocked; off-allowlist hosts seen: {rep.skipped_hosts[:10]}"
    )
    for d in rep.documents[:60]:
        typer.echo(f"  [{d.manufacturer_guess or '?':<16}] [{d.kind_guess or '?':<22}] {d.url}")
    if write_registry:
        n = merge_into_registry(rep, reg)
        reg_path.write_text(json.dumps(reg, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        typer.echo(f"{n} new entries appended to {reg_path}; run `ffs fetch-sources` to download")


@app.command("import-isolatek-chart")
def import_isolatek_chart(
    pdfs: list[Path],
    out: Path = typer.Option(Path("out_charts"), help="output directory"),
) -> None:
    """Parse Isolatek 'Designs & Thicknesses' chart PDFs into per-member thickness rows."""
    from ffs.importers.isolatek_chart import parse_chart_pdf, write_chart

    for pdf in pdfs:
        rec = parse_chart_pdf(pdf)
        p = write_chart(rec, out)
        typer.echo(
            f"{pdf.name}: design={rec.design} date={rec.chart_date} cols={rec.rating_columns} rows={len(rec.rows)}"
            + (f"  xref: {rec.cross_reference}" if rec.cross_reference else "")
        )
        typer.echo(f"   condition: {rec.condition}")
        typer.echo(f"   products: {rec.products}")
        for r in rec.rows[:3]:
            typer.echo(
                f"   {r.member_label:<14} W/D={r.wd} {r.thickness_as_printed} sect={r.section}"
            )
        for n in rec.notes[:5]:
            typer.secho(f"   ! {n}", fg="yellow")
        typer.echo(f"   → {p}")


@app.command("import-reference")
def import_reference(
    library: Path = typer.Option(
        Path("../data/reference_library/fetched"), help="fetched library root"
    ),
    out: Path = typer.Option(Path("../data/reference_library/parsed"), help="output root"),
    url_filter: str = typer.Option("", help="only documents whose URL contains this text"),
) -> None:
    """Route every fetched PDF by content (UL printout / Isolatek chart / other) and parse it."""
    from collections import Counter

    from ffs.importers.router import route_manifest

    results = route_manifest(library / "manifest.jsonl", library, out, url_filter)
    by = Counter(r.kind for r in results)
    typer.echo(f"{len(results)} documents routed: {dict(by)}")
    typer.echo(
        f"  UL designs with tables/equations: {sum(1 for r in results if r.kind == 'ul_design' and (r.tables or r.equations))}"
        f" of {by.get('ul_design', 0)}; chart rows: {sum(r.rows for r in results if r.kind in ('isolatek_chart', 'gcp_chart'))}"
    )
    for r in results:
        if r.kind == "error" or (r.kind in ("isolatek_chart", "gcp_chart") and r.rows == 0):
            typer.secho(f"  ! {r.kind} {r.path.split('/')[-1]} {r.error or 'no rows'}", fg="yellow")
    typer.echo(f"report: {out / 'route_report.jsonl'}")


@app.command()
def synth(out_dir: Path = Path("golden/synthetic/gp0_simple_bay")) -> None:
    """Generate the synthetic golden sheet + truth.json."""
    from ffs.synth import generate

    typer.echo(f"wrote {generate(out_dir)}")


@golden_app.command("score")
def golden_score(truth: Path, members_json: Path) -> None:
    """Score a members.json against a truth.json."""
    from ffs.synth import score

    res = score(truth, json.loads(members_json.read_text()))
    typer.echo(json.dumps(res, indent=1))


def _parse_pages(spec: str | None) -> list[int] | None:
    if not spec:
        return None
    idxs: list[int] = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            idxs.extend(range(int(a) - 1, int(b)))
        else:
            idxs.append(int(part) - 1)
    return idxs


if __name__ == "__main__":
    app()


@app.command()
def reference_coverage(
    library: Path = typer.Option(
        Path("../data/reference_library/fetched"), help="fetched library root"
    ),
    parsed: Path = typer.Option(Path("../data/reference_library/parsed"), help="parsed root"),
) -> None:
    """Report what the reference library holds per manufacturer (from files on disk only)."""
    from ffs.importers.coverage import build_coverage, render_markdown, write_coverage

    report = build_coverage(library, parsed)
    typer.echo(render_markdown(report))
    js, md = write_coverage(report, parsed)
    typer.echo(f"wrote {js} and {md}")


@app.command()
def manual_list(
    registries_dir: Path = typer.Option(
        Path("../data/reference_library/registries"), help="folder of per-manufacturer registries"
    ),
    out: Path = typer.Option(Path("../data/reference_library/manual"), help="output folder"),
) -> None:
    """Write the list of documents a person must download by hand (robots-disallowed hosts)."""
    from ffs.sources.manual import manual_items, write_manual_list

    regs = sorted(registries_dir.glob("*.json"))
    items = manual_items(regs)
    html_path, csv_path = write_manual_list(items, out)
    by = {}
    for it in items:
        by[it.manufacturer] = by.get(it.manufacturer, 0) + 1
    typer.echo(f"{len(items)} documents to download by hand: {by}")
    typer.echo(f"open {html_path} in a browser; list also at {csv_path}")


@app.command()
def import_manual(
    drop_dir: Path = typer.Argument(..., help="folder holding the files you downloaded"),
    registries_dir: Path = typer.Option(
        Path("../data/reference_library/registries"), help="folder of per-manufacturer registries"
    ),
    library: Path = typer.Option(
        Path("../data/reference_library/fetched"), help="fetched library root"
    ),
) -> None:
    """File hand-downloaded documents into the library with manifest provenance (method: manual)."""
    from ffs.sources.manual import import_manual as _import

    regs = sorted(registries_dir.glob("*.json"))
    results, unmatched = _import(drop_dir, regs, library)
    from collections import Counter

    typer.echo(f"{len(results)} filed: {dict(Counter(r.status for r in results))}")
    for name in unmatched:
        typer.secho(f"  ! not filed (no registry entry with this file name): {name}", fg="yellow")


@app.command()
def thickness(
    design: str = typer.Option(..., help="design number, e.g. P723"),
    member: str = typer.Option(..., help="canonical designation, e.g. W12X26 or HSS5X5X3/8"),
    rating: float = typer.Option(..., help="hourly rating, e.g. 1 or 1.5"),
    restraint: str = typer.Option(None, help="restrained / unrestrained"),
    product: str = typer.Option(None, help="product line printed on the chart, e.g. 'CAFCO 400'"),
    application: str = typer.Option("contour", help="contour or half_flange_tip"),
    condition: str = typer.Option(None, help="assembly condition / column group text to require"),
    parsed: Path = typer.Option(Path("../data/reference_library/parsed"), help="parsed root"),
) -> None:
    """Resolve a thickness from the design library and show every source that applies."""
    from ffs.design.library import DesignLibrary
    from ffs.design.thickness import ThicknessQuery, resolve

    lib = DesignLibrary.load(parsed)
    res = resolve(
        lib,
        ThicknessQuery(
            design, member, rating, restraint, product, application=application, condition=condition
        ),
    )
    typer.echo(f"{design} {member} {rating} h → {res.status.upper()}: {res.value}")
    for c in res.candidates:
        src = {k: v for k, v in c.source.items() if v not in (None, [], "")}
        typer.echo(
            f"  [{c.assertion_kind} {c.method} authority {c.authority}] {c.as_printed or ''} = {c.thickness_in} in"
        )
        typer.echo(f"      {src}")
        if c.inputs and c.method == "ul_equation":
            typer.echo(f"      inputs {c.inputs}")
        for n in c.notes:
            typer.echo(f"      note: {n}")
    for r in res.reasons:
        typer.secho(f"  - {r}", fg="yellow")


@app.command()
def check_bid(
    report: Path = typer.Argument(..., help="spray_report.json from import-spray-report"),
    parsed: Path = typer.Option(Path("../data/reference_library/parsed"), help="parsed root"),
) -> None:
    """Compare every thickness in an EDGE spray report with the design library (never corrects)."""
    from ffs.design.bid_check import check_report_file, summarize
    from ffs.design.library import DesignLibrary

    lib = DesignLibrary.load(parsed)
    rows = check_report_file(lib, report)
    typer.echo("sheet | member | role | design | h | bid | engine | status | verdict")
    for r in rows:
        eng = r.engine_in if r.engine_in is not None else (r.distinct or "")
        typer.echo(
            f"{r.sheet_no} | {r.member} | {r.role} | {r.design} | {r.rating_hours} | {r.bid_in} | {eng} | {r.status} | {r.verdict}"
        )
    typer.echo(f"summary: {summarize(rows)}")


def _project(db_url: str, project_id: str | None):
    from sqlalchemy import select

    from ffs.db.models import Project, session

    s = session(db_url)
    prj = s.get(Project, project_id) if project_id else s.scalars(select(Project)).first()
    if prj is None:
        raise typer.BadParameter("no project in that database")
    return s, prj


@app.command()
def assign_designs(
    db: str = typer.Option(..., help="SQLAlchemy URL of the project database"),
    design: str = typer.Option(..., help="design number, e.g. P723"),
    rating: float = typer.Option(..., help="hourly rating"),
    product: str = typer.Option(None, help="product line, e.g. 'CAFCO 400'"),
    restraint: str = typer.Option(None, help="restrained / unrestrained"),
    role: str = typer.Option(None, help="only members of this type (beam / column / brace …)"),
    application: str = typer.Option("contour", help="contour or half_flange_tip"),
    condition: str = typer.Option(None, help="assembly condition / column group to require"),
    parsed: Path = typer.Option(Path("../data/reference_library/parsed"), help="parsed root"),
    project_id: str = typer.Option(None, help="project id (default: first project)"),
    actor: str = typer.Option("design-engine", help="who is recorded as the actor"),
) -> None:
    """Resolve a thickness for every member under one design and persist the assignments;
    anything not cleanly resolved becomes a review item."""
    from ffs.db.assign import assign_designs_for_project, ensure_base_scenario, resolution_meter
    from ffs.design.library import DesignLibrary

    s, prj = _project(db, project_id)
    scn = ensure_base_scenario(s, prj)
    lib = DesignLibrary.load(parsed)
    counts = assign_designs_for_project(
        s, prj, scn, lib, design, rating, product, restraint, role, application, condition, actor
    )
    typer.echo(f"assigned {sum(counts.values())} members under {design} {rating} h: {counts}")
    typer.echo(f"meter: {resolution_meter(s, prj, scn)}")


@app.command()
def review_queue(
    db: str = typer.Option(..., help="SQLAlchemy URL of the project database"),
    project_id: str = typer.Option(None, help="project id (default: first project)"),
) -> None:
    """List open review items: what is known, what is likely, why it is open, the options."""
    from ffs.db.assign import ensure_base_scenario, open_review_items

    s, prj = _project(db, project_id)
    scn = ensure_base_scenario(s, prj)
    items = open_review_items(s, prj, scn)
    typer.echo(f"{len(items)} open review items")
    for it in items:
        typer.echo(f"- [{it.kind}/{it.category}] {it.title}")
        typer.echo(f"    known: {it.known}")
        if it.likely:
            typer.echo(f"    likely: {it.likely}")
        typer.echo(f"    why: {it.why}")
        if it.missing:
            typer.echo(f"    missing: {it.missing}")
        for o in it.options or []:
            typer.echo(
                f"    option: {o.get('thickness_in')} in by {o.get('method')} ({o.get('kind')})"
            )


@app.command()
def meter(
    db: str = typer.Option(..., help="SQLAlchemy URL of the project database"),
    project_id: str = typer.Option(None, help="project id (default: first project)"),
) -> None:
    """Resolution meter: members, open review items by category, assignments per table."""
    from ffs.db.assign import ensure_base_scenario, resolution_meter

    s, prj = _project(db, project_id)
    typer.echo(json.dumps(resolution_meter(s, prj, ensure_base_scenario(s, prj)), indent=1))


@app.command()
def import_drawing_report(
    pdf: Path = typer.Argument(..., help="EDGE Fireproofing Drawing Report / Spray Chart PDF"),
    out: Path = typer.Option(Path("out_drawing_report"), help="output directory"),
) -> None:
    """Parse the legend rows (member, design code, hours, thickness) of a shop-drawing report."""
    from ffs.importers.edge_drawing_report import parse_drawing_report, write_drawing_report

    rep = parse_drawing_report(pdf)
    p = write_drawing_report(rep, out)
    n = sum(len(s.rows) for s in rep.sheets)
    typer.echo(
        f"{rep.project} | {rep.report_name} | {rep.print_date}: {len(rep.sheets)} sheets, {n} legend rows → {p}"
    )
    for note in rep.notes:
        typer.secho(f"  ! {note}", fg="yellow")


@app.command()
def check_drawing_report(
    pdf: Path = typer.Argument(..., help="EDGE Fireproofing Drawing Report PDF"),
    parsed: Path = typer.Option(Path("../data/reference_library/parsed"), help="parsed root"),
    show: str = typer.Option("differs", help="comma list of verdicts to print in full, or 'all'"),
) -> None:
    """Check every legend row of a shop-drawing report against the design library."""
    from ffs.design.library import DesignLibrary
    from ffs.design.report_check import check_drawing_report as _check
    from ffs.design.report_check import summarize
    from ffs.importers.edge_drawing_report import parse_drawing_report

    rep = parse_drawing_report(pdf)
    checks = _check(DesignLibrary.load(parsed), rep)
    typer.echo(f"{rep.project}: {summarize(checks)}")
    wanted = None if show == "all" else {x.strip() for x in show.split(",")}
    for c in checks:
        if wanted is not None and not any(c.verdict.startswith(w) for w in wanted):
            continue
        r = c.row
        eng = c.resolution.distinct_values() if c.resolution else []
        typer.echo(
            f"- {c.sheet} | {r.description} | {r.design_code} {r.hours} h | bid {r.thickness_as_printed} | engine {eng} | {c.verdict}"
        )
        for n in c.interpretations + c.assumptions:
            typer.echo(f"    {n}")
        if c.resolution:
            for cand in c.resolution.candidates[:4]:
                src = {
                    k: v
                    for k, v in cand.source.items()
                    if k
                    in (
                        "design",
                        "chart_date",
                        "condition",
                        "section",
                        "group",
                        "row",
                        "column",
                        "via",
                    )
                    and v
                }
                typer.echo(f"    {cand.method} {cand.thickness_in} {src}")
            for reason in c.resolution.reasons[:3]:
                typer.secho(f"    - {reason}", fg="yellow")
