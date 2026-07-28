"""Phase 7 — public/private storage factory separation and key isolation."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.core.config import get_settings
from app.core.media import (
    LocalMediaStorage,
    MediaStorageError,
    get_public_media_storage,
    reset_media_storage,
    validate_media_storage_config,
)
from app.core.media_folders import (
    inbox_private_folder,
    memory_public_folder,
    vault_private_folder,
)
from app.core.media_private import (
    LocalPrivateMediaStorage,
    R2PrivateMediaStorage,
    get_private_media_storage,
)
from app.core.media_r2 import R2MediaStorage


def _clear() -> None:
    get_settings.cache_clear()
    reset_media_storage()


@pytest.fixture(autouse=True)
def _reset_storage():
    _clear()
    yield
    _clear()
    os.environ["MEDIA_STORAGE_PROVIDER"] = "local"


def _set_dual_r2(monkeypatch, *, private_ok=True) -> None:
    monkeypatch.setenv("MEDIA_STORAGE_PROVIDER", "r2")
    monkeypatch.setenv("R2_BUCKET_NAME", "padeya-media")
    monkeypatch.setenv("R2_ENDPOINT", "https://acct.r2.cloudflarestorage.com")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "pub-key")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "pub-secret")
    monkeypatch.setenv("R2_PUBLIC_URL", "https://media.padeya.com")
    if private_ok:
        monkeypatch.setenv("R2_PRIVATE_BUCKET_NAME", "padeya-private")
        monkeypatch.setenv("R2_PRIVATE_ENDPOINT", "https://acct.r2.cloudflarestorage.com")
        monkeypatch.setenv("R2_PRIVATE_ACCESS_KEY_ID", "priv-key")
        monkeypatch.setenv("R2_PRIVATE_SECRET_ACCESS_KEY", "priv-secret")
    else:
        for k in (
            "R2_PRIVATE_BUCKET_NAME",
            "R2_PRIVATE_ENDPOINT",
            "R2_PRIVATE_ACCESS_KEY_ID",
            "R2_PRIVATE_SECRET_ACCESS_KEY",
        ):
            monkeypatch.delenv(k, raising=False)
    _clear()


def test_local_factories_are_distinct():
    public = get_public_media_storage()
    private = get_private_media_storage()
    assert isinstance(public, LocalMediaStorage)
    assert isinstance(private, LocalPrivateMediaStorage)
    assert public is not private


def test_r2_private_missing_config_fails_closed(monkeypatch):
    _set_dual_r2(monkeypatch, private_ok=False)
    with pytest.raises(MediaStorageError):
        validate_media_storage_config()


def test_r2_private_never_falls_back_to_public_bucket(monkeypatch):
    _set_dual_r2(monkeypatch, private_ok=False)
    with patch("boto3.client", return_value=MagicMock()):
        with pytest.raises(MediaStorageError):
            get_private_media_storage()


def test_public_private_bucket_separation(monkeypatch):
    _set_dual_r2(monkeypatch)
    client = MagicMock()
    with patch("boto3.client", return_value=client):
        pub = R2MediaStorage()
        priv = R2PrivateMediaStorage()
        pub.store_validated_bytes(
            data=b"x",
            filename="a.webp",
            content_type="image/webp",
            folder=memory_public_folder(uuid4()),
            extension=".webp",
            max_bytes=100,
        )
        priv.store_validated_bytes(
            data=b"y",
            folder=vault_private_folder(uuid4()),
            extension=".pdf",
            content_type="application/pdf",
            max_bytes=100,
        )
    buckets = {c.kwargs["Bucket"] for c in client.put_object.call_args_list}
    assert buckets == {"padeya-media", "padeya-private"}


def test_path_traversal_rejected_on_local_public():
    storage = LocalMediaStorage()
    storage.delete("../../etc/passwd")
    assert storage.exists("../../etc/passwd") is False


def test_private_key_namespaces_disjoint():
    eid = uuid4()
    tid = uuid4()
    assert memory_public_folder(eid).startswith("memories/events/")
    assert inbox_private_folder(tid).startswith("inbox/")
    assert vault_private_folder(uuid4()).startswith("vault/")
    assert not inbox_private_folder(tid).startswith("memories/")
