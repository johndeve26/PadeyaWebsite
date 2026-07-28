"""Phase 5 — offline sync conflicts, group tickets, capacity non-consumption."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.audit import AuditLog
from app.events.models import TicketType
from app.tickets.advanced_models import TicketGroup, TicketGroupMember
from tests.phase5.helpers import host_headers, login, scan, seed_event_with_ticket


def test_offline_valid_then_duplicate_conflict(client: TestClient, db_session: Session):
    event, _h, host_user, _b, ticket, qr = seed_event_with_ticket(db_session)
    headers = host_headers(client, host_user.email)
    batch_id = f"batch-{uuid4().hex}"
    first = client.post(
        "/api/v1/checkins/offline/sync",
        headers=headers,
        json={
            "event_id": str(event.id),
            "client_batch_id": batch_id,
            "device_label": "Offline Gate",
            "scans": [
                {
                    "client_scan_id": "s1",
                    "qr_payload": qr,
                    "scanned_at": datetime.now(UTC).isoformat(),
                }
            ],
        },
    )
    assert first.status_code == 200, first.text
    assert first.json()["accepted_count"] == 1
    db_session.refresh(ticket)
    assert ticket.status == "checked_in"

    # Same batch idempotent replay
    replay = client.post(
        "/api/v1/checkins/offline/sync",
        headers=headers,
        json={
            "event_id": str(event.id),
            "client_batch_id": batch_id,
            "device_label": "Offline Gate",
            "scans": [
                {
                    "client_scan_id": "s1",
                    "qr_payload": qr,
                    "scanned_at": datetime.now(UTC).isoformat(),
                }
            ],
        },
    )
    assert replay.status_code == 200
    assert replay.json()["accepted_count"] == 1

    # Cross-device / second batch → conflict
    second = client.post(
        "/api/v1/checkins/offline/sync",
        headers=headers,
        json={
            "event_id": str(event.id),
            "client_batch_id": f"batch2-{uuid4().hex}",
            "device_label": "Offline Gate 2",
            "scans": [
                {
                    "client_scan_id": "s2",
                    "qr_payload": qr,
                    "scanned_at": datetime.now(UTC).isoformat(),
                }
            ],
        },
    )
    assert second.status_code == 200
    body = second.json()
    assert body["conflict_count"] == 1
    assert body["accepted_count"] == 0
    assert body["results"][0]["sync_status"] == "conflict"


def test_online_then_offline_conflict(client: TestClient, db_session: Session):
    event, _h, host_user, _b, ticket, qr = seed_event_with_ticket(db_session)
    headers = host_headers(client, host_user.email)
    online = scan(client, headers, event_id=event.id, qr_payload=qr)
    assert online["outcome"] == "success"
    offline = client.post(
        "/api/v1/checkins/offline/sync",
        headers=headers,
        json={
            "event_id": str(event.id),
            "client_batch_id": f"ol-{uuid4().hex}",
            "scans": [
                {
                    "client_scan_id": "x1",
                    "qr_payload": qr,
                    "scanned_at": datetime.now(UTC).isoformat(),
                }
            ],
        },
    )
    assert offline.status_code == 200
    assert offline.json()["conflict_count"] == 1


def test_offline_refunded_invalid(client: TestClient, db_session: Session):
    event, _h, host_user, _b, ticket, qr = seed_event_with_ticket(
        db_session, ticket_status="refunded", slug=f"p5-off-ref-{uuid4().hex[:6]}"
    )
    headers = host_headers(client, host_user.email)
    res = client.post(
        "/api/v1/checkins/offline/sync",
        headers=headers,
        json={
            "event_id": str(event.id),
            "client_batch_id": f"ref-{uuid4().hex}",
            "scans": [
                {
                    "client_scan_id": "r1",
                    "qr_payload": qr,
                    "scanned_at": datetime.now(UTC).isoformat(),
                }
            ],
        },
    )
    assert res.status_code == 200
    assert res.json()["invalid_count"] == 1
    db_session.refresh(ticket)
    assert ticket.status == "refunded"


def test_unauthorized_offline_sync(client: TestClient, db_session: Session):
    event, _h, _hu, buyer, _t, qr = seed_event_with_ticket(db_session)
    buyer_h = login(client, buyer.email)
    res = client.post(
        "/api/v1/checkins/offline/sync",
        headers=buyer_h,
        json={
            "event_id": str(event.id),
            "client_batch_id": f"bad-{uuid4().hex}",
            "scans": [
                {
                    "client_scan_id": "b1",
                    "qr_payload": qr,
                    "scanned_at": datetime.now(UTC).isoformat(),
                }
            ],
        },
    )
    assert res.status_code == 403


def test_checkin_does_not_consume_inventory(client: TestClient, db_session: Session):
    event, _h, host_user, _b, ticket, qr = seed_event_with_ticket(db_session)
    tt = db_session.get(TicketType, ticket.ticket_type_id)
    assert tt is not None
    sold_before = tt.quantity_sold
    reserved_before = tt.quantity_reserved
    capacity_before = event.capacity
    headers = host_headers(client, host_user.email)
    body = scan(client, headers, event_id=event.id, qr_payload=qr)
    assert body["outcome"] == "success"
    db_session.refresh(tt)
    db_session.refresh(event)
    assert tt.quantity_sold == sold_before
    assert tt.quantity_reserved == reserved_before
    assert event.capacity == capacity_before


def test_group_ticket_member_check_in(client: TestClient, db_session: Session):
    """Each issued ticket admits once — group membership does not multiply scans."""
    event, _h, host_user, buyer, ticket, qr = seed_event_with_ticket(db_session)
    group = TicketGroup(
        order_id=ticket.order_id,
        order_item_id=ticket.order_item_id,
        event_id=event.id,
        ticket_type_id=ticket.ticket_type_id,
        buyer_user_id=buyer.id,
        group_kind="group",
        expected_size=4,
        label="Friends",
        status="active",
    )
    db_session.add(group)
    db_session.flush()
    db_session.add(
        TicketGroupMember(
            group_id=group.id,
            ticket_id=ticket.id,
            attendee_index=0,
        )
    )
    db_session.commit()
    headers = host_headers(client, host_user.email)
    body = scan(client, headers, event_id=event.id, qr_payload=qr)
    assert body["outcome"] == "success"
    # Second scan still duplicate — one admission per ticket seat
    body2 = scan(client, headers, event_id=event.id, qr_payload=qr)
    assert body2["outcome"] == "duplicate"


def test_checkin_writes_audit_log(client: TestClient, db_session: Session):
    event, _h, host_user, _b, ticket, qr = seed_event_with_ticket(db_session)
    headers = host_headers(client, host_user.email)
    scan(client, headers, event_id=event.id, qr_payload=qr)
    logs = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "checkins.success")
        .all()
    )
    assert any(str(ticket.id) == (l.resource_id or "") for l in logs)


def test_scan_response_privacy_no_buyer_email(client: TestClient, db_session: Session):
    event, _h, host_user, buyer, _t, qr = seed_event_with_ticket(db_session)
    headers = host_headers(client, host_user.email)
    body = scan(client, headers, event_id=event.id, qr_payload=qr)
    blob = str(body)
    assert buyer.email not in blob
    assert body["ticket"]["holder_email"] is None
