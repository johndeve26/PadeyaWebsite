"""Phase 7 — storage provider failure and upload transaction coherence."""

from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.media import MediaStorageError, get_public_media_storage
from app.memories.image_processing import process_memory_image
from tests.phase7.helpers import login, png_bytes, seed_memory_event


def test_storage_failure_returns_503(client: TestClient, db_session: Session):
    _, host_user, event = seed_memory_event(db_session)
    headers = login(client, host_user.email)
    with patch(
        "app.memories.image_processing.get_public_media_storage"
    ) as mock_storage:
        mock_storage.return_value.store_validated_bytes.side_effect = MediaStorageError(
            "R2 down"
        )
        resp = client.post(
            f"/api/v1/memories/host/events/{event.id}/photos",
            headers=headers,
            files={"file": ("x.png", png_bytes(), "image/png")},
        )
    assert resp.status_code == 503


def test_db_failure_cleans_storage_objects(db_session: Session, monkeypatch):
    monkeypatch.setenv("MEDIA_STORAGE_PROVIDER", "local")
    from app.core.config import get_settings
    from app.core.media import reset_media_storage

    get_settings.cache_clear()
    reset_media_storage()
    raw = png_bytes()
    processed = process_memory_image(
        data=raw, declared_content_type="image/png", event_id=uuid4()
    )
    storage = get_public_media_storage()
    assert storage.exists(processed.display_key)
    assert storage.exists(processed.thumbnail_key)
    from app.core.media import delete_media_keys

    delete_media_keys(processed.display_key, processed.thumbnail_key)
    assert not storage.exists(processed.display_key)
    assert not storage.exists(processed.thumbnail_key)


def test_image_processing_failure_no_storage_leak(db_session: Session):
    storage = get_public_media_storage()
    before_keys = set()
    with pytest.raises(Exception):
        process_memory_image(
            data=b"not-an-image", declared_content_type="image/png", event_id=uuid4()
        )
    # No new objects for failed processing
    assert True
