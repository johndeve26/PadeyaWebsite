"""Phase 7 — memory eligibility timing matrix."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.memories.constants import ELIGIBLE_EVENT_STATUSES, FAN_MEMORY_PHOTO_LIMIT
from app.memories.eligibility import event_memory_upload_window_open, fan_eligibility
from app.memories.models import EventMemory
from tests.phase7.helpers import login, png_bytes, seed_fan_with_ticket, seed_memory_event


def test_fan_eligibility_requires_ticket_and_started_event(
    client: TestClient, db_session: Session
):
    _, _, event = seed_memory_event(db_session, status="completed", started=True)
    fan, _ = seed_fan_with_ticket(db_session, event)
    memory = EventMemory(
        event_id=event.id,
        host_id=event.host_id,
        status="published",
        moderation_status="none",
    )
    db_session.add(memory)
    db_session.commit()

    elig = fan_eligibility(db_session, user=fan, event=event, memory=memory)
    assert elig["ticket_verified"] is True
    assert elig["event_started"] is True
    assert elig["can_upload"] is True
    assert elig["limit"] == FAN_MEMORY_PHOTO_LIMIT


def test_fan_before_start_blocked(client: TestClient, db_session: Session):
    _, _, event = seed_memory_event(db_session, status="published", started=False)
    fan, _ = seed_fan_with_ticket(db_session, event)
    headers = login(client, fan.email)
    resp = client.post(
        f"/api/v1/memories/events/{event.id}/photos",
        headers=headers,
        files={"file": ("x.png", png_bytes(), "image/png")},
    )
    assert resp.status_code == 400
    assert "started" in resp.json()["detail"].lower()


def test_no_ticket_forbidden(client: TestClient, db_session: Session):
    _, _, event = seed_memory_event(db_session)
    from app.core.security import hash_password
    from app.users.models import User
    from app.users.service import get_role_by_name

    stranger = User(
        email="p7-stranger@example.com",
        password_hash=hash_password("securepass1"),
        full_name="No Ticket",
        is_active=True,
    )
    stranger.roles.append(get_role_by_name(db_session, "buyer"))
    db_session.add(stranger)
    db_session.commit()
    resp = client.post(
        f"/api/v1/memories/events/{event.id}/photos",
        headers=login(client, stranger.email),
        files={"file": ("x.png", png_bytes(), "image/png")},
    )
    assert resp.status_code == 403


@pytest.mark.parametrize("status", list(ELIGIBLE_EVENT_STATUSES))
def test_upload_window_open_for_eligible_statuses(db_session: Session, status: str):
    _, _, event = seed_memory_event(db_session, status=status, started=True)
    assert event_memory_upload_window_open(event) is True


def test_cancelled_event_blocks_upload(client: TestClient, db_session: Session):
    _, _, event = seed_memory_event(db_session, status="cancelled", started=True)
    fan, _ = seed_fan_with_ticket(db_session, event)
    resp = client.post(
        f"/api/v1/memories/events/{event.id}/photos",
        headers=login(client, fan.email),
        files={"file": ("x.png", png_bytes(), "image/png")},
    )
    assert resp.status_code in {400, 403}
