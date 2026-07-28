"""Phase 4.5 — transactional atomicity via injected pre-commit failures."""

from __future__ import annotations

import os
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.payments.models import Order
from app.tickets.models import Ticket
from tests.phase45.helpers import (
    create_buyer,
    login,
    pending_order,
    seed_event,
    signed_charge_body,
)

pytestmark = pytest.mark.skipif(
    os.environ.get("PHASE45_POSTGRES") != "1",
    reason="Phase 4.5 Postgres concurrency — set PHASE45_POSTGRES=1",
)


def test_atomicity_failure_before_commit_rolls_back_then_retry_succeeds(
    client: TestClient, db_session: Session
):
    """Inject failure during finalize; order stays pending; retry succeeds once."""
    event, tt = seed_event(db_session, price="1000.00", qty=5)
    email = f"atom-{uuid4().hex[:8]}@example.com"
    create_buyer(db_session, email)
    headers = login(client, email)
    order = pending_order(
        client,
        headers,
        event_id=str(event.id),
        ticket_type_id=str(tt.id),
    )
    body, sig = signed_charge_body(order)
    wh = {"x-paystack-signature": sig, "content-type": "application/json"}

    def boom(db, order_obj):
        raise RuntimeError("PHASE45_INJECTED_FAILURE_DURING_TICKET_ISSUANCE")

    with patch(
        "app.payments.webhook.issue_tickets_for_paid_order",
        side_effect=boom,
    ):
        res = client.post(
            "/api/v1/payments/webhooks/paystack", content=body, headers=wh
        )
    assert res.status_code in {400, 500}
    db_session.commit()
    db_session.expire_all()
    row = db_session.get(Order, UUID(order["id"]))
    assert row is not None
    tickets = list(
        db_session.scalars(select(Ticket).where(Ticket.order_id == UUID(order["id"])))
    )
    # API45-P1-001: pre-commit failure must roll back — never paid without tickets
    assert row.status == "pending"
    assert tickets == []

    # Retry without injection — new provider event id; exactly-once success
    body2, sig2 = signed_charge_body(order)
    wh2 = {"x-paystack-signature": sig2, "content-type": "application/json"}
    ok = client.post(
        "/api/v1/payments/webhooks/paystack", content=body2, headers=wh2
    )
    assert ok.status_code == 200, ok.text
    assert ok.json().get("status") == "ok", ok.text
    db_session.commit()
    db_session.expire_all()
    row2 = db_session.get(Order, UUID(order["id"]))
    assert row2 is not None
    assert row2.status == "paid", (row2.status, ok.text)
    tickets2 = list(
        db_session.scalars(select(Ticket).where(Ticket.order_id == UUID(order["id"])))
    )
    assert len(tickets2) == 1


def test_post_commit_notification_failure_keeps_paid(
    client: TestClient, db_session: Session
):
    event, tt = seed_event(db_session, price="1000.00", qty=5)
    email = f"postc-{uuid4().hex[:8]}@example.com"
    create_buyer(db_session, email)
    headers = login(client, email)
    order = pending_order(
        client,
        headers,
        event_id=str(event.id),
        ticket_type_id=str(tt.id),
    )
    body, sig = signed_charge_body(order)
    wh = {"x-paystack-signature": sig, "content-type": "application/json"}

    with patch(
        "app.payments.webhook.send_ticket_email",
        side_effect=RuntimeError("email down"),
    ):
        res = client.post(
            "/api/v1/payments/webhooks/paystack", content=body, headers=wh
        )
    assert res.status_code == 200, res.text
    db_session.commit()
    db_session.expire_all()
    row = db_session.get(Order, UUID(order["id"]))
    assert row.status == "paid"
    tickets = list(
        db_session.scalars(select(Ticket).where(Ticket.order_id == UUID(order["id"])))
    )
    assert len(tickets) == 1
