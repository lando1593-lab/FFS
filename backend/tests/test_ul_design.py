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
