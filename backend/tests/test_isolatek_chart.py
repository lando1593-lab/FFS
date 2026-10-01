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
