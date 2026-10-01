# ADR-0002: Provenance and assertion classes

Status: accepted.

## Decision
Every stored statement is an `Assertion` with class FACT / INTERPRETATION / CALCULATION /
ASSUMPTION / CODE_PRODUCT_RULE / HUMAN_OVERRIDE, confidence 0–1, a `source_ref`, a reasoning
string, and verification fields. Member rows require at least one `MemberEvidence`. Overrides
supersede rather than mutate.

## Why
The product promise is "click any quantity and see where it came from." That is only cheap if
provenance is a first-class table from day one, not a log bolted on later.

## Consequences
- More rows, more joins. Acceptable; projects are tens of thousands of members, not billions.
- Service-layer functions, not raw ORM writes, are the only way to create members.
