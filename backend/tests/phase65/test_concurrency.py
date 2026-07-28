"""Phase 6.5 — Postgres races: event cancel vs payment, order cancel vs payment."""

from __future__ import annotations

import os
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.events.models import Event
from app.events.service import cancel_event
from app.payments.models import Order, Payment
from app.payments.reservations import cancel_pending_order, expire_pending_order
from app.payments.webhook import finalize_successful_payment, process_paystack_webhook
from app.tickets.models import Ticket
from app.users.models import User
from tests.helpers.phase4_payments import expected_kobo
from tests.phase45.helpers import truncate_financial_tables
from tests.phase65.helpers import (
    ITERATIONS,
    create_user,
    login,
    pending_order,
    run_barriered,
    seed_published_event,
)

pytestmark = pytest.mark.skipif(
    os.environ.get("PHASE45_POSTGRES") != "1",
    reason="Phase 6.5 concurrency requires PHASE45_POSTGRES=1",
)


def _pay_payload(order: Order) -> dict:
    return {
        "id": 880001,
        "reference": order.reference,
        "amount": expected_kobo(order.total_amount),
        "currency": order.currency,
        "status": "success",
    }


def test_event_cancel_vs_webhook_race_iterations(
    client: TestClient, db_session: Session
):
    SessionLocal = sessionmaker(
        bind=db_session.get_bind(), autocommit=False, autoflush=False
    )
    bad = 0
    for i in range(ITERATIONS):
        truncate_financial_tables(db_session)
        event, tt, host_user, _ = seed_published_event(
            db_session, qty=1, capacity=1, reservation_hold_minutes=30
        )
        buyer = create_user(db_session, f"p65-race-{uuid4().hex}@example.com")
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
        host_id = host_user.id
        event_id = event.id

        def cancel_worker() -> str:
            s = SessionLocal()
            try:
                host = s.get(User, host_id)
                assert host is not None
                cancel_event(s, user=host, event_id=event_id)
                s.commit()
                return "cancelled"
            except Exception as exc:  # noqa: BLE001
                s.rollback()
                return f"err:{type(exc).__name__}"
            finally:
                s.close()

        def pay_worker() -> str:
            s = SessionLocal()
            try:
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
                payment = s.scalar(
                    select(Payment).where(Payment.order_id == order_id).with_for_update()
                )
                assert locked is not None and payment is not None
                finalize_successful_payment(
                    s,
                    order=locked,
                    payment=payment,
                    provider_payment_id=f"p65-{i}",
                    raw_payload=_pay_payload(locked),
                    actor_user_id=buyer.id,
                )
                s.commit()
                return locked.status
            except Exception as exc:  # noqa: BLE001
                s.rollback()
                o2 = SessionLocal().get(Order, order_id)
                return o2.status if o2 else f"err:{type(exc).__name__}"
            finally:
                s.close()

        run_barriered([cancel_worker, pay_worker])
        verify = SessionLocal()
        try:
            final = verify.get(Order, order_id)
            tt_final = verify.get(type(tt), tt.id)
            tickets = list(
                verify.scalars(select(Ticket).where(Ticket.order_id == order_id))
            )
            if final is None or tt_final is None:
                bad += 1
                continue
            if final.status == "paid":
                if len(tickets) != 1 or tt_final.quantity_sold != 1:
                    bad += 1
            else:
                if len(tickets) != 0 or tt_final.quantity_sold != 0:
                    bad += 1
                if final.status not in {"cancelled", "payment_received"}:
                    bad += 1
        finally:
            verify.close()
    assert bad == 0


def test_order_cancel_vs_webhook_race_iterations(
    client: TestClient, db_session: Session
):
    SessionLocal = sessionmaker(
        bind=db_session.get_bind(), autocommit=False, autoflush=False
    )
    bad = 0
    for i in range(ITERATIONS):
        truncate_financial_tables(db_session)
        event, tt, _, _ = seed_published_event(db_session, qty=1, capacity=1)
        buyer = create_user(db_session, f"p65-oc-race-{uuid4().hex}@example.com")
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

        def cancel_worker() -> str:
            s = SessionLocal()
            try:
                from sqlalchemy.orm import selectinload

                locked = s.scalar(
                    select(Order)
                    .where(Order.id == order_id)
                    .options(selectinload(Order.items))
                    .with_for_update()
                )
                if locked is None:
                    return "missing"
                cancel_pending_order(s, order=locked, actor_user_id=buyer.id)
                s.commit()
                return "cancelled"
            finally:
                s.close()

        def pay_worker() -> str:
            s = SessionLocal()
            try:
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
                payment = s.scalar(
                    select(Payment).where(Payment.order_id == order_id).with_for_update()
                )
                assert locked is not None and payment is not None
                finalize_successful_payment(
                    s,
                    order=locked,
                    payment=payment,
                    provider_payment_id=f"p65oc-{i}",
                    raw_payload=_pay_payload(locked),
                    actor_user_id=buyer.id,
                )
                s.commit()
                return locked.status
            finally:
                s.close()

        run_barriered([cancel_worker, pay_worker])
        verify = SessionLocal()
        try:
            final = verify.get(Order, order_id)
            tt_final = verify.get(type(tt), tt.id)
            tickets = list(
                verify.scalars(select(Ticket).where(Ticket.order_id == order_id))
            )
            if final is None or tt_final is None:
                bad += 1
                continue
            if final.status == "paid":
                if len(tickets) != 1 or tt_final.quantity_sold != 1:
                    bad += 1
            else:
                if len(tickets) != 0 or tt_final.quantity_sold != 0:
                    bad += 1
                if final.status not in {"cancelled", "payment_received"}:
                    bad += 1
        finally:
            verify.close()
    assert bad == 0


def test_order_cancel_vs_expiry_worker_iterations(client: TestClient, db_session: Session):
    SessionLocal = sessionmaker(
        bind=db_session.get_bind(), autocommit=False, autoflush=False
    )
    bad = 0
    for i in range(ITERATIONS):
        truncate_financial_tables(db_session)
        event, tt, _, _ = seed_published_event(db_session, qty=1)
        buyer = create_user(db_session, f"p65-exp-oc-{uuid4().hex}@example.com")
        headers = login(client, buyer.email)
        body = pending_order(
            client,
            headers,
            event_id=event.id,
            ticket_type_id=tt.id,
            buyer_email=buyer.email,
        )
        order_id = UUID(str(body["id"]))

        def cancel_worker() -> str:
            s = SessionLocal()
            try:
                from sqlalchemy.orm import selectinload

                locked = s.scalar(
                    select(Order)
                    .where(Order.id == order_id)
                    .options(selectinload(Order.items))
                    .with_for_update()
                )
                cancel_pending_order(s, order=locked, actor_user_id=buyer.id)
                s.commit()
                return "cancelled"
            finally:
                s.close()

        def expire_worker() -> str:
            s = SessionLocal()
            try:
                from sqlalchemy.orm import selectinload

                locked = s.scalar(
                    select(Order)
                    .where(Order.id == order_id)
                    .options(selectinload(Order.items))
                    .with_for_update()
                )
                expire_pending_order(s, order=locked, reason="forced")
                s.commit()
                return "expired"
            finally:
                s.close()

        run_barriered([cancel_worker, expire_worker])
        verify = SessionLocal()
        try:
            final = verify.get(Order, order_id)
            tt_final = verify.get(type(tt), tt.id)
            if final is None or tt_final is None:
                bad += 1
                continue
            assert final.status in {"cancelled", "expired"}
            assert tt_final.quantity_reserved == 0
        finally:
            verify.close()
    assert bad == 0
