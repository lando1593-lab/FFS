import json

from ffs.importers.coverage import build_coverage, render_markdown, write_coverage


def test_coverage_counts_from_disk(tmp_path):
    lib = tmp_path / "fetched"
    parsed = tmp_path / "parsed"
    (lib).mkdir()
    (parsed / "charts").mkdir(parents=True)
    rows = [
        {
            "status": "fetched",
            "url": "https://a.example/x790.pdf",
            "stored_path": "Acme/x790/1.pdf",
        },
        {
            "status": "unchanged",
            "url": "https://a.example/s721.pdf",
            "stored_path": "Acme/s721/2.pdf",
        },
        {"status": "fetched", "url": "https://a.example/j.pdf", "stored_path": "Acme/j/3.pdf"},
        {"status": "error", "url": "https://a.example/bad.pdf", "stored_path": None},
        {"status": "fetched", "url": "https://b.example/n.pdf", "stored_path": "Beta/n/4.pdf"},
    ]
    (lib / "manifest.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    chart = parsed / "charts" / "s721.json"
    chart.write_text(json.dumps({"products": "CAFCO 300", "design": "S721", "rows": [1, 2, 3]}))
    nochart = parsed / "charts" / "j.json"
    nochart.write_text(json.dumps({"products": None, "design": "S721", "rows": []}))
    report_rows = [
        {
            "path": "https://a.example/x790.pdf",
            "kind": "ul_design",
            "design": "X790",
            "rows": 0,
            "tables": 1,
            "equations": 1,
            "notes": 0,
            "out": None,
        },
        {
            "path": "https://a.example/s721.pdf",
            "kind": "isolatek_chart",
            "design": "S721",
            "rows": 3,
            "tables": 0,
            "equations": 0,
            "notes": 0,
            "out": str(chart),
        },
        {
            "path": "https://a.example/j.pdf",
            "kind": "isolatek_chart",
            "design": "S721",
            "rows": 0,
            "tables": 0,
            "equations": 0,
            "notes": 0,
            "out": str(nochart),
        },
        {
            "path": "https://b.example/n.pdf",
            "kind": "ul_design",
            "design": "N830",
            "rows": 0,
            "tables": 0,
            "equations": 0,
            "notes": 0,
            "out": None,
        },
    ]
    (parsed / "route_report.jsonl").write_text("\n".join(json.dumps(r) for r in report_rows) + "\n")

    report = build_coverage(lib, parsed)
    acme, beta = report["Acme"], report["Beta"]
    assert acme.documents == 3  # the error row is not a document
    assert acme.by_kind == {"isolatek_chart": 2, "ul_design": 1}
    assert acme.designs_with_tables == ["X790"]
    assert acme.designs_without_tables == []
    assert acme.chart_designs == ["S721"]
    assert acme.chart_rows == 3
    assert acme.charts_without_rows == ["j.pdf"]
    assert acme.rows_by_product == {"CAFCO 300": 3, "(product line not printed on chart)": 0}
    assert beta.designs_without_tables == ["N830"]

    md = render_markdown(report)
    assert "| Acme | 3 | isolatek_chart 2, ul_design 1 | 1 | 0 | 1 / 3 |" in md
    assert "N830" in md
    js, mdp = write_coverage(report, parsed)
    assert json.loads(js.read_text())["Beta"]["designs_without_tables"] == ["N830"]
    assert mdp.read_text() == md
