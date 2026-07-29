"""Event Ambassador vs Event Merch Ambassador campaign types."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostProfile
from app.payments.models import Order, OrderItem
from app.promos.models import Ambassador, AmbassadorSale
from app.promos.service import finalize_promo_and_attribution
from app.users.models import User
from app.users.service import get_role_by_name


def _login(client: TestClient, email: str) -> dict[str, str]:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _seed(db: Session) -> tuple[Host, Event]:
    host_user = User(
        email="ctype-host@example.com",
        password_hash=hash_password("securepass1"),
        full_name="CType Host",
        is_active=True,
    )
    role = get_role_by_name(db, "host")
    assert role is not None
    host_user.roles.append(role)
    db.add(host_user)
    db.flush()
    host = Host(
        user_id=host_user.id,
        display_name="CType Host",
        slug="ctype-host",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, city="Lagos"))
    category = db.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=8)
    event = Event(
        title="Type Night",
        slug="type-night",
        description="Campaign type tests.",
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
            quantity=100,
            quantity_sold=0,
            quantity_reserved=0,
            min_per_order=1,
            max_per_order=5,
            visibility="public",
            status="active",
        )
    )
    db.commit()
    return host, event


def test_both_campaign_types_per_event(client: TestClient, db_session: Session):
    _, event = _seed(db_session)
    host = _login(client, "ctype-host@example.com")

    tickets = client.post(
        "/api/v1/promos/campaigns",
        headers=host,
        json={
            "event_id": str(event.id),
            "name": "Ticket ambassadors",
            "campaign_type": "event_tickets",
            "commission_percent": "10",
        },
    )
    assert tickets.status_code == 201, tickets.text
    assert tickets.json()["campaign_type"] == "event_tickets"
    assert tickets.json()["merch_included"] is False
    assert tickets.json()["campaign_type_label"] == "Event Ambassador"

    merch = client.post(
        "/api/v1/promos/campaigns",
        headers=host,
        json={
            "event_id": str(event.id),
            "name": "Merch ambassadors",
            "campaign_type": "event_merch",
            "commission_percent": "12",
        },
    )
    assert merch.status_code == 201, merch.text
    assert merch.json()["campaign_type"] == "event_merch"
    assert merch.json()["merch_included"] is True

    dup = client.post(
        "/api/v1/promos/campaigns",
        headers=host,
        json={
            "event_id": str(event.id),
            "name": "Dup tickets",
            "campaign_type": "event_tickets",
        },
    )
    assert dup.status_code == 409

    listed = client.get(f"/api/v1/promos/events/{event.id}/campaigns", headers=host)
    assert listed.status_code == 200
    assert len(listed.json()) == 2

    program = client.get(f"/api/v1/promos/events/{event.id}/ambassadors/program")
    assert program.status_code == 200
    body = program.json()
    assert body["enabled"] is True
    assert len(body["campaigns"]) == 2


def test_join_and_attribute_by_campaign_type(
    client: TestClient, db_session: Session
):
    _, event = _seed(db_session)
    host = _login(client, "ctype-host@example.com")
    for ctype, pct in (("event_tickets", "10"), ("event_merch", "15")):
        created = client.post(
            "/api/v1/promos/campaigns",
            headers=host,
            json={
                "event_id": str(event.id),
                "name": ctype,
                "campaign_type": ctype,
                "commission_percent": pct,
            },
        )
        assert created.status_code == 201, created.text

    client.post(
        "/api/v1/auth/register",
        json={
            "email": "ctype-fan@example.com",
            "password": "securepass1",
            "full_name": "CType Fan",
        "gender": "prefer_not_to_say"},
    )
    fan = _login(client, "ctype-fan@example.com")

    ticket_join = client.post(
        f"/api/v1/promos/events/{event.id}/ambassadors/join",
        headers=fan,
        json={"accept_terms": True, "campaign_type": "event_tickets"},
    )
    assert ticket_join.status_code == 201, ticket_join.text
    merch_join = client.post(
        f"/api/v1/promos/events/{event.id}/ambassadors/join",
        headers=fan,
        json={"accept_terms": True, "campaign_type": "event_merch"},
    )
    assert merch_join.status_code == 201, merch_join.text
    assert ticket_join.json()["id"] != merch_join.json()["id"]

    ticket_amb = db_session.get(Ambassador, UUID(ticket_join.json()["id"]))
    merch_amb = db_session.get(Ambassador, UUID(merch_join.json()["id"]))
    assert ticket_amb is not None and merch_amb is not None

    buyer = User(
        email="ctype-buyer@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Buyer",
        is_active=True,
    )
    db_session.add(buyer)
    db_session.flush()

    # Ticket-only order → ticket ambassador earns.
    order = Order(
        event_id=event.id,
        buyer_user_id=buyer.id,
        buyer_email=buyer.email,
        buyer_name=buyer.full_name,
        status="paid",
        currency="NGN",
        subtotal_amount=Decimal("5000"),
        discount_amount=Decimal("0"),
        total_amount=Decimal("5000"),
        reference=f"ref-{uuid4().hex[:10]}",
        ambassador_id=ticket_amb.id,
        referral_code=ticket_amb.referral_code,
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
    _ = list(order.items)
    finalize_promo_and_attribution(db_session, order=order)
    db_session.commit()
    db_session.expire_all()
    sale = db_session.scalar(
        select(AmbassadorSale).where(AmbassadorSale.order_id == order.id)
    )
    assert sale is not None
    assert sale.tickets_sold == 1
    assert sale.merch_units_sold == 0
    assert sale.commission_owed == Decimal("500.00")

    # Merch-only order attributed to merch ambassador.
    order2 = Order(
        event_id=event.id,
        buyer_user_id=buyer.id,
        buyer_email=buyer.email,
        buyer_name=buyer.full_name,
        status="paid",
        currency="NGN",
        subtotal_amount=Decimal("2000"),
        discount_amount=Decimal("0"),
        total_amount=Decimal("2000"),
        reference=f"ref-{uuid4().hex[:10]}",
        ambassador_id=merch_amb.id,
        referral_code=merch_amb.referral_code,
    )
    db_session.add(order2)
    db_session.flush()
    db_session.add(
        OrderItem(
            order_id=order2.id,
            item_kind="merch",
            product_name="Tee",
            quantity=2,
            unit_price=Decimal("1000"),
            line_total=Decimal("2000"),
        )
    )
    db_session.commit()
    order2 = db_session.get(Order, order2.id)
    assert order2 is not None
    _ = list(order2.items)
    finalize_promo_and_attribution(db_session, order=order2)
    db_session.commit()
    db_session.expire_all()
    sale2 = db_session.scalar(
        select(AmbassadorSale).where(AmbassadorSale.order_id == order2.id)
    )
    assert sale2 is not None
    assert sale2.tickets_sold == 0
    assert sale2.merch_units_sold == 2
    assert sale2.commission_owed == Decimal("300.00")
