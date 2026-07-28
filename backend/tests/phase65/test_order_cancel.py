"""Phase 6.5 — buyer pending-order cancellation."""

from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.payments.models import Order
from tests.phase65.helpers import create_user, login, pending_order, seed_published_event


def test_buyer_cancel_pending_order_releases_inventory(
    client: TestClient, db_session: Session
):
    event, tt, _, _ = seed_published_event(db_session, qty=4, capacity=4)
    buyer = create_user(db_session, "p65-oc-buyer@example.com")
    other = create_user(db_session, "p65-oc-other@example.com")
    headers = login(client, buyer.email)
    body = pending_order(
        client,
        headers,
        event_id=event.id,
        ticket_type_id=tt.id,
        quantity=2,
        buyer_email=buyer.email,
    )
    order_id = UUID(str(body["id"]))
    db_session.refresh(tt)
    assert tt.quantity_reserved == 2

    res = client.post(f"/api/v1/orders/{order_id}/cancel", headers=headers)
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "cancelled"

    again = client.post(f"/api/v1/orders/{order_id}/cancel", headers=headers)
    assert again.status_code == 200
    assert again.json()["status"] == "cancelled"

    db_session.refresh(tt)
    assert tt.quantity_reserved == 0

    forbidden = client.post(
        f"/api/v1/orders/{order_id}/cancel",
        headers=login(client, other.email),
    )
    assert forbidden.status_code == 404


def test_cancelled_order_late_webhook_records_payment_not_tickets(
    client: TestClient, db_session: Session
):
    from sqlalchemy import select

    from app.payments.models import Payment
    from app.payments.webhook import finalize_successful_payment
    from app.tickets.models import Ticket

    event, tt, _, _ = seed_published_event(db_session, qty=2)
    buyer = create_user(db_session, "p65-late-oc@example.com")
    headers = login(client, buyer.email)
    body = pending_order(
        client,
        headers,
        event_id=event.id,
        ticket_type_id=tt.id,
        buyer_email=buyer.email,
    )
    order_id = UUID(str(body["id"]))
    assert (
        client.post(f"/api/v1/orders/{order_id}/cancel", headers=headers).status_code
        == 200
    )
    order = db_session.get(Order, order_id)
    assert order is not None
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
        provider_payment_id="p65-oc-late",
        raw_payload={"event": "charge.success"},
        actor_user_id=buyer.id,
    )
    db_session.commit()
    db_session.expire_all()
    order = db_session.get(Order, order_id)
    payment = db_session.scalar(select(Payment).where(Payment.order_id == order_id))
    tickets = list(db_session.scalars(select(Ticket).where(Ticket.order_id == order_id)))
    assert order.status == "payment_received"
    assert payment.status == "successful"
    assert len(tickets) == 0
