"""Synthetic structural framing sheet generator with an exact answer key.

Produces a 24x36 vector PDF that looks like a simple framing plan: grid bubbles, grid lines,
girders along grids, infill beams, parallel labels, a dimension string, a beam schedule block, a
general note containing a designation (should be classified as NOTE, not a member), and a title
block with sheet number, title, and scale. ``truth.json`` lists every physical member with its
exact length so the pipeline can be scored.

The synthetic sheet is a *unit test*, not a claim that real drawings look like this.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pymupdf

from ffs.core.units import inches_to_ft_in

SHEET_W, SHEET_H = 36 * 72, 24 * 72  # 36x24 landscape, points
SCALE_TXT = '1/8" = 1\'-0"'
IPP = 96.0 / 72.0  # 1/8"=1'-0": 1 pt = 96/72 real inches


def _pt(real_in: float) -> float:
    return real_in / IPP


def generate(
    out_dir: str | Path,
    *,
    bays_x: int = 4,
    bays_y: int = 3,
    bay_ft: float = 30.0,
    level: str = "LEVEL 02",
    sheet_no: str = "S-202",
) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open()
    page = doc.new_page(width=SHEET_W, height=SHEET_H)
    sh = page.new_shape()
    ox, oy = 180.0, 160.0  # plan origin on sheet (points)
    bay_pt = _pt(bay_ft * 12)
    xs = [ox + i * bay_pt for i in range(bays_x + 1)]
    ys = [oy + j * bay_pt for j in range(bays_y + 1)]
    letters = "ABCDEFGH"
    truth: list[dict] = []

    # grid lines + bubbles
    for i, x in enumerate(xs):
        sh.draw_line((x, oy - 40), (x, ys[-1] + 20))
        sh.finish(color=(0.4, 0.4, 0.4), width=0.3, dashes="[6 3] 0")
        sh.draw_circle((x, oy - 55), 11)
        sh.finish(color=(0, 0, 0), width=0.7)
        page.insert_text((x - 3.5, oy - 51), str(i + 1), fontsize=10)
    for j, y in enumerate(ys):
        sh.draw_line((ox - 40, y), (xs[-1] + 20, y))
        sh.finish(color=(0.4, 0.4, 0.4), width=0.3, dashes="[6 3] 0")
        sh.draw_circle((ox - 55, y), 11)
        sh.finish(color=(0, 0, 0), width=0.7)
        page.insert_text((ox - 59, y + 3.5), letters[j], fontsize=10)

    # girders along horizontal grids (W24X76), drawn slightly off the grid line as in CAD (offset 0)
    gird = "W24X76"
    for j, y in enumerate(ys):
        for i in range(bays_x):
            x0, x1 = xs[i], xs[i + 1]
            sh.draw_line((x0, y), (x1, y))
            sh.finish(color=(0, 0, 0), width=1.4)
            page.insert_text(((x0 + x1) / 2 - 16, y - 4), gird, fontsize=6)
            truth.append(
                _member(
                    gird,
                    "beam",
                    level,
                    f"{letters[j]}/{i + 1}",
                    f"{letters[j]}/{i + 2}",
                    bay_ft * 12,
                )
            )
    # columns along vertical grids are drawn as small squares (not taken off in M1 plan pass)
    for x in xs:
        for y in ys:
            sh.draw_rect(pymupdf.Rect(x - 3, y - 3, x + 3, y + 3))
            sh.finish(color=(0, 0, 0), fill=(0, 0, 0), width=0.5)
    # infill beams: 2 per bay, vertical (along y), labelled with rotated text; alternate sections
    infill = ["W18X35", "W16X26", "W18X40"]
    k = 0
    for i in range(bays_x):
        for j in range(bays_y):
            y0, y1 = ys[j], ys[j + 1]
            for n in (1, 2):
                x = xs[i] + n * bay_pt / 3
                sec = infill[k % len(infill)]
                k += 1
                # draw as two collinear pieces to exercise chain merging
                mid = (y0 + y1) / 2
                sh.draw_line((x, y0), (x, mid))
                sh.finish(color=(0, 0, 0), width=1.0)
                sh.draw_line((x, mid), (x, y1))
                sh.finish(color=(0, 0, 0), width=1.0)
                page.insert_text((x - 4, mid + 14), sec, fontsize=6, rotate=90)
                truth.append(
                    _member(
                        sec,
                        "beam",
                        level,
                        None,
                        None,
                        bay_ft * 12,
                        note=f"infill {n} in bay {letters[j]}-{letters[j + 1]}/{i + 1}-{i + 2}",
                    )
                )
    # a dimension string under the plan for the first bay (corroborates scale)
    dy = ys[-1] + 50
    sh.draw_line((xs[0], dy), (xs[1], dy))
    sh.finish(color=(0, 0, 0), width=0.4)
    for x in (xs[0], xs[1]):
        sh.draw_line((x, dy - 5), (x, dy + 5))
        sh.finish(color=(0, 0, 0), width=0.4)
    page.insert_text(((xs[0] + xs[1]) / 2 - 14, dy - 3), inches_to_ft_in(bay_ft * 12), fontsize=6)

    # beam schedule block (should be classified as schedule entries, not members)
    bx, by = xs[-1] + 120, oy
    page.insert_text((bx, by - 14), "BEAM SCHEDULE", fontsize=8)
    for r, (mark, sec) in enumerate(
        [("B1", "W18X35"), ("B2", "W16X26"), ("B3", "W18X40"), ("G1", "W24X76")]
    ):
        page.insert_text((bx, by + r * 12), mark, fontsize=6)
        page.insert_text((bx + 40, by + r * 12), sec, fontsize=6)
    # general note with a designation inside (should be NOTE context)
    page.insert_text(
        (bx, by + 80), "NOTES: ALL LINTELS W8X10 TYP. UNLESS NOTED OTHERWISE.", fontsize=6
    )

    # title block (right strip)
    tbx = SHEET_W - 200
    sh.draw_rect(pymupdf.Rect(tbx, 20, SHEET_W - 20, SHEET_H - 20))
    sh.finish(color=(0, 0, 0), width=1.0)
    page.insert_text((tbx + 12, SHEET_H - 160), "SYNTHETIC PROJECT — FFS GOLDEN 0", fontsize=8)
    page.insert_text((tbx + 12, SHEET_H - 130), f"{level} FRAMING PLAN", fontsize=10)
    page.insert_text((tbx + 12, SHEET_H - 110), f"SCALE: {SCALE_TXT}", fontsize=7)
    page.insert_text((tbx + 12, SHEET_H - 60), sheet_no, fontsize=18)
    sh.commit()

    pdf_path = out_dir / "sheet.pdf"
    doc.save(pdf_path)
    doc.close()
    (out_dir / "truth.json").write_text(
        json.dumps(
            {
                "project": out_dir.name,
                "sheets": [
                    {
                        "file": "sheet.pdf",
                        "page": 1,
                        "sheet_no": sheet_no,
                        "level": level,
                        "scale": SCALE_TXT,
                    }
                ],
                "members": truth,
                "distractors": {"schedule_entries": 4, "note_designations": 1},
            },
            indent=1,
        )
    )
    return pdf_path


def _member(
    sec: str, typ: str, level: str, sg: str | None, eg: str | None, length_in: float, note: str = ""
) -> dict:
    return {
        "level": level,
        "section": sec,
        "type": typ,
        "start_grid": sg,
        "end_grid": eg,
        "length_in": round(length_in, 2),
        "status": "new",
        "note": note,
    }


def score(truth_path: str | Path, members: list[dict]) -> dict:
    """Match predicted members to truth by (level, section) with greedy length matching.

    Returns detection recall/precision, designation accuracy, length error stats, duplicate rate.
    """
    truth = json.loads(Path(truth_path).read_text())["members"]
    pool = [dict(t, used=False) for t in truth]
    matched = 0
    dup = 0
    errs: list[float] = []
    fp: list[dict] = []
    for p in members:
        if p.get("review_state") == "excluded":
            continue
        best = None
        for t in pool:
            if t["used"] or t["level"] != p["level"] or t["section"] != p["canonical_section"]:
                continue
            if p.get("length_in") is None:
                cand_err = math.inf
            else:
                cand_err = abs(p["length_in"] - t["length_in"]) / t["length_in"]
            if best is None or cand_err < best[0]:
                best = (cand_err, t)
        if best is None:
            # same section/level exists but every copy is already matched → duplicate; else FP
            if any(
                t["level"] == p["level"] and t["section"] == p["canonical_section"] for t in pool
            ):
                dup += 1
            else:
                fp.append(p)
            continue
        err, t = best
        t["used"] = True
        matched += 1
        if err != math.inf:
            errs.append(err)
    fn = [t for t in pool if not t["used"]]
    n_pred = len([m for m in members if m.get("review_state") != "excluded"])
    errs_sorted = sorted(errs)
    p95 = errs_sorted[int(0.95 * (len(errs_sorted) - 1))] if errs_sorted else None
    return {
        "truth_members": len(truth),
        "predicted": n_pred,
        "matched": matched,
        "recall": round(matched / len(truth), 4) if truth else None,
        "precision": round(matched / n_pred, 4) if n_pred else None,
        "duplicates": dup,
        "false_positives": len(fp),
        "false_negatives": len(fn),
        "length_median_err": round(errs_sorted[len(errs_sorted) // 2], 5) if errs_sorted else None,
        "length_p95_err": round(p95, 5) if p95 is not None else None,
        "length_over_2pct": sum(1 for e in errs if e > 0.02),
        "fp_detail": [
            {
                "section": m["canonical_section"],
                "mark": m["member_mark"],
                "sheet": m.get("sheet_no"),
            }
            for m in fp
        ],
        "fn_detail": [
            {
                "section": t["section"],
                "grids": f"{t['start_grid']}→{t['end_grid']}",
                "note": t["note"],
            }
            for t in fn
        ],
    }
