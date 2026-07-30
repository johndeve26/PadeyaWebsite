"""Private media storage — padeya-private / local private disk.

Never returns permanent public URLs. Authorized callers use open_bytes()
or short-lived presigned GETs after application-level authorization.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.core.config import get_settings
from app.core.media import MediaStorageError, media_storage_provider
from app.core.r2_client import (
    PRIVATE_CACHE_CONTROL,
    R2BucketClient,
    make_object_key,
    private_r2_config,
)

logger = logging.getLogger(__name__)

DEFAULT_PRESIGN_TTL_SECONDS = 900


@dataclass(frozen=True)
class StoredPrivateMedia:
    """Opaque private object handle — never a public CDN URL."""

    key: str


class PrivateMediaStorage:
    """Authorization-protected file storage (no permanent public URLs)."""

    kind: str = "private"

    def store_validated_bytes(
        self,
        *,
        data: bytes,
        folder: str,
        extension: str,
        content_type: str,
        max_bytes: int,
        filename: str = "",
    ) -> StoredPrivateMedia:
        raise NotImplementedError

    def open_bytes(self, key: str) -> bytes:
        raise NotImplementedError

    def delete(self, key: str) -> None:
        raise NotImplementedError

    def exists(self, key: str) -> bool:
        raise NotImplementedError

    def presign_get(
        self,
        key: str,
        *,
        expires_in: int = DEFAULT_PRESIGN_TTL_SECONDS,
        response_content_type: str | None = None,
        response_content_disposition: str | None = None,
    ) -> str:
        """Return a short-lived download URL. Must not be persisted."""
        raise NotImplementedError

    def supports_presign(self) -> bool:
        return False

    def check_connectivity(self) -> dict[str, bool | str]:
        raise NotImplementedError


class LocalPrivateMediaStorage(PrivateMediaStorage):
    """Local private disk under storage/private/ (never mounted as /media)."""

    def _root(self) -> Path:
        settings = get_settings()
        root = Path(settings.private_media_root or "storage/private")
        if not root.is_absolute():
            root = Path.cwd() / root
        root.mkdir(parents=True, exist_ok=True)
        return root.resolve()

    def _safe_path(self, key: str) -> Path:
        cleaned = (key or "").replace("\\", "/").lstrip("/")
        if not cleaned or ".." in cleaned.split("/"):
            raise FileNotFoundError("Invalid storage key")
        path = (self._root() / cleaned).resolve()
        root = self._root()
        if not str(path).startswith(str(root)):
            raise FileNotFoundError("Invalid storage key")
        return path

    def store_validated_bytes(
        self,
        *,
        data: bytes,
        folder: str,
        extension: str,
        content_type: str,
        max_bytes: int,
        filename: str = "",
    ) -> StoredPrivateMedia:
        if not data:
            raise ValueError("Empty file")
        if len(data) > max_bytes:
            raise ValueError("File exceeds the allowed size.")
        _ = content_type
        _ = filename
        key = make_object_key(folder=folder, extension=extension)
        path = self._safe_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return StoredPrivateMedia(key=key)

    def open_bytes(self, key: str) -> bytes:
        path = self._safe_path(key)
        if not path.is_file():
            raise FileNotFoundError("Private media missing from storage")
        return path.read_bytes()

    def delete(self, key: str) -> None:
        try:
            path = self._safe_path(key)
            if path.is_file():
                path.unlink()
        except (FileNotFoundError, OSError):
            logger.debug("private media delete skipped key_prefix=%s", (key or "").split("/")[0])

    def exists(self, key: str) -> bool:
        try:
            return self._safe_path(key).is_file()
        except FileNotFoundError:
            return False

    def presign_get(
        self,
        key: str,
        *,
        expires_in: int = DEFAULT_PRESIGN_TTL_SECONDS,
        response_content_type: str | None = None,
        response_content_disposition: str | None = None,
    ) -> str:
        _ = (key, expires_in, response_content_type, response_content_disposition)
        raise MediaStorageError(
            "Local private storage does not support presigned URLs; stream via the API."
        )

    def supports_presign(self) -> bool:
        return False

    def check_connectivity(self) -> dict[str, bool | str]:
        root = self._root()
        try:
            stored = self.store_validated_bytes(
                data=b"padeya-private-probe",
                folder="_health",
                extension=".bin",
                content_type="application/octet-stream",
                max_bytes=64,
            )
            ok = self.exists(stored.key)
            self.delete(stored.key)
            return {
                "configured": True,
                "reachable": ok,
                "bucket_accessible": ok,
                "provider": "local",
                "kind": "private",
                "bucket": str(root),
            }
        except Exception as exc:
            return {
                "configured": True,
                "reachable": False,
                "bucket_accessible": False,
                "provider": "local",
                "kind": "private",
                "error": type(exc).__name__,
            }


class R2PrivateMediaStorage(PrivateMediaStorage):
    """Cloudflare R2 private bucket — no public domain, presigned GET only."""

    def __init__(self) -> None:
        self._r2 = R2BucketClient(private_r2_config())

    def store_validated_bytes(
        self,
        *,
        data: bytes,
        folder: str,
        extension: str,
        content_type: str,
        max_bytes: int,
        filename: str = "",
    ) -> StoredPrivateMedia:
        if not data:
            raise ValueError("Empty file")
        if len(data) > max_bytes:
            raise ValueError("File exceeds the allowed size.")
        _ = filename
        ctype = (content_type or "application/octet-stream").split(";")[0].strip()
        key = make_object_key(folder=folder, extension=extension)
        self._r2.put_object(
            key=key,
            data=data,
            content_type=ctype or "application/octet-stream",
            cache_control=PRIVATE_CACHE_CONTROL,
        )
        return StoredPrivateMedia(key=key)

    def open_bytes(self, key: str) -> bytes:
        try:
            return self._r2.get_object_bytes(key)
        except MediaStorageError as exc:
            raise FileNotFoundError("Private media missing from storage") from exc

    def delete(self, key: str) -> None:
        self._r2.delete_object(key)

    def exists(self, key: str) -> bool:
        return self._r2.head_object(key)

    def presign_get(
        self,
        key: str,
        *,
        expires_in: int = DEFAULT_PRESIGN_TTL_SECONDS,
        response_content_type: str | None = None,
        response_content_disposition: str | None = None,
    ) -> str:
        return self._r2.presign_get(
            key,
            expires_in=expires_in,
            response_content_type=response_content_type,
            response_content_disposition=response_content_disposition,
        )

    def supports_presign(self) -> bool:
        return True

    def check_connectivity(self) -> dict[str, bool | str]:
        return self._r2.check_connectivity()


def validate_private_media_config() -> None:
    """When provider=r2, private R2 env must be complete (never fall back to public)."""
    provider = media_storage_provider()
    if provider in {"local", "filesystem", "disk", ""}:
        return
    if provider == "r2":
        private_r2_config()
        return
    raise MediaStorageError(
        f"Unknown MEDIA_STORAGE_PROVIDER={provider!r}. Use local or r2."
    )


@lru_cache
def get_private_media_storage() -> PrivateMediaStorage:
    provider = media_storage_provider()
    if provider in {"local", "filesystem", "disk", ""}:
        return LocalPrivateMediaStorage()
    if provider == "r2":
        return R2PrivateMediaStorage()
    raise MediaStorageError(
        f"Unknown MEDIA_STORAGE_PROVIDER={provider!r}. Use local or r2."
    )


def reset_private_media_storage() -> None:
    get_private_media_storage.cache_clear()


def is_public_padeya_media_url(url: str | None) -> bool:
    """True when URL points at our public media CDN or /media/ mount."""
    if not url:
        return False
    cleaned = url.strip()
    if not cleaned:
        return False
    if cleaned.startswith("/media/"):
        return True
    lower = cleaned.lower()
    if "media.padeya.com/" in lower:
        return True
    settings = get_settings()
    base = (settings.r2_public_url or "").strip().rstrip("/").lower()
    if base and lower.startswith(base + "/"):
        return True
    return False


def assert_not_public_media_url(url: str | None, *, context: str) -> None:
    if is_public_padeya_media_url(url):
        raise ValueError(
            f"{context} cannot reference public media URLs "
            "(media.padeya.com or /media/). Use private storage."
        )


def safe_private_folder(*parts: str) -> str:
    cleaned = []
    for part in parts:
        piece = re.sub(r"[^a-zA-Z0-9/_-]+", "-", str(part)).strip("-/")
        if piece and ".." not in piece.split("/"):
            cleaned.append(piece)
    return "/".join(cleaned) if cleaned else "private"
