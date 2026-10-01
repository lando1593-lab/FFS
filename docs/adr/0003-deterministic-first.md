# ADR-0003: Deterministic-first processing

Status: accepted.

Geometry, scale, lengths, counts, section factors, thickness lookups, material math, revision
diffs, and QA are deterministic and unit-tested. Milestone 1 uses no LLM at all so that golden
project metrics measure the pipeline, not a model's mood. AI assists later for classification and
messy-text interpretation, always behind an interface and always producing reviewable
INTERPRETATION assertions.
