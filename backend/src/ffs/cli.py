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
                f"   equation item {e.item_no}: h = R / ({e.a}*(W/D) + {e.b})  W/D {e.wd_range}  h {e.h_range_in}"
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
