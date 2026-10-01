# B. Competitive Workflow Matrix — Construction Takeoff / Estimating / Drawing / PM Software

**Purpose.** Understand the workflows experienced estimators already know, so a structural-steel fireproofing takeoff + shop-drawing platform feels familiar on day one. This is a *functional* survey and lessons list. It does not clone any UI, proprietary data, or code, and it assigns no numeric scores or rankings.

**Method and limits (read first).** Research date 2026-10-01. The sandbox's egress proxy blocked direct fetches of nearly every vendor and review domain (estimatingedge.com, buzzbid.com, procore.com/support/developers, planswift.com, bluebeam.com, stackct.com, togal.ai, oncenter.com, help.constructconnect.com, support.tekla.com, capterra.com, g2.com, softwareadvice.com, selecthub.com, forums.autodesk.com). Reachable: github.com (Procore's public API documentation repository) and sourceforge.net. Everything else below comes from **web-search result snippets of those vendor/help/review pages**, cited by URL. Treat snippet-derived claims as "(certain)" only when the snippet was from the vendor's own page and the wording was unambiguous; otherwise "(likely)". Nothing was invented; where a dimension could not be established it says **not determined from public sources**.

Confidence tags: **(certain)** vendor docs/official pages; **(likely)** reviews, resellers, secondary sources; **(guessing)** inference.

---

## 1. Product profiles

### 1.1 The EDGE (Estimating Edge) — the fireproofing incumbent

The EDGE is the one mainstream estimating package with a dedicated fireproofing trade module ("The EDGE Estimator for Fireproofing"), marketed for cementitious, fiber and intumescent fireproofing (certain) [https://estimatingedge.com/construction/fireproofing/]. Isolatek's own "Estimating Center" page points contractors at The EDGE, which signals how embedded it is in the manufacturer ecosystem (likely) [https://www.isolatek.com/construction/commercial-support/estimating-center/].

| Dimension | Finding |
|---|---|
| Plan ingestion | PDF/image plans loaded into a job; a "New Job" / "File New" / template workflow exists in the v12 knowledgebase (certain) [https://www.estimatingedge.com/knowledgebase/6515/], [https://estimatingedge.com/knowledgebase/new-template/]. Formats beyond PDF: not determined from public sources. |
| Scale handling | Set scale either by picking a pre-defined scale from a dropdown or by calculating from a known dimension by clicking the two endpoints of the largest known line on the drawing (certain) [https://estimatingedge.com/knowledgebase/setting-scale/]. Multi-scale per sheet / viewport scale: not determined from public sources. |
| Takeoff interactions | Condition-based takeoff on the "Condition Screen"; linear/area/count digitizing of steel members by shape (certain) [https://estimatingedge.com/knowledgebase/5996/]. Users praise "the versatility of creating different conditions, the ability to quickly add conditions, and the accuracy of the calculations" (likely, Capterra) [https://www.capterra.com/p/8668/The-EDGE/reviews/]. |
| Automation / AI | Auto-count/OCR/auto-naming for The EDGE: not determined from public sources (searches returned nothing specific). |
| Conditions | Central object. "Project Conditions" (v12) lets you "set up a condition once and use it anywhere inside of the section"; "Common Conditions" let an estimator "define a portion of a takeoff on a page and save that area to reuse on other pages, with takeoff from multiple conditions able to be included"; a "Map Conditions" function exists (certain) [https://estimatingedge.com/knowledgebase/database-descriptions/], [https://estimatingedge.com/knowledgebase/map-conditions/]. |
| Assemblies | Conditions carry labor + material + misc items; the "Condition Detail" report "prints each condition with quantities, order units, unit prices and extended prices … a detail printout of all labor material and miscellaneous items for each condition" (certain) [https://www.estimatingedge.com/knowledgebase/standard-reports-definitions/]. |
| Databases | "Customizable fireproofing database with manufacturer-specific products for W.R. Grace, Isolatek, Carboline and others with their related UL Designs and thickness"; AISC steel shapes "in both imperial and metric, with W/D and heated perimeters" (certain) [https://estimatingedge.com/construction/fireproofing/], [https://www.estimatingedge.com/wp-content/uploads/2022/11/LIT-Trade-Fireproofing-WEB_0522-1.pdf]. Reviewers: "the database that comes with it is robust and has multiple manufacturers included from day one" but "the back end/database portion could be more user friendly and less 'coding'" (likely) [https://www.capterra.com/p/8668/The-EDGE/reviews/]. |
| Fireproofing specialization | Yes — the reference implementation. Steel takeoff by shape → UL design → auto thickness → board feet → bags; spray charts; shop drawings (certain) [https://estimatingedge.com/construction/fireproofing/]. |
| UL design handling | "Fire Test and steel shape databases containing UL designs and formulas that auto-assign thicknesses" (certain) [https://www.estimatingedge.com/wp-content/uploads/2022/11/LIT-Trade-Fireproofing-WEB_0522-1.pdf]. |
| Thickness handling | Auto-assigned from UL design + shape W/D; then a **Fireproofing Adjustments** screen lets the estimator "make adjustments to the fireproofing material thicknesses on a shape by shape basis. All of the estimated shapes are displayed … along with a Thickness, Board Foot and Adjusted Board foot columns … enter your adjusted thickness … you will see the BF and Adj BF columns display the adjusted amounts" (certain) [http://www.estimatingedge.com/knowledgebase/fireproofing-adjustments/]. |
| Estimating | Labor screen with production per manday/manhour; "Labor Adjustments – Time" report; Recap "summarizes the job and shows appropriate taxes and markups. It is the report you will base your bid on" (certain) [https://www.estimatingedge.com/knowledgebase/standard-reports-definitions/], [https://estimatingedge.com/knowledgebase/labor-screen/]. Alternates/WBS: scenarios exist per section (multiple estimators can check out a section, only one a scenario) (likely) [https://www.estimatingedge.com/knowledgebase/collaboration-webinar/]. |
| Revision handling | Overlay/compare for addenda: not determined from public sources. |
| Reports | Recap, Condition Detail, Stocking (material list for stocking), Labor Adjustments, special fireproofing report "showing original thickness and adjusted thickness, as well as the original board feet and the adjusted board feet"; exports to Excel ("Download as Excel" from Recap) (certain) [https://www.estimatingedge.com/knowledgebase/standard-reports-definitions/], [https://estimatingedge.com/knowledgebase/exporting-reports/]. |
| Shop drawings | "Generate shop drawings quickly … by color-coding your blueprints by steel type, UL design, Hourly Rating, and thickness" (certain) [https://estimatingedge.com/construction/fireproofing/]. User-reported: "Fireproofing Shop Drawings as printed out directly from the Edge are a bit messy, and users need to use a PDF editor to edit and clean them up" (likely) [https://www.capterra.com/p/8668/The-EDGE/reviews/]. |
| Spray charts | "Spray Charts (or color ups) of your blueprints with lines color-coded by thickness to be sprayed, and a legend for what thickness each color represents" (certain) [https://estimatingedge.com/construction/fireproofing/]. |
| Submittals | Not a submittal-management tool; shop drawings are printed/PDF'd and handled outside (guessing, based on the review above). |
| Field use | "EDGE On Site" iPad app (2018) uploads foreman production progress to a cloud portal (certain) [https://estimatingedge.com/release-edge-on-site/]. |
| Collaboration | Cloud-stored jobs; "multiple estimators can work on the same project at the same time in different sections … each estimator can check out a section" (certain) [https://www.estimatingedge.com/knowledgebase/collaboration-webinar/]. |
| Auditability | Shape-by-shape thickness/BF table and Condition Detail report give per-condition, per-shape traceability (certain, as above). Per-sheet drill-down from a number back to the drawing: not determined from public sources. |
| Integrations | Excel export; accounting integration listed on SourceForge (likely) [https://sourceforge.net/software/product/The-EDGE/]. Public API: not determined from public sources. |
| Strengths | Only product with full steel-shape→UL→thickness→BF→spray chart→shop drawing chain; strong manufacturer databases; strong support ("technical support is second to no one") (likely) [https://www.capterra.com/p/8668/The-EDGE/reviews/]. |
| Limitations (user-reported) | Overwhelming feature set / learning curve; "frequent crashes" and crashes "when working abroad, due to language or regional configuration"; "many fine tuning has to happen … users still adjust hours in the summary"; database back end feels like coding; messy shop drawing output; resentment at move from perpetual to subscription licensing (likely) [https://www.selecthub.com/p/construction-estimating-software/the-estimating-edge/], [https://www.capterra.com/p/8668/The-EDGE/reviews/]. |

### 1.2 BuzzBID (incl. FireShield edition)

Cloud-native takeoff+estimating for interior/specialty trades (drywall, framing, ACT, fireproofing, plaster/EIFS, insulation, paint) with published pricing (certain) [https://buzzbid.com/pricing].

| Dimension | Finding |
|---|---|
| Plan ingestion | Cloud plan management bundled in one app (certain) [https://buzzbid.com/]. Formats: not determined from public sources. |
| Scale handling | Not determined from public sources. |
| Takeoff interactions | "ClickONCE" computer vision: single-click / double-click actions "detect and measure walls, ceiling tiles, door assemblies, corner bead, and trim"; manual on-screen tools also present with "easy visual verification" (certain) [https://buzzbid.com/articles/buzzbid-vs-on-screen-takeoff-quickbid], [https://softwarefinder.com/construction/buzzbid]. |
| Automation / AI | ClickONCE symbol/fixture counting and "structural member detection" (FireShield) (certain) [https://buzzbid.com/pricing]. |
| Conditions / Assemblies | "Assembly quantities are available in your Estimate page" because takeoff and estimate share one database (certain) [https://buzzbid.com/fireproofing]. (SourceForge's generic feature grid marks "assembly takeoff" unsupported — a listing artifact that contradicts the vendor; treat as unreliable (likely) [https://sourceforge.net/software/product/BuzzBID/].) |
| Databases | Single integrated database; UL Fire Test integration in FireShield (certain) [https://buzzbid.com/pricing]. Manufacturer coverage: not determined from public sources. |
| Fireproofing specialization | FireShield tier: "UL Fire Test integration, ClickONCE structural member detection, board foot calculations, calculated heated perimeter and flute fill, shop drawings optimization, and the inspector spray report" for cementitious, intumescent and spray foam (certain) [https://buzzbid.com/pricing], [https://buzzbid.com/fireproofing]. "Instantly take off primaries and secondaries … including calculating Heated Perimeter and Material Count" (certain) [https://buzzbid.com/fireproofing]. |
| UL design / Thickness | UL fire-test integration drives thickness; "Shop Drawings Optimization will instantly optimize spray thicknesses for field crews" while "the Inspector Spray Report maintains the detailed accuracy reflecting every estimated thickness" (certain) [https://buzzbid.com/fireproofing]. Flute fill is computed (certain) [https://buzzbid.com/pricing]. |
| Estimating | Pricing and assembly-based estimating in the same app; "work tracking" (certain) [https://softwarefinder.com/construction/buzzbid]. Labor/WBS/alternates detail: not determined from public sources. |
| Revision handling | Not determined from public sources. |
| Reports / Spray charts | Two spray reports: "As Estimated" for inspectors and "Optimized" for crew (certain) [https://buzzbid.com/fireproofing]. |
| Shop drawings | "Shop drawings optimization" (thickness-rounded crew version) (certain) [https://buzzbid.com/pricing]. |
| Submittals | Not determined from public sources. |
| Field use / Collaboration | Cloud-based; otherwise not determined from public sources. |
| Auditability | Visual verification of ClickONCE results is emphasized (certain) [https://softwarefinder.com/construction/buzzbid]. |
| Integrations | Not determined from public sources (Excel export not confirmed). |
| Strengths | Explicit two-audience spray-report model (inspector vs crew); computer-vision member detection; flat published pricing; integrated takeoff→estimate. |
| Limitations | Few independent reviews exist (SourceForge/Capterra show none) (likely) [https://sourceforge.net/software/product/BuzzBID/]. Narrow trade focus. |

### 1.3 PlanSwift (ConstructConnect)

| Dimension | Finding |
|---|---|
| Plan ingestion | PDF and raster; "limited document compatibility" is a user-reported con (likely) [https://www.planswift.com/features/], [https://www.capterra.com/p/70808/PlanSwift/]. |
| Scale handling | One scale per page: "PlanSwift supports one Scale per Page … you simply have to create a copy of the Page (or region of the Page) to account for different Scales" via Crop Region or Duplicate Page; separate horizontal/vertical scales supported; Auto Scale exists but warns when applying to all pages and requires DPI info (certain) [https://help.constructconnect.com/14-advanced-plans-and-takeoff-tools-and-printing-187/planswift-14-03-01-handling-more-than-one-scale-on-the-same-plan-1783], [https://help.constructconnect.com/14-advanced-plans-and-takeoff-tools-and-printing-187/planswift-14-03-calculating-scale-and-handling-different-horizontal-and-vertical-scales-on-the-same-plan-1757]. |
| Takeoff interactions | Point-and-click linear/area/count; "drag and drop individual parts or assemblies directly onto a digitized blueprint"; New Count tool with properties window (certain) [https://www.planswift.com/features/]. |
| Automation / AI | Takeoff Boost suite: Auto Takeoff, Auto Count, Auto Scale, Auto Bookmark ("links plan sheets to related detail sheets") (certain) [https://www.planswift.com/features/]. |
| Conditions / Assemblies | Items + "Lists and parts libraries"; assembly-based estimating "lets you apply material and labor assemblies as you measure so costs update with the takeoff" (certain) [https://www.planswift.com/features/]. |
| Databases | User-built lists/parts; Import-from-Excel plugin creates items from a spreadsheet (certain) [https://constructconnect-help.atlassian.net/wiki/spaces/PSUPPORT/pages/34244768/PlanSwift+Import+from+Excel+Tool+Plugin+User+Guide]. No fireproofing/UL content. |
| Fireproofing / UL / Thickness | None. |
| Estimating | Material + labor assemblies, bill of materials, customizable templates (certain) [https://www.planswift.com/features/]. |
| Revision handling | Overlay tab places another page over the current one; users say overlays help review addenda, though "some users experience … difficulties with the overlay feature" (likely) [https://www.softwareadvice.com/construction/planswift-takeoff-estimating-profile/reviews/]. |
| Reports / Integrations | Excel export (incl. "Export to Excel by Page" plugin) and accounting integration (certain) [https://constructconnect-help.atlassian.net/wiki/spaces/PSUPPORT/pages/34244745/Export+to+Excel+(by+Page)+Plugin]. |
| Shop drawings / Spray charts / Submittals | None. |
| Field use | Desktop Windows only (likely) [https://www.capterra.com/p/70808/PlanSwift/]. |
| Collaboration | Not determined from public sources (desktop file-based). |
| Auditability | Items organized per page; per-page Excel export supports sheet-level audit (certain, above). |
| Strengths | Speed and flexibility for high-volume takeoff; "nothing better for high volume takeoffs" per some reviewers; multiple page tabs (likely) [https://www.softwareadvice.com/construction/planswift-takeoff-estimating-profile/reviews/]. |
| Limitations (user-reported) | "steep learning curve, limited document compatibility, occasional software glitches or licensing issues, and customer support gaps"; slow loading (likely) [https://www.capterra.com/p/70808/PlanSwift/]. |

### 1.4 Procore (focus: precon → operations handoff, submittals, drawings, API)

| Dimension | Finding |
|---|---|
| Plan ingestion | Drawings tool accepts PDF only: "All files uploaded to the Procore Drawings tool must in PDF format" (certain) [https://github.com/procore/documentation/blob/main/tutorials/tutorial_drawings.md]. OCR "automatically detect[s] the name, number, and discipline of each set while splitting sheets" (certain) [https://www.prnewswire.com/news-releases/procore-unveils-industry-leading-drawing-management-solution-300086125.html]. |
| Scale / Takeoff | Procore Estimating (ex-Esticom) does cloud takeoff where "quantities measured on-screen flow directly into the estimate" (likely) [https://buildern.com/resources/blog/procore-estimating/]. Scale/multi-scale details: not determined from public sources. |
| Automation / AI | OCR sheet naming; "Automatic Drawing Sheet Linking" scans callouts and links details to related drawings (certain) [https://support.procore.com/products/online/user-guide/project-level/drawings/tutorials/automatic-drawing-sheet-linking]. AI Submittal Builder "draft[s] a robust list of submittals while also predicting each submittal type and title" from selected spec sections (certain) [https://v2.support.procore.com/product-manuals/specifications-project/tutorials/submittal-builder-with-ai-generate-submittals-from-specifications]. |
| Conditions / Assemblies / Databases | Estimating module has material/labor/equipment cost databases (likely) [https://buildern.com/resources/blog/procore-estimating/]. No fireproofing/UL content. |
| Revision handling | Re-uploading a sheet with the same number stacks it as the next revision; markups carry forward; overlay compare shows additions in blue / deletions in red; "Compare Set" runs bulk comparison of a whole set (likely) [https://www.followupcrm.com/blog/how-to-overlay-drawings-in-procore], [https://evolvemep.com/blog/procore-tips-uncovering-procore-drawing-comparisons-and-bulk-overlay]. API: Drawing Areas, Drawing Sets, Drawing Uploads, Drawing Revisions (filter `current`), Drawing Tiles (certain) [https://github.com/procore/documentation/blob/main/tutorials/tutorial_drawings.md]. |
| Submittals | Create → spec section → Submittal Manager → sequential/parallel workflow steps with approvers → ball-in-court → responses; "Enable Reject Workflows" routes BIC back to the Submittal Manager on "Rejected"/"Revise and Resubmit", who "can close the submittal and create a revision"; workflow templates define submitters/approvers (certain) [https://v2.support.procore.com/product-manuals/submittals-project/tutorials/create-a-submittal/], [https://v2.support.procore.com/product-manuals/submittals-project/tutorials/manage-submittal-workflow-templates]. |
| Precon → ops handoff | "turning won proposals into prime contracts and field-ready project budgets … Awarded bid data, subcontractor contacts, and pricing transfer directly into Procore's Commitments and Financials modules" (certain, vendor) [https://www.procore.com/preconstruction]. |
| Field use | Full mobile apps (general knowledge; vendor) (likely). |
| Integrations / API | **Submittals:** `POST /rest/v1.1/projects/{project_id}/submittals` with required `submittal.number`, optional `revision`, `status_id`, `submit_by`, and `prostore_file_ids` "array of Prostore File IDs, which will be associated with the Submittal as attachments" (likely, third-party mirror of the reference) [https://www.simworkflow.com/integration-operation/procore-rest-v1-1-projects-project_id-submittals-post-d3d]; v2 `GET /rest/v2.0/companies/{company_id}/projects/{project_id}/submittals` returns richer workflow-step/approver data; status IDs are company-specific (likely) [https://github.com/khrnchn/procore-skills/blob/main/skills/procore-api/references/submittals.md]. **Drawings:** direct-upload tutorial: list drawing areas → create placeholder drawing (`drawing:number`, `drawing_discipline:name`) → create project upload (presigned URL + UUID) → create drawing upload with `drawing_log_imports[{drawing_date, upload_uuid, drawing_id}]`; supplying `drawing_id` means "it will automatically be assigned to the given Drawing without a manual review" (certain) [https://github.com/procore/documentation/blob/main/tutorials/tutorial_direct_drawing_uploads.md]. **Documents:** folders/files endpoints; recursive walking "can burn through Procore's API quota quickly" (3,600 req/hr) (certain) [https://github.com/procore/documentation/blob/main/tutorials/tutorial_documents.md]. **Uploads:** two-step direct upload (`POST /rest/v1.1/projects/{project_id}/uploads` → PUT to storage → associate by `upload_id`/UUID); segmented uploads for large files; multipart is legacy (certain) [https://github.com/procore/documentation/blob/main/tutorials/tutorial_uploads.md], [https://github.com/procore/documentation/blob/main/tutorials/attachments.md]. **Document Management (new DM tool):** revisions grouped in containers, `version` field, webhooks `created/updated/recycled`, ID-only polling pattern (certain) [https://github.com/procore/documentation/blob/main/document_management_integration/document_management_document_revisions.md]. **Webhooks** for create/update/delete on supported resources (certain) [https://procore.github.io/documentation/webhooks]. **Conclusion:** yes, the public API supports pushing a shop drawing as a Drawing revision, as a Document, and as a Submittal attachment — but the exact v1.1 submittal attachment field could not be verified against developers.procore.com (blocked). |
| Strengths | Industry-standard home for drawings/submittals; OCR + auto-linking; mature API and marketplace (STACK, Bluebeam, Drawboard all sync drawings) (likely) [https://www.stackct.com/blog/4-things-to-know-about-the-stack-procore-integration/], [https://www.drawboard.com/integrations/procore]. |
| Limitations (user-reported) | Procore is "built for large general contractors"; subs are usually guests in the GC's instance (likely) [https://buildern.com/resources/blog/procore-estimating/]. Auto sheet links can be missing (certain, FAQ exists) [https://support.procore.com/faq/why-are-automatic-drawing-sheet-links-missing]. |

### 1.5 Bluebeam Revu

- **Plan ingestion:** PDF-native; Sets stitch many files into one navigable document; AutoMark builds bookmarks/page labels; Batch Link auto-hyperlinks callouts across a set (certain) [https://support.bluebeam.com/user-manual/menus/document/overlay-pages.html], [https://www.brightergraphics.com/bluebeam-revu-workflows].
- **Scale:** Calibrate to one scale or separate X/Y; **Viewports** assign different scales to regions of the same page (certain) [https://blog.bluebeam.com/revu-20-dot-2-measurement-tools-quantity-takeoffs/], [https://novedge.com/blogs/design-news/bluebeam-tip-viewport-based-scaling-for-accurate-takeoffs]. Scale templates can be standardized (likely) [https://novedge.com/blogs/design-news/bluebeam-tip-standardize-calibration-with-scale-templates-in-bluebeam-revu].
- **Takeoff:** length/area/perimeter/count/volume; Dynamic Fill for irregular rooms; Count tool + **VisualSearch** to find a symbol across the set (certain) [https://blog.bluebeam.com/maini-qto-revu/], [https://novedge.com/blogs/design-news/bluebeam-tip-maximize-measurement-efficiency-with-bluebeam-revus-dynamic-fill-tool].
- **Conditions / assemblies:** none natively; Tool Chest tool sets + Custom Columns (Cost Code, Unit Rate, Waste %, Formula) approximate them; **Legend** tool auto-summarizes placed markups (certain) [https://support.bluebeam.com/online-help/revu20/Content/RevuHelp/Tutorials/Custom-Columns-for-Takeoffs.htm], [https://novedge.com/blogs/design-news/bluebeam-tip-create-dynamic-legends-to-auto-count-and-summarize-markups-in-bluebeam-revu]. A reseller states plainly: "no conditions library and no assembly logic" (likely) [https://builderbuzz.com/bluebeam-review].
- **Revisions:** Overlay Pages (color-stacked layers) and Compare Documents (differences become reviewable markups), both batchable (certain) [https://support.bluebeam.com/online-help/revu20/Content/RevuHelp/Menus/Batch/Overlay/Batch-Overlay.htm], [https://support.bluebeam.com/user-manual/menus/document/compare-documents.html].
- **Auditability:** Markups List filterable by Page/Author/Status/date; CSV/XML/PDF Summary; every quantity is a markup on a page (certain) [https://support.bluebeam.com/online-help/revu21/Content/RevuHelp/Menus/Window/Panels/Markups/Markups-List--MTV.htm].
- **Integrations:** Quantity Link pushes live measurement values into Excel cells; "custom columns cannot be linked using Quantity Link" (certain) [https://blog.bluebeam.com/benefits-quantity-link-revu/], [https://support.bluebeam.com/revu/how-to/enable-quantity-link.html].
- **Collaboration / field:** Studio Sessions (live multi-user markup) and Projects; iPad app (certain) [https://sourceforge.net/software/product/Bluebeam-Revu/].
- **Fireproofing / UL / thickness / spray charts / shop drawings:** none natively, but Revu is what estimators use to *clean up* The EDGE's shop drawings (likely, per EDGE review above). Steel takeoff needs external shape weights (likely) [https://bidferra.com/knowledge-base/can-you-do-a-steel-takeoff-in-bluebeam].
- **Limitations (user-reported):** "laggy and hangs from time to time, according to 62% of users"; dense interface; large files crash; Revu 21 subscription shift (likely) [https://selecthub.com/p/takeoff-software/bluebeam-revu], [https://www.capterra.com/p/121586/Bluebeam-PDF-Revu/reviews/].

### 1.6 On-Screen Takeoff / Quick Bid / ConstructConnect Takeoff

- **Conditions** are the unit of work; patented **Multi-Condition Takeoff** measures several conditions in one pass; **Typical Groups** reuse repeated areas (certain) [https://www.constructconnect.com/products/on-screen-takeoff], [https://www.constructionperks.com/software/on-screen-takeoff].
- **Automation:** Takeoff BOOST = Auto Takeoff (creates Conditions and takeoff for detected areas/linears/counts), Auto Count, Auto Name (sheet names/numbers from title blocks), Auto Scale, **Auto Link** (AI creates Hot Links + Named Views for the whole project; shown in a "Views" sub-tab) (certain) [https://help.constructconnect.com/06-setting-scale-and-drawing-takeoff-including-auto-takeoff-73/on-screen-takeoff-06-02-01-takeoff-boost-auto-takeoff-overview-and-requirements-246], [https://help.constructconnect.com/08-annotations-plan-markups-and-the-image-legend-75/on-screen-takeoff-08-06-00-using-auto-link-to-create-named-views-and-hot-links-automatically-359]. Auto Link caveat: "The built-in links may not correctly reference the updated revision sheets" (certain) [same].
- **Navigation:** Hot Links / Named Views; second and third image windows (annotation/view windows) for multi-window viewing (certain) [https://help.constructconnect.com/04-the-takeoff-tab-in-detail-71/on-screen-takeoff-04-06-takeoff-tab-annotation-and-view-window-2nd-image-window-685].
- **Revisions:** color-coded overlays that "instantly identify additions and deletions between plan versions, with quantities updating" (certain) [https://www.constructionperks.com/software/on-screen-takeoff]. User-reported: PDFs are converted to TIF, "revising drawings to TIFF is outdated" (likely) [https://www.capterra.com/p/121585/On-Screen-Takeoff/reviews/].
- **Estimating (Quick Bid):** labor production adjustable at bid level, change orders, alternates (help section "Projects, Bids, Alternates and Change Orders"), vendor pricing, Excel/QuickBooks/Sage export (certain) [https://help.constructconnect.com/10-adjusting-labor-costs-and-production-131/quick-bid-10-05-adjusting-labor-production-at-the-bid-level-538], [https://www.oncenter.com/products/quick-bid/].
- **Cloud successor:** ConstructConnect Takeoff (browser) carries Auto Name / Auto Scale / Auto Takeoff (certain) [https://www.constructconnect.com/blog/ccto_launch_announcement].
- **Fireproofing / UL / spray charts:** none.
- **Limitations (user-reported):** "lots of menus … confusing"; OST "disconnects from … QuickBid"; no preloaded conditions ("wish the software came preloaded with takeoff items"); report formatting "completely terrible … all one font … random page breaks"; database crashes losing hours; price (likely) [https://www.capterra.com/p/121585/On-Screen-Takeoff/reviews/].

### 1.7 STACK

Cloud takeoff+estimate; area/linear/count/volume/surface tools; OCR, Autoname (sheet names from title block), Auto Count (symbol), auto-bookmarking; prebuilt assemblies/items; prebuilt reports; Excel/CSV export and Excel plugin; API; mobile (iOS/Android) and STACK Invite for third-party markup; Procore integration makes "every drawing, spec, and document in a Procore account available for takeoff in STACK" (certain) [https://www.stackct.com/faq/], [https://www.stackct.com/blog/4-things-to-know-about-the-stack-procore-integration/], [https://sourceforge.net/software/product/STACK/]. User-reported: "a little slow to load at times"; free tier excludes auto-count/export; auto-count "works well enough for simple items … don't trust it blindly" (likely) [https://sourceforge.net/software/product/STACK/], [https://constructioncoverage.com/takeoff-software]. Fireproofing/UL/spray charts: none.

### 1.8 Autodesk Takeoff / ACC

2D (linear/count/area with custom formulas and multiple outputs per takeoff type) + 3D (Revit model classification → counts/areas/volumes/lengths); **Classification systems** uploaded and standardized across projects; **Packages** and **Takeoff Types**; rollup by classification/type/material; Excel export; Takeoff API lists packages/takeoff types/items (certain) [https://construction.autodesk.eu/products/autodesk-takeoff/], [https://aps.autodesk.com/en/docs/acc/v1/reference/http/takeoff-projects-project_id-packages-package_id-takeoff-types-GET]. Sheets live in ACC Docs with native versioning; a yellow indicator flags a taken-off sheet when a new version arrives, and "the user needs to check which areas have changed" (likely) [https://forums.autodesk.com/t5/community-blog-aec-english/autodesk-takeoff-as-a-tool-for-quantitative-calculations/ba-p/14025804]. Snapshots support comparison (certain) [https://www.autodesk.com/blogs/construction/have-you-tried-it-snapshots-and-robust-comparison-capabilities/]. User-reported: "no way to add simple annotations like text notes, clouds, or arrows … every drawing element must be tied to a takeoff type"; complex UI; cost; lag on big projects (likely) [https://www.bidicontracting.com/blog/autodesk-takeoff-review-2026], [https://www.selecthub.com/p/takeoff-software/autodesk-takeoff/]. Fireproofing: none.

### 1.9 Trimble (Tekla Structures / Tekla Structural Designer / Accubid / Estimation MEP)

- **Tekla Structures Fire Proofing Calculator** "calculates the fireproofing thickness and flute fill volume per individual member in the Tekla model … define reference profiles and rating system thickness"; formulas "based on the Fire Resistance Directory Isolatek Designs"; fire-resistance custom components model SFRM for W all-around, W except top flange, and HSS (certain) [https://support.tekla.com/help/tekla-structures/not-version-specific/fire_proofing_calculator], [https://support.tekla.com/help/tekla-structures/usa_fire_resistance]. This is the closest BIM-side analogue to our thickness engine.
- **Tekla Structural Designer 2021** applies fireproofing distribution/thickness/density to all 1D members and adds its self-weight and surface to analysis (certain) [https://support.tekla.com/dist/sxf/document/tekla-structural-designer-2021-release-notes.pdf].
- **Accubid / Estimation MEP:** MEP-only estimating with graphical takeoff, change management, submittal management; new AI for scale/sheet setup and symbol counts (certain) [https://mep.trimble.com/product/trimble-estimation/], [https://highways.today/2026/07/09/trimble-ai-takeoff-tools/]. Not applicable to fireproofing takeoff from 2D PDFs.

### 1.10 Revit / Navisworks

- **Revit:** wide-flange families with an "SOFP thickness" parameter that "will adjust to any size beam"; the Firenetics plugin does "element-by-element fireproofing analysis based on selected manufacturer and fire rating" and computes DFT, gallons, layers for intumescents; Structural Framing schedules quantify beams (certain) [https://www.revitcity.com/downloads.php?action=view&object_id=20328], [https://apps.autodesk.com/RVT/en/Detail/Index?id=4158941018156843625&appLang=en&os=Win64]. Requires a model; most fireproofing subs get PDFs only (guessing).
- **Navisworks Quantification:** Item Catalog + Resource Catalog, Quantification Workbook, model and 2D takeoff, formula overrides, Export Quantities to Excel (certain) [https://help.autodesk.com/cloudhelp/2019/ENU/Navisworks/files/GUID-DC1BE6E6-0DE6-4747-AB2B-2BACF8FEAAFA.htm], [https://www.autodesk.com/autodesk-university/class/Estimating-Navisworks-Quantification-2014]. Fireproofing: none.

### 1.11 Togal.AI

Auto-detects rooms, walls, wall types and counts from PDF; bounding-box **image/pattern search** and text search across the set; auto-naming; version overlay compare; Excel/PDF export; real-time collaboration; Togal.CHAT asks questions of plans/specs (certain) [https://sourceforge.net/software/product/Togal.AI/], [https://www.togal.ai/blog/how-to-export-information-takeoffs-with-togal-ai]. User-reported: latency, selection difficulty, weak civil, "no equivalent review step" and accuracy variance (85% residential vs 60% retail podium on one project) (likely) [https://www.g2.com/products/togal-ai/reviews?qs=pros-and-cons], [https://struvia.co/blog/togal-ai-review-2026]. $299/user/mo (certain) [https://sourceforge.net/software/product/Togal.AI/]. Fireproofing: none.

### 1.12 Other specialty tools

- **eTakeoff Dimension** (drywall/Sage): assemblies "give you multiple results with just one takeoff, such as studs, tracks and drywall by just taking the wall length"; Pattern Search; Snap AI; eTakeoff Bridge pushes quantities into Sage Estimating (certain) [https://etakeoff.com/etakeoff-dimension/dimension-features/].
- **Steelcalc (UK):** estimating/comparison for intumescent, spray and board PFP (certain, title only) [https://steelcalc.co.uk/]. Details not determined from public sources.
- **Manufacturer calculators:** Isolatek UL design PDFs (e.g., X790), Schundler W/D calculator, generic SFRM thickness calculators — all single-member, not takeoff tools (certain) [https://www.isolatek.com/storage/designs_thickness/2019_ul/Wet%20Mix/X790.pdf], [http://www.schundler.com/wdcalc.htm], [https://fire.ezvirtualtools.com/calc/spray-fireproofing.html].
- **Estimating services** (1800estimating, Blaze, Tyler, Primage) describe today's deliverable set: "color-coded markup drawings, takeoff and estimate in Excel spreadsheets, total man-hours … Estimators create submittal drawings and distribute spray charts to workers" (likely) [https://blazeestimating.com/fireproofing-estimating-services/], [https://1800estimating.com/fireproofing-estimating-services/].

---

## 2. Workflow lessons

### 2.1 What an experienced estimator expects takeoff software to do
1. **Conditions first.** Across OST, EDGE, STACK and BuzzBID the primary object is a *condition* (what is being measured + how it is priced), and the drawing is just where you click. Bluebeam's lack of a conditions library is the main reason resellers say it is "not a purpose-built estimating tool" (likely) [https://builderbuzz.com/bluebeam-review]. Users of OST explicitly want conditions preloaded rather than built from scratch (likely) [https://www.capterra.com/p/121585/On-Screen-Takeoff/reviews/].
2. **Set up once, reuse everywhere.** EDGE "Project Conditions" and "Common Conditions", OST "Typical Groups", PlanSwift lists/parts, STACK prebuilt assemblies all exist to avoid re-defining things per sheet (certain) [https://estimatingedge.com/knowledgebase/database-descriptions/].
3. **Quantities flow into the estimate without re-keying** — BuzzBID, Quick Bid, Procore Estimating, eTakeoff Bridge all market this as the core benefit (certain).
4. **Every number is defensible.** "If you can't click into a count and see its source on the plan, you can't defend the bid" (likely, industry guide) [https://quotr.ai/blog/electrical-estimating-software-buyers-guide/].

### 2.2 Fast interactions (worth copying as patterns)
- Scale by clicking two endpoints of a known dimension, or picking a preset from a dropdown (EDGE, PlanSwift, Bluebeam) (certain).
- Click-to-count with the item's properties already selected; drag-and-drop an assembly onto the sheet (PlanSwift) (certain).
- Single-click computer-vision pickup of a whole beam/wall (BuzzBID ClickONCE), with mandatory visual verification (certain).
- Draw a bounding box → search the entire set (Bluebeam VisualSearch, Togal pattern search) (certain).
- Multi-condition takeoff: one trace produces several quantities (OST patent; eTakeoff assemblies) (certain).
- Copy a defined area/takeoff region to other pages (EDGE Common Conditions; EDGE "shapes copied from one area to another") (certain).
- Auto Name + Auto Link + Auto Bookmark on upload, so sheet navigation is set up before the first click (OST/CC Takeoff, PlanSwift, STACK, Procore) (certain).

### 2.3 What frustrates estimators (user-reported)
- Crashes that lose hours (OST databases, EDGE, PlanSwift glitches, Bluebeam large files) [Capterra links above].
- Converting PDFs to TIF for overlays; overlay tools that are hard to use (OST, PlanSwift).
- Ugly, unformatted reports that need hours of cleanup (OST); shop drawings that must be cleaned in a PDF editor (EDGE).
- Database setup that feels like programming (EDGE); having to build every condition from zero (OST).
- One-scale-per-page forcing page duplication for details (PlanSwift).
- AI auto-links that break on revision sheets (OST Auto Link); AI takeoff without a review step (Togal).
- "Still adjust hours in the summary" after fine-tuning — labor that never quite matches the firm's reality (EDGE).
- Subscription licensing migrations (EDGE, Bluebeam Revu 21).
- No simple annotations in a takeoff tool (Autodesk Takeoff).

### 2.4 What should be one click
- Set scale from a preset or from a known line. Apply to selected sheets with an explicit warning (PlanSwift's warning is the right instinct).
- Place a steel member with its shape already resolved to W/D and UL thickness.
- Copy a typical bay/area to another sheet or level.
- Jump from a quantity row to the exact sheet + markup (Bluebeam Markups List pattern).
- Overlay current vs previous revision for the sheet in view (Procore/Bluebeam pattern).
- Toggle the spray-chart color scheme between thickness / UL design / rating / steel type (EDGE pattern).
- Export: Excel per page, PDF spray chart, inspector vs crew spray report (BuzzBID pattern).

### 2.5 How recurring mechanics are handled across the field
| Mechanic | State of the art |
|---|---|
| Assemblies / conditions | Condition = measurement + price/labor recipe (OST, EDGE); assemblies produce several outputs per trace (eTakeoff, OST multi-condition, Autodesk "additional outputs" per takeoff type). |
| Page folders / sheet navigation | Auto Name from title block (OST, STACK, Procore OCR); drawing *areas* and *sets* (Procore); Sets + bookmarks (Bluebeam); page tabs (PlanSwift). |
| Plan hyperlinks / detail linking | Auto Link → Hot Links/Named Views (OST); Batch Link (Bluebeam); callout auto-linking (Procore); Auto Bookmark (PlanSwift). All warn that revision sheets break links. |
| Multi-scale | Bluebeam Viewports (best); PlanSwift requires page duplication; Procore/STACK/EDGE not determined. |
| Multi-window | OST 2nd/3rd image windows; Bluebeam split view/tabs; PlanSwift page tabs. |
| Overlays / revision compare | Bluebeam Overlay Pages + Compare Documents (batch); Procore overlay + Compare Set + markups carry forward; OST color overlay with quantity update; Autodesk yellow indicator on new version; Togal overlay. |
| Legends | Bluebeam dynamic Legend; EDGE spray-chart legend by thickness; OST Image Legend; STACK plan legends. |
| Searchable text | Bluebeam text + VisualSearch; Togal text/image/pattern search; STACK OCR; Procore OCR for sheet metadata. |
| Audit trails | Bluebeam Markups List (page/author/date/status, CSV summary); EDGE shape-by-shape thickness/BF table + Condition Detail; PlanSwift per-page Excel export. |
| Excel connectivity | Bluebeam Quantity Link (live); PlanSwift import/export plugins; STACK plugin + CSV; EDGE "Download as Excel"; Navisworks/Autodesk export. |
| Custom reports | EDGE standard report set (Recap, Condition Detail, Stocking, Labor, fireproofing adjustments); Quick Bid branded proposals; STACK prebuilt reports; OST reports criticized. |

### 2.6 Estimating → operations transfer
- **General:** Procore converts won estimates into prime contracts, budgets and commitments (certain) [https://www.procore.com/preconstruction]. STACK/Bluebeam/Drawboard push annotated sets into Procore Documents/Drawings (likely).
- **Fireproofing-specific:** the handoff artifacts are the **spray chart / color-up** (crew), the **inspector spray report** with every estimated thickness (BuzzBID "As Estimated"), the **stocking list** (EDGE Stocking report, bags per job), labor man-days (EDGE Labor report), and **shop drawings** for submittal (EDGE/BuzzBID) (certain). EDGE On Site then collects field production back to the office (certain) [https://estimatingedge.com/release-edge-on-site/].
- Inspectors verify installed thickness against the approved submittal's thickness tables and mark inspected areas on a reduced plan kept on site (likely) [https://bahlfireproofing.com/the-fireproofing-inspection-process-a-complete-guide-for-building-owners/]. The spec expects shop drawings showing "the extent of sprayed fire-resistive material for each construction and fire-resistance rating including minimum thicknesses" (certain, spec text) [https://webapps.bart.gov/bfs/BFS_3_1_Spec/STDSPEC/07%2081%2016.pdf].

### 2.7 How shop/submittal drawings are created today — and what nobody does
- **EDGE:** color-codes the takeoff lines on the blueprint by steel type / UL design / rating / thickness and prints; output described by users as messy and finished in a PDF editor (certain + likely).
- **BuzzBID:** produces an optimized (rounded-up for crew) and an as-estimated (inspector) spray report (certain).
- **Everyone else:** estimators export quantities, then hand-draw color-ups in Bluebeam and assemble a submittal package manually; estimating services deliver "color-coded markup drawings" as PDFs (likely).
- **Not done by any tool found:** (a) a submittal-ready drawing set with title block, legend, UL design references and thickness schedule generated from the takeoff *and* kept in sync when a revision arrives; (b) pushing that set into the GC's Procore Drawings/Submittals via API; (c) revision-diff on the *fireproofing* layer (which members changed, which thicknesses changed) rather than raster overlay; (d) a field/inspector view that links each sprayed member back to its UL design and estimated thickness; (e) per-member audit from bag count back to drawing click. None of these were found in any product surveyed (guessing that they exist nowhere, certain that no public source describes them).

---

## 3. Comparison table

Legend: Y = present (certain/likely as cited above); P = partial/workaround; N = none; ? = not determined from public sources.

| Dimension | EDGE | BuzzBID | PlanSwift | Procore | Bluebeam | OST/QB | STACK | Autodesk Takeoff | Tekla | Revit/Navis | Togal |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Plan ingestion | PDF/img | cloud | PDF/img, limited | PDF only, OCR split | PDF, Sets | PDF→TIF | PDF, OCR | ACC Docs | model | model | PDF/CAD |
| Multi-scale per sheet | ? | ? | P (dup page) | ? | Y viewports | ? | ? | ? | n/a | n/a | ? |
| Takeoff modes | lin/area/count by shape | click-once CV | lin/area/count | lin/area/count | all + dyn fill | lin/area/count, multi-cond | all + volume | lin/area/count/BIM | model | model/2D | auto + manual |
| Auto-count / symbol search | ? | Y (CV) | Y | N | VisualSearch | Y Boost | Y | N | n/a | n/a | Y |
| Auto-name / OCR | ? | ? | Auto Bookmark | Y | AutoMark | Auto Name/Link | Y | ACC | n/a | n/a | Y |
| Conditions | Y core | Y | items | est. module | N (columns) | Y core | Y | takeoff types | n/a | catalogs | N |
| Assemblies | Y | Y | Y | ? | P | Y (QB) | Y | outputs/formulas | n/a | Y | N |
| Mfr databases | Y (Grace/Isolatek/Carboline) | UL tests | user | ? | N | vendor pricing | regional | N | Isolatek designs | plugin | N |
| Fireproofing specialization | Y | Y (FireShield) | N | N | N | N | N | N | calculator | plugin/family | N |
| UL design handling | Y auto-assign | Y | N | N | N | N | N | N | Y | plugin | N |
| Thickness handling | auto + per-shape adjust | auto + crew-optimized | N | N | N | N | N | N | per member | parameter | N |
| Estimating (labor/WBS/alt) | Y | Y | Y | Y | N | Y (QB) | Y | export | N | export | N |
| Revision overlay/compare | ? | ? | P | Y + bulk | Y batch | Y | ? | indicator + snapshots | n/a | n/a | Y |
| Reports | strong set | spray reports | Excel | PM reports | Markups summary | weak (user) | prebuilt | rollups | reports | Excel | Excel/PDF |
| Shop drawings | Y (messy) | Y optimized | N | N (hosts them) | manual | N | N | N | N | N | N |
| Spray charts | Y | Y (2 kinds) | N | N | manual | N | N | N | N | N | N |
| Submittals | N | ? | N | Y core + API | N | N | N | ACC | N | N | N |
| Field / mobile | EDGE On Site | ? | N | Y | iPad | tablet | Y | ACC | N | N | ? |
| Collaboration | section checkout | cloud | N | Y | Studio | N | Y + Invite | Y | N | N | Y |
| Auditability | per-shape table | visual verify | per-page export | logs | Markups List | per-condition | ? | inventory | n/a | workbook | ? |
| Excel / API | Excel | ? | Excel plugins | REST + webhooks | Quantity Link | Excel/Sage | Excel + API | Excel + API | reports | Excel | Excel |

---

## 4. Design implications for our product

1. **Make the condition the primary object, and pre-seed it.** Ship fireproofing conditions (beam/column/joist/deck/flute fill by rating, product, UL design) ready to use; OST users' top wish is preloaded conditions, and EDGE users dislike the "coding" feel of database setup.
2. **Steel shape → W/D → UL design → thickness must be automatic, visible, and overridable per member.** Mirror EDGE's shape-by-shape adjustment grid (thickness, BF, adjusted BF) and BuzzBID's crew-optimized vs as-estimated split; show the formula inputs so the number is defensible.
3. **Two spray-chart products from one dataset:** inspector/"as estimated" (exact UL thickness per member) and crew/"optimized" (rounded, simplified). Color-by selector: thickness / UL design / rating / steel type, with an auto-generated legend.
4. **Shop drawings must be submittal-ready out of the box** (title block, legend, UL references, thickness schedule, clean vector output). The incumbent's output is cleaned up in Bluebeam; eliminate that step.
5. **Per-member audit trail:** every bag/board-foot total drills to member → sheet → click → UL design → formula. Bluebeam's Markups List filter-by-page and CSV summary is the familiar pattern.
6. **Scale: preset dropdown + two-click calibration + viewports for multi-scale sheets** (Bluebeam model), never PlanSwift-style page duplication. Warn before applying a scale to many sheets.
7. **Sheet setup on upload:** OCR sheet names/numbers, discipline, auto-bookmarks and callout links; expect revision sheets to break links and provide a repair action.
8. **Revision handling at the member level, not just raster overlay:** keep raster overlay (familiar), but also diff the fireproofing layer (members added/removed/resized → thickness delta) and carry markups forward like Procore.
9. **Copy typical areas across sheets/levels** (EDGE Common Conditions / OST Typical Groups) with a one-click "paste to level" that re-resolves member sizes.
10. **Excel is the lingua franca:** per-page and per-condition exports, plus a live link option like Quantity Link, before any ERP integrations.
11. **Procore integration is feasible and valuable:** push shop drawings as Drawing revisions (direct-upload flow with `drawing_id` for no-review assignment), as Documents, and as Submittal attachments; subscribe to drawing-revision webhooks to trigger re-takeoff. Resolve company-specific status IDs at runtime; respect the 3,600 req/hr quota.
12. **Reliability over features:** the loudest complaints across every product are crashes/lost work, lag on large sets, and bad report formatting. Autosave, per-sheet incremental saves and clean PDF/Excel output are table stakes.
13. **AI with a review step:** auto-detect beams/columns (BuzzBID/OST Boost pattern) but always present a verification pass; Togal reviews show unreviewed AI output is not trusted.
14. **Field loop:** a lightweight crew/inspector view (spray chart on tablet, tap member → UL design + thickness) and production capture back to the office (EDGE On Site pattern) closes the estimating→operations gap that no competitor fully closes.

---

## 5. Gaps in this research
- Direct vendor pages for EDGE, BuzzBID, Procore developer portal, Bluebeam, OST help, Tekla help and all review sites were blocked; only snippets were available. EDGE revision/overlay, auto-count, multi-scale and API capabilities remain undetermined. BuzzBID scale, revisions, Excel and collaboration remain undetermined.
- Procore submittal attachment field (`prostore_file_ids` vs `upload_ids`) on v1.1 came from a third-party mirror and should be verified on developers.procore.com.
- No first-hand forum threads (Reddit r/estimators, Mike Holt) could be read; frustrations are drawn from Capterra/SelectHub/SourceForge snippets.
