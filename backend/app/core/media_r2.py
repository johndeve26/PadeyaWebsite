"""Cloudflare R2 (S3-compatible) public media storage."""

from __future__ import annotations

import logging
import re
import uuid
from urllib.parse import urlparse

from app.core.config import Settings, get_settings
from app.core.media import (
    ALLOWED_IMAGE_CONTENT_TYPES,
    CONTENT_TYPE_EXTENSIONS,
    MAX_UPLOAD_BYTES,
    MediaStorage,
    MediaStorageError,
    StoredMedia,
    normalize_public_media_url,
)

logger = logging.getLogger(__name__)

IMMUTABLE_CACHE_CONTROL = "public, max-age=31536000, immutable"


def validate_r2_settings(settings: Settings | None = None) -> None:
    """Raise MediaStorageError if R2 env is incomplete. Never logs secret values."""
    settings = settings or get_settings()
    missing: list[str] = []
    if not (settings.r2_endpoint or "").strip():
        missing.append("R2_ENDPOINT")
    if not (settings.r2_bucket_name or "").strip():
        missing.append("R2_BUCKET_NAME")
    if not (settings.r2_access_key_id or "").strip():
        missing.append("R2_ACCESS_KEY_ID")
    if not (settings.r2_secret_access_key or "").strip():
        missing.append("R2_SECRET_ACCESS_KEY")
    if not (settings.r2_public_url or "").strip():
        missing.append("R2_PUBLIC_URL")
    if missing:
        raise MediaStorageError(
            "R2 media storage is misconfigured. Missing: " + ", ".join(missing)
        )


def r2_public_domain(settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    raw = (settings.r2_public_url or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    return parsed.netloc or raw.rstrip("/")


class R2MediaStorage(MediaStorage):
    """Stores public media in Cloudflare R2; URLs use R2_PUBLIC_URL."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        validate_r2_settings(self._settings)
        self._bucket = self._settings.r2_bucket_name.strip()
        self._public_base = self._settings.r2_public_url.strip().rstrip("/")
        self._endpoint = self._settings.r2_endpoint.strip()
        try:
            import boto3
        except ImportError as exc:  # pragma: no cover
            raise MediaStorageError(
                "boto3 is required for R2 media storage"
            ) from exc
        self._client = boto3.client(
            "s3",
            endpoint_url=self._endpoint,
            aws_access_key_id=self._settings.r2_access_key_id,
            aws_secret_access_key=self._settings.r2_secret_access_key,
            region_name="auto",
        )
        logger.info(
            "R2 storage configured: yes bucket=%s public_domain=%s",
            self._bucket,
            r2_public_domain(self._settings),
        )

    def _public_url(self, key: str) -> str:
        return f"{self._public_base}/{key.lstrip('/')}"

    def _make_key(self, *, folder: str, extension: str) -> str:
        safe_folder = re.sub(r"[^a-zA-Z0-9/_-]+", "-", folder).strip("-/") or "events"
        ext = extension if extension.startswith(".") else f".{extension}"
        ext = re.sub(r"[^a-zA-Z0-9.]+", "", ext)[:16] or ".bin"
        return f"{safe_folder}/{uuid.uuid4()}{ext}"

    def _put(
        self,
        *,
        key: str,
        data: bytes,
        content_type: str,
        cache_control: str = IMMUTABLE_CACHE_CONTROL,
    ) -> None:
        try:
            self._client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
                CacheControl=cache_control,
            )
            logger.info(
                "media_storage provider=r2 bucket=%s operation=upload "
                "result=success key_prefix=%s",
                self._bucket,
                key.rsplit("/", 1)[0] if "/" in key else key,
            )
        except MediaStorageError:
            raise
        except Exception as exc:
            logger.error(
                "media_storage provider=r2 bucket=%s operation=upload "
                "result=failure key_prefix=%s error_type=%s",
                self._bucket,
                key.rsplit("/", 1)[0] if "/" in key else key,
                type(exc).__name__,
            )
            raise MediaStorageError("Failed to upload media") from exc

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
        # UUID prefix keeps keys unique; filename suffix is cosmetic only.
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

        return self.store_validated_bytes(
            data=data,
            filename=filename,
            content_type=ctype,
            folder=folder,
            extension=ext,
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
        key = self._make_key(folder=folder, extension=extension)
        self._put(
            key=key,
            data=data,
            content_type=ctype or "application/octet-stream",
            cache_control=cache_control or IMMUTABLE_CACHE_CONTROL,
        )
        return StoredMedia(url=self._public_url(key), key=key)

    def delete(self, key: str) -> None:
        cleaned = (key or "").replace("\\", "/").lstrip("/")
        if not cleaned or ".." in cleaned.split("/"):
            return
        try:
            self._client.delete_object(Bucket=self._bucket, Key=cleaned)
            logger.info(
                "media_storage provider=r2 bucket=%s operation=delete "
                "result=success key_prefix=%s",
                self._bucket,
                cleaned.rsplit("/", 1)[0] if "/" in cleaned else cleaned,
            )
        except Exception as exc:
            logger.error(
                "media_storage provider=r2 bucket=%s operation=delete "
                "result=failure key_prefix=%s error_type=%s",
                self._bucket,
                cleaned.rsplit("/", 1)[0] if "/" in cleaned else cleaned,
                type(exc).__name__,
            )
            raise MediaStorageError("Failed to delete media") from exc

    def exists(self, key: str) -> bool:
        cleaned = (key or "").replace("\\", "/").lstrip("/")
        if not cleaned or ".." in cleaned.split("/"):
            return False
        try:
            self._client.head_object(Bucket=self._bucket, Key=cleaned)
            return True
        except Exception:
            return False

    def check_connectivity(self) -> dict[str, bool | str]:
        """Lightweight internal probe — never returns credentials."""
        result: dict[str, bool | str] = {
            "configured": True,
            "reachable": False,
            "bucket_accessible": False,
            "provider": "r2",
            "bucket": self._bucket,
            "public_domain": r2_public_domain(self._settings),
        }
        try:
            self._client.list_objects_v2(Bucket=self._bucket, MaxKeys=1)
            result["reachable"] = True
            result["bucket_accessible"] = True
        except Exception as exc:
            logger.error(
                "media_storage provider=r2 bucket=%s operation=connectivity "
                "result=failure error_type=%s",
                self._bucket,
                type(exc).__name__,
            )
        return result
