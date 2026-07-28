"""Phase 7 — upload validation, dangerous types, EXIF stripping."""

from __future__ import annotations

import io
from uuid import uuid4

import pytest
from PIL import Image

from app.core.media import ALLOWED_IMAGE_CONTENT_TYPES, LocalMediaStorage, MAX_UPLOAD_BYTES
from app.memories.image_processing import MemoryImageError, process_memory_image, validate_external_gallery_url


def _jpeg_with_exif() -> bytes:
    img = Image.new("RGB", (400, 300), (100, 150, 200))
    exif = img.getexif()
    exif[0x010E] = "Phase7 test"
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    return buf.getvalue()


def test_memory_rejects_svg():
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
    with pytest.raises(MemoryImageError, match="Unrecognized|unsupported"):
        process_memory_image(
            data=svg, declared_content_type="image/svg+xml", event_id=uuid4()
        )


def test_event_public_storage_allows_svg_by_design():
    """Event gallery uploads allow SVG; memories pipeline does not."""
    storage = LocalMediaStorage()
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"></svg>'
    stored = storage.store_bytes(
        data=svg,
        filename="x.svg",
        content_type="image/svg+xml",
        folder="events/test",
    )
    assert stored.key.endswith(".svg")


def test_oversized_public_upload_rejected():
    storage = LocalMediaStorage()
    with pytest.raises(ValueError, match="5MB"):
        storage.store_bytes(
            data=b"x" * (MAX_UPLOAD_BYTES + 1),
            filename="big.jpg",
            content_type="image/jpeg",
            folder="events/test",
        )


def test_memory_rejects_mime_spoof():
    fake = b"not-an-image-at-all"
    with pytest.raises(MemoryImageError, match="Unrecognized"):
        process_memory_image(data=fake, declared_content_type="image/png", event_id=uuid4())


def test_memory_strips_exif_and_outputs_webp():
    from pathlib import Path

    from app.core.config import get_settings

    raw = _jpeg_with_exif()
    processed = process_memory_image(
        data=raw, declared_content_type="image/jpeg", event_id=uuid4()
    )
    assert processed.mime_type == "image/webp"
    assert processed.width <= 1800
    data = (Path(get_settings().media_root) / processed.display_key).read_bytes()
    with Image.open(io.BytesIO(data)) as out:
        exif = out.getexif()
        assert not exif or 0x8825 not in exif  # no GPS IFD


def test_external_gallery_ssrf_schemes_blocked():
    for bad in ("javascript:alert(1)", "data:text/html,x", "file:///etc/passwd"):
        with pytest.raises(ValueError):
            validate_external_gallery_url(bad)


def test_allowed_image_types_documented():
    assert "image/jpeg" in ALLOWED_IMAGE_CONTENT_TYPES
    assert "image/svg+xml" in ALLOWED_IMAGE_CONTENT_TYPES  # public events only
