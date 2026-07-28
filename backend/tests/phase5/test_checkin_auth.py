"""Phase 5 — check-in auth, sessions, invalid tickets, event status."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.hosts.models import HostTeamMember
from app.hosts.team_permissions import pack_scope_json, permissions_for_role
from app.users.models import User
from app.users.service import get_role_by_name
from tests.phase5.helpers import create_user, host_headers, login, scan, seed_event_with_ticket


def test_wrong_host_cannot_check_in(client: TestClient, db_session: Session):
    event, _h, _host_user, _b, ticket, qr = seed_event_with_ticket(db_session)
    other = create_user(
        db_session,
        f"p5-other-host-{uuid4().hex[:6]}@example.com",
        role="host",
        name="Other Host",
    )
    # Onboard other host
    headers = login(client, other.email)
    onboard = client.post(
        "/api/v1/hosts/onboard",
        headers=headers,
        json={
            "display_name": "Other Host Co",
            "bio": "Another host for wrong-host check-in denial with enough text.",
            "city": "Abuja",
            "state": "FCT",
            "country": "Nigeria",
        },
    )
    assert onboard.status_code == 201, onboard.text
    res = client.post(
        "/api/v1/checkins/scan",
        headers=headers,
        json={"event_id": str(event.id), "qr_payload": qr},
    )
    assert res.status_code == 403
    db_session.refresh(ticket)
    assert ticket.status == "active"


def test_events_view_without_scan_denied(client: TestClient, db_session: Session):
    from datetime import UTC, datetime

    event, host, host_user, _b, ticket, qr = seed_event_with_ticket(db_session)
    staff = create_user(
        db_session,
        f"p5-viewonly-{uuid4().hex[:6]}@example.com",
        role="buyer",
        name="View Only",
    )
    perms = permissions_for_role("viewer")
    # Strip scan permissions; keep events.view if present
    perms["tickets.scan_qr"] = False
    perms["tickets.check_in"] = False
    perms["events.view"] = True
    db_session.add(
        HostTeamMember(
            host_id=host.id,
            user_id=staff.id,
            role="viewer",
            role_label="viewer",
            status="active",
            invited_by_user_id=host_user.id,
            permissions_json=perms,
            scope_json=pack_scope_json("host_wide", []),
            joined_at=datetime.now(UTC),
        )
    )
    db_session.commit()

    headers = login(client, staff.email)
    res = client.post(
        "/api/v1/checkins/scan",
        headers=headers,
        json={"event_id": str(event.id), "qr_payload": qr},
    )
    assert res.status_code == 403
    db_session.refresh(ticket)
    assert ticket.status == "active"


def test_scanner_session_lifecycle(client: TestClient, db_session: Session):
    event, _h, host_user, _b, _ticket, qr = seed_event_with_ticket(db_session)
    headers = host_headers(client, host_user.email)
    start = client.post(
        "/api/v1/checkins/sessions",
        headers=headers,
        json={"event_id": str(event.id), "device_label": "Gate A"},
    )
    assert start.status_code == 201
    sid = start.json()["id"]
    body = scan(client, headers, event_id=event.id, qr_payload=qr, session_id=sid)
    assert body["outcome"] == "success"
    end = client.post(f"/api/v1/checkins/sessions/{sid}/end", headers=headers)
    assert end.status_code == 200
    assert end.json()["status"] == "ended"

    # Seed a second active ticket on same event, try ended session
    event2, _h2, host2, _b2, ticket2, qr2 = seed_event_with_ticket(
        db_session,
        slug=f"p5-sess2-{uuid4().hex[:6]}",
    )
    headers2 = host_headers(client, host2.email)
    start2 = client.post(
        "/api/v1/checkins/sessions",
        headers=headers2,
        json={"event_id": str(event2.id), "device_label": "Gate B"},
    )
    sid2 = start2.json()["id"]
    client.post(f"/api/v1/checkins/sessions/{sid2}/end", headers=headers2)
    res = client.post(
        "/api/v1/checkins/scan",
        headers=headers2,
        json={
            "event_id": str(event2.id),
            "qr_payload": qr2,
            "session_id": sid2,
        },
    )
    assert res.status_code == 400
    assert "session" in res.json()["detail"].lower()
    db_session.refresh(ticket2)
    assert ticket2.status == "active"


def test_refunded_cancelled_invalid_cannot_admit(client: TestClient, db_session: Session):
    for status in ("refunded", "cancelled", "invalid", "expired", "transferred"):
        event, _h, host_user, _b, ticket, qr = seed_event_with_ticket(
            db_session,
            ticket_status=status,
            slug=f"p5-{status}-{uuid4().hex[:6]}",
            host_email=f"p5-h-{status}-{uuid4().hex[:6]}@example.com",
            buyer_email=f"p5-b-{status}-{uuid4().hex[:6]}@example.com",
        )
        headers = host_headers(client, host_user.email)
        body = scan(client, headers, event_id=event.id, qr_payload=qr)
        assert body["outcome"] == "invalid", status
        db_session.refresh(ticket)
        assert ticket.status == status


def test_cancelled_event_cannot_admit(client: TestClient, db_session: Session):
    event, _h, host_user, _b, ticket, qr = seed_event_with_ticket(
        db_session, event_status="cancelled", slug=f"p5-evcan-{uuid4().hex[:6]}"
    )
    headers = host_headers(client, host_user.email)
    body = scan(client, headers, event_id=event.id, qr_payload=qr)
    assert body["outcome"] == "invalid"
    assert "cancelled" in body["message"].lower()
    db_session.refresh(ticket)
    assert ticket.status == "active"


def test_sequential_duplicate_check_in(client: TestClient, db_session: Session):
    event, _h, host_user, _b, ticket, qr = seed_event_with_ticket(db_session)
    headers = host_headers(client, host_user.email)
    first = scan(client, headers, event_id=event.id, qr_payload=qr)
    second = scan(client, headers, event_id=event.id, qr_payload=qr)
    assert first["outcome"] == "success"
    assert second["outcome"] == "duplicate"
    db_session.refresh(ticket)
    assert ticket.status == "checked_in"


def test_desk_search_omits_holder_email(client: TestClient, db_session: Session):
    event, _h, host_user, buyer, ticket, qr = seed_event_with_ticket(db_session)
    headers = host_headers(client, host_user.email)
    body = scan(client, headers, event_id=event.id, qr_payload=qr)
    assert body["ticket"]["holder_email"] is None
    search = client.get(
        f"/api/v1/checkins/events/{event.id}/search",
        headers=headers,
        params={"q": buyer.full_name[:4]},
    )
    assert search.status_code == 200
    rows = search.json()
    assert rows
    for row in rows:
        assert "holder_email" not in row or row.get("holder_email") in (None, "")
        assert buyer.email not in str(row)


def test_override_requires_admin(client: TestClient, db_session: Session):
    event, _h, host_user, _b, ticket, _qr = seed_event_with_ticket(db_session)
    headers = host_headers(client, host_user.email)
    res = client.post(
        "/api/v1/checkins/override",
        headers=headers,
        json={
            "event_id": str(event.id),
            "ticket_id": str(ticket.id),
            "reason": "VIP walk-in",
        },
    )
    assert res.status_code == 403

    admin = User(
        email=f"p5-admin-{uuid4().hex[:6]}@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Admin",
        is_active=True,
        is_verified=True,
    )
    role = get_role_by_name(db_session, "super_admin")
    assert role is not None
    admin.roles.append(role)
    db_session.add(admin)
    db_session.commit()
    admin_headers = login(client, admin.email)
    ok = client.post(
        "/api/v1/checkins/override",
        headers=admin_headers,
        json={
            "event_id": str(event.id),
            "ticket_id": str(ticket.id),
            "reason": "VIP walk-in",
        },
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["outcome"] == "success"
    db_session.refresh(ticket)
    assert ticket.status == "checked_in"
