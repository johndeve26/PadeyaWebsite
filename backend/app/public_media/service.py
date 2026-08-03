"""Store processed public media variants under immutable keys."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.media import MediaStorageError, get_public_media_storage
from app.public_media.contract import build_public_media_payload, variant_public_dict
from app.public_media.models import PublicMediaAsset, PublicMediaVariant
from app.public_media.processor import (
    PublicMediaProcessingError,
    encode_variants,
)
from app.public_media.roles import MediaRole, map_upload_kind_to_role

logger = logging.getLogger(__name__)


def public_media_folder(
    *,
    role: MediaRole | str,
    asset_id: uuid.UUID,
    owner_type: str | None = None,
    owner_id: uuid.UUID | None = None,
) -> str:
    role_s = role.value if isinstance(role, MediaRole) else str(role)
    if owner_type and owner_id:
        return f"public-media/{owner_type}/{owner_id}/{asset_id}"
    return f"public-media/{role_s}/{asset_id}"


def process_and_store_public_media(
    db: Session,
    *,
    data: bytes,
    declared_content_type: str | None,
    role: MediaRole | str,
    created_by_user_id: uuid.UUID | None = None,
    owner_type: str | None = None,
    owner_id: uuid.UUID | None = None,
    alt_text: str | None = None,
    focal_x: float | None = None,
    focal_y: float | None = None,
    store_source: bool = True,
) -> dict[str, Any]:
    """Validate → encode → upload all variants → persist asset rows.

    On failure after partial uploads, best-effort deletes uploaded keys and
    does not leave a ready asset pointing at incomplete variants.
    """
    role_enum = role if isinstance(role, MediaRole) else MediaRole(str(role))
    processed = encode_variants(
        data=data,
        declared_content_type=declared_content_type,
        role=role_enum,
    )

    asset_id = uuid.uuid4()
    folder = public_media_folder(
        role=role_enum,
        asset_id=asset_id,
        owner_type=owner_type,
        owner_id=owner_id,
    )
    storage = get_public_media_storage()
    uploaded_keys: list[str] = []
    variant_rows: list[PublicMediaVariant] = []
    public_variants: dict[str, dict[str, Any]] = {}

    source_key: str | None = None
    try:
        if store_source:
            # Controlled unguessable source key — APIs never return this.
            src_ext = {
                "image/jpeg": ".jpg",
                "image/png": ".png",
                "image/webp": ".webp",
                "image/gif": ".gif",
            }.get(processed.source_mime, ".bin")
            source_stored = storage.store_validated_bytes(
                data=data,
                filename=f"source{src_ext}",
                content_type=processed.source_mime,
                folder=f"{folder}/source",
                extension=src_ext,
                max_bytes=max(len(data), 10 * 1024 * 1024),
            )
            source_key = source_stored.key
            uploaded_keys.append(source_key)

        for encoded in processed.variants:
            stored = storage.store_validated_bytes(
                data=encoded.data,
                filename=f"{encoded.variant.value}-{processed.processing_version}{encoded.extension}",
                content_type=encoded.mime_type,
                folder=folder,
                extension=encoded.extension,
                max_bytes=max(len(encoded.data), 10 * 1024 * 1024),
            )
            uploaded_keys.append(stored.key)
            variant_rows.append(
                PublicMediaVariant(
                    id=uuid.uuid4(),
                    asset_id=asset_id,
                    variant_type=encoded.variant.value,
                    storage_key=stored.key,
                    public_url=stored.url,
                    mime_type=encoded.mime_type,
                    width=encoded.width,
                    height=encoded.height,
                    byte_size=len(encoded.data),
                    quality=encoded.quality,
                    processing_version=processed.processing_version,
                )
            )
            public_variants[encoded.variant.value] = variant_public_dict(
                url=stored.url,
                width=encoded.width,
                height=encoded.height,
            )
    except MediaStorageError:
        _cleanup_keys(storage, uploaded_keys)
        raise
    except (ValueError, PublicMediaProcessingError) as exc:
        _cleanup_keys(storage, uploaded_keys)
        if isinstance(exc, PublicMediaProcessingError):
            raise
        raise PublicMediaProcessingError(str(exc)) from exc
    except Exception:
        _cleanup_keys(storage, uploaded_keys)
        raise

    display = public_variants.get("display") or next(iter(public_variants.values()))
    asset = PublicMediaAsset(
        id=asset_id,
        owner_type=owner_type,
        owner_id=owner_id,
        media_role=role_enum.value,
        source_key=source_key,
        source_mime=processed.source_mime,
        source_width=processed.source_width,
        source_height=processed.source_height,
        source_byte_size=processed.source_bytes,
        alt_text=alt_text,
        focal_x=focal_x,
        focal_y=focal_y,
        processing_status="ready",
        processing_version=processed.processing_version,
        created_by_user_id=created_by_user_id,
    )
    db.add(asset)
    for row in variant_rows:
        db.add(row)
    db.flush()

    payload = build_public_media_payload(
        asset_id=asset_id,
        role=role_enum.value,
        variants=public_variants,
        alt=alt_text,
        focal_x=focal_x,
        focal_y=focal_y,
        width=(display or {}).get("width") or processed.source_width,
        height=(display or {}).get("height") or processed.source_height,
    )
    # Internal-only — callers must strip before public HTTP responses.
    payload["_storage_keys"] = list(uploaded_keys)
    payload["_source_bytes"] = processed.source_bytes
    payload["_variant_byte_sizes"] = {
        row.variant_type: row.byte_size for row in variant_rows
    }
    logger.info(
        "public_media_processed",
        extra={
            "role": role_enum.value,
            "source_mime": processed.source_mime,
            "source_bytes": processed.source_bytes,
            "source_width": processed.source_width,
            "source_height": processed.source_height,
            "variant_count": len(variant_rows),
            "generated_bytes": sum(v.byte_size for v in variant_rows),
        },
    )
    return payload


def public_media_response(payload: dict[str, Any]) -> dict[str, Any]:
    """Strip internal keys before returning over HTTP."""
    return {k: v for k, v in payload.items() if not str(k).startswith("_")}


def process_upload_kind(
    db: Session,
    *,
    data: bytes,
    declared_content_type: str | None,
    media_type: str,
    created_by_user_id: uuid.UUID | None = None,
    owner_type: str | None = None,
    owner_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    role = map_upload_kind_to_role(media_type)
    return process_and_store_public_media(
        db,
        data=data,
        declared_content_type=declared_content_type,
        role=role,
        created_by_user_id=created_by_user_id,
        owner_type=owner_type,
        owner_id=owner_id,
    )


def _cleanup_keys(storage, keys: list[str]) -> None:
    for key in keys:
        try:
            storage.delete(key)
        except Exception:
            logger.warning("public_media_cleanup_failed key=%s", key, exc_info=True)
