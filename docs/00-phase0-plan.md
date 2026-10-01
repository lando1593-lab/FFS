# Phase 0 — Foundation

Phase 0 is everything that must exist before Milestone 1 (structural steel takeoff MVP) can be
built honestly: the rules of the system, the research that informs the UX, the data model that
every later milestone depends on, the LaCie inventory tool, and a first vertical slice proving
`structural PDF → member database → counts + LF → visual verification`.

## Deliverables and status

| # | Deliverable | Status | Where |
|---|-------------|--------|-------|
| 1 | Environment inspection | Done | This file, §Environment |
| 2 | LaCie drive inventory | **Blocked: drive is on your local machine, not this cloud container** | Tool ready: `tools/lacie_inventory/` |
| 3 | Research A — Fireproofing domain ledger | Drafted (≈7,000 words, 79 source URLs). **Caveat: this container's proxy blocked every vendor/ICC/UL page; content is from search-result excerpts and every number is flagged re-verify.** Needs your domain review | `docs/research/A-fireproofing-domain-ledger.md` |
| 4 | Research B — Competitive workflow matrix | Drafted (≈6,000 words, 89 URLs, 11 products × 21 dimensions). Same proxy caveat: vendor and review sites were unreachable; only Procore's public API repo was read directly. Needs your review, especially The EDGE section | `docs/research/B-competitive-workflow-matrix.md` |
| 5 | Vision → requirements (functional + nonfunctional + missing) | Done, v0 | `docs/02-requirements.md` |
| 6 | Production architecture incl. drawing-generation service | Done, v0 | `docs/03-architecture.md`, `docs/adr/` |
| 7 | Schema / data model | Done, v0 | `docs/04-data-model.md`, `backend/src/ffs/db/models.py` |
| 8 | M1 pipeline design | Done, v0 | `docs/05-milestone1-pipeline.md` |
| 9 | Golden project framework + metrics | Framework done; synthetic golden #0 generated; real goldens need your drawings | `docs/06-golden-projects.md`, `golden/` |
| 10 | First vertical slice (code) | Runs end-to-end on synthetic golden #0: recall 1.0, precision 1.0, 0 duplicates, length error 0.0%; 52 tests pass | `backend/` |
| 11 | Open domain questions for you | Done | `docs/07-open-domain-questions.md` |
| 12 | EDGE spray-report importer (historical takeoffs → structured data) | Done; verified on the user's sample report (3 sheets, 18 items) | `backend/src/ffs/importers/edge_spray_report.py`, `docs/research/C-edge-spray-report-anatomy.md` |
| 14 | UL Product iQ design parser (BXUV) | Done; verified on X829, S801, P922 (2019 snapshots) | `backend/src/ffs/importers/ul_design.py` |
| 15 | Manufacturer thickness-workbook importer | Done; 84,444 rows from the two Isolatek workbooks, cell-level provenance | `backend/src/ffs/importers/thickness_workbook.py`, `docs/research/E-design-and-product-data-acquisition.md` |
| 16 | Public-document fetcher + crawler; first collection run (Isolatek 525 docs, NFCA 300 found) | Done | `backend/src/ffs/sources/`, `docs/research/E-…` |
| 17 | Isolatek chart importer + first design-layer validation (13/13 beams match the bid; HSS and angles differ, explained) | Done | `docs/validation/2026-10-01-sample-bid-vs-isolatek-charts.md` |
| 18 | Manufacturer collection: GCP 308 docs (86 thickness charts, 87 UL printouts), Carboline 127, Sherwin-Williams 47, PPG 50, Hilti 40, AkzoNobel 68, Albi/Nullifire/Promat/Jotun/Hempel/Grace 128; 139 documents listed for manual download; audit clean; 50 official hosts allow-listed | Done | `docs/research/E-…`, `data/reference_library/registries/` |
| 19 | GCP MONOKOTE chart parser (positional, two-group; derived HSS canonicals) | Done; 86 charts, 49,140 rows, 31 designs | `backend/src/ffs/importers/gcp_chart.py` |
| 20 | Human-assisted import (`manual-list`, `import-manual`) and per-manufacturer coverage report (`reference-coverage`) | Done | `backend/src/ffs/sources/manual.py`, `backend/src/ffs/importers/coverage.py`, `docs/downloads/` |
| 21 | Parser extensions from the real library: intumescent decimal tables and `T=k/(W/D)` equations, A/P pipe-tube tables, joist and AISC/metric chart layouts, generic 300-series charts | Done; 302 Isolatek charts with rows (0 without), 69,535 rows; 150 of 218 UL printouts (incl. the current-site 2025 layout) with tables or equations; 118,675 chart rows | `backend/src/ffs/importers/` |
| 22 | Design layer: thickness resolution engine over the parsed library (UL tables, UL equations, manufacturer charts; cross-references; restraint/product/application/condition filters; conflict and review statuses) + `ffs check-bid` | Done; reproduces validation 1 (13/13 beams, HSS conflict, angles review) | `backend/src/ffs/design/`, `docs/09-design-layer.md` |
| 13 | One-command local LaCie inventory bootstrap | Done (macOS/Linux `run.sh`, Windows `run.ps1`); tool under adversarial review | `tools/lacie_inventory/` |

## Environment (this session)
- Cloud Linux container, Python 3.11, `uv`, Node 22, Postgres client. PyMuPDF and Shapely install cleanly.
- No removable media is mounted. The LaCie drive **cannot** be inventoried from here. The inventory
  tool is written to be run on the machine the drive is plugged into; it writes a catalog
  (SQLite + JSONL + CSV) that can be committed or shared without copying the source files.

## What Phase 0 deliberately does not do
- No pricing, labor, or material math yet (Milestones 3–4). The data model reserves the slots.
- No UL/manufacturer data ingestion. Only the schema and the provenance rules for it.
- No web UI yet. Visual verification in this phase is a vector overlay PDF produced by the CLI,
  which proves the geometry pipeline before we spend effort on a viewer.
- No LLM usage at all. The M1 slice is fully deterministic so accuracy numbers mean something.

## Exit criteria for Phase 0 → Milestone 1
1. You have run the LaCie inventory and committed (or shared) the catalog summary.
2. You have supplied at least two real structural drawing sets (vector PDF preferred) and
   hand-verified counts/LF for at least one level each. These become golden projects 1 and 2.
3. The M1 pipeline reports detection / classification / length / duplicate metrics against them.
4. Open domain questions in `docs/07-open-domain-questions.md` have answers or explicit deferrals.

## Research caveats you must know
Both research documents were produced from this cloud container, whose outbound proxy blocked
direct reads of essentially every vendor, code, and listing website. The agents fell back to
search-engine result excerpts of those pages and cited the URLs. That means:
- Structural claims (what a UL design page contains, how The EDGE's fireproofing workflow is
  organized, which Procore API endpoints exist) are reasonably reliable and tagged.
- Every numeric value (bag weights, yields, IBC thresholds, mils per coat) is tagged (likely) at
  best and must be re-read from the live document before it enters any reference table. The
  ledger says `UNKNOWN — verify against source` wherever a value could not be found.
- First-hand estimator forum threads could not be read. The "frustrations" lists lean on review
  snippets.
A pass from a machine with normal internet access (or your own reading of the EDGE/BuzzBID
material and the LaCie library) is the next step for both documents.

## Golden #0 result (synthetic, committed)
| metric | value |
|--------|-------|
| truth members / predicted | 40 / 40 |
| recall / precision | 1.0 / 1.0 |
| duplicates / FP / FN | 0 / 0 / 0 |
| length error median / p95 | 0.0 / 0.0 |
| distractors correctly excluded | 4 schedule entries, 1 note designation |
All 40 members are flagged yellow (review) because the sheet scale came from title-block text
only and was not corroborated by a dimension string for each member. That is the intended
behaviour: a text-only scale is a 0.75-confidence fact.

## Known limitations of the slice (honest list)
- Vector PDFs only. Scanned sheets are detected and flagged; OCR is not implemented.
- Columns are not taken off (plan pass finds beams/girders; columns need schedule + elevation logic).
- Indirect marks (B1 → schedule) are classified but not yet resolved to sections.
- Member type for HSS/pipe/angles is "unknown"/"misc" pending context rules.
- No cross-sheet dedupe (enlarged plans, matchlines) yet.
- Scale is per sheet; multi-viewport sheets are flagged, not handled.
- Dimension corroboration raises per-member length confidence but does not yet raise the sheet's
  scale confidence globally.


## Roadmap re-cut (2026-10-01, after the "intelligent first pass" standard)
Milestone numbers from the original brief are kept; content is re-balanced so that review-queue
infrastructure arrives early and reference data (already in hand) is used sooner.

| Milestone | Content | Depends on |
|---|---|---|
| M1 | Structural takeoff on real drawings: schedules, columns, cross-sheet dedupe, OCR path, two real goldens with measured accuracy | user's drawing sets |
| M2 | Preflight + code profile + ReviewItem entity + physical/interpretation split (ADR-0005) + scope engine + conflict and missing-document engines + bulk actions (CLI/API) | M1 detector accuracy |
| M3 | Design engine: section factors, thickness resolution against the parsed UL designs and manufacturer charts/workbooks, spec intelligence, special-condition detectors, RFI candidates | reference library (in progress) |
| M4 | Material quantities, scenarios, product switching with deltas, resolution meter, bid readiness | M2, M3 |
| M5 | Exposure engine and intumescent review workspace; correction memory | architectural sheet understanding |
| M6–M10 | Shop drawings, submittals, field drawings, revisions, operations/stages (unchanged) | M4 |
The web viewer (drawing-first review UI) starts at M2 because the review queue is unusable
without it.
