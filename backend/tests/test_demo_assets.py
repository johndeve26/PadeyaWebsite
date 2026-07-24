"""Tests for demo asset URL helpers."""

from __future__ import annotations

import pytest

from app.core.config import get_settings
from app.demo import assets


@pytest.fixture()
def frontend_padeya(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("FRONTEND_URL", "https://padeya.com")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_normalize_demo_asset_url_rewrites_old_origin(frontend_padeya) -> None:
    old = (
        "http://padeya.smartlancedesigns.com/demo/events/"
        "mainland-vibes-summer-gallery.svg"
    )
    assert assets.normalize_demo_asset_url(old) == (
        "https://padeya.com/demo/events/mainland-vibes-summer-gallery.svg"
    )


def test_normalize_demo_asset_url_handles_relative_path(frontend_padeya) -> None:
    assert assets.normalize_demo_asset_url("/demo/events/afrobeats-night-live.svg") == (
        "https://padeya.com/demo/events/afrobeats-night-live.svg"
    )


def test_normalize_demo_asset_url_leaves_external_urls(frontend_padeya) -> None:
    external = "https://cdn.example.com/poster.jpg"
    assert assets.normalize_demo_asset_url(external) == external
