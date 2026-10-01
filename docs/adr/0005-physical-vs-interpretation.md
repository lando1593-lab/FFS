# ADR-0005: Immutable physical member layer; versioned, scenario-scoped interpretation

Status: accepted (design); implementation in Milestone 2.

## Decision
`member_instances` holds only what a tape measure and the structural drawing establish:
canonical section, geometry, length (with its evidence and confidence), level, sheet, grid
references, and the evidence links. Rows are write-once; a corrected geometry is a new row that
supersedes the old (`superseded_by_id`), never an update.

Everything an estimator can disagree about lives in assignment tables keyed by
`(member_id, scenario_id)` with their own revision and provenance:

| table | holds |
|---|---|
| member_interpretations | member role (beam/girder/column/brace), new/existing/demo, scope class (in / out / likely in / likely out / unknown) with reason, exclusion category |
| rating_assignments | required rating, element category (primary frame, floor, roof…), rule reference and edition |
| exposure_assignments | concealed / exposed / likely exposed / AESS / exterior / unknown, evidence |
| condition_assignments | condition id (FP-01…), protection type (SFRM / intumescent / none), sides |
| design_assignments | design@revision, product@revision, section-factor method and value, thickness with its exact source row |
| scenarios | base bid, alternates, VE, post-bid; each owns its assignment sets; one is current |
| review_items | unknown / conflict / missing_document / assumption / rfi_candidate; subject, known, likely, why, missing, options, status, resolution assertion |
| stages | estimated / contracted / approved / field / as_built: frozen snapshots of a scenario's assignment sets and quantities |

## Consequences
- Product switching, scenario comparison and live recalculation are reads over assignment
  sets; geometry is never touched.
- The resolution meter and bid readiness are queries over `review_items`.
- Corrections (AI proposal → human decision) are pairs of assertions with a class
  (company practice, estimator preference, project-specific, code, manufacturer) and never
  become rules by themselves.
- The current `MemberRecord`/`MemberInstance` fields `member_type`, `status`, `review_state`
  move to `member_interpretations`; the Milestone-1 CLI keeps working through a compatibility
  view until the web app exists.
