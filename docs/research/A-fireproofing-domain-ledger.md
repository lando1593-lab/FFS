# A — Fireproofing Domain Ledger

**Purpose.** A map of the authoritative sources, their structure, and the data the platform must capture for structural-steel fireproofing takeoff, estimating and shop drawings. It is deliberately *not* a copy of any source's contents.

**Research date:** 2026-10-01.

**Method and a critical caveat on provenance.** Direct page fetches were blocked by the network egress proxy for every external domain attempted (ICC, UL, AISC, Isolatek, GCP, Carboline, ASTM, up.codes, Wikipedia and others). Every statement below therefore comes from search-engine result excerpts attributed to the listed URLs, not from reading the documents themselves. Consequently:

- **(certain)** is used only where the excerpt was attributed to the primary document itself (e.g., a manufacturer PDS hosted on the manufacturer's domain, or ICC's own code page) *and* the fact is structural rather than numeric.
- **(likely)** marks facts drawn from excerpts of primary or reputable secondary sources that must be re-read before being hard-coded.
- **(guessing)** marks inferences.
- Any number quoted here (hours, psf, mils, board feet, bag weights) is **reproduced from a search excerpt and must be re-verified against the live document before entering the product database**. Where a value could not be found it is written `UNKNOWN — verify against source`.

Absolute rule honoured: no UL design contents, thicknesses, W/D limits, yields, packaging or code thresholds have been invented. Where an excerpt reported a value, the source URL and the document date visible in the excerpt are given.

---

## 1. Code framework (IBC)

### 1.1 Editions and adoption

- The International Code Council publishes a new IBC edition every three years; the recent editions are **2015, 2018, 2021 and 2024** (certain — ICC publication cadence; see https://www.iccsafe.org/adoptions/code-adoption-map/IBC and https://specta.build/codes/editions/ibc).
- The IBC is a *model* code. It has legal force only when a state or local jurisdiction adopts it, usually with amendments, and the edition in force varies by jurisdiction and lags publication by roughly one to three years (likely — ICC "How States Adopt I-Codes": https://www.iccsafe.org/wp-content/uploads/adoption_ordinances/HowStatesAdopt_I-Codes.pdf; ICC adoption map; Oklahoma example of 2018 IBC effective 2021-09-14: https://oklahoma.gov/oubcc/codes-and-rules/international-building-code-adoptions.html).
- Jurisdictions amend during adoption "to reflect local practices and laws"; California, for example, allows local amendments only if more stringent and justified by local conditions (likely — ICC adoption pages). Large cities (New York City, Chicago) maintain their own codes derived from, but not identical to, the IBC (likely — NYC Admin Code 703.3 mirrored at https://codelibrary.amlegal.com/codes/newyorkcity/latest/NYCadmin/0-0-0-168977; Chicago 14B-7-704 at https://codelibrary.amlegal.com/codes/chicago/latest/chicago_il/0-0-0-2663555).
- ICC publishes state/local adoption charts as PDFs (e.g., https://www.iccsafe.org/wp-content/uploads/Master-I-Code-Adoption-Chart-Jan-2023.pdf) and the interactive map at https://www.iccsafe.org/adoptions/code-adoption-map/IBC (likely).
- Public read-only code text is at https://codes.iccsafe.org (ICC's own viewer; free "public access" tier) and at third-party mirrors such as up.codes (likely). Both were egress-blocked in this session.

**Data-model implication.** A project must carry: `code_family` (IBC / NYC BC / etc.), `edition_year`, `jurisdiction`, `amendment_set_ref`, and `effective_date`, because the same building element can have different rating requirements under different editions/amendments. Never store "the IBC value"; store the value *as adopted*.

### 1.2 The project "code analysis" sheet

- Architects place a building-code summary on the General (G-series) sheets (e.g., G-001). It states applicable code and edition, occupancy, construction type, height/area, sprinkler status, and the fire-resistance ratings for the structural frame, bearing walls, floor and roof construction (likely — Archtoolbox sheet-numbering guide https://www.archtoolbox.com/construction-document-sheet-numbers/; Biloxi code summary form https://biloxi.ms.us/wp-content/static/formspermits/BuildingCodeSummaryForm.pdf).
- Clark County NV's fireproofing permit guide BPG-053 (revised 2025-12-15 per excerpt) requires "a complete building code analysis, prepared by the Architect of Record ... indicating the applicable code, type of construction, and fire-resistance rating requirements for all building elements" and structural framing backgrounds showing required fireproofing per member, e.g. `W8x10 (5/8")` or `W8x10 (3-hours)` (likely — https://www.clarkcountynv.gov/adobe/assets/urn:aaid:aem:f02bab66-d54d-462d-9cd1-52afd3ce51fc/original/as/BPG-053-Fireproofing-for-Steel-Construction.pdf).

**Data-model implication.** The code analysis sheet is the *project-level* authority for required hourly ratings. Capture it as a first-class record (`CodeAnalysis`) with ratings per Table 601 row, sprinkler status, and the roof-height/sprinkler trade-offs claimed, plus the sheet number and revision.

### 1.3 Chapter 6 — Types of construction, Table 601, Section 602

- **Table 601, "Fire-Resistance Rating Requirements for Building Elements (hours)"**, has rows for: primary structural frame; bearing walls (exterior, interior); nonbearing walls and partitions (exterior — refers to Table 705.5; interior); floor construction and associated secondary members; roof construction and associated secondary members. Columns are construction types I-A, I-B, II-A, II-B, III-A, III-B, IV (subtypes in 2021+), V-A, V-B (likely — https://codes.iccsafe.org/s/IBC2021P1/chapter-6-types-of-construction/IBC2021P1-Ch06-Sec601; secondary summary https://www.field-pm.com/charts/ibc-fire-resistance-ratings).
- Excerpted primary-structural-frame hours (2021): I-A 3, I-B 2, II-A 1, II-B 0, III-A 1, III-B 0, IV HT, V-A 1, V-B 0 (likely — same ICC URL; verify against adopted edition; 2021 Type IV-A/B/C mass-timber columns differ).
- **Footnotes that change takeoff scope** (likely — excerpts of the ICC Table 601 page and the 2015 IBC Commentary https://cms4files1.revize.com/marshfieldwi/Development%20Services/Permits%20and%20Inspections/IBC%20Types%20of%20Construction.pdf):
  - Footnote a: structural frame members supporting *roof only* may have the rating reduced by 1 hour in certain types (I-B, II-A noted in excerpt).
  - Footnote b: roof construction, including primary frame members supporting only the roof, needs no rating where every part of the roof is 20 ft or more above any floor below, **except** in Group F-1, H, M and S-1 occupancies.
  - Footnote d (2021 wording per excerpt): an approved NFPA 13 sprinkler system (903.3.1.1) "shall be allowed to be substituted for 1-hour fire-resistance-rated construction, provided such system is not otherwise required by other provisions of the code or used for an allowable area increase in accordance with Section 506.3 or an allowable height increase in accordance with Section 504.2"; not permitted for exterior walls.
- **Section 602** defines each construction type (I/II noncombustible; III noncombustible exterior walls; IV heavy timber / mass timber; V any permitted material) (likely — up.codes CT viewer https://up.codes/viewer/connecticut/ibc-2021/chapter/6/types-of-construction).
- **Section 202 definitions** (2021): *Primary structural frame* = columns; members with direct connections to columns including girders, beams, trusses and spandrels; floor/roof members with direct connections to columns; bracing members essential to vertical stability under gravity load. *Secondary members* = members without direct connection to columns; floor/roof members without direct connection to columns; bracing not designated primary (likely — ICC significant-changes PDF https://www.iccsafe.org/wp-content/uploads/2021_SigChanges_IBC_202_StructuralMbrs.pdf and ICC BSJ article https://www.iccsafe.org/building-safety-journal/bsj-technical/significant-changes-to-definition-of-structural-members-in-the-2021-international-building-code/).

**Data-model implication.** Every steel member needs a `frame_role` ∈ {primary_frame_column, primary_frame_member, floor_secondary, roof_secondary, bracing_primary, bracing_secondary, lintel/shelf_angle, misc}, a `supports` flag (floor / roof-only), a `roof_clear_height_ok` flag, and an `occupancy_group` so the Table 601 footnotes can be evaluated per member rather than per building.

### 1.4 Chapter 7 — Fire-resistance determination and structural members

- **703.2** Fire-resistance ratings are determined by test per ASTM E119 or UL 263 (703.2.1/703.2.2), without credit for sprinklers, or per 703.2.3; **703.3** permits alternative methods: prescriptive designs per **Section 721**, calculations per **Section 722**, engineering analysis based on E119/UL 263 comparison, and alternative-material approval under 104.11 (likely — up.codes https://up.codes/s/alternative-methods-for-determining-fire-resistance; ICC 2018 https://codes.iccsafe.org/s/IBC2018/chapter-7-fire-and-smoke-protection-features/IBC2018-Ch07-Sec703.3).
- **Section 722** calculated fire resistance includes steel-member procedures that use **weight-to-heated-perimeter W/D** tables with separate *contour* and *box* profile values (Table 722.5.1(x) series) (likely — up.codes "Weight-to-Heated Perimeter" https://up.codes/s/weight-to-heated-perimeter and "Structural Steel Columns" https://up.codes/s/structural-steel-columns).
- **Section 704** (2018/2021 numbering; verify per edition) (likely — up.codes section index https://up.codes/s/fire-resistance-rating-of-structural-members and AWC FAQ https://awc.org/faq/what-is-the-correct-application-of-2018-ibc-sections-704-2-column-protection-and-704-3-protection-of-the-primary-structural-frame-other-than-columns-to-wood-construction/):
  - 704.2 Column protection: individual encasement on all sides for the full column height **including connections**, continuous through ceiling spaces.
  - 704.3 Protection of the primary structural frame other than columns: individual encasement (membrane protection is not accepted for primary frame members other than in the specific exceptions).
  - 704.4 Protection of secondary structural members: individual encasement **or** the membrane of a rated wall/horizontal assembly (704.4.1 light-frame studs; 704.4.2 horizontal assemblies per 711).
  - 704.10 (2018/2021) Exterior structural members: highest rating from Table 601 (frame), Table 601 (exterior bearing walls) or Table 705.5 (separation distance).
  - 704.11 Bottom flange protection: not required at the bottom flange of lintels, shelf angles and plates spanning ≤ 6 ft 4 in (whether primary frame or not), nor for such members not part of the structural frame regardless of span (likely — https://up.codes/s/bottom-flange-protection).
  - 704.13 Sprayed fire-resistant materials: application must match the listing (thickness, dry density, method, substrate condition, bonding adhesives, sealants, reinforcing); substrates free of primers/paints/encapsulants other than those fire-tested and listed; minimum cohesive/adhesive bond strength 150 psf (five tests per ASTM E736), with high-rise bond-strength tiers (430 psf for 75–420 ft, 1,000 psf above 420 ft) introduced in Section 403 (likely — https://up.codes/s/sprayed-fire-resistant-materials-sfrm; F&R summary https://www.fandr.com/sic-blast-sfrm-code-alert/).
  - 704.14 Mastic and intumescent fire-resistant coatings: must be applied per listing and inspected per Chapter 17 (likely — same section index; AWCI 12-B references).
- **Chapter 17 special inspection**, 1705.15 (SFRM) and 1705.16 (mastic/intumescent) in 2018/2021 (likely — https://codes.iccsafe.org/content/IBC2021P2/chapter-17-special-inspections-and-tests; https://up.codes/s/sprayed-fire-resistant-materials). Excerpted 1705.15 rules: inspections cover substrate condition, thickness, density, bond strength, finished condition; thickness per ASTM E605 with ≥ 4 measurements per 1,000 ft² of sprayed deck per story and on ≥ 25 % of structural members per floor; no more than 10 % of measurements below the design thickness; density per E605 not less than the listed density. Numbering shifts between editions (2012 used 1705.13/1705.14).

**Data-model implication.** Store the `protection_method` per member (individual encasement vs membrane), the `exclusion_reason` for members needing no protection (704.11 lintel, 601 footnote b roof, 0-hr construction type), and the applicable `special_inspection_regime` (IBC section + AWCI manual edition) so the field-QC module can generate the right sampling plan.

---

## 2. Listing bodies and design conventions

### 2.1 UL Solutions — BXUV category and Product iQ

- UL's fire-resistance designs are published in product category **BXUV** ("Fire-resistance Ratings — ANSI/UL 263"); the Canadian equivalent is **BXUV7** (CAN/ULC-S101) (likely — design PDFs mirrored by manufacturers, e.g. https://www.isolatek.com/storage/designs_thickness/2019_ul/Wet%20Mix/X790.pdf; https://albi.com/wp-content/uploads/2019/06/D_998_UL263_ULC_S101.pdf).
- **Design-number convention** (from the BXUV Guide Information as excerpted at https://pacinternationalllc.com/pdf/Test_Data/ULTESTS/BXUV.Gernaral%20Provisions%20-%20Fire-resistance%20Ratings%20-%20ANSI_UL%20263%20_%20UL%20Product%20iQ.pdf and UL's terminology article https://www.ul.com/news/explaining-ul-solutions-guide-information-fire-resistance-ratings-terminology) (likely):
  - "The prefix letter designates the group of construction, the first number designates the type of protection, and the other numbers and letters identify the particular assembly."
  - **A** floor-ceiling, concrete with *cellular* steel floor units and beam support; **D or E** floor-ceiling, concrete with steel floor units and beam support; **G** floor-ceiling, concrete and steel joists; **J or K** floor-ceiling, precast and field-poured concrete; **L** floor-ceiling, wood or wood/steel joist; **N** beam designs for floor-ceiling assemblies; **P** roof-ceiling designs; **S** beam designs for roof-ceiling assemblies; **U or V** walls and partitions; **X or Y** column designs; **XR** designs tested to UL 1709 (hydrocarbon).
  - Excerpt: "A D700 series design is a floor-ceiling assembly utilizing concrete and steel floor units with a structural support entirely protected with spray applied fire resistive material." The series number (700/800/900) encodes protection type, but the full number-to-protection mapping was not retrievable: `UNKNOWN — verify against BXUV Guide Information`.
- **Restrained vs unrestrained.** Full floor/roof assemblies (A, D, G, J, P ...) carry *restrained assembly*, *unrestrained assembly* and *unrestrained beam* ratings; N and S designs come from tests on a restrained beam with partial floor/roof representation. Excerpted definitions from mirrored design pages: restrained assembly rating is the rating in the restrained condition; unrestrained assembly rating equals the unrestrained beam rating "for a maximum of 3 hours and is limited to specific floor unit types and spans" (likely — https://ca.gcpat.com/sites/ca.gcpat.com/files/2017-06/UL-Design-D925.pdf; https://www.isolatek.com/storage/designs_thickness/2019_ul/Wet%20Mix/D902.pdf). Whether a project's construction is restrained or unrestrained is decided by the engineer of record using ASTM E119/UL 263 Appendix X guidance; the fireproofing takeoff must record which rating column was used.
- **What a design page contains** (synthesised from excerpts of mirrored designs X790, D902, D925, N653, X638 and the UL Best Practice Guide) (likely):
  1. Design number, ratings available (e.g., "1, 1-1/2, 2, 3 and 4 Hr"), and a "last updated" date.
  2. Numbered component list (steel floor units/deck type and gauge; concrete type — normal-weight or lightweight — and thickness; beam/column minimum size; shear connectors; welded wire fabric; SFRM/IFRM product names by manufacturer with the manufacturer's UL file reference).
  3. Minimum member sizes, usually given as the minimum section (e.g., a specific W-shape) and/or a minimum **W/D** or **A/P**.
  4. Thickness as a table (thickness vs rating for named sections or W/D bands) and/or an equation in W/D with a valid W/D range and thickness range; separate treatment for *contour* vs *box* (and flange-tip "half-flange" options).
  5. Conditions: primer/paint restrictions, bonding agents, mesh/lath requirements for wide flanges or painted steel, deck/concrete conditions, topcoat restrictions for intumescents, exterior-use durability conditions.
- **Design-page structural example (reported, not verified).** The Isolatek-hosted BXUV.X790 PDF dated 10/29/2019 is excerpted as giving column thickness via `R/h = 75(W/D) + 32` for W/D 0.33–2.51 and `R/h = 75(W/D) + 15` for W/D 2.51–6.68, with h = SFRM thickness ¼–4½ in rounded up to the nearest 1/16 in, R = rating 60–240 min, and a note that flange-tip thickness may be halved for contour application (likely — https://www.isolatek.com/storage/designs_thickness/2019_ul/Wet%20Mix/X790.pdf and https://samacor.co/wp-content/uploads/2017/03/X790.pdf). **These coefficients are reproduced from a search excerpt only. Re-verify against the live UL listing before use; UL designs are revised.**
- **HSS/pipe example (reported, not verified).** An excerpted tube/pipe design gives `A/P_tube = t(a + b − 2t)/(a + b)` and `h = (R − 0.2)/(4.43 (A/P))`, h 0.25–3.875 in (likely — appears in excerpts for Isolatek X790/X-series PDFs; the exact design number carrying this formula is `UNKNOWN — verify`).
- **Primer/topcoat.** IBC 704.13 and UL designs restrict SFRM to bare steel or to primers/paints that were included in the fire test; Isolatek's ISOLUTIONS bulletin on primed steel (10-19) is excerpted as allowing SFRM over painted/primed steel only when bond-test conditions are met and the beam flange width ≤ 12 in / column flange width ≤ 16 in (largest tested), otherwise mechanical reinforcement (metal lath, studs) is required (likely — http://www.isolatek.com/storage/Isolutions/ISOLUTIONS_V9_Primed-Structural-Steel-SFRM_10-19.pdf). For intumescents, the listing names compatible primers and topcoats; unlisted topcoats void the rating (likely — Hilti CFP-SP WB and FIRETEX application manuals).

### 2.2 UL Product iQ — access and terms of use

- Product iQ (https://productiq.ulprospector.com/en, info page https://iq.ulprospector.com/info/index.html) is the successor to the Online Certifications Directory; certification search is free with registration; premium features exist and are free for AHJs (likely — https://www.ul.com/news/ul-product-iq-premium-features-now-free-authorities-having-jurisdiction-ahjs).
- **Terms of use (describe, do not advise circumvention).** UL's online terms (https://www.ul.com/resources/online-policies/terms-of-use) and the Prospector/Product iQ terms (https://www.ulprospector.com/en/terms) are excerpted as stating that content "may not be reproduced or distributed in bulk, aggregated for commercial use, or otherwise used in a manner that is objectionable to UL" and that users agree "not to access (or attempt to access), or systematically retrieve data from, any part of the Sites through any automated means (including use of scripts, bots or web crawlers)" (likely). Product iQ is a B2B platform; consumer use is limited to the public search (likely).
- No public API or bulk data licence for BXUV designs was found: `UNKNOWN — ask UL Solutions directly` (UL does sell a "Product Sourcing and Certifications Database" product: https://www.ul.com/software/product-sourcing-and-certifications-database).
- Practical consequence: the platform should store **references** (design number, rating used, the date the user viewed/downloaded the listing, and the manufacturer-hosted PDF URL) and let the user upload the design PDF they are entitled to use, rather than scraping UL.

### 2.3 Intertek (Warnock Hersey) and FM

- Intertek's Building Products Directory (https://bpdirectory.intertek.com) publishes WH-listed fireproofing designs with identifiers of the form `CC/IF 180-01` (Carboline, restrained/unrestrained beam) and `CII/IF 120-01` (Contego intumescent); listings carry the Warnock Hersey mark (likely — https://bpdirectory.intertek.com/controls/SDDocumentViewer.aspx?document_id=781262&name=CC%2FIF+180-01; https://www.intertek.com/directories/).
- FM Approvals Class 4975 covers *fire-retardant coatings for interior finish*, not structural fire resistance (likely — https://fireshellcoatings.com/wp-content/uploads/2019/03/Fireshell-FM-approval.pdf). FM approval relevant to structural SFRM/IFRM: `UNKNOWN — verify`.

### 2.4 Test and inspection standards

| Standard | What it is | Edition seen in excerpts | Source |
|---|---|---|---|
| ASTM E119 | Fire tests of building construction (cellulosic time-temperature curve) | E119-24 (May 2024); excerpt reports E119-26 released Jan 2026 | https://webstore.ansi.org/standards/astm/astme11924 ; https://store.astm.org/standards/e119 (likely) |
| ANSI/UL 263 | UL's harmonised equivalent of E119 | 14th ed. 2011, revisions through 2025-09-02 | https://www.shopulstandards.com/ProductDetail.aspx?UniqueKey=23018 (likely) |
| ANSI/UL 1709 | Rapid-rise (hydrocarbon) test; furnace ≈1,093 °C within 5 min; "XR" designs | — | https://code-authorities.ul.com/wp-content/uploads/sites/40/2015/03/144182614.pdf (likely) |
| ASTM E605/E605M | Thickness and density of SFRM | E605/E605M-19 (reapproved 2023) | https://store.astm.org/e0605_e0605m-19r23.html (likely) |
| ASTM E736 | Cohesion/adhesion (bond) of SFRM | — | https://www.appliedtesting.com/standards/astm-e736-cohesion-adhesion-of-sprayed-fire-resistive-materials-applied-to-structural-members (likely) |
| ASTM E759 | Effect of deflection on SFRM | — | NYC HPD spec https://www.nyc.gov/assets/hpd/downloads/pdfs/services/07g-sprayed-fireproofing.pdf (likely) |
| ASTM E760 | Effect of impact on bonding of SFRM | — | same (likely) |
| ASTM E761 | Compressive strength of SFRM | — | same (likely) |
| ASTM E859 | Air erosion of SFRM | E859-93(2000) seen | https://store.astm.org/e0859-93r00.html (likely) |
| ASTM E2924 | **Standard Practice for Intumescent Coatings** (specifying, testing, labelling, storage, installation, inspection). Note: it is an *intumescent* practice, not an SFRM inspection practice. | E2924-14(2020) | https://www.astm.org/Standards/E2924.htm ; https://newsroom.astm.org/astm-building-committee-approves-standard-intumescent-coatings-used-protect-steel-fire (likely) |
| UL 2431 | Durability of fire-resistive coatings/materials; environmental categories (outdoor heavy industrial, outdoor general, indoor concealed, indoor exposed, elevator shafts) | — | https://datasheets.globalspec.com/ds/uls/ul-2431/cd279803-af2e-4d8c-8bc3-7e7c0de31829 (likely) |
| AWCI Technical Manual 12-A | Standard practice for testing and inspection of field-applied SFRM; the trade's inspection "bible" | 4th edition sold by ICC; AWCI articles reference 3rd | https://shop.iccsafe.org/technical-manual-12-a-field-applied-sprayed-fire-resistive-materials-4th-edition.html ; https://www.awci.org/media/codes-standards/how-many-tests-of-sfrm-are-needed/ (likely) |
| AWCI Technical Manual 12-B | Standard practice for testing and inspection of field-applied thin-film intumescent FRM, up to 660 mils; IBC 1705.16 inspections performed per 12-B | 3rd edition | https://standards.globalspec.com/std/9920077/awci-117 ; https://www.awci.org/media/codes-standards/testing-film-thickness/ (likely) |

---

## 3. Section-factor concepts (W/D, A/P)

- **W/D** = weight per linear foot (lb/ft) ÷ heated perimeter D (in). **A/P** = cross-sectional area (in²) ÷ heated perimeter P (in), used for HSS and pipe. Lower W/D ⇒ thinner steel ⇒ heats faster ⇒ thicker protection; thickness is inversely related to section factor (likely — UL Best Practice Guide 2022 https://www.ul.com/sites/g/files/qbfpbp251/files/2023-04/BE22CS758433_-_Best_Practice_Guide_for_Passive_Fire_Protection_for_Structural_Steelwork_2022_Final-Digitsl.pdf; Steel Tube Institute https://steeltubeinstitute.org/resources/keeping-your-cool-how-to-get-started-with-hss-fire-ratings/).
- **3-sided vs 4-sided.** Columns are exposed on all four sides, so the full perimeter counts. For beams supporting a slab/deck, D includes only the steel surface *not* in contact with the slab (top of top flange excluded) (likely — UL Best Practice Guide; up.codes 722 W/D pages).
- **Contour vs box.** Contour (profile) protection follows the flange/web outline; box protection spans flange tips. IBC 722 tables and UL designs list separate contour and box W/D values for the same section (excerpt example: a W14×233 has contour W/D 2.55 and box W/D 3.65 per up.codes "Structural Steel Columns" — likely; verify in the adopted edition's Table 722.5.1).
- **How UL designs express thickness.** Either a lookup table (section or W/D band → thickness per hourly rating) or an equation in W/D with stated validity ranges for W/D and thickness; results are rounded up to the nearest 1/16 in in the excerpted examples (likely — X790 excerpt). Interpolation between table rows: `UNKNOWN — each design states its own rule; verify per design`.
- **Substitution principle.** The BXUV Guide Information is excerpted as: "when a steel section with an equal or greater W/D is substituted for the specified column size of the same configuration, the same hourly rating applies," and the UL Best Practice Guide as: substituting a heavier (greater W/D) member at the same thickness is acceptable; applying a thickness listed for a larger section to a *smaller* (lower W/D) section is not (likely — https://www.ul.com/sites/g/files/qbfpbp251/files/2019-04/Best-Practice-Guide-for-Passive-Fire-Protection-for-Structural-Steelwork.pdf). Column designs "always specify a minimum steel section size implying that only sections with higher W/D (or A/P) ratios can be used, unless a special adjustment is permitted" (likely — Steel Tube Institute citing AISC DG19).
- **Beam thickness adjustment.** North American practice (IBC 722, UL N/D designs with "beam ratings") allows adjusting SFRM thickness between beams of different W/D by formula, within limits; the Canadian CISC guide excerpt gives the metric version with constraints (M/D)₂ ≥ 23 and T ≥ 10 mm (likely — https://cisc-icca.ca/ciscwp/wp-content/uploads/2017/05/SteelDesignSeries_SDS-1-1.pdf). The exact IBC 722 equation and the UL "beam only" adjustment conditions: `UNKNOWN — verify in adopted IBC 722.5.1.3 and the specific UL design`.
- **HSS/pipe/WT.** HSS and pipe use A/P with closed-form perimeter formulas per shape; many X-series designs cover tubes and pipes (excerpts name X526, X630, X638, X710, X771, X790, X795, X854 as HSS-related) (likely — https://fireproofing.us/wp-content/uploads/2020/09/UL-X638-HSS-Column.pdf; https://ca.gcpat.com/sites/ca.gcpat.com/files/2017-06/UL-Design-X795.pdf). WT, channel, angle and built-up handling: Isolatek publishes "Miscellaneous Shapes" and "Double Angle" thickness charts under X790 (likely — https://www.isolatek.com/storage/designs_thickness/mii_tg/thickness_charts/X790%20Dbl%20Angl%20Uneq.pdf). General rule: `UNKNOWN — per design`.
- **AISC Design Guide 19, "Fire Resistance of Structural Steel Framing" (2003)** — covers model codes, IBC fire-resistant design, selection of rated designs for columns/beams/trusses, worked examples, and Appendix A W/D tables (Appendix B-1 reproduces a D902 thickness example). Paid AISC publication (free to members) (likely — https://www.aisc.org/Design-Guide-19-Fire-Resistance-of-Structural-Steel-Framing; https://www.intertekinform.com/en-us/standards/aisc-design-guide-19-2003-1496938_saig_aisc_aisc_3928398/). Authors as commonly cited (Ruddy, Marlo, Ioannides, Alfawakhiri): `UNKNOWN — verify on AISC page`.
- Isolatek publishes W/D conversion factors and "square foot per lineal foot" factors derived from the AISC Manual for its long-hand estimating procedure (likely — https://www.isolatek.com/storage/designs_thickness/factors/Wide%20Flange%20Beams.pdf dated 6/13/2012; https://www.isolatek.com/wp-content/uploads/2019/10/WB-4-FINAL.pdf).

**Data-model implication.** Per shape: `weight_per_ft`, `depth`, `flange_width`, `web/flange thickness`, computed `perimeter_contour_4s`, `perimeter_contour_3s`, `perimeter_box_4s`, `perimeter_box_3s`, `area`, and derived `W/D` or `A/P` per exposure. Per design: `thickness_rule` = {table rows | equation with coefficients, validity ranges, rounding rule, exposure (contour/box), sides (3/4)}, `min_section`, `min_WD`, `max_WD`, `allowed_substitution = WD_equal_or_greater`. Store the **rule as data with a source snapshot**, never as code constants.

---

## 4. Manufacturer landscape

Packaging and yield figures below are reproduced from search excerpts of manufacturer documents; each must be re-read from the dated document before use.

### 4.1 Isolatek International (CAFCO® / ISOLATEK® Type)

- Product families confirmed from isolatek.com pages: **CAFCO 300 / 300 SB / 300 ES / 300 HS / 300 AC** (commercial-density wet-mix SFRM), **CAFCO 400** (commercial-density), **CAFCO BLAZE-SHIELD II** (dry-mix mineral-fiber SFRM), **CAFCO FENDOLITE M-II / M-II/P** (medium/high-density Portland-cement SFRM for industrial/exterior/UL 1709), **CAFCO SprayFilm WB** series (water-based thin-film intumescent) and FIRESOLVE SB, **CAFCO-BOARD** (likely — https://www.isolatek.com/construction/commercial-products/commercial-density/cafco-300-isolatek-type-300/; https://www.isolatek.com/storage/tds/CAFCO%20400_C-TDS_10-19.pdf; https://www.isolatek.com/storage/tds/CAFCO%20BLAZESHIELD%20ll_C-TDS_10-19.pdf; https://www.isolatek.com/wp-content/uploads/2026/05/CAFCO-FENDOLITE-M-ll_I-TDS_08-20.pdf).
- Design/thickness publication: "UL Designs & Thicknesses" pages per product family with per-design PDFs and thickness charts organised by Floor-Ceiling, Concrete Floor, Floor Beams, Roof, Roof Beams, Columns; Isolatek defers to UL Product iQ as the current source (likely — https://www.isolatek.com/ul-designs-thicknesses/; https://www.isolatek.com/ul-designs-thicknesses/cafco-300-400/; https://www.isolatek.com/ul-designs-thicknesses/cafco-blazeshield/; https://www.isolatek.com/ul-designs-thicknesses/cafco-sprayfilm/).
- Structured data: an "Estimating Center" with a long-hand estimating worksheet procedure (W/D or A/P plus ft²/lf factors per member) and shape factor PDFs; no public API found (likely — https://www.isolatek.com/construction/commercial-support/estimating-center/). Documents Library: https://www.isolatek.com/construction/commercial-support/documents-library/.
- Packaging/yield excerpts: CAFCO 300 sold in 50 lb bags (distributor listing https://myfbm.com/all-products/firestop-and-sound-proofing/firestop/firestop-sprays/50-lb-bag-cafco%C2%AE-300-wet-mix-sfrm-spray-applied-fireproofing-material/p/caf-300 — likely); CAFCO 300 short-form guide (10-8-19) warns that exceeding 46 bd ft/bag yields density below 15 pcf (likely — https://www.isolatek.com/wp-content/uploads/2022/12/CAFCO-300-300-SB-Short-Form-Dual-Branding-Update-Final-10-8-19.pdf); CAFCO 300 HS short form (10-9-19) gives a maximum recommended 40 bd ft/bag to hold ≥ 17.5 pcf (likely — https://www.isolatek.com/wp-content/uploads/2022/12/CAFCO-300-HS-Short-Form-dual-branding-final-10-9-19.pdf). BLAZE-SHIELD II, CAFCO 400, FENDOLITE bag weights/yields: `UNKNOWN — verify against TDS`.
- Corporate relationship with Promat/Etex (CAFCO brand in Europe): `UNKNOWN — verify`.

### 4.2 GCP Applied Technologies (MONOKOTE®) — now Saint-Gobain

- Saint-Gobain announced the acquisition of GCP Applied Technologies on 2021-12-06 and closed it on 2022-09-27 (likely — https://www.roofingcontractor.com/articles/97493-saint-gobain-completes-acquisition-of-gcp-applied-technologies; SEC filings at https://www.sec.gov/Archives/edgar/data/1644440/). gcpat.com remains the product-data host.
- Products confirmed from gcpat.com PDS pages: **MK-6/HY**, MK-6/HY Extended Set, MK-6s (commercial density, gypsum-based), **Z-106/HY, Z-106/G** (medium density, excerpt: min avg dry density 22 pcf), **Z-146, Z-146PC, Z-146T** (high density Portland-cement; excerpt: min avg 40 pcf; theoretical max yield 16.7 bd ft/bag), **Z-156PC** (excerpt: min avg 50 pcf) (likely — https://gcpat.com/en/solutions/products/monokote-fireproofing/monokote-mk-6hy-product-data-sheet; https://gcpat.com/en/solutions/products/monokote-fireproofing/monokote-z-146-product-data-sheet; https://gcpat.com/en/solutions/products/monokote-fireproofing/monokote-z-156pc-product-data-sheet; https://gcpat.com/sites/default/files/pdf/current/resource/GCPAT_monokote_z_106hy_us_4966.pdf). MK-1000: `UNKNOWN — not found`.
- MK-6/HY excerpts: minimum density 15 pcf; GCP "Simplified Yield Chart" (doc MK-453-0616) references a 60 lb bag, ~10 gal water, and nozzle yields of roughly 40–45.7 bd ft at the stated densities (likely — https://gcpat.com/sites/gcpat.com/files/2017-09/MK-453-0616%20Monokote%20MK6%20HY%20Yield.pdf). Bag weight must be confirmed on the current PDS (`verify`).
- Design/thickness publication: "UL Designs & Thickness" pages by assembly class (columns, roof assemblies, beams), per-design PDFs (e.g., BXUV.D782 dated 11/20/2024), and "All UL Thickness Chart" pages for D782 and D925 — i.e., GCP publishes consolidated thickness charts by design (likely — https://gcpat.com/en/solutions/products/monokote-fireproofing/ul-designs-thickness-columns; https://gcpat.com/en/solutions/products/monokote-fireproofing/d782-all-ul-thickness-chart; https://gcpat.com/sites/gcpat.com/files/2024-12/BXUV.D782-11202024.pdf; https://gcpat.com/en/solutions/products/monokote-fireproofing/monokote-ul-information).
- Application rules excerpt: ≤ ~½ in in one pass; ≥ 5/8 in in multiple passes after set (likely — Monokote Field Application Manual https://ceasefire.com.au/wp-content/uploads/2024/05/Monokote-Field-Application-Manual-AM.pdf).

### 4.3 Carboline (incl. Southwest Fireproofing brands)

- Families from carboline msds server: **Pyrocrete 241 / 241 HY** (high-density cementitious; PDS March 2024 excerpt: 50 lb bag, 13.3 bd ft/bag at 55 pcf), **Pyrolite 15** (gypsum SFRM, 15 pcf, up to 4 hr; PDS Oct 2024), **Southwest Type 5GP** (gypsum, up to 4 hr; PDS Sept 2022) and **Type 7GP** (Portland cement, 22 pcf average), **Thermo-Sorb VOC / HB** (thin-film intumescent; excerpt: 5 gal kits), **Thermo-Lag 3000-SP / 3000-P** (epoxy intumescent for 1–4 hr incl. hydrocarbon; excerpt: 4.5 gal kits), **Pyroclad X1** (epoxy for jet/hydrocarbon fire) (likely — https://msds.carboline.com/servlet/FeedFile/1/prod/0148/PDS:%7BPC:0148;MID:1;LID:1%7D/Pyrocrete_241_PDS.pdf; https://msds.carboline.com/servlet/FeedFile/16/prod/0149/PDS:%7BPC:0149;MID:1;LID:1%7D/Pyrolite_15_PDS.pdf; https://msds.carboline.com/servlet/FeedFile/1/prod/29AD/PDS:%7BPC:29AD;MID:1;LID:1%7D/SOUTHWEST_TYPE_7GP_PDS.pdf; https://msds.carboline.com/servlet/FeedFile/23/prod/NC06/PDS%3A%7BPC%3ANC06%3BMID%3A1%3BLID%3A1%7D/Thermo-Lag_3000-SP_PDS.pdf; https://msds.carboline.com/servlet/FeedFile/1/prod/NC25/PDS%3A%7BPC%3ANC25%3BMID%3A1%3BLID%3A1%7D/Thermo-Sorb_VOC_PDS.pdf).
- Design publication: submittal packages (PDS + UL designs) hosted on msds.carboline.com and distributor sites; Intertek WH designs also used (CC/IF series). Structured selectors/API: `UNKNOWN — none found`.
- Carboline publishes an "International Building Code Highlights for Fireproofing" bulletin (likely — https://msds.carboline.com/servlet/FeedFile/2/live/1/528/International%20Building%20Code%20Highlights%20For%20Fireproofing%20031218.pdf).

### 4.4 Sherwin-Williams (FIRETEX®)

- **FX5120** water-based thin-film (interior, up to 2 hr; excerpt lists UL designs D981, N636, Y623, Y624), **FX6002** three-component (interior/exterior, up to 3 hr, ASTM E119/UL 263), **FX7002** solvent-based thin-film, plus FX5062/FX5090 (likely — https://industrial.sherwin-williams.com/na/us/en/protective-marine/industry-solutions/fire-protection/key-products/firetex-fx5120-cellulosic.html; FX6002 application manual https://industrial.sherwin-williams.com/content/dam/pcg/sherwin-williams/protective-marine/na/us/en-us/pdfs/marketing-uploads/FIRETEX%20FX6002%20Application%20Manual.pdf).
- FX5120 PDS excerpt (revised 2025-06-10; later issue 19 dated 03/2026 also indexed): volume solids 69 % ± 3 %, max WFT per coat 56 mils (airless), theoretical coverage 1,104 ft²/gal at 1 mil DFT (likely — https://www.paintdocs.com/docs/webPDF.jsp?SITEID=SWPCGPROT&doctype=PDS&prodno=035777145722&lang=2). Pail size: `UNKNOWN — verify`.
- Design/thickness data: PDS + UL designs; S-W publishes articles on shop-applied intumescents and AESS finish standards (likely — https://industrial.sherwin-williams.com/na/us/en/protective-marine/media-center/articles/finish-standard-intumescent-cellulosic-fire-protection-aess.html).

### 4.5 PPG

- **PPG STEELGUARD 951** two-component epoxy intumescent, launched in the Americas in 2024; tested to ASTM E119/UL 263 among others; excerpt: 300–3,500 µm (12–140 mils) DFT per coat; **PPG PITT-CHAR NX** flexible epoxy intumescent for hydrocarbon/jet fire, UL 1709 (likely — https://www.ppg.com/en-US/pmc/protective-coatings/ppg-steelguard-951-protective; https://investor.ppg.com/news/news-details/2024/PPG-launches-PPG-STEELGUARD-951-fire-protection-coating-in-the-Americas/default.aspx; https://www.ppg.com/en-US/pmc/protective-coatings/ppg-pitt-char-nx-protective). UL design numbers and packaging: `UNKNOWN — verify`.

### 4.6 AkzoNobel International (Interchar®, Chartek®), Hempel, Jotun

- **Interchar 1120** single-pack water-borne thin-film, approved to UL 263, marketed for interior exposed steel in North America; **Interchar 212** epoxy intumescent with UL 263 exterior listing; **Chartek 7** epoxy intumescent with UL 1709 listing excerpted as design XR617; **Chartek 1709** (likely — https://international.brand.akzonobel.com/m/24ef1432327cb83f/original/NAM_IP_Interchar-1120_US_FLR.pdf; https://north-america.international-pc.com/chemistry/epoxy-intumescent; https://www.international-pc.com/en/products/chartek-1709).
- **Hempel Hempacore ONE / AQ** and **Jotun Jotachar / SteelMaster 600WF / 120SB**: primarily EN 13381-8 / BS 476 markets; North American UL listings `UNKNOWN — verify` (likely — https://www.jotun.com/ww-en/industries/solutions-and-brands/jotachar/products; https://ejadtech.com/coating-library/intumescent-coatings/).

### 4.7 Hilti, Nullifire (Tremco CPG), Promat (Etex)

- **Hilti Fire Finish 60+ / 120+ CFP-SP WB** water-based intumescent, tested to UL 263 up to 4 hr; Product Application Guidelines (2019 and 2024 editions) published (likely — https://www.hilti.com/c/CLS_FIRESTOP_PROTECTION_7131/CLS_INTUMESCENT_COATINGS_FOR_STEEL_7131; https://files-ask.hilti.com/original/sj/sjresxd2zi.pdf).
- **Nullifire SC803 / SC902** (Tremco CPG) — EN-market intumescents; North American UL status `UNKNOWN — verify` (likely — https://www.tremcocpg-asiapacific.com/products/nullifire-sc803).
- **Promat PROMAPAINT-SC3 / SC4** (Etex) — EN 13501-2 classifications; Promat also publishes a structural-steel PFP guide (likely — https://www.promat.com/en/construction/products-systems/products/intumescent-paints/promapaint-sc4/; https://media.promat.com/pi780664/original/979492903/promat-structuralsteelguide-jul25.pdf). North American listings `UNKNOWN`.

### 4.8 Density classes (as used in specs)

- Specs classify SFRM as low/commercial density (≈15 pcf minimum class), medium density (≈22 pcf class) and high density (≈40–55 pcf class); the exact pcf cut-offs are spec-specific (MasterSpec 078100, UFGS 07 81 00) and manufacturer-specific. Treat the class as a spec attribute and the pcf as a product attribute (likely — https://orf.od.nih.gov/TechnicalResources/Documents/Fire%20Protection%20-%20Specifications/078100%E2%80%93AppliedFireproofing_508.pdf; https://nibs-s3-wbdg3-production.s3.us-east-1.amazonaws.com/FFC/DOD/UFGS/UFGS%2007%2081%2000.pdf).

**Data-model implication.** `Manufacturer` → `ProductFamily` → `Product` (type: SFRM-wet, SFRM-dry, SFRM-high-density, IFRM-thin-film-WB, IFRM-thin-film-SB, IFRM-epoxy) → `ProductDocument` (TDS/PDS with revision date and URL), `Packaging` (unit, mass or volume, verified_from_doc_id), `YieldSpec` (bd ft/bag at pcf; ft²/gal at 1 mil with volume solids), `ListedDesign` links (design number, body, role in design, rating range), `Compatibility` (primers, bonding agents, topcoats, sealers, mesh triggers).

---

## 5. Material estimating practices

- **Takeoff unit.** SFRM is taken off as *surface area* (ft²) per member = length × (ft² per linear foot factor for the shape and exposure), then converted to **board feet** (ft² × thickness in inches) and to bags via the product's bd ft/bag yield. Isolatek's long-hand procedure and The EDGE estimating software both work this way, auto-assigning thickness from UL designs and shape databases (likely — https://www.isolatek.com/wp-content/uploads/2019/10/WB-4-FINAL.pdf; https://estimatingedge.com/construction/fireproofing/). Intumescents are taken off as ft² at a required DFT (mils) → gallons via theoretical coverage.
- **Theoretical vs applied yield.** Manufacturer yield (bd ft/bag) is a *nozzle* or *theoretical* figure at a target density; field yield is lower because of overspray, rebound, density variance, cleanup and patching. Blog-level sources quote 5–10 % waste/overspray allowances for spray systems; this is **not** an authoritative figure (guessing — https://bahlfireproofing.com/how-spray-applied-fireproofing-is-applied/). The estimator's own historical factor is the real source (see Open Questions).
- **Density drives yield.** Isolatek and GCP yield charts show yield falling as in-place density rises; exceeding the max bd ft/bag drops density below the listed minimum and fails inspection (likely — Isolatek short-form guides; GCP MK-453-0616).
- **Reinforcement, bonding and finishing triggers** (all "verify per design/TDS"):
  - Mesh/lath: required by many designs on wide flanges, on painted/primed steel beyond tested flange widths (Isolatek: beam flange > 12 in, column flange > 16 in in the painted-steel case), on deck types, or at thick applications; expanded metal lath min 1.7 lb/yd² and 25 %-coverage strip-lath rule appear in excerpted engineering-judgement documents (likely — https://www.portlandoregon.gov/bds/appeals/index.cfm?action=getfile&appeal_id=18146&file_id=21823).
  - Bonding agent/primer: required over primed steel when bond tests fail or when the design requires it; some products need a bonding adhesive on galvanised or painted steel (likely — IBC 704.13; Isolatek ISOLUTIONS V9).
  - Sealer/topcoat: exterior or high-humidity SFRM often needs a sealer; intumescents need listed topcoats for exterior/UL 2431 categories (likely).
  - Pins/clips: mechanical attachment for boards and some dense products; trigger rules `UNKNOWN — per design`.
- **Intumescent math** (certain for the formulas, which are standard coatings practice; cite KTA https://kta.com/calculating-wet-film-thickness-2/ and AkzoNobel definitions https://www.international-pc.com/content/dam/akzonobel-coatings/international-pc/gl/pdf/PC-DefinitionsandAbbreviations-1.pdf):
  - `DFT = WFT × volume_solids`; `theoretical coverage (ft²/gal at 1 mil) = 1604 × volume_solids`; gallons = area × DFT_mils ÷ (1604 × VS) ÷ (1 − loss factor).
  - Per-coat limits: each PDS states max WFT/DFT per coat (FX5120 excerpt: 56 mils WFT airless); over-building causes mud-cracking; number of coats = ceil(required DFT ÷ max DFT per coat) plus recoat windows (likely — PDS excerpts; https://huilicoating.com/what-is-dft-in-coating/).
  - Required DFT comes from the UL design table by section and rating; S-W, Hilti and Carboline publish those tables in application manuals (likely).
- **Field verification of thickness/density** (likely — IBC 1705.15 excerpts; AWCI "How Many Tests" https://www.awci.org/media/codes-standards/how-many-tests-of-sfrm-are-needed/):
  - IBC 1705.15: E605 thickness, ≥ 4 readings per 1,000 ft² of deck per story; ≥ 25 % of members per floor; ≤ 10 % of readings below design thickness; density per E605.
  - ASTM E605 (as excerpted): one density test per element type (deck, beam, column) per floor or per 10,000 ft², whichever gives more; thickness readings per member cross-section (an excerpt reports 7 for beams/girders and 12 for columns — `verify`).
  - AWCI 12-A (3rd ed. excerpt): one density test per element per 10,000 ft²; manual includes measurement-location diagrams and record templates. AWCI notes known differences among IBC, E605 and 12-A frequencies.
  - Intumescent: DFT gauges per AWCI 12-B / SSPC-PA 2; 12-B covers up to 660 mils (likely — https://www.defelsko.com/resources/intumescent-fire-resistive-coating-thickness-measurement).
  - Bond: ASTM E736, minimum five tests, 150 psf (code) — specs often require more (NYC HPD spec excerpt: 200 psf) (likely).

**Data-model implication.** Separate `TheoreticalQuantity` (area, bd ft, gallons from listed thickness/DFT) from `EstimatedQuantity` (after density target, waste %, mesh/primer/topcoat adders) and `AppliedQuantity` (bags/pails consumed, from field logs). Keep `waste_factor` as a user/company parameter with provenance, never a constant.

---

## 6. Specifications (CSI MasterFormat)

- MasterFormat 2011 numbers and titles (likely — NYC MasterFormat list https://www.nyc.gov/html/oec/downloads/pdf/green_building/MasterFormat%202011%20Numbers%20and%20Titles.pdf; BuildSite https://www.buildsite.com/masterformat/applied-fireproofing-078100):
  - **07 81 00 Applied Fireproofing** (parent)
  - **07 81 13 Cement Aggregate Fireproofing**
  - **07 81 16 Cementitious Fireproofing**
  - **07 81 23 Intumescent Fireproofing**
  - (07 82 00 Board Fireproofing; 07 84 00 Firestopping are siblings — not structural fireproofing.)
- Public examples: NIH MasterSpec-based 078100 (https://orf.od.nih.gov/TechnicalResources/Documents/Fire%20Protection%20-%20Specifications/078100%E2%80%93AppliedFireproofing_508.pdf), UFGS 07 81 00 (https://nibs-s3-wbdg3-production.s3.us-east-1.amazonaws.com/FFC/DOD/UFGS/UFGS%2007%2081%2000.pdf), BART 07 81 16 (https://webapps.bart.gov/bfs/BFS_3_1_Spec/STDSPEC/07%2081%2016.pdf), UCSF 07 81 16 (https://realestate.ucsf.edu/sites/g/files/tkssra17111/files/07%2081%2016%20%20UCSF%20MC%20Master%20220103.pdf), UTA 07 81 23 (https://cdn.prod.web.uta.edu/-/media/project/website/campus-ops/facilities/files/dsgn_spec_guidelines/division_07/uta-07-81-23-intumescent-mastic-fireproofing.pdf), Isolatek guide spec 078120 for SprayFilm (https://isolatek.com/wp-content/uploads/2019/10/CAFCO-SprayFilm-Exterior-Spec-10-2019.doc).
- **Typical submittal list** enumerated across these specs (likely): product data and application instructions; evaluation/listing reports (UL design pages, ICC-ES/UL ER); a **fireproofing schedule** showing, for each member/assembly, the UL design, rating, restraint condition, concrete type, W/D or A/P, and minimum thickness/DFT; structural framing plans marked with extent of each rating and surface-prep type; applicator qualifications and manufacturer certification; material certificates (density, bond, E759/E760/E761/E859 results); field QC/special-inspection test reports; patching procedure; primer compatibility letters; mock-ups/samples for intumescents; warranty. UFGS tags these as SD-02 (drawings), SD-03 (product data), SD-06 (test reports), SD-07 (certificates) (likely — UFGS excerpt; University of Houston master spec https://www.uh.edu/facilities-services/departments/fpc/master-specs/07-81-00-applied-fireproofing.pdf).
- A UFGS excerpt also states a minimum applied thickness of 3/8 in regardless of design (likely — verify in current UFGS).

**Data-model implication.** `SpecSection` with `masterformat_number`, `edition`, required submittal items (checklist), density class, bond strength requirement, inspection frequency overrides, and approved manufacturers list. The fireproofing schedule the spec demands is the same object the shop-drawing module must generate.

---

## 7. Architectural exposure: SFRM vs intumescent, AESS

- Rule of thumb in the trade: SFRM on concealed steel (above ceilings, inside shafts/walls); intumescent on exposed/architecturally expressed steel; epoxy intumescent where hydrocarbon (UL 1709) or exterior durability (UL 2431 categories) governs (likely — https://bahlfireproofing.com/cementitious-vs-intumescent-fireproofing/; https://www.andrexltd.com/resources/sfrm-vs-intumescent/).
- **AESS categories** (AISC Code of Standard Practice §10, since the 2016 edition): AESS 1 basic elements; AESS 2 feature elements viewed from > 20 ft; AESS 3 feature elements viewed from ≤ 20 ft; AESS 4 showcase elements; AESS C custom (likely — https://www.aisc.org/media/hjsjprbr/gc_toolboxtalk9_2025.pdf; https://www.aia.org/article/right-way-specify-architecturally-exposed-structural-steel). Higher categories imply smoother finish expectations, which drives intumescent selection, number of coats, sanding, and topcoat scope; S-W argues for an explicit finish standard for intumescents on AESS (likely — S-W article above).
- **Drawing inputs that decide exposure** (guessing, synthesised from the above and general practice): structural framing plans (member sizes), architectural RCPs and ceiling types (hard lid vs ACT vs open), finish schedules and wall sections (which beams land inside rated walls → membrane protection), AESS designations on structural general notes/plans, exterior elevations (exposed canopies, exterior columns → exterior-rated product), and mechanical/shaft layouts (concealed but requires continuity).

**Data-model implication.** Per member: `exposure` ∈ {concealed, exposed-interior, exposed-exterior, within-rated-wall, within-shaft}, `aess_category`, `finish_requirement`, `product_system_override`.

---

## 8. Shop drawing / spray chart conventions

- Little formal public guidance exists; conventions are visible mostly through estimating-software marketing and permit guides (likely):
  - **Spray charts ("color-ups")**: structural framing plans with members colour-coded by required thickness, plus a legend mapping colour → thickness (and product/design); produced for field crews (likely — The EDGE fireproofing page https://estimatingedge.com/construction/fireproofing/ and brochure https://www.estimatingedge.com/wp-content/uploads/2022/11/LIT-Trade-Fireproofing-WEB_0522-1.pdf).
  - **Fireproofing schedule/plan for permit** (Clark County BPG-053): framing backgrounds at ≥ 1/8" = 1'-0" noting each member's thickness or rating, e.g., `W8x10 (5/8")`; a schedule listing UL design numbers, W/D and/or A/P, restraint condition, hourly rating, concrete type, minimum thickness; code analysis by the Architect of Record; sheets stamped by the design professional (likely).
  - **UFGS/MasterSpec shop drawings**: framing plans showing extent of SFRM for each rating, surface-prep types, and minimum thickness per component (likely).
- Sheet numbering: no trade-wide standard found; fireproofing shop drawings typically reuse the structural sheet numbering with a prefix/suffix (e.g., "FP-" or "S-xxx FP") — (guessing). Legend conventions beyond colour-by-thickness: `UNKNOWN — not public`.

**Data-model implication.** A `SprayChart` = {plan background ref, member → (product, design, rating, thickness/DFT, exposure, mesh/primer flags), colour legend, revision, stamp}. Generate the permit schedule and the spray chart from the same member table.

---

## 9. Terminology glossary

- **SFRM** — Sprayed Fire-Resistive Material (cementitious or mineral-fibre, wet- or dry-mix). **IFRM** — Intumescent Fire-Resistive Material (thin-film or epoxy). **MFRM** — mastic FRM (IBC 704.14 term).
- **CAFCO** — Isolatek's commercial brand family (CAFCO 300, BLAZE-SHIELD, FENDOLITE, SprayFilm); **ISOLATEK Type ...** is the dual-branded equivalent (likely).
- **MONOKOTE** — GCP/Saint-Gobain SFRM brand (MK-6/HY, Z-106, Z-146, Z-156).
- **Intumescent** — coating that swells into an insulating char when heated.
- **DFT / WFT** — dry / wet film thickness (mils or µm); **volume solids** links them.
- **W/D** — weight per foot ÷ heated perimeter (I-shapes); **A/P** — area ÷ heated perimeter (HSS/pipe); **M/D** metric equivalent.
- **Heated perimeter** — steel surface exposed to fire; 3-sided for slab-supported beams, 4-sided for columns.
- **Contour vs box** — protection profile following the section vs spanning flange tips.
- **Restrained / unrestrained** — thermal-expansion restraint condition in the E119/UL 263 test; drives which rating column applies; assigned by the EOR.
- **Assembly rating vs beam rating** — rating of a whole floor/roof assembly vs rating of the beam alone (UL "unrestrained beam rating"); **hourly rating** — the required/achieved duration (¾, 1, 1½, 2, 3, 4 h).
- **Listed design** — a UL/Intertek design number describing a tested assembly; **listing** — the manufacturer's certification file (e.g., UL category CHPX for SFRM products, excerpt: CHPX.R13348 Isolatek).
- **Primary structural frame / secondary member** — IBC 202 definitions (Section 1.3).
- **Individual encasement vs membrane protection** — protecting each member on all sides vs relying on a rated ceiling/wall membrane (IBC 704).
- **Bond strength** — cohesion/adhesion per ASTM E736 (psf). **Density** — in-place dry density (pcf) per ASTM E605.
- **Board foot (bd ft)** — 1 ft² at 1 in thick; the SFRM yield unit.
- **Yield** — bd ft per bag (SFRM) or ft²/gal at 1 mil (coatings).
- **Special inspection** — IBC Chapter 17 third-party inspection (1705.15/1705.16).
- **AESS** — Architecturally Exposed Structural Steel (AISC CoSP categories 1–4, C).
- **AHJ** — Authority Having Jurisdiction. **EOR** — Engineer of Record. **EJ** — Engineering Judgement (manufacturer/engineer letter for conditions not covered by a listing; examples in Portland BDS appeals files, e.g., https://www.portlandoregon.gov/bds/appeals/index.cfm?action=getfile&appeal_id=18146&file_id=21814).
- **XR design** — UL 1709 hydrocarbon design prefix. **BXUV / BXUV7** — UL fire-resistance design categories (US / Canada).

---

## 10. Authoritative data sources by hierarchy

| Rank | Source | Access mechanism | Structured ingestion permitted? |
|---|---|---|---|
| 1 | Adopted building code (IBC edition as adopted; NYC/Chicago codes) | ICC codes.iccsafe.org (free read-only tier, paid premium); state/city sites; up.codes (freemium) | ICC content is copyrighted; free tier is read-only; no bulk right — store references and user-entered values (likely) |
| 2 | State/local amendments | Jurisdiction websites, amlegal/municode mirrors | Public-record text, usually reusable; still verify per jurisdiction (likely) |
| 3 | Project code analysis sheet | Project drawings (PDF/DWG/BIM) from GC/architect | Project-licensed; internal use (certain) |
| 4 | Referenced standards (ASTM E119/E605/E736..., UL 263/1709/2431, AWCI 12-A/12-B, AISC DG19) | Paid PDFs (ASTM, UL Standards, AWCI/ICC shop, AISC) | Copyrighted; no redistribution; encode only the *parameters the team itself derives* with citations (likely) |
| 5 | Current UL / Intertek listing | UL Product iQ (free with registration, no public API); Intertek directory (free web); manufacturer-hosted design PDFs | UL terms prohibit automated/systematic retrieval and bulk aggregation; user-uploaded PDFs plus manual entry with snapshot date; Intertek terms `UNKNOWN — verify` (likely) |
| 6 | Manufacturer documents (TDS/PDS, yield charts, thickness charts, application manuals) | Public web PDFs (isolatek.com, gcpat.com, msds.carboline.com, paintdocs.com, hilti.com); no APIs found | Generally public but copyrighted; capture values with document revision date and URL; confirm redistribution policy per manufacturer (likely) |
| 7 | Project specifications (07 81 xx) | Project documents | Project-licensed (certain) |
| 8 | Drawings (structural, architectural, AESS notes) | Project documents (PDF/DWG/IFC) | Project-licensed (certain) |
| 9 | RFIs, addenda, engineering judgements | Project correspondence | Project-licensed; supersede earlier items by date (certain) |
| 10 | Historical company data (field yields, waste, productivity) | Internal | Internal (certain) |

---

## 11. Open domain questions for an experienced fireproofing estimator

1. For a beam framed into a slab on metal deck, which exact surfaces do you include in the ft²/lf factor — do you deduct the top flange entirely, and how do you treat the deck flutes above the top flange on a 3-sided box application?
2. When a UL design gives thickness by W/D bands, do you interpolate between bands, round to the next band, or use the published equation — and does your answer change between SFRM and intumescent designs?
3. How do you decide restrained vs unrestrained when the structural drawings are silent? Do you default to the unrestrained column and then ask for a letter from the EOR?
4. What waste/overspray percentage do you carry by product type (wet-mix commercial density, dry-mix fibre, high density, thin-film intumescent, epoxy), by application (deck vs beams vs columns) and by thickness, and how often is it recalibrated against bags consumed?
5. What target in-place density do you plan to (versus the listed minimum), and how does that change the bd ft/bag you use?
6. Which design conditions most often add cost that the takeoff misses: mesh on wide flanges, bonding agent on primed steel, sealer on exterior, lath at deck-to-beam junctions, pins on dense products?
7. How do you handle primed or shop-painted steel — do you assume a bond test will pass, carry a bonding agent allowance, or price both?
8. For columns, do you fireproof to the underside of deck, to the slab top, or to the top of the base plate — and how do you treat connections, gusset plates, stiffeners and bolted splices in area?
9. How do you take off miscellaneous steel (kickers, braces, angles, channels, WTs, built-up members) and what design do you assign when there is no listed design for that shape?
10. For HSS columns, which perimeter (A/P) and which X-series design do you use, and does the architect's fill (concrete-filled vs hollow) change the design?
11. Which members do you exclude from scope by rule (lintels ≤ 6'-4", roof-only members above 20 ft, 0-hour construction types, members inside rated walls) and how do you document those exclusions for the inspector?
12. What minimum thickness do you apply regardless of design (e.g., the 3/8 in rule in some specs), and when the spec and the design disagree, which wins in your bid?
13. For intumescents, how many coats and what per-coat DFT do you assume per product, and how do you price sanding, primer, topcoat, and AESS finish levels?
14. Do you price shop-applied intumescent differently (touch-up, field splices) and who owns the thickness verification at the shop?
15. What inspection regime do you assume in your QC budget (IBC 1705.15 sampling vs AWCI 12-A vs the spec's own frequency) and which one does the special inspector actually follow in your market?
16. How do you reconcile the "exposed vs concealed" call when RCPs change after bid — what triggers a change order?
17. What does your spray chart show that your estimate does not (patching zones, no-spray zones, phased areas, deck types)?
18. Which manufacturers' consolidated thickness charts (GCP "All UL thickness chart", Isolatek thickness charts) do you trust versus going to Product iQ, and how do you track when a design is revised mid-project?
19. How do you handle roof decks (P-series) differently from floor decks (D-series) in area factors and in yield?
20. What historical productivity (ft² or bd ft per crew-day) do you track, and by what breakdown (deck vs beams vs columns vs misc, lift height, mesh)?

---

## Summary of what remains unverified

- All page content; nothing was read directly. Every number above is from a search-index excerpt.
- UL BXUV Guide Information: full prefix list and the meaning of the first digit (700/800/900 series), interpolation rules, exact substitution wording.
- UL design X790 equation coefficients and the HSS A/P/thickness equation (reported from excerpts of mirrored PDFs).
- IBC 704 subsection numbering per edition (2015/2018/2021/2024) and the 2024 Table 601 footnote wording.
- Bag weights/yields for BLAZE-SHIELD II, CAFCO 400, FENDOLITE, Z-146/Z-156, MK-6/HY current PDS; pail sizes for FX5120/FX6002, Steelguard 951, Interchar 1120, Hilti CFP-SP WB.
- AISC DG19 authorship; AWCI 12-A current edition number (ICC lists a 4th edition); E605 per-member reading counts.
- Intertek directory terms of use; any FM approval class applicable to structural SFRM/IFRM.
- Corporate relationships: Isolatek–Promat/Etex; Carboline–Southwest Fireproofing acquisition history.
