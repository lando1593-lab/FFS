# E — How the design and product library gets built (hundreds of designs, many manufacturers)

The question: "how do we get the hundreds of other designs and manufacturers?"

The short answer: in three layers, driven by what the company actually bids, never by trying
to copy a listing database wholesale. The product does not need every BXUV design. It needs the
designs that the products you spray are listed in, and it needs to know which of those are
current. That set is a few hundred rows per manufacturer, not tens of thousands.

## Layer 1 — Manufacturer databases (breadth, fast)
(certain) Manufacturers already publish and hand out structured thickness data per product:
- The Isolatek intumescent estimating workbooks received today (WB 4 guide, intumescent
  estimating program V4.3) contain complete per-member tables: designation, W/D or A/P, square
  feet per linear foot, and DFT in mils for each hourly rating, for designs N614, N634, N635,
  N653, N661, X649, X650, Y614, Y615, Y616, Y669, Y670, with a column group per design or
  product variant and an explicit "extrapolated thickness is an engineering analysis" note.
- (likely) The same exists for SFRM: Isolatek's "Estimating Center" thickness charts for
  CAFCO 300/400, GCP's consolidated "all UL thickness chart" documents for Monokote, Carboline's
  design listings for Pyrocrete and Thermo-Sorb, Sherwin-Williams FIRETEX design tables.
- (likely) The EDGE's manufacturer databases are supplied by the manufacturers themselves; your
  reps can supply the same source files directly. The contact list you uploaded is the route.

Each file is ingested as a versioned `Product@Revision` + `ThicknessTable` set with the file's
own revision mark, and tagged authority level 6 (manufacturer document). This layer gives
coverage in days, not months.

## Layer 2 — UL listings (verification, on demand)
(certain) UL Product iQ pages print to PDF and parse completely with `ffs import-ul-design`
(verified on X829, S801, P922). (likely, from UL's terms as reported in research doc A) UL
does not permit automated bulk retrieval, and there is no public API. So:
- Designs are pulled by a person, one at a time, in priority order: first the designs on the
  current bid list, then the designs referenced by the Layer-1 tables for the products you use.
  Two minutes per design; two hundred designs is one person-day, once.
- Each parsed listing is stored with its "Last Updated" stamp and the print date. A listing
  older than its manufacturer table is flagged; a manufacturer table value that disagrees with
  the listing is a finding, never silently resolved.
- Re-pull only designs in active use, on a cadence (for example quarterly) or when a
  manufacturer bulletin announces a change.
- Ask UL whether a data licence for Product iQ exists for software use. (guessing) It may; it
  is not assumed in the plan.

## Layer 3 — Other listing bodies and reports
(likely) Intertek design listings and ICC-ES evaluation reports are public PDFs. They are
fetched with permission, parsed with their own importers when a product needs them, and stored
the same way. FM is not relevant to structural fireproofing listings.

## What never happens
- No scraping of UL or manufacturer sites. No bulk downloads outside published terms.
- No thickness value enters a reference table without its governing design, product,
  rating, restraint, deck condition, source file, and revision.
- No manufacturer table supersedes a UL listing; it fills in where the listing delegates
  (substitution by W/D) and is cross-checked where they overlap.

## Priority order for this company (from the documents received)
1. Isolatek: CAFCO 300/400 SFRM designs (P723 and X790 appear on the sample bid), SprayFilm
   WB 3/WB 4 and Firesolve intumescent (workbooks in hand).
2. GCP Monokote MK-6/HY, Z-106, Z-146 (data sheets in hand; designs to request).
3. Carboline Thermo-Sorb / Pyrocrete (primer lists and PDS in hand; designs to request).
4. Sherwin-Williams FIRETEX FX9502 (system set in hand; designs to request).

## Next build steps
1. Workbook importer for the Isolatek intumescent tables (wide "rating columns per design"
   layout) → ThicknessTable rows with cell-level provenance.
2. Request from reps: CAFCO 300/400 thickness charts (current), GCP all-UL thickness chart,
   Carboline design listings. Ingest with a generic table importer.
3. Pull P723 and X790 from Product iQ (current), parse, and check the sample bid's thickness
   values against them: the first end-to-end validation of Milestone 3 logic.


## First collection run (2026-10-01, network opened by the user)
Probe results through the environment proxy: isolatek.com, carboline.com, sherwin-williams.com
(protective), iccsafe.org, icc-es.org, aisc.org, nfca-online.org answer; gcpat.com, intertek.com
and iq.ulprospector.com return 403 to any non-browser client. Those three are not fetched.

| Source | Crawl result | Action |
|---|---|---|
| Isolatek (isolatek.com) | 205 pages, 778 documents: 444 under `/storage/designs_thickness/` (per-product thickness charts for CAFCO 300/400, BLAZE-SHIELD II/HP, FENDOLITE M-II/TG, SprayFilm WB 3/4/5, CAFCO Board, Albi; the full 2019 UL design set: 40 dry-mix, 28 wet-mix, 7 intumescent, 7 rigid-board designs), 51 product data sheets incl. CAFCO 300 and 400 C-TDS 10-20 and BLAZE-SHIELD II 04-23, 70 SDS, listing reports, guide specs | 525 documents fetched with provenance (SDS and non-technical PDFs skipped) |
| Sherwin-Williams protective | 36 pages, 0 documents: product documents are served without file extensions, which the crawler does not yet follow | crawler improvement queued (content-type sniffing for extension-less links) |
| Carboline | 250 pages, 2 documents; product pages redirect to http and answer 403 to automated clients | respected; documents to come from the rep or manual download |
| NFCA | 150 pages, 300 documents, mostly association admin; code-update presentations and guidance PDFs among them | fetch the guidance subset later |
| AISC shapes database | the download page serves a bot-challenge page and direct file paths return 403 | one manual download by the user; the file is then imported locally |

### Validation note from X790 (fetched copy, last updated 2019-10-09)
The sample bid lists HSS5X5X3/8 columns at 9/16 in. for 1 hour under X790. X790 gives
`h = R / (188·(A/P) + 45)` with R in minutes for A/P 0.18–0.49, rounded up to 1/16 in.
- With A/P from the nominal wall (gross 5×5 minus the 4.25×4.25 void over a 20 in. perimeter,
  A/P ≈ 0.347): h = 60 / (65.2 + 45) = 0.544 → 9/16 in. Matches the bid.
- With A/P from AISC's design wall thickness (A = 6.18 in², A/P ≈ 0.309): h = 0.582 → 5/8 in.
(certain) The two conventions give different thicknesses for the same member under the same
design. Which one the listing intends is a domain question for the estimator and the
manufacturer, and the engine must record which convention it used on every HSS/pipe result.
