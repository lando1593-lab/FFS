"""Quantity engine (Milestone 4): surface area, theoretical volume, adjusted volume, bags.

Rules (CLAUDE.md 1, 2, 5):
* Surface area per foot comes from one of three cited sources, in this order: the AISC Shapes
  Database dimensions through the stated perimeter formula; the heated perimeter implied by the
  printed W/D on the very chart row that gave the thickness (D = W / (W/D), the manufacturer's
  own practice in its estimating workbooks); a manufacturer workbook's printed sq ft per lf.
  Nothing else. A member with none of these gets UNKNOWN — REVIEW REQUIRED.
* Theoretical quantities and adjusted (waste-applied) quantities are separate numbers; the
  waste factor and the yield are explicit inputs with a source, never defaults.
* Every number is a CALCULATION with its inputs and method.
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from dataclasses import dataclass, field

from ffs.design.thickness import UNKNOWN

_WEIGHT = re.compile(r"^(?:W|S|M|HP|C|MC|WT|ST|MT)\d+(?:\.\d+)?X(\d+(?:\.\d+)?)$")
_HSS = re.compile(r"^HSS(\d+(?:\.\d+)?)X(\d+(?:\.\d+)?)X(\d+/\d+|\d*\.\d+)$")
_HSS_ROUND = re.compile(r"^HSS(\d+(?:\.\d+)?)X(\d+/\d+|\d*\.\d+)$")
_ANGLE = re.compile(r"^L(\d+(?:-\d+/\d+|\.\d+)?)X(\d+(?:-\d+/\d+|\.\d+)?)X(\d+/\d+|\d*\.\d+)$")


def _num(s: str) -> float:
    from fractions import Fraction

    if "-" in s:
        w, f = s.split("-")
        return float(w) + float(Fraction(f))
    if "/" in s:
        return float(Fraction(s))
    return float(s)


def nominal_weight_plf(canonical: str) -> float | None:
    """The weight printed in a W/S/C-type designation (W12X26 → 26 plf); None otherwise."""
    m = _WEIGHT.match(canonical.upper())
    return float(m.group(1)) if m else None


@dataclass
class SurfaceBasis:
    sf_per_lf: float
    perimeter_in: float
    method: str  # aisc_dimensions / chart_wd / workbook_sf / nominal_geometry
    basis: str  # "3-sided contour" / "4-sided contour" / "box" / "nominal tube perimeter"
    source: dict
    inputs: dict
    notes: list[str] = field(default_factory=list)


def perimeter_from_dimensions(
    d: float, bf: float, tw: float, sides: int, profile: str = "contour"
) -> tuple[float, str]:
    """Heated perimeter of a wide-flange section (inches).

    contour, 4 sides: 2d + 4bf − 2tw;  contour, 3 sides (one flange against a deck or slab):
    2d + 3bf − 2tw;  box, 4 sides: 2d + 2bf;  box, 3 sides: 2d + bf. These are the perimeter
    definitions the UL designs give for W/D (D = heated perimeter) and are pure geometry."""
    if profile == "box":
        return (2 * d + 2 * bf, "4-sided box") if sides == 4 else (2 * d + bf, "3-sided box")
    if sides == 4:
        return 2 * d + 4 * bf - 2 * tw, "4-sided contour"
    return 2 * d + 3 * bf - 2 * tw, "3-sided contour"


def surface_basis(
    canonical: str,
    sides: int,
    thickness_source: dict | None,
    thickness_inputs: dict | None,
    aisc=None,
    workbook_sf: dict | None = None,
    profile: str = "contour",
) -> SurfaceBasis | None:
    can = canonical.upper()
    shape = aisc.get(can) if aisc is not None else None
    if shape is not None and shape.depth_in and shape.bf_in and shape.tw_in and can[0] in "WSMH":
        p, basis = perimeter_from_dimensions(
            shape.depth_in, shape.bf_in, shape.tw_in, sides, profile
        )
        return SurfaceBasis(
            p / 12,
            p,
            "aisc_dimensions",
            basis,
            {"document": shape.source, "label": shape.label},
            {
                "d": shape.depth_in,
                "bf": shape.bf_in,
                "tw": shape.tw_in,
                "sides": sides,
                "profile": profile,
            },
        )
    inputs = thickness_inputs or {}
    src = thickness_source or {}
    ratio, kind = inputs.get("ratio"), inputs.get("ratio_kind")
    weight = nominal_weight_plf(can)
    if ratio and kind == "W/D" and weight:
        p = weight / ratio
        basis = (
            "4-sided contour"
            if src.get("section") is None and "column" in (src.get("condition") or "").lower()
            else "chart basis"
        )
        if "column" in (src.get("condition") or "").lower():
            basis = "4-sided contour (column chart)"
        elif src.get("section") or src.get("design"):
            basis = (
                "3-sided contour (beam chart)" if sides == 3 else "chart basis (sides as printed)"
            )
        unc = 100 * 0.005 / ratio
        notes = [
            f"D = W / (W/D), W/D printed to two decimals: perimeter uncertainty about ±{unc:.1f}%"
        ]
        if sides == 4 and "beam" in basis:
            notes.append("4-sided exposure requested but the chart row is a 3-sided beam basis")
        return SurfaceBasis(
            p / 12,
            p,
            "chart_wd",
            basis,
            {
                k: v
                for k, v in src.items()
                if k in ("document", "design", "chart_date", "condition", "section", "row", "page")
            },
            {"weight_plf": weight, "W/D": ratio, "sides": sides},
            notes,
        )
    m = _HSS.match(can)
    if m:
        a, b = _num(m.group(1)), _num(m.group(2))
        p = 2 * (a + b) if sides == 4 else a + 2 * b
        return SurfaceBasis(
            p / 12,
            p,
            "nominal_geometry",
            f"{sides}-sided nominal tube perimeter",
            {"label": can},
            {"a": a, "b": b, "sides": sides},
            ["outside dimensions nominal; corner radii ignored"],
        )
    m = _HSS_ROUND.match(can)
    if m:
        od = _num(m.group(1))
        p = math.pi * od
        return SurfaceBasis(
            p / 12, p, "nominal_geometry", "round outside perimeter", {"label": can}, {"od": od}
        )
    m = _ANGLE.match(can)
    if m:
        a, b, t = _num(m.group(1)), _num(m.group(2)), _num(m.group(3))
        p = 2 * a + 2 * b - 2 * t
        return SurfaceBasis(
            p / 12,
            p,
            "nominal_geometry",
            "angle contour (both faces of each leg)",
            {"label": can},
            {"a": a, "b": b, "t": t},
        )
    if workbook_sf and can in workbook_sf:
        sf, info = workbook_sf[can]
        return SurfaceBasis(
            sf, sf * 12, "workbook_sf", info.get("basis", "workbook"), info, {"sf_per_lf": sf}
        )
    return None


@dataclass
class MemberQuantity:
    member_id: str
    canonical: str
    level: str | None
    role: str | None
    sides: int
    sides_source: str  # condition_assignment / assumed
    length_ft: float | None
    thickness_in: float | None
    design: str | None
    product: str | None
    basis: SurfaceBasis | None
    sq_ft: float | None
    bd_ft: float | None  # sq ft × thickness in inches (board feet)
    status: str  # ok / no_length / no_thickness / no_surface_basis
    notes: list[str] = field(default_factory=list)


@dataclass
class QuantitySet:
    scenario_id: str
    rows: list[MemberQuantity]
    waste_pct: float | None
    waste_source: str | None
    yield_bdft_per_bag: float | None
    yield_source: str | None
    totals: dict = field(default_factory=dict)
    by_condition: dict = field(default_factory=dict)
    by_level: dict = field(default_factory=dict)
    unresolved: int = 0

    def adjusted(self, bd_ft: float) -> float | None:
        return None if self.waste_pct is None else bd_ft * (1 + self.waste_pct / 100)


def _key(r: MemberQuantity) -> str:
    thk = "—" if r.thickness_in is None else f"{r.thickness_in:g} in"
    return f"{r.design or '?'} | {r.product or '?'} | {thk} | {r.sides} sides"


def member_quantity(
    member_id,
    canonical,
    level,
    role,
    length_in,
    thickness_in,
    design,
    product,
    thickness_source,
    thickness_inputs,
    sides=None,
    sides_source="assumed",
    aisc=None,
    workbook_sf=None,
) -> MemberQuantity:
    notes: list[str] = []
    if sides is None:
        sides = 4 if (role or "").startswith("column") else 3
        sides_source = "assumed"
        notes.append(
            f"sides assumed {sides} from role {role!r} (ASSUMPTION; no condition assignment)"
        )
    basis = surface_basis(canonical, sides, thickness_source, thickness_inputs, aisc, workbook_sf)
    length_ft = None if length_in is None else length_in / 12
    status = "ok"
    if length_in is None:
        status = "no_length"
    elif thickness_in is None:
        status = "no_thickness"
    elif basis is None:
        status = "no_surface_basis"
    sq_ft = bd_ft = None
    if status == "ok":
        sq_ft = round(basis.sf_per_lf * length_ft, 3)
        bd_ft = round(sq_ft * thickness_in, 3)
    return MemberQuantity(
        member_id,
        canonical,
        level,
        role,
        sides,
        sides_source,
        length_ft,
        thickness_in,
        design,
        product,
        basis,
        sq_ft,
        bd_ft,
        status,
        notes + (basis.notes if basis else []),
    )


def aggregate(
    rows: list[MemberQuantity],
    scenario_id: str,
    waste_pct: float | None = None,
    waste_source: str | None = None,
    yield_bdft_per_bag: float | None = None,
    yield_source: str | None = None,
) -> QuantitySet:
    qs = QuantitySet(scenario_id, rows, waste_pct, waste_source, yield_bdft_per_bag, yield_source)
    lf = sum(r.length_ft or 0 for r in rows if r.status == "ok")
    sq = sum(r.sq_ft or 0 for r in rows if r.status == "ok")
    bd = sum(r.bd_ft or 0 for r in rows if r.status == "ok")
    qs.unresolved = sum(1 for r in rows if r.status != "ok")
    adj = qs.adjusted(bd)
    qs.totals = {
        "members": len(rows),
        "members_quantified": len(rows) - qs.unresolved,
        "linear_ft": round(lf, 1),
        "sq_ft": round(sq, 1),
        "bd_ft_theoretical": round(bd, 1),
        "bd_ft_adjusted": None if adj is None else round(adj, 1),
        "bags": None
        if adj is None or not yield_bdft_per_bag
        else math.ceil(adj / yield_bdft_per_bag),
        "bags_theoretical": None if not yield_bdft_per_bag else math.ceil(bd / yield_bdft_per_bag),
    }
    cond: dict[str, dict] = defaultdict(
        lambda: {"members": 0, "linear_ft": 0.0, "sq_ft": 0.0, "bd_ft_theoretical": 0.0}
    )
    lvl: dict[str, dict] = defaultdict(
        lambda: {"members": 0, "linear_ft": 0.0, "sq_ft": 0.0, "bd_ft_theoretical": 0.0}
    )
    for r in rows:
        if r.status != "ok":
            continue
        for bucket in (cond[_key(r)], lvl[r.level or "?"]):
            bucket["members"] += 1
            bucket["linear_ft"] += r.length_ft
            bucket["sq_ft"] += r.sq_ft
            bucket["bd_ft_theoretical"] += r.bd_ft
    for b in list(cond.values()) + list(lvl.values()):
        for k in ("linear_ft", "sq_ft", "bd_ft_theoretical"):
            b[k] = round(b[k], 1)
        b["bd_ft_adjusted"] = (
            None if waste_pct is None else round(b["bd_ft_theoretical"] * (1 + waste_pct / 100), 1)
        )
    qs.by_condition = dict(cond)
    qs.by_level = dict(lvl)
    return qs


def value_or_unknown(x) -> str:
    return UNKNOWN if x is None else f"{x:g}"
