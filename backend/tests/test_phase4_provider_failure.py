"""Phase 4 — provider failure / timeout leave recoverable pending state."""

from __future__ import annotations

from unittest.mock import patch
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.payments.models import Order
from app.payments.paystack import PaystackError
from app.tickets.models import Ticket
from tests.helpers.phase4_payments import (
    create_pending_order,
    register_and_login,
    seed_published_event,
)


def test_initialize_timeout_leaves_order_pending_no_tickets(
    client: TestClient, db_session: Session
):
    event, ticket_type = seed_published_event(db_session, price="1000.00")
    headers = register_and_login(client, f"to-init-{uuid4().hex[:8]}@example.com")
    order = client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "event_id": str(event.id),
            "items": [{"ticket_type_id": str(ticket_type.id), "quantity": 1}],
        },
    )
    assert order.status_code == 201, order.text
    body = order.json()

    with patch(
        "app.payments.service.initialize_transaction",
        side_effect=PaystackError("timeout", status_code=504),
    ):
        res = client.post(f"/api/v1/payments/checkout/{body['id']}", headers=headers)
    assert res.status_code in {400, 502, 503, 504}
    assert db_session.get(Order, UUID(body["id"])).status == "pending"
    assert list(
        db_session.scalars(select(Ticket).where(Ticket.order_id == UUID(body["id"])))
    ) == []


def test_confirm_provider_500_leaves_pending_no_tickets(
    client: TestClient, db_session: Session
):
    event, ticket_type = seed_published_event(db_session, price="1000.00")
    headers = register_and_login(client, f"to-conf-{uuid4().hex[:8]}@example.com")
    order = create_pending_order(
        client,
        headers,
        event_id=str(event.id),
        ticket_type_id=str(ticket_type.id),
    )
    with patch(
        "app.payments.service.verify_transaction",
        side_effect=PaystackError("upstream 500", status_code=500),
    ):
        res = client.post(
            f"/api/v1/payments/checkout/{order['id']}/confirm",
            headers=headers,
        )
    assert res.status_code in {400, 502, 503, 504, 409}
    assert db_session.get(Order, UUID(order["id"])).status == "pending"
    assert list(
        db_session.scalars(select(Ticket).where(Ticket.order_id == UUID(order["id"])))
    ) == []


def test_confirm_malformed_provider_payload_no_tickets(
    client: TestClient, db_session: Session
):
    event, ticket_type = seed_published_event(db_session, price="1000.00")
    headers = register_and_login(client, f"bad-pay-{uuid4().hex[:8]}@example.com")
    order = create_pending_order(
        client,
        headers,
        event_id=str(event.id),
        ticket_type_id=str(ticket_type.id),
    )
    with patch(
        "app.payments.service.verify_transaction",
        return_value={"status": "success"},  # missing amount/reference
    ):
        res = client.post(
            f"/api/v1/payments/checkout/{order['id']}/confirm",
            headers=headers,
        )
    # Must not finalize without authoritative amount
    assert res.status_code in {400, 409, 500}
    db_session.expire_all()
    row = db_session.get(Order, UUID(order["id"]))
    assert row.status == "pending"
    assert list(
        db_session.scalars(select(Ticket).where(Ticket.order_id == UUID(order["id"])))
    ) == []
