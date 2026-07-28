"""Paid buyers auto-follow the host with marketing notifications on."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.crm.buyer_follow import (
    backfill_buyer_follows,
    ensure_paid_order_buyer_follows_host,
)
from app.crm.models import HostFollower
from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostProfile
from app.payments.models import Order, OrderItem, Payment
from app.payments.webhook import finalize_successful_payment
from app.users.models import User
from app.users.service import get_role_by_name


def _seed_host_and_buyer(db: Session, *, tag: str) -> tuple[Host, User, Event, TicketType]:
    host_user = User(
        email=f"buyer-follow-host-{tag}@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Buyer Follow Host",
        is_active=True,
        is_verified=True,
    )
    role = get_role_by_name(db, "host")
    assert role is not None
    host_user.roles.append(role)
    db.add(host_user)
    db.flush()

    host = Host(
        user_id=host_user.id,
        display_name="Buyer Follow Host",
        slug=f"buyer-follow-host-{tag}",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, bio="Test"))

    buyer = User(
        email=f"buyer-follow-fan-{tag}@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Buyer Follow Fan",
        is_active=True,
        is_verified=True,
    )
    buyer_role = get_role_by_name(db, "buyer")
    assert buyer_role is not None
    buyer.roles.append(buyer_role)
    db.add(buyer)
    db.flush()

    category = db.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=5)
    event = Event(
        title=f"Buyer Follow Event {tag}",
        slug=f"buyer-follow-event-{tag}",
        description="Event for buyer auto-follow tests with enough detail.",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=3),
        city="Lagos",
        country="NG",
        venue_name="Test Hall",
        status="published",
        visibility="public",
    )
    db.add(event)
    db.flush()

    tt = TicketType(
        event_id=event.id,
        name="GA",
        type="general",
        price=Decimal("1000.00"),
        quantity=100,
        quantity_sold=0,
        quantity_reserved=1,
        status="active",
        visibility="public",
    )
    db.add(tt)
    db.commit()
    return host, buyer, event, tt


def test_ensure_paid_order_creates_follow_with_notify_on(db_session: Session):
    host, buyer, event, _tt = _seed_host_and_buyer(db_session, tag="a1")
    order = Order(
        reference="PDY-BF-A1",
        buyer_user_id=buyer.id,
        event_id=event.id,
        host_id=host.id,
        status="paid",
        currency="NGN",
        subtotal_amount=Decimal("1000.00"),
        total_amount=Decimal("1000.00"),
        paid_at=datetime.now(UTC),
        buyer_email=buyer.email,
        buyer_name=buyer.full_name,
    )
    db_session.add(order)
    db_session.commit()

    ensure_paid_order_buyer_follows_host(db_session, order)
    db_session.commit()

    row = db_session.scalar(
        select(HostFollower).where(
            HostFollower.host_id == host.id,
            HostFollower.user_id == buyer.id,
        )
    )
    assert row is not None
    assert row.marketing_opt_in is True


def test_ensure_paid_order_opts_in_existing_follower(db_session: Session):
    host, buyer, event, _tt = _seed_host_and_buyer(db_session, tag="a2")
    db_session.add(
        HostFollower(host_id=host.id, user_id=buyer.id, marketing_opt_in=False)
    )
    order = Order(
        reference="PDY-BF-A2",
        buyer_user_id=buyer.id,
        event_id=event.id,
        host_id=host.id,
        status="paid",
        currency="NGN",
        subtotal_amount=Decimal("1000.00"),
        total_amount=Decimal("1000.00"),
        paid_at=datetime.now(UTC),
        buyer_email=buyer.email,
        buyer_name=buyer.full_name,
    )
    db_session.add(order)
    db_session.commit()

    ensure_paid_order_buyer_follows_host(db_session, order)
    db_session.commit()

    row = db_session.scalar(
        select(HostFollower).where(
            HostFollower.host_id == host.id,
            HostFollower.user_id == buyer.id,
        )
    )
    assert row is not None
    assert row.marketing_opt_in is True


def test_finalize_payment_auto_follows_buyer(db_session: Session):
    host, buyer, event, tt = _seed_host_and_buyer(db_session, tag="a3")

    order = Order(
        reference="PDY-BF-A3",
        buyer_user_id=buyer.id,
        event_id=event.id,
        host_id=host.id,
        status="pending",
        currency="NGN",
        subtotal_amount=Decimal("1000.00"),
        total_amount=Decimal("1000.00"),
        buyer_email=buyer.email,
        buyer_name=buyer.full_name,
    )
    db_session.add(order)
    db_session.flush()
    db_session.add(
        OrderItem(
            order_id=order.id,
            item_kind="ticket",
            ticket_type_id=tt.id,
            quantity=1,
            unit_price=Decimal("1000.00"),
            line_total=Decimal("1000.00"),
            ticket_type_name="GA",
        )
    )
    payment = Payment(
        order_id=order.id,
        provider="paystack",
        reference=order.reference,
        amount=Decimal("1000.00"),
        currency="NGN",
        status="pending",
    )
    db_session.add(payment)
    db_session.commit()

    finalize_successful_payment(
        db_session,
        order=order,
        payment=payment,
        provider_payment_id="chg_bf_a3",
        raw_payload={"event": "charge.success"},
        actor_user_id=buyer.id,
    )
    db_session.commit()

    row = db_session.scalar(
        select(HostFollower).where(
            HostFollower.host_id == host.id,
            HostFollower.user_id == buyer.id,
        )
    )
    assert row is not None
    assert row.marketing_opt_in is True


def test_backfill_buyer_follows(db_session: Session):
    host, buyer, event, _tt = _seed_host_and_buyer(db_session, tag="a4")
    other = User(
        email="buyer-follow-other-a4@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Other Buyer",
        is_active=True,
        is_verified=True,
    )
    db_session.add(other)
    db_session.flush()
    db_session.add(
        HostFollower(host_id=host.id, user_id=other.id, marketing_opt_in=False)
    )
    db_session.add(
        Order(
            reference="PDY-BF-A4A",
            buyer_user_id=buyer.id,
            event_id=event.id,
            host_id=host.id,
            status="paid",
            currency="NGN",
            subtotal_amount=Decimal("1000.00"),
            total_amount=Decimal("1000.00"),
            paid_at=datetime.now(UTC),
            buyer_email=buyer.email,
            buyer_name=buyer.full_name,
        )
    )
    db_session.add(
        Order(
            reference="PDY-BF-A4B",
            buyer_user_id=other.id,
            event_id=event.id,
            host_id=host.id,
            status="paid",
            currency="NGN",
            subtotal_amount=Decimal("1000.00"),
            total_amount=Decimal("1000.00"),
            paid_at=datetime.now(UTC),
            buyer_email=other.email,
            buyer_name=other.full_name,
        )
    )
    db_session.commit()

    stats = backfill_buyer_follows(db_session)
    db_session.commit()
    assert stats["created"] >= 1
    assert stats["opted_in"] >= 1

    buyer_row = db_session.scalar(
        select(HostFollower).where(
            HostFollower.host_id == host.id,
            HostFollower.user_id == buyer.id,
        )
    )
    other_row = db_session.scalar(
        select(HostFollower).where(
            HostFollower.host_id == host.id,
            HostFollower.user_id == other.id,
        )
    )
    assert buyer_row is not None and buyer_row.marketing_opt_in is True
    assert other_row is not None and other_row.marketing_opt_in is True
