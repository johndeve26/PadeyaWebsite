"""Private message-attachment storage (provider-ready).

Local files live under ``storage/message_attachments/`` (never public /media).
When MEDIA_STORAGE_PROVIDER=r2, writes go to private R2 (padeya-private).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import re
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from app.core.config import get_settings
from app.core.media import media_storage_provider
from app.core.media_folders import inbox_private_folder
from app.core.media_private import get_private_media_storage

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StoredAttachment:
    """Opaque storage handle — never expose filesystem paths to clients."""

    key: str


class AttachmentStorage(ABC):
    @abstractmethod
    def store(
        self,
        *,
        data: bytes,
        extension: str,
        thread_id: uuid.UUID,
        uploader_id: uuid.UUID,
        content_type: str = "application/octet-stream",
    ) -> StoredAttachment:
        raise NotImplementedError

    @abstractmethod
    def open_bytes(self, key: str) -> bytes:
        raise NotImplementedError

    @abstractmethod
    def delete(self, key: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def exists(self, key: str) -> bool:
        raise NotImplementedError

    def presign_get(self, key: str, *, expires_in: int = 900) -> str | None:
        """Optional short-lived URL after authorization. Never persist."""
        return None

    def supports_presign(self) -> bool:
        return False


class LocalAttachmentStorage(AttachmentStorage):
    """Dev/local private disk store under storage/message_attachments/."""

    def _root(self) -> Path:
        settings = get_settings()
        root = Path(settings.messaging_attachment_storage_root)
        if not root.is_absolute():
            root = Path.cwd() / root
        root.mkdir(parents=True, exist_ok=True)
        return root.resolve()

    def _safe_key_path(self, key: str) -> Path:
        cleaned = key.replace("\\", "/").lstrip("/")
        if ".." in cleaned.split("/"):
            raise FileNotFoundError("Invalid storage key")
        path = (self._root() / cleaned).resolve()
        root = self._root()
        if not str(path).startswith(str(root)):
            raise FileNotFoundError("Invalid storage key")
        return path

    def store(
        self,
        *,
        data: bytes,
        extension: str,
        thread_id: uuid.UUID,
        uploader_id: uuid.UUID,
        content_type: str = "application/octet-stream",
    ) -> StoredAttachment:
        if not data:
            raise ValueError("Empty file")
        _ = content_type
        _ = uploader_id  # retained for audit; not used in opaque key path
        ext = extension if extension.startswith(".") else f".{extension}"
        ext = re.sub(r"[^a-zA-Z0-9.]+", "", ext)[:16] or ".bin"
        # Prefer opaque inbox/ folder; keep legacy thread/uploader layout for local
        # compatibility with existing demo seeds that may use older keys.
        key = f"{thread_id}/{uploader_id}/{uuid.uuid4().hex}{ext}"
        path = self._safe_key_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return StoredAttachment(key=key)

    def open_bytes(self, key: str) -> bytes:
        path = self._safe_key_path(key)
        if not path.is_file():
            raise FileNotFoundError("Attachment missing from storage")
        return path.read_bytes()

    def delete(self, key: str) -> None:
        try:
            path = self._safe_key_path(key)
            if path.is_file():
                path.unlink()
        except (FileNotFoundError, OSError):
            logger.debug("attachment delete skipped key=%s", key, exc_info=True)

    def exists(self, key: str) -> bool:
        try:
            return self._safe_key_path(key).is_file()
        except FileNotFoundError:
            return False


class PrivateR2AttachmentStorage(AttachmentStorage):
    """Inbox attachments on padeya-private via shared private media storage."""

    def store(
        self,
        *,
        data: bytes,
        extension: str,
        thread_id: uuid.UUID,
        uploader_id: uuid.UUID,
        content_type: str = "application/octet-stream",
    ) -> StoredAttachment:
        _ = uploader_id
        private = get_private_media_storage()
        stored = private.store_validated_bytes(
            data=data,
            folder=inbox_private_folder(thread_id),
            extension=extension,
            content_type=content_type,
            max_bytes=max(len(data), 1),
        )
        return StoredAttachment(key=stored.key)

    def open_bytes(self, key: str) -> bytes:
        return get_private_media_storage().open_bytes(key)

    def delete(self, key: str) -> None:
        get_private_media_storage().delete(key)

    def exists(self, key: str) -> bool:
        return get_private_media_storage().exists(key)

    def supports_presign(self) -> bool:
        return get_private_media_storage().supports_presign()

    def presign_get(self, key: str, *, expires_in: int = 900) -> str | None:
        private = get_private_media_storage()
        if not private.supports_presign():
            return None
        return private.presign_get(key, expires_in=expires_in)


# Back-compat name used in docs/comments.
S3AttachmentStorage = PrivateR2AttachmentStorage


def get_attachment_storage() -> AttachmentStorage:
    """Select inbox attachment backend.

    - MEDIA_STORAGE_PROVIDER=local → local private disk
    - MEDIA_STORAGE_PROVIDER=r2 → private R2 (never public padeya-media)
    - MESSAGING_ATTACHMENT_STORAGE_PROVIDER=r2|s3 forces private R2
    """
    settings = get_settings()
    msg_provider = (
        settings.messaging_attachment_storage_provider or "local"
    ).strip().lower()
    media_provider = media_storage_provider()

    if media_provider == "r2" or msg_provider in {"s3", "r2", "s3-compatible"}:
        return PrivateR2AttachmentStorage()
    if msg_provider in {"local", "filesystem", "disk"}:
        return LocalAttachmentStorage()
    raise ValueError(
        f"Unknown MESSAGING_ATTACHMENT_STORAGE_PROVIDER={msg_provider!r}. "
        "Use local (or r2 when MEDIA_STORAGE_PROVIDER=r2)."
    )


def attachment_api_path(attachment_id: uuid.UUID) -> str:
    """Authorized download path — never a filesystem path."""
    prefix = (get_settings().api_prefix or "/api/v1").rstrip("/")
    return f"{prefix}/messages/attachments/{attachment_id}"


def sign_attachment_download_token(
    *,
    attachment_id: uuid.UUID,
    user_id: uuid.UUID,
    ttl_seconds: int | None = None,
) -> str:
    """Short-lived HMAC token so <img src> can load private files."""
    settings = get_settings()
    ttl = ttl_seconds
    if ttl is None:
        from app.runtime_settings import get_runtime_setting

        ttl = int(
            get_runtime_setting("messaging_attachment_download_ttl_seconds", settings=settings)
            or 900
        )
    ttl = max(60, min(ttl, 3600))
    exp = int(time.time()) + ttl
    payload = f"{attachment_id}:{user_id}:{exp}"
    sig = hmac.new(
        settings.effective_qr_secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    raw = f"{payload}:{base64.urlsafe_b64encode(sig).decode('ascii').rstrip('=')}"
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii").rstrip("=")


def verify_attachment_download_token(
    token: str, *, attachment_id: uuid.UUID
) -> uuid.UUID | None:
    """Return user_id when token is valid for this attachment; else None."""
    try:
        pad = "=" * (-len(token) % 4)
        decoded = base64.urlsafe_b64decode(token + pad).decode("utf-8")
        att_s, user_s, exp_s, sig_b64 = decoded.rsplit(":", 3)
        if uuid.UUID(att_s) != attachment_id:
            return None
        if int(exp_s) < int(time.time()):
            return None
        payload = f"{att_s}:{user_s}:{exp_s}"
        expected = hmac.new(
            get_settings().effective_qr_secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        got = base64.urlsafe_b64decode(sig_b64 + "=" * (-len(sig_b64) % 4))
        if not hmac.compare_digest(expected, got):
            return None
        return uuid.UUID(user_s)
    except Exception:
        return None


def signed_attachment_url(
    attachment_id: uuid.UUID, *, viewer_id: uuid.UUID
) -> str:
    token = sign_attachment_download_token(
        attachment_id=attachment_id, user_id=viewer_id
    )
    return f"{attachment_api_path(attachment_id)}?d={token}"
