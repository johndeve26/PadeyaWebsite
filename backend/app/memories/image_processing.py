"""Optimize memory photo uploads via the shared public media pipeline."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.media import MediaStorageError, delete_media_keys, get_public_media_storage
from app.core.media_folders import memory_public_folder
from app.public_media.processor import PublicMediaProcessingError, encode_variants
from app.public_media.roles import MediaRole, VariantType
from app.public_media.service import process_and_store_public_media


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
    asset_id: str | None = None
    full_url: str | None = None


def process_memory_image(
    *,
    data: bytes,
    declared_content_type: str | None,
    event_id: uuid.UUID,
    db: Session | None = None,
    created_by_user_id: uuid.UUID | None = None,
) -> ProcessedMemoryImage:
    """Validate and optimize a memory photo for storage.

    With ``db``: persist a PublicMediaAsset + variants (shared pipeline).
    Without ``db``: encode + store under legacy memory folders (unit tests /
    offline callers) without asset rows.
    """
    if db is not None:
        return _process_with_asset(
            db,
            data=data,
            declared_content_type=declared_content_type,
            event_id=event_id,
            created_by_user_id=created_by_user_id,
        )
    return _process_legacy_folders(
        data=data,
        declared_content_type=declared_content_type,
        event_id=event_id,
    )


def _process_with_asset(
    db: Session,
    *,
    data: bytes,
    declared_content_type: str | None,
    event_id: uuid.UUID,
    created_by_user_id: uuid.UUID | None,
) -> ProcessedMemoryImage:
    try:
        payload = process_and_store_public_media(
            db,
            data=data,
            declared_content_type=declared_content_type,
            role=MediaRole.MEMORY,
            created_by_user_id=created_by_user_id,
            owner_type="event",
            owner_id=event_id,
            store_source=True,
        )
    except MediaStorageError:
        raise
    except PublicMediaProcessingError as exc:
        raise MemoryImageError(str(exc)) from exc

    db.flush()

    from app.public_media.models import PublicMediaVariant

    asset_id = payload.get("id")
    display_key = ""
    thumb_key = ""
    if asset_id:
        rows = (
            db.query(PublicMediaVariant)
            .filter(PublicMediaVariant.asset_id == uuid.UUID(str(asset_id)))
            .all()
        )
        by_type = {r.variant_type: r for r in rows}
        if "display" in by_type:
            display_key = by_type["display"].storage_key
        if "thumbnail" in by_type:
            thumb_key = by_type["thumbnail"].storage_key

    variants = payload.get("variants") or {}
    display = variants.get("display") or {}
    thumb = variants.get("thumbnail") or {}
    full = variants.get("full") or display
    return ProcessedMemoryImage(
        display_url=str(payload.get("display_url") or display.get("url") or ""),
        display_key=display_key,
        thumbnail_url=str(payload.get("thumbnail_url") or thumb.get("url") or ""),
        thumbnail_key=thumb_key,
        width=int(payload.get("width") or display.get("width") or 0),
        height=int(payload.get("height") or display.get("height") or 0),
        mime_type="image/webp",
        size_bytes=int((payload.get("_variant_byte_sizes") or {}).get("display") or 0),
        original_bytes=int(payload.get("_source_bytes") or len(data)),
        asset_id=str(asset_id) if asset_id else None,
        full_url=str(
            payload.get("full_url") or full.get("url") or payload.get("display_url") or ""
        ),
    )


def _process_legacy_folders(
    *,
    data: bytes,
    declared_content_type: str | None,
    event_id: uuid.UUID,
) -> ProcessedMemoryImage:
    try:
        processed = encode_variants(
            data=data,
            declared_content_type=declared_content_type,
            role=MediaRole.MEMORY,
        )
    except PublicMediaProcessingError as exc:
        raise MemoryImageError(str(exc)) from exc

    by = {v.variant: v for v in processed.variants}
    display = by.get(VariantType.DISPLAY) or next(iter(processed.variants))
    thumb = by.get(VariantType.THUMBNAIL) or display
    full = by.get(VariantType.FULL) or display

    storage = get_public_media_storage()
    try:
        display_stored = storage.store_validated_bytes(
            data=display.data,
            filename="memory.webp",
            content_type="image/webp",
            folder=memory_public_folder(event_id, thumb=False),
            extension=".webp",
            max_bytes=max(len(display.data), 10 * 1024 * 1024),
        )
    except MediaStorageError:
        raise
    except ValueError as exc:
        raise MemoryImageError(str(exc)) from exc

    try:
        thumb_stored = storage.store_validated_bytes(
            data=thumb.data,
            filename="memory-thumb.webp",
            content_type="image/webp",
            folder=memory_public_folder(event_id, thumb=True),
            extension=".webp",
            max_bytes=max(len(thumb.data), 10 * 1024 * 1024),
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
        width=display.width,
        height=display.height,
        mime_type="image/webp",
        size_bytes=len(display.data),
        original_bytes=processed.source_bytes,
        asset_id=None,
        full_url=display_stored.url if full is display else display_stored.url,
    )


def cleanup_processed_memory_keys(processed: ProcessedMemoryImage) -> None:
    delete_media_keys(processed.display_key, processed.thumbnail_key)


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
