"""Unit tests for media storage provider selection and R2MediaStorage (mocked)."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.core.config import get_settings
from app.core.media import (
    LocalMediaStorage,
    MediaStorageError,
    delete_media_keys,
    get_media_storage,
    media_storage_provider,
    reset_media_storage,
    storage_key_from_url,
    validate_media_storage_config,
)
from app.core.media_r2 import IMMUTABLE_CACHE_CONTROL, R2MediaStorage, validate_r2_settings
from app.memories.models import EventMemoryMedia
from app.memories.photos import _delete_photo_storage_objects


def _clear_settings() -> None:
    get_settings.cache_clear()
    reset_media_storage()


@pytest.fixture(autouse=True)
def _reset_storage_singleton():
    _clear_settings()
    yield
    _clear_settings()
    os.environ["MEDIA_STORAGE_PROVIDER"] = "local"


def _set_r2_env(monkeypatch, *, complete: bool = True) -> None:
    monkeypatch.setenv("MEDIA_STORAGE_PROVIDER", "r2")
    if complete:
        monkeypatch.setenv("R2_BUCKET_NAME", "padeya-media")
        monkeypatch.setenv(
            "R2_ENDPOINT", "https://example-account.r2.cloudflarestorage.com"
        )
        monkeypatch.setenv("R2_ACCESS_KEY_ID", "test-access-key")
        monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "test-secret-key-value")
        monkeypatch.setenv("R2_PUBLIC_URL", "https://media.padeya.com")
    else:
        monkeypatch.delenv("R2_BUCKET_NAME", raising=False)
        monkeypatch.delenv("R2_ENDPOINT", raising=False)
        monkeypatch.delenv("R2_ACCESS_KEY_ID", raising=False)
        monkeypatch.delenv("R2_SECRET_ACCESS_KEY", raising=False)
        monkeypatch.delenv("R2_PUBLIC_URL", raising=False)
    _clear_settings()


def test_local_provider_selection(monkeypatch):
    monkeypatch.setenv("MEDIA_STORAGE_PROVIDER", "local")
    _clear_settings()
    assert media_storage_provider() == "local"
    storage = get_media_storage()
    assert isinstance(storage, LocalMediaStorage)


def test_r2_provider_selection(monkeypatch):
    _set_r2_env(monkeypatch, complete=True)
    with patch("boto3.client") as client_factory:
        client_factory.return_value = MagicMock()
        storage = get_media_storage()
    assert isinstance(storage, R2MediaStorage)
    client_factory.assert_called_once()
    kwargs = client_factory.call_args.kwargs
    assert kwargs["endpoint_url"] == "https://example-account.r2.cloudflarestorage.com"
    assert kwargs["region_name"] == "auto"
    assert kwargs["aws_access_key_id"] == "test-access-key"
    assert kwargs["aws_secret_access_key"] == "test-secret-key-value"


def test_missing_r2_config_fails(monkeypatch):
    _set_r2_env(monkeypatch, complete=False)
    monkeypatch.setenv("R2_BUCKET_NAME", "padeya-media")
    _clear_settings()
    with pytest.raises(MediaStorageError) as exc:
        validate_media_storage_config()
    msg = str(exc.value)
    assert "R2_ENDPOINT" in msg
    assert "test-secret" not in msg
    assert "test-access" not in msg


def test_validate_r2_settings_lists_missing_only(monkeypatch):
    _set_r2_env(monkeypatch, complete=False)
    with pytest.raises(MediaStorageError) as exc:
        validate_r2_settings()
    for name in (
        "R2_ENDPOINT",
        "R2_BUCKET_NAME",
        "R2_ACCESS_KEY_ID",
        "R2_SECRET_ACCESS_KEY",
        "R2_PUBLIC_URL",
    ):
        assert name in str(exc.value)


def test_r2_upload_bucket_key_headers_and_public_url(monkeypatch):
    _set_r2_env(monkeypatch, complete=True)
    client = MagicMock()
    with patch("boto3.client", return_value=client):
        storage = R2MediaStorage()
        stored = storage.store_validated_bytes(
            data=b"webp-bytes",
            filename="../../evil name.webp",
            content_type="image/webp",
            folder="memories/events/evt-1",
            extension=".webp",
            max_bytes=1024,
        )

    client.put_object.assert_called_once()
    call = client.put_object.call_args.kwargs
    assert call["Bucket"] == "padeya-media"
    assert call["ContentType"] == "image/webp"
    assert call["CacheControl"] == IMMUTABLE_CACHE_CONTROL
    assert call["Body"] == b"webp-bytes"
    key = call["Key"]
    assert key.startswith("memories/events/evt-1/")
    assert key.endswith(".webp")
    assert "evil" not in key
    assert ".." not in key
    assert stored.key == key
    assert stored.url == f"https://media.padeya.com/{key}"
    assert "r2.cloudflarestorage.com" not in stored.url


def test_r2_thumbnail_url_under_thumbs(monkeypatch):
    _set_r2_env(monkeypatch, complete=True)
    client = MagicMock()
    with patch("boto3.client", return_value=client):
        storage = R2MediaStorage()
        stored = storage.store_validated_bytes(
            data=b"thumb",
            filename="ignored.jpg",
            content_type="image/webp",
            folder=f"memories/events/{uuid4()}/thumbs",
            extension=".webp",
            max_bytes=1024,
        )
    assert "/thumbs/" in stored.key
    assert stored.url.startswith("https://media.padeya.com/memories/events/")


def test_r2_delete(monkeypatch):
    _set_r2_env(monkeypatch, complete=True)
    client = MagicMock()
    with patch("boto3.client", return_value=client):
        storage = R2MediaStorage()
        storage.delete("memories/events/abc/file.webp")
    client.delete_object.assert_called_once_with(
        Bucket="padeya-media",
        Key="memories/events/abc/file.webp",
    )


def test_r2_upload_failure_raises_safe_error(monkeypatch):
    _set_r2_env(monkeypatch, complete=True)
    client = MagicMock()
    client.put_object.side_effect = RuntimeError("boom credentials=test-secret-key-value")
    with patch("boto3.client", return_value=client):
        storage = R2MediaStorage()
        with pytest.raises(MediaStorageError) as exc:
            storage.store_validated_bytes(
                data=b"x",
                filename="a.webp",
                content_type="image/webp",
                folder="memories/events/x",
                extension=".webp",
                max_bytes=10,
            )
    assert "Failed to upload media" in str(exc.value)
    assert "test-secret" not in str(exc.value)
    assert "credentials=" not in str(exc.value)


def test_invalid_user_filename_cannot_control_storage_key(monkeypatch, tmp_path):
    monkeypatch.setenv("MEDIA_STORAGE_PROVIDER", "local")
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path))
    _clear_settings()
    storage = LocalMediaStorage()
    stored = storage.store_validated_bytes(
        data=b"hello",
        filename="../../../etc/passwd",
        content_type="image/webp",
        folder="memories/events/demo",
        extension=".webp",
        max_bytes=100,
    )
    assert "passwd" not in stored.key
    assert ".." not in stored.key
    assert stored.key.startswith("memories/events/demo/")
    assert stored.key.endswith(".webp")


def test_storage_key_from_url_r2_and_local(monkeypatch):
    monkeypatch.setenv("R2_PUBLIC_URL", "https://media.padeya.com")
    monkeypatch.setenv("MEDIA_PUBLIC_BASE_URL", "http://testserver")
    _clear_settings()
    assert (
        storage_key_from_url("https://media.padeya.com/memories/events/a/b.webp")
        == "memories/events/a/b.webp"
    )
    assert storage_key_from_url("/media/events/x.jpg") == "events/x.jpg"
    assert (
        storage_key_from_url("http://testserver/media/events/x.jpg") == "events/x.jpg"
    )


def test_permanent_delete_removes_display_and_thumb(monkeypatch):
    monkeypatch.setenv("R2_PUBLIC_URL", "https://media.padeya.com")
    _clear_settings()
    deleted: list[str] = []

    class FakeStorage:
        def delete(self, key: str) -> None:
            deleted.append(key)

    monkeypatch.setattr("app.core.media.get_media_storage", lambda: FakeStorage())
    media = EventMemoryMedia(
        memory_id=uuid4(),
        media_type="image",
        url="https://media.padeya.com/memories/events/a/display.webp",
        storage_key="memories/events/a/display.webp",
        thumbnail_url="https://media.padeya.com/memories/events/a/thumbs/t.webp",
        status="removed",
    )
    _delete_photo_storage_objects(media)
    assert "memories/events/a/display.webp" in deleted
    assert "memories/events/a/thumbs/t.webp" in deleted


def test_hide_moderation_does_not_invoke_storage_delete():
    """Hide is moderation state — photos.py must not call object delete for hide."""
    import inspect

    from app.memories import photos as photos_mod

    source = inspect.getsource(photos_mod.host_moderate_photo)
    assert 'action == "hide"' in source
    # Hide branch must not call storage cleanup helper.
    hide_block = source.split('if action == "hide":', 1)[1].split("elif", 1)[0]
    assert "_delete_photo_storage_objects" not in hide_block


def test_db_failure_cleanup_deletes_uploaded_keys(monkeypatch):
    deleted: list[str] = []

    class FakeStorage:
        def delete(self, key: str) -> None:
            deleted.append(key)

    monkeypatch.setattr("app.core.media.get_media_storage", lambda: FakeStorage())
    delete_media_keys("memories/events/a/one.webp", "memories/events/a/thumbs/two.webp")
    assert deleted == [
        "memories/events/a/one.webp",
        "memories/events/a/thumbs/two.webp",
    ]


def test_credentials_never_in_stored_media_repr(monkeypatch):
    _set_r2_env(monkeypatch, complete=True)
    client = MagicMock()
    with patch("boto3.client", return_value=client):
        storage = R2MediaStorage()
        stored = storage.store_validated_bytes(
            data=b"x",
            filename="a.webp",
            content_type="image/webp",
            folder="memories/events/x",
            extension=".webp",
            max_bytes=10,
        )
    blob = repr(stored) + stored.url + stored.key
    assert "test-secret-key-value" not in blob
    assert "test-access-key" not in blob
    assert "r2.cloudflarestorage.com" not in blob
