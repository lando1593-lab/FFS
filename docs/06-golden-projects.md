# Golden Projects

A golden project is a drawing set plus a hand-verified answer key. Metrics are computed by
`ffs golden score`. Nothing ships without the numbers.

## Layout
```
golden/
  synthetic/            generated sheets with exact known answers (committed)
    gp0_simple_bay/
      sheet.pdf
      truth.json
  gp1_<name>/           real project (source PDFs NOT committed; see .gitignore)
    source/             contract PDFs (local only)
    truth.json          hand-verified members per level
    notes.md            what was ambiguous and how you decided
```

## truth.json schema (v0)
```json
{
  "project": "gp0_simple_bay",
  "sheets": [{"file": "sheet.pdf", "page": 1, "sheet_no": "S-201", "level": "LEVEL 02", "scale": "1/8\"=1'-0\""}],
  "members": [
    {"id": "m001", "level": "LEVEL 02", "section": "W18X35", "type": "beam",
     "start_grid": "C/5", "end_grid": "D/5", "length_in": 342.0, "status": "new"}
  ]
}
```

## Metrics
| metric | definition |
|--------|-----------|
| detection recall | truth members matched by a predicted instance (same level, same section, geometry overlap) / truth members |
| detection precision | matched predictions / all predictions |
| designation accuracy | matched instances whose canonical section equals truth |
| length error | median and 95th percentile of |pred − truth| / truth; also count beyond 2% |
| duplicate rate | predictions matching an already-matched truth member / predictions |
| false positives / negatives | listed individually with sheet and bbox for triage |

## What I need from you for real goldens
1. Two structural sets (vector PDF preferred, one scanned set later). Different engineers' drawing
   styles are more valuable than two sets from the same firm.
2. For one level per set: your own takeoff by designation and LF, plus how you handled columns,
   cantilevers, and existing steel.
3. Which architect's set goes with them (needed later for exposure, not for M1).
