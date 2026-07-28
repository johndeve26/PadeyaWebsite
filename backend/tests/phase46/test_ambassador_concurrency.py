"""Phase 4.6 — ambassador conversion concurrent finalization (Postgres)."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostProfile
from app.payments.webhook import process_paystack_webhook
from app.promos.ambassador_domain import AmbassadorConversion
from app.users.models import User
from app.users.service import get_role_by_name
from tests.phase45.helpers import (
    create_buyer,
    login,
    run_barriered,
    session_factory,
    signed_charge_body,
)

pytestmark = pytest.mark.skipif(
    os.environ.get("PHASE45_POSTGRES") != "1",
    reason="Phase 4.6 uses Phase 4.5 Postgres profile",
)

ITERATIONS = int(os.environ.get("PHASE46_ITERATIONS", os.environ.get("PHASE45_ITERATIONS", "20")))


def _host_event(db: Session, tag: str) -> tuple[str, Event, TicketType]:
    host_email = f"amb46-host-{tag}@example.com"
    host_user = User(
        email=host_email,
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
    host = Host(
        user_id=host_user.id,
        display_name="H",
        slug=f"amb46-{tag}",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, city="Lagos"))
    cat = db.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=12)
    event = Event(
        title="Amb46",
        slug=f"amb46-{tag}",
        description="Ambassador concurrency event description with enough text.",
        category_id=cat.id if cat else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=3),
        city="Lagos",
        state="Lagos",
        venue_name="V",
        status="published",
        published_at=datetime.now(UTC),
    )
    db.add(event)
    db.flush()
    ga = TicketType(
        event_id=event.id,
        name="GA",
        type="regular",
        description="GA",
        price=Decimal("5000.00"),
        quantity=50,
        quantity_sold=0,
        quantity_reserved=0,
        min_per_order=1,
        max_per_order=5,
        visibility="public",
        status="active",
    )
    db.add(ga)
    db.commit()
    db.refresh(event)
    db.refresh(ga)
    return host_email, event, ga


def test_ambassador_conversion_concurrent_webhook(
    client: TestClient, db_session: Session, db_engine
):
    SessionLocal = session_factory(db_engine)
    failures: list[str] = []
    for i in range(ITERATIONS):
        try:
            tag = uuid4().hex[:8]
            host_email, event, ga = _host_event(db_session, tag)
            host_h = login(client, host_email)
            amb_email = f"amb46-a-{tag}@example.com"
            create_buyer(db_session, amb_email)
            amb_h = login(client, amb_email)
            buyer_email = f"amb46-b-{tag}@example.com"
            create_buyer(db_session, buyer_email)
            buyer_h = login(client, buyer_email)

            created = client.post(
                "/api/v1/host/ambassadors/campaigns",
                headers=host_h,
                json={
                    "event_id": str(event.id),
                    "name": "Pay campaign",
                    "campaign_type": "event",
                    "commission_type": "percentage",
                    "commission_value": "10",
                    "applies_to": "tickets",
                    "status": "active",
                    "visibility": "public_open",
                },
            )
            assert created.status_code == 201, created.text
            campaign_id = created.json()["id"]
            join = client.post(
                "/api/v1/ambassadors/join",
                headers=amb_h,
                json={"accept_terms": True, "campaign_id": campaign_id},
            )
            assert join.status_code == 200, join.text
            code = join.json()["ambassador_code"]

            order_resp = client.post(
                "/api/v1/orders",
                headers=buyer_h,
                json={
                    "event_id": str(event.id),
                    "items": [{"ticket_type_id": str(ga.id), "quantity": 1}],
                    "referral_code": code,
                    "referral_source": "cookie",
                },
            )
            assert order_resp.status_code == 201, order_resp.text
            order = order_resp.json()
            with __import__("unittest.mock", fromlist=["patch"]).patch(
                "app.payments.service.initialize_transaction",
                return_value={
                    "authorization_url": "https://checkout.paystack.com/test",
                    "access_code": "ACCESS",
                    "reference": order["reference"],
                },
            ):
                assert (
                    client.post(
                        f"/api/v1/payments/checkout/{order['id']}", headers=buyer_h
                    ).status_code
                    == 200
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
            db_session.expire_all()
            conversions = list(
                db_session.scalars(
                    select(AmbassadorConversion).where(
                        AmbassadorConversion.order_id == UUID(order["id"])
                    )
                )
            )
            assert len(conversions) == 1, (len(conversions), statuses)
            assert conversions[0].status == "approved"
        except Exception as exc:  # noqa: BLE001
            failures.append(f"iter={i}: {type(exc).__name__}: {exc}")
    assert not failures, failures
