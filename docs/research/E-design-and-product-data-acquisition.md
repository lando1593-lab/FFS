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
