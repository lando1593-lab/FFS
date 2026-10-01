"""Length units and architectural dimension parsing.

Internal storage: inches (float). PDF geometry: points (1/72 in) in page space.
"""

from __future__ import annotations

import re
from fractions import Fraction

_FEET_INCHES = re.compile(
    r"""
    (?P<neg>-)?\s*
    (?:(?P<ft>\d+)\s*(?:'|’|ft\.?|FT\.?))?        # feet
    \s*-?\s*
    (?:
        (?:(?P<inch>\d+)(?:\s*[ -]\s*(?P<num>\d+)/(?P<den>\d+))?|(?P<num2>\d+)/(?P<den2>\d+))
        \s*(?:"|”|''|in\.?|IN\.?)
    )?  # inches: 6", 6 1/2", 1/2"
    """,
    re.VERBOSE,
)


def parse_dimension_to_inches(text: str) -> float | None:
    """Parse strings like ``28'-6"``, ``28' - 6 1/2"``, ``6"``, ``12'`` into inches.

    Returns None when the string is not a clean dimension. Never guesses.
    """
    s = text.strip().replace("’", "'").replace("”", '"').replace("″", '"').replace("′", "'")
    if not s or not re.search(r"[\d]", s):
        return None
    m = _FEET_INCHES.fullmatch(s)
    if not m or all(m.group(k) is None for k in ("ft", "inch", "num", "num2")):
        return None
    total = 0.0
    if m.group("ft"):
        total += int(m.group("ft")) * 12
    if m.group("inch"):
        total += int(m.group("inch"))
    num, den = (
        (m.group("num"), m.group("den")) if m.group("num") else (m.group("num2"), m.group("den2"))
    )
    if num and den:
        total += float(Fraction(int(num), int(den)))
    return -total if m.group("neg") else total


def inches_to_ft_in(inches: float, denom: int = 16) -> str:
    """Format inches as ``28'-6"`` or ``28'-6 1/2"`` rounded to 1/denom inch."""
    sign = "-" if inches < 0 else ""
    inches = abs(inches)
    ft = int(inches // 12)
    rem = inches - ft * 12
    whole = int(rem)
    frac = Fraction(rem - whole).limit_denominator(denom)
    if frac == 1:
        whole += 1
        frac = Fraction(0)
    if whole == 12:
        ft += 1
        whole = 0
    s = f"{sign}{ft}'-{whole}"
    if frac:
        s += f" {frac.numerator}/{frac.denominator}"
    return s + '"'


def feet(inches: float) -> float:
    return inches / 12.0
