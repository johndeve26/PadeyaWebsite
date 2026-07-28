"""Phase 4.5 PostgreSQL concurrency — CC-001 via dedicated DB sessions (not TestClient threads)."""

from __future__ import annotations

import os
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.finance.models import PlatformLedgerEntry
from app.payments.models import Order, Payment
from app.payments.webhook import process_paystack_webhook
from app.tickets.models import Ticket
from tests.phase45.helpers import (
    create_buyer,
    login,
    pending_order,
    run_barriered,
    seed_event,
    session_factory,
    signed_charge_body,
)

pytestmark = pytest.mark.skipif(
    os.environ.get("PHASE45_POSTGRES") != "1",
    reason="Phase 4.5 Postgres concurrency — set PHASE45_POSTGRES=1",
)

ITERATIONS = int(os.environ.get("PHASE45_ITERATIONS", "20"))


def _assert_single_paid(db: Session, order_id: UUID, *, qty: int) -> None:
    db.expire_all()
    order = db.get(Order, order_id)
    assert order is not None
    assert order.status == "paid"
    tickets = list(db.scalars(select(Ticket).where(Ticket.order_id == order_id)))
    assert len(tickets) == qty
    payments = list(db.scalars(select(Payment).where(Payment.order_id == order_id)))
    assert len([p for p in payments if p.status == "successful"]) == 1
    ledger_rows = list(
        db.scalars(
            select(PlatformLedgerEntry).where(
                PlatformLedgerEntry.dedupe_key.contains(str(order_id))
            )
        )
    )
    keys = [r.dedupe_key for r in ledger_rows]
    assert len(keys) == len(set(keys))


def test_cc001_concurrent_duplicate_webhook_iterations(
    client: TestClient, db_session: Session, db_engine
):
    """CC-001: two sessions, barriered process_paystack_webhook → one paid order."""
    SessionLocal = session_factory(db_engine)
    passes = 0
    failures: list[str] = []
    for i in range(ITERATIONS):
        try:
            event, tt = seed_event(db_session, price="1000.00", qty=20)
            email = f"cc001-{i}-{uuid4().hex[:8]}@example.com"
            create_buyer(db_session, email)
            headers = login(client, email)
            order = pending_order(
                client,
                headers,
                event_id=str(event.id),
                ticket_type_id=str(tt.id),
                quantity=1,
            )
            body, sig = signed_charge_body(order)

            def _worker() -> str:
                s = SessionLocal()
                try:
                    result = process_paystack_webhook(s, body=body, signature=sig)
                    return str(result.get("status"))
                except Exception as exc:  # noqa: BLE001
                    return f"err:{type(exc).__name__}"
                finally:
                    s.close()

            statuses = run_barriered([_worker, _worker])
            assert any(st in {"ok", "duplicate"} for st in statuses), statuses
            db_session.commit()
            _assert_single_paid(db_session, UUID(order["id"]), qty=1)
            passes += 1
        except Exception as exc:  # noqa: BLE001
            failures.append(f"iter={i}: {type(exc).__name__}: {exc}")

    assert not failures, failures
    assert passes == ITERATIONS


def test_cc001_confirm_vs_webhook_race_iterations(
    client: TestClient, db_session: Session, db_engine
):
    SessionLocal = session_factory(db_engine)
    passes = 0
    failures: list[str] = []
    for i in range(ITERATIONS):
        try:
            event, tt = seed_event(db_session, price="1000.00", qty=20)
            email = f"cc001b-{i}-{uuid4().hex[:8]}@example.com"
            create_buyer(db_session, email)
            headers = login(client, email)
            order = pending_order(
                client,
                headers,
                event_id=str(event.id),
                ticket_type_id=str(tt.id),
            )
            body, sig = signed_charge_body(order)
            amount = int(float(order["total_amount"]) * 100)
            # unique provider id per iteration (avoid cross-run event_key collisions)
            verify = {
                "id": uuid4().int % 10**12,
                "reference": order["reference"],
                "amount": amount,
                "currency": "NGN",
                "status": "success",
            }
            order_id = UUID(order["id"])

            def _webhook() -> str:
                s = SessionLocal()
                try:
                    result = process_paystack_webhook(s, body=body, signature=sig)
                    return f"wh:{result.get('status')}"
                except Exception as exc:  # noqa: BLE001
                    return f"wh:err:{type(exc).__name__}"
                finally:
                    s.close()

            def _confirm() -> str:
                s = SessionLocal()
                try:
                    from app.payments.service import finalize_pending_order_via_paystack

                    with patch(
                        "app.payments.service.verify_transaction",
                        return_value=verify,
                    ):
                        o = s.get(Order, order_id)
                        assert o is not None
                        finalize_pending_order_via_paystack(s, o)
                    return "cf:ok"
                except Exception as exc:  # noqa: BLE001
                    s.rollback()
                    return f"cf:err:{type(exc).__name__}"
                finally:
                    s.close()

            statuses = run_barriered([_webhook, _confirm])
            assert any(
                st.startswith("wh:ok")
                or st.startswith("wh:duplicate")
                or st == "cf:ok"
                for st in statuses
            ), statuses
            db_session.commit()
            _assert_single_paid(db_session, order_id, qty=1)
            passes += 1
        except Exception as exc:  # noqa: BLE001
            failures.append(f"iter={i}: {type(exc).__name__}: {exc}")

    assert not failures, failures
    assert passes == ITERATIONS
