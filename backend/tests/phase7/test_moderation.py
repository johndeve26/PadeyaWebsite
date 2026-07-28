"""Phase 7 — memory moderation state machine and serializer privacy."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.phase7.helpers import login, png_bytes, seed_fan_with_ticket, seed_memory_event


def test_host_hide_fan_photo(client: TestClient, db_session: Session):
    _, host_user, event = seed_memory_event(db_session)
    fan, _ = seed_fan_with_ticket(db_session, event)
    fan_h = login(client, fan.email)
    host_h = login(client, host_user.email)
    up = client.post(
        f"/api/v1/memories/events/{event.id}/photos",
        headers=fan_h,
        files={"file": ("m.png", png_bytes(), "image/png")},
    )
    assert up.status_code == 200
    media_id = up.json()["community_media"][0]["id"]
    hidden = client.post(
        f"/api/v1/memories/host/events/{event.id}/photos/{media_id}/moderate",
        headers=host_h,
        json={"action": "hide"},
    )
    assert hidden.status_code == 200
    public = client.get(f"/api/v1/memories/events/{event.slug}")
    assert all(m["id"] != media_id for m in public.json()["community_media"])


def test_public_serializer_omits_storage_key(client: TestClient, db_session: Session):
    _, host_user, event = seed_memory_event(db_session)
    host_h = login(client, host_user.email)
    up = client.post(
        f"/api/v1/memories/host/events/{event.id}/photos",
        headers=host_h,
        files={"file": ("h.png", png_bytes(), "image/png")},
    )
    assert up.status_code == 200
    public = client.get(f"/api/v1/memories/events/{event.slug}")
    for photo in public.json().get("host_media", []):
        assert photo.get("storage_key") is None


def test_fan_delete_soft_removes_from_public(client: TestClient, db_session: Session):
    _, _, event = seed_memory_event(db_session)
    fan, _ = seed_fan_with_ticket(db_session, event)
    fan_h = login(client, fan.email)
    up = client.post(
        f"/api/v1/memories/events/{event.id}/photos",
        headers=fan_h,
        files={"file": ("d.png", png_bytes(), "image/png")},
    )
    media_id = up.json()["community_media"][0]["id"]
    deleted = client.delete(
        f"/api/v1/memories/events/{event.id}/photos/{media_id}",
        headers=fan_h,
    )
    assert deleted.status_code == 200
    public = client.get(f"/api/v1/memories/events/{event.slug}")
    assert all(m["id"] != media_id for m in public.json()["community_media"])
