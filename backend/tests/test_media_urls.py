"""Public media URL normalization."""

from __future__ import annotations

import os

from app.core.media import normalize_public_media_url


def test_normalize_localhost_to_relative_when_base_empty(monkeypatch):
    monkeypatch.delenv("MEDIA_PUBLIC_BASE_URL", raising=False)
    os.environ["MEDIA_PUBLIC_BASE_URL"] = ""
    from app.core.config import get_settings

    get_settings.cache_clear()
    try:
        assert (
            normalize_public_media_url(
                "http://localhost:8000/media/events/abc/file.png"
            )
            == "/media/events/abc/file.png"
        )
        assert normalize_public_media_url("/media/events/abc/file.png") == (
            "/media/events/abc/file.png"
        )
        assert (
            normalize_public_media_url("https://cdn.example.com/x.png")
            == "https://cdn.example.com/x.png"
        )
    finally:
        get_settings.cache_clear()


def test_normalize_applies_public_base(monkeypatch):
    monkeypatch.setenv("MEDIA_PUBLIC_BASE_URL", "https://api.example.com")
    from app.core.config import get_settings

    get_settings.cache_clear()
    try:
        assert (
            normalize_public_media_url(
                "http://localhost:8000/media/events/abc/file.png"
            )
            == "https://api.example.com/media/events/abc/file.png"
        )
        assert (
            normalize_public_media_url("/media/events/abc/file.png")
            == "https://api.example.com/media/events/abc/file.png"
        )
    finally:
        get_settings.cache_clear()
