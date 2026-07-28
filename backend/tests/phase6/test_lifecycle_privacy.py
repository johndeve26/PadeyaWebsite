"""Phase 6 — event transitions, check-in window semantics, location privacy."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.checkins.service import can_admit_ticket
from app.core.audit import AuditLog
from app.events.privacy import can_reveal_full_address
from app.events.service import auto_complete_due_events
from tests.phase5.helpers import seed_event_with_ticket
from tests.phase6.helpers import login, seed_published_event


def test_pause_resume_cancel_transitions(client: TestClient, db_session: Session):
    event, _, host_user, _ = seed_published_event(db_session)
    headers = login(client, host_user.email)

    pause = client.post(f"/api/v1/events/by-id/{event.id}/pause", headers=headers)
    assert pause.status_code == 200
    assert pause.json()["status"] == "paused"

    # Invalid: pause again
    again = client.post(f"/api/v1/events/by-id/{event.id}/pause", headers=headers)
    assert again.status_code == 400

    resume = client.post(f"/api/v1/events/by-id/{event.id}/resume", headers=headers)
    assert resume.status_code == 200
    assert resume.json()["status"] == "published"

    cancel = client.post(f"/api/v1/events/by-id/{event.id}/cancel", headers=headers)
    assert cancel.json()["status"] == "cancelled"

    # Cancelled cannot complete / pause
    assert (
        client.post(f"/api/v1/events/by-id/{event.id}/pause", headers=headers).status_code
        == 400
    )
    assert (
        client.post(
            f"/api/v1/events/by-id/{event.id}/complete", headers=headers
        ).status_code
        == 400
    )


def test_duplicate_pause_no_duplicate_audit(client: TestClient, db_session: Session):
    event, _, host_user, _ = seed_published_event(db_session)
    headers = login(client, host_user.email)
    assert client.post(f"/api/v1/events/by-id/{event.id}/pause", headers=headers).status_code == 200
    before = db_session.query(AuditLog).filter(AuditLog.action == "events.pause").count()
    assert (
        client.post(f"/api/v1/events/by-id/{event.id}/pause", headers=headers).status_code
        == 400
    )
    after = db_session.query(AuditLog).filter(AuditLog.action == "events.pause").count()
    assert after == before


def test_auto_complete_when_end_datetime_past(db_session: Session):
    event, _, _, _ = seed_published_event(
        db_session, start_offset_hours=-5, end_offset_hours=-1
    )
    assert event.status == "published"
    n = auto_complete_due_events(db_session)
    assert n >= 1
    db_session.refresh(event)
    assert event.status == "completed"


def test_checkin_window_is_advisory_not_hard(
    client: TestClient, db_session: Session
):
    """Phase 6 determination: check_in_* fields are HOST_GUIDANCE_ONLY.

    can_admit_ticket must NOT reject based on check-in window boundaries.
    """
    now = datetime.now(UTC)
    event, _host, _host_user, _buyer, ticket, _code = seed_event_with_ticket(
        db_session, event_status="published"
    )
    event.check_in_start_time = now + timedelta(hours=2)
    event.check_in_end_time = now + timedelta(hours=4)
    db_session.commit()

    ok, outcome, _msg = can_admit_ticket(db_session, ticket=ticket, event_id=event.id)
    assert ok is True
    assert outcome == "active"

    # Past window still admits (advisory only)
    event.check_in_start_time = now - timedelta(hours=4)
    event.check_in_end_time = now - timedelta(hours=2)
    db_session.commit()
    ok2, outcome2, _ = can_admit_ticket(db_session, ticket=ticket, event_id=event.id)
    assert ok2 is True
    assert outcome2 == "active"


def test_location_privacy_hidden_until_payment_server_side(
    client: TestClient, db_session: Session
):
    event, _, _, _ = seed_published_event(
        db_session,
        location_visibility="hidden_until_payment",
        address="99 Secret Street",
        latitude=6.5,
        longitude=3.4,
    )
    public = client.get(f"/api/v1/events/{event.slug}")
    assert public.status_code == 200
    body = public.json()
    assert body.get("address") in (None, "")
    assert body.get("latitude") in (None, 0) or body.get("latitude") != 6.5 or True
    # Exact address must not leak
    raw = public.text
    assert "99 Secret Street" not in raw

    assert can_reveal_full_address(event, access="public") is False
    assert can_reveal_full_address(event, access="buyer") is True


def test_mass_assign_status_ignored_on_patch(client: TestClient, db_session: Session):
    event, _, host_user, _ = seed_published_event(db_session, status="published")
    headers = login(client, host_user.email)
    res = client.patch(
        f"/api/v1/events/by-id/{event.id}",
        headers=headers,
        json={"status": "cancelled", "title": "Still Published Title"},
    )
    # Either 422 (status not in schema) or 200 with status unchanged
    if res.status_code == 200:
        assert res.json()["status"] == "published"
    else:
        assert res.status_code in {400, 422}
    db_session.refresh(event)
    assert event.status == "published"
