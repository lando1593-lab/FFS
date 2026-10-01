"""Counts and LF by level × designation, plus CSV/XLSX writers."""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from ffs.takeoff.model import MemberRecord

MEMBER_COLUMNS = [
    "id",
    "level",
    "sheet_no",
    "start_grid",
    "end_grid",
    "member_mark",
    "canonical_section",
    "family",
    "member_type",
    "status",
    "length_in",
    "length_ft",
    "length_display",
    "length_source",
    "confidence_id",
    "confidence_geom",
    "confidence_length",
    "confidence_level",
    "review_state",
    "status_color",
    "notes",
]


@dataclass
class SummaryRow:
    level: str
    canonical_section: str
    count: int
    count_with_length: int
    total_lf: float
    unknown_lengths: int
    needs_review: int


def summarize(members: list[MemberRecord], include_excluded: bool = False) -> list[SummaryRow]:
    acc: dict[tuple[str, str], SummaryRow] = {}
    for m in members:
        if m.review_state == "excluded" and not include_excluded:
            continue
        k = (m.level, m.canonical_section)
        r = acc.get(k)
        if r is None:
            r = acc[k] = SummaryRow(m.level, m.canonical_section, 0, 0, 0.0, 0, 0)
        r.count += 1
        if m.length_in is None:
            r.unknown_lengths += 1
        else:
            r.count_with_length += 1
            r.total_lf += m.length_in / 12.0
        if m.needs_review:
            r.needs_review += 1
    return sorted(acc.values(), key=lambda r: (r.level, r.canonical_section))


def write_members_csv(members: list[MemberRecord], path: str | Path) -> None:
    with Path(path).open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(MEMBER_COLUMNS)
        for m in members:
            w.writerow(
                [
                    m.id,
                    m.level,
                    m.sheet_no or "",
                    m.start_grid or "",
                    m.end_grid or "",
                    m.member_mark,
                    m.canonical_section,
                    m.family,
                    m.member_type,
                    m.status,
                    "" if m.length_in is None else f"{m.length_in:.2f}",
                    "" if m.length_ft is None else f"{m.length_ft:.3f}",
                    m.length_display,
                    m.length_source,
                    m.confidence_id,
                    m.confidence_geom,
                    m.confidence_length,
                    m.confidence_level,
                    m.review_state,
                    m.status_color,
                    " | ".join(m.notes),
                ]
            )


def write_summary_csv(rows: list[SummaryRow], path: str | Path) -> None:
    with Path(path).open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "level",
                "section",
                "count",
                "count_with_length",
                "total_lf",
                "unknown_lengths",
                "needs_review",
            ]
        )
        for r in rows:
            w.writerow(
                [
                    r.level,
                    r.canonical_section,
                    r.count,
                    r.count_with_length,
                    f"{r.total_lf:.2f}",
                    r.unknown_lengths,
                    r.needs_review,
                ]
            )


def write_xlsx(members: list[MemberRecord], rows: list[SummaryRow], path: str | Path) -> None:
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Summary"
    ws.append(
        [
            "Level",
            "Section",
            "Count",
            "Count w/ length",
            "Total LF",
            "Unknown lengths",
            "Needs review",
        ]
    )
    for r in rows:
        ws.append(
            [
                r.level,
                r.canonical_section,
                r.count,
                r.count_with_length,
                round(r.total_lf, 2),
                r.unknown_lengths,
                r.needs_review,
            ]
        )
    ws2 = wb.create_sheet("Members")
    ws2.append(MEMBER_COLUMNS)
    for m in members:
        ws2.append(
            [
                m.id,
                m.level,
                m.sheet_no,
                m.start_grid,
                m.end_grid,
                m.member_mark,
                m.canonical_section,
                m.family,
                m.member_type,
                m.status,
                m.length_in,
                m.length_ft,
                m.length_display,
                m.length_source,
                m.confidence_id,
                m.confidence_geom,
                m.confidence_length,
                m.confidence_level,
                m.review_state,
                m.status_color,
                " | ".join(m.notes),
            ]
        )
    by_level: dict[str, list[SummaryRow]] = defaultdict(list)
    for r in rows:
        by_level[r.level].append(r)
    wb.save(str(path))
