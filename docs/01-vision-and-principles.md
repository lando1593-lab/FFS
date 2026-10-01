# Vision and Operating Principles

The product: a fireproofing estimator + project engineer + detailing assistant, built on one
project model that flows

CONTRACT DOCUMENTS → PROJECT MODEL → STEEL MEMBER DATABASE → FIRE-RATING ENGINE →
FIREPROOFING DESIGN ASSIGNMENTS → ESTIMATE → SHOP DRAWINGS → SUBMITTAL PACKAGE →
APPROVED REVISIONS → FIELD SPRAY DRAWINGS → MATERIAL PROCUREMENT → FIELD VERIFICATION / AS-BUILTS

A change upstream is traceable downstream. Nothing is recreated by hand between estimating and
operations.

## Priority order (ties are broken in this order)
1. Accuracy over speed.
2. Traceability over magic.
3. Current authoritative data over stale assumptions.
4. Deterministic calculation over LLM guesses.
5. Human review over fake confidence.
6. One project model over disconnected estimating and operations databases.

## Assertion classes
Every stored statement about the project is exactly one of:

| Class | Meaning | Example |
|-------|---------|---------|
| FACT | Extracted directly from a source document, with location | "Text `W18X35` at S-201 bbox (412,318,460,327)" |
| INTERPRETATION | A reading of facts that a reasonable estimator could dispute | "That label belongs to the beam segment from grid C/5 to D/5" |
| CALCULATION | Deterministic math over inputs with a stated method | "Length = 342.0 in from segment endpoints at 1/8\"=1'-0\"" |
| ASSUMPTION | A value chosen in the absence of evidence, flagged for review | "Deck condition assumed per project default; no detail found" |
| CODE_PRODUCT_RULE | A rule drawn from code, listing, or manufacturer data with revision | "IBC 2021 Table 601 … (edition, jurisdiction)" |
| HUMAN_OVERRIDE | An estimator's explicit decision that supersedes the above | "Reclassified as existing-to-remain; excluded" |

Each carries: source document, sheet/page, location, evidence, confidence, reasoning path,
applicable rule/design, and `verified_by` / `verified_at`.

## Authority hierarchy for code and compliance questions
1. Code legally adopted by the project jurisdiction
2. State / local amendments
3. Project-specific code analysis and permitted construction documents
4. Referenced standards / listed assemblies
5. Current UL listing / certification information
6. Current manufacturer design documents and technical data
7. Project specifications
8. Project drawings and schedules
9. Approved substitutions / addenda / RFIs
10. Historical reference material (LaCie library) — never authoritative on its own

Effective dates and revision dates are stored with every rule. "Latest IBC" is never assumed.

## Never manufacture
UL designs, ratings, thicknesses, product data, yields, code requirements.
`UNKNOWN — REVIEW REQUIRED` is always acceptable output.
