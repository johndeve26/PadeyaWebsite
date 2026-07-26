"""Public vs private R2 storage architecture tests (mocked boto3)."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.core.config import get_settings
from app.core.media import (
    MediaStorageError,
    get_public_media_storage,
    reset_media_storage,
    validate_media_storage_config,
)
from app.core.media_private import (
    R2PrivateMediaStorage,
    StoredPrivateMedia,
    assert_not_public_media_url,
    get_private_media_storage,
    is_public_padeya_media_url,
)
from app.core.media_r2 import R2MediaStorage
from app.messaging.attachment_storage import (
    LocalAttachmentStorage,
    PrivateR2AttachmentStorage,
    get_attachment_storage,
)


def _clear() -> None:
    get_settings.cache_clear()
    reset_media_storage()


@pytest.fixture(autouse=True)
def _reset():
    _clear()
    yield
    _clear()
    os.environ["MEDIA_STORAGE_PROVIDER"] = "local"


def _set_dual_r2(monkeypatch, *, public_ok=True, private_ok=True) -> None:
    monkeypatch.setenv("MEDIA_STORAGE_PROVIDER", "r2")
    if public_ok:
        monkeypatch.setenv("R2_BUCKET_NAME", "padeya-media")
        monkeypatch.setenv(
            "R2_ENDPOINT", "https://example-account.r2.cloudflarestorage.com"
        )
        monkeypatch.setenv("R2_ACCESS_KEY_ID", "public-access")
        monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "public-secret-value")
        monkeypatch.setenv("R2_PUBLIC_URL", "https://media.padeya.com")
    else:
        for k in (
            "R2_BUCKET_NAME",
            "R2_ENDPOINT",
            "R2_ACCESS_KEY_ID",
            "R2_SECRET_ACCESS_KEY",
            "R2_PUBLIC_URL",
        ):
            monkeypatch.delenv(k, raising=False)
    if private_ok:
        monkeypatch.setenv("R2_PRIVATE_BUCKET_NAME", "padeya-private")
        monkeypatch.setenv(
            "R2_PRIVATE_ENDPOINT",
            "https://example-account.r2.cloudflarestorage.com",
        )
        monkeypatch.setenv("R2_PRIVATE_ACCESS_KEY_ID", "private-access")
        monkeypatch.setenv("R2_PRIVATE_SECRET_ACCESS_KEY", "private-secret-value")
    else:
        for k in (
            "R2_PRIVATE_BUCKET_NAME",
            "R2_PRIVATE_ENDPOINT",
            "R2_PRIVATE_ACCESS_KEY_ID",
            "R2_PRIVATE_SECRET_ACCESS_KEY",
        ):
            monkeypatch.delenv(k, raising=False)
    _clear()


def test_public_and_private_selection(monkeypatch):
    _set_dual_r2(monkeypatch)
    with patch("boto3.client", return_value=MagicMock()):
        public = get_public_media_storage()
        private = get_private_media_storage()
    assert isinstance(public, R2MediaStorage)
    assert isinstance(private, R2PrivateMediaStorage)


def test_missing_private_config_fails_validation(monkeypatch):
    _set_dual_r2(monkeypatch, private_ok=False)
    with pytest.raises(MediaStorageError) as exc:
        validate_media_storage_config()
    msg = str(exc.value)
    assert "R2_PRIVATE_" in msg
    assert "private-secret" not in msg


def test_private_does_not_fall_back_to_public_bucket(monkeypatch):
    _set_dual_r2(monkeypatch, private_ok=False)
    with patch("boto3.client", return_value=MagicMock()):
        with pytest.raises(MediaStorageError):
            get_private_media_storage()


def test_public_upload_url_and_bucket(monkeypatch):
    _set_dual_r2(monkeypatch)
    client = MagicMock()
    with patch("boto3.client", return_value=client):
        storage = R2MediaStorage()
        stored = storage.store_validated_bytes(
            data=b"img",
            filename="x.webp",
            content_type="image/webp",
            folder="events/abc/gallery",
            extension=".webp",
            max_bytes=100,
        )
    assert client.put_object.call_args.kwargs["Bucket"] == "padeya-media"
    assert stored.url.startswith("https://media.padeya.com/")
    assert "r2.cloudflarestorage.com" not in stored.url


def test_private_upload_has_no_public_url(monkeypatch):
    _set_dual_r2(monkeypatch)
    client = MagicMock()
    with patch("boto3.client", return_value=client):
        storage = R2PrivateMediaStorage()
        stored = storage.store_validated_bytes(
            data=b"secret",
            folder="inbox/thread-1/attachments",
            extension=".png",
            content_type="image/png",
            max_bytes=100,
        )
    assert isinstance(stored, StoredPrivateMedia)
    assert not hasattr(stored, "url")
    assert client.put_object.call_args.kwargs["Bucket"] == "padeya-private"
    assert "media.padeya.com" not in stored.key
    assert stored.key.startswith("inbox/")


def test_private_presign_not_persisted_and_uses_private_bucket(monkeypatch):
    _set_dual_r2(monkeypatch)
    client = MagicMock()
    client.generate_presigned_url.return_value = (
        "https://example-account.r2.cloudflarestorage.com/padeya-private/x?X-Amz-Signature=abc"
    )
    with patch("boto3.client", return_value=client):
        storage = R2PrivateMediaStorage()
        url = storage.presign_get("inbox/t/attachments/a.bin", expires_in=600)
    assert "X-Amz-Signature" in url
    kwargs = client.generate_presigned_url.call_args
    assert kwargs.kwargs["Params"]["Bucket"] == "padeya-private"
    assert kwargs.kwargs["ExpiresIn"] == 600
    # Must not look like permanent public CDN.
    assert "media.padeya.com" not in url


def test_inbox_uses_private_r2_when_provider_r2(monkeypatch):
    _set_dual_r2(monkeypatch)
    with patch("boto3.client", return_value=MagicMock()):
        storage = get_attachment_storage()
    assert isinstance(storage, PrivateR2AttachmentStorage)


def test_inbox_local_when_provider_local(monkeypatch):
    monkeypatch.setenv("MEDIA_STORAGE_PROVIDER", "local")
    monkeypatch.setenv("MESSAGING_ATTACHMENT_STORAGE_PROVIDER", "local")
    _clear()
    assert isinstance(get_attachment_storage(), LocalAttachmentStorage)


def test_vault_rejects_public_media_urls():
    assert is_public_padeya_media_url("https://media.padeya.com/vault/x.webp")
    assert is_public_padeya_media_url("/media/vault/x.webp")
    with pytest.raises(ValueError):
        assert_not_public_media_url(
            "https://media.padeya.com/hosts/1/x.webp",
            context="Vault file_url",
        )


def test_memory_and_event_folders_are_public_shaped():
    from app.core.media_folders import (
        event_public_folder,
        host_public_folder,
        inbox_private_folder,
        memory_public_folder,
        support_private_folder,
        vault_private_folder,
    )

    eid = uuid4()
    hid = uuid4()
    assert event_public_folder(eid, "banner").startswith(f"events/{eid}/banner")
    assert memory_public_folder(eid).startswith("memories/events/")
    assert host_public_folder(hid, "avatar").endswith("/avatar")
    assert inbox_private_folder(eid).startswith("inbox/")
    assert support_private_folder(eid).startswith("support/")
    assert vault_private_folder(hid).startswith("vault/")
