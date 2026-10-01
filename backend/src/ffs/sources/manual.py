"""Human-assisted import for documents the fetcher may not retrieve itself.

Some official hosts disallow automated clients (robots.txt ``Disallow: /``) or sit behind a
browser challenge. The collectors record such documents in the registry with ``url: null`` and a
``manual_url`` a person can open in a browser. This module turns those entries into a download
list and files the saved copies into the library with the same manifest provenance as a fetch,
marked ``method: manual``. A file that does not match a registry entry by name is reported and
left alone: nothing is filed under a guessed identity.
"""

from __future__ import annotations

import csv
import hashlib
import html
import json
import mimetypes
import re
import shutil
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from ffs.sources.fetch import FetchResult, _previous

_URL_IN_NOTES = re.compile(r"https?://\S+")


@dataclass
class ManualItem:
    id: str
    manufacturer: str
    product: str | None
    kind: str | None
    file_name: str | None
    manual_url: str
    reason: str | None
    registry: str


def _manual_url(src: dict) -> str | None:
    if src.get("manual_url"):
        return src["manual_url"]
    m = _URL_IN_NOTES.search(src.get("notes") or "")
    return m.group(0) if m else None


def _name_from_url(url: str) -> str | None:
    q = parse_qs(urlparse(url).query)
    for key in ("name", "filename", "file"):
        if q.get(key):
            return unquote(q[key][0].replace("+", " "))
    tail = unquote(urlparse(url).path.rsplit("/", 1)[-1])
    return tail or None


def manual_items(registries: list[Path]) -> list[ManualItem]:
    items: list[ManualItem] = []
    for reg_path in registries:
        reg = json.loads(Path(reg_path).read_text(encoding="utf-8"))
        for src in reg.get("sources", []):
            if src.get("url"):
                continue
            url = _manual_url(src)
            if not url:
                continue
            items.append(
                ManualItem(
                    id=src["id"],
                    manufacturer=src.get("manufacturer") or Path(reg_path).stem,
                    product=src.get("product"),
                    kind=src.get("kind"),
                    file_name=src.get("file_name") or _name_from_url(url),
                    manual_url=url,
                    reason=src.get("status") or src.get("reason"),
                    registry=str(reg_path),
                )
            )
    return items


def write_manual_list(items: list[ManualItem], out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "manual_downloads.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["manufacturer", "product", "kind", "file_name", "manual_url", "reason", "id"])
        for it in items:
            w.writerow(
                [
                    it.manufacturer,
                    it.product,
                    it.kind,
                    it.file_name,
                    it.manual_url,
                    it.reason,
                    it.id,
                ]
            )
    html_path = out_dir / "manual_downloads.html"
    parts = [
        "<!doctype html><meta charset='utf-8'><title>FFS manual downloads</title>",
        "<style>body{font-family:system-ui;margin:2rem;max-width:70rem}li{margin:.3rem 0}"
        "small{color:#666}</style>",
        "<h1>Documents to download by hand</h1>",
        "<p>Open each link, save the file with the name shown, drop all files in one folder, then "
        "run <code>ffs import-manual --drop-dir &lt;folder&gt;</code>. The fetcher did not "
        "retrieve these because the host asks automated clients to stay out.</p>",
    ]
    by_mfr: dict[str, dict[str, list[ManualItem]]] = {}
    for it in items:
        by_mfr.setdefault(it.manufacturer, {}).setdefault(it.product or "", []).append(it)
    for mfr in sorted(by_mfr):
        parts.append(f"<h2>{html.escape(mfr)}</h2>")
        for prod in sorted(by_mfr[mfr]):
            if prod:
                parts.append(f"<h3>{html.escape(prod)}</h3>")
            parts.append("<ol>")
            for it in by_mfr[mfr][prod]:
                meta = html.escape(f"{it.kind or ''} · {it.reason or ''}")
                parts.append(
                    f"<li><a href='{html.escape(it.manual_url)}' target='_blank'>"
                    f"{html.escape(it.file_name or it.id)}</a> <small>{meta}</small></li>"
                )
            parts.append("</ol>")
    html_path.write_text("\n".join(parts) + "\n", encoding="utf-8")
    return html_path, csv_path


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def import_manual(
    drop_dir: Path, registries: list[Path], library: Path, now: datetime | None = None
) -> tuple[list[FetchResult], list[str]]:
    """File every document in ``drop_dir`` that matches a manual item by file name.

    Returns (results, unmatched file names). Matching is by exact name, then by the name with
    punctuation and case removed; anything looser would file a document under the wrong identity.
    """
    items = manual_items(registries)
    by_name: dict[str, ManualItem] = {}
    for it in items:
        if it.file_name:
            by_name.setdefault(_norm(it.file_name), it)
    manifest = library / "manifest.jsonl"
    stamp = (now or datetime.now(UTC)).isoformat()
    results: list[FetchResult] = []
    unmatched: list[str] = []
    for f in sorted(p for p in Path(drop_dir).iterdir() if p.is_file()):
        it = by_name.get(_norm(f.name))
        if not it:
            unmatched.append(f.name)
            continue
        data = f.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        ext = f.suffix.lower() or ".bin"
        res = FetchResult(
            id=it.id,
            url=it.manual_url,
            status="manual",
            content_type=mimetypes.guess_type(f.name)[0],
            size=len(data),
            sha256=sha,
            fetched_at=stamp,
        )
        prev = _previous(manifest, it.id, it.manual_url)
        if prev and prev.get("sha256") == sha:
            res.status = "unchanged"
            res.changed = False
            res.stored_path = prev.get("stored_path")
        else:
            dest = library / it.manufacturer / it.id / f"{sha[:12]}{ext}"
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                shutil.copyfile(f, dest)
            res.stored_path = str(dest.relative_to(library))
            res.changed = prev is not None
        with manifest.open("a", encoding="utf-8") as mf:
            row = asdict(res)
            row["method"] = "manual"
            row["drop_file"] = f.name
            mf.write(json.dumps(row) + "\n")
        results.append(res)
    return results, unmatched
