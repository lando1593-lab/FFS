"""Importer test on a synthetic mimic of The EDGE spray-report layout (hermetic), plus an
optional check against a real report when FFS_SAMPLE_SPRAY_REPORT points at one."""

import os
from pathlib import Path

import pymupdf
import pytest

from ffs.importers.edge_spray_report import extract_plan_images, parse_spray_report

ROWS = [
    ('W12X26 - 0.5000"', "Beam - 3 Side", "1/2 inch", (1, 0, 0), "solid"),
    ('W16X36 - 0.4375"', "Beam - 3 Side", "7/16 inch", (0, 1, 0), "solid"),
    ('W21X44 - 0.4375"', "Beam - 3 Side", "7/16 inch", (1, 0, 0), "dashed"),
    ('W8X10 - 0.6250"', "Beam - 3 Side", "5/8 inch", (1, 0, 0), "solid"),  # colour reuse → QA
    ('HSS6X6X1/4 - 0.6250"', "Column - 4 Side", "5/8 inch", (0, 0, 1), "solid"),
]


def _mimic(path: Path) -> None:
    doc = pymupdf.open()
    p = doc.new_page(width=612, height=792)
    p.insert_text((17.3, 32), "Spray Report - 2-S102 - STRUCTURAL FRAMING", fontsize=15)
    p.insert_text((17.3, 52), "PLAN - LEVEL 2", fontsize=15)
    p.insert_text((509, 27), "Bid Date - 01/02/2026", fontsize=8.3)
    p.insert_text((488, 40), "Estimator - Test Person", fontsize=8.3)
    p.insert_text((510, 65), "Status - Not Assigned", fontsize=8.3)
    p.insert_text(
        (17.3, 80), "CAFCO400 - Isolatek Cafco 400 - Med Density - Cement Based - ", fontsize=12
    )
    p.insert_text((17.3, 96), "Inspector Report", fontsize=12)
    p.insert_text((17.3, 123), "N708 - 2HR", fontsize=9.9)
    p.insert_text((17.3, 139), "X790 - 2HR - Columns", fontsize=9.9)
    p.insert_text((17.3, 188), "Linear Spray Items", fontsize=8)
    p.insert_text((21.6, 205), "Color", fontsize=6.9)
    p.insert_text((146.9, 205), "Member", fontsize=6.9)
    y = 221.0
    sh = p.new_shape()
    for i, (member, typ, thk, col, pat) in enumerate(ROWS):
        if i == 4:
            p.insert_text((17.3, y + 10), "Count Spray Items", fontsize=8)
            y += 34
        p.insert_text((146.9, y), member, fontsize=6.9)
        p.insert_text((454.3, y), typ, fontsize=6.9)
        p.insert_text((561.7, y), thk, fontsize=6.9)
        if pat == "solid":
            sh.draw_line((26.3, y - 2.5), (134.3, y - 2.5))
            sh.finish(color=col, width=3.48)
        else:
            for k in range(13):
                x = 26.3 + k * 8.4
                sh.draw_rect(pymupdf.Rect(x, y - 4.2, x + 4.2, y - 0.7))
            sh.finish(color=None, fill=col)
        y += 14.4
    sh.commit()
    # plan page with two raster strips
    p2 = doc.new_page(width=792, height=612)
    p2.insert_text(
        (17.3, 32), "Spray Report - 2-S102 - STRUCTURAL FRAMING PLAN - LEVEL 2", fontsize=15
    )
    for j, (y0, h) in enumerate(((93, 136), (229, 136))):
        pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 400, 80), False)
        pix.clear_with(40 + j * 100)
        p2.insert_image(pymupdf.Rect(62, y0, 730, y0 + h), pixmap=pix)
    doc.save(path)
    doc.close()


def test_parse_mimic(tmp_path):
    pdf = tmp_path / "mimic.pdf"
    _mimic(pdf)
    rep = parse_spray_report(pdf)
    assert len(rep.sheets) == 1
    sh = rep.sheets[0]
    assert sh.sheet_no == "2-S102"
    assert sh.level_guess == "LEVEL 2"
    assert sh.product_code == "CAFCO400" and sh.product_name == "Isolatek Cafco 400"
    assert sh.report_variant == "Inspector Report"
    assert [d["design"] for d in sh.designs] == ["N708", "X790"]
    assert sh.designs[1]["note"] == "Columns" and sh.designs[1]["rating_hr"] == 2.0
    assert sh.plan_page == 2 and sh.plan_image_count == 2
    assert [it.canonical_section for it in sh.items] == [
        "W12X26",
        "W16X36",
        "W21X44",
        "W8X10",
        "HSS6X6X1/4",
    ]
    assert [it.section for it in sh.items] == ["linear"] * 4 + ["count"]
    assert [it.thickness_in for it in sh.items] == [0.5, 0.4375, 0.4375, 0.625, 0.625]
    assert all(it.thickness_consistent for it in sh.items)
    assert sh.items[4].role == "column" and sh.items[4].sides == 4
    assert [it.swatch.pattern for it in sh.items] == ["solid", "solid", "dashed", "solid", "solid"]
    assert sh.items[0].swatch.rgb_hex == "#ff0000" and sh.items[2].swatch.rgb_hex == "#ff0000"
    assert any("reused" in n for n in sh.qa_notes), sh.qa_notes
    imgs = extract_plan_images(pdf, tmp_path / "plans")
    assert len(imgs) == 1
    pix = pymupdf.Pixmap(str(imgs[0]))
    assert pix.width == 400 and pix.height == 160


@pytest.mark.skipif(
    not os.environ.get("FFS_SAMPLE_SPRAY_REPORT"), reason="no sample report configured"
)
def test_parse_real_sample():
    rep = parse_spray_report(os.environ["FFS_SAMPLE_SPRAY_REPORT"])
    assert rep.sheets
    for sh in rep.sheets:
        for it in sh.items:
            assert it.thickness_consistent is not False, (sh.sheet_no, it)
