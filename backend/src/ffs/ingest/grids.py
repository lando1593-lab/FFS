"""Grid bubble and grid line detection.

A grid bubble is a short label (``A``..``ZZ`` or ``1``..``99``) centered inside a circle. A grid
line is a long segment that passes through the bubble center and is roughly perpendicular to the
sheet edge the bubble sits near. The result is a coordinate frame used to express member ends as
``C/5``-style references and later to drive shop drawings.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from ffs.ingest.pdf import PageData, Segment

_LABEL = re.compile(r"^(?:[A-Z]{1,2}|\d{1,2}|[A-Z]\.\d|[A-Z]\d)$")


@dataclass
class GridLine:
    label: str
    axis: str  # "x" for vertical lines (numbers/letters along the top), "y" for horizontal lines
    coord: float  # x for axis "x", y for axis "y" (page points)
    x0: float
    y0: float
    x1: float
    y1: float
    confidence: float
    bubble_center: tuple[float, float]


def _point_segment_distance(px: float, py: float, s: Segment) -> float:
    dx, dy = s.x1 - s.x0, s.y1 - s.y0
    if dx == 0 and dy == 0:
        return math.hypot(px - s.x0, py - s.y0)
    t = ((px - s.x0) * dx + (py - s.y0) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return math.hypot(px - (s.x0 + t * dx), py - (s.y0 + t * dy))


def detect_grids(page: PageData, min_line_len: float = 100.0) -> list[GridLine]:
    out: list[GridLine] = []
    if not page.circles:
        return out
    long_segs = [s for s in page.segments if s.length >= min_line_len]
    for sp in page.spans:
        t = sp.text.strip()
        if not _LABEL.match(t):
            continue
        cx, cy = sp.center
        circ = next(
            (c for c in page.circles if math.hypot(c.cx - cx, c.cy - cy) <= c.r * 0.6 and c.r >= 4),
            None,
        )
        if circ is None:
            continue
        best: tuple[float, Segment] | None = None
        for s in long_segs:
            ang = s.angle_deg
            vertical = abs(ang - 90) < 3
            horizontal = ang < 3 or ang > 177
            if not (vertical or horizontal):
                continue
            # line should start/end near the bubble (within ~2 radii) and be collinear with center
            d_line = _point_segment_distance(circ.cx, circ.cy, s)
            end_d = min(
                math.hypot(s.x0 - circ.cx, s.y0 - circ.cy),
                math.hypot(s.x1 - circ.cx, s.y1 - circ.cy),
            )
            if d_line <= circ.r * 2.5 and end_d <= circ.r * 4:
                score = d_line + end_d * 0.25
                if best is None or score < best[0]:
                    best = (score, s)
        if best is None:
            continue
        s = best[1]
        vertical = abs(s.angle_deg - 90) < 3
        out.append(
            GridLine(
                label=t,
                axis="x" if vertical else "y",
                coord=(s.x0 + s.x1) / 2 if vertical else (s.y0 + s.y1) / 2,
                x0=s.x0,
                y0=s.y0,
                x1=s.x1,
                y1=s.y1,
                confidence=0.9 if best[0] < circ.r else 0.7,
                bubble_center=(circ.cx, circ.cy),
            )
        )
    # de-duplicate: same label + axis → keep highest confidence
    uniq: dict[tuple[str, str], GridLine] = {}
    for g in out:
        k = (g.label, g.axis)
        if k not in uniq or g.confidence > uniq[k].confidence:
            uniq[k] = g
    return sorted(uniq.values(), key=lambda g: (g.axis, g.coord))


def nearest_grid_ref(
    x: float, y: float, grids: list[GridLine], tol: float = 12.0
) -> tuple[str | None, float]:
    """Return ``"C/5"``-style reference for a point if it lies within ``tol`` points of both a
    vertical and a horizontal grid line, else the single nearest axis label, else None.
    Second element is the distance of the worse of the two matches."""
    vx = [(abs(g.coord - x), g) for g in grids if g.axis == "x"]
    hy = [(abs(g.coord - y), g) for g in grids if g.axis == "y"]
    bx = min(vx, default=None, key=lambda t: t[0])
    by = min(hy, default=None, key=lambda t: t[0])
    labels: list[str] = []
    worst = 0.0
    for b in (bx, by):
        if b is not None and b[0] <= tol:
            labels.append(b[1].label)
            worst = max(worst, b[0])
    if not labels:
        return (None, float("inf"))
    # Convention: letters first, then numbers, joined by "/"
    labels.sort(key=lambda s: (not s[0].isalpha(), s))
    return ("/".join(labels), worst)
