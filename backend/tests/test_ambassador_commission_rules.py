"""Ambassador commission / reward rules (phase 8)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostProfile
from app.payments.models import Order, OrderItem
from app.promos.commission import (
    compute_commission_owed,
    reverse_ambassador_sale_for_order,
)
from app.promos.models import Ambassador, AmbassadorCampaign, AmbassadorSale
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


def _seed(db: Session, *, tag: str) -> tuple[Host, Event, User, str]:
    email = f"comm-host-{tag}@example.com"
    host_user = User(
        email=email,
        password_hash=hash_password("securepass1"),
        full_name="Comm Host",
        is_active=True,
    )
    role = get_role_by_name(db, "host")
    assert role is not None
    host_user.roles.append(role)
    db.add(host_user)
    db.flush()
    host = Host(
        user_id=host_user.id,
        display_name="Comm Host",
        slug=f"comm-host-{tag}",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, city="Lagos"))
    category = db.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=8)
    event = Event(
        title="Commission Night",
        slug=f"commission-night-{tag}",
        description="Commission rule tests.",
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
    buyer = User(
        email=f"comm-buyer-{tag}@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Buyer",
        is_active=True,
    )
    db.add(buyer)
    db.commit()
    return host, event, buyer, email


def _make_ambassador(
    db: Session,
    *,
    host: Host,
    event: Event,
    campaign_id: UUID,
    tag: str,
) -> Ambassador:
    amb_user = User(
        email=f"comm-amb-{tag}@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Amb",
        is_active=True,
    )
    db.add(amb_user)
    db.flush()
    amb = Ambassador(
        host_id=host.id,
        event_id=event.id,
        campaign_id=campaign_id,
        user_id=amb_user.id,
        program_kind="open_event",
        referral_code=f"C{tag.upper()[:8]}",
        display_name="Amb",
        email=amb_user.email,
        status="active",
        commission_rate_percent=Decimal("0"),
        terms_accepted_at=datetime.now(UTC),
        terms_version="1",
    )
    db.add(amb)
    db.commit()
    db.refresh(amb)
    return amb


def _paid_ticket_order(
    db: Session,
    *,
    event: Event,
    buyer: User,
    amb: Ambassador,
    qty: int,
    status: str = "paid",
) -> Order:
    unit = Decimal("5000")
    total = unit * qty
    order = Order(
        event_id=event.id,
        buyer_user_id=buyer.id,
        buyer_email=buyer.email,
        buyer_name=buyer.full_name,
        status=status,
        currency="NGN",
        subtotal_amount=total,
        discount_amount=Decimal("0"),
        total_amount=total,
        reference=f"ref-{uuid4().hex[:10]}",
        ambassador_id=amb.id,
        referral_code=amb.referral_code,
    )
    db.add(order)
    db.flush()
    db.add(
        OrderItem(
            order_id=order.id,
            item_kind="ticket",
            ticket_type_name="GA",
            quantity=qty,
            unit_price=unit,
            line_total=total,
        )
    )
    db.commit()
    order = db.get(Order, order.id)
    assert order is not None
    _ = list(order.items)
    return order


def test_compute_commission_variants():
    assert compute_commission_owed(
        commission_type="percentage",
        commission_value=Decimal("10"),
        applies_to="tickets",
        tickets_sold=2,
        merch_units=0,
        commissionable_revenue=Decimal("10000"),
        max_commission_per_order=None,
    ) == Decimal("1000.00")

    assert compute_commission_owed(
        commission_type="flat",
        commission_value=Decimal("200"),
        applies_to="tickets",
        tickets_sold=3,
        merch_units=0,
        commissionable_revenue=Decimal("15000"),
        max_commission_per_order=None,
    ) == Decimal("600.00")

    assert compute_commission_owed(
        commission_type="flat",
        commission_value=Decimal("500"),
        applies_to="merch",
        tickets_sold=0,
        merch_units=4,
        commissionable_revenue=Decimal("4000"),
        max_commission_per_order=None,
    ) == Decimal("500.00")

    assert compute_commission_owed(
        commission_type="reward_only",
        commission_value=Decimal("10"),
        applies_to="tickets",
        tickets_sold=2,
        merch_units=0,
        commissionable_revenue=Decimal("10000"),
        max_commission_per_order=None,
    ) == Decimal("0.00")

    assert compute_commission_owed(
        commission_type="percentage",
        commission_value=Decimal("50"),
        applies_to="tickets",
        tickets_sold=1,
        merch_units=0,
        commissionable_revenue=Decimal("10000"),
        max_commission_per_order=Decimal("100"),
    ) == Decimal("100.00")


def test_create_flat_campaign_and_attribute(
    client: TestClient, db_session: Session
):
    tag = uuid4().hex[:8]
    host, event, buyer, host_email = _seed(db_session, tag=tag)
    headers = _login(client, host_email)

    created = client.post(
        "/api/v1/promos/campaigns",
        headers=headers,
        json={
            "event_id": str(event.id),
            "name": "Flat tickets",
            "campaign_type": "event_tickets",
            "commission_type": "flat",
            "commission_value": "250",
            "applies_to": "tickets",
            "hold_period_days": 7,
            "free_ticket_after_sales": 2,
            "status": "public_open",
        },
    )
    assert created.status_code in {200, 201}, created.text
    body = created.json()
    assert body["commission_type"] == "flat"
    assert Decimal(body["commission_value"]) == Decimal("250.00")
    assert body["hold_period_days"] == 7

    campaign_id = UUID(body["id"])
    amb = _make_ambassador(
        db_session, host=host, event=event, campaign_id=campaign_id, tag=tag
    )

    order = _paid_ticket_order(
        db_session, event=event, buyer=buyer, amb=amb, qty=2
    )
    finalize_promo_and_attribution(db_session, order=order)
    db_session.commit()
    sale = db_session.scalar(
        select(AmbassadorSale).where(AmbassadorSale.order_id == order.id)
    )
    assert sale is not None
    assert sale.commission_owed == Decimal("500.00")
    assert sale.commission_type == "flat"
    assert sale.hold_until is not None
    assert sale.tickets_sold == 2

    # Duplicate finalize must not create a second sale.
    finalize_promo_and_attribution(db_session, order=order)
    db_session.commit()
    sales = list(
        db_session.scalars(
            select(AmbassadorSale).where(AmbassadorSale.order_id == order.id)
        )
    )
    assert len(sales) == 1

    # Pending order must not earn commission.
    pending = _paid_ticket_order(
        db_session, event=event, buyer=buyer, amb=amb, qty=1, status="pending"
    )
    finalize_promo_and_attribution(db_session, order=pending)
    db_session.commit()
    assert (
        db_session.scalar(
            select(AmbassadorSale).where(AmbassadorSale.order_id == pending.id)
        )
        is None
    )

    # Free ticket after 2 confirmed sales.
    order2 = _paid_ticket_order(
        db_session, event=event, buyer=buyer, amb=amb, qty=1
    )
    finalize_promo_and_attribution(db_session, order=order2)
    db_session.commit()
    db_session.refresh(amb)
    assert amb.free_ticket_earned_at is not None

    # Refund reverses commission idempotently.
    reverse_ambassador_sale_for_order(
        db_session, order_id=order.id, reason="Order refunded"
    )
    db_session.commit()
    db_session.refresh(sale)
    assert sale.status == "reversed"
    reverse_ambassador_sale_for_order(
        db_session, order_id=order.id, reason="Order refunded again"
    )
    db_session.commit()
    db_session.refresh(sale)
    assert sale.status == "reversed"
    assert sale.reversal_reason == "Order refunded"


def test_reward_only_campaign(client: TestClient, db_session: Session):
    tag = uuid4().hex[:8]
    host, event, buyer, host_email = _seed(db_session, tag=tag)
    headers = _login(client, host_email)

    created = client.post(
        "/api/v1/promos/campaigns",
        headers=headers,
        json={
            "event_id": str(event.id),
            "name": "Reward only",
            "campaign_type": "event_tickets",
            "commission_type": "reward_only",
            "commission_value": 0,
            "leaderboard_reward_enabled": True,
            "leaderboard_reward_description": "Top seller wins merch",
            "status": "public_open",
        },
    )
    assert created.status_code in {200, 201}, created.text
    assert created.json()["commission_type"] == "reward_only"
    assert created.json()["leaderboard_reward_enabled"] is True

    campaign = db_session.get(AmbassadorCampaign, UUID(created.json()["id"]))
    assert campaign is not None
    amb = _make_ambassador(
        db_session, host=host, event=event, campaign_id=campaign.id, tag=tag
    )

    order = _paid_ticket_order(
        db_session, event=event, buyer=buyer, amb=amb, qty=1
    )
    finalize_promo_and_attribution(db_session, order=order)
    db_session.commit()
    sale = db_session.scalar(
        select(AmbassadorSale).where(AmbassadorSale.order_id == order.id)
    )
    assert sale is not None
    assert sale.commission_owed == Decimal("0.00")
    assert sale.commission_type == "reward_only"
