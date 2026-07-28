"""Phase 6.5 — event cancel vs late payment (no usable tickets)."""

from __future__ import annotations

from unittest.mock import patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.payments.models import Order, Payment
from app.payments.webhook import finalize_successful_payment
from app.tickets.models import Ticket
from tests.helpers.phase4_payments import expected_kobo
from tests.phase65.helpers import create_user, login, pending_order, seed_published_event


def test_cancelled_event_blocks_ticket_issuance_on_webhook(
    client: TestClient, db_session: Session
):
    event, tt, host_user, _ = seed_published_event(db_session, qty=5, capacity=5)
    buyer = create_user(db_session, "p65-cancel-buyer@example.com")
    headers = login(client, buyer.email)
    body = pending_order(
        client,
        headers,
        event_id=event.id,
        ticket_type_id=tt.id,
        buyer_email=buyer.email,
    )
    order_id = UUID(str(body["id"]))
    host_headers = login(client, host_user.email)
    cancel = client.post(
        f"/api/v1/events/by-id/{event.id}/cancel",
        headers=host_headers,
    )
    assert cancel.status_code == 200, cancel.text

    db_session.expire_all()
    order = db_session.get(Order, order_id)
    assert order is not None
    assert order.status == "cancelled"

    payment = db_session.scalar(select(Payment).where(Payment.order_id == order_id))
    if payment is None:
        payment = Payment(
            order_id=order_id,
            provider="paystack",
            reference=body["reference"],
            amount=order.total_amount,
            currency=order.currency,
            status="pending",
        )
        db_session.add(payment)
        db_session.commit()

    finalize_successful_payment(
        db_session,
        order=order,
        payment=payment,
        provider_payment_id="p65-cancel",
        raw_payload={"event": "charge.success"},
        actor_user_id=buyer.id,
    )
    db_session.commit()
    db_session.expire_all()

    order = db_session.get(Order, order_id)
    db_session.refresh(tt)
    tickets = list(db_session.scalars(select(Ticket).where(Ticket.order_id == order_id)))
    payment = db_session.scalar(select(Payment).where(Payment.order_id == order_id))

    assert order is not None
    assert order.status == "payment_received"
    assert payment is not None
    assert payment.status == "successful"
    assert len(tickets) == 0
    assert tt.quantity_reserved == 0
    assert tt.quantity_sold == 0


def test_cancelled_event_confirm_matches_webhook_policy(
    client: TestClient, db_session: Session
):
    event, tt, host_user, _ = seed_published_event(db_session, qty=3)
    buyer = create_user(db_session, "p65-confirm-buyer@example.com")
    headers = login(client, buyer.email)
    body = pending_order(
        client,
        headers,
        event_id=event.id,
        ticket_type_id=tt.id,
        buyer_email=buyer.email,
    )
    order_id = UUID(str(body["id"]))
    host_headers = login(client, host_user.email)
    assert (
        client.post(f"/api/v1/events/by-id/{event.id}/cancel", headers=host_headers).status_code
        == 200
    )

    charge = {
        "id": 42,
        "reference": body["reference"],
        "amount": expected_kobo(body["total_amount"]),
        "currency": "NGN",
        "status": "success",
    }
    with patch("app.payments.service.verify_transaction", return_value=charge):
        confirm = client.post(
            f"/api/v1/payments/checkout/{order_id}/confirm", headers=headers
        )
    assert confirm.status_code == 200, confirm.text
    assert confirm.json()["status"] == "payment_received"
    db_session.expire_all()
    assert (
        len(list(db_session.scalars(select(Ticket).where(Ticket.order_id == order_id))))
        == 0
    )
