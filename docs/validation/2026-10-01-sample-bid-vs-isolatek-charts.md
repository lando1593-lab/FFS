# Validation 1 — sample roof bid (EDGE spray report) vs Isolatek design charts

Date: 2026-10-01. Inputs: the user's EDGE spray report for sheet 1-S102 (CAFCO 400, 1 hour,
designs P723 and X790) parsed by `ffs import-spray-report`; Isolatek's public
"Designs & Thicknesses" charts (chart date 10/3/2013; P723 cross-reference page dated
10/07/13) fetched from isolatek.com and parsed by `ffs import-isolatek-chart`; UL design
printouts X790 (last updated 2019-10-09) and P723 (2019-11-14) from isolatek.com parsed by
`ffs import-ul-design`.

Chain used for the beams: the P723 chart page says "Use Design S721 Table" (beam substitution
per UL guidelines). S721 chart, unrestrained beam, 1 hour:

| member | sides | bid | S721 chart | W/D | result |
|---|---|---|---|---|---|
| W8X10 | 3 | 5/8 | 5/8 | 0.37 | match |
| W10X12 | 3 | 5/8 | 5/8 | 0.39 | match |
| W12X14 | 3 | 9/16 | 9/16 | 0.40 | match |
| W12X19 | 3 | 1/2 | 1/2 | 0.54 | match |
| W12X26 | 3 | 1/2 | 1/2 | 0.61 | match |
| W14X22 | 3 | 1/2 | 1/2 | 0.53 | match |
| W14X30 | 3 | 1/2 | 1/2 | 0.64 | match |
| W16X26 | 3 | 1/2 | 1/2 | 0.55 | match |
| W16X31 | 3 | 1/2 | 1/2 | 0.66 | match |
| W16X36 | 3 | 7/16 | 7/16 | 0.70 | match |
| W18X35 | 3 | 1/2 | 1/2 | 0.67 | match |
| W18X46 | 3 | 7/16 | 7/16 | 0.87 | match |
| W21X44 | 3 | 7/16 | 7/16 | 0.74 | match |
| L3X3X1/4 | 3 | 7/8 | 15/16 (misc. shapes chart, W/D 0.41) | | differs by 1/16 |
| L4X4X5/16 | 3 | 3/4 | 13/16 (misc. shapes chart, W/D 0.51) | | differs by 1/16 |
| HSS5X5X3/8 column | 4 | 9/16 | 7/16 (X790 square-tube chart, A/P 0.35) | | differs by 1/8 |
| HSS5X5X3/8 brace (1-S211) | 3 | 9/16 | 7/16 (same chart) | | differs by 1/8 |

## Reading of the differences (interpretations, for the estimator to confirm)
1. **HSS column.** UL X790 offers two permitted routes: the tested table (ST 4x4x0.375,
   A/P 0.34 → 7/16 in. at 1 hour; Isolatek's chart extends this to 5x5x3/8 at A/P 0.35 → 7/16)
   and the alternate equation h = R/(188·A/P + 45), R in minutes, rounded up to 1/16 in., which
   gives 60/(188·0.35 + 45) = 0.54 → 9/16 in. The bid carries the equation value. Both are
   listed; they disagree by 1/8 in. on every tube in this range. The engine must present both
   with their sources and record which one the estimator chose, never pick silently.
2. **Angles.** The "Miscellaneous Shapes — Single Angles" chart is a 4-sided contour W/D table
   (likely a column basis). The bid treats the angles as 3-sided beams under the roof assembly,
   which yields 1/16 in. less. Which chart or substitution rule the company uses for angles
   under a beam design is a domain decision to capture as a condition rule.
3. **Beams.** 13 of 13 exact matches through the P723 → S721 cross-reference. This confirms
   the chart importer, the spray-report importer, the design cross-reference handling, and
   that Isolatek's public charts are the operative source for CAFCO 300/400 beam thickness.

## Caveats
- Chart dates are 2013; UL design dates 2019. Currency of both against today's Isolatek site
  and Product iQ is still to be checked (the fetch manifest records what was fetched and when).
- Only 1-hour values were exercised. The charts carry 1-1/2, 2, 3 and 4 hour columns.
