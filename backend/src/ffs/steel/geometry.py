"""Associate plan labels with member geometry and compute lengths.

Algorithm (deterministic, documented so the estimator can audit it):
1. Merge collinear, touching vector segments *of the same line style* into chains (CAD exporters
   split lines; grid lines are usually thin/dashed and must not merge with the beam on top of
   them).
2. Split chains at supports: column symbols (small closed squares) and, for chains lying on a
   grid line, grid intersections. A beam framing INTO a girder (T-junction) does not split the
   girder. Each split is recorded in the reasoning as an interpretation.
3. For a label with rotation ``r``, candidate pieces are those within ``angle_tol`` of ``r``
   (text is written along the member), at least ``min_len`` long, whose perpendicular distance
   from the label center is within ``max_offset`` (scaled by text size), and whose extent
   contains the label's projection (with slack).
4. Pieces that are the grid line itself are excluded.
5. The best candidate is the closest; geometry confidence falls with the number of competing
   candidates and with distance.
6. Length = piece length × inches_per_point. Length confidence = geometry × scale confidence,
   raised when a parallel dimension string agrees within 2%.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ffs.core.units import parse_dimension_to_inches
from ffs.ingest.grids import GridLine, nearest_grid_ref
from ffs.ingest.pdf import PageData, Segment, TextSpan
from ffs.ingest.scale import ScaleCandidate
from ffs.steel.labels import MemberLabel


@dataclass
class Chain:
    x0: float
    y0: float
    x1: float
    y1: float
    width: float
    dashed: bool
    parts: int = 1
    split_reason: str = ""

    @property
    def length(self) -> float:
        return math.hypot(self.x1 - self.x0, self.y1 - self.y0)

    @property
    def angle_deg(self) -> float:
        return math.degrees(math.atan2(self.y1 - self.y0, self.x1 - self.x0)) % 180.0


@dataclass
class GeometryMatch:
    label: MemberLabel
    chain: Chain | None
    length_in: float | None
    geometry_confidence: float
    length_confidence: float
    start_grid: str | None = None
    end_grid: str | None = None
    competing: int = 0
    reasoning: str = ""
    dimension_corroboration: str | None = None
    notes: list[str] = field(default_factory=list)


def _angle_diff(a: float, b: float) -> float:
    d = abs(a - b) % 180.0
    return min(d, 180.0 - d)


def _flush(
    group: list[tuple[tuple[float, float, float], Segment]],
    ux: float,
    uy: float,
    nx: float,
    ny: float,
) -> Chain:
    off = sum(k[0] for k, _ in group) / len(group)
    t0 = min(k[1] for k, _ in group)
    t1 = max(k[2] for k, _ in group)
    return Chain(
        x0=ux * t0 + nx * off,
        y0=uy * t0 + ny * off,
        x1=ux * t1 + nx * off,
        y1=uy * t1 + ny * off,
        width=max(s.width for _, s in group),
        dashed=all(s.dashed for _, s in group),
        parts=len(group),
    )


def merge_collinear(
    segments: list[Segment], gap: float = 1.5, offset: float = 0.75, width_tol: float = 0.35
) -> list[Chain]:
    """Merge touching collinear segments of the same style into chains."""
    buckets: dict[tuple[int, bool, int], list[Segment]] = {}
    for s in segments:
        if s.length < 0.5:
            continue
        key = (int(round(s.angle_deg / 2.0)) % 90, s.dashed, int(round(s.width / width_tol)))
        buckets.setdefault(key, []).append(s)
    chains: list[Chain] = []
    for segs in buckets.values():
        a = math.radians(segs[0].angle_deg)
        ux, uy = math.cos(a), math.sin(a)
        nx, ny = -uy, ux
        items: list[tuple[tuple[float, float, float], Segment]] = []
        for s in segs:
            off = s.x0 * nx + s.y0 * ny
            t0, t1 = s.x0 * ux + s.y0 * uy, s.x1 * ux + s.y1 * uy
            items.append(((off, min(t0, t1), max(t0, t1)), s))
        items.sort(key=lambda t: (t[0][0], t[0][1]))
        cur: list[tuple[tuple[float, float, float], Segment]] = []
        cur_end = -math.inf
        for k, s in items:
            if cur and abs(k[0] - cur[-1][0][0]) <= offset and k[1] <= cur_end + gap:
                cur.append((k, s))
                cur_end = max(cur_end, k[2])
            else:
                if cur:
                    chains.append(_flush(cur, ux, uy, nx, ny))
                cur = [(k, s)]
                cur_end = k[2]
        if cur:
            chains.append(_flush(cur, ux, uy, nx, ny))
    return chains


def column_symbols(
    page: PageData, max_size: float = 14.0, min_size: float = 2.0
) -> list[tuple[float, float]]:
    """Centers of small closed squares — the usual plan symbol for a column."""
    pts: list[tuple[float, float]] = []
    seen: set[tuple[int, int]] = set()
    # tiny rectangles arrive as 4 edges; find pairs of short perpendicular segments sharing corners
    short = [s for s in page.segments if min_size <= s.length <= max_size]
    by_corner: dict[tuple[int, int], int] = {}
    for s in short:
        for x, y in ((s.x0, s.y0), (s.x1, s.y1)):
            by_corner[(round(x), round(y))] = by_corner.get((round(x), round(y)), 0) + 1
    for s in short:
        cx, cy = (s.x0 + s.x1) / 2, (s.y0 + s.y1) / 2
        # a square edge has both corners shared with other short edges
        if (
            by_corner.get((round(s.x0), round(s.y0)), 0) >= 2
            and by_corner.get((round(s.x1), round(s.y1)), 0) >= 2
        ):
            key = (round(cx / 6), round(cy / 6))
            if key not in seen:
                seen.add(key)
                pts.append((cx, cy))
    # cluster edge midpoints into square centers (mean of all edges in the cluster)
    clusters: list[list[tuple[float, float]]] = []
    for x, y in pts:
        for cl in clusters:
            cx = sum(a for a, _ in cl) / len(cl)
            cy = sum(b for _, b in cl) / len(cl)
            if abs(cx - x) <= max_size and abs(cy - y) <= max_size:
                cl.append((x, y))
                break
        else:
            clusters.append([(x, y)])
    return [(sum(a for a, _ in cl) / len(cl), sum(b for _, b in cl) / len(cl)) for cl in clusters]


def _perp_distance_and_t(px: float, py: float, c: Chain) -> tuple[float, float]:
    dx, dy = c.x1 - c.x0, c.y1 - c.y0
    L2 = dx * dx + dy * dy
    if L2 == 0:
        return (math.hypot(px - c.x0, py - c.y0), 0.0)
    t = ((px - c.x0) * dx + (py - c.y0) * dy) / L2
    perp = abs((px - c.x0) * dy - (py - c.y0) * dx) / math.sqrt(L2)
    return (perp, t)


def _on_grid(c: Chain, grids: list[GridLine], tol: float = 1.5) -> GridLine | None:
    for g in grids:
        if g.axis == "x" and abs(c.angle_deg - 90) < 2 and abs(c.x0 - g.coord) <= tol:
            return g
        if g.axis == "y" and _angle_diff(c.angle_deg, 0) < 2 and abs(c.y0 - g.coord) <= tol:
            return g
    return None


def _is_grid_line_itself(c: Chain, g: GridLine) -> bool:
    glen = math.hypot(g.x1 - g.x0, g.y1 - g.y0)
    return c.length >= 0.9 * glen and (c.dashed or c.width <= 0.5)


def split_at_supports(
    chains: list[Chain],
    supports: list[tuple[float, float]],
    grids: list[GridLine],
    min_piece: float = 6.0,
) -> list[Chain]:
    """Split each chain at support points lying on it (columns; grid intersections when the chain
    runs along a grid line). Chain ends within ``min_piece`` of a support are not split."""
    out: list[Chain] = []
    for c in chains:
        cut_ts: list[tuple[float, str]] = []
        for sx, sy in supports:
            perp, t = _perp_distance_and_t(sx, sy, c)
            if perp <= 3.0 and 0 < t < 1:
                cut_ts.append((t, "column symbol"))
        g = _on_grid(c, grids)
        if g is not None:
            for o in grids:
                if o.axis == g.axis:
                    continue
                px, py = (o.coord, c.y0) if o.axis == "x" else (c.x0, o.coord)
                perp, t = _perp_distance_and_t(px, py, c)
                if perp <= 3.0 and 0 < t < 1:
                    cut_ts.append((t, f"grid intersection {o.label}"))
        if not cut_ts:
            out.append(c)
            continue
        L = c.length
        # prefer exact grid-intersection cuts; drop column cuts within 4pt of one
        grid_cuts = [t for t, why in cut_ts if why.startswith("grid")]
        cut_ts = [
            (t, why)
            for t, why in cut_ts
            if why.startswith("grid") or all(abs(t - g) * L > 4.0 for g in grid_cuts)
        ]
        cut_ts.sort()
        pts = [0.0]
        reasons: list[str] = []
        for t, why in cut_ts:
            if (t - pts[-1]) * L >= min_piece and (1 - t) * L >= min_piece:
                pts.append(t)
                reasons.append(why)
        pts.append(1.0)
        dx, dy = c.x1 - c.x0, c.y1 - c.y0
        for a, b in zip(pts, pts[1:], strict=False):
            out.append(
                Chain(
                    x0=c.x0 + dx * a,
                    y0=c.y0 + dy * a,
                    x1=c.x0 + dx * b,
                    y1=c.y0 + dy * b,
                    width=c.width,
                    dashed=c.dashed,
                    parts=c.parts,
                    split_reason=("split at " + ", ".join(sorted(set(reasons)))) if reasons else "",
                )
            )
    return out


def _crossings(c: Chain, others: list[Chain], grids: list[GridLine]) -> list[tuple[float, str]]:
    """Parameter t (0..1) along ``c`` where another chain (angle differing by >30°) or a grid
    line crosses or terminates on it."""
    out: list[tuple[float, str]] = []
    dx, dy = c.x1 - c.x0, c.y1 - c.y0
    for o in others:
        if o is c or _angle_diff(o.angle_deg, c.angle_deg) < 30:
            continue
        ex, ey = o.x1 - o.x0, o.y1 - o.y0
        den = dx * ey - dy * ex
        if abs(den) < 1e-9:
            continue
        t = ((o.x0 - c.x0) * ey - (o.y0 - c.y0) * ex) / den
        u = ((o.x0 - c.x0) * dy - (o.y0 - c.y0) * dx) / den
        slack = 3.0 / max(o.length, 1.0)
        if 0 < t < 1 and -slack <= u <= 1 + slack:
            out.append((t, "crossing member"))
    for g in grids:
        if g.axis == "x" and abs(dx) > 1e-6:
            t = (g.coord - c.x0) / dx
        elif g.axis == "y" and abs(dy) > 1e-6:
            t = (g.coord - c.y0) / dy
        else:
            continue
        if 0 < t < 1:
            out.append((t, f"grid {g.label}"))
    return out


def split_by_labels(
    chains: list[Chain], labels: list[MemberLabel], grids: list[GridLine], angle_tol: float = 3.0
) -> list[Chain]:
    """A chain carrying k parallel labels is k members (INTERPRETATION). Split between consecutive
    labels at the crossing member/grid nearest the midpoint; at the midpoint itself if nothing
    crosses there (flagged in ``split_reason``)."""
    out: list[Chain] = []
    for c in chains:
        ts: list[float] = []
        for lab in labels:
            if _angle_diff(c.angle_deg, lab.span.rotation_deg % 180.0) > angle_tol:
                continue
            perp, t = _perp_distance_and_t(*lab.span.center, c)
            if perp <= max(10.0, lab.span.size * 2.5) and 0 <= t <= 1:
                ts.append(t)
        ts.sort()
        if len(ts) < 2:
            out.append(c)
            continue
        cross = _crossings(c, chains, grids)
        cuts: list[tuple[float, str]] = []
        for a, b in zip(ts, ts[1:], strict=False):
            mid = (a + b) / 2
            window = (b - a) * 0.4
            near = [
                (abs(t - mid), t, why) for t, why in cross if a < t < b and abs(t - mid) <= window
            ]
            if near:
                _, t, why = min(near)
                cuts.append((t, f"between labels at {why}"))
            else:
                cuts.append((mid, "between labels at midpoint (no crossing found) — REVIEW"))
        pts = [0.0] + [t for t, _ in cuts] + [1.0]
        dx, dy = c.x1 - c.x0, c.y1 - c.y0
        for i, (a, b) in enumerate(zip(pts, pts[1:], strict=False)):
            why = []
            if i > 0:
                why.append(cuts[i - 1][1])
            if i < len(cuts):
                why.append(cuts[i][1])
            out.append(
                Chain(
                    x0=c.x0 + dx * a,
                    y0=c.y0 + dy * a,
                    x1=c.x0 + dx * b,
                    y1=c.y0 + dy * b,
                    width=c.width,
                    dashed=c.dashed,
                    parts=c.parts,
                    split_reason="; ".join(
                        filter(None, [c.split_reason, "split " + "; ".join(sorted(set(why)))])
                    ),
                )
            )
    return out


def _dimension_spans(page: PageData) -> list[tuple[TextSpan, float]]:
    out = []
    for s in page.spans:
        v = parse_dimension_to_inches(s.text)
        if v is not None and v > 0:
            out.append((s, v))
    return out


def associate(
    page: PageData,
    labels: list[MemberLabel],
    scale: ScaleCandidate | None,
    grids: list[GridLine] | None = None,
    angle_tol: float = 3.0,
    min_len: float = 18.0,
) -> list[GeometryMatch]:
    grids = grids or []
    chains = merge_collinear(page.segments)
    chains = [
        c
        for c in chains
        if not (_on_grid(c, grids) and _is_grid_line_itself(c, _on_grid(c, grids)))
    ]
    chains = split_at_supports(chains, column_symbols(page), grids)
    chains = split_by_labels(chains, labels, grids, angle_tol)
    chains = [c for c in chains if c.length >= min_len]
    dims = _dimension_spans(page)
    out: list[GeometryMatch] = []
    for lab in labels:
        sp = lab.span
        cx, cy = sp.center
        text_rot = sp.rotation_deg % 180.0
        max_offset = max(10.0, sp.size * 2.5)
        cands: list[tuple[float, Chain, float]] = []
        for c in chains:
            if _angle_diff(c.angle_deg, text_rot) > angle_tol:
                continue
            perp, t = _perp_distance_and_t(cx, cy, c)
            if perp > max_offset:
                continue
            if not (-0.15 <= t <= 1.15):
                continue
            cands.append((perp, c, t))
        if not cands:
            out.append(
                GeometryMatch(
                    label=lab,
                    chain=None,
                    length_in=None,
                    geometry_confidence=0.0,
                    length_confidence=0.0,
                    competing=0,
                    reasoning=f"no parallel segment within {max_offset:.0f}pt of label",
                )
            )
            continue
        cands.sort(key=lambda t: t[0])
        perp, chain, _ = cands[0]
        competing = len(cands) - 1
        gconf = 0.9 if competing == 0 else max(0.35, 0.9 - 0.2 * competing)
        if perp > max_offset * 0.6:
            gconf -= 0.1
        if chain.dashed:
            gconf -= 0.1
        reasoning = (
            f"chain {chain.length:.1f}pt at {chain.angle_deg:.1f}°, {perp:.1f}pt from label, "
            f"{competing} competing" + (f"; {chain.split_reason}" if chain.split_reason else "")
        )
        length_in = None
        lconf = 0.0
        corroboration = None
        if scale is not None:
            length_in = chain.length * scale.inches_per_point
            lconf = round(gconf * scale.confidence, 3)
            for ds, val in dims:
                dperp, dt = _perp_distance_and_t(*ds.center, chain)
                if (
                    _angle_diff(ds.rotation_deg % 180, chain.angle_deg) <= angle_tol
                    and dperp <= 60
                    and 0 <= dt <= 1
                    and abs(val - length_in) / max(val, 1) <= 0.02
                ):
                    corroboration = f"dimension '{ds.text}' agrees within 2%"
                    lconf = min(1.0, lconf + 0.1)
                    break
        sg, eg = None, None
        if grids:
            sg, _ = nearest_grid_ref(chain.x0, chain.y0, grids)
            eg, _ = nearest_grid_ref(chain.x1, chain.y1, grids)
        out.append(
            GeometryMatch(
                label=lab,
                chain=chain,
                length_in=length_in,
                geometry_confidence=round(gconf, 3),
                length_confidence=lconf,
                start_grid=sg,
                end_grid=eg,
                competing=competing,
                reasoning=reasoning,
                dimension_corroboration=corroboration,
            )
        )
    return out
