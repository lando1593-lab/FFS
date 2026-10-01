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

## Second collection run (2026-10-01, per-manufacturer collectors; "GCP, Carboline and any manufacturer is non-negotiable")
Method: one collector per manufacturer, each restricted to the manufacturer's own hosts, honouring
robots.txt, sending ordinary browser headers under the project's own user agent, never passing a
bot challenge, never logging in, pacing requests, confirming every URL with a HEAD/GET before it
entered a registry, then fetching through `ffs fetch-sources` so every file carries the manifest
provenance (URL, time, ETag, SHA-256, content type). Registries live in
`data/reference_library/registries/<manufacturer>.json`; the confirmed hosts were added to the
shipped allowlist in `backend/src/ffs/sources/registry.json` with a note per host.

| Manufacturer | Fetched | Hosts | What it is | Not fetched, and why |
|---|---|---|---|---|
| GCP (MONOKOTE) | 195 documents | gcpat.com file paths; regional gcpat.in / .uk / .hk / .com.au / th. / ca. / beta. | **76 per-design thickness charts** (D739…Y724, 30 designs, 2016–2023 revisions), **59 UL printouts** from the current UL site (2024), 3 consolidated "UL Designs & Thickness" indexes (columns / floor / roof), design flowcharts, MK-6/HY, MK-10 HB, Z-106, Z-146, Z-156, Z-3306 data sheets, SDS, application guides | gcpat.com HTML pages are challenge-gated and were never requested; two file links answered 404 |
| Carboline | 123 documents | www.carboline.com, msds.carboline.com (RPM servlet, legacy TLS), javapublic1.rpmsfa.com, carboline-me.com | Product data sheets for every fireproofing product (Pyrocrete 239/241/241 HY/341/40, Pyrolite 15/22, Southwest 5GP/5MD/5AR/7GP/7HD/7TB/DK3, Thermo-Sorb 263/VOC/HB, Thermo-Lag 3000-P/SP, Pyroclad X1, A/D Firefilm III/III C, Firefilm IV), primer and topcoat lists (commercial and industrial, 2025–2026), Southwest UL design flowcharts (2019), the Simplified Guide to Fire Resistance Ratings (2022), UL evaluation report ER8213-01, three Thermo-Sorb HB UL printouts (N663, Y677, Y678), yield and density charts, application guides, specifications | **97 documents on carboline.canto.com** (robots.txt `Disallow: /`): the per-design UL and Intertek listings for Firefilm III/IV, Pyrocrete 40, Thermo-Lag 3000, Thermo-Sorb 263/VOC, Pyroclad X1 and the Southwest selector. Listed for one-click manual download (below) |
| Sherwin-Williams (FIRETEX) | 47 documents | industrial.sherwin-williams.com, paintdocs.com, protectiveeu.sherwin-williams.com, pages.s-w.com, icc-es.org | FIRETEX FX5090 / FX5120 / FX6002 / FX6010 / FX7002 / FX9502 data sheets (2025–2026 revisions), application manuals, approved primer and topcoat guides, ICC-ES ESR-4766 and ESR-4767 | Sherwin-Williams publishes no per-design thickness PDFs; the data sheets only cite the UL designs (D981, N636, Y623, Y624, N627, Y606, Y660, Y664, D994, N642, Y635, Y636). Those are pulled by a person from UL |
| Isolatek | 529 documents | isolatek.com | see the first run; re-fetched under unique ids | — |
| GCP, second pass (gap fill) | +113 → 308 | beta.gcpat.com (GCP's own staging host serves the challenge-free copies), ca.gcpat.com | current 2025 US data sheets for every MONOKOTE product, the three "UL Designs & Thickness" directories (floor, roof, columns; May 2025), GCP's "UL Design" summary sheets for 30 designs, the 2017 Grace design pages (Canada mirror), N784 castellated-beam design, MK-1000 HB yield chart, test reports, LEED/EPD packages | the 2026 MONOKOTE FireProtect line (N312/P306/S302/X316) and the per-product UL certificates sit on challenge-gated pages with unknown file names: browser download if wanted |
| PPG (STEELGUARD, PITT-CHAR) | 50 | www.ppg.com (ppgpmc.com redirects there), dam-cdn.ppg.com, max.ppg.com | STEELGUARD 951 data sheet (three revisions to July 2026), application guide sheets, Information Sheet 1223, approved primer and topcoat system sheets (Sept 2026), PITT-CHAR NX data sheet and 29-page application guidelines, Declarations of Performance | PPG publishes **no UL design numbers or thickness tables** anywhere; everything says "refer to the UL 263 certification". Designs are a person's UL pull (file R38529). SDS server refuses non-browser clients. STEELGUARD 601 and FM 585 have no current pages (likely superseded by 651/652 and 550): ask the rep |
| Hilti (CFP-SP WB Fire Finish 60+/120+) | 40 | www.hilti.com engineering Q&A pages, files-ask.hilti.com (Hilti's attachment bucket) | UL printouts and Hilti reprints for Y633, Y634, N640, D990, E901, Y656, Y657, N655, UL ER26677-01, primer and topcoat lists, estimator workbook with Hilti-transcribed thickness tables, application guides | productdata.hilti.com, the host behind every "Download" button, is robots-disallowed: **30 documents listed for manual download** (product data sheets, spec section, SDS, troubleshooting guide). Fire Finish 60+ designs N659, Y675, Y676 exist only on UL |
| AkzoNobel International (Interchar, Chartek) | 68 | www.international-pc.com, international.brand.akzonobel.com (DAM), AkzoNobel storage for SDS | current TDS for Interchar 1120/1120HY/212/1260/3120 and Chartek 7/7E/1709 (May–June 2026), water-borne and solvent-borne Interchar application guidelines, SDS; the 2,045-document index was enumerated through the site's own document API and saved | AkzoNobel hosts **no UL listings or thickness tables**; TDS cite only standards (and XR627 for Interchar 212). Chartek application manuals and the qualified primer list are not public: rep request |
| Albi (now Isolatek), Nullifire (Tremco CPG), Promat (Etex), Jotun, Hempel, Grace legacy | 128 (Albi 47, Nullifire 32, Promat 24, Jotun 20, Hempel 3, Grace 2) | albi.com, nullifire.com + assets.cpg-europe.com, promat.com + media.promat.com, jotun.com + Jotun datasheet store, hempel.com, ca.gcpat.com | Albi Clad TF+ UL printouts (Y649, Y650, N649, D998), DriClad designs, ESR-5089, application manual, legacy Albi Clad 800; Nullifire SC900/SC800-series data; Promat PROMASPRAY, FENDOLITE and Cafco documents; Jotun SteelMaster TDS; Hempafire sheets | Jotun's DoPs (cp.jotun.com, robots-disallowed) and Hempel's data sheets (an /api/ endpoint, robots-disallowed) are on the manual list (12 documents). Promat's US document lists load through a POST-only component and could not be enumerated. Jotun, Promat, Hempel and Nullifire designs exist only on UL |

**Audit** (an independent agent over the manifest and registries): 1,666 stored ids resolving to 1,298
distinct files (567 MB) across 13 manufacturer folders; every URL host is a manufacturer first- or
second-level domain or a DAM linked from the manufacturer's own pages; no third-party mirror, no UL
Product iQ or ICC premium URL appears in any registry or manifest row; 33 files sit on
manufacturer-owned Azure storage accounts that the manufacturers' own pages link to.

**Manual-download list** after this run: 139 documents (Carboline 97, Hilti 30, Hempel 8, Jotun 4),
committed at `docs/downloads/manual-downloads.html`.

### Human-assisted import (the robots-disallowed host)
`ffs manual-list` writes `manual_downloads.html` (one link per document, grouped by manufacturer
and product, with the file name to save) and a CSV; `ffs import-manual <folder>` files the saved
copies under the same library layout and appends manifest rows with `method: manual`, the
`manual_url`, the SHA-256 and the time. A file whose name matches no registry entry is reported
and left alone. The Carboline list is committed at `docs/downloads/carboline-manual-downloads.html`.

### Parsing coverage after this run (`ffs reference-coverage`)
- **GCP charts**: all 76 parse with the positional parser (`importers/gcp_chart.py`): 42,466 rows
  across 30 designs, two column groups where printed (normal-weight / lightweight concrete fill,
  full / half flange tip), tube and pipe tables keyed by nominal size, wall and A/P, and the
  generic "Other" rows keyed by section factor alone. 58 notes in total, every one naming the
  page and the printed cells (blank cells, a header-less continuation page, seven rows on Y724
  whose first cell is a section factor printed in the thickness column and which are therefore
  skipped rather than stored). 37 of the older-template charts print no revision date; the
  record carries `None`, not a guess.
- **GCP consolidated indexes and flowcharts**, Carboline's Simplified Guide and Southwest
  flowcharts: design selectors (assembly description → design number), not thickness tables.
  They are fetched and routed as `other`; a selector parser is a later step.
- **Carboline yield charts** (Southwest 5MD/7GP/7HD/7TB): density, water and yield tables for the
  material engine (Milestone 4), not thickness.
- **UL printouts from the current UL site** (59 GCP, 3 Carboline, 2025 layout): the parser now
  reads them (no page furniture at all, tables keyed by Hp/A alone, "Rating Period (hr)" and
  "30 min … 180 min" heads, linear `T = a·(Hp/A) + b` equation tables with ranges printed high
  to low and kept that way with a note). Library-wide: **110 of 163 UL printouts yield tables or
  equations**; the rest are wall, board and exterior designs whose thickness is stated in item
  text, which is captured. The 528 Isolatek records were re-checked count-for-count against the
  previous parser (no change beyond completed wrapped manufacturer lines and the reproduction
  notice); one GCP design (X854) had a W/D printed as "1" mis-read as a thickness before and is
  now right.
- **Library total after the full run** (`ffs reference-coverage`): 1,282 documents routed; 302
  Isolatek charts (69,535 rows) and 86 GCP charts (49,140 rows, 31 designs); 218 UL printouts of
  which 150 yield tables or equations (Isolatek 52, GCP 37, Hilti 7, Albi 4, Carboline 3, Grace 1).
  Extension-less downloads (Nullifire, Jotun) are typed from their magic bytes, so they route.
- **Where thickness data does not exist on any manufacturer host**: PPG, AkzoNobel,
  Sherwin-Williams, Jotun, Promat, Hempel, Nullifire. Their products are listed only on UL
  Product iQ (and Intertek's directory, which refuses non-browser clients). That is a person's
  pull per design, two minutes each, and the importer handles both the 2019 and the 2025 UL
  printout layouts.
- **Hilti transcribes its thickness tables into an estimator workbook**; a Hilti workbook importer
  (same shape as the Isolatek one) is the next data step for that manufacturer.

### Caveats that stay on the record
- Regional GCP hosts serve some documents the US site does not; each record carries its URL, so
  a Canadian or UK copy is never mistaken for the US edition.
- msds.carboline.com negotiates TLS with legacy renegotiation; the fetch needs an OpenSSL
  configuration that allows `UnsafeLegacyServerConnect`. The registry note records this.
- Chart rows for tubes and pipes carry the printed nominal size and wall; the AISC canonical
  designation (`HSS6X4X1/4`) is not derived yet, so `canonical` is `None` on those rows.
