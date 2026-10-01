# Architecture (v0)

## Stack decision (see ADR-0001)
| Concern | Choice | Why |
|---------|--------|-----|
| Core language | Python 3.11+ | Best libraries for PDF, geometry, CV, OCR, data; your team can read it |
| PDF / vector | PyMuPDF | Fast native text with coordinates, vector path extraction, rendering, PDF writing (overlays, shop drawings) |
| Geometry | Shapely 2 | Robust line/polygon ops for label↔member association, grid intersection, exposure surfaces |
| CV / OCR | OpenCV + (Tesseract or PaddleOCR; decide at first scanned golden) | Raster pages only; OCR path always flagged |
| Rules | Python rule modules + versioned data tables (not a generic rules engine) | Rules must be readable, cite sources, and be unit-tested |
| Database | PostgreSQL (SQLite for local dev/tests) via SQLAlchemy 2 + Alembic | Relational provenance graph, JSONB for evidence detail, PostGIS optional later |
| API | FastAPI | Typed, async, OpenAPI for the frontend |
| Frontend | React + TypeScript (Vite), canvas/WebGL viewer over PDF tiles, SVG overlay layer | Estimating-software feel: multi-window, fast pan/zoom, overlays |
| Drawing generation | Dedicated service: model → layered vector scene graph → PDF (PyMuPDF/ReportLab), SVG, DXF (ezdxf) | DXF via ezdxf is reliable; native DWG authoring is NOT promised |
| Jobs | Background worker (arq/Celery) for ingest, compare, render | Long-running, resumable |
| AI | Optional interpretation service (LLM) behind an interface; outputs INTERPRETATION rows only | Deterministic-first |

## Services (logical; one process in dev, separable in prod)
```
┌─────────────┐  ┌──────────────┐  ┌───────────────┐  ┌────────────────┐
│ Ingest       │  │ Steel        │  │ Rating / Code │  │ Design / Mat'l │
│ pdf,ocr,scale│→ │ designation, │→ │ profile,rules │→ │ listings, W/D, │
│ grids, sheets│  │ labels, geom │  │ categories    │  │ thickness, qty │
└─────────────┘  └──────────────┘  └───────────────┘  └────────────────┘
        ↓                ↓                 ↓                   ↓
┌──────────────────────────────────────────────────────────────────────┐
│ PROJECT MODEL (PostgreSQL): members, evidence, assertions, conditions │
│ WBS, revisions, audit                                                 │
└──────────────────────────────────────────────────────────────────────┘
        ↓                ↓                 ↓                   ↓
┌─────────────┐  ┌──────────────┐  ┌───────────────┐  ┌────────────────┐
│ Review queue │  │ Estimate     │  │ Drawing Gen   │  │ Submittal /    │
│ + viewer API │  │ scenarios    │  │ shop/field    │  │ Field / Ops    │
└─────────────┘  └──────────────┘  └───────────────┘  └────────────────┘
```

## Drawing-generation service (explicit)
Input: a `ShopDrawingSet` request (project, WBS selection, template, revision).
Steps:
1. Resolve background: the contract sheet revision referenced by the set (rendered as a locked
   base layer, or re-vectorized where possible).
2. Build a scene graph: `Layer{name, visible, objects[]}`, `DrawingObject{geometry, style,
   links: member_instance_id | condition_id | note_id}`.
3. Legend, spray chart, key plan, title block from templates with data bindings.
4. Run QA checks (FR-QA-01) and print-preview validation; refuse to issue on blocking failures.
5. Emit vector PDF (primary), SVG, DXF; persist `ShopDrawingSheet` with object→ID map so clicks in
   the viewer resolve to model entities.

## Deterministic vs AI boundary
- Deterministic: text extraction, designation parsing, scale math, grid detection, geometry
  association, lengths, section factors, thickness lookup, quantity math, revision diffs, QA.
- AI-assisted (later, optional): sheet-type classification, code summary field extraction from
  messy text, note/spec interpretation, exposure hints from architectural descriptions. Always
  recorded as INTERPRETATION with model id, prompt hash, and confidence; always reviewable.

## Privacy
Default deployment is single-tenant and local (Docker Compose). No external calls unless an
integration (Procore, manufacturer data refresh, LLM) is explicitly configured.

## Milestone-1 subset implemented in Phase 0
`backend/src/ffs/`: `ingest/pdf.py`, `ingest/scale.py`, `steel/designation.py`, `steel/aisc.py`,
`steel/labels.py`, `steel/geometry.py`, `takeoff/`, `render/overlay.py`, `db/models.py`, `cli.py`.
