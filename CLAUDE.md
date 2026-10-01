# FFS — Fireproofing Takeoff & Project Platform

Structural-steel fireproofing takeoff → estimate → shop drawings → submittals → field drawings,
all driven by ONE project model. Read `docs/00-phase0-plan.md` first, then `docs/03-architecture.md`.

## Non-negotiable product rules (enforced in code review)
1. Never manufacture UL designs, ratings, thicknesses, product data, yields, or code requirements.
   `UNKNOWN — REVIEW REQUIRED` is always an acceptable value. Fabrication is a P0 bug.
2. Every stored fact/calculation carries provenance: source document, sheet/page, location,
   evidence text, confidence, reasoning path, applicable rule/design, and verification state.
3. Every assertion is classed as one of: FACT, INTERPRETATION, CALCULATION, ASSUMPTION,
   CODE_PRODUCT_RULE, HUMAN_OVERRIDE. See `backend/src/ffs/core/assertions.py`.
4. Deterministic engines own geometry, quantities, rules, and calculations. LLMs may assist
   interpretation only, and their output is an INTERPRETATION with confidence, never a FACT.
5. Theoretical and adjusted (waste-applied) quantities are stored separately. Never store a bare
   thickness without its governing design/product/revision context.
6. The LaCie reference library is READ ONLY and is historical reference, never authority.
7. One `MemberInstance` participates in takeoff, estimate, shop drawing, submittal, field drawing
   and revision without being recreated. Stable IDs (ULID) everywhere.

## Layout
- `backend/` Python 3.11+ package `ffs` (uv-managed). CLI: `ffs`. Tests: `backend/tests`.
- `tools/lacie_inventory/` standalone read-only cataloging tool run on the user's local machine.
- `docs/` requirements, architecture, data model, ADRs, research outputs.
- `golden/` manually verified golden projects + synthetic generators used for accuracy metrics.
- `frontend/` (not yet created) React/TypeScript drawing viewer + takeoff panel.

## Dev commands
```
cd backend && uv sync && uv run pytest -q
uv run ffs --help
uv run ruff check src tests && uv run ruff format --check src tests
```

## Conventions
- Units: internal lengths in PDF points at ingest; member lengths stored in inches (Decimal-safe
  float) with a `length_source` and `length_confidence`. Display in ft-in.
- Designations canonicalized to AISC form (`W18X35`, `HSS6X6X1/4`, `L4X4X1/2`), raw text preserved.
- No silent merges of distinct shapes. Ambiguous OCR → low confidence + review flag.
- Commit messages: imperative, scoped (`steel: parse HSS designations`).
