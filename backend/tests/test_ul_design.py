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


# --- intumescent column design (X649 layout): decimal thickness tables with NR cells, an inch and
# a metric (M/D + Hp/A) table, inline "T = k/(W/D)" equations restricted to one rating each
INTUMESCENT_COLUMN = """4/24/2019
FIRE-RESISTANCE RATINGS - ANSI/UL 263 | UL Product iQ
https://iq.ulprospector.com/en/profile?e=15402
1/2
BXUV.X997 - FIRE-RESISTANCE RATINGS - ANSI/UL 263
Design No. X997
October 04, 2016
Ratings - 1, 1-1/2, 2 and 3 Hr. (See Item 2)
1. Steel Column — Wide flange steel columns with the minimum sizes shown in the tables below.
2. Mastic and Intumescent Coatings* — Coating spray, brush or trowel applied directly from containers to desired thickness. See tables
below for appropriate final dry thickness and applicable rating.
Steel 
Size
 
W/D
1 Hr Min 
Thickness, In.
1-1/2 Hr Min 
Thickness, In.
2 Hr Min 
Thickness, In.
3 Hr Min 
Thickness, In.
W8 x 10
0.33
0.145
0.266
NR
NR
W6 X 16
0.58
0.083
0.163
0.257

0.504
W14 x 283
3.00
0.023
0.033
0.050
0.116
NR = No Rating
As an alternate to the above table, the required thickness of coating (in inches) to be applied to all surfaces of wide flange steel columns
for 1 hour ratings, in the W/D range of 0.33 to 1.14, may be determined from the following equation:
T = 0.04785/(W/D)
Where T = Thickness of coating in the range of 0.042 to 0.145 in., W = Weight of steel column in pounds per linear foot, D = Heated
perimeter of steel column section in inches.
As an alternate to the above table, the required thickness of coating (in inches) to be applied to all surfaces of wide flange steel columns
for 3 hour ratings, in the W/D range of 0.58 to 1.64, may be determined from the following equation:
T = 0.3082/(W/D)
Where T = Thickness of coating in the range of 0.504 to 0.188 in., W = Weight of steel column in pounds per linear foot, D = Heated
perimeter of steel column section in inches.
As an alternate to the above, the following table listing metric units may be used.
Steel 
Size
 
M/D
 
Hp/A
1 Hr Min 
Thickness,
mm
1-1/2 Hr Min 
Thickness,
mm
2 Hr Min 
Thickness,
mm
3 Hr Min 
Thickness,
mm
W8 x 10
19.1
412
3.68
6.76
NR
NR
W16 x
100
79.4
99
0.91
1.76
2.78
5.76
NR = No Rating
As an alternate to the above table, the required thickness of coating (in mm) to be applied to all surfaces of wide flange steel columns for
1 hour ratings, in the M/D range of 19.1 to 66.9, may be determined from the following equation:
T = 71.6/(M/D)
Where T = Thickness of coating in the range of 1.07 to 3.68 mm, M = Weight of steel column in kilograms per linear meter, D = Heated
perimeter of steel column section in meters.
ISOLATEK INTERNATIONAL — Type SprayFilm-WB 3 and Type WB 3, Investigated for Interior General Purpose.
Last Updated on 2016-10-04
"""


def test_intumescent_decimal_tables_and_inline_equations():
    rec = parse_design_text(INTUMESCENT_COLUMN)
    assert rec.design_no == "X997" and rec.ratings[0].hours == [1.0, 1.5, 2.0, 3.0]
    assert len(rec.tables) == 2
    t_in, t_mm = rec.tables
    assert t_in.kind == "size_wd" and t_in.item_no == "2"
    assert t_in.rating_columns == ["1 Hr", "1-1/2 Hr", "2 Hr", "3 Hr"]
    assert t_in.units == "in" and t_in.ratio_names == ["W/D"] and t_in.condition is None
    assert [r.label for r in t_in.rows] == ["W8 x 10", "W6 X 16", "W14 x 283"]
    assert [r.canonical for r in t_in.rows] == ["W8X10", "W6X16", "W14X283"]
    # markers kept verbatim, never turned into numbers; the ratio cell kept as printed
    assert t_in.rows[0].cells == ["W8 x 10", "0.33", "0.145", "0.266", "NR", "NR"]
    assert t_in.rows[0].wd == 0.33 and t_in.rows[0].values_in == [0.145, 0.266, None, None]
    assert t_in.rows[1].values_in == [0.083, 0.163, 0.257, 0.504]  # page break inside the row
    assert t_in.rows[2].cells[1] == "3.00"
    assert t_in.notes == ["NR = No Rating"]
    assert t_mm.units == "mm" and t_mm.ratio_names == ["M/D", "Hp/A"]
    assert t_mm.rows[0].cells == ["W8 x 10", "19.1", "412", "3.68", "6.76", "NR", "NR"]
    assert t_mm.rows[1].label == "W16 x 100" and t_mm.rows[1].ratios == [79.4, 99.0]
    assert t_mm.rows[1].values == [0.91, 1.76, 2.78, 5.76]
    assert t_mm.rows[1].values_in == [None] * 4  # mm values are never passed off as inches
    eqs = rec.equations
    assert [
        (e.form, e.k, e.rating, e.rating_hours, e.wd_range, e.h_range, e.h_units) for e in eqs
    ] == [
        ("T = k / (W/D)", 0.04785, "1", 1.0, (0.33, 1.14), (0.042, 0.145), "in"),
        ("T = k / (W/D)", 0.3082, "3", 3.0, (0.58, 1.64), (0.504, 0.188), "in"),
        ("T = k / (M/D)", 71.6, "1", 1.0, (19.1, 66.9), (1.07, 3.68), "mm"),
    ]
    assert all(e.a is None and e.b is None and e.c is None and e.item_no == "2" for e in eqs)
    assert eqs[0].h_range_in == (0.042, 0.145) and eqs[2].h_range_in is None
    assert eqs[0].notes == []
    assert eqs[1].notes and "kept as printed" in eqs[1].notes[0]  # UL printed 0.504 to 0.188


# --- intumescent column design (Y615 layout): N/A cells and an equation table
INTUMESCENT_EQ_TABLE = """Design No. Y997
September 22, 2016
Ratings - 1, 1-1/2, 2, and 3 Hr. (See Item 2)
1. Steel Column — Wide flange steel columns with the minimum sizes shown in the tables below.
2. Mastic and Intumescent Coatings* — Coating spray or brush applied directly from containers to desired thickness. See tables below
for appropriate final dry thickness and applicable rating.
Steel 
Size
 
W/D
1 Hr Min 
Thickness, in.
1-1/2 Hr Min 
Thickness, in.
2 Hr Min 
Thickness, in.
3 Hr Min 
Thickness, in.
W6x12
0.44
0.093
N/A
N/A
N/A
W8x31
0.66
0.062
0.126
0.191
N/A
W10x49
0.84
0.049
0.099
0.150
0.307
N/A = Not Available
As an alternate to the above table, the required thickness of coating (in inches) to be applied to all surfaces of wide flange steel columns
may be determined from the equations listed below. The equations may only be used for the indicated hourly rating and for the
corresponding listed ranges of thickness and W/D.
Hourly  
Ratng
Thickness  
Equation, in.
Thickness  
Range, in.
W/D  
Ratio Range
1
T = 0.0408/(W/D)
0.021 to 0.093
0.44 to 3.00
1-1/2
T = 0.0833/(W/D)
0.028 to 0.126
0.66 to 3.00
2
T = 0.1258/(W/D)
0.042 to 0.191
0.66 to 3.00
3
T = 0.2576/(W/D)
0.086 to 0.307
0.84 to 3.00
Where T = Thickness of coating in inches, W = Weight of steel column in pounds per linear foot, and D = Heated perimeter of steel
column section in inches.
ISOLATEK INTERNATIONAL — Type SprayFilm WB 5 or Type WB 5, Investigated for Interior Conditioned Space and Interior General
Purpose
Last Updated on 2016-09-22
"""


def test_intumescent_equation_table_with_na_cells():
    rec = parse_design_text(INTUMESCENT_EQ_TABLE)
    assert len(rec.tables) == 1
    t = rec.tables[0]
    assert t.rating_columns == ["1 Hr", "1-1/2 Hr", "2 Hr", "3 Hr"] and t.units == "in"
    assert [r.cells for r in t.rows] == [
        ["W6x12", "0.44", "0.093", "N/A", "N/A", "N/A"],
        ["W8x31", "0.66", "0.062", "0.126", "0.191", "N/A"],
        ["W10x49", "0.84", "0.049", "0.099", "0.150", "0.307"],
    ]
    assert t.rows[0].values_in == [0.093, None, None, None]
    assert t.notes == ["N/A = Not Available"]
    assert [(e.rating, e.k, e.h_range_in, e.wd_range) for e in rec.equations] == [
        ("1", 0.0408, (0.021, 0.093), (0.44, 3.0)),
        ("1-1/2", 0.0833, (0.028, 0.126), (0.66, 3.0)),
        ("2", 0.1258, (0.042, 0.191), (0.66, 3.0)),
        ("3", 0.2576, (0.086, 0.307), (0.84, 3.0)),
    ]
    assert [e.rating_hours for e in rec.equations] == [1.0, 1.5, 2.0, 3.0]
    assert all(
        e.form == "T = k / (W/D)" and e.h_units == "in" and e.item_no == "2" for e in rec.equations
    )


EQ_TABLE_NO_HEADS = """Design No. Y996
September 22, 2016
Ratings - 1 and 2 Hr. (See Item 2)
2. Mastic and Intumescent Coatings* — Coating applied to the thickness determined from the equations below.
1
T = 0.0408/(W/D)
0.021 to 0.093
0.44 to 3.00
Last Updated on 2016-09-22
"""


def test_equation_table_without_column_heads_leaves_ranges_unassigned():
    rec = parse_design_text(EQ_TABLE_NO_HEADS)
    (eq,) = rec.equations
    assert eq.rating == "1" and eq.k == 0.0408
    assert eq.h_range is None and eq.h_range_in is None and eq.wd_range is None
    assert eq.notes and "not assigned" in eq.notes[0] and "0.021 to 0.093" in eq.notes[0]


# --- intumescent HSS beam design (N653 layout): "Rating Period (min)" heads, bare HSS sizes,
# mils and mm copies of each table under one heading
HSS_BEAM = """2/6/2020
| UL Product iQ
https://iq.ulprospector.com/en/profile?e=613324
1/2
BXUV.N997 -
Design No. N997
February 03, 2020
Restrained Beam Rating — 1, 1-1/2, 2, 2-1/2 and 3 Hr. (See Item 7)
Unrestrained Beam Rating — 1, 1-1/2, 2 and 2-1/2 Hr. (See Item 7)
1. Steel Tube Beam — ASTM A500 tube beams (46 or 50 ksi) having an A/P between 0.267 and 0.616.
7. Mastic and Intumescent Coatings* — Coating spray or brush applied in accordance with the manufacturer's instructions at
the min dry thickness as shown in the table below. The thickness shown below includes the primer thickness.
Unrestrained Beam Ratings:
HSS Steel Size
A/P
Rating Period (min)
60
90
120
150
Required Thickness (mils)
6x4x1/4
0.267
61
142
N/A
N/A
12x6x5/8
0.616
22
76
129
183
HSS Steel Size
A/P
Rating Period (min)
60
90
120
150
Required Thickness (mm)
6x4x1/4
0.267
1.56
3.6
N/A
N/A

12x6x5/8
0.616
0.56
1.92
3.28
4.64
Restrained Beam Ratings:
HSS Steel Size
A/P
Rating Period (min)
60
90
120
150
180
Required Thickness (mils)
6x4x1/4
0.267
61
95
N/A
N/A
N/A
ISOLATEK INTERNATIONAL — Type SprayFilm-WB 3 and Type WB3, Investigated for Interior General Purpose.
Last Updated on 2020-02-03
"""


def test_hss_beam_tables_in_minutes_mils_and_mm():
    rec = parse_design_text(HSS_BEAM)
    assert rec.design_no == "N997" and rec.snapshot_date == "2/6/2020"
    assert [r.kind for r in rec.ratings] == ["Restrained Beam Rating", "Unrestrained Beam Rating"]
    assert len(rec.tables) == 3
    assert all(t.item_no == "7" and t.kind == "size_wd" for t in rec.tables)
    t_mils, t_mm, t_r = rec.tables
    assert t_mils.rating_columns == ["60 min", "90 min", "120 min", "150 min"]
    assert t_mils.units == "mils" and t_mils.ratio_names == ["A/P"]
    assert t_mils.condition == "Unrestrained Beam Ratings:"
    assert t_mils.notes[0].startswith("introduced by: the min dry thickness")
    assert [r.label for r in t_mils.rows] == ["6x4x1/4", "12x6x5/8"]
    assert [r.canonical for r in t_mils.rows] == ["HSS6X4X1/4", "HSS12X6X5/8"]
    assert t_mils.rows[0].cells == ["6x4x1/4", "0.267", "61", "142", "N/A", "N/A"]
    assert t_mils.rows[0].wd == 0.267 and t_mils.rows[0].values == [61.0, 142.0, None, None]
    assert t_mils.rows[0].values_in == [0.061, 0.142, None, None]
    assert t_mm.units == "mm" and t_mm.condition == "Unrestrained Beam Ratings:"
    assert t_mm.notes[0].startswith("heading carried over")
    assert len(t_mm.rows) == 2 and t_mm.rows[1].values == [0.56, 1.92, 3.28, 4.64]
    assert t_mm.rows[0].values_in == [None] * 4
    assert t_r.condition == "Restrained Beam Ratings:" and t_r.notes == []
    assert t_r.rating_columns[-1] == "180 min"
    assert t_r.rows[0].values_in == [0.061, 0.095, None, None, None]


# --- dry-mix pipe/tube column design (X827 layout): "Rating, Hr." heads, an A/P column, "—"
# cells, and the thickness equation printed as a fraction
PIPE_TUBE = """Design No. X996
May 03, 2018
Ratings — 1, 1-1/2, 2, 3 and 4 Hr.
1. Steel Pipe or Tube Column — Steel circular pipe (SP) with diameter (ID) ranging from a minimum of 3 in. to a maximum of 32 in.
2. Spray-Applied Fire Resistive Materials* — Applied by spraying with water to the final thicknesses shown below.
The min thickness of Spray-Applied Fire Resistive Material required for various fire resistance ratings of contour sprayed steel pipes or
tubes are shown in the tables below.
Tube Steel Columns, Min Thkns, In.
Min Column Size
A/P
Rating, Hr.
1
1-1/2
2
3
4
ST 3x3x0.188
0.18
1
1-3/4
2-9/16
—
—
ST4x4x0.25
0.24
3/4
1-5/16
1-15/16
3
4-13/16
Pipe Columns, Min Thkns, In.
Min Column Size
A/P
Rating, Hr.
1
1-1/2
2
3
4
SP 3x0.188
0.18
1
3-3/4
2-9/16
—
—
ISOLATEK INTERNATIONAL — Type HP, D-C/F, II, or II HS. Investigated for exterior use.
 
As an alternate to the above tables, the required thickness of Spray-Applied Fire Resistive Materials to be applied to all surfaces of the
steel pipes or tubes for all rating periods may be determined from the following equation:
The thickness of sprayed for ratings of 1, 1-1/2, 2, 3, and 4 h of a steel pipe or tube may be determined by the equation:
R — 0.38
h =  
3.58 (A/P)
Where:
R = the hourly rating (hrs).
h = the thickness of protection material, min 0.35 - max 3.50 in.
A = the cross sectional area (sq in.)
P = the heated perimeter (in.)
The A/P ratio of the steel pipe or tube (see Item 2) shall range from 0.18 to 2.0.
The A/P ratio of a circular pipe is determined by:
t (d — t)
A/P = 
d
Last Updated on 2018-05-03
"""


def test_pipe_tube_ap_tables_and_fraction_equation():
    rec = parse_design_text(PIPE_TUBE)
    assert len(rec.tables) == 2
    tube, pipe = rec.tables
    assert tube.condition == "Tube Steel Columns, Min Thkns, In." and tube.units == "in"
    assert tube.rating_columns == ["1 Hr", "1-1/2 Hr", "2 Hr", "3 Hr", "4 Hr"]
    assert tube.ratio_names == ["A/P"] and tube.item_no == "2"
    assert [r.label for r in tube.rows] == ["ST 3x3x0.188", "ST4x4x0.25"]
    assert tube.rows[0].cells == ["ST 3x3x0.188", "0.18", "1", "1-3/4", "2-9/16", "—", "—"]
    assert tube.rows[0].wd == 0.18 and tube.rows[0].values_in == [1.0, 1.75, 2.5625, None, None]
    assert pipe.condition == "Pipe Columns, Min Thkns, In." and pipe.rows[0].label == "SP 3x0.188"
    (eq,) = rec.equations
    assert eq.form == "h = (R - c) / (k*(A/P))" and (eq.c, eq.k) == (0.38, 3.58)
    assert eq.factor == "A/P" and eq.r_units == "hours" and eq.item_no == "2"
    assert eq.h_range_in == (0.35, 3.5) and eq.h_units == "in" and eq.wd_range == (0.18, 2.0)
    assert eq.a is None and eq.b is None and eq.rating is None
    assert eq.as_printed == "R — 0.38 h = 3.58 (A/P)"
    assert eq.notes and "fraction layout" in eq.notes[0]


def test_find_design_no():
    from ffs.importers.ul_design import find_design_no

    assert find_design_no("Design No. X649\nOctober 04, 2016") == "X649"
    assert find_design_no("BXUV.N-653 - FIRE-RESISTANCE RATINGS") == "N653"
    assert find_design_no("Type WB 7 coating for use in Design No.  \nBS-RC-0021.") is None


def _tiny_pdf(path: Path, text: str) -> Path:
    import pymupdf

    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), text, fontsize=8)
    doc.save(path)
    doc.close()
    return path


def test_router_requires_a_bxuv_design_number(tmp_path):
    """A UL Certificate of Compliance mentions "Design No." and Product iQ but is not a design."""
    from ffs.importers.router import sniff

    cert = _tiny_pdf(
        tmp_path / "cert.pdf",
        "C E R T I F I C A T E O F C O M P L I A N C E\nISOLATEK INTERNATIONAL\n"
        "Type WB 7 coating for use in Design No.\nBS-RC-0021.\n"
        "See the UL Online Certifications Directory at https://iq.ulprospector.com",
    )
    design = _tiny_pdf(
        tmp_path / "design.pdf",
        "4/24/2019\nFIRE-RESISTANCE RATINGS - ANSI/UL 263 | UL Product iQ\n"
        "BXUV.X649 - FIRE-RESISTANCE RATINGS - ANSI/UL 263\nDesign No. X649\nOctober 04, 2016",
    )
    assert sniff(cert)[0] == "other"
    assert sniff(design)[0] == "ul_design"


# --- real fetched files (git-ignored); skipped when the library is absent
FETCHED = REF / "fetched" / "Isolatek"
X649_PDF = FETCHED / "isolatek-x649-bd0333" / "8eba86a78e05.pdf"
Y615_PDF = FETCHED / "isolatek-ul-Y615" / "c4917457a682.pdf"
N653_PDF = FETCHED / "isolatek-n653" / "f30e395c95d0.pdf"
X827_PDF = FETCHED / "isolatek-x827" / "6363c76b7976.pdf"
CERT_PDF = FETCHED / "isolatek-certificate-of-compliance-sprayfilm-type-wb7" / "fad86fbbfa12.pdf"


@pytest.mark.skipif(not X649_PDF.exists(), reason="reference library not present")
def test_real_x649():
    rec = parse_design_pdf(X649_PDF)
    assert rec.design_no == "X649" and rec.last_updated == "2016-10-04"
    assert rec.ratings[0].hours == [1.0, 1.5, 2.0, 3.0, 4.0]
    assert [(t.units, t.ratio_names, len(t.rows)) for t in rec.tables] == [
        ("in", ["W/D"], 33),
        ("mm", ["M/D", "Hp/A"], 33),
    ]
    t = rec.tables[0]
    assert t.rating_columns == ["1 Hr", "1-1/2 Hr", "2 Hr", "3 Hr", "4 Hr"]
    assert t.rows[0].cells == ["W8 x 10", "0.33", "0.145", "0.266", "NR", "NR", "NR"]
    assert t.rows[-1].label == "W14 x 283"
    assert t.rows[-1].values_in == [0.023, 0.033, 0.05, 0.116, 0.194]
    assert t.notes == ["NR = No Rating"]
    mm = rec.tables[1]
    assert mm.rows[-1].cells == ["W14 x 283", "176.0", "45", "0.59", "0.84", "1.28", "2.94", "4.92"]
    assert mm.rows[-1].values_in == [None] * 5
    wd_eqs = [e for e in rec.equations if e.factor == "W/D"]
    assert [(e.k, e.rating, e.wd_range, e.h_range_in) for e in wd_eqs] == [
        (0.04785, "1", (0.33, 1.14), (0.042, 0.145)),
        (0.0945, "1-1/2", (0.33, 1.64), (0.058, 0.266)),
        (0.1489, "2", (0.44, 1.64), (0.091, 0.338)),
        (0.3082, "3", (0.58, 1.64), (0.188, 0.504)),
        (0.749, "4", (1.72, 3.0), (0.433, 0.194)),
    ]
    assert [e.k for e in rec.equations if e.factor == "M/D"] == [71.6, 141.3, 222.7, 461.0, 1116.4]
    assert all(e.form.startswith("T = k /") and e.item_no == "2" for e in rec.equations)
    assert any(m.name == "ISOLATEK INTERNATIONAL" for m in rec.items[1].manufacturers)


@pytest.mark.skipif(not Y615_PDF.exists(), reason="reference library not present")
def test_real_y615():
    rec = parse_design_pdf(Y615_PDF)
    assert rec.design_no == "Y615" and rec.last_updated == "2016-09-22"
    assert [(t.units, len(t.rows)) for t in rec.tables] == [("in", 31), ("mm", 31)]
    t = rec.tables[0]
    assert t.rows[0].cells == ["W6x12", "0.44", "0.093", "N/A", "N/A", "N/A"]
    assert t.rows[-1].canonical == "W14X730" and t.rows[-1].wd == 6.68
    assert t.notes == ["N/A = Not Available"]
    inch = [e for e in rec.equations if e.factor == "W/D"]
    assert [(e.rating, e.k, e.h_range_in, e.wd_range) for e in inch] == [
        ("1", 0.0408, (0.021, 0.093), (0.44, 3.0)),
        ("1-1/2", 0.0833, (0.028, 0.126), (0.66, 3.0)),
        ("2", 0.1258, (0.042, 0.191), (0.66, 3.0)),
        ("3", 0.2576, (0.086, 0.307), (0.84, 3.0)),
    ]
    mm = [e for e in rec.equations if e.factor == "M/D"]
    assert [(e.rating, e.k, e.h_range, e.h_units) for e in mm] == [
        ("1", 60.9, (0.53, 2.35), "mm"),
        ("1-1/2", 123.9, (0.71, 3.2), "mm"),
        ("2", 186.9, (1.07, 4.83), "mm"),
        ("3", 382.5, (2.18, 7.79), "mm"),
    ]


@pytest.mark.skipif(not N653_PDF.exists(), reason="reference library not present")
def test_real_n653():
    rec = parse_design_pdf(N653_PDF)
    assert rec.design_no == "N653" and rec.snapshot_date == "2/6/2020"
    assert rec.last_updated == "2020-02-03"
    assert [r.kind for r in rec.ratings] == ["Restrained Beam Rating", "Unrestrained Beam Rating"]
    assert len(rec.tables) == 8 and all(len(t.rows) == 11 for t in rec.tables)
    assert [t.item_no for t in rec.tables] == ["7"] * 4 + ["7A"] * 4
    assert [t.units for t in rec.tables] == ["mils", "mm"] * 4
    assert [t.condition for t in rec.tables] == (
        ["Unrestrained Beam Ratings:"] * 2 + ["Restrained Beam Ratings:"] * 2
    ) * 2
    t = rec.tables[0]
    assert t.rating_columns == ["60 min", "90 min", "120 min", "150 min"]
    assert t.ratio_names == ["A/P"]
    assert t.rows[0].cells == ["6x4x1/4", "0.267", "61", "142", "N/A", "N/A"]
    assert t.rows[0].canonical == "HSS6X4X1/4" and t.rows[0].values_in == [0.061, 0.142, None, None]
    assert rec.tables[2].rating_columns[-1] == "180 min"
    assert rec.tables[2].rows[-1].cells == ["12x6x5/8", "0.616", "22", "46", "96", "146", "195"]
    assert rec.tables[7].rows[-1].values == [0.67, 1.18, 2.44, 3.7, 4.96]
    assert rec.tables[7].rows[-1].values_in == [None] * 5
    assert rec.equations == []


@pytest.mark.skipif(not X827_PDF.exists(), reason="reference library not present")
def test_real_x827():
    rec = parse_design_pdf(X827_PDF)
    assert rec.design_no == "X827" and rec.last_updated == "2018-05-03"
    tube, pipe = rec.tables
    assert tube.condition == "Tube Steel Columns, Min Thkns, In." and len(tube.rows) == 6
    assert [r.label for r in tube.rows] == [
        "ST 3x3x0.188",
        "ST 4x4x0.188",
        "ST4x4x0.25",
        "ST 4x4x0.375",
        "ST 4x4x0.5",
        "ST 36x24x0.5",
    ]
    assert tube.rows[0].cells == ["ST 3x3x0.188", "0.18", "1", "1-3/4", "2-9/16", "—", "—"]
    assert tube.rows[0].values_in == [1.0, 1.75, 2.5625, None, None]
    assert pipe.condition == "Pipe Columns, Min Thkns, In."
    assert [r.label for r in pipe.rows] == ["SP 3x0.188", "SP 4x0.237"]
    assert pipe.rows[1].values_in == [0.8125, 1.4375, 2.0625, 3.375, 4.8125]
    (eq,) = rec.equations
    assert eq.form == "h = (R - c) / (k*(A/P))" and (eq.c, eq.k) == (0.38, 3.58)
    assert eq.r_units == "hours" and eq.h_range_in == (0.35, 3.5) and eq.wd_range == (0.18, 2.0)
    assert any(m.name == "ISOLATEK INTERNATIONAL" for m in rec.sfrm_manufacturers)


@pytest.mark.skipif(not CERT_PDF.exists(), reason="reference library not present")
def test_real_certificate_routes_as_other():
    from ffs.importers.router import sniff

    assert sniff(CERT_PDF)[0] == "other"


FRACTION_RATINGS = """Design No. Y995
May 03, 2018
Ratings - 1/2, 3/4, 1, 1-1/2 and 2 Hr. (See Item 2)
2. Mastic and Intumescent Coatings* — Applied to the thicknesses shown below.
Size
W/D
Required Thickness (inches)
Rating Period (hr)
1/2
3/4
1
1-1/2
2
W8x10
0.33
0.063
0.109
0.154
N/A
N/A
Last Updated on 2018-05-03
"""


def test_bare_fraction_ratings_and_inches_header():
    rec = parse_design_text(FRACTION_RATINGS)
    assert rec.ratings[0].hours == [0.5, 0.75, 1.0, 1.5, 2.0]
    (t,) = rec.tables
    assert t.rating_columns == ["1/2 Hr", "3/4 Hr", "1 Hr", "1-1/2 Hr", "2 Hr"] and t.units == "in"
    assert t.rows[0].cells == ["W8x10", "0.33", "0.063", "0.109", "0.154", "N/A", "N/A"]
    assert t.rows[0].values_in == [0.063, 0.109, 0.154, None, None]


# --- current Product iQ site (2025 printouts, Carboline Y677 layout): a site banner and the UL
# usage disclaimer before "Design No.", no per-page header/footer, a linear equation table
# "T =((a*Hp/A) + b)", bare "Rating Period (hr)" heads, a size table whose W/D may print as "1",
# an Hp/A-keyed metric table with no member sizes, a wrapped manufacturer line and UL Solutions'
# notices after "Last Updated"
CURRENT_SITE_COLUMN = """Coming October 20th, discover our sleek new design and powerful features. Learn More
ⓘ
Design/System/Construction/Assembly Usage Disclaimer
Authorities Having Jurisdiction should be consulted in all cases as to the particular requirements covering the installation
and use of UL Certified products, equipment, system, devices, and materials.
Only products which bear UL's Mark are considered Certified.
BXUV - Fire Resistance Ratings - ANSI/UL 263 Certified for United States
See General Information for Fire-resistance Ratings - ANSI/UL 263 Certified for United States
Design Criteria and Allowable Variances
Design No. Y994
August 22, 2025
\xa0
Ratings - 1/2, 3/4, 1, 1-1/2, 2, 2-1/2, 3 and 3-1/2 Hr. (See Item 2)
* Indicates such products shall bear the UL or cUL Certification Mark for jurisdictions employing the UL or cUL
Certification (such as Canada), respectively.

1. Steel Column — Wide flange steel columns with the minimum sizes shown in the tables below.
2. Mastic & Intumescent Coating* — Coating spray or brush applied in accordance with the manufacturer's instructions at the minimum
average dry thickness shown in the table below.
As an alternate to the table below, the required thickness of coating (in mm) to be applied to surfaces of Wide-Flange columns may be
determined from the equations listed below. The equations may only be used for the indicated hourly rating, and for the corresponding listed
ranges of thickness and Hp/A.

Hourly
Rating
Thickness Equation
(mm)
Thickness Range
(mm)
Hp/A Section
Factor Range
1
T =((0.0008*Hp/A) + 3.5825)
3.92 - 3.83
406 - 298
1
T =((0.0142*Hp/A) - 0.4131)
3.83 - 1.86
298 - 160
2
T =((0.0283*Hp/A) + 0.5201
8.94 - 2.02
298 - 53
Size
W/D
Required Thickness (inches)
Rating Period (hr)
1/2
3/4
1
1-1/2
2
2-1/2
3
3-1/2
W8x10
0.33
0.063
0.109
0.154
N/A
N/A
N/A
N/A
N/A
W18x65
1
0.038
0.038
0.060
0.113
0.170
N/A
N/A
N/A

W14x233
2.55
0.018
0.018
0.019
0.048
0.080
0.111
0.143
0.175
Hp/A
Required Thickness (mm)
Rating Period (hr)
1/2
3/4
1
1-1/2
2
2-1/2
3
3-1/2
406
1.6
2.76
3.92
N/A
N/A
N/A
N/A
N/A
140
1
1
1.61
2.98
4.48
N/A
N/A
N/A
53
0.47
0.47
0.47
1.22
2.02
2.83
3.63
4.44
CARBOLINE GLOBAL INC — Thermo-Sorb HB, INVESTIGATED FOR INTERIOR GENERAL PURPOSE, INTERIOR CONDITIONED SPACE and
EXTERIOR ENVIRONMENTAL
* Indicates such products shall bear the UL or cUL Certification Mark for jurisdictions employing the UL or cUL
Certification (such as Canada), respectively.
Last Updated on 2025-08-22
The appearance of a company's name or product in this database does not in itself assure that products so identified have been
manufactured under UL Solutions' Follow - Up Service.
UL Solutions permits the reproduction of the material contained in Product iQ subject to the following conditions: 1. The Guide Information,
Assemblies, Constructions, Designs, Systems, and/or Certifications (files) must be presented in their entirety and in a non-misleading manner,
without any manipulation of the data (or drawings).
"""


def test_current_site_header_boilerplate_and_linear_equation_table():
    rec = parse_design_text(CURRENT_SITE_COLUMN)
    assert rec.design_no == "Y994" and rec.member_category_guess == "column"
    assert rec.design_date == "August 22, 2025" and rec.last_updated == "2025-08-22"
    # the current site prints no print date, URL or page number: nothing is invented
    assert rec.snapshot_date is None and rec.source_url is None
    assert rec.ratings[0].hours == [0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5]
    assert rec.ratings[0].see == "See Item 2"
    assert [it.no for it in rec.items] == ["1", "2"] and rec.items[1].is_intumescent
    assert rec.unparsed == []  # the banner and the usage disclaimer are not design content
    assert "Coming October" not in rec.items[0].text and "Disclaimer" not in rec.items[0].text
    assert rec.reproduction_notice.startswith("UL Solutions permits the reproduction")
    (mfr,) = rec.items[1].manufacturers
    assert mfr.name == "CARBOLINE GLOBAL INC"
    assert mfr.text == (
        "Thermo-Sorb HB, INVESTIGATED FOR INTERIOR GENERAL PURPOSE, INTERIOR CONDITIONED SPACE "
        "and EXTERIOR ENVIRONMENTAL"
    )
    assert "EXTERIOR ENVIRONMENTAL" not in rec.items[1].text
    # equations: one record per table row, constants and ranges exactly as printed
    eqs = rec.equations
    assert [
        (e.form, e.a, e.b, e.rating, e.rating_hours, e.wd_range, e.h_range, e.h_units) for e in eqs
    ] == [
        ("T = a*(Hp/A) + b", 0.0008, 3.5825, "1", 1.0, (406.0, 298.0), (3.92, 3.83), "mm"),
        ("T = a*(Hp/A) + b", 0.0142, -0.4131, "1", 1.0, (298.0, 160.0), (3.83, 1.86), "mm"),
        ("T = a*(Hp/A) + b", 0.0283, 0.5201, "2", 2.0, (298.0, 53.0), (8.94, 2.02), "mm"),
    ]
    assert [e.as_printed for e in eqs] == [
        "T =((0.0008*Hp/A) + 3.5825)",
        "T =((0.0142*Hp/A) - 0.4131)",
        "T =((0.0283*Hp/A) + 0.5201",
    ]
    assert all(
        e.item_no == "2"
        and e.factor == "Hp/A"
        and e.k is None
        and e.c is None
        and e.r_units is None
        and e.h_range_in is None
        for e in eqs
    )
    assert any("high to low" in n for n in eqs[0].notes) and any(
        "kept as printed" in n for n in eqs[0].notes
    )
    assert any("parentheses unbalanced" in n for n in eqs[2].notes)
    assert not any("parentheses" in n for n in eqs[0].notes)
    # tables: the inch size table and the Hp/A-keyed metric table
    assert len(rec.tables) == 2
    t_in, t_mm = rec.tables
    assert t_in.kind == "size_wd" and t_in.units == "in" and t_in.ratio_names == ["W/D"]
    assert t_in.rating_columns == [
        "1/2 Hr",
        "3/4 Hr",
        "1 Hr",
        "1-1/2 Hr",
        "2 Hr",
        "2-1/2 Hr",
        "3 Hr",
        "3-1/2 Hr",
    ]
    assert t_in.condition is None  # the "table below" sentence introduced the equations
    assert [r.canonical for r in t_in.rows] == ["W8X10", "W18X65", "W14X233"]
    assert t_in.rows[1].cells == [
        "W18x65",
        "1",
        "0.038",
        "0.038",
        "0.060",
        "0.113",
        "0.170",
        "N/A",
        "N/A",
        "N/A",
    ]
    assert t_in.rows[1].wd == 1.0  # W/D printed as a whole number under a declared W/D column
    assert t_in.rows[2].values_in == [0.018, 0.018, 0.019, 0.048, 0.08, 0.111, 0.143, 0.175]
    assert t_mm.kind == "ratio_rows" and t_mm.units == "mm" and t_mm.ratio_names == ["Hp/A"]
    assert t_mm.rating_columns == t_in.rating_columns and t_mm.item_no == "2"
    assert [r.cells for r in t_mm.rows] == [
        ["406", "1.6", "2.76", "3.92", "N/A", "N/A", "N/A", "N/A", "N/A"],
        ["140", "1", "1", "1.61", "2.98", "4.48", "N/A", "N/A", "N/A"],
        ["53", "0.47", "0.47", "0.47", "1.22", "2.02", "2.83", "3.63", "4.44"],
    ]
    assert all(r.label is None and r.canonical is None for r in t_mm.rows)
    assert [r.wd for r in t_mm.rows] == [406.0, 140.0, 53.0]
    assert t_mm.rows[1].values == [1.0, 1.0, 1.61, 2.98, 4.48, None, None, None]
    assert t_mm.rows[1].values_in == [None] * 8


# --- current site, beam design (N663 layout): an all-caps title over an Hp/A-keyed metric table
# whose column heads name the units ("1 Hr., MM"), then the inch copy ("Beam | W/D | 1 Hr., IN")
# with no title of its own; no equation is printed
CURRENT_SITE_BEAM = """Design No. N994
August 22, 2025
\xa0
Restrained Beam Rating — 1 and 2 Hr (See Item 7)
Unrestrained Beam Rating — 1 and 2 Hr (See Item 7)
1. Steel Beam — Min size as shown in the table below (See Item 7). Maximum allowable yield stress of 50 ksi.
7. Mastic and Intumescent Coating* — Coating spray or brush applied in accordance with the manufacturer's instructions at the minimum
average dry thickness shown in the table below. The thickness shown in the table is intumescent only.
UNRESTRAINED BEAM RATINGS
Hp/A
1 Hr., MM
1-1/2 Hr., MM
2 Hr., MM
2-1/2 Hr., MM
3 Hr., MM
253
1.51
3.24
4.96
6.69
8.41

250
1.50
3.21
4.92
6.64
8.41

Beam
W/D
1 Hr., IN
1-1/2 Hr., IN
2 Hr., IN
2-1/2 Hr., IN
3 Hr., IN
W6x12
0.53
0.060
0.128
0.195
0.263
0.331
W8x67
1.65
0.019
0.081
0.132
0.184
0.331
RESTRAINED BEAM RATINGS
\xa0
Hp/A
1 Hr., MM
1-1/2 Hr., MM
2 Hr., MM
2-1/2 Hr., MM
3 Hr., MM
253
1.51
2.63
4.33
6.02
7.71
CARBOLINE GLOBAL INC — Thermo-Sorb HB, INVESTIGATED FOR INTERIOR GENERAL PURPOSE.
Last Updated on 2025-08-22
"""


def test_current_site_beam_tables_with_units_in_column_heads():
    rec = parse_design_text(CURRENT_SITE_BEAM)
    assert rec.design_no == "N994" and rec.member_category_guess.startswith("floor beam")
    assert [r.kind for r in rec.ratings] == ["Restrained Beam Rating", "Unrestrained Beam Rating"]
    assert rec.equations == []
    assert [(t.kind, t.units, t.ratio_names, len(t.rows), t.condition) for t in rec.tables] == [
        ("ratio_rows", "mm", ["Hp/A"], 2, "UNRESTRAINED BEAM RATINGS"),
        ("size_wd", "in", ["W/D"], 2, "UNRESTRAINED BEAM RATINGS"),
        ("ratio_rows", "mm", ["Hp/A"], 1, "RESTRAINED BEAM RATINGS"),
    ]
    assert all(
        t.item_no == "7" and t.rating_columns == ["1 Hr", "1-1/2 Hr", "2 Hr", "2-1/2 Hr", "3 Hr"]
        for t in rec.tables
    )
    t_mm, t_in, t_r = rec.tables
    assert t_mm.notes[0].startswith("introduced by: average dry thickness shown in the table below")
    assert t_mm.rows[0].cells == ["253", "1.51", "3.24", "4.96", "6.69", "8.41"]
    assert t_mm.rows[1].cells[0] == "250"  # page break before the row
    assert t_mm.rows[0].label is None and t_mm.rows[0].wd == 253.0
    assert (
        t_mm.rows[0].values == [1.51, 3.24, 4.96, 6.69, 8.41]
        and t_mm.rows[0].values_in == [None] * 5
    )
    assert t_in.notes[0].startswith("heading carried over")
    assert [r.canonical for r in t_in.rows] == ["W6X12", "W8X67"]
    assert t_in.rows[0].wd == 0.53 and t_in.rows[0].values_in == [0.06, 0.128, 0.195, 0.263, 0.331]
    assert t_r.notes == [] and t_r.rows[0].cells == ["253", "1.51", "2.63", "4.33", "6.02", "7.71"]
    assert rec.items[-1].manufacturers[0].text == (
        "Thermo-Sorb HB, INVESTIGATED FOR INTERIOR GENERAL PURPOSE."
    )


# --- current site, tube column design (Y678 layout): "Minimum Required Thickness (mm) for Rating
# Period" titles, "30 min" column heads, an Hp/A-keyed metric table and an "HSS Tube Size" table
# with bare labels including a decimal size
CURRENT_SITE_TUBE = """Design No. Y993
August 22, 2025
Ratings - 1/2, 3/4, 1, 1-1/2 2, 2-1/2 and 3 Hr. (See Item 3)
1. Steel Tube Column — Steel rectangular tube (ST) or pipe (SP) columns with the minimum sizes shown in the tables below.
3. Mastic & Intumescent Coating* — Coating spray or brush applied in accordance with the manufacturer's instructions at the minimum
average dry thickness shown in the thickness below. The thickness shown does not include primer thickness.
\xa0
Minimum Required Thickness (mm) for Rating Period
Hp/A
30 min
45 min
60 min
90 min
120 min
150 min
180 min
212
1.29
3.26
5.22
9.15
N/A
N/A
N/A
65
0.45
0.45
1.16
2.68
4.21
5.73
7.26

\xa0
Minimum Required Thickness (in) for Rating Period
\xa0
HSS Tube
Size
A/P
30 min
45 min
60 min
90 min
120 min
150 min
180 min
8x8x3/16
0.17
0.051
0.128
0.206
0.360
N/A
N/A
N/A
3.5x3.5x5/16
0.27
0.039
0.091
0.162
0.261
0.347
N/A
N/A
Last Updated on 2025-08-22
"""


def test_current_site_minute_heads_and_titled_tables():
    rec = parse_design_text(CURRENT_SITE_TUBE)
    assert rec.ratings[0].hours == [0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0]
    assert len(rec.tables) == 2
    t_mm, t_in = rec.tables
    cols = ["30 min", "45 min", "60 min", "90 min", "120 min", "150 min", "180 min"]
    assert t_mm.kind == "ratio_rows" and t_mm.rating_columns == cols and t_mm.units == "mm"
    assert t_mm.condition == "Minimum Required Thickness (mm) for Rating Period"
    assert t_mm.ratio_names == ["Hp/A"] and t_mm.item_no == "3" and t_mm.notes == []
    assert [r.cells for r in t_mm.rows] == [
        ["212", "1.29", "3.26", "5.22", "9.15", "N/A", "N/A", "N/A"],
        ["65", "0.45", "0.45", "1.16", "2.68", "4.21", "5.73", "7.26"],
    ]
    assert t_mm.rows[0].values == [1.29, 3.26, 5.22, 9.15, None, None, None]
    assert t_in.kind == "size_wd" and t_in.rating_columns == cols and t_in.units == "in"
    assert t_in.condition == "Minimum Required Thickness (in) for Rating Period"
    assert t_in.ratio_names == ["A/P"] and t_in.notes == []
    assert [r.label for r in t_in.rows] == ["8x8x3/16", "3.5x3.5x5/16"]
    assert t_in.rows[0].canonical == "HSS8X8X3/16" and t_in.rows[1].canonical.startswith("HSS3.5")
    assert t_in.rows[0].wd == 0.17 and t_in.rows[0].values_in == [
        0.051,
        0.128,
        0.206,
        0.36,
        None,
        None,
        None,
    ]
    assert t_in.rows[1].cells == [
        "3.5x3.5x5/16",
        "0.27",
        "0.039",
        "0.091",
        "0.162",
        "0.261",
        "0.347",
        "N/A",
        "N/A",
    ]


# --- real current-site printouts hosted by Carboline (git-ignored); skipped when absent
CARBOLINE = REF / "fetched" / "Carboline"
N663_PDF = (
    CARBOLINE / "carboline-thermo-sorb-hb-bxuv-n663-ul-product-iq-a43069" / "5f1912ed8381.pdf"
)
Y677_PDF = (
    CARBOLINE / "carboline-thermo-sorb-hb-bxuv-y677-ul-product-iq-21ba17" / "29f4ee58958e.pdf"
)
Y678_PDF = (
    CARBOLINE / "carboline-thermo-sorb-hb-bxuv-y678-ul-product-iq-ff6177" / "e9e9e93be070.pdf"
)
THERMO_SORB_MFR = (
    "Thermo-Sorb HB, INVESTIGATED FOR INTERIOR GENERAL PURPOSE, INTERIOR CONDITIONED SPACE and "
    "EXTERIOR ENVIRONMENTAL"
)


def test_real_n663():
    if not N663_PDF.exists():
        pytest.skip("reference library not present")
    rec = parse_design_pdf(N663_PDF)
    assert rec.design_no == "N663" and rec.design_date == "August 22, 2025"
    assert rec.last_updated == "2025-08-22" and rec.snapshot_date is None
    assert rec.source_url is None and rec.unparsed == []
    assert [(r.kind, r.hours, r.see) for r in rec.ratings] == [
        ("Restrained Beam Rating", [1.0, 2.0], "See Item 7"),
        ("Unrestrained Beam Rating", [1.0, 2.0], "See Item 7"),
    ]
    assert [it.no for it in rec.items] == ["1", "2", "3", "4", "5", "6", "7"]
    assert rec.items[6].is_intumescent and rec.items[6].manufacturers[0].text == THERMO_SORB_MFR
    assert rec.equations == []  # N663 prints thickness tables only
    assert [(t.kind, t.units, t.ratio_names, len(t.rows), t.condition) for t in rec.tables] == [
        ("ratio_rows", "mm", ["Hp/A"], 36, "UNRESTRAINED BEAM RATINGS"),
        ("size_wd", "in", ["W/D"], 128, "UNRESTRAINED BEAM RATINGS"),
        ("ratio_rows", "mm", ["Hp/A"], 36, "RESTRAINED BEAM RATINGS"),
        ("size_wd", "in", ["W/D"], 128, "RESTRAINED BEAM RATINGS"),
    ]
    assert all(
        t.item_no == "7" and t.rating_columns == ["1 Hr", "1-1/2 Hr", "2 Hr", "2-1/2 Hr", "3 Hr"]
        for t in rec.tables
    )
    u_mm, u_in, r_mm, r_in = rec.tables
    assert u_mm.rows[0].cells == ["253", "1.51", "3.24", "4.96", "6.69", "8.41"]
    assert u_mm.rows[0].wd == 253.0 and u_mm.rows[0].values_in == [None] * 5
    assert u_mm.rows[-1].cells == ["81", "0.48", "2.06", "3.36", "4.67", "8.41"]
    assert u_in.rows[0].cells == ["W6x12", "0.53", "0.060", "0.128", "0.195", "0.263", "0.331"]
    assert u_in.rows[0].canonical == "W6X12" and u_in.rows[0].values_in == [
        0.06,
        0.128,
        0.195,
        0.263,
        0.331,
    ]
    assert u_in.rows[-1].cells == ["W8x67", "1.65", "0.019", "0.081", "0.132", "0.184", "0.331"]
    assert r_mm.rows[-1].cells == ["81", "0.48", "1.70", "2.85", "4.01", "5.17"]
    assert r_in.rows[-1].cells == ["W8x67", "1.65", "0.019", "0.067", "0.112", "0.158", "0.203"]
    assert u_mm.notes[0].startswith("introduced by:") and r_mm.notes == []
    assert u_in.notes[0].startswith("heading carried over") and r_in.notes[0].startswith(
        "heading carried over"
    )
    assert rec.reproduction_notice.startswith("UL Solutions permits the reproduction")


def test_real_y677():
    if not Y677_PDF.exists():
        pytest.skip("reference library not present")
    rec = parse_design_pdf(Y677_PDF)
    assert rec.design_no == "Y677" and rec.last_updated == "2025-08-22"
    assert rec.design_date == "August 22, 2025" and rec.snapshot_date is None
    assert rec.ratings[0].hours == [0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5]
    assert [it.no for it in rec.items] == ["1", "2"]
    assert rec.items[1].manufacturers[0].text == THERMO_SORB_MFR and rec.unparsed == []
    cols = ["1/2 Hr", "3/4 Hr", "1 Hr", "1-1/2 Hr", "2 Hr", "2-1/2 Hr", "3 Hr", "3-1/2 Hr"]
    assert [(t.kind, t.units, t.ratio_names, len(t.rows), t.condition) for t in rec.tables] == [
        ("size_wd", "in", ["W/D"], 168, None),
        ("ratio_rows", "mm", ["Hp/A"], 72, None),
    ]
    t_in, t_mm = rec.tables
    assert t_in.rating_columns == cols and t_mm.rating_columns == cols
    assert t_in.rows[0].cells == ["W8x10", "0.33", "0.063", "0.109", "0.154"] + ["N/A"] * 5
    assert t_in.rows[79].cells[:2] == ["W18x65", "1"] and t_in.rows[79].wd == 1.0
    assert t_in.rows[79].values_in == [0.038, 0.038, 0.06, 0.113, 0.17, None, None, None]
    assert t_in.rows[-1].cells == [
        "W14x233",
        "2.55",
        "0.018",
        "0.018",
        "0.019",
        "0.048",
        "0.080",
        "0.111",
        "0.143",
        "0.175",
    ]
    assert all(r.canonical and len(r.cells) == 10 for r in t_in.rows)
    assert t_mm.rows[0].cells == ["406", "1.6", "2.76", "3.92"] + ["N/A"] * 5
    assert t_mm.rows[-1].cells == [
        "53",
        "0.47",
        "0.47",
        "0.47",
        "1.22",
        "2.02",
        "2.83",
        "3.63",
        "4.44",
    ]
    assert all(r.label is None and len(r.cells) == 9 for r in t_mm.rows)
    assert [r.wd for r in t_mm.rows][:3] == [406.0, 400.0, 395.0]
    assert [
        (e.form, e.a, e.b, e.rating, e.wd_range, e.h_range, e.h_units, e.item_no)
        for e in rec.equations
    ] == [
        ("T = a*(Hp/A) + b", 0.0008, 3.5825, "1", (406.0, 298.0), (3.92, 3.83), "mm", "2"),
        ("T = a*(Hp/A) + b", 0.0142, -0.4131, "1", (298.0, 160.0), (3.83, 1.86), "mm", "2"),
        ("T = a*(Hp/A) + b", 0.0131, -0.225, "1", (160.0, 53.0), (1.86, 0.47), "mm", "2"),
        ("T = a*(Hp/A) + b", 0.0283, 0.5201, "2", (298.0, 53.0), (8.94, 2.02), "mm", "2"),
    ]
    assert rec.equations[3].as_printed == "T =((0.0283*Hp/A) + 0.5201"
    assert any("parentheses unbalanced" in n for n in rec.equations[3].notes)
    assert all(e.h_range_in is None and e.k is None for e in rec.equations)


def test_real_y678():
    if not Y678_PDF.exists():
        pytest.skip("reference library not present")
    rec = parse_design_pdf(Y678_PDF)
    assert rec.design_no == "Y678" and rec.last_updated == "2025-08-22"
    assert rec.ratings[0].hours == [0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0]
    assert rec.ratings[0].see == "See Item 3"
    assert [it.no for it in rec.items] == ["1", "2", "3"] and rec.unparsed == []
    assert rec.items[2].manufacturers[0].text == THERMO_SORB_MFR
    cols = ["30 min", "45 min", "60 min", "90 min", "120 min", "150 min", "180 min"]
    assert [(t.kind, t.units, t.ratio_names, len(t.rows), t.condition) for t in rec.tables] == [
        ("ratio_rows", "mm", ["Hp/A"], 31, "Minimum Required Thickness (mm) for Rating Period"),
        ("size_wd", "in", ["A/P"], 130, "Minimum Required Thickness (in) for Rating Period"),
    ]
    t_mm, t_in = rec.tables
    assert t_mm.rating_columns == cols and t_in.rating_columns == cols
    assert all(t.item_no == "3" and t.notes == [] for t in rec.tables)
    assert t_mm.rows[0].cells == ["212", "1.29", "3.26", "5.22", "9.15", "N/A", "N/A", "N/A"]
    assert t_mm.rows[-1].cells == ["65", "0.45", "0.45", "1.16", "2.68", "4.21", "5.73", "7.26"]
    assert (
        t_in.rows[0].cells == ["8x8x3/16", "0.17", "0.051", "0.128", "0.206", "0.360"] + ["N/A"] * 3
    )
    assert t_in.rows[0].canonical == "HSS8X8X3/16"
    assert t_in.rows[0].values_in == [0.051, 0.128, 0.206, 0.36, None, None, None]
    assert "3.5x3.5x5/16" in [r.label for r in t_in.rows]
    assert t_in.rows[-1].cells == [
        "12x8x5/8",
        "0.55",
        "0.018",
        "0.018",
        "0.046",
        "0.106",
        "0.166",
        "0.226",
        "0.286",
    ]
    assert all(r.canonical and len(r.cells) == 9 for r in t_in.rows)
    assert [
        (e.form, e.a, e.b, e.rating, e.wd_range, e.h_range, e.h_units, e.item_no)
        for e in rec.equations
    ] == [
        ("T = a*(Hp/A) + b", 0.0077, 3.5962, "1", (212.0, 165.0), (5.22, 4.86), "mm", "3"),
        ("T = a*(Hp/A) + b", 0.037, -1.245, "1", (165.0, 65.0), (4.86, 1.16), "mm", "3"),
        ("T = a*(Hp/A) + b", 0.0576, 0.466, "2", (165.0, 65.0), (9.97, 4.21), "mm", "3"),
    ]
    assert [e.as_printed for e in rec.equations][:2] == [
        "T =((0.0077*Hp/A) + 3.5962)",
        "T =((0.037*Hp/A) - 1.245)",
    ]
