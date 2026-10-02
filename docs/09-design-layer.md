# 09 — Design layer: from (design, member, rating) to a thickness with its source

Status: first implementation 2026-10-01 (`backend/src/ffs/design/`). Reproduces validation 1
(`docs/validation/2026-10-01-sample-bid-vs-isolatek-charts.md`) from the parsed library:
13 of 13 beams, the HSS two-route conflict, the angles review.

## What it is
`DesignLibrary.load(parsed_dir)` indexes every parsed UL printout (`ul_designs/UL_*.json`,
latest "Last Updated" wins per design), every Isolatek chart (`charts/*.json`) and every GCP
chart (`gcp_charts/*.json`), deduplicated by content hash, keyed by design number. Charts that
cross-reference another design ("Use Design S721 Table") are followed, carrying their own
assembly condition. Charts with no design number (Isolatek "Miscellaneous Shapes") are indexed
under the empty key and only ever produce review items.

`resolve(lib, ThicknessQuery)` returns a `Resolution` with every candidate that applies and one
of four statuses:

| status | meaning | value |
|---|---|---|
| `resolved` | one printed value, all applicable sources agree, product line known | the thickness, with the selected candidate's source |
| `conflict` | two or more printed or computed values disagree (UL table vs UL equation, two charts) | `UNKNOWN — REVIEW REQUIRED`; every candidate returned; the estimator's choice is to be recorded as a HUMAN_OVERRIDE |
| `review` | a value exists but cannot be tied to the job: no product line named, or only a design-less shapes chart has the member | `UNKNOWN — REVIEW REQUIRED`; candidates returned with the reason |
| `unknown` | nothing printed applies (design not in library, member not in any table, rating column absent, equation out of range) | `UNKNOWN — REVIEW REQUIRED`; reasons list what was searched |

## Query fields and what they filter
| field | effect |
|---|---|
| `design` | UL record and charts for that design, plus cross-reference targets |
| `member` | canonical AISC designation; tube chart rows printed as "ST 5 x 5 x 3/8" are matched through a designation derived from the label and the candidate says so |
| `rating_hours` | the chart/table column ("1-1/2 Hr", "90 min", "1.5 hr" all read as hours) |
| `restraint` | chart section ("Restrained Beam" / "Unrestrained Beam") and UL table condition; a section label printed only on a later page of the same chart is accepted with a note |
| `product` | required phrase on the chart's product line (whole words: "CAFCO 400" matches "CAFCO® 300 Series, CAFCO® 400 & …"); UL tables are product-agnostic |
| `application` | `contour` (default) or `half_flange_tip`; Isolatek prints separate charts, GCP prints both as column groups of one chart; they differ |
| `joist_depth_in` | shop drawings specify steel joists by depth; every chart designation of that depth is gathered, equal values collapse into one candidate listing the designations, unequal values are a conflict |
| `condition` | assembly condition or column group phrase ("Protected Roof Deck", "LIGHTWEIGHT CONCRETE FILL"); cross-references carry the source chart's condition automatically |
| `ratio`, `ratio_kind`, `ratio_source` | the section factor for the equation route when the caller has it (AISC database); otherwise a printed W/D or A/P for the same member from a UL row or chart row is used and cited |

## Candidate classes and authority
- UL table row: FACT, authority 2 (listing). Cites document, item, table condition, row label, column.
- UL equation: CALCULATION, authority 2. Cites the equation as printed, the constants, R and its units, the section factor and where it came from, the raw result and the rounding rule (up to the next 1/16 in). Refused outside the printed W/D (A/P) range or thickness range, with the reason.
- Manufacturer chart row: FACT, authority 6. Cites document, chart date, product line, condition, application, section, column group, page, row, column, and the cross-reference chain.
- Shapes chart row: FACT, authority 6, review only.

Identical cells reached through two copies of the same chart are collapsed and the second
document is listed under `also_in`. Different values are never collapsed.

## What it refuses to do
- Interpolate between sizes or section factors, or carry a neighbour's value.
- Pick between a UL table and a UL equation, or between two charts, when they disagree.
- Return a chart value as resolved without the product line it was printed for (rule 5).
- Convert a metric table to inches (metric UL tables are returned with `values_in` empty and a note).

## `ffs check-bid`
Runs every item of an imported EDGE spray report through the engine using the report's own
design list and product line. Roles decide the designs (column designs X/Y for columns, the
rest for beams); restraint for beams is passed as an explicit assumption ("unrestrained") and
printed as such. Output is a comparison per item (match / differs / match-one-route / review /
unknown); it never changes the bid.

## Persisting (ADR-0005)
`ffs assign-designs --db sqlite:///project.sqlite --design P723 --rating 1 --product "CAFCO 400"
--restraint unrestrained` resolves every member of the project's current scenario and writes a
`design_assignments` row per member (thickness, source record, design and product revisions,
section factor) linked to its FACT or CALCULATION assertion. Anything not cleanly resolved
is stored with `thickness_in = None` and opens a `review_items` row whose options are the
candidates; `ffs review-queue --db …` lists them and `ffs meter --db …` prints the counts.
An estimator's choice is persisted through `assign_design(..., choice=…)` as a HUMAN_OVERRIDE
assertion that cites the chosen candidate and resolves the open item. On the synthetic golden
against the real library: 40 members, 40 resolved through P723 → S721, 0 review items.

## Quantities (Milestone 4, first implementation)
`ffs quantities --db … [--waste 10 --waste-source "…"] [--yield-bdft 40 --yield-source "…"] [--aisc file]`
computes, per member of the current scenario: linear feet (from the physical layer), square feet
(linear feet × surface area per foot), theoretical board feet (square feet × thickness in inches),
adjusted board feet (theoretical × (1 + waste)) and bags (adjusted ÷ yield), with totals by
condition (design | product | thickness | sides) and by level. Surface area per foot comes from,
in order: AISC dimensions through the stated perimeter formula (contour or box, 3 or 4 sides);
the heated perimeter implied by the printed W/D of the chart row that gave the thickness
(D = W ÷ (W/D), which is exactly how Isolatek's estimating workbooks compute their square feet
per foot: W12x26 beam 3.54, column 4.08); nominal geometry for tubes, pipes and angles; a
manufacturer workbook's printed square feet per foot. A member with none of these, a missing
length or an unresolved thickness is reported, never estimated. Waste and yield are refused
without a source; without them the adjusted and bag numbers are simply absent. Sides come from
the condition assignment or are assumed from the role (3 for beams, 4 for columns) and flagged.

## Next
- Manufacturer workbook rows (Isolatek intumescent, Hilti estimator) as a fourth candidate class.
- Yield from the product data sheets as parsed facts (today it is a cited CLI input).
- Area items (deck, patching) and joist surface area; a quantity_sets table so stages freeze them.
- AISC section factors (W/D, A/P from the shapes database) so the equation route no longer
  depends on a chart row for the ratio.
