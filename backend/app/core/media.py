"""Media upload abstraction.

Stores files on local disk for development; swap LocalMediaStorage for S3/Cloudinary later
without changing route contracts.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from pathlib import Path

from app.core.config import get_settings

ALLOWED_IMAGE_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/svg+xml",
}

CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/svg+xml": ".svg",
}

MAX_UPLOAD_BYTES = 5 * 1024 * 1024

_LOCALHOST_MEDIA_URL = re.compile(
    r"^https?://(?:localhost|127\.0\.0\.1)(?::\d+)?(/media/.+)$",
    re.IGNORECASE,
)


def normalize_public_media_url(url: str | None) -> str | None:
    """Rewrite legacy localhost /media URLs and apply MEDIA_PUBLIC_BASE_URL when set."""
    if not url:
        return url
    cleaned = url.strip()
    if not cleaned:
        return url

    settings = get_settings()
    base = (settings.media_public_base_url or "").strip().rstrip("/")

    path: str | None = None
    if cleaned.startswith("/media/"):
        path = cleaned
    else:
        match = _LOCALHOST_MEDIA_URL.match(cleaned)
        if match:
            path = match.group(1)

    if path is not None:
        return f"{base}{path}" if base else path

    return cleaned


@dataclass
class StoredMedia:
    url: str
    key: str


class MediaStorage:
    def store_remote_url(self, *, url: str, folder: str = "events") -> StoredMedia:
        raise NotImplementedError

    def build_placeholder_url(self, *, filename: str, folder: str = "events") -> StoredMedia:
        raise NotImplementedError

    def store_bytes(
        self,
        *,
        data: bytes,
        filename: str,
        content_type: str,
        folder: str = "events",
    ) -> StoredMedia:
        raise NotImplementedError


class LocalMediaStorage(MediaStorage):
    """Writes uploads under MEDIA_ROOT and exposes them via /media/..."""

    def _public_url(self, key: str) -> str:
        return normalize_public_media_url(f"/media/{key}") or f"/media/{key}"

    def _root(self) -> Path:
        settings = get_settings()
        root = Path(settings.media_root)
        root.mkdir(parents=True, exist_ok=True)
        return root

    def store_remote_url(self, *, url: str, folder: str = "events") -> StoredMedia:
        cleaned = url.strip()
        if not cleaned:
            raise ValueError("Media URL is required")
        # Already-hosted local media or absolute http(s) URLs are accepted as-is.
        if cleaned.startswith("/media/"):
            key = cleaned.removeprefix("/media/")
            return StoredMedia(url=cleaned, key=key)
        if re.match(r"^https?://", cleaned, flags=re.IGNORECASE):
            if re.search(r"[\s<>\"'`]", cleaned):
                raise ValueError("Media URL contains invalid characters")
            key = f"{folder}/{uuid.uuid4()}"
            return StoredMedia(url=cleaned, key=key)
        raise ValueError("Media URL must start with http://, https://, or /media/")

    def build_placeholder_url(self, *, filename: str, folder: str = "events") -> StoredMedia:
        safe = re.sub(r"[^a-zA-Z0-9._-]+", "-", filename).strip("-") or "banner"
        key = f"{folder}/{uuid.uuid4()}-{safe}"
        return StoredMedia(url=self._public_url(key), key=key)

    def store_bytes(
        self,
        *,
        data: bytes,
        filename: str,
        content_type: str,
        folder: str = "events",
    ) -> StoredMedia:
        ctype = (content_type or "").split(";")[0].strip().lower()
        if ctype not in ALLOWED_IMAGE_CONTENT_TYPES:
            raise ValueError(
                "Unsupported image type. Use JPEG, PNG, WebP, GIF, or SVG."
            )
        if not data:
            raise ValueError("Empty file")
        if len(data) > MAX_UPLOAD_BYTES:
            raise ValueError("Image must be 5MB or smaller")

        ext = CONTENT_TYPE_EXTENSIONS.get(ctype, "")
        if not ext:
            match = re.search(r"\.([a-zA-Z0-9]{2,5})$", filename or "")
            ext = f".{match.group(1).lower()}" if match else ".bin"

        return self._write_bytes(
            data=data,
            folder=folder,
            extension=ext,
            filename=filename,
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
    ) -> StoredMedia:
        """Store pre-validated bytes (chat attachments, etc.). No image-only gate."""
        if not data:
            raise ValueError("Empty file")
        if len(data) > max_bytes:
            raise ValueError("File exceeds the allowed size.")
        _ = content_type  # caller already validated
        ext = extension if extension.startswith(".") else f".{extension}"
        return self._write_bytes(
            data=data,
            folder=folder,
            extension=ext,
            filename=filename,
        )

    def _write_bytes(
        self,
        *,
        data: bytes,
        folder: str,
        extension: str,
        filename: str,
    ) -> StoredMedia:
        safe_folder = re.sub(r"[^a-zA-Z0-9/_-]+", "-", folder).strip("-/") or "events"
        key = f"{safe_folder}/{uuid.uuid4()}{extension}"
        path = self._root() / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return StoredMedia(url=self._public_url(key), key=key)


def get_media_storage() -> MediaStorage:
    return LocalMediaStorage()
