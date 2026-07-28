"""Phase 4.5 helpers — fixtures for isolated PostgreSQL concurrency."""

from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Callable
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from app.core.security import hash_password
from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostProfile
from app.payments.paystack import sign_body_for_tests
from app.users.models import User
from app.users.service import get_role_by_name
from tests.helpers.phase4_payments import expected_kobo


def truncate_financial_tables(db: Session) -> None:
    """Best-effort cleanup between Phase 4.5 iterations (Postgres only)."""
    tables = [
        "platform_ledger_entries",
        "ambassador_conversions",
        "ticket_qr_tokens",
        "tickets",
        "payment_webhook_events",
        "payments",
        "order_items",
        "order_attendees",
        "order_checkout_answers",
        "order_fee_snapshots",
        "orders",
        "merch_fulfillments",
        "promo_redemptions",
    ]
    for name in tables:
        try:
            db.execute(text(f"TRUNCATE TABLE {name} RESTART IDENTITY CASCADE"))
            db.commit()
        except Exception:
            db.rollback()


def create_buyer(db: Session, email: str) -> User:
    role = get_role_by_name(db, "buyer")
    user = User(
        email=email.lower(),
        password_hash=hash_password("securepass1"),
        full_name="Buyer",
        is_active=True,
        is_verified=True,
    )
    if role is not None:
        user.roles.append(role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def login(client: TestClient, email: str) -> dict[str, str]:
    res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def seed_event(
    db: Session,
    *,
    price: str = "1000.00",
    qty: int = 10,
    capacity: int | None = None,
) -> tuple[Event, TicketType]:
    suffix = uuid4().hex[:10]
    host_user = User(
        email=f"host-{suffix}@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Host",
        is_active=True,
        is_verified=True,
    )
    role = get_role_by_name(db, "host")
    if role is not None:
        host_user.roles.append(role)
    db.add(host_user)
    db.flush()
    host = Host(
        user_id=host_user.id,
        display_name="Host",
        slug=f"host-{suffix}",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, city="Lagos"))
    category = db.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=14)
    event = Event(
        title="Phase45 Event",
        slug=f"p45-{suffix}",
        description="Isolated PostgreSQL concurrency event with enough description text.",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=4),
        venue_name="Arena",
        city="Lagos",
        state="Lagos",
        status="published",
        featured=False,
        published_at=datetime.now(UTC),
        capacity=capacity,
    )
    db.add(event)
    db.flush()
    tt = TicketType(
        event_id=event.id,
        name="GA",
        type="regular",
        description="GA",
        price=Decimal(price),
        quantity=qty,
        quantity_sold=0,
        quantity_reserved=0,
        min_per_order=1,
        max_per_order=10,
        visibility="public",
        status="active",
    )
    db.add(tt)
    db.commit()
    db.refresh(event)
    db.refresh(tt)
    return event, tt


def pending_order(
    client: TestClient,
    headers: dict[str, str],
    *,
    event_id: str,
    ticket_type_id: str,
    quantity: int = 1,
    promo_code: str | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "event_id": event_id,
        "items": [{"ticket_type_id": ticket_type_id, "quantity": quantity}],
    }
    if promo_code:
        body["promo_code"] = promo_code
    res = client.post("/api/v1/orders", headers=headers, json=body)
    assert res.status_code == 201, res.text
    order = res.json()
    with patch(
        "app.payments.service.initialize_transaction",
        return_value={
            "authorization_url": "https://checkout.paystack.com/test",
            "access_code": "ACCESS",
            "reference": order["reference"],
        },
    ):
        ck = client.post(f"/api/v1/payments/checkout/{order['id']}", headers=headers)
    assert ck.status_code == 200, ck.text
    return order


def signed_charge_body(
    order: dict[str, Any], *, event_id: int | None = None
) -> tuple[bytes, str]:
    eid = event_id if event_id is not None else (uuid4().int % 10**12)
    payload = {
        "event": "charge.success",
        "data": {
            "id": eid,
            "reference": order["reference"],
            "amount": expected_kobo(order["total_amount"]),
            "currency": "NGN",
            "status": "success",
        },
    }
    body = json.dumps(payload).encode("utf-8")
    return body, sign_body_for_tests(body)


def run_barriered(workers: list[Callable[[], Any]]) -> list[Any]:
    barrier = threading.Barrier(len(workers))
    results: list[Any] = [None] * len(workers)

    def _wrap(i: int, fn: Callable[[], Any]) -> None:
        barrier.wait(timeout=30)
        results[i] = fn()

    with ThreadPoolExecutor(max_workers=len(workers)) as pool:
        futs = [pool.submit(_wrap, i, fn) for i, fn in enumerate(workers)]
        for f in futs:
            f.result(timeout=60)
    return results


def session_factory(engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)
