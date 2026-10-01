"""PDF ingest: text spans with coordinates, vector segments, raster detection.

Everything here is a FACT source. Coordinates are PDF points in *unrotated page space*
(PyMuPDF's default), origin top-left, y down.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

import pymupdf

from ffs.core.assertions import ExtractionPath


@dataclass
class TextSpan:
    text: str
    bbox: tuple[float, float, float, float]
    size: float
    rotation_deg: float  # 0, 90, 180, 270 (text direction)
    font: str = ""
    block: int = -1
    line: int = -1

    @property
    def center(self) -> tuple[float, float]:
        x0, y0, x1, y1 = self.bbox
        return ((x0 + x1) / 2, (y0 + y1) / 2)


@dataclass
class Segment:
    x0: float
    y0: float
    x1: float
    y1: float
    width: float = 0.0
    color: tuple[float, float, float] | None = None
    dashed: bool = False

    @property
    def length(self) -> float:
        return math.hypot(self.x1 - self.x0, self.y1 - self.y0)

    @property
    def angle_deg(self) -> float:
        """Direction angle in [0, 180)."""
        a = math.degrees(math.atan2(self.y1 - self.y0, self.x1 - self.x0)) % 180.0
        return a

    @property
    def midpoint(self) -> tuple[float, float]:
        return ((self.x0 + self.x1) / 2, (self.y0 + self.y1) / 2)


@dataclass
class Circle:
    cx: float
    cy: float
    r: float


@dataclass
class PageData:
    document: str
    page_index: int  # 0-based
    width: float
    height: float
    rotation: int
    spans: list[TextSpan] = field(default_factory=list)
    segments: list[Segment] = field(default_factory=list)
    circles: list[Circle] = field(default_factory=list)
    has_text_layer: bool = False
    has_vector_graphics: bool = False
    image_coverage: float = 0.0  # fraction of page area covered by images
    extraction_path: ExtractionPath = ExtractionPath.PDF_TEXT

    @property
    def page_number(self) -> int:
        return self.page_index + 1

    @property
    def likely_scanned(self) -> bool:
        return (not self.has_text_layer) and self.image_coverage > 0.5

    def text(self) -> str:
        return "\n".join(s.text for s in self.spans)


def _span_rotation(dir_vec: tuple[float, float]) -> float:
    dx, dy = dir_vec
    ang = math.degrees(math.atan2(-dy, dx)) % 360  # pymupdf dir: (1,0)=horizontal
    return float(round(ang / 90) * 90 % 360)


def extract_page(doc: pymupdf.Document, page_index: int, document_name: str) -> PageData:
    page = doc[page_index]
    rect = page.rect
    pd = PageData(
        document=document_name,
        page_index=page_index,
        width=rect.width,
        height=rect.height,
        rotation=page.rotation,
    )

    # --- text spans
    raw = page.get_text("dict", flags=pymupdf.TEXT_PRESERVE_WHITESPACE)
    for bi, block in enumerate(raw.get("blocks", [])):
        if block.get("type") != 0:
            continue
        for li, line in enumerate(block.get("lines", [])):
            rot = _span_rotation(tuple(line.get("dir", (1, 0))))
            for sp in line.get("spans", []):
                t = sp.get("text", "")
                if not t.strip():
                    continue
                pd.spans.append(
                    TextSpan(
                        text=t,
                        bbox=tuple(sp["bbox"]),
                        size=float(sp.get("size", 0.0)),
                        rotation_deg=rot,
                        font=sp.get("font", ""),
                        block=bi,
                        line=li,
                    )
                )
    pd.has_text_layer = len(pd.spans) > 0

    # --- vector segments (lines and polyline edges; curves ignored for framing)
    try:
        drawings = page.get_drawings()
    except Exception:  # pragma: no cover - defensive against malformed content streams
        drawings = []
    for d in drawings:
        width = float(d.get("width") or 0.0)
        color = d.get("color")
        dashed = bool(d.get("dashes") and d["dashes"] not in ("[] 0", "", None))
        items = d.get("items", [])
        n_curves = sum(1 for it in items if it[0] == "c")
        if n_curves >= 3 and d.get("closePath", False) or n_curves >= 4:
            r = d.get("rect")
            if (
                r is not None
                and r.width > 0
                and abs(r.width - r.height) <= 0.15 * max(r.width, r.height)
            ):
                pd.circles.append(
                    Circle((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2, (r.width + r.height) / 4)
                )
                continue
        for item in items:
            op = item[0]
            if op == "l":
                p0, p1 = item[1], item[2]
                pd.segments.append(Segment(p0.x, p0.y, p1.x, p1.y, width, color, dashed))
            elif op == "re":
                r = item[1]
                # thin rectangles are drawn as lines by many CAD exporters; keep edges
                corners = [(r.x0, r.y0), (r.x1, r.y0), (r.x1, r.y1), (r.x0, r.y1)]
                for i in range(4):
                    a, b = corners[i], corners[(i + 1) % 4]
                    pd.segments.append(Segment(a[0], a[1], b[0], b[1], width, color, dashed))
    pd.has_vector_graphics = len(pd.segments) > 0

    # --- image coverage
    area = rect.width * rect.height or 1.0
    covered = 0.0
    for img in page.get_images(full=True):
        try:
            for r in page.get_image_rects(img[0]):
                covered += r.width * r.height
        except Exception:  # pragma: no cover
            pass
    pd.image_coverage = min(1.0, covered / area)
    if pd.likely_scanned:
        pd.extraction_path = ExtractionPath.OCR  # OCR not yet implemented; flagged, not faked
    return pd


def load_pdf(path: str | Path, pages: list[int] | None = None) -> list[PageData]:
    """Load all (or selected 0-based) pages of a PDF into :class:`PageData` records."""
    path = Path(path)
    doc = pymupdf.open(path)
    idxs = pages if pages is not None else list(range(len(doc)))
    out = [extract_page(doc, i, path.name) for i in idxs]
    doc.close()
    return out
