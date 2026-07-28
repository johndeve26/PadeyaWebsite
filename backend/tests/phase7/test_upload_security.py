"""Phase 7 — upload validation, dangerous types, EXIF stripping."""

from __future__ import annotations

import io
from pathlib import Path
from uuid import uuid4

import pytest
from PIL import Image

from app.core.config import get_settings
from app.core.media import ALLOWED_IMAGE_CONTENT_TYPES, LocalMediaStorage, MAX_UPLOAD_BYTES
from app.core.public_image_validation import (
    PublicImageValidationError,
    validate_public_raster_upload,
)
from app.memories.image_processing import MemoryImageError, process_memory_image, validate_external_gallery_url


def _jpeg_with_exif() -> bytes:
    img = Image.new("RGB", (400, 300), (100, 150, 200))
    exif = img.getexif()
    exif[0x010E] = "Phase7 test"
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    return buf.getvalue()


def _raster_bytes(fmt: str) -> bytes:
    img = Image.new("RGB", (12, 12), (40, 80, 120))
    buf = io.BytesIO()
    if fmt == "GIF":
        img.save(buf, format="GIF")
    else:
        img.save(buf, format=fmt)
    return buf.getvalue()


@pytest.mark.parametrize(
    ("payload", "declared", "filename"),
    [
        (
            b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="10" height="10"/></svg>',
            "image/svg+xml",
            "shape.svg",
        ),
        (
            b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
            "image/svg+xml",
            "evil.svg",
        ),
        (
            b'<svg xmlns="http://www.w3.org/2000/svg"><image href="https://evil.test/x.png"/></svg>',
            "image/svg+xml",
            "external.svg",
        ),
        (
            b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="10" height="10"/></svg>',
            "image/png",
            "spoof.png",
        ),
        (
            b"<!DOCTYPE html><html><body>hi</body></html>",
            "image/jpeg",
            "page.jpg",
        ),
        (
            b"alert('owned')",
            "image/png",
            "script.png",
        ),
        (
            b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="10" height="10"/></svg>',
            "image/jpeg",
            "spoof-body.jpg",
        ),
    ],
)
def test_public_storage_rejects_active_or_spoofed_uploads(
    payload: bytes, declared: str, filename: str
) -> None:
    storage = LocalMediaStorage()
    before = _count_public_files()
    with pytest.raises(ValueError):
        storage.store_bytes(
            data=payload,
            filename=filename,
            content_type=declared,
            folder="events/test",
        )
    assert _count_public_files() == before


def test_public_storage_accepts_valid_raster_images() -> None:
    storage = LocalMediaStorage()
    cases = [
        ("JPEG", "image/jpeg", ".jpg"),
        ("PNG", "image/png", ".png"),
        ("WEBP", "image/webp", ".webp"),
        ("GIF", "image/gif", ".gif"),
    ]
    for fmt, declared, ext in cases:
        data = _raster_bytes(fmt)
        stored = storage.store_bytes(
            data=data,
            filename=f"ok{ext}",
            content_type=declared,
            folder="events/test",
        )
        assert stored.key.endswith(ext)
        path = Path(get_settings().media_root) / stored.key
        assert path.is_file()
        storage.delete(stored.key)


def test_public_storage_rejects_malformed_raster() -> None:
    storage = LocalMediaStorage()
    corrupt = b"\x89PNG\r\n\x1a\n" + b"not-a-real-png"
    with pytest.raises(ValueError, match="Invalid|corrupt|Unrecognized"):
        storage.store_bytes(
            data=corrupt,
            filename="bad.png",
            content_type="image/png",
            folder="events/test",
        )


def test_validate_public_raster_uses_sniff_not_filename() -> None:
    png = _raster_bytes("PNG")
    validated = validate_public_raster_upload(
        png, declared_content_type="image/png"
    )
    assert validated.content_type == "image/png"
    with pytest.raises(PublicImageValidationError):
        validate_public_raster_upload(
            png, declared_content_type="image/jpeg"
        )


def test_memory_rejects_svg() -> None:
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
    with pytest.raises(MemoryImageError, match="Unrecognized|unsupported"):
        process_memory_image(
            data=svg, declared_content_type="image/svg+xml", event_id=uuid4()
        )


def test_oversized_public_upload_rejected() -> None:
    storage = LocalMediaStorage()
    with pytest.raises(ValueError, match="5MB"):
        storage.store_bytes(
            data=b"x" * (MAX_UPLOAD_BYTES + 1),
            filename="big.jpg",
            content_type="image/jpeg",
            folder="events/test",
        )


def test_memory_rejects_mime_spoof() -> None:
    fake = b"not-an-image-at-all"
    with pytest.raises(MemoryImageError, match="Unrecognized"):
        process_memory_image(data=fake, declared_content_type="image/png", event_id=uuid4())


def test_memory_strips_exif_and_outputs_webp() -> None:
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


def test_external_gallery_ssrf_schemes_blocked() -> None:
    for bad in ("javascript:alert(1)", "data:text/html,x", "file:///etc/passwd"):
        with pytest.raises(ValueError):
            validate_external_gallery_url(bad)


def test_allowed_image_types_exclude_svg() -> None:
    assert "image/jpeg" in ALLOWED_IMAGE_CONTENT_TYPES
    assert "image/png" in ALLOWED_IMAGE_CONTENT_TYPES
    assert "image/webp" in ALLOWED_IMAGE_CONTENT_TYPES
    assert "image/gif" in ALLOWED_IMAGE_CONTENT_TYPES
    assert "image/svg+xml" not in ALLOWED_IMAGE_CONTENT_TYPES


def _count_public_files() -> int:
    root = Path(get_settings().media_root)
    if not root.exists():
        return 0
    return sum(1 for path in root.rglob("*") if path.is_file())
