import pymupdf

from ffs.importers.isolatek_chart import parse_chart_pdf


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
