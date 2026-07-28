"""Phase 4.6 — event capacity, mixed commerce, ambassador concurrency (Postgres)."""

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
from app.users.models import User
from app.users.service import get_role_by_name
from tests.phase45.helpers import (
    create_buyer,
    login,
    run_barriered,
    seed_event,
)

pytestmark = pytest.mark.skipif(
    os.environ.get("PHASE45_POSTGRES") != "1",
    reason="Phase 4.6 uses Phase 4.5 Postgres profile (PHASE45_POSTGRES=1)",
)

ITERATIONS = int(os.environ.get("PHASE46_ITERATIONS", os.environ.get("PHASE45_ITERATIONS", "20")))


def _two_types_event(db: Session, *, capacity: int, qty_each: int = 5) -> tuple[Event, TicketType, TicketType]:
    suffix = uuid4().hex[:10]
    host_user = User(
        email=f"cap46-{suffix}@example.com",
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
    host = Host(user_id=host_user.id, display_name="H", slug=f"h46-{suffix}", status="active")
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, city="Lagos"))
    cat = db.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=10)
    event = Event(
        title="Cap46",
        slug=f"cap46-{suffix}",
        description="Phase 4.6 capacity event description with enough characters.",
        category_id=cat.id if cat else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=3),
        venue_name="V",
        city="Lagos",
        state="Lagos",
        status="published",
        published_at=datetime.now(UTC),
        capacity=capacity,
    )
    db.add(event)
    db.flush()
    t1 = TicketType(
        event_id=event.id,
        name="A",
        type="regular",
        description="A",
        price=Decimal("1000.00"),
        quantity=qty_each,
        quantity_sold=0,
        quantity_reserved=0,
        seats_per_unit=1,
        min_per_order=1,
        max_per_order=10,
        visibility="public",
        status="active",
    )
    t2 = TicketType(
        event_id=event.id,
        name="B",
        type="regular",
        description="B",
        price=Decimal("1000.00"),
        quantity=qty_each,
        quantity_sold=0,
        quantity_reserved=0,
        seats_per_unit=1,
        min_per_order=1,
        max_per_order=10,
        visibility="public",
        status="active",
    )
    db.add_all([t1, t2])
    db.commit()
    db.refresh(event)
    db.refresh(t1)
    db.refresh(t2)
    return event, t1, t2


def test_event_capacity_cross_type_concurrent(client: TestClient, db_session: Session):
    """capacity=1, two types each with stock — at most one order succeeds."""
    failures: list[str] = []
    for i in range(ITERATIONS):
        try:
            event, t1, t2 = _two_types_event(db_session, capacity=1, qty_each=5)
            e1 = f"c46a-{i}-{uuid4().hex[:8]}@example.com"
            e2 = f"c46b-{i}-{uuid4().hex[:8]}@example.com"
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
                        "items": [{"ticket_type_id": str(t1.id), "quantity": 1}],
                    },
                ).status_code

            def _o2() -> int:
                return client.post(
                    "/api/v1/orders",
                    headers=h2,
                    json={
                        "event_id": str(event.id),
                        "items": [{"ticket_type_id": str(t2.id), "quantity": 1}],
                    },
                ).status_code

            codes = run_barriered([_o1, _o2])
            assert codes.count(201) <= 1, codes
            db_session.expire_all()
            db_session.refresh(t1)
            db_session.refresh(t2)
            committed = (
                t1.quantity_reserved
                + t1.quantity_sold
                + t2.quantity_reserved
                + t2.quantity_sold
            )
            assert committed <= 1
        except Exception as exc:  # noqa: BLE001
            failures.append(f"iter={i}: {type(exc).__name__}: {exc}")
    assert not failures, failures


def test_event_capacity_multi_qty_race(client: TestClient, db_session: Session):
    """capacity=3; 2+2 concurrent across types → total reserved seats <= 3."""
    failures: list[str] = []
    for i in range(ITERATIONS):
        try:
            event, t1, t2 = _two_types_event(db_session, capacity=3, qty_each=5)
            e1 = f"c46m1-{i}-{uuid4().hex[:8]}@example.com"
            e2 = f"c46m2-{i}-{uuid4().hex[:8]}@example.com"
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
                        "items": [{"ticket_type_id": str(t1.id), "quantity": 2}],
                    },
                ).status_code

            def _o2() -> int:
                return client.post(
                    "/api/v1/orders",
                    headers=h2,
                    json={
                        "event_id": str(event.id),
                        "items": [{"ticket_type_id": str(t2.id), "quantity": 2}],
                    },
                ).status_code

            codes = run_barriered([_o1, _o2])
            assert codes.count(201) <= 1, codes
            db_session.refresh(t1)
            db_session.refresh(t2)
            committed = (
                t1.quantity_reserved
                + t1.quantity_sold
                + t2.quantity_reserved
                + t2.quantity_sold
            )
            assert committed <= 3
        except Exception as exc:  # noqa: BLE001
            failures.append(f"iter={i}: {type(exc).__name__}: {exc}")
    assert not failures, failures


def test_pending_reservation_holds_event_capacity(client: TestClient, db_session: Session):
    event, t1, t2 = _two_types_event(db_session, capacity=1, qty_each=5)
    e1 = f"hold-a-{uuid4().hex[:8]}@example.com"
    e2 = f"hold-b-{uuid4().hex[:8]}@example.com"
    create_buyer(db_session, e1)
    create_buyer(db_session, e2)
    h1 = login(client, e1)
    h2 = login(client, e2)
    r1 = client.post(
        "/api/v1/orders",
        headers=h1,
        json={
            "event_id": str(event.id),
            "items": [{"ticket_type_id": str(t1.id), "quantity": 1}],
        },
    )
    assert r1.status_code == 201, r1.text
    r2 = client.post(
        "/api/v1/orders",
        headers=h2,
        json={
            "event_id": str(event.id),
            "items": [{"ticket_type_id": str(t2.id), "quantity": 1}],
        },
    )
    assert r2.status_code == 409, r2.text


def test_free_ticket_respects_event_capacity(client: TestClient, db_session: Session):
    event, tt = seed_event(db_session, price="0.00", qty=5, capacity=1)
    # seed_event may not pass capacity — set it
    event.capacity = 1
    db_session.commit()
    e1 = f"free-a-{uuid4().hex[:8]}@example.com"
    e2 = f"free-b-{uuid4().hex[:8]}@example.com"
    create_buyer(db_session, e1)
    create_buyer(db_session, e2)
    h1 = login(client, e1)
    h2 = login(client, e2)
    body = {
        "event_id": str(event.id),
        "items": [{"ticket_type_id": str(tt.id), "quantity": 1}],
    }

    def _o1() -> int:
        return client.post("/api/v1/orders", headers=h1, json=body).status_code

    def _o2() -> int:
        return client.post("/api/v1/orders", headers=h2, json=body).status_code

    codes = run_barriered([_o1, _o2])
    assert codes.count(201) <= 1, codes


def test_group_seats_count_toward_capacity(client: TestClient, db_session: Session):
    event, t1, _t2 = _two_types_event(db_session, capacity=3, qty_each=5)
    t1.seats_per_unit = 3
    t1.price = Decimal("3000.00")
    t1.type = "group"
    db_session.commit()
    email = f"grp-{uuid4().hex[:8]}@example.com"
    create_buyer(db_session, email)
    headers = login(client, email)
    # one group unit = 3 seats → fills capacity
    ok = client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "event_id": str(event.id),
            "items": [{"ticket_type_id": str(t1.id), "quantity": 1}],
        },
    )
    assert ok.status_code == 201, ok.text
    email2 = f"grp2-{uuid4().hex[:8]}@example.com"
    create_buyer(db_session, email2)
    h2 = login(client, email2)
    blocked = client.post(
        "/api/v1/orders",
        headers=h2,
        json={
            "event_id": str(event.id),
            "items": [{"ticket_type_id": str(t1.id), "quantity": 1}],
        },
    )
    assert blocked.status_code == 409, blocked.text


def test_blank_capacity_is_tier_only(client: TestClient, db_session: Session):
    """When event.capacity is blank, only per-tier stock applies (both types can sell)."""
    event, t1, t2 = _two_types_event(db_session, capacity=1, qty_each=1)
    event.capacity = None
    db_session.commit()
    e1 = f"tier-a-{uuid4().hex[:8]}@example.com"
    e2 = f"tier-b-{uuid4().hex[:8]}@example.com"
    create_buyer(db_session, e1)
    create_buyer(db_session, e2)
    h1 = login(client, e1)
    h2 = login(client, e2)
    r1 = client.post(
        "/api/v1/orders",
        headers=h1,
        json={
            "event_id": str(event.id),
            "items": [{"ticket_type_id": str(t1.id), "quantity": 1}],
        },
    )
    r2 = client.post(
        "/api/v1/orders",
        headers=h2,
        json={
            "event_id": str(event.id),
            "items": [{"ticket_type_id": str(t2.id), "quantity": 1}],
        },
    )
    assert r1.status_code == 201, r1.text
    assert r2.status_code == 201, r2.text


def test_no_separate_complimentary_issuance_api(client: TestClient):
    """Host/admin complimentary issuance is not a separate ticket-mint API.

    Free tickets still go through POST /orders (+ free checkout finalize), which
    enforces event.capacity when set. Table reservations are a distinct resource.
    """
    assert client.post("/api/v1/tickets/complimentary").status_code in {404, 405, 401, 403}
    assert client.post("/api/v1/tickets/guest-list").status_code in {404, 405, 401, 403}
    assert client.post("/api/v1/admin/tickets/issue").status_code in {404, 405, 401, 403}
