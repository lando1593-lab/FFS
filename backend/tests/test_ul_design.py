import os
from pathlib import Path

import pytest

from ffs.importers.ul_design import parse_design_pdf, parse_design_text

MINI = """4/24/2019
FIRE-RESISTANCE RATINGS - ANSI/UL 263
UL Product iQ
https://iq.ulprospector.com/en/profile?e=99999
1/2
BXUV.X999 - FIRE-RESISTANCE RATINGS - ANSI/UL 263
Design No. X999
May 03, 2018
Ratings — 1, 2, 3 Hr
1. Spray-Applied Fire Resistive Materials* — Applied by spraying to the thickness shown in the table below.
The thickness required for rating periods of 1 h, 2 h, 3 h of contour sprayed columns with W/D=0.30-0.55 may be determined by the equation:
R
h =  
0.95 (W/D) + 0.45
Where:
h=Protection material thickness in the range 0.375-3.75 in.
Column 
Size
W/D
Min Thkns In.
1 Hr
2 Hr
3 Hr
W8X10
0.33
1-1/4
2-5/16
3-9/16
*W6X16
0.57
11/16
1-9/16
2-7/16
* = note about the 1/2 hour rating.
EXAMPLE MFG CO — Type Z-1 or Z-2.
2. Steel Column — Min. sizes as shown above in Item 1.
* Indicates such products shall bear the UL Mark.
Last Updated on 2018-05-03
UL permits the reproduction of the material contained in the Online Certification Directory subject to conditions.
"""

BEAM = """Design No. S999
May 08, 2018
Restrained Beam Ratings — 1, 1-1/2, 2 or 3 Hr. (See Item 6)
Unrestrained Beam Ratings — 1, 1-1/2, 2 or 3 Hr. (See Item 6)
1. Steel Beam — W8X28 min size.
6. Spray-Applied Fire Resistive Materials* — Applied by spraying to the final thicknesses shown below.
Restrained & Unrestrained 
Beam Rating Hr
 
Min Thkns In.
1
5/8
1-1/2
15/16
2
1-5/8
3
2-9/16
EXAMPLE MFG CO — Type D-C/F, II, or Type II HS.
Last Updated on 2018-05-08
"""


def test_column_design_mini():
    rec = parse_design_text(MINI)
    assert rec.design_no == "X999" and rec.member_category_guess.startswith("column")
    assert rec.design_date == "May 03, 2018" and rec.last_updated == "2018-05-03"
    assert rec.snapshot_date == "4/24/2019" and rec.source_url.endswith("e=99999")
    assert rec.ratings[0].hours == [1.0, 2.0, 3.0]
    assert len(rec.equations) == 1
    eq = rec.equations[0]
    assert (
        (eq.a, eq.b) == (0.95, 0.45)
        and eq.wd_range == (0.30, 0.55)
        and eq.h_range_in == (0.375, 3.75)
    )
    assert eq.item_no == "1"
    assert len(rec.tables) == 1
    t = rec.tables[0]
    assert t.kind == "size_wd" and t.rating_columns == ["1 Hr", "2 Hr", "3 Hr"]
    assert [r.canonical for r in t.rows] == ["W8X10", "W6X16"]
    assert t.rows[0].wd == 0.33 and t.rows[0].values_in == [1.25, 2.3125, 3.5625]
    assert t.rows[1].note == "*"
    assert rec.items[0].is_sfrm and rec.items[0].manufacturers[0].name == "EXAMPLE MFG CO"
    assert rec.sfrm_manufacturers[0].text.startswith("Type Z-1")
    assert rec.reproduction_notice and rec.reproduction_notice.startswith("UL permits")


def test_beam_design_mini():
    rec = parse_design_text(BEAM)
    assert rec.design_no == "S999" and rec.member_category_guess.startswith("roof beam")
    assert [r.kind for r in rec.ratings] == ["Restrained Beam Ratings", "Unrestrained Beam Ratings"]
    assert rec.ratings[0].see == "See Item 6" and rec.ratings[0].hours == [1.0, 1.5, 2.0, 3.0]
    t = rec.tables[0]
    assert t.kind == "rating_rows" and t.rating_fields == 1 and t.item_no == "6"
    assert [r.cells for r in t.rows] == [
        ["1", "5/8"],
        ["1-1/2", "15/16"],
        ["2", "1-5/8"],
        ["3", "2-9/16"],
    ]
    assert t.rows[3].values_in == [2.5625]


TUBES = """Design No. X998
May 03, 2018
Ratings — 1, 1-1/2, 2, 3, 4 Hr
2. Spray-Applied Fire Resistive Materials* — Applied to the thicknesses shown.
The min thickness required for contour sprayed steel pipes or tubes are shown on the table below:
Min 
Column 
Size In.
 
A/P
 
 
1 Hr
 
 
1-1/2 Hr
 
Min Thkns 
In. 2 Hr
 
 
3 Hr
 
 
4 Hr
SP 4x0.237
0.22
11/16
1
1-3/8
2-1/16
2-3/4
ST 4x4x0.375
0.34
7/16
3/4
1
1-9/16
2-1/8
ST20x20x0.75 in
0.72
5/16
1/2
11/16
1-1/16
1-7/16
EXAMPLE MFG CO — Type 300.
Last Updated on 2018-05-03
"""


def test_tube_table_with_split_header():
    rec = parse_design_text(TUBES)
    assert len(rec.tables) == 1
    t = rec.tables[0]
    assert t.rating_columns == ["1 Hr", "1-1/2 Hr", "2 Hr", "3 Hr", "4 Hr"]
    assert [r.label for r in t.rows] == ["SP 4x0.237", "ST 4x4x0.375", "ST20x20x0.75 in"]
    assert t.rows[1].wd == 0.34 and t.rows[1].values_in == [0.4375, 0.75, 1.0, 1.5625, 2.125]
    assert t.rows[0].canonical is None


FLOOR = """Design No. N998
May 07, 2018
Restrained Assembly Ratings — 1, 1-1/2, 2, 3 and 4 Hr
6. Spray-Applied Fire Resistive Materials* — Applied by spraying.
Normal Weight Concrete, Fluted Floor and Form Units, Min Thkns In.
Rating, Hr
Restrained Beam
Unrestrained Beam
1
1/2
1/2
1-1/2
3/4
3/4
2-1/2*
1-1/4
1-3/8
6A. Spray-Applied Fire Resistive Materials* — As an alternate.
Restrained Assembly 
Rating Hr
Unrestrained 
Beam Rating Hr
Min Beam 
Size
Min Thkns 
on Beam In.
1, 1-1/2, 2, 3
1-1/2
W10x29
3/4
1, 1-1/2, 2
1
W8x28
1/2
Last Updated on 2018-05-07
"""


def test_floor_beam_tables_with_text_columns():
    rec = parse_design_text(FLOOR)
    assert len(rec.tables) == 2
    t6, t6a = rec.tables
    assert (
        t6.item_no == "6"
        and t6.rating_fields == 1
        and t6.value_columns == ["Restrained Beam", "Unrestrained Beam"]
    )
    assert t6.condition.startswith("Normal Weight Concrete")
    assert [r.cells for r in t6.rows] == [
        ["1", "1/2", "1/2"],
        ["1-1/2", "3/4", "3/4"],
        ["2-1/2*", "1-1/4", "1-3/8"],
    ]
    assert t6a.item_no == "6A" and t6a.rating_fields == 2
    assert t6a.value_columns == ["Min Beam Size", "Min Thkns on Beam In."]
    assert t6a.rows[0].cells == ["1, 1-1/2, 2, 3", "1-1/2", "W10x29", "3/4"] and t6a.rows[
        0
    ].values_in == [None, 0.75]


REF = Path(os.environ.get("FFS_REFERENCE_LIBRARY", "/home/user/FFS/data/reference_library"))


@pytest.mark.skipif(not (REF / "X829.pdf").exists(), reason="reference library not present")
def test_real_x829():
    rec = parse_design_pdf(REF / "X829.pdf")
    assert (
        rec.design_no == "X829"
        and rec.last_updated == "2018-05-03"
        and rec.snapshot_date == "4/24/2019"
    )
    assert [(e.a, e.b, e.wd_range) for e in rec.equations] == [
        (1.01, 0.66, (0.55, 7.0)),
        (0.95, 0.45, (0.30, 0.55)),
    ]
    assert len(rec.tables) == 2, [len(t.rows) for t in rec.tables]
    main, reduced = rec.tables
    assert [r.canonical for r in main.rows] == [
        "W8X10",
        "W6X16",
        "W8X28",
        "W10X49",
        "W12X106",
        "W14X233",
        "W14X730",
    ]
    assert main.rows[0].values_in == [1.25, 1.8125, 2.3125, 3.5625, None]
    assert reduced.condition and "one-half" in reduced.condition
    assert len(reduced.rows) == 7 and reduced.rows[-1].canonical == "W14X730"
    assert reduced.rows[-1].values_in == [0.375, 0.375, 0.375, 0.5, 0.6875]
    assert any(m.name == "ISOLATEK INTERNATIONAL" for m in rec.sfrm_manufacturers)


@pytest.mark.skipif(not (REF / "P922.pdf").exists(), reason="reference library not present")
def test_real_p922():
    rec = parse_design_pdf(REF / "P922.pdf")
    assert rec.design_no == "P922" and rec.last_updated == "2019-02-11"
    assert [r.kind for r in rec.ratings] == [
        "Restrained Assembly Rating",
        "Unrestrained Assembly Rating",
        "Unrestrained Beam Rating",
    ]
    t7 = [t for t in rec.tables if t.item_no == "7"]
    assert len(t7) == 4
    assert t7[0].rating_fields == 2 and t7[0].value_columns[0].endswith("W6x16")
    assert t7[0].rows[0].cells == ["1", "1", "7/16", "15/16"]
    iso = [m for m in rec.sfrm_manufacturers if m.name == "ISOLATEK INTERNATIONAL"]
    assert len(iso) == 4 and "400AC" in iso[0].text  # items 7A, 7B, 7C, 7E


@pytest.mark.skipif(not (REF / "S801.pdf").exists(), reason="reference library not present")
def test_real_s801():
    rec = parse_design_pdf(REF / "S801.pdf")
    assert rec.design_no == "S801"
    t = rec.tables[0]
    assert t.item_no == "6" and [r.values_in[0] for r in t.rows] == [0.625, 0.9375, 1.625, 2.5625]
