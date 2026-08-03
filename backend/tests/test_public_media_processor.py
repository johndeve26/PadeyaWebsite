"""Tests for shared public media processor and contract."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from app.public_media.contract import build_public_media_payload, select_variant_url
from app.public_media.processor import PublicMediaProcessingError, encode_variants
from app.public_media.roles import MediaRole, policy_for


def _png_bytes(width: int = 800, height: int = 600, color=(20, 120, 200)) -> bytes:
    img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _rgba_png(width: int = 256, height: int = 256) -> bytes:
    img = Image.new("RGBA", (width, height), (10, 200, 40, 128))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_encode_event_cover_variants_bounded_and_ordered():
    raw = _png_bytes(3000, 2000)
    processed = encode_variants(
        data=raw,
        declared_content_type="image/png",
        role=MediaRole.EVENT_COVER,
    )
    types = [v.variant.value for v in processed.variants]
    assert "thumbnail" in types
    assert "card" in types
    assert "display" in types
    assert "full" in types
    by = {v.variant.value: v for v in processed.variants}
    assert by["thumbnail"].width <= 320
    assert by["card"].width <= 960
    assert by["display"].width <= 1920
    assert by["full"].width <= 2400
    assert by["full"].width >= by["card"].width
    assert by["card"].width >= by["thumbnail"].width
    assert all(v.mime_type == "image/webp" for v in processed.variants)
    assert sum(len(v.data) for v in processed.variants) < len(raw)


def test_encode_does_not_upscale_small_source():
    raw = _png_bytes(120, 80)
    processed = encode_variants(
        data=raw, declared_content_type="image/png", role=MediaRole.GENERAL
    )
    for v in processed.variants:
        assert v.width <= 120
        assert v.height <= 80


def test_logo_preserves_alpha_path():
    raw = _rgba_png()
    policy = policy_for(MediaRole.SPONSOR_LOGO)
    assert policy.preserve_alpha is True
    processed = encode_variants(
        data=raw,
        declared_content_type="image/png",
        role=MediaRole.SPONSOR_LOGO,
    )
    assert processed.variants
    assert all(v.mime_type == "image/webp" for v in processed.variants)


def test_rejects_mime_spoof():
    raw = _png_bytes()
    with pytest.raises(PublicMediaProcessingError):
        encode_variants(
            data=raw,
            declared_content_type="image/jpeg",
            role=MediaRole.GENERAL,
        )


def test_rejects_svg_active_content():
    svg = b'<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg"></svg>'
    with pytest.raises(PublicMediaProcessingError):
        encode_variants(
            data=svg,
            declared_content_type="image/png",
            role=MediaRole.GENERAL,
        )


def test_rejects_oversized_byte_payload():
    policy = policy_for(MediaRole.GENERAL)
    huge = b"\xff\xd8\xff" + b"0" * (policy.max_source_bytes + 10)
    with pytest.raises(PublicMediaProcessingError):
        encode_variants(
            data=huge,
            declared_content_type="image/jpeg",
            role=MediaRole.GENERAL,
        )


def test_select_variant_fallback_order():
    media = {
        "thumbnail_url": "https://media.example/t.webp",
        "card_url": "https://media.example/c.webp",
        "display_url": "https://media.example/d.webp",
        "full_url": "https://media.example/f.webp",
        "variants": {},
    }
    assert select_variant_url(media, intent="thumbnail") == media["thumbnail_url"]
    assert select_variant_url(media, intent="full") == media["full_url"]
    assert (
        select_variant_url({"url": "https://legacy"}, intent="card", legacy_url=None)
        == "https://legacy"
    )
    assert (
        select_variant_url(None, intent="display", legacy_url="https://legacy/x.jpg")
        == "https://legacy/x.jpg"
    )


def test_public_payload_never_includes_source_key():
    payload = build_public_media_payload(
        asset_id="00000000-0000-0000-0000-000000000001",
        role="event_cover",
        variants={
            "thumbnail": {"url": "https://x/t.webp", "width": 320, "height": 200},
            "display": {"url": "https://x/d.webp", "width": 1600, "height": 1000},
            "full": {"url": "https://x/f.webp", "width": 2400, "height": 1500},
        },
    )
    blob = str(payload)
    assert "source" not in blob.lower() or "source_key" not in blob
    assert payload["url"] == "https://x/d.webp"
    assert payload["full_url"] == "https://x/f.webp"
