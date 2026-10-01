"""Vector overlay PDF for visual verification of a takeoff.

Draws, on a copy of the source page, each member's chain in its status colour
(green verified / yellow uncertain / red conflict / gray excluded), a box around the label,
and a length annotation. Nothing is burned into the background: the overlay is appended as
separate vector content so it can be toggled by deleting the annotation layer later.
"""

from __future__ import annotations

from pathlib import Path

import pymupdf

from ffs.takeoff.model import MemberRecord

_COLORS = {
    "green": (0.0, 0.6, 0.0),
    "yellow": (0.85, 0.65, 0.0),
    "red": (0.85, 0.0, 0.0),
    "gray": (0.5, 0.5, 0.5),
    "blue": (0.0, 0.3, 0.9),
}


def write_overlay(
    src_pdf: str | Path,
    page_index: int,
    members: list[MemberRecord],
    out_pdf: str | Path,
    legend: bool = True,
) -> None:
    doc = pymupdf.open(src_pdf)
    page = doc[page_index]
    shape = page.new_shape()
    for m in members:
        color = _COLORS[m.status_color]
        if m.start_xy and m.end_xy:
            shape.draw_line(m.start_xy, m.end_xy)
            shape.finish(color=color, width=4.0, stroke_opacity=0.55)
        for ev in m.evidence:
            if ev.page == page_index + 1:
                r = pymupdf.Rect(*ev.bbox)
                shape.draw_rect(r + (-2, -2, 2, 2))
                shape.finish(color=color, width=0.8)
                tag = f"{m.canonical_section}  {m.length_display}"
                if m.start_grid or m.end_grid:
                    tag += f"  [{m.start_grid or '?'}→{m.end_grid or '?'}]"
                shape.insert_text((r.x0, r.y0 - 3), tag, fontsize=5, color=color)
    if legend:
        x, y = 36, 36
        shape.draw_rect(pymupdf.Rect(x - 6, y - 12, x + 230, y + 62))
        shape.finish(color=(0, 0, 0), fill=(1, 1, 1), width=0.5, fill_opacity=0.9)
        shape.insert_text((x, y), "FFS TAKEOFF OVERLAY — NOT A CONSTRUCTION DOCUMENT", fontsize=6)
        for i, (name, desc) in enumerate(
            [
                ("green", "verified / high confidence"),
                ("yellow", "uncertain — review"),
                ("red", "conflict — review required"),
                ("gray", "excluded"),
            ]
        ):
            yy = y + 12 + i * 11
            shape.draw_line((x, yy - 2), (x + 20, yy - 2))
            shape.finish(color=_COLORS[name], width=3)
            shape.insert_text((x + 26, yy), desc, fontsize=6)
    shape.commit()
    out = pymupdf.open()
    out.insert_pdf(doc, from_page=page_index, to_page=page_index)
    out.save(out_pdf)
    out.close()
    doc.close()
