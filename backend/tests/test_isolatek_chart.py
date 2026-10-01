from pathlib import Path

import pymupdf
import pytest

from ffs.importers.isolatek_chart import parse_chart_pdf, write_chart


def _chart(path):
    doc = pymupdf.open()
    p = doc.new_page()
    lines = [
        "Page 1",
        "10/3/2013",
        "N999",
        "All-Fluted Deck",
        "Lightweight and Normal Weight Concrete",
        "CAFCO® 300 Series, CAFCO® 400 & ISOLATEK® Type 300 Series",
        "ASTM",
        "Desig.",
        "W/D",
        "Metric Desig.",
        "M/D",
        "Hp/A",
        "1-Hour",
        "1-1/2 Hour",
        "2-Hour",
        "3-Hour",
        "4-Hour",
        "W44 x 335",
        "2.52",
        "W1120 x 498",
        "148.7",
        "53.2",
        "5/16",
        "3/8",
        "3/8",
        "1/2",
        "11/16",
        "290",
        "2.2",
        "432",
        "129.8",
        "60.9",
        "5/16",
        "3/8",
        "3/8",
        "9/16",
        "13/16",
        "Unrestrained Beam",
        "W12 x 26",
        "0.69",
        "W310 x 39",
        "40.7",
        "193.9",
        "7/16",
        "5/8",
        "13/16",
        "1-1/4",
        "1-11/16",
    ]
    y = 40
    for ln in lines:
        p.insert_text((40, y), ln, fontsize=8)
        y += 11
    doc.save(path)
    doc.close()


def test_chart_rows_and_family_carry(tmp_path):
    f = tmp_path / "N999.pdf"
    _chart(f)
    rec = parse_chart_pdf(f)
    assert rec.design == "N999" and rec.chart_date == "10/3/2013"
    assert rec.rating_columns == ["1 Hr", "1-1/2 Hr", "2 Hr", "3 Hr", "4 Hr"]
    assert "All-Fluted Deck" in rec.condition and "CAFCO" in rec.products
    assert [r.member_label for r in rec.rows] == ["W44 x 335", "W44 x 290", "W12 x 26"]
    assert rec.rows[1].family_label == "W44 x 335" and rec.rows[1].canonical == "W44X290"
    assert (
        rec.rows[1].wd == 2.2
        and rec.rows[1].metric_label == "432"
        and rec.rows[1].md == 129.8
        and rec.rows[1].hp_a == 60.9
    )
    assert rec.rows[1].thickness_in == [0.3125, 0.375, 0.375, 0.5625, 0.8125]
    assert rec.rows[2].section == "Unrestrained Beam" and rec.rows[2].thickness_in[0] == 0.4375
    assert rec.notes == []


def _lines_pdf(path, lines):
    doc = pymupdf.open()
    p = doc.new_page()
    y = 40
    for ln in lines:
        p.insert_text((40, y), ln, fontsize=8)
        y += 11
    doc.save(path)
    doc.close()


def test_angle_and_tube_families(tmp_path):
    ang = tmp_path / "Single Angles.pdf"
    _lines_pdf(
        ang,
        [
            "Page 1",
            "10/3/2013",
            "Miscellaneous Shapes",
            "Single Angles",
            "CAFCO® 300 Series",
            "ASTM Desig.",
            "W/D",
            "Metric Desig.",
            "M/D",
            "Hp/A",
            "1-Hour",
            "1-1/2 Hour",
            "2-Hour",
            "3-Hour",
            "4-Hour",
            "L 8 x 8 x 1-1/8",
            "1.80",
            "203 x 203 x 29",
            "106.2",
            "74.4",
            "3/8",
            "9/16",
            "3/4",
            "1-1/8",
            "1-7/16",
            "x 1",
            "1.62",
            "x 25",
            "95.6",
            "82.7",
            "3/8",
            "9/16",
            "13/16",
            "1-3/16",
            "1-5/8",
            "L3 x 3 x 1/4",
            "0.41",
            "76 x 76 x 6.4",
            "24.2",
            "326.3",
            "15/16",
            "1-1/4",
            "1-9/16",
            "2-1/8",
            "2-11/16",
        ],
    )
    rec = parse_chart_pdf(ang)
    assert [r.member_label for r in rec.rows] == ["L8 x 8 x 1-1/8", "L8 x 8 x 1", "L3 x 3 x 1/4"]
    assert (
        rec.rows[1].family_label == "L 8 x 8 x 1-1/8"
        and rec.rows[1].wd == 1.62
        and rec.rows[1].metric_label == "x 25"
    )
    assert rec.rows[2].canonical == "L3X3X1/4" and rec.rows[2].thickness_in[0] == 0.9375
    assert rec.factor_kind == "W/D" and rec.notes == []
    tube = tmp_path / "X790 ST.pdf"
    _lines_pdf(
        tube,
        [
            "Page 1",
            "10/3/2013",
            "X790",
            "Structural Steel Square Tube Columns",
            "CAFCO® 300 Series",
            "ASTM Desig.",
            "Wall Thk",
            "A/P",
            "Metric Desig.",
            "M/D",
            "Hp/A",
            "1-Hour",
            "1-1/2 Hour",
            "2-Hour",
            "3-Hour",
            "4-Hour",
            "30 x 30",
            "5/8",
            "0.61",
            "762 x 762 x 15.9",
            "121.2",
            "65.2",
            "5/16",
            "7/16",
            "11/16",
            "1-1/8",
            "1-9/16",
            "1/2",
            "0.49",
            "x 12.7",
            "96.9",
            "81.6",
            "5/16",
            "7/16",
            "11/16",
            "1-1/8",
            "1-9/16",
            "5 x 5",
            "3/8",
            "0.35",
            "127 x 127 x 9.5",
            "68.8",
            "115.0",
            "7/16",
            "3/4",
            "1",
            "1-9/16",
            "2-1/8",
        ],
    )
    rec2 = parse_chart_pdf(tube)
    assert rec2.design == "X790" and rec2.factor_kind == "A/P"
    assert [r.member_label for r in rec2.rows] == [
        "ST 30 x 30 x 5/8",
        "ST 30 x 30 x 1/2",
        "ST 5 x 5 x 3/8",
    ]
    assert rec2.rows[1].wd == 0.49 and rec2.rows[2].thickness_in == [
        0.4375,
        0.75,
        1.0,
        1.5625,
        2.125,
    ]
    assert rec2.notes == []


def _pages_pdf(path, pages):
    doc = pymupdf.open()
    for lines in pages:
        p = doc.new_page()
        y = 40
        for ln in lines:
            p.insert_text((40, y), ln, fontsize=8)
            y += 11
    doc.save(path)
    doc.close()


_LIB = Path(__file__).resolve().parents[2] / "data" / "reference_library" / "fetched" / "Isolatek"


def _real(rel):
    p = _LIB / rel
    if not p.exists():
        pytest.skip(f"reference library file not present: {p}")
    return p


def test_joist_joined_rating_header_footnote_and_nr(tmp_path):
    """S721 joist layout: three rating headers in one text span plus a fourth on its own, every
    header carrying a '+' footnote marker; NR cells; depth and approx. weight per row; product
    line, footer date and the footnote text printed under the table."""
    f = tmp_path / "S721 - Joists.pdf"
    _lines_pdf(
        f,
        [
            "S721",
            "Protected Roof Deck",
            "Joist",
            "Designation",
            "Depth",
            "(in.)",
            "Approx. Wt",
            "(lbs./ft.)",
            "1-Hour+ 1-1/2 Hour+ 2-Hour+",
            "3-Hour+",
            "8K1",
            "8",
            "4.9",
            "NR",
            "NR",
            "NR",
            "NR",
            "10K1",
            "10",
            "5.1",
            "3/4",
            "1  3/16",
            "1  7/16",
            "2  5/16",
            "Maximum 30,000 psi (30 ksi joists).  10K1 or 12K1 joists are limited to a max "
            "26,000 psi",
            "+Reduced thicknesses are available when metal lath or nonmetallic fabric mesh "
            "secured to one sid",
            "Unrestrained Beam",
            "CAFCO® Series, CAFCO® 400 & ISOLATEK® Type 300 Series, ISOLATEK® Type  400",
            "Page 1",
            "10/7/2013",
        ],
    )
    rec = parse_chart_pdf(f)
    assert rec.design == "S721" and rec.condition == "Protected Roof Deck Joist"
    assert rec.rating_columns == ["1 Hr", "1-1/2 Hr", "2 Hr", "3 Hr"]
    assert rec.rating_column_markers == ["+", "+", "+", "+"]
    assert rec.products.startswith("CAFCO® Series") and rec.chart_date == "10/7/2013"
    assert [r.member_label for r in rec.rows] == ["8K1", "10K1"]
    nr = rec.rows[0]
    assert nr.thickness_as_printed == ["NR"] * 4 and nr.thickness_in == [None] * 4
    assert nr.not_rated == [True] * 4 and nr.depth_in == 8.0 and nr.approx_wt == 4.9
    k10 = rec.rows[1]
    assert k10.thickness_in == [0.75, 1.1875, 1.4375, 2.3125]
    assert k10.thickness_as_printed[0] == "3/4" and k10.not_rated == [False] * 4
    assert k10.depth_in == 10.0 and k10.approx_wt == 5.1 and k10.canonical == "10K1"
    assert len(rec.footnotes) == 1
    fn = rec.footnotes[0]
    assert fn.marker == "+" and fn.page == 1
    assert fn.text.startswith("+Reduced thicknesses are available when metal lath")
    assert fn.columns == ["1 Hr", "1-1/2 Hr", "2 Hr", "3 Hr"]
    assert rec.notes == []
    assert rec.to_dict()["footnotes"][0]["marker"] == "+"


def test_aisc_metric_carry_down_and_headerless_continuation_page(tmp_path):
    """Albi DriClad layout: 'AISC Desig.' on one line, no Designs & Thicknesses title, product
    and date only under the table; weight-only rows carry both the AISC and the metric family
    down; the second page repeats the title but not the column header; a row whose text layer
    lacks thickness cells is noted and skipped, not padded."""
    f = tmp_path / "X999.pdf"
    _pages_pdf(
        f,
        [
            [
                "X999",
                "Wide Flange Structural Steel Columns",
                "AISC Desig.",
                "W/D",
                "Metric Desig.",
                "M/D",
                "Hp/A",
                "1-Hour",
                "2-Hour",
                "3-Hour",
                "4-Hour",
                "W44 x 335",
                "2.25",
                "W1120 x 498",
                "132.8",
                "59.5",
                "3/4",
                "1-1/2",
                "1-1/2",
                "1-1/2",
                "290",
                "1.97",
                "432",
                "116.2",
                "68.0",
                "3/4",
                "1-1/2",
                "1-1/2",
                "1-1/2",
                "230",
                "1.58",
                "342",
                "93.2",
                "84.8",
                "3/4",
                "1-1/2",
                "2-1/2",
                "NR",
                "Albi DriClad",
                "Page 1",
                "8/26/2025",
            ],
            [
                "X999",
                "Wide Flange Structural Steel Columns",
                "W16 x 40",
                "0.78",
                "W410 x 60",
                "46.0",
                "171.8",
                "3/4",
                "36",
                "0.7",
                "53",
                "41.3",
                "191.4",
                "NR",
                "NR",
                "NR",
                "NR",
                "Albi DriClad",
                "Page 2",
                "8/26/2025",
            ],
        ],
    )
    rec = parse_chart_pdf(f)
    assert rec.design == "X999" and rec.condition == "Wide Flange Structural Steel Columns"
    assert rec.products == "Albi DriClad" and rec.chart_date == "8/26/2025"
    assert rec.rating_columns == ["1 Hr", "2 Hr", "3 Hr", "4 Hr"]
    assert rec.rating_column_markers == ["", "", "", ""] and rec.footnotes == []
    assert rec.factor_kind == "W/D"
    assert [r.member_label for r in rec.rows] == [
        "W44 x 335",
        "W44 x 290",
        "W44 x 230",
        "W16 x 36",
    ]
    first, carried = rec.rows[0], rec.rows[1]
    assert first.metric_label == "W1120 x 498" and first.metric_member_label == "W1120 x 498"
    assert carried.family_label == "W44 x 335" and carried.canonical == "W44X290"
    assert carried.metric_label == "432" and carried.metric_member_label == "W1120 x 432"
    assert carried.wd == 1.97 and carried.md == 116.2 and carried.hp_a == 68.0
    assert carried.thickness_in == [0.75, 1.5, 1.5, 1.5]
    assert rec.rows[2].thickness_as_printed == ["3/4", "1-1/2", "2-1/2", "NR"]
    assert rec.rows[2].not_rated == [False, False, False, True]
    assert rec.rows[2].thickness_in[3] is None
    p2 = rec.rows[3]
    assert p2.page == 2 and p2.family_label == "W16 x 40"
    assert p2.metric_member_label == "W410 x 53" and p2.not_rated == [True] * 4
    assert rec.notes == ["p2: row 'W16 x 40' has 1 of 4 thickness cells"]


def test_metric_carry_without_full_metric_label_stays_none(tmp_path):
    f = tmp_path / "N998.pdf"
    _lines_pdf(
        f,
        [
            "N998",
            "All-Fluted Deck",
            "AISC",
            "Desig.",
            "W/D",
            "Metric Desig.",
            "M/D",
            "Hp/A",
            "1-Hour",
            "W44 x 335",
            "2.52",
            "1120 x 498",
            "148.7",
            "53.2",
            "2-1/2",
            "290",
            "2.2",
            "432",
            "129.8",
            "60.9",
            "2-1/2",
            "W40 x 593",
            "4.56",
            "269.0",
            "29.4",
            "2-1/2",
            "503",
            "3.93",
            "748",
            "231.9",
            "34.1",
            "2-1/2",
            "Albi DriClad",
        ],
    )
    rec = parse_chart_pdf(f)
    assert [r.member_label for r in rec.rows] == [
        "W44 x 335",
        "W44 x 290",
        "W40 x 593",
        "W40 x 503",
    ]
    assert rec.rows[1].metric_member_label == "1120 x 432"
    # W40 x 593 printed no metric label (the M/D cell is read as the metric number); the family
    # restarted, so W40 x 503's weight-only metric cell is not attached to the W44 family
    assert rec.rows[3].metric_label == "748" and rec.rows[3].metric_member_label is None
    assert rec.rows[3].wd == 3.93 and rec.rows[3].thickness_in == [2.5]


def test_real_s721_joist_chart():
    rec = parse_chart_pdf(_real("isolatek-s721-20-20joists/cbcaee95fca6.pdf"))
    assert rec.design == "S721" and len(rec.rows) == 186
    assert rec.rating_columns == ["1 Hr", "1-1/2 Hr", "2 Hr", "3 Hr"]
    assert rec.rating_column_markers == ["+"] * 4
    assert rec.chart_date == "10/7/2013" and "ISOLATEK" in rec.products
    assert rec.rows[0].member_label == "8K1" and rec.rows[0].not_rated == [True] * 4
    assert rec.rows[1].member_label == "10K1" and rec.rows[1].thickness_in == [
        0.75,
        1.1875,
        1.4375,
        2.3125,
    ]
    assert rec.rows[1].depth_in == 10.0 and rec.rows[1].approx_wt == 5.1
    assert rec.rows[-1].member_label == "72DLH19" and rec.rows[-1].section == "Unrestrained Beam"
    assert [f.marker for f in rec.footnotes] == ["+"]
    assert rec.footnotes[0].text.startswith("+Reduced thicknesses are available when metal lath")
    assert rec.footnotes[0].columns == rec.rating_columns
    assert rec.notes == []


def test_real_n307_albi_driclad_chart():
    rec = parse_chart_pdf(_real("isolatek-n307-1d712d/d7ebd6945e03.pdf"))
    assert rec.design == "N307" and rec.chart_date is None and rec.products == "Albi DriClad"
    assert rec.condition == "All-Fluted Deck Lightweight and Normal Weight Concrete"
    assert rec.rating_columns == ["1 Hr", "1-1/2 Hr", "2 Hr"] and rec.factor_kind == "W/D"
    assert len(rec.rows) == 266 and sorted({r.page for r in rec.rows}) == [1, 2, 3, 4, 5, 6, 7]
    assert rec.rows[0].member_label == "W44 x 335" and rec.rows[0].metric_label == "W1120 x 498"
    carried = rec.rows[1]
    assert carried.member_label == "W44 x 290" and carried.metric_member_label == "W1120 x 432"
    assert carried.wd == 2.2 and carried.md == 129.8 and carried.hp_a == 60.9
    assert carried.thickness_as_printed == ["3/4", "3/4", "1-5/8"]
    # the source page prints a single NR cell for W10 x 30 on page 6: noted, never padded
    assert rec.notes == ["p6: row 'W10 x 30' has 1 of 3 thickness cells"]
    assert rec.rows[-1].member_label == "W4 x 13" and rec.rows[-1].not_rated == [True] * 3


def test_real_x313_albi_driclad_columns_chart():
    rec = parse_chart_pdf(_real("isolatek-x313-9af374/5a425a3184ea.pdf"))
    assert rec.design == "X313" and rec.chart_date == "8/26/2025"
    assert rec.products == "Albi DriClad"
    assert rec.condition == "Wide Flange Structural Steel Columns"
    assert rec.rating_columns == ["1 Hr", "2 Hr", "3 Hr", "4 Hr"]
    assert len(rec.rows) == 266 and rec.notes == []
    assert rec.rows[1].member_label == "W44 x 290" and rec.rows[1].metric_member_label == (
        "W1120 x 432"
    )
    assert rec.rows[1].wd == 1.97 and rec.rows[1].thickness_in == [0.75, 1.5, 1.5, 1.5]
    w230 = next(r for r in rec.rows if r.member_label == "W44 x 230")
    assert w230.thickness_as_printed == ["3/4", "1-1/2", "2-1/2", "NR"]
    assert w230.not_rated == [False, False, False, True]


def test_split_rating_header_and_second_table_with_own_columns(tmp_path):
    """N815: the '2-1/2 Hour' header is broken over two lines ('2-1/2-' / 'Hour'); N759: a
    second table with its own rating columns follows on a later page, and its rows carry those
    columns instead of the record's."""
    f = tmp_path / "N815.pdf"
    _pages_pdf(
        f,
        [
            [
                "N815 - Half-Flange Tip Option",
                "Cellular or Corrugated Deck",
                "Lightweight Concrete",
                "CAFCO® BLAZE-SHIELD® II, HP & ISOLATEK® Type II, HP",
                "ASTM",
                "Desig.",
                "W/D",
                "Metric Desig.",
                "M/D",
                "Hp/A",
                "1-Hour",
                "1-1/2 Hour",
                "2-Hour",
                "2-1/2-",
                "Hour",
                "3-Hour",
                "W44 x 335",
                "2.52",
                "W1120 x 498",
                "148.7",
                "53.2",
                "3/8",
                "1/2",
                "5/8",
                "13/16",
                "1",
                "290",
                "2.2",
                "432",
                "129.8",
                "60.9",
                "3/8",
                "9/16",
                "3/4",
                "15/16",
                "1-1/8",
            ],
            [
                "N815 - Half-Flange Tip Option",
                "ASTM",
                "Desig.",
                "W/D",
                "Metric Desig.",
                "M/D",
                "Hp/A",
                "2-1/2 Hour 3-1/2 Hour",
                "W44 x 335",
                "2.52",
                "W1120 x 498",
                "148.7",
                "53.2",
                "7/16",
                "5/8",
                "290",
                "2.2",
                "432",
                "129.8",
                "60.9",
                "1/2",
                "11/16",
            ],
        ],
    )
    rec = parse_chart_pdf(f)
    assert rec.rating_columns == ["1 Hr", "1-1/2 Hr", "2 Hr", "2-1/2 Hr", "3 Hr"]
    # "N815 - Half-Flange Tip Option" matches the existing "flange" condition keyword
    assert rec.condition.endswith("Cellular or Corrugated Deck Lightweight Concrete")
    assert [r.member_label for r in rec.rows] == ["W44 x 335", "W44 x 290"] * 2
    assert rec.rows[0].thickness_as_printed == ["3/8", "1/2", "5/8", "13/16", "1"]
    assert rec.rows[0].rating_columns is None and rec.rows[1].thickness_in[4] == 1.125
    assert rec.rows[2].page == 2 and rec.rows[2].rating_columns == ["2-1/2 Hr", "3-1/2 Hr"]
    assert rec.rows[2].thickness_as_printed == ["7/16", "5/8"]
    assert rec.rows[3].metric_member_label == "W1120 x 432"
    assert rec.notes == []
    out = write_chart(rec, tmp_path / "out")
    csv_lines = (tmp_path / "out" / "N815.csv").read_text(encoding="utf-8-sig").splitlines()
    assert csv_lines[0].endswith("1 Hr,1-1/2 Hr,2 Hr,2-1/2 Hr,3 Hr,3-1/2 Hr")
    assert csv_lines[1].endswith(",3/8,1/2,5/8,13/16,1,")
    assert csv_lines[3].endswith(",,,,7/16,,5/8")
    assert out.exists()


def test_pipe_fraction_wall_metric_under_ten_and_digit_footnote(tmp_path):
    """X650 HSS P: nominal diameter + fraction wall family rows, wall-only continuation rows
    whose metric wall is a bare number under 10 ('9.3'); a '++' header marker whose note starts
    with a digit ('++3 hr. thickness from design N826')."""
    f = tmp_path / "X650 HSS P.pdf"
    _lines_pdf(
        f,
        [
            "Page 1",
            "6/26/2012",
            "X650",
            "HSS Structural Steel Pipe Columns",
            "Nominal Dia.",
            "Wall Thk",
            "A/P",
            "Metric Desig.",
            "M/D",
            "Hp/A",
            "1-Hour",
            "1-1/2 Hour",
            "2-Hour++",
            "20.00",
            "1/2",
            "0.49",
            "508 x 12.4",
            "92.6",
            "85.3",
            "0.097",
            "0.138",
            "0.202",
            "3/8",
            "0.37",
            "9.3",
            "69.9",
            "113.1",
            "0.117",
            "NR",
            "NR",
            "18.00",
            "1/2",
            "0.49",
            "457 x 12.3",
            "92.4",
            "85.6",
            "0.097",
            "0.138",
            "0.202",
            "++3 hr. thickness from design N826",
            "CAFCO® SprayFilm® WB 3 and WB 4 & ISOLATEK® Type WB 3 and WB 4",
        ],
    )
    rec = parse_chart_pdf(f)
    assert rec.factor_kind == "A/P" and rec.rating_column_markers == ["", "", "++"]
    assert [r.member_label for r in rec.rows] == [
        "SP 20.00 x 1/2",
        "SP 20.00 x 3/8",
        "SP 18.00 x 1/2",
    ]
    cont = rec.rows[1]
    assert (
        cont.wd == 0.37 and cont.metric_label == "9.3" and cont.metric_member_label == "508 x 9.3"
    )
    assert cont.md == 69.9 and cont.hp_a == 113.1
    assert cont.thickness_as_printed == ["0.117", "NR", "NR"]
    assert cont.thickness_in == [0.117, None, None] and cont.not_rated == [False, True, True]
    assert rec.rows[2].family_label == "SP 18.00" and rec.rows[2].metric_label == "457 x 12.3"
    assert [(fn.marker, fn.columns) for fn in rec.footnotes] == [("++", ["2 Hr"])]
    assert rec.footnotes[0].text == "++3 hr. thickness from design N826"
    assert rec.products.startswith("CAFCO® SprayFilm") and rec.notes == []


def test_fused_thickness_cells_are_split_but_joist_mixed_numbers_are_not(tmp_path):
    """X790 RT: the text layer fuses the last two cells of a row ("2     2-11/16"); a joist mixed
    number ("1  3/16") is a single cell."""
    f = tmp_path / "X790 RT.pdf"
    _lines_pdf(
        f,
        [
            "X790",
            "Structural Steel Rectangular Tube Columns",
            "CAFCO® 300 Series",
            "ASTM Desig.",
            "Wall Thk",
            "A/P",
            "Metric Desig.",
            "M/D",
            "Hp/A",
            "1-Hour 1-1/2 Hour",
            "2-Hour 3-Hour",
            "4-Hour",
            "18 x 6",
            "1/2",
            "0.48",
            "457 x 152 x 12.7",
            "93.2",
            "84.8",
            "3/8",
            "9/16",
            "7/8",
            "1-3/8",
            "1-13/16",
            "1/4",
            "0.24",
            "x 6.4",
            "48.4",
            "163.3",
            "11/16",
            "1",
            "1-3/8",
            "2     2-11/16",
        ],
    )
    rec = parse_chart_pdf(f)
    assert rec.rating_columns == ["1 Hr", "1-1/2 Hr", "2 Hr", "3 Hr", "4 Hr"]
    assert [r.member_label for r in rec.rows] == ["RT 18 x 6 x 1/2", "RT 18 x 6 x 1/4"]
    assert rec.rows[1].thickness_as_printed == ["11/16", "1", "1-3/8", "2", "2-11/16"]
    assert rec.rows[1].thickness_in == [0.6875, 1.0, 1.375, 2.0, 2.6875]
    assert rec.rows[1].metric_label == "x 6.4" and rec.rows[1].metric_member_label == (
        "457 x 152 x 6.4"
    )
    assert rec.notes == []
    joist = tmp_path / "J.pdf"
    _lines_pdf(
        joist,
        [
            "N999",
            "Protected Roof Deck",
            "CAFCO® 300 Series",
            "Joist",
            "Designation",
            "Depth",
            "(in.)",
            "Approx. Wt",
            "(lbs./ft.)",
            "1-Hour",
            "2-Hour",
            "10K1",
            "10",
            "5.1",
            "1  3/16",
            "2  5/16",
        ],
    )
    rec2 = parse_chart_pdf(joist)
    assert len(rec2.rows) == 1 and rec2.rows[0].thickness_in == [1.1875, 2.3125]
    assert rec2.notes == []


def test_single_spaced_bare_integers_are_not_split_into_cells():
    """N805r AF & C: corrupted duplicate lines like "97 8" and "1 37" (a weight or ratio with its
    decimal point dropped) must not be read as two thickness cells, which would manufacture rows
    such as 'W40 x 97'. Only a run of two or more spaces separates fused cells."""
    from ffs.importers.isolatek_chart import _normalize_lines

    assert _normalize_lines(["97 8"]) == ["97 8"]
    assert _normalize_lines(["1 37"]) == ["1 37"]
    assert _normalize_lines(["2     2-11/16"]) == ["2", "2-11/16"]
    assert _normalize_lines(["NR  NR"]) == ["NR", "NR"]
    assert _normalize_lines(["1  3/16"]) == ["1  3/16"]
