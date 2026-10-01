# Validation 2 — five submitted shop-drawing sets vs the design library

Date: 2026-10-01. Inputs: the company's own EDGE "Fireproofing Drawing Report" submittals for
five projects (Naples Players Theater, Blaze-Shield II; OCPS East Campus, Blaze-Shield II;
Broward SOE, MK-6/HY; Kissimmee City Hall, CAFCO 400, plus its field "Spray Chart" variant),
parsed by `ffs import-drawing-report` (142 legend rows) and checked row by row with
`ffs check-drawing-report` against the parsed reference library (`docs/09-design-layer.md`).

Each legend row is a decision the company actually submitted: member, role, EDGE design
code, hours, thickness. The checker maps the EDGE code tokens as follows and records the
mapping as an INTERPRETATION on every row: NW / LW → normal-weight / lightweight concrete
chart; C on a beam design → cellular or corrugated deck chart; C on a column design →
wide-flange column chart; P/T → pipe or tube chart; F and B → kept as printed, unmapped.
Restraint is not printed; beams are checked as unrestrained (ASSUMPTION).

## Result (133 checkable rows; 9 deck rows skipped)
| verdict | rows | meaning |
|---|---|---|
| match | 62 | one applicable printed value, equal to the submitted thickness |
| match-one-route | 35 | several applicable values (UL equation vs chart, two chart editions, two joist charts); the submitted value is one of them |
| review-match | 15 | angles and channels under X829: no X829 table lists them; Isolatek's "Miscellaneous Shapes — Single Angles" chart prints exactly the submitted value in 13 of 13 angle rows and both channel rows |
| differs-4-sides | 7 | beams marked "4 Sides": submitted value is one sixteenth above the 3-sided beam chart row in every case |
| differs | 8 | see below |
| review | 5 | bridging angles not on any chart but the double-angle shapes chart (which prints a different value) |
| unknown | 1 | L2-1/2x2-1/2x5/16 bridging: on no chart at all |

## By EDGE code (rows: verdicts)
N759 11: all match. N782 LW (MK-6/HY) 2: match once the GCP chart's restraint and concrete
line is read. N823 NW C 43: 39 match, 1 four-sided, 3 differ. P723F 5 beams: 4 match, 1
four-sided. P819F B 7 beams: 2 match, 5 four-sided; 22 joists match one of the two P819
joist charts. P936 2: match. X790 C 2 and X854 3 columns: one route matches. X790 P/T 2 and
X827 1 tubes: one route or +1/16. X829 9 columns: 2 match, 7 one route.

## Findings worth your decision (open questions 27–31 in `docs/07-open-domain-questions.md`)
1. **Columns follow the UL equation, not the chart.** For X829 (W10x54 at 2 h: submitted
   1-5/16, equation 1-5/16, chart 1-1/4) and X790 C (W10x39 at 1 h: 11/16 vs chart 5/8) the
   submitted value equals the equation route. For X854 (W12x65 at 1 h) it equals the table
   (1/2) and not the equation (11/16). The engine returns both; the company's rule for
   choosing is a HUMAN_OVERRIDE class to capture.
2. **Tubes sit one sixteenth above both routes** (HSS6x6x1/4 under X827 at 2 h: 2-1/16 vs
   1-15/16; HSS4x4x1/4 under X790 at 1 h: 3/4 vs 11/16; HSS7x7x3/8 matches the equation).
   Consistent with question 24: A/P from the design wall rather than the nominal wall.
3. **4-sided beams are +1/16 over the 3-sided chart row** in all seven cases. Which basis the
   company uses for four-sided exposure (column chart, 4-sided contour, a rule) is not in
   any document in hand.
4. **N830 joists at 1 h were submitted at 9/16 in.** The N830 joist charts print 15/16 to
   1-1/8+ at 1 h, and the "+" footnote says reduced thicknesses are available with metal lath
   or mesh. The submitted value presumably rests on that footnote or on a different basis;
   the engine cannot tell and must not guess.
5. **Two N823 rows are thinner than the chart**: W16x100 at 1 h submitted 1/4 (chart 3/8);
   W24x62 at 2 h submitted 13/16 (chart 3/4, the other direction). Both flagged.
6. **Angles under X829 use the single-angle miscellaneous-shapes chart** (13/13). That
   answers question 26 for column designs; for beam designs (validation 1) the chart was a
   sixteenth above the bid, so the rule is design-type dependent.
7. **EDGE suffix F and token B** (P723F, P819F B) are unmapped. The P819 chart in hand has
   only an "Unrestrained Assembly" section; "B" probably selects the beam-rating basis, which
   is a chart Isolatek does not publish in the set fetched. Until mapped, those rows are
   compared against the assembly table and flagged.

## What this proves and does not
- The importer reads the legend of every report with zero unread rows, including the field
  spray-chart variant (thickness colour legend and bag counts).
- Across three manufacturers and twelve design codes, the engine reproduces the submitted
  thickness or returns it as one explicit route in 112 of 133 rows, and every remaining row
  is flagged with the exact reason. Nothing is silently resolved.
- It does not prove the member takeoff: the legend carries no lengths and the plan is an
  image. Real vector structural sets are still needed for that.
