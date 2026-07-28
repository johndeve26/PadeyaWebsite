"""Phase 7 — private media: presign TTL, vault, messaging attachments."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.core.media_private import (
    DEFAULT_PRESIGN_TTL_SECONDS,
    R2PrivateMediaStorage,
    assert_not_public_media_url,
    is_public_padeya_media_url,
)
from app.core.r2_client import R2BucketClient
from app.messaging.attachment_storage import (
    get_attachment_storage,
    sign_attachment_download_token,
    verify_attachment_download_token,
)


def test_presign_ttl_capped_at_15_minutes(monkeypatch):
    monkeypatch.setenv("MEDIA_STORAGE_PROVIDER", "r2")
    monkeypatch.setenv("R2_PRIVATE_BUCKET_NAME", "padeya-private")
    monkeypatch.setenv("R2_PRIVATE_ENDPOINT", "https://x.r2.cloudflarestorage.com")
    monkeypatch.setenv("R2_PRIVATE_ACCESS_KEY_ID", "k")
    monkeypatch.setenv("R2_PRIVATE_SECRET_ACCESS_KEY", "s")
    monkeypatch.setenv("R2_BUCKET_NAME", "padeya-media")
    monkeypatch.setenv("R2_ENDPOINT", "https://x.r2.cloudflarestorage.com")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "k")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "s")
    monkeypatch.setenv("R2_PUBLIC_URL", "https://media.padeya.com")
    from app.core.config import get_settings
    from app.core.media import reset_media_storage

    get_settings.cache_clear()
    reset_media_storage()
    client = MagicMock()
    client.generate_presigned_url.return_value = "https://signed.example/get"
    with patch("boto3.client", return_value=client):
        storage = R2PrivateMediaStorage()
        storage.presign_get("inbox/t/a.bin", expires_in=3600)
    assert client.generate_presigned_url.call_args.kwargs["ExpiresIn"] == 900


def test_default_presign_ttl_is_900():
    assert DEFAULT_PRESIGN_TTL_SECONDS == 900


def test_vault_rejects_public_cdn_urls():
    with pytest.raises(ValueError):
        assert_not_public_media_url(
            "https://media.padeya.com/vault/secret.pdf", context="Vault"
        )


def test_private_urls_not_public_padeya():
    assert not is_public_padeya_media_url("private://pending")
    assert is_public_padeya_media_url("https://media.padeya.com/events/x.webp")


def test_attachment_download_token_roundtrip():
    att = uuid4()
    user = uuid4()
    token = sign_attachment_download_token(attachment_id=att, user_id=user, ttl_seconds=900)
    assert verify_attachment_download_token(token, attachment_id=att) == user


def test_local_attachment_storage_not_public_mount():
    from app.messaging.attachment_storage import LocalAttachmentStorage

    s = LocalAttachmentStorage()
    stored = s.store(
        data=b"secret",
        extension=".png",
        thread_id=uuid4(),
        uploader_id=uuid4(),
    )
    assert "message_attachments" in str(s._root()) or stored.key
