"""Parse sitemap index / urlset — same-origin only."""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from app.assistant.constants import (
    ALLOWED_KNOWLEDGE_HOST_SUFFIXES,
    SITEMAP_FORBIDDEN_EXACT_PATHS,
    SITEMAP_FORBIDDEN_PATH_PREFIXES,
)
from app.core.config import get_settings

logger = logging.getLogger(__name__)

_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
_MAX_URLS = 2000
_FETCH_TIMEOUT = 20


def _origin_hosts() -> set[str]:
    settings = get_settings()
    hosts: set[str] = set()
    for raw in (
        getattr(settings, "frontend_url", "") or "",
        "https://padeya.com",
        "https://www.padeya.com",
        "http://localhost:3000",
    ):
        try:
            host = urlparse(raw).hostname
            if host:
                hosts.add(host.lower())
        except Exception:
            continue
    return hosts


def is_allowed_knowledge_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    host = (parsed.hostname or "").lower()
    if not host:
        return False
    origins = _origin_hosts()
    if host in origins:
        return True
    for suffix in ALLOWED_KNOWLEDGE_HOST_SUFFIXES:
        if host == suffix or host.endswith("." + suffix):
            return True
    return False


def normalize_url(url: str, *, base: str | None = None) -> str:
    raw = (url or "").strip()
    if base:
        raw = urljoin(base, raw)
    parsed = urlparse(raw)
    # Drop fragment; normalize trailing slash for non-root
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    clean = parsed._replace(fragment="", path=path, query="")
    return clean.geturl()


def is_forbidden_path(path: str) -> bool:
    normalized = path if path.startswith("/") else f"/{path}"
    if normalized in SITEMAP_FORBIDDEN_EXACT_PATHS:
        return True
    for prefix in SITEMAP_FORBIDDEN_PATH_PREFIXES:
        if normalized == prefix or normalized.startswith(prefix + "/"):
            return True
    return False


def _local_tag(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def parse_sitemap_xml(xml_text: str, *, base_url: str) -> tuple[list[str], list[str]]:
    """Return (page_urls, child_sitemap_urls)."""
    page_urls: list[str] = []
    child_sitemaps: list[str] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return [], []
    root_tag = _local_tag(root.tag)
    if root_tag == "sitemapindex":
        for el in root.iter():
            if _local_tag(el.tag) == "loc" and el.text:
                child_sitemaps.append(normalize_url(el.text.strip(), base=base_url))
    elif root_tag == "urlset":
        for el in root.iter():
            if _local_tag(el.tag) == "loc" and el.text:
                page_urls.append(normalize_url(el.text.strip(), base=base_url))
    else:
        # Fallback: any <loc>
        for el in root.iter():
            if _local_tag(el.tag) == "loc" and el.text:
                page_urls.append(normalize_url(el.text.strip(), base=base_url))
    return page_urls, child_sitemaps


def fetch_url_text(url: str, *, timeout: int = _FETCH_TIMEOUT) -> str:
    req = Request(
        url,
        headers={"User-Agent": "PadeyaAssistantKnowledgeBot/1.0"},
        method="GET",
    )
    with urlopen(req, timeout=timeout) as resp:  # noqa: S310 — URL pre-validated
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")


def collect_sitemap_urls(
    sitemap_url: str,
    *,
    max_urls: int = _MAX_URLS,
    max_child_sitemaps: int = 20,
) -> list[str]:
    """Fetch sitemap index + children; filter same-origin + forbidden paths."""
    if not is_allowed_knowledge_url(sitemap_url):
        logger.warning("assistant.sitemap_rejected url_host_not_allowed")
        return []
    seen_pages: list[str] = []
    seen_set: set[str] = set()
    try:
        xml_text = fetch_url_text(sitemap_url)
    except Exception:
        logger.exception("assistant.sitemap_fetch_failed")
        return []
    pages, children = parse_sitemap_xml(xml_text, base_url=sitemap_url)
    to_fetch = [u for u in children if is_allowed_knowledge_url(u)][:max_child_sitemaps]

    def _add(url: str) -> None:
        if len(seen_pages) >= max_urls:
            return
        if not is_allowed_knowledge_url(url):
            return
        path = urlparse(url).path or "/"
        if is_forbidden_path(path):
            return
        if url in seen_set:
            return
        seen_set.add(url)
        seen_pages.append(url)

    for u in pages:
        _add(u)

    for child in to_fetch:
        try:
            child_xml = fetch_url_text(child)
            child_pages, _ = parse_sitemap_xml(child_xml, base_url=child)
            for u in child_pages:
                _add(u)
                if len(seen_pages) >= max_urls:
                    break
        except Exception:
            logger.exception("assistant.sitemap_child_failed")
    return seen_pages


def map_bounded(
    items: list[str],
    fn: Callable[[str], Any],
    *,
    max_workers: int = 4,
) -> list[Any]:
    """Run fn over items with bounded concurrency."""
    if not items:
        return []
    results: list[Any] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(fn, item): item for item in items}
        for fut in as_completed(futures):
            try:
                results.append(fut.result())
            except Exception:
                results.append(None)
    return results
