"""Discovery crawler for PUBLIC manufacturer / listing-body document sites.

Starting from seed pages, follows links within the allowed hosts (same registry allowlist as the
fetcher), honours robots.txt and a polite delay, and records every document link found (PDF,
XLS/XLSX, DOCX, CSV) with the page it was found on, its link text, and a first guess at the
manufacturer, product and document kind from the URL and link text. Discovered documents are
written as registry entries (``status: discovered``) so they can be fetched, versioned, and later
classified by the inventory tool. Nothing is parsed or promoted here.

Deliberately excluded: anything requiring a login (UL Product iQ, ICC premium), and any host not
on the allowlist.
"""

from __future__ import annotations

import json
import re
import time
import urllib.request
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.robotparser import RobotFileParser

from ffs.sources.fetch import USER_AGENT

DOC_EXT = (".pdf", ".xlsx", ".xlsm", ".xls", ".docx", ".csv", ".zip")
_KIND_HINTS = [
    (r"sds|msds|safety[-_ ]data", "sds"),
    (r"tds|pds|data[-_ ]?sheet|product[-_ ]data", "product_data"),
    (r"primer|topcoat|top[-_ ]coat", "primer_topcoat_list"),
    (r"thickness|w-?d|design[-_ ]?(?:list|chart|table|directory)|ul[-_ ]?design", "design_listing"),
    (r"application|install|applicator|manual", "application_guide"),
    (r"bulletin|tech[-_ ]?(?:release|note)", "technical_bulletin"),
    (r"warranty", "warranty"),
    (r"esr-|evaluation|certificat|listing", "listing_report"),
    (r"spec|csi|07[-_ ]?81", "specification"),
    (r"leed|voc|hpd|epd", "sustainability_compliance"),
]
_MFR_HINTS = [
    (r"isolatek|cafco|blaze|fendolite|sprayfilm|firesolve", "Isolatek"),
    (r"gcpat|monokote|grace", "GCP"),
    (r"carboline|pyrocrete|thermo-?sorb|pyrolite|thermo-?lag", "Carboline"),
    (r"sherwin|firetex", "Sherwin-Williams"),
    (r"ppg|pitt-?char|steelguard", "PPG"),
    (r"hilti", "Hilti"),
    (r"international-pc|interchar|chartek|akzo", "AkzoNobel"),
    (r"icc-es|iccsafe", "ICC"),
    (r"intertek", "Intertek"),
    (r"aisc", "AISC"),
]


class _Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self._href = href
                self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            self.links.append((self._href, re.sub(r"\s+", " ", " ".join(self._text)).strip()))
            self._href = None


@dataclass
class Discovered:
    url: str
    found_on: str
    link_text: str
    manufacturer_guess: str | None
    kind_guess: str | None
    discovered_at: str


@dataclass
class CrawlReport:
    seeds: list[str]
    pages_visited: int
    documents: list[Discovered]
    skipped_hosts: list[str] = field(default_factory=list)
    robots_blocked: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _norm(url: str) -> str:
    p = urlparse(url)
    return urlunparse((p.scheme.lower(), p.netloc.lower(), p.path, "", p.query, ""))


def _guess(patterns, *texts) -> str | None:
    hay = " ".join(t.lower() for t in texts if t)
    for rx, label in patterns:
        if re.search(rx, hay):
            return label
    return None


def crawl(
    seeds: list[str],
    allowed_hosts: list[str],
    max_pages: int = 200,
    max_depth: int = 3,
    delay_s: float = 1.0,
    opener=None,
    sleep=time.sleep,
) -> CrawlReport:
    opener = opener or urllib.request.build_opener()
    allowed = {h.lower() for h in allowed_hosts}
    robots: dict[str, RobotFileParser | None] = {}
    seen: set[str] = set()
    docs: dict[str, Discovered] = {}
    rep = CrawlReport(seeds, 0, [])
    q: deque[tuple[str, int]] = deque((s, 0) for s in seeds)

    def allowed_by_robots(url: str) -> bool:
        p = urlparse(url)
        key = f"{p.scheme}://{p.netloc}"
        if key not in robots:
            rp = RobotFileParser()
            try:
                req = urllib.request.Request(
                    key + "/robots.txt", headers={"User-Agent": USER_AGENT}
                )
                with opener.open(req, timeout=20) as r:
                    rp.parse(r.read().decode("utf-8", "replace").splitlines())
                robots[key] = rp
            except Exception:  # noqa: BLE001
                robots[key] = None
        rp = robots[key]
        return True if rp is None else rp.can_fetch(USER_AGENT, url)

    while q and rep.pages_visited < max_pages:
        url, depth = q.popleft()
        url = _norm(url)
        if url in seen:
            continue
        seen.add(url)
        host = (urlparse(url).hostname or "").lower()
        if host not in allowed:
            if host and host not in rep.skipped_hosts:
                rep.skipped_hosts.append(host)
            continue
        if not allowed_by_robots(url):
            rep.robots_blocked.append(url)
            continue
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with opener.open(req, timeout=30) as r:
                ctype = (r.headers.get("Content-Type") or "").lower()
                if "html" not in ctype:
                    continue
                html = r.read(2_000_000).decode("utf-8", "replace")
        except Exception as ex:  # noqa: BLE001
            rep.errors.append(f"{url}: {type(ex).__name__}")
            continue
        rep.pages_visited += 1
        parser = _Links()
        try:
            parser.feed(html)
        except Exception:  # noqa: BLE001
            pass
        for href, text in parser.links:
            if href.startswith(("mailto:", "tel:", "javascript:", "#")):
                continue
            target = _norm(urljoin(url, href))
            thost = (urlparse(target).hostname or "").lower()
            path = urlparse(target).path.lower()
            if path.endswith(DOC_EXT):
                if thost in allowed and target not in docs and not allowed_by_robots(target):
                    rep.robots_blocked.append(target)
                elif thost in allowed and target not in docs:
                    docs[target] = Discovered(
                        target,
                        url,
                        text[:200],
                        _guess(_MFR_HINTS, target, text, host),
                        _guess(_KIND_HINTS, path, text),
                        datetime.now(UTC).isoformat(timespec="seconds"),
                    )
                elif thost not in allowed and thost not in rep.skipped_hosts:
                    rep.skipped_hosts.append(thost)
            elif thost not in allowed:
                if thost and thost not in rep.skipped_hosts:
                    rep.skipped_hosts.append(thost)
            elif depth < max_depth and target not in seen:
                q.append((target, depth + 1))
        if delay_s:
            sleep(delay_s)
    rep.documents = list(docs.values())
    return rep


def merge_into_registry(rep: CrawlReport, registry: dict) -> int:
    """Add discovered documents to the registry as 'discovered' entries. Returns count added."""
    known = {s.get("url") for s in registry["sources"] if s.get("url")}
    added = 0
    for d in rep.documents:
        if d.url in known:
            continue
        slug = re.sub(r"[^a-z0-9]+", "-", (Path(urlparse(d.url).path).stem or "doc").lower()).strip(
            "-"
        )[:60]
        registry["sources"].append(
            {
                "id": f"{(d.manufacturer_guess or 'web').lower()}-{slug}",
                "manufacturer": d.manufacturer_guess,
                "product": None,
                "kind": d.kind_guess or "unknown",
                "url": d.url,
                "status": "discovered",
                "found_on": d.found_on,
                "link_text": d.link_text,
                "discovered_at": d.discovered_at,
            }
        )
        known.add(d.url)
        added += 1
    return added


def write_report(rep: CrawlReport, path: str | Path) -> None:
    Path(path).write_text(json.dumps(asdict(rep), indent=1), encoding="utf-8")
