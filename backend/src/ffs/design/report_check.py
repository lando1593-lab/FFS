"""Check every legend row of an EDGE drawing report against the design library.

The EDGE design codes carry suffix tokens whose meaning is company convention; the mapping
below is an INTERPRETATION recorded on every result, to be confirmed by the estimator:
  NW / LW   → normal-weight / lightweight concrete (chart condition or column group)
  C (N/D/P/S designs) → cellular or corrugated deck chart; C (X designs) → wide-flange column chart
  P/T       → pipe / tube column chart
  F, B (glued to or after the number) → unmapped, kept as printed
Restraint is not printed on the report; beams are checked as unrestrained (ASSUMPTION).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ffs.design.library import DesignLibrary
from ffs.design.thickness import Resolution, ThicknessQuery, resolve
from ffs.importers.edge_drawing_report import DrawingReport, LegendRow

PRODUCT_HINTS = {
    "blaze shield (type ii)": "BLAZE-SHIELD II",
    "blaze shield (type ii) roof": "BLAZE-SHIELD II",
    "cafco 400": "CAFCO 400",
    "cafco 300": "CAFCO 300",
    "mk-6 hy": "MK-6/HY",
    "mk-6/hy": "MK-6/HY",
}


@dataclass
class RowCheck:
    project: str | None
    sheet: str
    row: LegendRow
    query: ThicknessQuery | None
    resolution: Resolution | None
    verdict: str  # match / differs / match-one-route / review / unknown / skipped
    interpretations: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)


def product_line(hint: str | None) -> str | None:
    if not hint:
        return None
    return PRODUCT_HINTS.get(hint.strip().lower(), hint.strip().upper())


def conditions_for(row: LegendRow) -> tuple[str | None, list[str]]:
    """(condition phrase for the chart, interpretations) from the EDGE code tokens."""
    notes: list[str] = []
    cond: str | None = None
    toks = [t.upper() for t in row.design_tokens]
    if "NW" in toks:
        cond = "Normal Weight"
        notes.append("EDGE token NW read as normal-weight concrete")
    if "LW" in toks:
        cond = "Lightweight"
        notes.append("EDGE token LW read as lightweight concrete")
    if "C" in toks:
        if (row.design or "")[:1] == "X":
            notes.append("EDGE token C on a column design read as wide-flange column chart")
        else:
            cond = (cond + " " if cond else "") + ""  # concrete phrase still governs
            notes.append("EDGE token C read as cellular/corrugated deck chart")
            cond = "Cellular or Corrugated Deck " + (cond or "")
    if "P/T" in toks:
        notes.append("EDGE token P/T read as pipe/tube column chart")
    if row.design_suffix:
        notes.append(f"EDGE suffix {row.design_suffix!r} on {row.design} kept as printed, unmapped")
    for t in toks:
        if t not in ("NW", "LW", "C", "P/T"):
            notes.append(f"EDGE token {t!r} kept as printed, unmapped")
    return (cond.strip() or None) if cond else None, notes


def check_drawing_report(lib: DesignLibrary, rep: DrawingReport) -> list[RowCheck]:
    out: list[RowCheck] = []
    for sh in rep.sheets:
        product = product_line(sh.product_hint)
        for r in sh.rows:
            depth = r.extra.get("joist_depth_in") if r.role == "joist" else None
            if (not r.canonical and depth is None) or not r.design or r.hours is None:
                out.append(RowCheck(rep.project, sh.sheet_label, r, None, None, "skipped"))
                continue
            if r.thickness_in is None:
                out.append(RowCheck(rep.project, sh.sheet_label, r, None, None, "skipped"))
                continue
            cond, notes = conditions_for(r)
            unmapped = any("unmapped" in n for n in notes)
            restraint = None
            assumptions: list[str] = []
            beam_like = r.role in (
                "primary_beam",
                "secondary_beam",
                "bridging",
                "angle",
                "channel",
                "hss",
                "joist",
            )
            if beam_like and (r.design or "")[:1] not in ("X", "Y"):
                restraint = "unrestrained"
                assumptions.append("restraint assumed unrestrained (not printed on the report)")
            q = ThicknessQuery(
                r.design,
                r.canonical or f"JOIST {depth:g}",
                r.hours,
                restraint,
                product,
                condition=cond,
                joist_depth_in=depth,
            )
            res = resolve(lib, q)
            if res.status == "resolved":
                verdict = (
                    "match" if abs(res.selected.thickness_in - r.thickness_in) < 1e-6 else "differs"
                )
            elif res.status == "conflict":
                verdict = (
                    "match-one-route" if r.thickness_in in res.distinct_values() else "differs"
                )
            elif res.status == "review":
                verdict = "review-match" if r.thickness_in in res.distinct_values() else "review"
            else:
                verdict = "unknown"
            if verdict == "differs" and r.sides == 4:
                verdict = "differs-4-sides"
                notes.append("4-sided beam compared with the 3-sided beam chart row; basis differs")
            elif verdict == "differs" and unmapped:
                verdict = "differs-unmapped-code"
            elif verdict == "differs" and any(
                "footnote" in n for c in res.candidates for n in c.notes
            ):
                verdict = "differs-footnote"
            out.append(
                RowCheck(rep.project, sh.sheet_label, r, q, res, verdict, notes, assumptions)
            )
    return out


def summarize(checks: list[RowCheck]) -> dict[str, int]:
    out: dict[str, int] = {}
    for c in checks:
        out[c.verdict] = out.get(c.verdict, 0) + 1
    return out
