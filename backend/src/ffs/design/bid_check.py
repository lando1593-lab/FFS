"""Check an imported EDGE spray report against the design library, item by item.

For each item the report's own design list and product line drive the query; the role decides
which of the sheet's designs apply (column designs X/Y for columns, the rest for beams). The
restraint for beams is not stated in a spray report; "unrestrained" is passed as an explicit
ASSUMPTION and printed as such. The output is a comparison, never a correction of the bid.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from ffs.design.library import DesignLibrary
from ffs.design.thickness import Resolution, ThicknessQuery, resolve

_PRODUCT_WORDS = re.compile(r"isolatek|gcp|carboline|\bcafco\b", re.IGNORECASE)


@dataclass
class BidCheckRow:
    sheet_no: str
    member: str
    role: str
    sides: int | None
    bid_in: float | None
    design: str | None
    rating_hours: float | None
    status: str
    engine_in: float | None
    distinct: list[float]
    verdict: str  # match / differs / review / unknown / no-design
    assumptions: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    resolution: Resolution | None = None


def _product_line(name: str | None) -> str | None:
    """'Isolatek Cafco 400' → 'CAFCO 400' (the chart's own wording is matched loosely)."""
    if not name:
        return None
    words = [w for w in name.split() if not _PRODUCT_WORDS.fullmatch(w)]
    return " ".join(words).upper() if words else None


def _designs_for(role: str, designs: list[dict]) -> list[dict]:
    cols = [d for d in designs if (d.get("design") or "")[:1] in ("X", "Y")]
    others = [d for d in designs if d not in cols]
    if role == "column":
        return cols or designs
    return others or designs


def check_report(lib: DesignLibrary, report: dict) -> list[BidCheckRow]:
    rows: list[BidCheckRow] = []
    for sheet in report.get("sheets", []):
        product = _product_line(sheet.get("product_name"))
        designs = sheet.get("designs") or []
        for it in sheet.get("items", []):
            member = it.get("canonical_section") or it.get("member_label")
            if not member or it.get("thickness_in") is None:
                continue
            role = it.get("role") or "beam"
            cands = _designs_for(role, designs)
            seen: set[tuple] = set()
            if not cands:
                rows.append(
                    BidCheckRow(
                        sheet["sheet_no"],
                        member,
                        role,
                        it.get("sides"),
                        it.get("thickness_in"),
                        None,
                        None,
                        "no-design",
                        None,
                        [],
                        "no-design",
                        reasons=["the sheet lists no design"],
                    )
                )
                continue
            for d in cands:
                key = (d.get("design"), d.get("rating_hr"))
                if key in seen:
                    continue
                seen.add(key)
                assumptions = []
                restraint = None
                if role != "column":
                    restraint = "unrestrained"
                    assumptions.append("restraint assumed unrestrained (not stated in the report)")
                q = ThicknessQuery(
                    d["design"], member, float(d.get("rating_hr") or 0), restraint, product
                )
                res = resolve(lib, q)
                bid = it.get("thickness_in")
                if res.status == "resolved":
                    verdict = "match" if abs(res.selected.thickness_in - bid) < 1e-6 else "differs"
                elif res.status == "conflict":
                    verdict = "match-one-route" if bid in res.distinct_values() else "differs"
                else:
                    verdict = res.status
                rows.append(
                    BidCheckRow(
                        sheet["sheet_no"],
                        member,
                        role,
                        it.get("sides"),
                        bid,
                        d["design"],
                        q.rating_hours,
                        res.status,
                        res.selected.thickness_in if res.selected else None,
                        res.distinct_values(),
                        verdict,
                        assumptions,
                        res.reasons,
                        res,
                    )
                )
    return rows


def check_report_file(lib: DesignLibrary, path: str | Path) -> list[BidCheckRow]:
    return check_report(lib, json.loads(Path(path).read_text(encoding="utf-8")))


def summarize(rows: list[BidCheckRow]) -> dict[str, int]:
    out: dict[str, int] = {}
    for r in rows:
        out[r.verdict] = out.get(r.verdict, 0) + 1
    return out
