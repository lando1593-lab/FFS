# D — Reference documents received 2026-10-01 (inventory of the first library sample)

The user uploaded 105 files from the company library into the session. They were catalogued with
`tools/lacie_inventory/inventory.py` (this is the tool's first run on real documents) and copied
to `data/reference_library/` (git-ignored; the files themselves are never committed). This page
records what the set contains so later milestones know what authoritative material is already in
hand, and so the user can see what the inventory tool concluded.

Classification is the tool's heuristic output, reviewed by hand. Revision dates below are read
from the documents' file names or title blocks and are the documents' own revision marks, not an
assertion that they are the manufacturer's latest. Milestone 3 ingestion must confirm currency
against the manufacturer's website before any value enters a reference table.

## Manufacturer technical data (public documents)
| Manufacturer | Document | Revision mark | Category |
|---|---|---|---|
| Isolatek | CAFCO 400 C-TDS | 10-19 | SFRM data sheet |
| Isolatek | CAFCO 400 AC C-TDS | 10-19 | SFRM data sheet |
| Isolatek | CAFCO BLAZE-SHIELD II C-TDS | 09-20 | SFRM data sheet |
| Isolatek | CAFCO CELLU-SHIELD C-TDS | 10-23 | SFRM data sheet |
| Isolatek | CAFCO SprayFilm WB 3 C-TDS | 10-19 | intumescent data sheet |
| Isolatek | FIRESOLVE SB C-TDS (two copies) | 10-24 | solvent-based intumescent data sheet |
| Isolatek | ISOLA-GUARD WB 500 I-TDS | 03-22 | topcoat/sealer data sheet |
| Isolatek | CAFCO Finish Coat Materials C-TDS | 9-14 | finish coats |
| Isolatek | FENDOLITE M-II and TG application/installation manual | May 2016 r1 | application guide |
| Isolatek | Firesolve long-form and short-form application guides | 10-24 | application guides |
| Isolatek | Primers for CAFCO SprayFilm C-TDS | 11-22 | primer list |
| Isolatek | Firesolve primer list | — | primer list |
| Isolatek | Tech Release 2025-15 (IFRM/SFRM separate but intersecting members) | 5-13-25 | technical bulletin |
| Isolatek | Tech Release 2025-16 (IFRM/SFRM on the same member) | 5-13-25 | technical bulletin |
| Isolatek | Tech Release 2025-26 (primers for commercial-density SFRMs) (two copies) | 2025 | technical bulletin |
| Isolatek | SFRM abutting IFRM on same member (letter + drawing) | — | technical guidance |
| Isolatek | Wood nailer/runner reference | — | detail guidance |
| Isolatek | 28-day cure letter | 2025 | technical letter |
| Isolatek | Sample warranty | — | warranty |
| Isolatek | SprayFilm takeoff request form | 1-10-19 | estimating form |
| Isolatek | WB 3 estimating guide (.xls, two copies), WB 4 estimating guide (.xlsm) | — | manufacturer estimating workbooks (cite UL N614, N635, N653) |
| Isolatek | Intumescent estimating program V4.3 (.xlsm) | — | manufacturer estimating workbook (cites UL Y615, Y669, Y670) |
| Isolatek | Firesolve CHPD/VOC compliance documents, LEED v4 bulletin | 2019–2025 | sustainability/compliance |
| Isolatek | FIRESOLVE SB SDS | — | SDS |
| Isolatek | Evaluation report R13348 | 2016-08-23 | listing/evaluation report |
| GCP (Monokote) | MK-6/HY data sheet (#5546) | — | SFRM data sheet |
| GCP (Monokote) | MK-10 HB data sheet (#5266) | — | SFRM data sheet |
| GCP (Monokote) | Z-106/G (#4961), Z-106/HY (#4966) data sheets | — | SFRM data sheets |
| GCP (Monokote) | Firebond concentrate (#7306, two copies) | — | bonding agent data sheet |
| GCP (Monokote) | Firesafing | 2016 | product literature |
| GCP (Monokote) | Universal P917 track-to-steel letter (project-specific) | — | technical letter |
| Carboline | Thermo-Sorb HB PDS | — | intumescent data sheet |
| Carboline | Acceptable intumescent primer list | 04-07-20 | primer list |
| Carboline | Primer list (xlsx) | 12-2019 | primer list |
| Carboline | Thermo-Sorb VOC primer list (xlsx), T-Sorb approved primers | — | primer lists |
| Carboline | Thermo-Lag primer list | — | primer list |
| Carboline | Acceptable topcoat list | — | topcoat list |
| Carboline | ICC report letter, Thermo-Sorb VOC products (two copies) | 2023 | listing correspondence |
| Carboline | Cold-weather SFRM application | — | technical guidance |
| Sherwin-Williams | FIRETEX FX9502 data sheet, primer guide, topcoat guide, application manual | manual issue 1 rev 1, 13 May 2021 | intumescent system set |
| Sherwin-Williams | Heat-Flex 7000 data sheet | — | coating data sheet |
| Sherwin-Williams | Waterbased epoxy B73-300 TDS + SDS | — | primer data |
| Sherwin-Williams | ASTM comparisons, solvent-based intumescent | Oct 2024 | technical comparison |

## Listings and code references
| Document | Notes |
|---|---|
| UL design P922 (two copies) | roof-ceiling design; full design text present |
| UL design X829 | column design; full design text present |
| UL design S801 | roof beam design (per BXUV prefix convention); full design text present |
| UL certification letter | needs reading to identify subject |
| 2021 IBC significant changes, §704.6.1 secondary steel overspray | code commentary |
| NFCA GI 1002, primed or painted steel | industry guidance (National Fireproofing Contractors Association) |

All three UL designs are Product iQ printouts dated 4/24/2019 (X829 last updated 2018-05-03,
S801 2018-05-08, P922 2019-02-11). They parse completely with `ffs import-ul-design`: X829 yields
two thickness equations with W/D ranges and two 7-row size tables (contour, and flange tips
reduced); S801 one rating table; P922 six rating tables across items 3, 7, 7D, 7E plus the
manufacturer Type lists. Because they are 2019 snapshots, the user will pull current copies.

## Steel shape tables (15 PDFs)
Wide-flange beams, wide-flange columns, WT columns, single angles, double angles (equal, unequal
SLBB), miscellaneous channels, HSS and pipes, pipes, rectangular and square tube, solid round
bars. (likely) These are section-factor (W/D, A/P) tables used with the fireproofing design
tables. Their source and edition must be identified before use; they are a candidate replacement
for the AISC download for section properties only if provenance is confirmed.

## Company-internal documents (categories only; contents stay in the local data folder)
- Estimating procedures: estimating guide (5-14-2024), estimating guidelines and procedures
  (.docx and PDF print), "Estimating a Job — Start to Finish" (.pptx and PDF print)
- Pricing: labor matrix (Florida, January 2026), standard patching rate sheet 2026, OCIP
  calculation worksheet, fireproofing budget worksheet (two versions)
- Proposal templates: fireproofing proposal template (5-21-2026), patching bid letter template,
  bid qualification form
- Reference sheets: surface-conditions cheat sheet, wood building lath requirements, wood
  nailers/runners quick reference, manufacturer contact list
- Admin: awarded jobs 2026, task tracker, company info sheet
- The EDGE spray report sample (see research doc C)

## What this set unlocks
- **Milestone 3 seed**: three full UL designs, eleven manufacturer data sheets, nine primer and
  topcoat lists, four Isolatek tech releases on SFRM/IFRM interfaces and primers. Enough to design
  the versioned `FireDesign` and `Product` ingestion against real documents.
- **Milestone 4 seed**: the manufacturer estimating workbooks (WB 3/WB 4, intumescent program)
  encode yield and material math as the manufacturer expresses it; the company budget worksheet
  encodes how the estimator prices. Both are inputs to the material-quantity engine's
  requirements, not formulas to copy blindly.
- **Procedures**: the estimating guide and the start-to-finish deck describe the company's own
  workflow. They should drive the UX study in the competitive matrix (what an estimator here
  actually does between takeoff and bid).

## Inventory tool observations from this run
- Before filename rules were added, 43 of 105 files were unclassified and data sheets were
  misfiled as inspection reports. With filename cues the count is 3.
- Legacy `.xls` workbooks are catalogued but their text is not read; converting them to `.xlsx`
  makes them searchable.
- Duplicate uploads (same file twice) are detected by identical SHA-256 in the catalog.
