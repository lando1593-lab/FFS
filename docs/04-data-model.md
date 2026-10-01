# Data Model (v0)

Principle: a `MemberInstance` is created once and referenced everywhere. Everything that explains
a member (where it was seen, what it is, what rating/design/thickness it got, what changed) hangs
off it as evidence, assertions, assignments, and audit events. No downstream module copies member
rows.

## Entity map
```
Organization ─┬─ User
              └─ Project ─┬─ ProjectDocument ─┬─ DocumentRevision ─ Sheet ─┬─ Viewport (scale, bbox)
                          │                   └─ (addenda, RFIs, specs)    ├─ GridLine
                          │                                                └─ TextSpan / PathSegment (ingest cache)
                          ├─ Level / Area / Zone / WbsNode
                          ├─ CodeProfile ─ CodeRuleApplication
                          ├─ MemberMark (B1, C3 → schedule resolution)
                          ├─ MemberInstance ─┬─ MemberEvidence (n per member; each → Sheet, bbox, raw text)
                          │                  ├─ Assertion (FACT/INTERP/CALC/ASSUMPTION/RULE/OVERRIDE, confidence, reasoning)
                          │                  ├─ MemberGeometry (per level for columns; start/end xy, grids)
                          │                  ├─ ExposureClassification
                          │                  ├─ RatingAssignment (rating, source rule, confidence)
                          │                  ├─ DesignAssignment (FireDesign@rev, product@rev, W/D method, thickness, override)
                          │                  └─ ConditionAssignment (Condition, scenario)
                          ├─ Condition (repeatable logic: member type, rating, design, product, exposure sides, waste, labor, legend style)
                          ├─ TakeoffScenario (alternate systems/pricing; assignments are scenario-scoped)
                          ├─ ShopDrawingSet ─ ShopDrawingSheet ─ DrawingObject (geometry + link to MemberInstance/Condition/Note)
                          ├─ SubmittalPackage ─ SubmittalRevision ─ ReviewComment (→ affected members/conditions)
                          ├─ FieldDrawingSet ─ FieldSheet ─ FieldEvent (sprayed/inspected/repair, photo, note)
                          ├─ MaterialRelease (phase/level/area → quantities, tied to forecast)
                          ├─ RevisionComparison ─ MemberDelta
                          └─ AuditEvent (every mutation)

Reference (versioned, project-independent):
SteelShape (AISC data, version) · Manufacturer · Product@Revision · FireDesign@Revision ·
ThicknessTable · YieldTable · Packaging · CodeEdition · CodeRule@Edition · JurisdictionAdoption
```

## Key tables (M1 subset is implemented in `backend/src/ffs/db/models.py`)

### member_instances
| column | notes |
|--------|-------|
| id (ULID) | stable forever |
| project_id, level_id, zone_id (nullable) | every member belongs to a level |
| member_mark (raw), canonical_section (`W18X35`), shape_id (FK steel_shapes, nullable if unknown) | |
| member_type | beam / girder / column / brace / joist / misc / unknown |
| status | new / existing / demo / unknown |
| length_in, length_source (geometry / dimension_text / schedule / manual), length_confidence | |
| orientation_deg, start_x/y, end_x/y (sheet coords), start_grid, end_grid | |
| confidence_id, confidence_geom, confidence_length, confidence_level | split confidences |
| review_state | unreviewed / accepted / edited / excluded / conflict |
| created_from_revision_id | which document revision introduced it |
| superseded_by_id | revision lineage |

### member_evidence
| column | notes |
|--------|-------|
| member_instance_id, sheet_id, viewport_id | |
| kind | plan_label / schedule_row / section / elevation / detail / note / legend |
| bbox, raw_text, extraction_path (pdf_text / ocr / manual) | |
| confidence | |

### assertions
| column | notes |
|--------|-------|
| subject_type, subject_id | polymorphic: member, rating, design, code profile… |
| klass | FACT / INTERPRETATION / CALCULATION / ASSUMPTION / CODE_PRODUCT_RULE / HUMAN_OVERRIDE |
| key, value (JSON) | e.g. `length_in = 342.0` |
| method, inputs (JSON), reasoning | reproducible derivation |
| source_ref (JSON) | document/sheet/bbox/rule id/design id@rev |
| confidence | 0–1 |
| verified_by, verified_at | human verification |
| supersedes_id | overrides form a chain, never a delete |

### Quantities (M10) — distinct columns, never conflated
estimate_rev_qty · contract_qty · approved_qty · forecast_qty · shop_rev_qty · field_rev_qty · installed_qty

## Invariants enforced in code
- Member row cannot be inserted without ≥1 evidence row (service layer) — tests cover this.
- `thickness` never stored outside a `DesignAssignment` that references `fire_design_id` + `design_revision`.
- `theoretical_qty` and `adjusted_qty` are separate columns with a `waste_factor` and its source.
- Overrides never update the original assertion; they add a HUMAN_OVERRIDE that supersedes it.
