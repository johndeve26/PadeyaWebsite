"""Phase 4.6 — mixed ticket+merch concurrency (ALL_OR_NOTHING at reserve)."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostProfile
from app.merch.models import EventMerchProduct, EventMerchVariant
from app.users.models import User
from app.users.service import get_role_by_name
from tests.phase45.helpers import create_buyer, login, run_barriered

pytestmark = pytest.mark.skipif(
    os.environ.get("PHASE45_POSTGRES") != "1",
    reason="Phase 4.6 uses Phase 4.5 Postgres profile",
)

ITERATIONS = int(os.environ.get("PHASE46_ITERATIONS", os.environ.get("PHASE45_ITERATIONS", "20")))


def _seed_mixed(db: Session, *, ticket_qty: int, merch_qty: int):
    suffix = uuid4().hex[:10]
    host_user = User(
        email=f"mix-{suffix}@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Host",
        is_active=True,
        is_verified=True,
    )
    role = get_role_by_name(db, "host")
    if role:
        host_user.roles.append(role)
    db.add(host_user)
    db.flush()
    host = Host(user_id=host_user.id, display_name="H", slug=f"mix-{suffix}", status="active")
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, city="Lagos"))
    cat = db.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=8)
    event = Event(
        title="Mixed",
        slug=f"mix-{suffix}",
        description="Mixed ticket merch concurrency description text here.",
        category_id=cat.id if cat else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=3),
        venue_name="V",
        city="Lagos",
        state="Lagos",
        status="published",
        published_at=datetime.now(UTC),
        allow_merch_only_checkout=True,
    )
    db.add(event)
    db.flush()
    tt = TicketType(
        event_id=event.id,
        name="GA",
        type="regular",
        description="GA",
        price=Decimal("1000.00"),
        quantity=ticket_qty,
        quantity_sold=0,
        quantity_reserved=0,
        min_per_order=1,
        max_per_order=5,
        visibility="public",
        status="active",
    )
    db.add(tt)
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
        inventory_count=merch_qty,
        reserved_quantity=0,
        sold_quantity=0,
        status="active",
    )
    db.add(variant)
    db.commit()
    db.refresh(event)
    db.refresh(tt)
    db.refresh(variant)
    return event, tt, variant


def test_mixed_order_concurrent_last_of_each(client: TestClient, db_session: Session):
    """ticket=1 merch=1; two mixed carts — at most one full reservation succeeds."""
    failures: list[str] = []
    for i in range(ITERATIONS):
        try:
            event, tt, variant = _seed_mixed(db_session, ticket_qty=1, merch_qty=1)
            e1 = f"mx-a-{i}-{uuid4().hex[:8]}@example.com"
            e2 = f"mx-b-{i}-{uuid4().hex[:8]}@example.com"
            create_buyer(db_session, e1)
            create_buyer(db_session, e2)
            h1 = login(client, e1)
            h2 = login(client, e2)
            body = {
                "event_id": str(event.id),
                "items": [
                    {"ticket_type_id": str(tt.id), "quantity": 1},
                    {
                        "item_kind": "merch",
                        "merch_variant_id": str(variant.id),
                        "quantity": 1,
                    },
                ],
            }

            def _o1() -> int:
                return client.post("/api/v1/orders", headers=h1, json=body).status_code

            def _o2() -> int:
                return client.post("/api/v1/orders", headers=h2, json=body).status_code

            codes = run_barriered([_o1, _o2])
            assert codes.count(201) <= 1, codes
            db_session.expire_all()
            db_session.refresh(tt)
            db_session.refresh(variant)
            assert tt.quantity_reserved + tt.quantity_sold <= 1
            reserved = int(variant.reserved_quantity or 0)
            sold = int(variant.sold_quantity or 0)
            assert reserved + sold <= 1
            assert int(variant.inventory_count) >= 0
        except Exception as exc:  # noqa: BLE001
            failures.append(f"iter={i}: {type(exc).__name__}: {exc}")
    assert not failures, failures


def test_mixed_all_or_nothing_at_create(client: TestClient, db_session: Session):
    """If merch is sold out, ticket must not stay reserved from a failed mixed create."""
    event, tt, variant = _seed_mixed(db_session, ticket_qty=2, merch_qty=0)
    email = f"mx-none-{uuid4().hex[:8]}@example.com"
    create_buyer(db_session, email)
    headers = login(client, email)
    res = client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "event_id": str(event.id),
            "items": [
                {"ticket_type_id": str(tt.id), "quantity": 1},
                {
                    "item_kind": "merch",
                    "merch_variant_id": str(variant.id),
                    "quantity": 1,
                },
            ],
        },
    )
    assert res.status_code in {400, 409}, res.text
    db_session.refresh(tt)
    assert tt.quantity_reserved == 0
