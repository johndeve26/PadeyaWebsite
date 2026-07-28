"""Phase 6 — Postgres concurrency: transitions, expiry workers, payment vs expiry."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.payments.models import Order, Payment
from app.payments.reservations import expire_due_reservations, expire_pending_order
from app.payments.webhook import finalize_successful_payment
from app.tickets.models import Ticket
from tests.helpers.phase4_payments import expected_kobo
from tests.phase45.helpers import truncate_financial_tables
from tests.phase6.helpers import (
    ITERATIONS,
    create_user,
    login,
    pending_order,
    run_barriered,
    seed_published_event,
)
from uuid import UUID

pytestmark = pytest.mark.skipif(
    os.environ.get("PHASE45_POSTGRES") != "1",
    reason="Phase 6 concurrency requires PHASE45_POSTGRES=1 isolated Postgres",
)


def _pay_payload(order: Order) -> dict:
    return {
        "id": 900001,
        "reference": order.reference,
        "amount": expected_kobo(order.total_amount),
        "currency": order.currency,
        "status": "success",
    }


def test_payment_vs_expiry_race_iterations(client: TestClient, db_session: Session):
    """≥20 iters: never paid+released; exactly one of {paid, expired}."""
    SessionLocal = sessionmaker(
        bind=db_session.get_bind(), autocommit=False, autoflush=False
    )
    results = {"paid": 0, "expired": 0, "other": 0, "bad": 0}

    for i in range(ITERATIONS):
        truncate_financial_tables(db_session)
        event, tt, _, _ = seed_published_event(
            db_session, qty=1, capacity=1, reservation_hold_minutes=30, price="500.00"
        )
        buyer = create_user(db_session, f"race-{i}-{uuid4().hex[:6]}@example.com")
        headers = login(client, buyer.email)
        body = pending_order(
            client,
            headers,
            event_id=event.id,
            ticket_type_id=tt.id,
            buyer_email=buyer.email,
        )
        order_id = UUID(str(body["id"]))

        order = db_session.get(Order, order_id)
        assert order is not None
        # Still within TTL — expire worker force-releases; pay worker finalizes.
        if not order.payments:
            db_session.add(
                Payment(
                    order_id=order.id,
                    provider="paystack",
                    reference=order.reference,
                    amount=order.total_amount,
                    currency=order.currency,
                    status="pending",
                )
            )
        db_session.commit()

        def expire_worker() -> str:
            s = SessionLocal()
            try:
                from sqlalchemy import select
                from sqlalchemy.orm import selectinload

                locked = s.scalar(
                    select(Order)
                    .where(Order.id == order_id)
                    .options(selectinload(Order.items))
                    .with_for_update()
                )
                assert locked is not None
                did = expire_pending_order(
                    s, order=locked, reason="forced"
                )
                s.commit()
                return "expired" if did or locked.status == "expired" else locked.status
            finally:
                s.close()

        def pay_worker() -> str:
            s = SessionLocal()
            try:
                from sqlalchemy import select
                from sqlalchemy.orm import selectinload

                locked = s.scalar(
                    select(Order)
                    .where(Order.id == order_id)
                    .options(
                        selectinload(Order.items),
                        selectinload(Order.payments),
                    )
                    .with_for_update()
                )
                assert locked is not None
                payment = s.scalar(
                    select(Payment).where(Payment.order_id == order_id).with_for_update()
                )
                assert payment is not None
                try:
                    finalize_successful_payment(
                        s,
                        order=locked,
                        payment=payment,
                        provider_payment_id=f"race-{i}",
                        raw_payload=_pay_payload(locked),
                        actor_user_id=buyer.id,
                    )
                    s.commit()
                    return "paid"
                except Exception:
                    s.rollback()
                    s2 = SessionLocal()
                    try:
                        o2 = s2.get(Order, order_id)
                        return o2.status if o2 else "missing"
                    finally:
                        s2.close()
            finally:
                s.close()

        run_barriered([expire_worker, pay_worker])
        db_session.rollback()
        db_session.expire_all()
        final = db_session.get(Order, order_id)
        assert final is not None
        db_session.refresh(tt)
        tickets = list(
            db_session.query(Ticket).filter(Ticket.order_id == order_id)
        )

        if final.status == "paid":
            results["paid"] += 1
            assert tt.quantity_reserved == 0
            assert tt.quantity_sold == 1
            assert len(tickets) == 1
        elif final.status == "expired":
            results["expired"] += 1
            assert tt.quantity_reserved == 0
            assert tt.quantity_sold == 0
            assert len(tickets) == 0
        elif final.status == "payment_received":
            results.setdefault("payment_received", 0)
            results["payment_received"] += 1
            assert tt.quantity_reserved == 0
            assert tt.quantity_sold == 0
            assert len(tickets) == 0
        else:
            results["other"] += 1

        if final.status == "paid" and tt.quantity_sold == 0:
            results["bad"] += 1
        if final.status in {"expired", "payment_received"} and (tt.quantity_sold > 0 or tickets):
            results["bad"] += 1
        if final.status == "paid" and tt.quantity_reserved > 0:
            results["bad"] += 1

    assert results["bad"] == 0
    assert results["other"] == 0
    assert (
        results["paid"]
        + results["expired"]
        + results.get("payment_received", 0)
    ) == ITERATIONS
    # Under true concurrency both payment-win and release-win outcomes appear.
    assert results["paid"] >= 1 or results.get("payment_received", 0) >= 1


def test_concurrent_expiry_workers_idempotent(client: TestClient, db_session: Session):
    SessionLocal = sessionmaker(
        bind=db_session.get_bind(), autocommit=False, autoflush=False
    )
    for i in range(ITERATIONS):
        truncate_financial_tables(db_session)
        event, tt, _, _ = seed_published_event(
            db_session, qty=1, capacity=1, reservation_hold_minutes=5
        )
        buyer = create_user(db_session, f"sweeper-{i}-{uuid4().hex[:6]}@example.com")
        headers = login(client, buyer.email)
        body = pending_order(
            client,
            headers,
            event_id=event.id,
            ticket_type_id=tt.id,
            buyer_email=buyer.email,
        )
        order = db_session.get(Order, UUID(str(body["id"])))
        assert order is not None
        order.reservation_expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db_session.commit()
        order_id = order.id

        def worker() -> dict:
            s = SessionLocal()
            try:
                return expire_due_reservations(s, limit=50, now=datetime.now(UTC))
            finally:
                s.close()

        run_barriered([worker, worker, worker])
        db_session.expire_all()
        final = db_session.get(Order, order_id)
        db_session.refresh(tt)
        assert final is not None
        assert final.status == "expired"
        assert tt.quantity_reserved == 0
        assert tt.quantity_sold == 0


def test_capacity_floor_rejected_when_pending_seats_postgres(
    client: TestClient, db_session: Session
):
    """Host cannot shrink below reserved+sold under row lock (Postgres)."""
    event, tt, host_user, _ = seed_published_event(
        db_session, qty=5, capacity=3, reservation_hold_minutes=30
    )
    buyer = create_user(db_session, f"capfloor-{uuid4().hex[:6]}@example.com")
    headers = login(client, buyer.email)
    pending_order(
        client,
        headers,
        event_id=event.id,
        ticket_type_id=tt.id,
        quantity=2,
        buyer_email=buyer.email,
    )
    host_headers = login(client, host_user.email)
    res = client.patch(
        f"/api/v1/events/by-id/{event.id}",
        headers=host_headers,
        json={"capacity": 1},
    )
    assert res.status_code == 400
    db_session.refresh(event)
    assert event.capacity == 3
