"""Phase 11: domain conversions only after verified payment."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ambassadors.payment import (
    finalize_ambassador_conversions,
    reverse_conversions_for_order,
)
from app.core.security import hash_password
from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostProfile
from app.payments.models import Order, OrderItem, Payment
from app.payments.webhook import finalize_successful_payment
from app.promos.ambassador_domain import (
    AmbassadorConversion,
    AmbassadorParticipant,
    AmbassadorProfile,
)
from app.promos.models import AmbassadorCampaign
from app.users.models import User
from app.users.service import get_role_by_name


def _login(client: TestClient, email: str) -> dict[str, str]:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _seed(db: Session, *, tag: str) -> tuple[str, Event, TicketType]:
    host_email = f"pay-host-{tag}@example.com"
    host_user = User(
        email=host_email,
        password_hash=hash_password("securepass1"),
        full_name="Pay Host",
        is_active=True,
    )
    role = get_role_by_name(db, "host")
    assert role is not None
    host_user.roles.append(role)
    db.add(host_user)
    db.flush()
    host = Host(
        user_id=host_user.id,
        display_name="Pay Host",
        slug=f"pay-host-{tag}",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, city="Lagos"))
    category = db.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=11)
    event = Event(
        title="Pay Amb Night",
        slug=f"pay-amb-night-{tag}",
        description="Payment integration",
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
    ga = TicketType(
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
    db.add(ga)
    db.commit()
    return host_email, event, ga


def test_conversion_only_after_verified_payment(
    client: TestClient, db_session: Session
):
    tag = uuid4().hex[:8]
    host_email, event, ga = _seed(db_session, tag=tag)
    host_h = _login(client, host_email)

    amb_email = f"pay-amb-{tag}@example.com"
    db_session.add(
        User(
            email=amb_email,
            password_hash=hash_password("securepass1"),
            full_name="Pay Amb",
            is_active=True,
        )
    )
    db_session.commit()
    amb_h = _login(client, amb_email)

    buyer_email = f"pay-buyer-{tag}@example.com"
    db_session.add(
        User(
            email=buyer_email,
            password_hash=hash_password("securepass1"),
            full_name="Pay Buyer",
            is_active=True,
        )
    )
    db_session.commit()
    buyer_h = _login(client, buyer_email)

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

    # Pending order stores participant — no conversion yet.
    order_resp = client.post(
        "/api/v1/orders",
        headers=buyer_h,
        json={
            "event_id": str(event.id),
            "items": [{"ticket_type_id": str(ga.id), "quantity": 2}],
            "referral_code": code,
            "referral_source": "cookie",
        },
    )
    assert order_resp.status_code == 201, order_resp.text
    order_id = order_resp.json()["id"]
    assert order_resp.json()["referral_code"] == code

    db_session.expire_all()
    order = db_session.scalar(
        select(Order).where(Order.reference == order_resp.json()["reference"])
    )
    assert order is not None
    assert order.ambassador_participant_id is not None
    assert order.status == "pending"
    assert (
        db_session.scalar(
            select(AmbassadorConversion).where(
                AmbassadorConversion.dedupe_key.like(f"ticket:{order.id}:%")
            )
        )
        is None
    )

    # Simulate verified Paystack finalize (backend only).
    payment = Payment(
        order_id=order.id,
        provider="paystack",
        reference=f"pay-{order.reference}",
        amount=order.total_amount,
        currency="NGN",
        status="pending",
    )
    db_session.add(payment)
    db_session.commit()
    db_session.refresh(order)
    db_session.refresh(payment)
    _ = list(order.items)
    _ = list(order.payments)

    finalize_successful_payment(
        db_session,
        order=order,
        payment=payment,
        provider_payment_id=f"psk_{tag}",
        raw_payload={"event": "charge.success"},
    )
    db_session.commit()
    db_session.expire_all()

    conversions = list(
        db_session.scalars(
            select(AmbassadorConversion).where(
                AmbassadorConversion.order_id == UUID(str(order_id))
            )
        )
    )
    assert len(conversions) == 1
    conv = conversions[0]
    assert conv.conversion_type == "ticket"
    assert conv.status == "approved"
    assert conv.verified_at is not None
    assert conv.commission_amount == Decimal("1000.00")  # 10% of 10000
    assert conv.dedupe_key.startswith("ticket:")
    assert str(order_id) in conv.dedupe_key
    assert campaign_id in conv.dedupe_key

    # Duplicate domain finalize must not create a second row.
    order = db_session.get(Order, UUID(str(order_id)))
    assert order is not None
    assert order.status == "paid"
    again = finalize_ambassador_conversions(db_session, order=order)
    db_session.commit()
    assert len(again) == 1
    count = len(
        list(
            db_session.scalars(
                select(AmbassadorConversion).where(
                    AmbassadorConversion.order_id == UUID(str(order_id))
                )
            )
        )
    )
    assert count == 1

    # Refund reverses conversion + audit.
    reverse_conversions_for_order(
        db_session,
        order_id=UUID(str(order_id)),
        reason="Order refunded",
        actor_user_id=order.buyer_user_id,
    )
    db_session.commit()
    db_session.refresh(conv)
    assert conv.status == "reversed"
    assert conv.refunded_at is not None

    reverse_conversions_for_order(
        db_session, order_id=UUID(str(order_id)), reason="again"
    )
    db_session.commit()
    db_session.refresh(conv)
    assert conv.status == "reversed"

    earnings = client.get("/api/v1/ambassadors/me/earnings", headers=amb_h)
    assert earnings.status_code == 200
    assert earnings.json()["confirmed_conversions"] == 0
    assert Decimal(earnings.json()["reversed_amount"]) == Decimal("1000.00")


def test_pending_order_never_creates_conversion(db_session: Session):
    tag = uuid4().hex[:8]
    _host_email, event, ga = _seed(db_session, tag=tag)
    amb = User(
        email=f"pend-amb-{tag}@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Pend Amb",
        is_active=True,
    )
    buyer = User(
        email=f"pend-buyer-{tag}@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Pend Buyer",
        is_active=True,
    )
    db_session.add_all([amb, buyer])
    db_session.flush()

    campaign = AmbassadorCampaign(
        host_id=event.host_id,
        event_id=event.id,
        name="Pending guard",
        status="active",
        visibility="public_open",
        source="host",
        campaign_type="event",
        commission_type="percentage",
        commission_value=Decimal("5"),
        commission_percent=Decimal("5"),
        applies_to="tickets",
        hold_period_days=7,
        cookie_window_days=30,
        merch_included=False,
    )
    db_session.add(campaign)
    db_session.flush()
    profile = AmbassadorProfile(user_id=amb.id, status="active")
    db_session.add(profile)
    db_session.flush()
    participant = AmbassadorParticipant(
        campaign_id=campaign.id,
        ambassador_profile_id=profile.id,
        user_id=amb.id,
        ambassador_code=f"pend{tag[:6]}",
        status="active",
    )
    db_session.add(participant)
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
        ambassador_participant_id=participant.id,
        referral_code=participant.ambassador_code,
    )
    db_session.add(order)
    db_session.flush()
    db_session.add(
        OrderItem(
            order_id=order.id,
            item_kind="ticket",
            ticket_type_id=ga.id,
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

    created = finalize_ambassador_conversions(db_session, order=order)
    db_session.commit()
    assert created == []
    assert (
        db_session.scalar(
            select(AmbassadorConversion).where(
                AmbassadorConversion.order_id == order.id
            )
        )
        is None
    )
