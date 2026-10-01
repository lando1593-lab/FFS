from pathlib import Path

import pymupdf
import pytest

from ffs.importers.edge_drawing_report import parse_drawing_report, write_drawing_report

SHOP = Path(__file__).resolve().parents[2] / "data" / "shop_drawings"


def _report(path):
    doc = pymupdf.open()
    cover = doc.new_page()
    for x, y, t in [
        (373, 15, "Report Name:"),
        (436, 15, "Fireproofing Drawing Report"),
        (385, 34, "Print Date:"),
        (436, 34, "7/31/2023 2:19:07 PM"),
        (413, 46, "Bid:"),
        (436, 46, "Test Project"),
        (29, 105, "Section:"),
        (60, 105, "Section 1"),
        (29, 120, "Page:"),
        (60, 120, "S121-Second Floor"),
    ]:
        cover.insert_text((x, y), t, fontsize=8)
    p = doc.new_page()
    for x, y, t in [
        (29, 105, "Page:"),
        (60, 105, "S121-Second Floor"),
        (430, 105, "Calcs Blaze Shield (Type II)"),
        (12, 122, "Legend"),
        (60, 122, "Description"),
        (349, 122, "Test"),
        (431, 122, "Hours"),
        (499, 122, "Thickness"),
    ]:
        p.insert_text((x, y), t, fontsize=8)
    rows = [
        ("W 10 X 54 - COLUMN C2", "X829", "2.00", '1-5/16"'),
        ("W 18 X 35 - PRIMARY BEAM 4 Sides", "N823 NW C", "2.00", '15/16"'),
        ("L 4 X 4 X 3/8", "X829", "2.00", '1-9/16"'),
        ("L 2 X 2 X 3/16 Bridging", "X829", "1.00", '1-3/8"'),
        ('JOIST 16"', "P819F B", "1.00", '7/8"'),
        ("STEEL DECK TYPE B (1.33 Exp Factor)", "P819F B", "1.00", '1/2"'),
        ("HSS 6 X 6 X 1/4 C3", "X827", "2.00", '2-1/16"'),
        ("C 8 X 11.5 - AM STD", "X829", "2.00", '1-7/16"'),
    ]
    y = 139
    for desc, code, hrs, thk in rows:
        for x, t in [(60, desc), (335, code), (437, hrs), (509, thk)]:
            p.insert_text((x, y), t, fontsize=8)
        y += 16.7
    doc.save(path)
    doc.close()


def test_drawing_report_legend_rows(tmp_path):
    f = tmp_path / "rep.pdf"
    _report(f)
    rep = parse_drawing_report(f)
    assert (rep.report_name, rep.project, rep.print_date) == (
        "Fireproofing Drawing Report",
        "Test Project",
        "7/31/2023 2:19:07 PM",
    )
    assert len(rep.sheets) == 1 and rep.sheets[0].kind == "drawing_report"
    sh = rep.sheets[0]
    assert sh.sheet_label == "S121-Second Floor" and sh.product_hint == "Blaze Shield (Type II)"
    rows = {r.description: r for r in sh.rows}
    assert len(rows) == 8 and rep.notes == []
    col = rows["W 10 X 54 - COLUMN C2"]
    assert (col.member_label, col.canonical, col.role, col.extra) == (
        "W 10 X 54",
        "W10X54",
        "column",
        {"column_mark": "C2"},
    )
    assert (col.design_code, col.design, col.design_suffix, col.design_tokens) == (
        "X829",
        "X829",
        None,
        [],
    )
    assert (col.hours, col.thickness_as_printed, col.thickness_in) == (2.0, '1-5/16"', 1.3125)
    beam = rows["W 18 X 35 - PRIMARY BEAM 4 Sides"]
    assert (beam.canonical, beam.role, beam.sides) == ("W18X35", "primary_beam", 4)
    assert (beam.design, beam.design_tokens) == ("N823", ["NW", "C"])
    ang = rows["L 4 X 4 X 3/8"]
    assert (ang.canonical, ang.role) == ("L4X4X3/8", "angle")
    br = rows["L 2 X 2 X 3/16 Bridging"]
    assert (br.member_label, br.canonical, br.role) == ("L 2 X 2 X 3/16", "L2X2X3/16", "bridging")
    j = rows['JOIST 16"']
    assert (j.role, j.canonical, j.extra, j.design, j.design_suffix, j.design_tokens) == (
        "joist",
        None,
        {"joist_depth_in": 16.0},
        "P819",
        "F",
        ["B"],
    )
    deck = rows["STEEL DECK TYPE B (1.33 Exp Factor)"]
    assert deck.role == "deck" and deck.extra == {"deck_type": "B", "exposure_factor": 1.33}
    hss = rows["HSS 6 X 6 X 1/4 C3"]
    assert (hss.member_label, hss.canonical, hss.role) == ("HSS 6 X 6 X 1/4", "HSS6X6X1/4", "hss")
    ch = rows["C 8 X 11.5 - AM STD"]
    assert (ch.canonical, ch.role) == ("C8X11.5", "channel")
    js = write_drawing_report(rep, tmp_path / "out")
    assert js.exists() and (tmp_path / "out" / "rep.csv").read_text().count("\n") == 9


@pytest.mark.skipif(not SHOP.exists(), reason="shop drawings not present")
def test_real_ocps_report_if_present():
    import glob

    hits = glob.glob(str(SHOP / "*OCPS*.pdf"))
    if not hits:
        pytest.skip("OCPS report not present")
    rep = parse_drawing_report(hits[0])
    assert rep.project == "OCPS - OTC @ East Campus" and len(rep.sheets) == 10
    assert sum(len(s.rows) for s in rep.sheets) == 104 and rep.notes == []
    codes = {r.design_code for s in rep.sheets for r in s.rows}
    assert {"N823 NW C", "X829", "P819F B", "X827"} <= codes
    assert all(r.swatch_rgb is not None for s in rep.sheets for r in s.rows)
