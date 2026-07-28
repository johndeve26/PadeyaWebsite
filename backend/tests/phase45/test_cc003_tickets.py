"""Phase 4.5 — CC-003 ticket inventory + event capacity concurrency."""

from __future__ import annotations

import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.tickets.models import Ticket
from tests.phase45.helpers import create_buyer, login, run_barriered, seed_event

pytestmark = pytest.mark.skipif(
    os.environ.get("PHASE45_POSTGRES") != "1",
    reason="Phase 4.5 Postgres concurrency — set PHASE45_POSTGRES=1",
)

ITERATIONS = int(os.environ.get("PHASE45_ITERATIONS", "20"))


def test_cc003_last_ticket_concurrent_create_iterations(
    client: TestClient, db_session: Session
):
    failures: list[str] = []
    for i in range(ITERATIONS):
        try:
            event, tt = seed_event(db_session, price="1000.00", qty=1)
            e1 = f"t3a-{i}-{uuid4().hex[:8]}@example.com"
            e2 = f"t3b-{i}-{uuid4().hex[:8]}@example.com"
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
            db_session.expire_all()
            db_session.refresh(tt)
            assert tt.quantity_sold + tt.quantity_reserved <= 1
            assert tt.quantity_sold + tt.quantity_reserved >= 0
        except Exception as exc:  # noqa: BLE001
            failures.append(f"iter={i}: {type(exc).__name__}: {exc}")
    assert not failures, failures


def test_cc003_multi_qty_cap_concurrent(client: TestClient, db_session: Session):
    failures: list[str] = []
    for i in range(ITERATIONS):
        try:
            event, tt = seed_event(db_session, price="1000.00", qty=3)
            e1 = f"t3m1-{i}-{uuid4().hex[:8]}@example.com"
            e2 = f"t3m2-{i}-{uuid4().hex[:8]}@example.com"
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
                        "items": [{"ticket_type_id": str(tt.id), "quantity": 2}],
                    },
                ).status_code

            def _o2() -> int:
                return client.post(
                    "/api/v1/orders",
                    headers=h2,
                    json={
                        "event_id": str(event.id),
                        "items": [{"ticket_type_id": str(tt.id), "quantity": 2}],
                    },
                ).status_code

            codes = run_barriered([_o1, _o2])
            assert codes.count(201) <= 1, codes
            db_session.expire_all()
            db_session.refresh(tt)
            assert tt.quantity_reserved + tt.quantity_sold <= 3
        except Exception as exc:  # noqa: BLE001
            failures.append(f"iter={i}: {type(exc).__name__}: {exc}")
    assert not failures, failures


def test_event_capacity_concurrency(client: TestClient, db_session: Session):
    """If event.capacity is enforced, two types cannot oversell event capacity."""
    from datetime import UTC, datetime, timedelta
    from decimal import Decimal
    from uuid import uuid4 as u4

    from app.core.security import hash_password
    from app.events.models import Event, EventCategory, TicketType
    from app.hosts.models import Host, HostProfile
    from app.users.models import User
    from app.users.service import get_role_by_name

    failures: list[str] = []
    for i in range(min(ITERATIONS, 10)):
        try:
            suffix = u4().hex[:10]
            host_user = User(
                email=f"cap-host-{suffix}@example.com",
                password_hash=hash_password("securepass1"),
                full_name="Host",
                is_active=True,
                is_verified=True,
            )
            role = get_role_by_name(db_session, "host")
            if role:
                host_user.roles.append(role)
            db_session.add(host_user)
            db_session.flush()
            host = Host(
                user_id=host_user.id,
                display_name="H",
                slug=f"cap-{suffix}",
                status="active",
            )
            db_session.add(host)
            db_session.flush()
            db_session.add(HostProfile(host_id=host.id, city="Lagos"))
            cat = db_session.query(EventCategory).first()
            start = datetime.now(UTC) + timedelta(days=10)
            event = Event(
                title="Cap",
                slug=f"cap-ev-{suffix}",
                description="Event capacity concurrency test description text here.",
                category_id=cat.id if cat else None,
                host_id=host.id,
                start_datetime=start,
                end_datetime=start + timedelta(hours=3),
                venue_name="V",
                city="Lagos",
                state="Lagos",
                status="published",
                published_at=datetime.now(UTC),
                capacity=1,
            )
            db_session.add(event)
            db_session.flush()
            t1 = TicketType(
                event_id=event.id,
                name="A",
                type="regular",
                description="A",
                price=Decimal("1000.00"),
                quantity=5,
                quantity_sold=0,
                quantity_reserved=0,
                min_per_order=1,
                max_per_order=5,
                visibility="public",
                status="active",
            )
            t2 = TicketType(
                event_id=event.id,
                name="B",
                type="regular",
                description="B",
                price=Decimal("1000.00"),
                quantity=5,
                quantity_sold=0,
                quantity_reserved=0,
                min_per_order=1,
                max_per_order=5,
                visibility="public",
                status="active",
            )
            db_session.add_all([t1, t2])
            db_session.commit()
            db_session.refresh(event)
            db_session.refresh(t1)
            db_session.refresh(t2)

            e1 = f"cap-a-{i}-{uuid4().hex[:8]}@example.com"
            e2 = f"cap-b-{i}-{uuid4().hex[:8]}@example.com"
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
            # Phase 4.6: event.capacity is a venue hard cap when set.
            assert codes.count(201) <= 1, codes
            db_session.expire_all()
            db_session.refresh(t1)
            db_session.refresh(t2)
            committed = (
                (t1.quantity_reserved or 0)
                + (t1.quantity_sold or 0)
                + (t2.quantity_reserved or 0)
                + (t2.quantity_sold or 0)
            )
            assert committed <= 1
        except pytest.skip.Exception:
            raise
        except Exception as exc:  # noqa: BLE001
            failures.append(f"iter={i}: {type(exc).__name__}: {exc}")
    assert not failures, failures
