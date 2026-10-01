# Milestone 1 Pipeline — Structural PDF → Member Database → Counts + LF

## Stages
```
PDF file
 1. ingest/pdf.py      → pages: size, rotation, text spans (text, bbox, font size, rotation),
                         vector path segments (lines/polylines with width), raster flag
 2. ingest/sheets.py   → sheet number/title from title block region; discipline/type class
 3. ingest/scale.py    → scale candidates from text ("1/8\" = 1'-0\"", "SCALE: 1/4\"=1'-0\"",
                         "1:100"); viewport bounds; verification against dimension strings
                         ("28'-6\"" between two witness lines); manual calibration record
 4. ingest/grids.py    → grid bubbles (circle-ish paths + short label) and grid lines
 5. steel/designation  → find designation tokens in spans; parse; canonicalize; OCR normalize;
                         AISC validate
 6. steel/labels.py    → classify context: plan label vs schedule/legend/note/detail; new vs
                         existing (E)/demo (D) prefixes; "TYP", "SIM", "UNO" handling
 7. steel/geometry.py  → associate label with the member segment: candidate segments parallel to
                         label rotation within a search radius, long enough to be framing, not
                         grid lines; pick best; compute length via scale; compute grid endpoints
 8. steel/dedupe.py    → same canonical section + overlapping geometry on the same level/sheet
                         pair → one instance with multiple evidence
 9. takeoff/aggregate  → counts and LF by level × designation; by sheet; CSV/XLSX
10. render/overlay.py  → vector overlay PDF: green=verified, yellow=uncertain, red=conflict,
                         gray=excluded; label and length annotated
```

## Where the risk is (ranked)
1. **Label→segment association on dense plans.** Mitigation: parallelism + proximity + "not a grid
   line" + "not a dimension line" filters; low-confidence → review queue; synthetic goldens with
   known answers; real goldens.
2. **Scale.** Mitigation: never trust one source; cross-check scale text vs explicit dimension
   strings vs grid spacing from the structural grid dimension strings; store all candidates.
3. **Duplicates** across enlarged plans, matchlines, and sections. Mitigation: evidence model +
   dedupe stage + "counted once" assertion per instance.
4. **Scanned sets.** OCR path deferred until a real scanned golden exists.
5. **Schedules.** Table extraction via PyMuPDF `find_tables()` first; fallback to column clustering.

## Confidence model for M1
| confidence | derived from |
|------------|-------------|
| identification | token regex match quality, AISC validation, OCR normalization applied?, font size consistent with plan labels |
| geometry | segment found? parallel? distance; competing candidates ratio |
| length | scale confidence × geometry confidence; dimension-string corroboration raises it |
| level | sheet-level mapping confidence (title parse) |

## Done when
- Synthetic golden #0: 100% detection, 100% designation, ≤0.5% length error, 0 duplicates.
- Real golden #1 and #2 metrics reported (targets set after the first run; no made-up targets).
- CSV/XLSX export, overlay PDF, manual correction via CLI JSON patch (UI comes in M1.5).
