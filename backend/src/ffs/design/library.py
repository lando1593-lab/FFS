"""In-memory index over the parsed reference library (UL printouts, manufacturer charts).

Every record keeps the file it came from, the page and the printed row, so a resolved thickness
can cite its exact source. The index never merges sources: a UL table row and a manufacturer
chart row for the same member stay two candidates.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

_HOURS = re.compile(
    r"^\s*(\d+(?:[.-]\d+/\d+|\.\d+|/\d+)?)\s*-?\s*(hr|hour|hours|hrs)\b", re.IGNORECASE
)
_MINUTES = re.compile(r"^\s*(\d+)\s*min", re.IGNORECASE)


_TUBE_LABEL = re.compile(
    r"^(?:ST|RT|HSS)\s*(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\s*x\s*(\d+/\d+|\d*\.\d+|\d+)$",
    re.IGNORECASE,
)


def derived_tube_canonical(label: str) -> str | None:
    """'ST 5 x 5 x 3/8' / 'RT 6 x 4 x 1/4' → the AISC HSS designation (designation module)."""
    from ffs.steel.designation import find_designations

    m = _TUBE_LABEL.match(label.strip())
    if not m:
        return None
    des = find_designations(f"HSS{m.group(1)}X{m.group(2)}X{m.group(3)}")
    return des[0].canonical if len(des) == 1 else None


def rating_hours(column: str) -> float | None:
    """'1 Hr', '1-1/2 Hr', '1.5 hr', '3/4 Hr', '1-Hour', '90 min' → hours as a float; else None."""
    from fractions import Fraction

    m = _MINUTES.match(column)
    if m:
        return int(m.group(1)) / 60
    m = _HOURS.match(column)
    if not m:
        return None
    tok = m.group(1)
    try:
        if "-" in tok:
            w, f = tok.split("-", 1)
            return float(w) + float(Fraction(f))
        if "/" in tok:
            return float(Fraction(tok))
        return float(tok)
    except (ValueError, ZeroDivisionError):
        return None


@dataclass
class ChartRow:
    manufacturer: str
    design: str | None
    source_file: str
    page: int
    section: str | None  # restraint / table section as printed ("Unrestrained Beam")
    group: str | None  # column group as printed ("LIGHTWEIGHT CONCRETE FILL", "HALF FLANGE TIP…")
    condition: str | None
    products: str | None
    chart_date: str | None
    member_label: str
    canonical: str | None
    ratio_kind: str | None  # "W/D" or "A/P"
    ratio: float | None
    rating_columns: list[str]
    thickness_in: list[float | None]
    as_printed: list[str]
    not_rated: list[bool]
    footnote_markers: list[str] = field(default_factory=list)
    # AISC designation composed from a printed tube label ("ST 5 x 5 x 3/8" → HSS5X5X3/8) when
    # the chart prints no designation; None otherwise. Always labelled as derived when used.
    derived_canonical: str | None = None


@dataclass
class ChartSet:
    design: str | None
    rows: list[ChartRow]
    cross_reference_designs: list[str]
    source_file: str
    condition: str | None
    products: str | None
    chart_date: str | None
    notes: list[str]
    footnotes: list[dict]


@dataclass
class ULDesign:
    design_no: str
    last_updated: str | None
    design_date: str | None
    source_file: str | None
    ratings: list[dict]
    tables: list[dict]
    equations: list[dict]
    items: list[dict]


@dataclass
class DesignLibrary:
    ul: dict[str, ULDesign] = field(default_factory=dict)
    charts: dict[str, list[ChartSet]] = field(default_factory=dict)  # design → chart sets
    chart_files: int = 0
    _shas: set[str] = field(default_factory=set)

    @classmethod
    def load(cls, parsed_dir: str | Path) -> DesignLibrary:
        parsed_dir = Path(parsed_dir)
        lib = cls()
        for p in sorted((parsed_dir / "ul_designs").glob("UL_*.json")):
            d = json.loads(p.read_text(encoding="utf-8"))
            no = d.get("design_no")
            if not no or no == "UNKNOWN":
                continue
            rec = ULDesign(
                no,
                d.get("last_updated"),
                d.get("design_date"),
                d.get("source_file"),
                d.get("ratings") or [],
                d.get("tables") or [],
                d.get("equations") or [],
                d.get("items") or [],
            )
            prev = lib.ul.get(no)
            if prev is None or (rec.last_updated or "") >= (prev.last_updated or ""):
                lib.ul[no] = rec
        for p in sorted((parsed_dir / "charts").glob("*.json")):
            lib._add_isolatek(json.loads(p.read_text(encoding="utf-8")))
        for p in sorted((parsed_dir / "gcp_charts").glob("*.json")):
            lib._add_gcp(json.loads(p.read_text(encoding="utf-8")))
        return lib

    def _add_isolatek(self, c: dict) -> None:
        design = c.get("design")
        markers = c.get("rating_column_markers") or []
        rows = [
            ChartRow(
                "Isolatek",
                design,
                c.get("source_file") or "",
                r.get("page") or 0,
                r.get("section"),
                None,
                c.get("condition"),
                c.get("products"),
                c.get("chart_date"),
                r.get("member_label") or "",
                r.get("canonical"),
                c.get("factor_kind"),
                r.get("wd"),
                r.get("rating_columns") or c.get("rating_columns") or [],
                r.get("thickness_in") or [],
                r.get("thickness_as_printed") or [],
                r.get("not_rated") or [],
                markers,
                None if r.get("canonical") else derived_tube_canonical(r.get("member_label") or ""),
            )
            for r in c.get("rows") or []
        ]
        cs = ChartSet(
            design,
            rows,
            [str(x) for x in c.get("cross_reference_designs") or []],
            c.get("source_file") or "",
            c.get("condition"),
            c.get("products"),
            c.get("chart_date"),
            c.get("notes") or [],
            c.get("footnotes") or [],
        )
        self._register(cs)

    def _add_gcp(self, c: dict) -> None:
        design = c.get("design")
        groups = {g.get("title"): g.get("rating_columns") or [] for g in c.get("groups") or []}
        rows = [
            ChartRow(
                "GCP",
                design,
                c.get("source_file") or "",
                r.get("page") or 0,
                c.get("restraint"),
                r.get("group"),
                " ".join(x for x in (c.get("assembly"), c.get("concrete")) if x) or None,
                c.get("products"),
                c.get("chart_date"),
                r.get("member_label") or "",
                r.get("canonical"),
                r.get("ratio_name"),
                r.get("wd"),
                groups.get(r.get("group")) or next(iter(groups.values()), []),
                r.get("thickness_in") or [],
                r.get("thickness_as_printed") or [],
                r.get("not_rated") or [],
            )
            for r in c.get("rows") or []
        ]
        cs = ChartSet(
            design,
            rows,
            [],
            c.get("source_file") or "",
            c.get("assembly"),
            c.get("products"),
            c.get("chart_date"),
            c.get("notes") or [],
            [],
        )
        self._register(cs)

    def _register(self, cs: ChartSet) -> None:
        sha = cs.source_file.rsplit("__", 1)[-1]
        if sha in self._shas:
            return  # the same file fetched under two ids
        self._shas.add(sha)
        self.chart_files += 1
        keys = [cs.design] if cs.design else [""]  # "" = design-less (miscellaneous shapes)
        for k in keys:
            for part in re.split(r"\s*/\s*", k):  # "N308/N309" charts serve both designs
                self.charts.setdefault(part, []).append(cs)

    def designs(self) -> list[str]:
        return sorted(set(self.ul) | set(self.charts))
