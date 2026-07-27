"""Media upload abstraction.

LocalMediaStorage (dev) and R2MediaStorage (production) share MediaStorage.
Select via MEDIA_STORAGE_PROVIDER=local|r2.
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from app.core.config import get_settings

logger = logging.getLogger(__name__)

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


class MediaStorageError(Exception):
    """Operational media storage failure (not validation)."""


@dataclass
class StoredMedia:
    url: str
    key: str


def normalize_public_media_url(url: str | None) -> str | None:
    """Rewrite legacy localhost /media URLs and apply MEDIA_PUBLIC_BASE_URL when set.

    Also collapses retired Smartlance (and any-host) `/demo/...` static assets to
    site-relative `/demo/...` so APIs never emit padeya.smartlancedesigns.com.
    """
    if not url:
        return url
    cleaned = url.strip()
    if not cleaned:
        return url

    # Lazy import avoids circular imports at module load.
    from app.demo.assets import normalize_demo_asset_url

    demo_normalized = normalize_demo_asset_url(cleaned)
    if demo_normalized and demo_normalized.startswith("/demo/"):
        return demo_normalized

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


def storage_key_from_url(url: str | None) -> str | None:
    """Best-effort object key from a public media URL (local or R2)."""
    if not url:
        return None
    cleaned = url.strip()
    if not cleaned:
        return None
    if cleaned.startswith("/media/"):
        return cleaned.removeprefix("/media/")
    match = _LOCALHOST_MEDIA_URL.match(cleaned)
    if match:
        return match.group(1).removeprefix("/media/")

    settings = get_settings()
    r2_base = (settings.r2_public_url or "").strip().rstrip("/")
    if r2_base and cleaned.startswith(f"{r2_base}/"):
        return cleaned[len(r2_base) + 1 :]

    media_base = (settings.media_public_base_url or "").strip().rstrip("/")
    if media_base and cleaned.startswith(f"{media_base}/media/"):
        return cleaned[len(media_base) + len("/media/") :]
    return None


class MediaStorage:
    def store_remote_url(self, *, url: str, folder: str = "events") -> StoredMedia:
        raise NotImplementedError

    def build_placeholder_url(
        self, *, filename: str, folder: str = "events"
    ) -> StoredMedia:
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
        raise NotImplementedError

    def delete(self, key: str) -> None:
        raise NotImplementedError

    def exists(self, key: str) -> bool:
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

    def build_placeholder_url(
        self, *, filename: str, folder: str = "events"
    ) -> StoredMedia:
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
            content_type=ctype,
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
        """Store pre-validated bytes (chat attachments, memories, etc.)."""
        if not data:
            raise ValueError("Empty file")
        if len(data) > max_bytes:
            raise ValueError("File exceeds the allowed size.")
        _ = content_type
        _ = cache_control
        ext = extension if extension.startswith(".") else f".{extension}"
        return self._write_bytes(
            data=data,
            folder=folder,
            extension=ext,
            filename=filename,
            content_type=content_type,
        )

    def _write_bytes(
        self,
        *,
        data: bytes,
        folder: str,
        extension: str,
        filename: str,
        content_type: str | None = None,
    ) -> StoredMedia:
        _ = filename  # never used as object key
        _ = content_type
        safe_folder = re.sub(r"[^a-zA-Z0-9/_-]+", "-", folder).strip("-/") or "events"
        key = f"{safe_folder}/{uuid.uuid4()}{extension}"
        path = self._root() / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return StoredMedia(url=self._public_url(key), key=key)

    def delete(self, key: str) -> None:
        cleaned = (key or "").replace("\\", "/").lstrip("/")
        if not cleaned or ".." in cleaned.split("/"):
            return
        path = (self._root() / cleaned).resolve()
        root = self._root().resolve()
        if not str(path).startswith(str(root)):
            return
        try:
            if path.is_file():
                path.unlink()
        except OSError:
            logger.debug("local media delete skipped key_prefix=%s", cleaned.split("/")[0])

    def exists(self, key: str) -> bool:
        cleaned = (key or "").replace("\\", "/").lstrip("/")
        if not cleaned or ".." in cleaned.split("/"):
            return False
        path = (self._root() / cleaned).resolve()
        root = self._root().resolve()
        if not str(path).startswith(str(root)):
            return False
        return path.is_file()


def media_storage_provider() -> str:
    return (get_settings().media_storage_provider or "local").strip().lower()


def validate_media_storage_config() -> None:
    """Fail clearly when provider=r2 and required public+private env is missing."""
    provider = media_storage_provider()
    if provider in {"local", "filesystem", "disk", ""}:
        return
    if provider == "r2":
        from app.core.media_r2 import validate_r2_settings
        from app.core.media_private import validate_private_media_config

        validate_r2_settings()
        validate_private_media_config()
        return
    raise MediaStorageError(
        f"Unknown MEDIA_STORAGE_PROVIDER={provider!r}. Use local or r2."
    )


def log_media_storage_status() -> None:
    """Safe startup log — never prints credentials."""
    provider = media_storage_provider()
    settings = get_settings()
    if provider == "r2":
        domain = ""
        raw = (settings.r2_public_url or "").strip()
        if raw:
            parsed = urlparse(raw if "://" in raw else f"https://{raw}")
            domain = parsed.netloc or raw.rstrip("/")
        logger.info(
            "Media storage: provider=r2 public_configured=yes bucket=%s "
            "public_domain=%s private_bucket=%s",
            (settings.r2_bucket_name or "").strip() or "(missing)",
            domain or "(missing)",
            (settings.r2_private_bucket_name or "").strip() or "(missing)",
        )
    else:
        logger.info("Media storage: provider=local public=yes private=yes")


@lru_cache
def get_public_media_storage() -> MediaStorage:
    """Public uploaded media (events, memories, host/merch images, etc.)."""
    provider = media_storage_provider()
    if provider in {"local", "filesystem", "disk", ""}:
        return LocalMediaStorage()
    if provider == "r2":
        from app.core.media_r2 import R2MediaStorage

        return R2MediaStorage()
    raise MediaStorageError(
        f"Unknown MEDIA_STORAGE_PROVIDER={provider!r}. Use local or r2."
    )


def get_media_storage() -> MediaStorage:
    """Back-compat alias for public media storage.

    Prefer get_public_media_storage() or get_private_media_storage() explicitly.
    """
    return get_public_media_storage()


def reset_media_storage() -> None:
    """Clear cached storage instances (tests / settings changes)."""
    get_public_media_storage.cache_clear()
    try:
        from app.core.media_private import reset_private_media_storage

        reset_private_media_storage()
    except Exception:
        pass


def delete_media_keys(*keys: str | None) -> None:
    """Best-effort delete of public storage objects."""
    storage = get_public_media_storage()
    seen: set[str] = set()
    for key in keys:
        if not key or key in seen:
            continue
        seen.add(key)
        try:
            storage.delete(key)
        except MediaStorageError:
            logger.warning(
                "media_storage operation=delete result=failure key_prefix=%s",
                key.split("/", 1)[0],
            )
        except Exception:
            logger.warning(
                "media_storage operation=delete result=failure key_prefix=%s",
                key.split("/", 1)[0],
                exc_info=True,
            )
