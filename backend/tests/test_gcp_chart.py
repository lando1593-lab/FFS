from pathlib import Path

import pymupdf
import pytest

from ffs.importers.gcp_chart import parse_gcp_chart_pdf, write_gcp_chart
from ffs.importers.router import route_file, sniff

LIB = Path(__file__).resolve().parents[2] / "data" / "reference_library" / "fetched"


def _put(page, x, y, text, size=6.8):
    page.insert_text((x, y), text, fontsize=size)


def _beam_chart(path, pages=1):
    """A two-group MONOKOTE beam chart in the real D739 geometry (positions in pt)."""
    doc = pymupdf.open()
    for pi in range(pages):
        p = doc.new_page(width=612, height=792)
        _put(p, 283, 64, "BXUV.D739", 8.5)
        _put(p, 182, 76, "Beam for Protected Floor/Ceiling, Fluted/Corrugated Decking", 8.5)
        _put(p, 101, 89, "Unrestrained Beam", 8.5)
        _put(p, 345, 89, "Normal Weight Concrete & Lightweight Concrete", 8.5)
        _put(p, 63, 109, "GCP APPLIED TECHNOLOGIES INC -   Types MK-6/HY, MK-10 HB, Z-106,", 8.5)
        _put(p, 244, 120, "Z-106/HY, Z-146", 8.5)
        _put(p, 99, 146, "NORMAL WEIGHT CONCRETE FILL", 7.7)
        _put(p, 390, 146, "LIGHTWEIGHT CONCRETE FILL", 7.7)
        for x, t in ((73, "1 hr"), (112, "1.5 hr"), (157, "2 hr"), (199, "3 hr"), (242, "4 hr")):
            _put(p, x, 158, t)
            _put(p, x + 285, 158, t)
        _put(p, 294, 158, "Member")
        _put(p, 278, 170, "Size")
        _put(p, 296, 170, "x  Wt.")
        _put(p, 320, 170, "W/D")
        rows = [
            (
                "W4",
                "x 13",
                "0.670",
                ["9/16", "7/8", "1", "1 7/16", "2 1/4"],
                ["9/16", "1", "1 1/8", "1 3/4", "2 1/4"],
            ),
            (
                "W6",
                "x 9",
                "0.398",
                ["3/4", "1 1/8", "1 1/4", "1 13/16", "2 7/8"],
                ["3/4", "1 1/4", "1 7/16", "NR", "NR"],
            ),
        ]
        if pi == pages - 1:
            rows.append(
                (
                    "Other   0.370",
                    "",
                    "",
                    ["3/4", "1 1/8", "1 5/16", "1 7/8", "2 15/16"],
                    ["3/4", "1 5/16", "1 1/2", "2 5/16", "2 15/16"],
                )
            )
        y = 181
        for fam, wt, wd, left, right in rows:
            _put(p, 283 if wt else 296, y, fam)
            if wt:
                _put(p, 296, y, wt)
                _put(p, 323, y, wd)
            for x, v in zip((75, 117, 152, 194, 237), left, strict=True):
                _put(p, x, y, v)
            for x, v in zip((361, 395, 437, 479, 522), right, strict=True):
                _put(p, x, y, v)
            y += 10
        _put(p, 257, 754, "GCP Applied Technologies", 9.4)
        _put(p, 51, 765, "Disclaimer at end of document", 9.4)
        _put(p, 286, 765, "3/15/2021", 9.4)
        _put(p, 492, 765, f"D739 Page {pi + 1} of {pages}", 9.4)
    doc.save(path)
    doc.close()


def test_two_group_beam_chart_rows_titles_and_generic_row(tmp_path):
    f = tmp_path / "D739.pdf"
    _beam_chart(f)
    rec = parse_gcp_chart_pdf(f)
    assert rec.design == "D739"
    assert rec.assembly == "Beam for Protected Floor/Ceiling, Fluted/Corrugated Decking"
    assert rec.restraint == "Unrestrained Beam"
    assert rec.concrete == "Normal Weight Concrete & Lightweight Concrete"
    assert rec.products.startswith("GCP APPLIED TECHNOLOGIES INC") and rec.products.endswith(
        "Z-146"
    )
    assert rec.chart_date == "3/15/2021"
    assert [g.title for g in rec.groups] == [
        "NORMAL WEIGHT CONCRETE FILL",
        "LIGHTWEIGHT CONCRETE FILL",
    ]
    assert all(g.rating_columns == ["1 hr", "1.5 hr", "2 hr", "3 hr", "4 hr"] for g in rec.groups)
    assert rec.member_columns == ["Size", "x  Wt.", "W/D"]
    assert len(rec.rows) == 6  # 3 printed rows × 2 groups
    r0, r1 = rec.rows[0], rec.rows[1]
    assert (r0.member_label, r0.canonical, r0.wd, r0.ratio_name) == (
        "W4 x 13",
        "W4X13",
        0.67,
        "W/D",
    )
    assert r0.group == "NORMAL WEIGHT CONCRETE FILL"
    assert r0.thickness_as_printed == ["9/16", "7/8", "1", "1 7/16", "2 1/4"]
    assert r0.thickness_in == [0.5625, 0.875, 1.0, 1.4375, 2.25]
    assert r1.group == "LIGHTWEIGHT CONCRETE FILL" and r1.thickness_in[2] == 1.125
    w6_lwc = rec.rows[3]
    assert w6_lwc.thickness_as_printed[3:] == ["NR", "NR"]
    assert w6_lwc.thickness_in[3:] == [None, None] and w6_lwc.not_rated == [False] * 3 + [True] * 2
    other = rec.rows[4]
    assert other.member_label == "Other" and other.canonical is None and other.wd == 0.37
    assert rec.notes == []
    js = write_gcp_chart(rec, tmp_path / "out")
    assert js.exists() and (tmp_path / "out" / "D739.csv").read_text().count("\n") == 7


def test_continuation_pages_reuse_the_columns(tmp_path):
    f = tmp_path / "D739.pdf"
    _beam_chart(f, pages=2)
    rec = parse_gcp_chart_pdf(f)
    assert rec.pages == 2 and len(rec.rows) == 10
    assert {r.page for r in rec.rows} == {1, 2}


def test_router_routes_gcp_chart_before_ul_design(tmp_path):
    f = tmp_path / "D739.pdf"
    _beam_chart(f)
    kind, _ = sniff(f)
    assert kind == "gcp_chart"
    res = route_file(f, tmp_path / "out")
    assert (res.kind, res.design, res.rows, res.tables) == ("gcp_chart", "D739", 6, 2)
    assert Path(res.out).exists()


REAL = {
    "D739": LIB / "GCP_Applied_Technologies" / "gcp-thk-d739-47ac5d" / "f9dd63e1b3e3.pdf",
}


@pytest.mark.skipif(not LIB.exists(), reason="fetched library not present")
def test_real_d739_chart_if_present():
    import glob

    hits = glob.glob(str(LIB / "GCP_Applied_Technologies" / "gcp-thk-d739-*" / "*.pdf"))
    if not hits:
        pytest.skip("D739 chart not fetched")
    rec = parse_gcp_chart_pdf(hits[0])
    assert rec.design == "D739" and rec.pages == 6 and rec.chart_date == "3/15/2021"
    assert [g.title for g in rec.groups] == [
        "NORMAL WEIGHT CONCRETE FILL",
        "LIGHTWEIGHT CONCRETE FILL",
    ]
    assert len(rec.rows) == 704
    first = rec.rows[0]
    assert (first.member_label, first.canonical, first.wd) == ("W4 x 13", "W4X13", 0.67)
    assert first.thickness_in == [0.5625, 0.875, 1.0, 1.4375, 2.25]
    assert all(r.wd is not None for r in rec.rows)
