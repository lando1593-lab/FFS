# ADR-0001: Core stack

Status: accepted (Phase 0). Revisit at Milestone 6 (drawing generation) and Milestone 10 (field).

## Decision
Python 3.11+ for all document, geometry, rules, and generation code. PostgreSQL for the project
model (SQLite for tests/dev). FastAPI for the API. React + TypeScript for the viewer. PyMuPDF for
PDF read/render/write. Shapely for geometry. ezdxf for DXF export. Background jobs via a worker.

## Why not a .NET/desktop stack like legacy estimating tools
The hard parts (PDF vector extraction, geometry, CV, OCR, structured data) are best served in
Python. A web UI lets estimating, review, and field modes share one model and run locally in a
container for privacy.

## Why not "upload PDF → LLM → answer"
Quantities derived by an LLM cannot be audited, reproduced, or scored. Every milestone's accuracy
gate depends on deterministic code. LLMs are allowed only as interpretation assistants writing
INTERPRETATION rows.

## Consequences
- Team must maintain a Python backend and a TS frontend.
- Native DWG authoring is not promised. DXF via ezdxf and vector PDF are the interchange formats.
