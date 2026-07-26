"""Optimize memory photo uploads: orient, strip EXIF, resize, WebP."""

from __future__ import annotations

import io
import uuid
from dataclasses import dataclass

from app.core.media import MediaStorageError, get_media_storage

ALLOWED_MEMORY_MIME = frozenset({"image/jpeg", "image/jpg", "image/png", "image/webp"})
MAX_RAW_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_LONG_EDGE = 1800
THUMB_LONG_EDGE = 400
WEBP_QUALITY = 80
THUMB_QUALITY = 75


class MemoryImageError(ValueError):
    """Raised when a memory photo fails validation or processing."""


@dataclass(frozen=True)
class ProcessedMemoryImage:
    display_url: str
    display_key: str
    thumbnail_url: str
    thumbnail_key: str
    width: int
    height: int
    mime_type: str
    size_bytes: int
    original_bytes: int


def _normalize_mime(declared: str | None) -> str:
    return (declared or "").split(";")[0].strip().lower()


def _sniff_image_mime(data: bytes) -> str | None:
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def process_memory_image(
    *,
    data: bytes,
    declared_content_type: str | None,
    event_id: uuid.UUID,
) -> ProcessedMemoryImage:
    """Validate and optimize a memory photo for storage."""
    if not data:
        raise MemoryImageError("Empty file")
    original_bytes = len(data)
    if original_bytes > MAX_RAW_UPLOAD_BYTES:
        raise MemoryImageError("Image must be 10MB or smaller")

    sniffed = _sniff_image_mime(data)
    if sniffed is None:
        raise MemoryImageError("Unrecognized or unsupported image")
    declared = _normalize_mime(declared_content_type)
    if declared and declared not in ALLOWED_MEMORY_MIME:
        raise MemoryImageError("Only JPEG, PNG, and WebP images are allowed")
    if declared and declared in ALLOWED_MEMORY_MIME:
        # jpg alias
        declared_norm = "image/jpeg" if declared == "image/jpg" else declared
        sniffed_norm = "image/jpeg" if sniffed == "image/jpg" else sniffed
        if declared_norm != sniffed_norm:
            raise MemoryImageError("File content does not match declared type")

    try:
        from PIL import Image, ImageOps, UnidentifiedImageError
    except ImportError as exc:  # pragma: no cover
        raise MemoryImageError("Image processing unavailable") from exc

    try:
        with Image.open(io.BytesIO(data)) as img:
            img.verify()
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError) as exc:
        raise MemoryImageError("Invalid or corrupt image") from exc

    try:
        with Image.open(io.BytesIO(data)) as img:
            img = ImageOps.exif_transpose(img)
            if img.mode not in {"RGB", "RGBA"}:
                img = img.convert("RGB")
            elif img.mode == "RGBA":
                # Flatten alpha onto white for consistent WebP photos.
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1])
                img = background

            width, height = img.size
            if width < 1 or height < 1 or width > 20000 or height > 20000:
                raise MemoryImageError("Image dimensions are not allowed")

            display = img.copy()
            display.thumbnail((MAX_LONG_EDGE, MAX_LONG_EDGE), Image.Resampling.LANCZOS)
            thumb = img.copy()
            thumb.thumbnail((THUMB_LONG_EDGE, THUMB_LONG_EDGE), Image.Resampling.LANCZOS)

            display_buf = io.BytesIO()
            display.save(display_buf, format="WEBP", quality=WEBP_QUALITY, method=4)
            display_bytes = display_buf.getvalue()

            thumb_buf = io.BytesIO()
            thumb.save(thumb_buf, format="WEBP", quality=THUMB_QUALITY, method=4)
            thumb_bytes = thumb_buf.getvalue()

            out_w, out_h = display.size
    except MemoryImageError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError) as exc:
        raise MemoryImageError("Failed to process image") from exc

    if not display_bytes or not thumb_bytes:
        raise MemoryImageError("Failed to encode image")

    # Object keys are backend-generated UUIDs under memories/events/{event_id}/…
    folder = f"memories/events/{event_id}"
    storage = get_media_storage()
    try:
        display_stored = storage.store_validated_bytes(
            data=display_bytes,
            filename="memory.webp",
            content_type="image/webp",
            folder=folder,
            extension=".webp",
            max_bytes=MAX_RAW_UPLOAD_BYTES,
        )
    except MediaStorageError:
        raise
    except ValueError as exc:
        raise MemoryImageError(str(exc)) from exc

    try:
        thumb_stored = storage.store_validated_bytes(
            data=thumb_bytes,
            filename="memory-thumb.webp",
            content_type="image/webp",
            folder=f"{folder}/thumbs",
            extension=".webp",
            max_bytes=MAX_RAW_UPLOAD_BYTES,
        )
    except Exception:
        try:
            storage.delete(display_stored.key)
        except Exception:
            pass
        raise

    return ProcessedMemoryImage(
        display_url=display_stored.url,
        display_key=display_stored.key,
        thumbnail_url=thumb_stored.url,
        thumbnail_key=thumb_stored.key,
        width=int(out_w),
        height=int(out_h),
        mime_type="image/webp",
        size_bytes=len(display_bytes),
        original_bytes=original_bytes,
    )


def validate_external_gallery_url(url: str | None) -> str | None:
    """Accept only http(s) URLs; reject javascript:/data:/etc."""
    if url is None:
        return None
    cleaned = url.strip()
    if not cleaned:
        return None
    lower = cleaned.lower()
    if lower.startswith(("javascript:", "data:", "vbscript:", "file:")):
        raise ValueError("Unsupported URL scheme")
    if not (lower.startswith("https://") or lower.startswith("http://")):
        raise ValueError("External gallery URL must be http or https")
    if any(ch in cleaned for ch in (" ", "<", ">", '"', "'", "`")):
        raise ValueError("External gallery URL contains invalid characters")
    if len(cleaned) > 500:
        raise ValueError("External gallery URL is too long")
    return cleaned
