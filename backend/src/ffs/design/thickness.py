"""Thickness resolution: (design, member, rating, restraint, product, application) → thickness
with its source.

Rules (CLAUDE.md 1, 2, 5):
* A thickness is only ever the value printed in a UL design table or a manufacturer chart row,
  or the result of a UL design equation applied to a printed section factor. Nothing is
  interpolated, nothing is carried from a neighbouring size.
* Every candidate carries the document, page, printed row and column it came from, the
  design and revision, and its assertion class: FACT for a printed cell, CALCULATION for an
  equation (with its inputs and the rounding rule).
* Sources that disagree are all returned; the engine never picks silently between a UL table
  and an equation route, or between a listing and a manufacturer chart. "UNKNOWN — REVIEW
  REQUIRED" is the answer when nothing printed applies, with the reasons.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from ffs.design.library import ChartSet, DesignLibrary, ULDesign, rating_hours

UNKNOWN = "UNKNOWN — REVIEW REQUIRED"
AUTHORITY_LISTING = 2  # UL design (listing body)
AUTHORITY_MANUFACTURER = 6  # manufacturer chart / workbook
_HALF_FLANGE = re.compile(r"half[\s-]*flange", re.IGNORECASE)


@dataclass
class ThicknessQuery:
    design: str
    member: str  # canonical AISC designation (W12X26, HSS5X5X3/8)
    rating_hours: float
    restraint: str | None = None  # "restrained" / "unrestrained" / None (n/a or unknown)
    product: str | None = None  # product line text to require on a chart ("CAFCO 400")
    ratio: float | None = None  # W/D or A/P when the caller knows it (AISC database)
    ratio_kind: str | None = None  # "W/D" / "A/P"
    ratio_source: str | None = None
    application: str = "contour"  # "contour" (full) or "half_flange_tip"; charts say which
    condition: str | None = None  # assembly condition to require on a chart ("Protected Roof Deck")
    joist_depth_in: float | None = None  # steel joists are specified by depth on shop drawings


@dataclass
class Candidate:
    thickness_in: float | None  # None when the printed cell is NR / not rated
    as_printed: str | None
    method: str  # ul_table / ul_equation / chart_table / shape_chart
    assertion_kind: str  # FACT / CALCULATION
    authority: int
    design: str
    source: dict
    inputs: dict = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


@dataclass
class Resolution:
    query: ThicknessQuery
    candidates: list[Candidate]
    status: str  # resolved / conflict / review / unknown
    selected: Candidate | None
    reasons: list[str]

    @property
    def value(self) -> float | str | None:
        if self.status == "resolved" and self.selected:
            return self.selected.thickness_in
        return UNKNOWN

    def distinct_values(self) -> list[float]:
        return sorted({c.thickness_in for c in self.candidates if c.thickness_in is not None})


def _tokens(s: str | None) -> list[str]:
    return re.findall(r"[a-z0-9/]+", (s or "").lower().replace("®", ""))


def _norm(s: str | None) -> str:
    return " ".join(_tokens(s))


def _has_phrase(hay: str | None, needle: str | None) -> bool:
    """True when the needle's words appear in order and adjacent in the hay (whole words only:
    'Protected Roof Deck' is not inside 'Unprotected Roof Deck')."""
    h, n = _tokens(hay), _tokens(needle)
    if not n:
        return True
    return any(h[i : i + len(n)] == n for i in range(len(h) - len(n) + 1))


def _restraint_of(text: str | None) -> str | None:
    t = (text or "").lower()
    if "unrestrained" in t:
        return "unrestrained"
    if "restrained" in t:
        return "restrained"
    return None


def _application_of(cs: ChartSet) -> str:
    return "half_flange_tip" if _HALF_FLANGE.search(cs.condition or "") else "contour"


def _column_index(columns: list[str], hours: float) -> int | None:
    for i, c in enumerate(columns):
        h = rating_hours(c)
        if h is not None and abs(h - hours) < 1e-6:
            return i
    return None


def _ceil_sixteenth(x: float) -> float:
    return math.ceil(x * 16 - 1e-9) / 16


def _ul_table_candidates(d: ULDesign, q: ThicknessQuery, reasons: list[str]) -> list[Candidate]:
    out: list[Candidate] = []
    for t in d.tables:
        if t.get("kind") not in ("size_wd", "ratio_rows"):
            continue
        cols = t.get("rating_columns") or []
        idx = _column_index(cols, q.rating_hours)
        cond_restraint = _restraint_of(t.get("condition"))
        if q.restraint and cond_restraint and cond_restraint != q.restraint:
            continue
        for r in t.get("rows") or []:
            if r.get("canonical") != q.member:
                continue
            if idx is None:
                reasons.append(
                    f"UL {d.design_no}: table item {t.get('item_no')} has no "
                    f"{q.rating_hours} h column"
                )
                continue
            vals = r.get("values_in") or []
            cells = r.get("cells") or []
            printed = cells[len(cells) - len(cols) + idx] if len(cells) >= len(cols) else None
            value = vals[idx] if idx < len(vals) else None
            c = Candidate(
                value,
                printed,
                "ul_table",
                "FACT",
                AUTHORITY_LISTING,
                d.design_no,
                {
                    "document": d.source_file,
                    "design": d.design_no,
                    "last_updated": d.last_updated,
                    "item": t.get("item_no"),
                    "table_condition": t.get("condition"),
                    "row": r.get("label"),
                    "column": cols[idx],
                    "units": t.get("units"),
                },
            )
            if value is None:
                c.notes.append("printed as not rated / not available at this rating")
            if t.get("units") not in (None, "in"):
                c.notes.append(f"table units {t.get('units')}; inches derived by unit conversion")
            out.append(c)
    return out


def _equation_candidates(
    d: ULDesign,
    q: ThicknessQuery,
    ratio: float | None,
    ratio_kind: str | None,
    ratio_src: str | None,
    reasons: list[str],
) -> list[Candidate]:
    out: list[Candidate] = []
    if ratio is None:
        if d.equations:
            reasons.append(
                f"UL {d.design_no}: equation route needs {d.equations[0].get('factor')} "
                f"for {q.member}; none known"
            )
        return out
    for e in d.equations:
        if _norm(e.get("factor")) != _norm(ratio_kind):
            continue
        rng = e.get("wd_range")
        if rng and not (min(rng) - 1e-9 <= ratio <= max(rng) + 1e-9):
            reasons.append(
                f"UL {d.design_no} item {e.get('item_no')}: {ratio_kind} {ratio} outside "
                f"the equation range {rng}"
            )
            continue
        if (
            e.get("rating_hours") is not None
            and abs(float(e["rating_hours"]) - q.rating_hours) > 1e-6
        ):
            continue
        form = e.get("form") or ""
        r_minutes = (e.get("r_units") or "").startswith("min")
        R = q.rating_hours * 60 if r_minutes else q.rating_hours
        try:
            if form.startswith("h = R / ("):
                raw = R / (float(e["a"]) * ratio + float(e["b"]))
            elif form.startswith("T = k / ("):
                raw = float(e["k"]) / ratio
            elif form.startswith("h = (R - c)"):
                raw = (R - float(e["c"])) / (float(e["k"]) * ratio)
            elif form.startswith("T = a*("):
                raw = float(e["a"]) * ratio + float(e["b"])
            else:
                reasons.append(f"UL {d.design_no}: equation form not implemented: {form}")
                continue
        except (TypeError, ValueError, ZeroDivisionError):
            reasons.append(
                f"UL {d.design_no}: equation constants incomplete: {e.get('as_printed')}"
            )
            continue
        units = e.get("h_units") or "in"
        if units != "in":
            reasons.append(
                f"UL {d.design_no} item {e.get('item_no')}: equation in {units}; not converted"
            )
            continue
        hr = e.get("h_range_in") or e.get("h_range")
        if hr and not (min(hr) - 1e-9 <= raw <= max(hr) + 1e-9):
            reasons.append(
                f"UL {d.design_no} item {e.get('item_no')}: computed {raw:.3f} in outside "
                f"the thickness range {hr}"
            )
            continue
        out.append(
            Candidate(
                _ceil_sixteenth(raw),
                None,
                "ul_equation",
                "CALCULATION",
                AUTHORITY_LISTING,
                d.design_no,
                {
                    "document": d.source_file,
                    "design": d.design_no,
                    "last_updated": d.last_updated,
                    "item": e.get("item_no"),
                    "equation": e.get("as_printed"),
                    "form": form,
                },
                {
                    "ratio_kind": ratio_kind,
                    "ratio": ratio,
                    "ratio_source": ratio_src,
                    "R": R,
                    "r_units": e.get("r_units"),
                    "constants": {
                        k: e.get(k) for k in ("a", "b", "k", "c") if e.get(k) is not None
                    },
                    "raw_in": round(raw, 4),
                    "rounding": "up to the next 1/16 in",
                },
                list(e.get("notes") or []),
            )
        )
    return out


def _chart_candidates(
    lib: DesignLibrary,
    design: str,
    q: ThicknessQuery,
    chain: list[str],
    reasons: list[str],
    condition: str | None,
) -> list[Candidate]:
    out: list[Candidate] = []
    for cs in lib.charts.get(design, []):
        if q.product and not _has_phrase(cs.products, q.product):
            continue
        if not cs.rows and cs.cross_reference_designs:
            # "Use Design S721 Table": the target chart must serve the same assembly condition
            for target in cs.cross_reference_designs:
                if target in chain:
                    continue
                out.extend(
                    _chart_candidates(lib, target, q, chain + [target], reasons, cs.condition)
                )
            continue
        if _application_of(cs) != q.application and not any(r.group for r in cs.rows):
            continue  # a chart printed for the other application (half-flange tip option)
        if condition and not _has_phrase(cs.condition, condition):
            # the condition may be a column group instead ("LIGHTWEIGHT CONCRETE FILL")
            if not any(_has_phrase(r.group, condition) for r in cs.rows if r.group):
                continue
        sections = {_restraint_of(r.section) for r in cs.rows if _restraint_of(r.section)}
        for r in cs.rows:
            if q.joist_depth_in is not None:
                if r.depth_in is None or abs(r.depth_in - q.joist_depth_in) > 1e-6:
                    continue
            elif (r.canonical or r.derived_canonical) != q.member:
                continue
            if condition and r.group and not _has_phrase(cs.condition, condition):
                if not _has_phrase(r.group, condition):
                    continue
            row_restraint = _restraint_of(r.section)
            note = []
            if q.restraint:
                if row_restraint and row_restraint != q.restraint:
                    continue
                if row_restraint is None and sections:
                    if sections != {q.restraint}:
                        continue
                    note.append("section label printed on a later page of the same chart")
            if r.group and (
                ("half_flange_tip" if _HALF_FLANGE.search(r.group) else "contour") != q.application
            ):
                continue  # GCP prints full and half flange tip as column groups of one chart
            if r.canonical is None and r.derived_canonical:
                note.append(f"designation derived from the printed label {r.member_label!r}")
            idx = _column_index(r.rating_columns, q.rating_hours)
            if idx is None:
                reasons.append(
                    f"chart {cs.source_file}: no {q.rating_hours} h column for {q.member}"
                )
                continue
            value = r.thickness_in[idx] if idx < len(r.thickness_in) else None
            c = Candidate(
                value,
                r.as_printed[idx] if idx < len(r.as_printed) else None,
                "chart_table",
                "FACT",
                AUTHORITY_MANUFACTURER,
                design,
                {
                    "document": cs.source_file,
                    "manufacturer": r.manufacturer,
                    "design": design,
                    "chart_date": cs.chart_date,
                    "products": cs.products,
                    "condition": cs.condition,
                    "application": _application_of(cs),
                    "section": r.section,
                    "group": r.group,
                    "page": r.page,
                    "row": r.member_label,
                    "column": r.rating_columns[idx],
                    "via": " → ".join(chain) if len(chain) > 1 else None,
                },
                {"ratio_kind": r.ratio_kind, "ratio": r.ratio},
                note,
            )
            if value is None:
                c.notes.append("printed as NR at this rating")
            if r.footnote_markers and idx < len(r.footnote_markers) and r.footnote_markers[idx]:
                c.notes.append(f"column carries footnote marker {r.footnote_markers[idx]!r}")
            out.append(c)
    return out


def _shape_chart_candidates(
    lib: DesignLibrary, q: ThicknessQuery, reasons: list[str]
) -> list[Candidate]:
    """Design-less 'Miscellaneous Shapes' charts (angles, channels, WT) of the product line.

    They are not tied to a design, so a hit is returned for review, never as resolved."""
    out: list[Candidate] = []
    if not q.product:
        return out  # without a product line a design-less chart cannot be tied to the job
    for cs in lib.charts.get("", []):
        if not _has_phrase(cs.products, q.product):
            continue
        for r in cs.rows:
            if (r.canonical or r.derived_canonical) != q.member:
                continue
            idx = _column_index(r.rating_columns, q.rating_hours)
            if idx is None:
                continue
            value = r.thickness_in[idx] if idx < len(r.thickness_in) else None
            out.append(
                Candidate(
                    value,
                    r.as_printed[idx] if idx < len(r.as_printed) else None,
                    "shape_chart",
                    "FACT",
                    AUTHORITY_MANUFACTURER,
                    q.design,
                    {
                        "document": cs.source_file,
                        "manufacturer": r.manufacturer,
                        "design": None,
                        "chart_date": cs.chart_date,
                        "products": cs.products,
                        "condition": cs.condition,
                        "page": r.page,
                        "row": r.member_label,
                        "column": r.rating_columns[idx],
                    },
                    {"ratio_kind": r.ratio_kind, "ratio": r.ratio},
                    [
                        f"chart is not tied to design {q.design}; it is the manufacturer's "
                        "miscellaneous-shapes table for the product line (basis to be confirmed)"
                    ],
                )
            )
    return out


def _collapse_joists(cands: list[Candidate], q: ThicknessQuery) -> list[Candidate]:
    """Joist charts print one row per designation; a depth query gathers every designation of
    that depth. Equal values collapse into one candidate that lists the designations; unequal
    values stay separate (and the resolution becomes a conflict)."""
    if q.joist_depth_in is None:
        return cands
    out: list[Candidate] = []
    for c in cands:
        key = (
            c.thickness_in,
            c.source.get("document"),
            c.source.get("section"),
            c.source.get("column"),
        )
        for o in out:
            if (
                o.thickness_in,
                o.source.get("document"),
                o.source.get("section"),
                o.source.get("column"),
            ) == key:
                o.source.setdefault("rows", [o.source.get("row")]).append(c.source.get("row"))
                break
        else:
            c.notes.append(
                f"joist depth {q.joist_depth_in:g} in: every designation of this depth printed"
            )
            out.append(c)
    for o in out:
        if "rows" in o.source:
            o.source["row"] = f"{len(o.source['rows'])} designations: " + ", ".join(
                o.source["rows"]
            )
    return out


def _dedupe(cands: list[Candidate]) -> list[Candidate]:
    """Collapse identical printed cells reached through two copies of the same chart."""
    out: list[tuple[tuple, Candidate]] = []
    for c in cands:
        key = (
            c.method,
            c.thickness_in,
            c.as_printed,
            c.source.get("design"),
            c.source.get("chart_date") or c.source.get("last_updated"),
            c.source.get("products"),
            c.source.get("condition") or c.source.get("table_condition"),
            c.source.get("section"),
            c.source.get("group"),
            c.source.get("row"),
            c.source.get("column"),
        )
        for k, o in out:
            if k == key:
                o.source.setdefault("also_in", []).append(c.source.get("document"))
                break
        else:
            out.append((key, c))
    return [c for _, c in out]


def _ratio_from_rows(
    lib: DesignLibrary, design: str, member: str
) -> tuple[float | None, str | None, str | None]:
    """A printed section factor for the member from any row that names it (UL table first)."""
    d = lib.ul.get(design)
    if d:
        for t in d.tables:
            for r in t.get("rows") or []:
                if r.get("canonical") == member and r.get("wd") is not None:
                    kind = (t.get("ratio_names") or ["W/D"])[0]
                    return (
                        float(r["wd"]),
                        kind,
                        f"UL {design} item {t.get('item_no')} row {r.get('label')}",
                    )
    for cs in lib.charts.get(design, []):
        for r in cs.rows:
            if (r.canonical or r.derived_canonical) == member and r.ratio is not None:
                return (
                    r.ratio,
                    r.ratio_kind,
                    f"chart {cs.source_file} p{r.page} row {r.member_label}",
                )
    return None, None, None


def resolve(lib: DesignLibrary, q: ThicknessQuery) -> Resolution:
    reasons: list[str] = []
    candidates: list[Candidate] = []
    d = lib.ul.get(q.design)
    if d is None and q.design not in lib.charts:
        reasons.append(f"design {q.design} is not in the library (no UL printout, no chart)")
        return Resolution(q, [], "unknown", None, reasons)
    if d:
        candidates.extend(_ul_table_candidates(d, q, reasons))
        ratio, kind, src = q.ratio, q.ratio_kind, q.ratio_source
        if ratio is None:
            ratio, kind, src = _ratio_from_rows(lib, q.design, q.member)
        candidates.extend(_equation_candidates(d, q, ratio, kind, src, reasons))
    else:
        reasons.append(f"no UL printout for {q.design} in the library; manufacturer chart only")
    candidates.extend(_chart_candidates(lib, q.design, q, [q.design], reasons, q.condition))
    candidates = _dedupe(_collapse_joists(candidates, q))
    if not candidates:
        shape = _dedupe(_shape_chart_candidates(lib, q, reasons))
        if shape:
            reasons.append(
                f"{q.member} is not printed in any {q.design} table or chart; the product's "
                "miscellaneous-shapes chart has it, basis to be confirmed by the estimator"
            )
            return Resolution(q, shape, "review", None, reasons)
        reasons.append(
            f"{q.member} is not printed in any {q.design} table or chart for {q.rating_hours} h"
        )
        return Resolution(q, [], "unknown", None, reasons)
    values = {c.thickness_in for c in candidates}
    candidates.sort(key=lambda c: (c.authority, c.method != "ul_table"))
    if len(values) > 1:
        return Resolution(
            q,
            candidates,
            "conflict",
            None,
            reasons + ["sources disagree; the estimator chooses and the choice is recorded"],
        )
    best = candidates[0]
    if best.method == "chart_table" and not q.product:
        # a manufacturer chart value is only a thickness together with the product line it was
        # printed for (CLAUDE.md rule 5); without one named, this is a review item
        lines = sorted({c.source.get("products") or "" for c in candidates})
        reasons.append(
            f"no product line given; {len(lines)} manufacturer chart line(s) print this value: "
            + "; ".join(x[:60] for x in lines)
        )
        return Resolution(q, candidates, "review", None, reasons)
    return Resolution(q, candidates, "resolved", best, reasons)
