# C — Anatomy of an EDGE Spray Report (from a real sample)

Source: a six-page "Spray Report" PDF exported from The EDGE (PDF metadata title `xrSprayReport`,
producer "Microsoft: Print To PDF"), supplied by the user on 2026-10-01 for a 2026 hospital
addition bid in Florida, product Isolatek CAFCO 400, 1-hour ratings. The PDF itself is not
committed (client-identifying). The importer `ffs import-spray-report` was written against it and
reproduces every row; the hermetic test in `backend/tests/test_edge_spray_report.py` mimics the
layout.

## Structure (certain — read directly from the file)
Pages come in pairs per contract sheet: a portrait TABLE page then a landscape PLAN page.

TABLE page:
```
Spray Report - <sheet no> - <sheet title>                    Bid Date - mm/dd/yyyy
                                                              Estimator - <name>
<PRODUCT CODE> - <Manufacturer Product> - <Density> -        Market Sector - <...>
<Base> - <Report variant: "Inspector Report">                 Status - Not Assigned
<design> - <rating>                 e.g.  P723 - 1HR
<design> - <rating> - <note>        e.g.  P723 - 1HR - Roof Assembly
<design> - <rating>                 e.g.  X790 - 1HR
Linear Spray Items   | Color | Member                  | Type            | Inches / Mils |
                     | ━━━━━ | W12X26 - 0.5000"        | Beam - 3 Side   | 1/2 inch      |
                     | ╍╍╍╍╍ | W14X30 - 0.5000"        | Beam - 3 Side   | 1/2 inch      |
Area Spray Items     | ━━━━━ | Type Ⅰ 1 ½" - 0.8750"   |                 | 7/8 inch      |
Count Spray Items    | ━━━━━ | HSS5X5X3/8 - 0.5625"    | Column - 4 Side | 9/16 inch     |
```
- Three item classes: **linear** (beams, braces on elevations), **area** (deck/assembly
  fill, e.g. the roof deck type), **count** (columns on the foundation plan, counted each).
- Member cell = designation + decimal thickness; last column repeats the thickness as a fraction
  (or mils for intumescent). The importer cross-checks both.
- Colour cell is a vector swatch: solid = stroke; dashed = a run of 13 filled dashes. The
  palette is 7 hues (red, green, blue, purple, cyan, magenta, orange) × {solid, dashed} = 14
  distinct marks, then it wraps.
- Designs are printed per sheet, as free text. In the sample the roof sheet lists P723 twice
  (bare and with the note "Roof Assembly") and X790; the foundation sheet (columns) and the
  braced-frame sheet print **no design at all** even though the same column condition is used.

PLAN page: the contract sheet rendered as five horizontal raster strips (3024 px wide, stitched
height 2160 px), with the takeoff drawn over it:
- every linear member gets a coloured line along the member **and** a boxed text callout of the
  thickness ("1/2 inch"), rotated with the member, white-filled, placed on the member — which
  frequently covers the engineer's own size label;
- area items are a green cross-hatch over the deck area;
- count items (columns) are solid coloured squares;
- the original sheet's grid bubbles, keynote hexagons, dimensions, notes and title block remain
  underneath, at screen resolution.

## What the sample teaches (likely — one report, one estimator)
1. **A condition in this world is (member size, sides, thickness) under one product and one
   design per sheet.** There is no explicit condition ID; the colour is the condition.
2. **Colour is overloaded as soon as a sheet has more than 14 linear sizes.** The sample roof
   sheet has 15: solid red is both L3X3X1/4 at 7/8" and W8X10 at 5/8". The field crew must rely
   on the per-member thickness boxes, which is why every member carries one.
3. **Per-member thickness boxes are the real information carrier, and they cost legibility.**
   They hide the structural labels and cannot be verified against the member size without
   zooming. A legend keyed by condition, with thickness by member size on a chart, is the
   alternative the product brief already asks for.
4. **The design reference is weakly attached.** It is a text line on the table page, not tied to
   rows, and it is missing on two of three sheets. Our model attaches the design and revision
   to every member assignment, and the QA check "member with protection but no design" exists
   precisely for this.
5. **Raster background.** The report prints the plan as images, so nothing on the plan page is
   selectable, searchable, or diffable. The output is a picture of a takeoff, not a takeoff.
6. **Report variant matters.** "Inspector Report" suggests EDGE distinguishes an inspector-facing
   layout from others (the competitive matrix notes BuzzBID's "As Estimated" vs "Optimized"
   split). Our field drawings should be a separate, simplified rendering of the same model.
7. **Columns live on the foundation plan as counts; braces on elevations as linear 3-side.** The
   same HSS5X5X3/8 is a 4-side column (9/16") on one sheet and a 3-side brace (9/16") on another.
   Member role is per instance, not per size.
8. **The engineer's general notes carried fireproofing-relevant facts** on the original sheet:
   steel to remain unprimed and unpainted to receive SFRM, members marked "PNT" to be primed and
   painted (bond/primer compatibility issue), hourly rating "see arch". These are exactly the
   notes the spec/notes interpreter must capture (FR-CODE-05, FR-DESIGN-01 primer restrictions).

## Implications for our spray chart / shop drawing standard (proposal)
- Legend keyed by **condition ID + colour** (FP-01 …), thickness **by member size on a chart**,
  not on every member. Optional per-member thickness tags as a toggleable layer for inspectors.
- Never reuse a colour on a sheet. If more than ~10 conditions exist on one sheet, split by
  system/rating or use hatch variants, and have QA refuse to issue otherwise.
- Design number and revision printed in the legend next to every condition, on every sheet.
- Vector overlay on a vector background; every drawn member linked to its MemberInstance.
- Area (deck) conditions drawn as a hatch with its own legend row, including deck type.
- Columns drawn as filled symbols with the 4-side condition colour; braces as linear.

## Reuse of the sample as validation data
- The importer output is a **historical takeoff record**: sizes present per sheet, sides, product,
  design, thickness as the estimator applied it. It is not a source of thickness rules.
- Once the matching Isolatek design tables (P723, X790 for CAFCO 400) are ingested with their
  revision dates, the Milestone 3 thickness engine can be checked against these 16 rows as a
  first external validation set. Disagreement would be a finding, not a reason to tune to the
  sample.
- With the original vector 1-S102 PDF and an EDGE quantity report (Condition Detail / Recap) for
  the same sheet, this project becomes golden project #1 for Milestone 1 (sizes, counts, LF).
