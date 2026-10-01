# Requirements (v0)

Numbered so later docs, tests, and commits can cite them (`FR-STEEL-04`, `NFR-TRACE-02`).
Milestone column shows where the requirement is first satisfied. "Missing" marks requirements
not in the original brief that the brief implies.

## Functional requirements

### Documents and sheets (FR-DOC)
| ID | Requirement | M |
|----|-------------|---|
| FR-DOC-01 | Ingest vector PDF, scanned PDF, and (later) IFC/BIM exports; preserve page, sheet number, title, revision, scale, text coordinates, and vector geometry | 1 |
| FR-DOC-02 | Prefer native PDF text/vector data; fall back to OCR only for raster pages, and record which path was used per page | 1 |
| FR-DOC-03 | Classify sheets by discipline (S, A, M, etc.) and type (plan, section, detail, schedule, notes, code summary) with confidence | 1 (basic), 5 |
| FR-DOC-04 | Determine sheet scale from title block / viewport text; detect multiple scales per sheet; verify scale against explicit dimension strings; allow manual calibration with audit | 1 |
| FR-DOC-05 | Detect grid lines and grid bubbles; expose a grid coordinate frame per sheet/level | 1 |
| FR-DOC-06 | Version documents; store every revision; link addenda/RFIs/ASIs to the sheets they modify | 1 (store), 9 (compare) |
| FR-DOC-07 | Full-text search across drawing text and specifications, with jump-to-location | 1 (text), 2 (specs) |
| FR-DOC-08 | Auto-link plan callouts to details/sections and provide back-navigation | 5 |
| FR-DOC-09 **Missing** | Handle rotated pages, mirrored viewports, and sheets with multiple viewports at different scales (common on S-4xx detail sheets) | 1 |
| FR-DOC-10 **Missing** | Detect "NOT FOR CONSTRUCTION"/"PRELIMINARY"/"ISSUED FOR PERMIT" stamps and surface drawing set status | 1 |

### Steel members (FR-STEEL)
| ID | Requirement | M |
|----|-------------|---|
| FR-STEEL-01 | Recognize steel designations (W, HSS, WT, C, MC, L, HP, S, pipe, joists, girders, misc) from text; canonicalize to AISC form; preserve raw text; never merge distinct shapes | 1 |
| FR-STEEL-02 | Validate designations against authoritative AISC shape data; flag unknown shapes | 1 |
| FR-STEEL-03 | Classify each designation occurrence as physical member label, schedule entry, detail annotation, legend, callout, typical note, existing, new, or demolition | 1 |
| FR-STEEL-04 | Resolve indirect marks (B1, C3, G-12) through schedules on the same set | 1 |
| FR-STEEL-05 | Associate labels with member geometry (line/polyline on plan) and compute length from scaled geometry; store start/end coordinates and nearest grids | 1 |
| FR-STEEL-06 | Represent one physical member once, with multiple evidence references (plan, section, elevation, schedule) | 1 |
| FR-STEEL-07 | Story-aware column geometry: elevations, splices, protected lengths per level | 1 (basic), 3 |
| FR-STEEL-08 | Assign every member to a level/floor/roof and optionally a zone; produce counts and LF by designation per level | 1 |
| FR-STEEL-09 | Per-member confidence split into: identification, geometry, length, level | 1 |
| FR-STEEL-10 | Manual review actions: accept, edit, reclassify, exclude, add note; all audited | 1 |
| FR-STEEL-11 **Missing** | Duplicate detection across overlapping viewports, match-lined sheets, and plan/enlarged-plan pairs | 1 |
| FR-STEEL-12 **Missing** | Composite-deck/concrete-encased/embedded members flagged, since protection scope differs | 3 |
| FR-STEEL-13 **Missing** | Cantilevers, moment connections, and beam-to-beam framing where label refers to a partial segment | 1 |

### Code analysis (FR-CODE)
| ID | Requirement | M |
|----|-------------|---|
| FR-CODE-01 | Extract a structured ProjectCodeProfile from code summary sheets: adopted code + edition, jurisdiction, amendments, construction type, occupancy, height, stories, sprinkler status, NFPA 13 type, mixed construction, listed designs referenced | 2 |
| FR-CODE-02 | Rules engine deriving required ratings per structural element category (primary frame, bearing, floor, secondary floor, roof, secondary roof, exterior) with exceptions, reductions, and substitutions, each citing the rule and edition | 2 |
| FR-CODE-03 | Never invent missing profile values; emit review items instead | 2 |
| FR-CODE-04 **Missing** | Member-to-category mapping rules (e.g., when a beam is "primary structural frame" vs "secondary member") with per-member evidence | 2 |
| FR-CODE-05 **Missing** | Conflict reporting between code analysis sheet, spec, and drawing general notes | 2 |

### Fireproofing design (FR-DESIGN)
| ID | Requirement | M |
|----|-------------|---|
| FR-DESIGN-01 | Versioned listed-design records (agency, number, manufacturer, product, assembly, member category, restrained status, deck/concrete condition, ratings, thickness tables/formulas, W/D limits, primer/topcoat restrictions, reinforcement, source, revision) | 3 |
| FR-DESIGN-02 | Section-factor calculator for W, HSS, pipe, WT, C, L, built-up: 3-side, 4-side, box, contour; method stored with result | 3 |
| FR-DESIGN-03 | Thickness derivation from design tables/formulas with interpolation rules as published; out-of-range → review | 3 |
| FR-DESIGN-04 | Provider abstraction: no hard-coded manufacturer; scenarios compare systems without implying interchangeability | 3 |
| FR-DESIGN-05 **Missing** | Superseded-listing detection: design revision date vs project document date | 3 |

### Material and estimate (FR-MAT, FR-EST)
| ID | Requirement | M |
|----|-------------|---|
| FR-MAT-01 | Protected surface area per member from exposure geometry; theoretical quantity; waste factor; adjusted quantity; packaging units; kept separate | 4 |
| FR-MAT-02 | Intumescent math: DFT, WFT, volume solids, coats, max per-coat build, primer/topcoat, exposure | 4 |
| FR-EST-01 | Conditions and assemblies: reusable fireproofing logic applied to members; changing a condition updates members without losing geometry | 4 |
| FR-EST-02 | User-defined WBS (building, phase, level, area, zone, package, system, rating, crew, sequence) flowing into all outputs | 4 |
| FR-EST-03 | Labor/production, alternates, scenarios, Excel/CSV export | 4 |

### Exposure (FR-EXP)
| ID | Requirement | M |
|----|-------------|---|
| FR-EXP-01 | Cross-reference architectural RCPs, finish schedules, wall sections to classify CONCEALED / EXPOSED / LIKELY EXPOSED / AESS / EXTERIOR EXPOSED / UNKNOWN per member | 5 |

### Shop drawings, submittals, field (FR-SHOP, FR-SUB, FR-FIELD)
| ID | Requirement | M |
|----|-------------|---|
| FR-SHOP-01 | Vector shop drawings generated from the model: layered (base, grid, members, SFRM, intumescent, ratings, thickness, designs, notes, clouds, field notes), title-block templates, standard sheet sizes, legends, spray charts, key plans, matchlines, revision deltas | 6 |
| FR-SHOP-02 | Drawing objects remain linked to MemberInstance/Condition IDs | 6 |
| FR-SHOP-03 | Print-preview validation (font size, line weight, grayscale, density, overlaps) | 6 |
| FR-SHOP-04 | Exports: vector PDF first; SVG; DXF; DWG-compatible interchange only if reliably achievable | 6 |
| FR-SUB-01 | Spec-driven submittal checklist from Division 07 sections; package assembly; revision/status tracking; reviewer comments mapped to affected members/conditions | 7 |
| FR-FIELD-01 | Simplified field drawings, QR codes (auth-respecting), tablet mode, production/inspection marks | 8, 10 |
| FR-REV-01 | Revision comparison: added/removed/changed members, ratings, exposure, details, specs; impact on estimate, material, shop sheets, field areas; auto-clouds | 9 |
| FR-QA-01 | Pre-issue QA checks (unassigned protected members, conflicting ratings, unknown design, missing thickness, superseded design, legend/usage mismatch, estimate/shop mismatch, stale revision) | 6 |
| FR-OPS-01 | Separate quantities: estimate revision, contract, approved, forecast, shop rev, field rev, installed | 10 |
| FR-INT-01 | Optional Procore integration (never required) | 10 |

## Nonfunctional requirements
| ID | Requirement |
|----|-------------|
| NFR-TRACE-01 | Every fact/calculation has provenance (doc, sheet, location, evidence, confidence, reasoning, rule, verification). Enforced by schema: evidence FK is NOT NULL on member and derived rows. |
| NFR-TRACE-02 | Every mutation is an AuditEvent with actor, before/after, reason. |
| NFR-TRACE-03 | Click any quantity → full derivation chain in UI/API. |
| NFR-ACC-01 | Golden-project metrics gate releases: detection precision/recall, designation accuracy, length error distribution, duplicate rate. Targets set after first real golden. |
| NFR-DET-01 | Geometry, quantities, rules, calculations are deterministic and unit-tested. LLM output never writes FACT or CALCULATION rows. |
| NFR-PRIV-01 | Local/private processing path; no document leaves the deployment without explicit configuration. |
| NFR-VER-01 | All reference data (code, listings, manufacturer) is versioned with effective/revision dates; queries are "as of" a date. |
| NFR-PERF-01 | A 300-sheet set ingests in background with per-sheet progress; viewer interactions stay under 100 ms for pan/zoom on cached tiles. |
| NFR-IDS-01 | ULIDs for all entities; IDs never reused; soft-delete only. |
| NFR-LACIE-01 | Reference library is read-only; the inventory tool opens files read-only and never writes into the library path. |
| NFR-OFF-01 | Field mode must tolerate offline use (design the model for sync; implement in M10). |


## Added 2026-10-01 — intelligent first pass (see docs/08-gap-analysis.md)
| ID | Requirement | M |
|----|-------------|---|
| FR-PRE-01 | Project preflight over the whole document set producing a typed ProjectProfile (project info, document set, building data, fire-resistance summary, structural systems, architectural exposure cues, specified fireproofing) with per-field evidence | 2 |
| FR-PRE-02 | Missing-document detection: referenced sheets, details, designs and addenda not in the set, with estimating impact | 2 |
| FR-SCOPE-01 | Five-state scope classification per member (in / out / likely in / likely out / unknown) with reason and evidence; never defaults to "all steel sprayed" | 2 |
| FR-SCOPE-02 | Exclusion categories flagged, not auto-excluded (existing, demo, temporary, misc metals, stairs, embedded, alternate assemblies, outside limits) | 2 |
| FR-EXP-02 | Intumescent candidate detection with confidence tiers from architectural cues; dedicated review mode with bulk accept | 5 |
| FR-REV-01 | ReviewItem entity for unknown / conflict / missing document / assumption / RFI candidate with known / likely / why / missing / options and a lifecycle | 2 |
| FR-REV-02 | Bulk actions by level, area, zone, type, designation, rating, protection, exposure, condition, grid range, sheet, confidence; preview before apply; audited | 2 |
| FR-REV-03 | Natural-language editing as a front end to bulk actions, always previewed | Future |
| FR-SCN-01 | Physical member layer immutable; all interpretation scenario-scoped (ADR-0005) | 2 |
| FR-SCN-02 | Product switching and live recalculation with deltas (quantity, members affected); mixed systems by zone | 4 |
| FR-SCN-03 | Scenario comparison (base, alternates, VE, post-bid) on quantities, LF, surface area, special conditions | 4 |
| FR-SPEC-01 | Specification intelligence: acceptable products, basis of design, substitutions, surface prep, primer, bonding agent, reinforcement, density, testing, inspection, patching, finish, environmental, submittals, warranty, closeout | 3 |
| FR-CONF-01 | Conflict engine with conflict IDs, evidence for each side, resolution options; never silently chooses | 2 |
| FR-ASSUME-01 | Assumption register from ASSUMPTION assertions and engine defaults; accept / edit / delete / convert to RFI / add to proposal exclusions | 2 |
| FR-RFI-01 | RFI candidates drafted from unresolved items; never sent automatically | 3 |
| FR-READY-01 | Resolution meter derived from unresolved items by category; bid-readiness list; proceeding allowed with items visible | 4 |
| FR-STATE-01 | Estimated / contracted / approved / field / as-built stages as frozen snapshots | 10 |
| FR-MEM-01 | Correction memory: AI proposal, human decision, reason, class (company practice / estimator preference / project-specific / code / manufacturer); informs proposals, never becomes a rule automatically | 5 |
| FR-COND-01 | Special-condition detectors (primed, galvanized, painted, exterior, bonding agent, lath/mesh, topcoat, density, patching, deck interfaces, trusses, joists) from notes and specs; evidence-driven | 3 |
