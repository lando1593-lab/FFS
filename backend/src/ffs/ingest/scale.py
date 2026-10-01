"""Drawing scale detection and calibration.

A scale is expressed as ``inches_per_point``: real-world inches represented by one PDF point.
For an architectural scale ``1/8" = 1'-0"`` on an unresized sheet:
    1/8 paper-inch → 12 real inches  ⇒  1 paper-inch → 96 real inches  ⇒  1 pt → 96/72 real in.

Nothing here is trusted alone. Candidates carry confidence and a source; corroboration with
explicit dimension strings (``verify_with_dimension``) raises confidence; manual calibration is a
HUMAN_OVERRIDE recorded with its two picked points.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from fractions import Fraction

from ffs.core.units import parse_dimension_to_inches

POINTS_PER_INCH = 72.0


@dataclass
class ScaleCandidate:
    inches_per_point: float
    label: str  # normalized human text, e.g. 1/8"=1'-0"
    source: str  # "scale_text" | "dimension_check" | "manual" | "grid_spacing"
    confidence: float
    evidence: str = ""  # raw matched text or description
    bbox: tuple[float, float, float, float] | None = None

    @property
    def paper_inches_per_foot(self) -> float:
        # how many paper inches represent one real foot
        return 12.0 / (self.inches_per_point * POINTS_PER_INCH)


_ARCH_SCALE = re.compile(
    r"""(?P<num>\d+(?:[ -]\d+/\d+)?|\d+/\d+|\d*\.\d+)\s*(?:"|”|''|in\.?)?\s*=\s*
        (?P<ft>\d+)\s*(?:'|’|ft\.?)\s*(?:-\s*(?P<in>\d+)\s*(?:"|”|'')?)?""",
    re.IGNORECASE | re.VERBOSE,
)
_RATIO_SCALE = re.compile(r"(?<![\d.])1\s*[:/]\s*(?P<r>\d{2,5})(?![\d.])")
_NTS = re.compile(r"\b(N\.?T\.?S\.?|NOT TO SCALE)\b", re.IGNORECASE)


def _num(s: str) -> float:
    s = s.strip()
    if " " in s or ("-" in s and "/" in s):
        whole, frac = re.split(r"[ -]", s, maxsplit=1)
        return float(whole) + float(Fraction(frac))
    if "/" in s:
        return float(Fraction(s))
    return float(s)


def parse_scale_text(text: str) -> ScaleCandidate | None:
    """Parse ``1/8" = 1'-0"``, ``3/16"=1'``, ``1:100``, ``1"=20'`` into a ScaleCandidate.

    Returns None for NTS or unparseable text.
    """
    if _NTS.search(text):
        return None
    m = _ARCH_SCALE.search(text)
    if m:
        paper_in = _num(m.group("num"))
        real_in = int(m.group("ft")) * 12 + int(m.group("in") or 0)
        if paper_in <= 0 or real_in <= 0:
            return None
        ipp = (real_in / paper_in) / POINTS_PER_INCH
        label = f'{m.group("num").strip()}"={m.group("ft")}\'-{int(m.group("in") or 0)}"'
        return ScaleCandidate(ipp, label, "scale_text", 0.75, evidence=m.group(0))
    m = _RATIO_SCALE.search(text)
    if m:
        r = int(m.group("r"))
        # 1:r means 1 paper unit = r real units; in inches: 1 pt = r/72 in
        return ScaleCandidate(r / POINTS_PER_INCH, f"1:{r}", "scale_text", 0.7, evidence=m.group(0))
    return None


def scale_from_points(
    p0: tuple[float, float], p1: tuple[float, float], real_inches: float, source: str = "manual"
) -> ScaleCandidate:
    """Calibrate from two picked points and the real distance between them (inches)."""
    dist = ((p1[0] - p0[0]) ** 2 + (p1[1] - p0[1]) ** 2) ** 0.5
    if dist <= 0 or real_inches <= 0:
        raise ValueError("calibration needs two distinct points and a positive distance")
    ipp = real_inches / dist
    conf = 0.98 if source == "manual" else 0.85
    return ScaleCandidate(
        ipp,
        f"calibrated {real_inches:.2f} in over {dist:.1f} pt",
        source,
        conf,
        evidence=f"{p0}->{p1}",
    )


def verify_with_dimension(
    cand: ScaleCandidate, measured_points: float, dimension_text: str, tol: float = 0.01
) -> tuple[bool, float]:
    """Check a scale candidate against an explicit dimension string spanning ``measured_points``.

    Returns (agrees, relative_error). ``agrees`` within ``tol`` (1% default).
    """
    real = parse_dimension_to_inches(dimension_text)
    if real is None or real <= 0 or measured_points <= 0:
        return (False, float("inf"))
    predicted = measured_points * cand.inches_per_point
    err = abs(predicted - real) / real
    return (err <= tol, err)


def points_to_inches(points: float, cand: ScaleCandidate) -> float:
    return points * cand.inches_per_point
