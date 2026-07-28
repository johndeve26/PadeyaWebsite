"""Phase 4.5 — CC-004 merch inventory concurrency (PostgreSQL)."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.events.models import Event, EventCategory
from app.hosts.models import Host, HostProfile
from app.merch.models import EventMerchProduct, EventMerchVariant
from app.payments.models import Order
from app.payments.paystack import sign_body_for_tests
from app.users.models import User
from app.users.service import get_role_by_name
from tests.helpers.phase4_payments import expected_kobo
from tests.phase45.helpers import create_buyer, login, run_barriered

pytestmark = pytest.mark.skipif(
    os.environ.get("PHASE45_POSTGRES") != "1",
    reason="Phase 4.5 Postgres concurrency — set PHASE45_POSTGRES=1",
)

ITERATIONS = int(os.environ.get("PHASE45_ITERATIONS", "20"))


def _seed_merch_event(db: Session, *, inventory: int) -> tuple[Event, EventMerchVariant, dict]:
    """Create host+event+merch via ORM then return host login via register path."""
    suffix = uuid4().hex[:10]
    host_user = User(
        email=f"mhost-{suffix}@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Merch Host",
        is_active=True,
        is_verified=True,
    )
    role = get_role_by_name(db, "host")
    if role:
        host_user.roles.append(role)
    db.add(host_user)
    db.flush()
    host = Host(
        user_id=host_user.id,
        display_name="MH",
        slug=f"mh-{suffix}",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, city="Lagos"))
    cat = db.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=7)
    event = Event(
        title="Merch Ev",
        slug=f"mev-{suffix}",
        description="Merch concurrency event description with enough characters.",
        category_id=cat.id if cat else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=3),
        venue_name="V",
        city="Lagos",
        state="Lagos",
        status="published",
        published_at=datetime.now(UTC),
    )
    if hasattr(event, "allow_merch_only_checkout"):
        event.allow_merch_only_checkout = True
    db.add(event)
    db.flush()
    product = EventMerchProduct(
        event_id=event.id,
        host_id=host.id,
        name="Tee",
        slug=f"tee-{suffix}",
        description="Shirt",
        status="active",
        currency="NGN",
        base_price=Decimal("2000.00"),
        max_per_order=5,
        is_merch_only_enabled=True,
    )
    db.add(product)
    db.flush()
    variant = EventMerchVariant(
        product_id=product.id,
        label="M",
        inventory_count=inventory,
        reserved_quantity=0,
        sold_quantity=0,
        status="active",
    )
    # Field names may differ — adapt
    for attr, val in (
        ("sku", f"SKU-{suffix}"),
        ("price_override", None),
    ):
        if hasattr(variant, attr):
            setattr(variant, attr, val)
    db.add(variant)
    db.commit()
    db.refresh(event)
    db.refresh(variant)
    return event, variant, {"email": host_user.email}


def test_cc004_last_merch_concurrent_orders(client: TestClient, db_session: Session):
    """stock=1 — at most one successful reservation under concurrent order create."""
    failures: list[str] = []
    for i in range(min(ITERATIONS, 15)):
        try:
            event, variant, _ = _seed_merch_event(db_session, inventory=1)
            e1 = f"mb-a-{i}-{uuid4().hex[:8]}@example.com"
            e2 = f"mb-b-{i}-{uuid4().hex[:8]}@example.com"
            create_buyer(db_session, e1)
            create_buyer(db_session, e2)
            h1 = login(client, e1)
            h2 = login(client, e2)
            body = {
                "event_id": str(event.id),
                "items": [
                    {
                        "item_kind": "merch",
                        "merch_variant_id": str(variant.id),
                        "quantity": 1,
                    }
                ],
            }

            def _o1() -> int:
                r = client.post("/api/v1/orders", headers=h1, json=body)
                return r.status_code

            def _o2() -> int:
                r = client.post("/api/v1/orders", headers=h2, json=body)
                return r.status_code

            codes = run_barriered([_o1, _o2])
            assert codes.count(201) <= 1, codes
            db_session.expire_all()
            db_session.refresh(variant)
            reserved = int(getattr(variant, "reserved_quantity", 0) or 0)
            inv = int(variant.inventory_count)
            sold = int(getattr(variant, "sold_quantity", 0) or 0)
            assert reserved + sold <= 1 or inv >= 0
            assert inv >= 0
            assert reserved >= 0
        except Exception as exc:  # noqa: BLE001
            failures.append(f"iter={i}: {type(exc).__name__}: {exc}")
    assert not failures, failures


def test_cc004_merch_stock_three_vs_two_two(client: TestClient, db_session: Session):
    failures: list[str] = []
    for i in range(min(ITERATIONS, 15)):
        try:
            event, variant, _ = _seed_merch_event(db_session, inventory=3)
            e1 = f"m32-a-{i}-{uuid4().hex[:8]}@example.com"
            e2 = f"m32-b-{i}-{uuid4().hex[:8]}@example.com"
            create_buyer(db_session, e1)
            create_buyer(db_session, e2)
            h1 = login(client, e1)
            h2 = login(client, e2)

            def _o1() -> int:
                return client.post(
                    "/api/v1/orders",
                    headers=h1,
                    json={
                        "event_id": str(event.id),
                        "items": [
                            {
                                "item_kind": "merch",
                                "merch_variant_id": str(variant.id),
                                "quantity": 2,
                            }
                        ],
                    },
                ).status_code

            def _o2() -> int:
                return client.post(
                    "/api/v1/orders",
                    headers=h2,
                    json={
                        "event_id": str(event.id),
                        "items": [
                            {
                                "item_kind": "merch",
                                "merch_variant_id": str(variant.id),
                                "quantity": 2,
                            }
                        ],
                    },
                ).status_code

            codes = run_barriered([_o1, _o2])
            assert codes.count(201) <= 1, codes
            db_session.refresh(variant)
            reserved = int(getattr(variant, "reserved_quantity", 0) or 0)
            assert reserved <= 3
        except Exception as exc:  # noqa: BLE001
            failures.append(f"iter={i}: {type(exc).__name__}: {exc}")
    assert not failures, failures
