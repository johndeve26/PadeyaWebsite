"""Shared Cloudflare R2 (S3-compatible) client helpers.

Public and private buckets reuse this module — do not duplicate boto3 setup.
Never log credentials, Authorization headers, or presigned URLs.
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from app.core.config import Settings, get_settings
from app.core.media import MediaStorageError

logger = logging.getLogger(__name__)

IMMUTABLE_PUBLIC_CACHE_CONTROL = "public, max-age=31536000, immutable"
PUBLIC_MEDIA_OBJECT_METADATA = {"x-content-type-options": "nosniff"}
PRIVATE_CACHE_CONTROL = "private, no-store"


@dataclass(frozen=True)
class R2ClientConfig:
    label: str  # "public" | "private"
    bucket: str
    endpoint: str
    access_key_id: str
    secret_access_key: str
    public_base_url: str | None = None  # only for public bucket


def _missing(fields: dict[str, str]) -> list[str]:
    return [name for name, value in fields.items() if not (value or "").strip()]


def public_r2_config(settings: Settings | None = None) -> R2ClientConfig:
    settings = settings or get_settings()
    missing = _missing(
        {
            "R2_ENDPOINT": settings.r2_endpoint,
            "R2_BUCKET_NAME": settings.r2_bucket_name,
            "R2_ACCESS_KEY_ID": settings.r2_access_key_id,
            "R2_SECRET_ACCESS_KEY": settings.r2_secret_access_key,
            "R2_PUBLIC_URL": settings.r2_public_url,
        }
    )
    if missing:
        raise MediaStorageError(
            "Public R2 media storage is misconfigured. Missing: " + ", ".join(missing)
        )
    return R2ClientConfig(
        label="public",
        bucket=settings.r2_bucket_name.strip(),
        endpoint=settings.r2_endpoint.strip(),
        access_key_id=settings.r2_access_key_id.strip(),
        secret_access_key=settings.r2_secret_access_key.strip(),
        public_base_url=settings.r2_public_url.strip().rstrip("/"),
    )


def private_r2_config(settings: Settings | None = None) -> R2ClientConfig:
    settings = settings or get_settings()
    missing = _missing(
        {
            "R2_PRIVATE_ENDPOINT": settings.r2_private_endpoint,
            "R2_PRIVATE_BUCKET_NAME": settings.r2_private_bucket_name,
            "R2_PRIVATE_ACCESS_KEY_ID": settings.r2_private_access_key_id,
            "R2_PRIVATE_SECRET_ACCESS_KEY": settings.r2_private_secret_access_key,
        }
    )
    if missing:
        raise MediaStorageError(
            "Private R2 media storage is misconfigured. Missing: " + ", ".join(missing)
        )
    return R2ClientConfig(
        label="private",
        bucket=settings.r2_private_bucket_name.strip(),
        endpoint=settings.r2_private_endpoint.strip(),
        access_key_id=settings.r2_private_access_key_id.strip(),
        secret_access_key=settings.r2_private_secret_access_key.strip(),
        public_base_url=None,
    )


def r2_public_domain(settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    raw = (settings.r2_public_url or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    return parsed.netloc or raw.rstrip("/")


def make_object_key(*, folder: str, extension: str) -> str:
    safe_folder = re.sub(r"[^a-zA-Z0-9/_-]+", "-", folder).strip("-/") or "media"
    ext = extension if extension.startswith(".") else f".{extension}"
    ext = re.sub(r"[^a-zA-Z0-9.]+", "", ext)[:16] or ".bin"
    return f"{safe_folder}/{uuid.uuid4()}{ext}"


def guess_image_content_type(key: str) -> str | None:
    """Map a storage key / path extension to an image MIME type."""
    lower = (key or "").lower()
    if lower.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith(".webp"):
        return "image/webp"
    if lower.endswith(".gif"):
        return "image/gif"
    if lower.endswith(".svg"):
        return "image/svg+xml"
    return None


# Back-compat alias used by older call sites / scripts.
_guess_image_content_type = guess_image_content_type


def build_r2_client(config: R2ClientConfig) -> Any:
    try:
        import boto3
    except ImportError as exc:  # pragma: no cover
        raise MediaStorageError("boto3 is required for R2 media storage") from exc
    return boto3.client(
        "s3",
        endpoint_url=config.endpoint,
        aws_access_key_id=config.access_key_id,
        aws_secret_access_key=config.secret_access_key,
        region_name="auto",
    )


class R2BucketClient:
    """Thin wrapper around one R2 bucket. Never logs secrets or signed URLs."""

    def __init__(self, config: R2ClientConfig) -> None:
        self.config = config
        self._client = build_r2_client(config)
        if config.label == "public":
            logger.info(
                "R2 storage configured: yes kind=public bucket=%s public_domain=%s",
                config.bucket,
                r2_public_domain(),
            )
        else:
            logger.info(
                "R2 storage configured: yes kind=private bucket=%s",
                config.bucket,
            )

    @property
    def bucket(self) -> str:
        return self.config.bucket

    def put_object(
        self,
        *,
        key: str,
        data: bytes,
        content_type: str,
        cache_control: str,
        metadata: dict[str, str] | None = None,
        content_disposition: str | None = None,
    ) -> None:
        try:
            kwargs: dict[str, Any] = {
                "Bucket": self.config.bucket,
                "Key": key,
                "Body": data,
                "ContentType": content_type,
                "CacheControl": cache_control,
                "Metadata": metadata or {},
            }
            # Public images must open inline in the browser (preview), not download.
            if content_disposition:
                kwargs["ContentDisposition"] = content_disposition
            elif content_type.startswith("image/"):
                kwargs["ContentDisposition"] = "inline"
            self._client.put_object(**kwargs)
            logger.info(
                "media_storage provider=r2 kind=%s bucket=%s operation=upload "
                "result=success key_prefix=%s",
                self.config.label,
                self.config.bucket,
                key.rsplit("/", 1)[0] if "/" in key else key,
            )
        except Exception as exc:
            logger.error(
                "media_storage provider=r2 kind=%s bucket=%s operation=upload "
                "result=failure key_prefix=%s error_type=%s",
                self.config.label,
                self.config.bucket,
                key.rsplit("/", 1)[0] if "/" in key else key,
                type(exc).__name__,
            )
            raise MediaStorageError("Failed to upload media") from exc

    def delete_object(self, key: str) -> None:
        cleaned = (key or "").replace("\\", "/").lstrip("/")
        if not cleaned or ".." in cleaned.split("/"):
            return
        try:
            self._client.delete_object(Bucket=self.config.bucket, Key=cleaned)
            logger.info(
                "media_storage provider=r2 kind=%s bucket=%s operation=delete "
                "result=success key_prefix=%s",
                self.config.label,
                self.config.bucket,
                cleaned.rsplit("/", 1)[0] if "/" in cleaned else cleaned,
            )
        except Exception as exc:
            logger.error(
                "media_storage provider=r2 kind=%s bucket=%s operation=delete "
                "result=failure key_prefix=%s error_type=%s",
                self.config.label,
                self.config.bucket,
                cleaned.rsplit("/", 1)[0] if "/" in cleaned else cleaned,
                type(exc).__name__,
            )
            raise MediaStorageError("Failed to delete media") from exc

    def head_object(self, key: str) -> bool:
        cleaned = (key or "").replace("\\", "/").lstrip("/")
        if not cleaned or ".." in cleaned.split("/"):
            return False
        try:
            self._client.head_object(Bucket=self.config.bucket, Key=cleaned)
            return True
        except Exception:
            return False

    def rewrite_public_image_headers(
        self,
        key: str,
        *,
        content_type: str | None = None,
        cache_control: str = IMMUTABLE_PUBLIC_CACHE_CONTROL,
    ) -> bool:
        """Replace object metadata so browsers preview images instead of downloading.

        Used to repair older public objects that were stored without
        ``Content-Disposition: inline`` or with a non-image Content-Type.
        """
        cleaned = (key or "").replace("\\", "/").lstrip("/")
        if not cleaned or ".." in cleaned.split("/"):
            return False
        ctype = (content_type or guess_image_content_type(cleaned) or "").strip()
        if not ctype.startswith("image/"):
            return False
        try:
            self._client.copy_object(
                Bucket=self.config.bucket,
                Key=cleaned,
                CopySource={"Bucket": self.config.bucket, "Key": cleaned},
                MetadataDirective="REPLACE",
                ContentType=ctype,
                ContentDisposition="inline",
                CacheControl=cache_control,
                Metadata=PUBLIC_MEDIA_OBJECT_METADATA,
            )
            logger.info(
                "media_storage provider=r2 kind=%s bucket=%s operation=rewrite_headers "
                "result=success key_prefix=%s",
                self.config.label,
                self.config.bucket,
                cleaned.rsplit("/", 1)[0] if "/" in cleaned else cleaned,
            )
            return True
        except Exception as exc:
            logger.error(
                "media_storage provider=r2 kind=%s bucket=%s operation=rewrite_headers "
                "result=failure key_prefix=%s error_type=%s",
                self.config.label,
                self.config.bucket,
                cleaned.rsplit("/", 1)[0] if "/" in cleaned else cleaned,
                type(exc).__name__,
            )
            return False

    def get_object_bytes(self, key: str) -> bytes:
        cleaned = (key or "").replace("\\", "/").lstrip("/")
        if not cleaned or ".." in cleaned.split("/"):
            raise FileNotFoundError("Invalid storage key")
        try:
            response = self._client.get_object(Bucket=self.config.bucket, Key=cleaned)
            body = response["Body"].read()
            return body
        except Exception as exc:
            logger.error(
                "media_storage provider=r2 kind=%s bucket=%s operation=get "
                "result=failure key_prefix=%s error_type=%s",
                self.config.label,
                self.config.bucket,
                cleaned.rsplit("/", 1)[0] if "/" in cleaned else cleaned,
                type(exc).__name__,
            )
            raise MediaStorageError("Failed to read media") from exc

    def presign_get(
        self,
        key: str,
        *,
        expires_in: int = 900,
        response_content_type: str | None = None,
        response_content_disposition: str | None = None,
    ) -> str:
        cleaned = (key or "").replace("\\", "/").lstrip("/")
        if not cleaned or ".." in cleaned.split("/"):
            raise MediaStorageError("Invalid storage key")
        ttl = max(60, min(int(expires_in), 900))
        try:
            params: dict[str, Any] = {
                "Bucket": self.config.bucket,
                "Key": cleaned,
            }
            if response_content_type:
                params["ResponseContentType"] = response_content_type
            if response_content_disposition:
                params["ResponseContentDisposition"] = response_content_disposition
            url = self._client.generate_presigned_url(
                "get_object",
                Params=params,
                ExpiresIn=ttl,
            )
            # Never log the signed URL.
            logger.info(
                "media_storage provider=r2 kind=%s bucket=%s operation=presign_get "
                "result=success key_prefix=%s expires_in=%s",
                self.config.label,
                self.config.bucket,
                cleaned.rsplit("/", 1)[0] if "/" in cleaned else cleaned,
                ttl,
            )
            return url
        except Exception as exc:
            logger.error(
                "media_storage provider=r2 kind=%s bucket=%s operation=presign_get "
                "result=failure key_prefix=%s error_type=%s",
                self.config.label,
                self.config.bucket,
                cleaned.rsplit("/", 1)[0] if "/" in cleaned else cleaned,
                type(exc).__name__,
            )
            raise MediaStorageError("Failed to authorize media download") from exc

    def check_connectivity(self) -> dict[str, bool | str]:
        result: dict[str, bool | str] = {
            "configured": True,
            "reachable": False,
            "bucket_accessible": False,
            "provider": "r2",
            "kind": self.config.label,
            "bucket": self.config.bucket,
        }
        if self.config.label == "public":
            result["public_domain"] = r2_public_domain()
        try:
            self._client.list_objects_v2(Bucket=self.config.bucket, MaxKeys=1)
            result["reachable"] = True
            result["bucket_accessible"] = True
        except Exception as exc:
            logger.error(
                "media_storage provider=r2 kind=%s bucket=%s operation=connectivity "
                "result=failure error_type=%s",
                self.config.label,
                self.config.bucket,
                type(exc).__name__,
            )
        return result
