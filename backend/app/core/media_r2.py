"""Cloudflare R2 public media storage (padeya-media → media.padeya.com)."""

from __future__ import annotations

import re
import uuid

from app.core.config import Settings, get_settings
from app.core.media import (
    MAX_UPLOAD_BYTES,
    MediaStorage,
    StoredMedia,
    normalize_public_media_url,
)
from app.core.public_image_validation import (
    PublicImageValidationError,
    validate_public_raster_upload,
)
from app.core.r2_client import (
    IMMUTABLE_PUBLIC_CACHE_CONTROL,
    PUBLIC_MEDIA_OBJECT_METADATA,
    R2BucketClient,
    make_object_key,
    public_r2_config,
    r2_public_domain,
)

# Back-compat aliases for existing tests/imports.
IMMUTABLE_CACHE_CONTROL = IMMUTABLE_PUBLIC_CACHE_CONTROL


def validate_r2_settings(settings: Settings | None = None) -> None:
    """Raise MediaStorageError if public R2 env is incomplete."""
    public_r2_config(settings)


class R2MediaStorage(MediaStorage):
    """Stores public media in Cloudflare R2; URLs use R2_PUBLIC_URL."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._r2 = R2BucketClient(public_r2_config(self._settings))
        self._public_base = (self._settings.r2_public_url or "").strip().rstrip("/")

    def _public_url(self, key: str) -> str:
        return f"{self._public_base}/{key.lstrip('/')}"

    def store_remote_url(self, *, url: str, folder: str = "events") -> StoredMedia:
        cleaned = url.strip()
        if not cleaned:
            raise ValueError("Media URL is required")
        if cleaned.startswith("/media/"):
            key = cleaned.removeprefix("/media/")
            return StoredMedia(
                url=normalize_public_media_url(cleaned) or cleaned,
                key=key,
            )
        if cleaned.startswith(f"{self._public_base}/"):
            key = cleaned[len(self._public_base) + 1 :]
            return StoredMedia(url=cleaned, key=key)
        if re.match(r"^https?://", cleaned, flags=re.IGNORECASE):
            if re.search(r"[\s<>\"'`]", cleaned):
                raise ValueError("Media URL contains invalid characters")
            key = f"{folder}/{uuid.uuid4()}"
            return StoredMedia(url=cleaned, key=key)
        raise ValueError(
            "Media URL must start with http://, https://, or /media/"
        )

    def build_placeholder_url(
        self, *, filename: str, folder: str = "events"
    ) -> StoredMedia:
        safe = re.sub(r"[^a-zA-Z0-9._-]+", "-", filename).strip("-") or "banner"
        key = f"{folder.strip('-/')}/{uuid.uuid4()}-{safe}"
        return StoredMedia(url=self._public_url(key), key=key)

    def store_bytes(
        self,
        *,
        data: bytes,
        filename: str,
        content_type: str,
        folder: str = "events",
    ) -> StoredMedia:
        if len(data) > MAX_UPLOAD_BYTES:
            raise ValueError("Image must be 5MB or smaller")
        try:
            validated = validate_public_raster_upload(
                data, declared_content_type=content_type
            )
        except PublicImageValidationError as exc:
            raise ValueError(str(exc)) from exc

        return self.store_validated_bytes(
            data=data,
            filename=filename,
            content_type=validated.content_type,
            folder=folder,
            extension=validated.extension,
            max_bytes=MAX_UPLOAD_BYTES,
        )

    def store_validated_bytes(
        self,
        *,
        data: bytes,
        filename: str,
        content_type: str,
        folder: str,
        extension: str,
        max_bytes: int,
        cache_control: str | None = None,
    ) -> StoredMedia:
        if not data:
            raise ValueError("Empty file")
        if len(data) > max_bytes:
            raise ValueError("File exceeds the allowed size.")
        _ = filename  # never used as object key
        ctype = (content_type or "application/octet-stream").split(";")[0].strip()
        if not ctype.startswith("image/"):
            raise ValueError("Public media must use an image Content-Type.")
        key = make_object_key(folder=folder, extension=extension)
        self._r2.put_object(
            key=key,
            data=data,
            content_type=ctype,
            cache_control=cache_control or IMMUTABLE_PUBLIC_CACHE_CONTROL,
            metadata=PUBLIC_MEDIA_OBJECT_METADATA,
        )
        return StoredMedia(url=self._public_url(key), key=key)

    def ensure_inline_headers(self, key: str) -> bool:
        """Repair CDN headers so image URLs preview in a browser tab."""
        return self._r2.rewrite_public_image_headers(key)

    def delete(self, key: str) -> None:
        self._r2.delete_object(key)

    def exists(self, key: str) -> bool:
        return self._r2.head_object(key)

    def check_connectivity(self) -> dict[str, bool | str]:
        return self._r2.check_connectivity()


# Re-export for scripts/tests
__all__ = [
    "IMMUTABLE_CACHE_CONTROL",
    "R2MediaStorage",
    "r2_public_domain",
    "validate_r2_settings",
]
