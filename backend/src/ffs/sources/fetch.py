"""Registry-driven fetcher for PUBLIC reference documents.

Rules (NFR-VER-01, ADR-0004):
* Only URLs whose host is in the registry's ``allowed_hosts`` are contacted. Anything else is
  refused, including UL Product iQ.
* ``robots.txt`` is honoured for the path being fetched.
* Each download is stored under ``<library>/<manufacturer>/<id>/<sha256[:12]>.<ext>`` and never
  overwritten; a ``manifest.jsonl`` records id, url, fetch time, status, ETag, Last-Modified,
  Content-Type, size, sha256, and whether the content changed since the previous fetch.
* Conditional requests (If-None-Match / If-Modified-Since) avoid re-downloading unchanged files.
* The fetcher only collects documents. It never parses or promotes anything to a rule.
"""

from __future__ import annotations

import hashlib
import json
import mimetypes
import re
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

USER_AGENT = "FFS-reference-fetcher/0.1 (+manual, registry-driven; contact: repo owner)"
REGISTRY_PATH = Path(__file__).with_name("registry.json")


@dataclass
class FetchResult:
    id: str
    url: str | None
    status: str  # fetched / unchanged / skipped_no_url / refused_host / robots_disallow / error
    http_status: int | None = None
    etag: str | None = None
    last_modified: str | None = None
    content_type: str | None = None
    size: int | None = None
    sha256: str | None = None
    stored_path: str | None = None
    changed: bool | None = None
    fetched_at: str = ""
    error: str | None = None


def load_registry(path: str | Path | None = None) -> dict:
    return json.loads(Path(path or REGISTRY_PATH).read_text(encoding="utf-8"))


def _host_allowed(url: str, allowed: list[str]) -> bool:
    host = urlparse(url).hostname or ""
    return host.lower() in {h.lower() for h in allowed}


def _robots_ok(url: str, opener) -> bool:
    p = urlparse(url)
    rp = RobotFileParser()
    try:
        req = urllib.request.Request(
            f"{p.scheme}://{p.netloc}/robots.txt", headers={"User-Agent": USER_AGENT}
        )
        with opener.open(req, timeout=20) as r:
            rp.parse(r.read().decode("utf-8", "replace").splitlines())
    except Exception:  # noqa: BLE001 - no robots.txt (404) or unreachable → allow per convention
        return True
    return rp.can_fetch(USER_AGENT, url)


def _previous(manifest: Path, source_id: str, url: str | None = None) -> dict | None:
    """Last successful record for this document: matched by URL first (ids may be renamed), then id."""
    if not manifest.exists():
        return None
    by_url = by_id = None
    for line in manifest.read_text(encoding="utf-8").splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("status") not in ("fetched", "unchanged"):
            continue
        if url and rec.get("url") == url:
            by_url = rec
        if rec.get("id") == source_id:
            by_id = rec
    return by_url or by_id


def fetch_all(
    library: str | Path,
    registry: dict | None = None,
    only: list[str] | None = None,
    opener=None,
) -> list[FetchResult]:
    registry = registry or load_registry()
    library = Path(library)
    library.mkdir(parents=True, exist_ok=True)
    manifest = library / "manifest.jsonl"
    opener = opener or urllib.request.build_opener()
    results: list[FetchResult] = []
    for src in registry["sources"]:
        if only and src["id"] not in only:
            continue
        now = datetime.now(UTC).isoformat(timespec="seconds")
        res = FetchResult(src["id"], src.get("url"), "skipped_no_url", fetched_at=now)
        if not src.get("url"):
            results.append(res)
            continue
        url = src["url"]
        if not _host_allowed(url, registry["allowed_hosts"]):
            res.status = "refused_host"
            results.append(res)
            _append(manifest, res)
            continue
        if not _robots_ok(url, opener):
            res.status = "robots_disallow"
            results.append(res)
            _append(manifest, res)
            continue
        prev = _previous(manifest, src["id"], url)
        headers = {"User-Agent": USER_AGENT}
        if prev and prev.get("etag"):
            headers["If-None-Match"] = prev["etag"]
        if prev and prev.get("last_modified"):
            headers["If-Modified-Since"] = prev["last_modified"]
        try:
            req = urllib.request.Request(url, headers=headers)
            with opener.open(req, timeout=60) as r:
                data = r.read()
                res.http_status = r.status
                res.etag = r.headers.get("ETag")
                res.last_modified = r.headers.get("Last-Modified")
                res.content_type = r.headers.get("Content-Type")
        except urllib.error.HTTPError as ex:
            if ex.code == 304 and prev:
                res.status = "unchanged"
                res.http_status = 304
                res.sha256 = prev.get("sha256")
                res.stored_path = prev.get("stored_path")
                res.changed = False
                results.append(res)
                _append(manifest, res)
                continue
            res.status = "error"
            res.http_status = ex.code
            res.error = str(ex)[:200]
            results.append(res)
            _append(manifest, res)
            continue
        except Exception as ex:  # noqa: BLE001
            res.status = "error"
            res.error = f"{type(ex).__name__}: {ex}"[:200]
            results.append(res)
            _append(manifest, res)
            continue
        sha = hashlib.sha256(data).hexdigest()
        res.sha256 = sha
        res.size = len(data)
        ext = (
            mimetypes.guess_extension((res.content_type or "").split(";")[0].strip())
            or Path(urlparse(url).path).suffix
            or ".bin"
        )
        if ext == ".jpe":
            ext = ".jpg"
        folder = (
            library / re.sub(r"[^A-Za-z0-9_-]+", "_", src.get("manufacturer") or "misc") / src["id"]
        )
        folder.mkdir(parents=True, exist_ok=True)
        dest = folder / f"{sha[:12]}{ext}"
        if prev and prev.get("sha256") == sha:
            res.status = "unchanged"
            res.changed = False
            res.stored_path = prev.get("stored_path")
        else:
            if not dest.exists():
                dest.write_bytes(data)
            res.status = "fetched"
            res.changed = prev is not None
            res.stored_path = str(dest.relative_to(library))
        results.append(res)
        _append(manifest, res)
    return results


def _append(manifest: Path, res: FetchResult) -> None:
    with manifest.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(res)) + "\n")
