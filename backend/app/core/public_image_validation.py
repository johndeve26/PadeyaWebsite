"""Validate user-controlled public raster uploads (events, hosts, legacy media).

Policy: JPEG, PNG, WebP, and GIF only. SVG/HTML/JS and other active content are
rejected. Magic-byte sniffing and Pillow decode are authoritative — never trust
filename, extension, or client Content-Type alone.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass

PUBLIC_RASTER_IMAGE_MIME_TYPES = frozenset(
    {
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/webp",
        "image/gif",
    }
)

MIME_TO_EXTENSION = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}

_PIL_FORMATS = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
    "image/gif": "GIF",
}

_ACTIVE_CONTENT_RE = re.compile(
    rb"(?:<\s*svg\b|<\s*script\b|<\s*html\b|<!doctype\s+html\b|<\s*\?xml\b)",
    re.IGNORECASE,
)


class PublicImageValidationError(ValueError):
    """Raised when a public raster upload fails validation."""


@dataclass(frozen=True)
class ValidatedPublicRasterImage:
    content_type: str
    extension: str


def _normalize_mime(value: str | None) -> str:
    return (value or "").split(";")[0].strip().lower()


def _canonical_mime(mime: str) -> str:
    return "image/jpeg" if mime == "image/jpg" else mime


def looks_like_active_content(data: bytes) -> bool:
    """Detect SVG/HTML/JS-style payloads regardless of declared MIME."""
    if not data:
        return False
    sample = data[:8192].lstrip()
    if _ACTIVE_CONTENT_RE.search(sample):
        return True
    lowered = sample.lower()
    if b"javascript:" in lowered or b"onload=" in lowered or b"onerror=" in lowered:
        return True
    return False


def sniff_public_raster_mime(data: bytes) -> str | None:
    if len(data) >= 3 and data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if len(data) >= 8 and data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if len(data) >= 6 and data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    return None


def _verify_raster_image(data: bytes, mime: str) -> None:
    try:
        from PIL import Image, UnidentifiedImageError
    except ImportError as exc:  # pragma: no cover
        raise PublicImageValidationError("Image processing unavailable") from exc

    expected = _PIL_FORMATS.get(mime)
    if expected is None:
        raise PublicImageValidationError("Unsupported image type")

    try:
        with Image.open(io.BytesIO(data)) as img:
            if img.format != expected:
                raise PublicImageValidationError("File content does not match image type")
            img.verify()
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError) as exc:
        raise PublicImageValidationError("Invalid or corrupt image") from exc

    try:
        with Image.open(io.BytesIO(data)) as img:
            width, height = img.size
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError) as exc:
        raise PublicImageValidationError("Invalid or corrupt image") from exc

    if width < 1 or height < 1 or width > 20000 or height > 20000:
        raise PublicImageValidationError("Image dimensions are not allowed")


def validate_public_raster_upload(
    data: bytes,
    *,
    declared_content_type: str | None = None,
) -> ValidatedPublicRasterImage:
    """Validate bytes for public raster storage; return authoritative MIME + ext."""
    if not data:
        raise PublicImageValidationError("Empty file")

    if looks_like_active_content(data):
        raise PublicImageValidationError(
            "SVG and other active content are not allowed for public image uploads"
        )

    sniffed = sniff_public_raster_mime(data)
    if sniffed is None:
        raise PublicImageValidationError(
            "Unrecognized or unsupported image. Use JPEG, PNG, WebP, or GIF."
        )

    declared = _normalize_mime(declared_content_type)
    if declared:
        if declared == "image/svg+xml":
            raise PublicImageValidationError(
                "SVG is not allowed for public image uploads"
            )
        if declared not in PUBLIC_RASTER_IMAGE_MIME_TYPES:
            raise PublicImageValidationError(
                "Unsupported image type. Use JPEG, PNG, WebP, or GIF."
            )
        if _canonical_mime(declared) != sniffed:
            raise PublicImageValidationError("File content does not match declared type")

    _verify_raster_image(data, sniffed)
    return ValidatedPublicRasterImage(
        content_type=sniffed,
        extension=MIME_TO_EXTENSION[sniffed],
    )
