from pathlib import Path

import pymupdf
import pytest

from ffs.importers.router import route_file, sniff

_LIB = Path(__file__).resolve().parents[2] / "data" / "reference_library" / "fetched" / "Isolatek"

_AISC_CHART = [
    "X999",
    "Wide Flange Structural Steel Columns",
    "AISC Desig.",
    "W/D",
    "Metric Desig.",
    "M/D",
    "Hp/A",
    "1-Hour",
    "2-Hour",
    "W44 x 335",
    "2.25",
    "W1120 x 498",
    "132.8",
    "59.5",
    "3/4",
    "1-1/2",
    "290",
    "1.97",
    "432",
    "116.2",
    "68.0",
    "3/4",
    "1-1/2",
]


def _pdf(path, lines):
    doc = pymupdf.open()
    p = doc.new_page()
    y = 40
    for ln in lines:
        p.insert_text((40, y), ln, fontsize=8)
        y += 11
    doc.save(path)
    doc.close()


def _real(rel):
    p = _LIB / rel
    if not p.exists():
        pytest.skip(f"reference library file not present: {p}")
    return p


def test_sniff_routes_aisc_albi_driclad_chart(tmp_path):
    f = tmp_path / "X999.pdf"
    _pdf(f, [*_AISC_CHART, "Albi DriClad", "Page 1", "8/26/2025"])
    assert sniff(f)[0] == "isolatek_chart"
    res = route_file(f, tmp_path / "out")
    assert res.kind == "isolatek_chart" and res.design == "X999" and res.rows == 2
    assert res.out and Path(res.out).exists()


def test_sniff_table_without_product_line_is_other(tmp_path):
    f = tmp_path / "table.pdf"
    _pdf(f, _AISC_CHART)
    assert sniff(f)[0] == "other"


def test_sniff_cafco_chart_and_xref_unchanged(tmp_path):
    chart = tmp_path / "N999.pdf"
    _pdf(
        chart,
        ["N999", "All-Fluted Deck", "CAFCO® 300 Series", "ASTM", "Desig.", "W/D", "1-Hour"],
    )
    assert sniff(chart)[0] == "isolatek_chart"
    xref = tmp_path / "G717.pdf"
    _pdf(xref, ["G717", "Joist", "Use Design S721 Table", "CAFCO® 300 Series"])
    assert sniff(xref)[0] == "chart_xref"
    ul = tmp_path / "ul.pdf"
    _pdf(ul, ["UL Product iQ", "BXUV.N307", "Design No. N307"])
    assert sniff(ul)[0] == "ul_design"


@pytest.mark.parametrize(
    "rel",
    [
        "isolatek-n307-1d712d/d7ebd6945e03.pdf",
        "isolatek-x313-9af374/5a425a3184ea.pdf",
        "isolatek-s721-20-20joists/cbcaee95fca6.pdf",
    ],
)
def test_real_charts_route_as_isolatek_chart(rel, tmp_path):
    f = _real(rel)
    assert sniff(f)[0] == "isolatek_chart"
    res = route_file(f, tmp_path / "out")
    assert res.kind == "isolatek_chart" and res.rows > 100 and res.error is None


def test_route_manifest_accepts_pdf_stored_without_extension(tmp_path):
    """Extension-less document URLs (Tremco CPG, Jotun) are stored as .bin; the bytes decide."""
    import json

    from ffs.importers.router import _is_pdf, route_manifest

    lib = tmp_path / "lib"
    (lib / "Nullifire" / "x").mkdir(parents=True)
    f = lib / "Nullifire" / "x" / "abc.bin"
    f.write_bytes(b"%PDF-1.4\n%%EOF\n")
    (lib / "Nullifire" / "x" / "page.bin").write_bytes(b"<html>")
    assert _is_pdf(f) and not _is_pdf(lib / "Nullifire" / "x" / "page.bin")
    rows = [
        {
            "status": "fetched",
            "url": "https://assets.cpg-europe.com/cms/r/1",
            "stored_path": "Nullifire/x/abc.bin",
        },
        {
            "status": "fetched",
            "url": "https://assets.cpg-europe.com/cms/r/2",
            "stored_path": "Nullifire/x/page.bin",
        },
    ]
    (lib / "manifest.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    res = route_manifest(lib / "manifest.jsonl", lib, tmp_path / "out")
    assert [r.path for r in res] == ["https://assets.cpg-europe.com/cms/r/1"]


def test_gcp_flowchart_is_not_a_chart(tmp_path):
    import pymupdf

    from ffs.importers.router import sniff

    f = tmp_path / "flow.pdf"
    doc = pymupdf.open()
    p = doc.new_page()
    y = 40
    for ln in [
        "GCP APPLIED TECHNOLOGIES",
        "Assembly",
        "Beam",
        "Joist",
        "Fluted/Cellular 1hr & 1 1/2hr (e)",
        "D743",
        "N706",
    ]:
        p.insert_text((40, y), ln, fontsize=8)
        y += 11
    doc.save(f)
    doc.close()
    assert sniff(f)[0] == "other"
