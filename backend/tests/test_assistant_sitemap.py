"""Unit tests for assistant sitemap parsing — no live network."""

from __future__ import annotations

from unittest.mock import patch

from app.assistant.knowledge.sitemap import (
    collect_sitemap_urls,
    is_allowed_knowledge_url,
    is_forbidden_path,
    normalize_url,
    parse_sitemap_xml,
)

SITEMAP_INDEX = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>https://padeya.com/sitemap-pages.xml</loc></sitemap>
  <sitemap><loc>https://evil.example/sitemap.xml</loc></sitemap>
</sitemapindex>
"""

URLSET = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://padeya.com/events/</loc></url>
  <url><loc>https://padeya.com/events</loc></url>
  <url><loc>https://padeya.com/help#faq</loc></url>
  <url><loc>https://padeya.com/admin/users</loc></url>
  <url><loc>https://padeya.com/dashboard/tickets</loc></url>
  <url><loc>https://padeya.com/checkout/pay</loc></url>
  <url><loc>https://padeya.com/host/events</loc></url>
  <url><loc>https://padeya.com/login</loc></url>
  <url><loc>https://evil.example/steal</loc></url>
  <url><loc>https://padeya.com/about</loc></url>
  <url><loc>https://padeya.com/events/search</loc></url>
</urlset>
"""


def test_parse_sitemap_index_and_urlset():
    pages, children = parse_sitemap_xml(SITEMAP_INDEX, base_url="https://padeya.com/sitemap.xml")
    assert pages == []
    assert "https://padeya.com/sitemap-pages.xml" in children
    assert any("evil.example" in c for c in children)

    pages2, children2 = parse_sitemap_xml(URLSET, base_url="https://padeya.com/sitemap-pages.xml")
    assert children2 == []
    assert "https://padeya.com/events" in pages2
    assert "https://padeya.com/about" in pages2


def test_normalize_trailing_slash_and_fragment():
    assert normalize_url("https://padeya.com/events/") == "https://padeya.com/events"
    assert normalize_url("https://padeya.com/help#faq") == "https://padeya.com/help"
    assert normalize_url("https://padeya.com/") == "https://padeya.com/"
    a = normalize_url("https://padeya.com/events/")
    b = normalize_url("https://padeya.com/events")
    assert a == b


def test_same_origin_restriction():
    assert is_allowed_knowledge_url("https://padeya.com/events") is True
    assert is_allowed_knowledge_url("https://www.padeya.com/about") is True
    assert is_allowed_knowledge_url("http://localhost:3000/help") is True
    assert is_allowed_knowledge_url("https://evil.example/x") is False
    assert is_allowed_knowledge_url("ftp://padeya.com/x") is False


def test_forbidden_private_routes():
    for path in (
        "/admin",
        "/admin/users",
        "/dashboard",
        "/dashboard/tickets",
        "/checkout",
        "/checkout/pay",
        "/host/events",
        "/login",
        "/register",
        "/api/v1/secret",
        "/events/search",
    ):
        assert is_forbidden_path(path) is True, path
    assert is_forbidden_path("/events") is False
    assert is_forbidden_path("/about") is False
    assert is_forbidden_path("/help") is False


def test_collect_filters_origin_forbidden_and_dedupes():
    def fake_fetch(url: str, **_: object) -> str:
        if url.endswith("sitemap.xml"):
            return SITEMAP_INDEX
        if "sitemap-pages" in url:
            return URLSET
        raise AssertionError(f"unexpected fetch {url}")

    with patch(
        "app.assistant.knowledge.sitemap.fetch_url_text",
        side_effect=fake_fetch,
    ):
        urls = collect_sitemap_urls("https://padeya.com/sitemap.xml")

    assert "https://padeya.com/events" in urls
    assert "https://padeya.com/about" in urls
    assert "https://padeya.com/help" in urls
    # Canonical dedupe: trailing slash variant collapsed
    assert urls.count("https://padeya.com/events") == 1
    # Forbidden / private
    assert not any("/admin" in u for u in urls)
    assert not any("/dashboard" in u for u in urls)
    assert not any("/checkout" in u for u in urls)
    assert not any("/host/" in u for u in urls)
    assert not any("/login" in u for u in urls)
    assert "https://padeya.com/events/search" not in urls
    # Off-origin rejected
    assert not any("evil.example" in u for u in urls)
