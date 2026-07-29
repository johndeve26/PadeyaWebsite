"""Referral codes unique per campaign + explicit attribution precedence."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostProfile
from app.payments.models import Order, OrderItem
from app.promos.models import Ambassador
from app.promos.service import (
    attach_ambassador_to_order,
    resolve_ambassador_for_event,
)
from app.users.models import User
from app.users.service import get_role_by_name


def _login(client: TestClient, email: str) -> dict[str, str]:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _seed(db: Session) -> Event:
    host_user = User(
        email="ref-host@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Ref Host",
        is_active=True,
    )
    role = get_role_by_name(db, "host")
    assert role is not None
    host_user.roles.append(role)
    db.add(host_user)
    db.flush()
    host = Host(
        user_id=host_user.id,
        display_name="Ref Host",
        slug="ref-host",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, city="Lagos"))
    category = db.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=5)
    event = Event(
        title="Ref Night",
        slug="ref-night",
        description="Referral attribution tests.",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=3),
        city="Lagos",
        status="published",
        featured=False,
        published_at=datetime.now(UTC),
    )
    db.add(event)
    db.flush()
    db.add(
        TicketType(
            event_id=event.id,
            name="GA",
            type="regular",
            price=Decimal("5000.00"),
            quantity=50,
            quantity_sold=0,
            quantity_reserved=0,
            min_per_order=1,
            max_per_order=5,
            visibility="public",
            status="active",
        )
    )
    db.commit()
    return event


def test_code_unique_per_campaign_and_readable_display(
    client: TestClient, db_session: Session
):
    event = _seed(db_session)
    host = _login(client, "ref-host@example.com")
    for ctype in ("event_tickets", "event_merch"):
        assert (
            client.post(
                "/api/v1/promos/campaigns",
                headers=host,
                json={
                    "event_id": str(event.id),
                    "name": ctype,
                    "campaign_type": ctype,
                    "commission_percent": "8",
                },
            ).status_code
            == 201
        )

    client.post(
        "/api/v1/auth/register",
        json={
            "email": "ref-fan@example.com",
            "password": "securepass1",
            "full_name": "Tolu Afro",
        "gender": "prefer_not_to_say"},
    )
    fan = _login(client, "ref-fan@example.com")
    ticket = client.post(
        f"/api/v1/promos/events/{event.id}/ambassadors/join",
        headers=fan,
        json={"accept_terms": True, "campaign_type": "event_tickets"},
    )
    assert ticket.status_code == 201, ticket.text
    merch = client.post(
        f"/api/v1/promos/events/{event.id}/ambassadors/join",
        headers=fan,
        json={"accept_terms": True, "campaign_type": "event_merch"},
    )
    assert merch.status_code == 201, merch.text
    # Same readable code reused across campaigns for one promoter when free.
    assert ticket.json()["referral_code"] == merch.json()["referral_code"]
    assert ticket.json()["referral_code_display"] == ticket.json()[
        "referral_code"
    ].upper()
    assert ticket.json()["campaign_id"] != merch.json()["campaign_id"]


def test_explicit_attribution_not_overwritten_by_link(
    client: TestClient, db_session: Session
):
    event = _seed(db_session)
    host = _login(client, "ref-host@example.com")
    assert (
        client.post(
            "/api/v1/promos/campaigns",
            headers=host,
            json={
                "event_id": str(event.id),
                "name": "Tickets",
                "campaign_type": "event_tickets",
            },
        ).status_code
        == 201
    )

    client.post(
        "/api/v1/auth/register",
        json={
            "email": "ref-a@example.com",
            "password": "securepass1",
            "full_name": "Alpha Ref",
        "gender": "prefer_not_to_say"},
    )
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "ref-b@example.com",
            "password": "securepass1",
            "full_name": "Beta Ref",
        "gender": "prefer_not_to_say"},
    )
    a = _login(client, "ref-a@example.com")
    b = _login(client, "ref-b@example.com")
    join_a = client.post(
        f"/api/v1/promos/events/{event.id}/ambassadors/join",
        headers=a,
        json={"accept_terms": True, "campaign_type": "event_tickets"},
    )
    join_b = client.post(
        f"/api/v1/promos/events/{event.id}/ambassadors/join",
        headers=b,
        json={"accept_terms": True, "campaign_type": "event_tickets"},
    )
    assert join_a.status_code == 201 and join_b.status_code == 201
    amb_a = db_session.get(Ambassador, UUID(join_a.json()["id"]))
    amb_b = db_session.get(Ambassador, UUID(join_b.json()["id"]))
    assert amb_a and amb_b

    buyer = User(
        email="ref-buyer@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Buyer",
        is_active=True,
    )
    db_session.add(buyer)
    db_session.flush()
    order = Order(
        event_id=event.id,
        buyer_user_id=buyer.id,
        buyer_email=buyer.email,
        buyer_name=buyer.full_name,
        status="pending",
        currency="NGN",
        subtotal_amount=Decimal("5000"),
        discount_amount=Decimal("0"),
        total_amount=Decimal("5000"),
        reference=f"ref-{uuid4().hex[:10]}",
    )
    db_session.add(order)
    db_session.flush()
    db_session.add(
        OrderItem(
            order_id=order.id,
            item_kind="ticket",
            ticket_type_name="GA",
            quantity=1,
            unit_price=Decimal("5000"),
            line_total=Decimal("5000"),
        )
    )
    db_session.commit()
    order = db_session.get(Order, order.id)
    assert order is not None

    # Explicit checkout code for A.
    attach_ambassador_to_order(
        db_session,
        order=order,
        ambassador=amb_a,
        attribution_source="explicit",
    )
    db_session.commit()
    db_session.refresh(order)
    assert order.ambassador_id == amb_a.id
    assert order.referral_attribution_source == "explicit"

    # Later link/cookie for B must not overwrite.
    attach_ambassador_to_order(
        db_session,
        order=order,
        ambassador=amb_b,
        attribution_source="cookie",
    )
    db_session.commit()
    db_session.refresh(order)
    assert order.ambassador_id == amb_a.id
    assert order.referral_code == amb_a.referral_code

    # Resolve still finds ambassadors by code.
    found = resolve_ambassador_for_event(
        db_session, referral_code=amb_b.referral_code, event=event
    )
    assert found is not None
    assert found.id == amb_b.id
