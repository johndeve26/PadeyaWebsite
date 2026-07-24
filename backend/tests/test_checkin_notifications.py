"""Check-in success → ticket.checked_in in-app + push."""

from __future__ import annotations

import re

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.email.prefs import get_or_create_preferences
from app.messaging.models import InAppNotification
from app.notifications.settings_service import update_push_settings
from app.push.models import PushEvent
from app.users.models import User
from tests.test_checkins import _host_headers, _seed_event_with_ticket


def _enable_push(db: Session) -> None:
    update_push_settings(
        db,
        updates={
            "push_enabled": True,
            "provider": "log",
            "generate_vapid_keys": True,
            "vapid_subject": "mailto:support@padeya.com",
        },
        actor_user_id=None,
        commit=True,
    )


def _scan(client: TestClient, event_id: str, qr: str, session_id: str | None = None):
    headers = _host_headers(client)
    body: dict = {"event_id": event_id, "qr_payload": qr}
    if session_id:
        body["session_id"] = session_id
    return client.post("/api/v1/checkins/scan", headers=headers, json=body)


def test_qr_check_in_triggers_checked_in_notification(
    client: TestClient, db_session: Session
):
    event, _, _, ticket, qr = _seed_event_with_ticket(db_session)
    _enable_push(db_session)
    buyer = db_session.get(User, ticket.buyer_user_id)
    assert buyer is not None
    prefs = get_or_create_preferences(db_session, buyer.id)
    prefs.push_enabled = True
    prefs.push_ticket_updates = True
    db_session.commit()

    res = _scan(client, str(event.id), qr)
    assert res.status_code == 200
    assert res.json()["outcome"] == "success"

    in_app = db_session.scalar(
        select(InAppNotification).where(
            InAppNotification.user_id == buyer.id,
            InAppNotification.kind == "ticket.checked_in",
            InAppNotification.dedupe_key == f"ticket:{ticket.id}:checked_in",
        )
    )
    assert in_app is not None
    assert in_app.title == "You're checked in"
    assert "Gate Night" in in_app.body

    push_row = db_session.scalar(
        select(PushEvent).where(
            PushEvent.dedupe_key == f"push:ticket:{ticket.id}:checked_in"
        )
    )
    assert push_row is not None
    assert push_row.template == "ticket_checked_in"
    assert "qr" not in (push_row.body or "").lower()
    assert not re.search(r"PDY-|paystack|order", push_row.body or "", re.I)


def test_duplicate_scan_does_not_duplicate_notification(
    client: TestClient, db_session: Session
):
    event, _, _, ticket, qr = _seed_event_with_ticket(db_session)
    _enable_push(db_session)
    buyer_id = ticket.buyer_user_id
    assert buyer_id is not None
    prefs = get_or_create_preferences(db_session, buyer_id)
    prefs.push_enabled = True
    prefs.push_ticket_updates = True
    db_session.commit()

    assert _scan(client, str(event.id), qr).json()["outcome"] == "success"
    assert _scan(client, str(event.id), qr).json()["outcome"] == "duplicate"

    rows = list(
        db_session.scalars(
            select(InAppNotification).where(
                InAppNotification.user_id == buyer_id,
                InAppNotification.kind == "ticket.checked_in",
            )
        )
    )
    assert len(rows) == 1


def test_guest_ticket_without_user_skips_notification(
    client: TestClient, db_session: Session
):
    event, _, _, ticket, qr = _seed_event_with_ticket(db_session)
    ticket.buyer_user_id = None
    db_session.commit()
    _enable_push(db_session)

    res = _scan(client, str(event.id), qr)
    assert res.json()["outcome"] == "success"

    rows = list(
        db_session.scalars(
            select(InAppNotification).where(
                InAppNotification.kind == "ticket.checked_in",
            )
        )
    )
    assert len(rows) == 0


def test_manual_public_code_check_in_notifies(
    client: TestClient, db_session: Session
):
    event, _, _, ticket, _ = _seed_event_with_ticket(db_session)
    _enable_push(db_session)
    buyer_id = ticket.buyer_user_id
    assert buyer_id is not None
    prefs = get_or_create_preferences(db_session, buyer_id)
    prefs.push_enabled = True
    prefs.push_ticket_updates = True
    db_session.commit()

    headers = _host_headers(client)
    res = client.post(
        "/api/v1/checkins/scan",
        headers=headers,
        json={
            "event_id": str(event.id),
            "public_code": ticket.public_code,
        },
    )
    assert res.status_code == 200
    assert res.json()["outcome"] == "success"

    row = db_session.scalar(
        select(InAppNotification).where(
            InAppNotification.dedupe_key == f"ticket:{ticket.id}:checked_in"
        )
    )
    assert row is not None


def test_user_push_opt_out_skips_push_but_in_app_works(
    client: TestClient, db_session: Session
):
    event, _, _, ticket, qr = _seed_event_with_ticket(db_session)
    _enable_push(db_session)
    buyer_id = ticket.buyer_user_id
    assert buyer_id is not None
    prefs = get_or_create_preferences(db_session, buyer_id)
    prefs.push_enabled = True
    prefs.push_ticket_updates = False
    db_session.commit()

    assert _scan(client, str(event.id), qr).json()["outcome"] == "success"

    in_app = db_session.scalar(
        select(InAppNotification).where(
            InAppNotification.dedupe_key == f"ticket:{ticket.id}:checked_in"
        )
    )
    assert in_app is not None

    push_row = db_session.scalar(
        select(PushEvent).where(
            PushEvent.dedupe_key == f"push:ticket:{ticket.id}:checked_in"
        )
    )
    assert push_row is not None
    assert push_row.status == "skipped"
    assert push_row.error_message == "pref_push_ticket_updates_off"


def test_admin_type_push_off_skips_push_enqueue(
    client: TestClient, db_session: Session, assign_role
):
    from app.admin_notifications.settings_service import update_setting

    event, _, host_user, ticket, qr = _seed_event_with_ticket(db_session)
    _enable_push(db_session)
    buyer_id = ticket.buyer_user_id
    assert buyer_id is not None
    prefs = get_or_create_preferences(db_session, buyer_id)
    prefs.push_enabled = True
    prefs.push_ticket_updates = True
    db_session.commit()

    assign_role(host_user.email, "super_admin")
    update_setting(
        db_session,
        type_key="checkin.successful",
        updates={"channels": {"push": False}},
        actor_user_id=host_user.id,
        actor_is_super_admin=True,
    )
    db_session.commit()

    assert _scan(client, str(event.id), qr).json()["outcome"] == "success"

    in_app = db_session.scalar(
        select(InAppNotification).where(
            InAppNotification.dedupe_key == f"ticket:{ticket.id}:checked_in"
        )
    )
    assert in_app is not None

    push_row = db_session.scalar(
        select(PushEvent).where(
            PushEvent.dedupe_key == f"push:ticket:{ticket.id}:checked_in"
        )
    )
    assert push_row is None
