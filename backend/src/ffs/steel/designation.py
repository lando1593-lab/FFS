"""Structural steel designation parsing and canonicalization.

Canonical form follows the AISC Shapes Database spelling: ``W18X35``, ``HSS6X6X1/4``,
``HSS6.000X0.250``, ``L4X4X1/2``, ``L3-1/2X3-1/2X1/4``, ``WT9X25``, ``C10X15.3``, ``MC12X31``,
``HP14X73``, ``PIPE4STD``.  Raw text is always preserved alongside the canonical form.

OCR normalization is deliberately narrow: only characters that are letter/digit confusions in a
position where a digit is required are repaired (``WI8x35`` → ``W18X35``), the repair is recorded
in ``notes`` and ``confidence`` is reduced.  Two genuinely different shapes are never merged.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum


class ShapeFamily(StrEnum):
    W = "W"
    M = "M"
    S = "S"
    HP = "HP"
    C = "C"
    MC = "MC"
    L = "L"
    DOUBLE_L = "2L"
    WT = "WT"
    MT = "MT"
    ST = "ST"
    HSS_RECT = "HSS"
    HSS_ROUND = "HSS_ROUND"
    PIPE = "PIPE"
    JOIST = "JOIST"
    JOIST_GIRDER = "JOIST_GIRDER"
    UNKNOWN = "UNKNOWN"


@dataclass
class ParsedDesignation:
    raw: str
    canonical: str
    family: ShapeFamily
    confidence: float
    dims: dict[str, str] = field(default_factory=dict)
    prefix: str | None = None  # e.g. "(E)", "(N)", "(D)" captured from context
    notes: list[str] = field(default_factory=list)

    @property
    def nominal_depth(self) -> float | None:
        d = self.dims.get("depth")
        return _frac_to_float(d) if d else None

    @property
    def weight_plf(self) -> float | None:
        w = self.dims.get("weight")
        return float(w) if w else None


# --- OCR-aware character classes -------------------------------------------------------------
# In digit positions we accept common OCR confusions and repair them afterward.
_D = r"[0-9OIl|S]"  # digit or confusable
_SEP = r"\s*[xX×\*]\s*"  # the "x" separator, including unicode times and asterisk

_OCR_DIGIT_MAP = str.maketrans({"O": "0", "I": "1", "l": "1", "|": "1", "S": "5"})

# Families whose designation is DEPTH x WEIGHT (two numbers).
_TWO_NUM_FAMILIES = {
    "W": ShapeFamily.W,
    "M": ShapeFamily.M,
    "S": ShapeFamily.S,
    "HP": ShapeFamily.HP,
    "C": ShapeFamily.C,
    "MC": ShapeFamily.MC,
    "WT": ShapeFamily.WT,
    "MT": ShapeFamily.MT,
    "ST": ShapeFamily.ST,
}

_TWO_NUM_RE = re.compile(
    rf"(?<![A-Z0-9])(?P<fam>W|M|S|HP|C|MC|WT|MT|ST)\s*-?\s*"
    rf"(?P<depth>{_D}{{1,2}})"
    rf"{_SEP}"
    rf"(?P<weight>{_D}{{1,4}}(?:\.{_D}{{1,2}})?)"
    rf"(?![A-Z0-9/.])",
    re.IGNORECASE,
)

_FRAC = r"(?:\d+(?:-\d+/\d+)?|\d*\.\d+|\d+/\d+)"  # 4, 3-1/2, 0.250, .25, 1/4
_HSS_RECT_RE = re.compile(
    rf"(?<![A-Z0-9])HSS\s*(?P<a>{_FRAC}){_SEP}(?P<b>{_FRAC}){_SEP}(?P<t>{_FRAC})(?![A-Z0-9/])",
    re.IGNORECASE,
)
_HSS_ROUND_RE = re.compile(
    rf"(?<![A-Z0-9])HSS\s*(?P<d>\d+(?:\.\d+)?){_SEP}(?P<t>\d*\.\d+)(?![A-Z0-9/xX×])",
    re.IGNORECASE,
)
_ANGLE_RE = re.compile(
    rf"(?<![A-Z0-9])(?P<dbl>2\s*)?L\s*(?P<a>{_FRAC}){_SEP}(?P<b>{_FRAC}){_SEP}(?P<t>{_FRAC})(?![A-Z0-9/])",
    re.IGNORECASE,
)
_PIPE_RE = re.compile(
    r"(?<![A-Z0-9])PIPE\s*(?P<d>\d+(?:-\d+/\d+)?(?:\.\d+)?)\s*(?P<sched>STD|XS|XXS|X-STRONG|XX-STRONG|SCH\s*\d+)?(?![A-Z0-9])",
    re.IGNORECASE,
)
_JOIST_RE = re.compile(
    r"(?<![A-Z0-9])(?P<depth>\d{2})\s*(?P<series>K|LH|DLH|KCS)\s*(?P<num>\d{1,2})(?![A-Z0-9])",
    re.IGNORECASE,
)
_JOIST_GIRDER_RE = re.compile(
    r"(?<![A-Z0-9])(?P<depth>\d{2})\s*G\s*(?P<n>\d+)\s*N\s*(?P<load>\d+(?:\.\d+)?)\s*(?P<unit>K|F)(?![A-Z0-9])",
    re.IGNORECASE,
)

_STATUS_PREFIX_RE = re.compile(r"\(\s*(?P<p>E|N|D|EX|EXIST(?:ING)?|NEW|DEMO)\s*\)", re.IGNORECASE)


def _frac_to_float(s: str) -> float | None:
    s = s.strip()
    try:
        if "-" in s and "/" in s:
            whole, frac = s.split("-", 1)
            n, d = frac.split("/")
            return float(whole) + float(n) / float(d)
        if "/" in s:
            n, d = s.split("/")
            return float(n) / float(d)
        return float(s)
    except (ValueError, ZeroDivisionError):
        return None


def _norm_frac(s: str) -> str:
    """Normalize a dimension token to AISC spelling: ``.25`` → ``0.250`` only for decimals,
    ``3-1/2`` kept, ``4`` kept, ``1/4`` kept."""
    s = s.strip()
    if "/" in s:
        return s
    if "." in s:
        v = float(s)
        return f"{v:.3f}"
    return s


def _repair_digits(token: str) -> tuple[str, bool]:
    repaired = token.translate(_OCR_DIGIT_MAP)
    return repaired, repaired != token


def _status_prefix(context: str, start: int) -> str | None:
    window = context[max(0, start - 8) : start]
    m = _STATUS_PREFIX_RE.search(window)
    if not m:
        return None
    p = m.group("p").upper()
    if p in ("E", "EX", "EXIST", "EXISTING"):
        return "E"
    if p in ("N", "NEW"):
        return "N"
    return "D"


def find_designations(text: str) -> list[ParsedDesignation]:
    """Find every steel designation in ``text`` (a text span, line, or cell).

    Returns parsed designations in order of appearance. Overlapping matches are resolved in favor
    of the more specific family (HSS/L/PIPE/joist before the generic two-number pattern).
    """
    found: list[tuple[int, int, ParsedDesignation]] = []

    def _add(m: re.Match[str], pd: ParsedDesignation) -> None:
        pd.prefix = _status_prefix(text, m.start())
        found.append((m.start(), m.end(), pd))

    for m in _HSS_RECT_RE.finditer(text):
        a, b, t = (_norm_frac(m.group(k)) for k in ("a", "b", "t"))
        _add(
            m,
            ParsedDesignation(
                raw=m.group(0),
                canonical=f"HSS{a}X{b}X{t}",
                family=ShapeFamily.HSS_RECT,
                confidence=0.97,
                dims={"a": a, "b": b, "t": t, "depth": a},
            ),
        )
    for m in _HSS_ROUND_RE.finditer(text):
        if any(s <= m.start() < e for s, e, _ in found):
            continue
        d, t = _norm_frac(m.group("d")), _norm_frac(m.group("t"))
        _add(
            m,
            ParsedDesignation(
                raw=m.group(0),
                canonical=f"HSS{d}X{t}",
                family=ShapeFamily.HSS_ROUND,
                confidence=0.95,
                dims={"d": d, "t": t, "depth": d},
            ),
        )
    for m in _ANGLE_RE.finditer(text):
        a, b, t = (_norm_frac(m.group(k)) for k in ("a", "b", "t"))
        dbl = bool(m.group("dbl"))
        _add(
            m,
            ParsedDesignation(
                raw=m.group(0),
                canonical=f"{'2L' if dbl else 'L'}{a}X{b}X{t}",
                family=ShapeFamily.DOUBLE_L if dbl else ShapeFamily.L,
                confidence=0.95,
                dims={"a": a, "b": b, "t": t, "depth": a},
            ),
        )
    for m in _PIPE_RE.finditer(text):
        sched = (m.group("sched") or "").upper().replace(" ", "")
        sched = {"X-STRONG": "XS", "XX-STRONG": "XXS"}.get(sched, sched)
        notes = [] if sched else ["pipe schedule not stated"]
        _add(
            m,
            ParsedDesignation(
                raw=m.group(0),
                canonical=f"PIPE{m.group('d')}{sched}",
                family=ShapeFamily.PIPE,
                confidence=0.9 if sched else 0.7,
                dims={"d": m.group("d"), "sched": sched, "depth": m.group("d")},
                notes=notes,
            ),
        )
    for m in _JOIST_GIRDER_RE.finditer(text):
        _add(
            m,
            ParsedDesignation(
                raw=m.group(0),
                canonical=f"{m.group('depth')}G{m.group('n')}N{m.group('load')}{m.group('unit').upper()}",
                family=ShapeFamily.JOIST_GIRDER,
                confidence=0.9,
                dims={"depth": m.group("depth")},
            ),
        )
    for m in _JOIST_RE.finditer(text):
        if any(s <= m.start() < e for s, e, _ in found):
            continue
        _add(
            m,
            ParsedDesignation(
                raw=m.group(0),
                canonical=f"{m.group('depth')}{m.group('series').upper()}{m.group('num')}",
                family=ShapeFamily.JOIST,
                confidence=0.9,
                dims={"depth": m.group("depth"), "series": m.group("series").upper()},
            ),
        )
    for m in _TWO_NUM_RE.finditer(text):
        if any(s < m.end() and m.start() < e for s, e, _ in found):
            continue
        fam_raw = m.group("fam").upper()
        fam = _TWO_NUM_FAMILIES[fam_raw]
        depth, d_fixed = _repair_digits(m.group("depth"))
        weight, w_fixed = _repair_digits(m.group("weight"))
        notes: list[str] = []
        conf = 0.95
        if d_fixed or w_fixed:
            notes.append(
                f"OCR digit repair: {m.group('depth')}x{m.group('weight')} → {depth}x{weight}"
            )
            conf = 0.6
        # Plausibility: AISC W depths run 4..44 in., weights up to ~1100 plf.
        try:
            dv, wv = int(depth), float(weight)
        except ValueError:
            continue
        if fam in (ShapeFamily.W, ShapeFamily.HP, ShapeFamily.M, ShapeFamily.S):
            if not (3 <= dv <= 44) or not (4 <= wv <= 1100):
                notes.append("implausible depth/weight for family")
                conf = min(conf, 0.3)
        elif fam in (ShapeFamily.C, ShapeFamily.MC):
            if not (3 <= dv <= 18) or not (3 <= wv <= 100):
                notes.append("implausible depth/weight for family")
                conf = min(conf, 0.3)
        elif fam in (ShapeFamily.WT, ShapeFamily.MT, ShapeFamily.ST):
            if not (1 <= dv <= 22) or not (2 <= wv <= 550):
                notes.append("implausible depth/weight for family")
                conf = min(conf, 0.3)
        # Normalize weight spelling: drop trailing ".0", keep "15.3".
        wtxt = weight
        if "." in wtxt:
            wtxt = wtxt.rstrip("0").rstrip(".")
        _add(
            m,
            ParsedDesignation(
                raw=m.group(0),
                canonical=f"{fam_raw}{dv}X{wtxt}",
                family=fam,
                confidence=conf,
                dims={"depth": str(dv), "weight": wtxt},
                notes=notes,
            ),
        )

    found.sort(key=lambda t: t[0])
    return [pd for _, _, pd in found]


def parse_designation(text: str) -> ParsedDesignation | None:
    """Parse a single designation token. Returns None if ``text`` is not exactly one designation."""
    res = find_designations(text)
    if len(res) != 1:
        return None
    pd = res[0]
    leftover = re.sub(re.escape(pd.raw), "", text, count=1)
    leftover = _STATUS_PREFIX_RE.sub("", leftover).strip(" -:,")
    if leftover:
        return None
    return pd
