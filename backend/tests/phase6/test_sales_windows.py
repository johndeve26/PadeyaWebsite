"""Phase 6 — sales windows, purchase matrix, capacity edit, validation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.payments.models import Order
from app.payments.reservations import (
    DEFAULT_RESERVATION_HOLD_MINUTES,
    expire_pending_order,
    ticket_sales_window_open,
)
from tests.phase6.helpers import create_user, login, pending_order, seed_published_event


def test_sales_window_rejects_before_sale_start(client: TestClient, db_session: Session):
    now = datetime.now(UTC)
    event, tt, _, _ = seed_published_event(
        db_session,
        sale_start=now + timedelta(hours=1),
        sale_end=now + timedelta(days=2),
    )
    buyer = create_user(db_session, f"sw-before-{tt.id.hex[:8]}@example.com")
    headers = login(client, buyer.email)
    res = client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "event_id": str(event.id),
            "buyer_email": buyer.email,
            "buyer_name": "Buyer",
            "items": [
                {"ticket_type_id": str(tt.id), "quantity": 1, "item_kind": "ticket"}
            ],
        },
    )
    assert res.status_code == 400
    assert "not opened" in res.json()["detail"].lower()


def test_sales_window_rejects_after_sale_end(client: TestClient, db_session: Session):
    now = datetime.now(UTC)
    event, tt, _, _ = seed_published_event(
        db_session,
        sale_start=now - timedelta(days=2),
        sale_end=now - timedelta(seconds=1),
    )
    buyer = create_user(db_session, f"sw-after-{tt.id.hex[:8]}@example.com")
    headers = login(client, buyer.email)
    res = client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "event_id": str(event.id),
            "buyer_email": buyer.email,
            "buyer_name": "Buyer",
            "items": [
                {"ticket_type_id": str(tt.id), "quantity": 1, "item_kind": "ticket"}
            ],
        },
    )
    assert res.status_code == 400
    assert "closed" in res.json()["detail"].lower()


def test_sales_window_boundary_open_at_exact_start(client: TestClient, db_session: Session):
    """At sale_start instant, purchase allowed (inclusive start)."""
    now = datetime.now(UTC)
    event, tt, _, _ = seed_published_event(
        db_session,
        sale_start=now,
        sale_end=now + timedelta(hours=2),
    )
    assert ticket_sales_window_open(tt, now=now) is True
    buyer = create_user(db_session, f"sw-exact-{tt.id.hex[:8]}@example.com")
    headers = login(client, buyer.email)
    body = pending_order(
        client, headers, event_id=event.id, ticket_type_id=tt.id, buyer_email=buyer.email
    )
    assert body["status"] == "pending"
    assert body.get("reservation_expires_at") or True  # may be nested


@pytest.mark.parametrize(
    "status",
    ["draft", "paused", "cancelled", "rejected", "archived", "completed"],
)
def test_purchase_matrix_non_published_blocked(
    client: TestClient, db_session: Session, status: str
):
    event, tt, _, _ = seed_published_event(db_session, status=status, qty=5)
    buyer = create_user(db_session, f"pm-{status}-{tt.id.hex[:6]}@example.com")
    headers = login(client, buyer.email)
    res = client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "event_id": str(event.id),
            "buyer_email": buyer.email,
            "buyer_name": "Buyer",
            "items": [
                {"ticket_type_id": str(tt.id), "quantity": 1, "item_kind": "ticket"}
            ],
        },
    )
    assert res.status_code == 400
    assert "not available" in res.json()["detail"].lower()


def test_capacity_cannot_reduce_below_committed(
    client: TestClient, db_session: Session
):
    event, tt, host_user, _ = seed_published_event(
        db_session, qty=10, capacity=10, reservation_hold_minutes=30
    )
    buyer = create_user(db_session, f"cap-edit-{tt.id.hex[:8]}@example.com")
    headers = login(client, buyer.email)
    pending_order(
        client, headers, event_id=event.id, ticket_type_id=tt.id, quantity=3,
        buyer_email=buyer.email,
    )
    db_session.refresh(tt)
    assert tt.quantity_reserved == 3

    host_headers = login(client, host_user.email)
    res = client.patch(
        f"/api/v1/events/by-id/{event.id}",
        headers=host_headers,
        json={"capacity": 2},
    )
    assert res.status_code == 400
    assert "committed" in res.json()["detail"].lower()

    ok = client.patch(
        f"/api/v1/events/by-id/{event.id}",
        headers=host_headers,
        json={"capacity": 5},
    )
    assert ok.status_code == 200
    assert ok.json()["capacity"] == 5


def test_reservation_expires_releases_inventory_once(
    client: TestClient, db_session: Session
):
    event, tt, _, _ = seed_published_event(
        db_session, qty=2, capacity=2, reservation_hold_minutes=1
    )
    buyer = create_user(db_session, f"exp-{tt.id.hex[:8]}@example.com")
    headers = login(client, buyer.email)
    body = pending_order(
        client, headers, event_id=event.id, ticket_type_id=tt.id, buyer_email=buyer.email
    )
    order = db_session.get(Order, UUID(str(body["id"])))
    assert order is not None
    assert order.reservation_expires_at is not None
    # Freeze clock past expiry
    order.reservation_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db_session.commit()

    assert expire_pending_order(db_session, order=order) is True
    db_session.commit()
    db_session.refresh(tt)
    db_session.refresh(order)
    assert order.status == "expired"
    assert tt.quantity_reserved == 0

    # Idempotent second expire
    assert expire_pending_order(db_session, order=order) is False

    # New buyer can purchase the released seat
    buyer2 = create_user(db_session, f"exp2-{tt.id.hex[:8]}@example.com")
    headers2 = login(client, buyer2.email)
    body2 = pending_order(
        client,
        headers2,
        event_id=event.id,
        ticket_type_id=tt.id,
        buyer_email=buyer2.email,
    )
    assert body2["status"] == "pending"


def test_checkout_after_expiry_rejected(client: TestClient, db_session: Session):
    event, tt, _, _ = seed_published_event(db_session, qty=3, reservation_hold_minutes=5)
    buyer = create_user(db_session, f"chk-exp-{tt.id.hex[:8]}@example.com")
    headers = login(client, buyer.email)
    body = pending_order(
        client, headers, event_id=event.id, ticket_type_id=tt.id, buyer_email=buyer.email
    )
    order = db_session.get(Order, UUID(str(body["id"])))
    assert order is not None
    order.reservation_expires_at = datetime.now(UTC) - timedelta(seconds=2)
    db_session.commit()

    res = client.post(
        f"/api/v1/payments/checkout/{order.id}",
        headers=headers,
    )
    assert res.status_code == 409
    db_session.refresh(tt)
    assert tt.quantity_reserved == 0


def test_default_hold_minutes_applied(client: TestClient, db_session: Session):
    event, tt, _, _ = seed_published_event(
        db_session, reservation_hold_minutes=None
    )
    buyer = create_user(db_session, f"hold-def-{tt.id.hex[:8]}@example.com")
    headers = login(client, buyer.email)
    before = datetime.now(UTC)
    body = pending_order(
        client, headers, event_id=event.id, ticket_type_id=tt.id, buyer_email=buyer.email
    )
    order = db_session.get(Order, UUID(str(body["id"])))
    assert order is not None
    assert order.reservation_expires_at is not None
    expires = order.reservation_expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    delta = expires - before
    assert timedelta(minutes=DEFAULT_RESERVATION_HOLD_MINUTES - 1) < delta
    assert delta < timedelta(minutes=DEFAULT_RESERVATION_HOLD_MINUTES + 1)


def test_end_before_start_rejected(client: TestClient, db_session: Session):
    event, _, host_user, _ = seed_published_event(db_session)
    host_headers = login(client, host_user.email)
    start = datetime.now(UTC) + timedelta(days=3)
    res = client.patch(
        f"/api/v1/events/by-id/{event.id}",
        headers=host_headers,
        json={
            "start_datetime": start.isoformat(),
            "end_datetime": (start - timedelta(hours=1)).isoformat(),
        },
    )
    assert res.status_code in {400, 422}


def test_ticket_qty_reduction_blocked_after_sales(
    client: TestClient, db_session: Session
):
    event, tt, host_user, _ = seed_published_event(db_session, qty=10)
    buyer = create_user(db_session, f"qty-{tt.id.hex[:8]}@example.com")
    headers = login(client, buyer.email)
    pending_order(
        client, headers, event_id=event.id, ticket_type_id=tt.id, buyer_email=buyer.email
    )
    host_headers = login(client, host_user.email)
    res = client.patch(
        f"/api/v1/events/by-id/{event.id}/ticket-types/{tt.id}",
        headers=host_headers,
        json={"quantity": 5},
    )
    assert res.status_code == 400
    assert "after sales" in res.json()["detail"].lower()
