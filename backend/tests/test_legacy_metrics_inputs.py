"""Legacy metrics input collectors — repeat buyers and refund/dispute rate."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.events.models import Event, EventCategory, TicketType
from app.finance.models import Refund, RefundRequest
from app.hosts.models import Host, HostProfile
from app.legacy.metrics_inputs import (
    compute_refund_dispute_rate,
    compute_repeat_buyers_rate,
)
from app.legacy.scoring import ScoreInputs, compute_composite_score
from app.payments.models import Order, OrderItem
from app.tickets.models import Ticket
from app.tickets.qr import new_public_ticket_code
from app.users.models import User
from app.users.service import get_role_by_name


def _buyer(db: Session, email: str) -> User:
    user = User(
        email=email,
        password_hash=hash_password("securepass1"),
        full_name="Buyer",
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def _host(db: Session, slug: str) -> Host:
    owner = User(
        email=f"{slug}@host.example.com",
        password_hash=hash_password("securepass1"),
        full_name="Host Owner",
        is_active=True,
    )
    role = get_role_by_name(db, "host")
    assert role is not None
    owner.roles.append(role)
    db.add(owner)
    db.flush()
    host = Host(user_id=owner.id, display_name=slug, slug=slug, status="active")
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id))
    db.flush()
    return host


def _event(db: Session, host: Host, slug: str) -> Event:
    category = db.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=10)
    ev = Event(
        host_id=host.id,
        title=slug,
        slug=slug,
        description="test",
        category_id=category.id if category else None,
        start_datetime=start,
        end_datetime=start + timedelta(hours=3),
        city="Lagos",
        status="published",
        visibility="listed",
        published_at=start - timedelta(days=1),
    )
    db.add(ev)
    db.flush()
    tt = TicketType(
        event_id=ev.id,
        name="GA",
        type="regular",
        price=Decimal("1000.00"),
        quantity=100,
        quantity_sold=0,
        quantity_reserved=0,
        min_per_order=1,
        max_per_order=5,
        visibility="public",
        status="active",
    )
    db.add(tt)
    db.flush()
    return ev


def _paid_order(
    db: Session,
    *,
    host: Host,
    event: Event,
    buyer: User,
) -> Order:
    order = Order(
        reference=f"PDY-{event.slug}-{buyer.id}",
        event_id=event.id,
        host_id=host.id,
        buyer_user_id=buyer.id,
        status="paid",
        subtotal_amount=Decimal("1000.00"),
        total_amount=Decimal("1000.00"),
        currency="NGN",
        buyer_email=buyer.email,
        buyer_name=buyer.full_name,
        paid_at=datetime.now(UTC),
    )
    db.add(order)
    db.flush()
    tt = db.query(TicketType).filter_by(event_id=event.id).one()
    item = OrderItem(
        order_id=order.id,
        ticket_type_id=tt.id,
        quantity=1,
        unit_price=Decimal("1000.00"),
        line_total=Decimal("1000.00"),
        ticket_type_name="GA",
    )
    db.add(item)
    db.flush()
    db.add(
        Ticket(
            public_code=new_public_ticket_code(),
            order_id=order.id,
            order_item_id=item.id,
            event_id=event.id,
            ticket_type_id=tt.id,
            buyer_user_id=buyer.id,
            status="active",
            ticket_type_name="GA",
            holder_name=buyer.full_name,
            holder_email=buyer.email,
        )
    )
    db.flush()
    return order


def test_repeat_buyers_rate_none_without_orders(db_session: Session):
    host = _host(db_session, "repeat-none")
    assert compute_repeat_buyers_rate(db_session, host.id) is None


def test_repeat_buyers_rate_from_eligible_orders(db_session: Session):
    host = _host(db_session, "repeat-calc")
    a = _buyer(db_session, "buyer-a@example.com")
    b = _buyer(db_session, "buyer-b@example.com")
    e1 = _event(db_session, host, "repeat-ev-1")
    e2 = _event(db_session, host, "repeat-ev-2")
    _paid_order(db_session, host=host, event=e1, buyer=a)
    _paid_order(db_session, host=host, event=e2, buyer=a)
    _paid_order(db_session, host=host, event=e1, buyer=b)
    db_session.commit()

    rate = compute_repeat_buyers_rate(db_session, host.id)
    assert rate == Decimal("50.00")


def test_repeat_buyers_excludes_owner_orders(db_session: Session):
    host = _host(db_session, "repeat-owner")
    owner = db_session.get(User, host.user_id)
    assert owner is not None
    e1 = _event(db_session, host, "owner-ev-1")
    e2 = _event(db_session, host, "owner-ev-2")
    _paid_order(db_session, host=host, event=e1, buyer=owner)
    _paid_order(db_session, host=host, event=e2, buyer=owner)
    buyer = _buyer(db_session, "real-buyer@example.com")
    _paid_order(db_session, host=host, event=e1, buyer=buyer)
    db_session.commit()

    assert compute_repeat_buyers_rate(db_session, host.id) == Decimal("0.00")


def test_refund_rate_none_without_paid_orders(db_session: Session):
    host = _host(db_session, "refund-none")
    assert compute_refund_dispute_rate(db_session, host.id) is None


def test_refund_rate_zero_when_no_refunds(db_session: Session):
    host = _host(db_session, "refund-zero")
    buyer = _buyer(db_session, "refund-buyer@example.com")
    ev = _event(db_session, host, "refund-ev")
    _paid_order(db_session, host=host, event=ev, buyer=buyer)
    db_session.commit()

    assert compute_refund_dispute_rate(db_session, host.id) == Decimal("0.00")


def test_refund_rate_from_completed_refunds(db_session: Session):
    host = _host(db_session, "refund-calc")
    admin = _buyer(db_session, "refund-admin@example.com")
    buyer = _buyer(db_session, "refund-buyer2@example.com")
    ev = _event(db_session, host, "refund-ev-2")
    order = _paid_order(db_session, host=host, event=ev, buyer=buyer)
    req = RefundRequest(
        order_id=order.id,
        buyer_user_id=buyer.id,
        host_id=host.id,
        event_id=ev.id,
        status="approved",
        refund_type="full",
        requested_amount=Decimal("1000"),
        currency="NGN",
        reason="test",
        policy_snapshot="flexible",
    )
    db_session.add(req)
    db_session.flush()
    db_session.add(
        Refund(
            refund_request_id=req.id,
            order_id=order.id,
            host_id=host.id,
            amount=Decimal("1000"),
            currency="NGN",
            status="completed",
            processed_by_user_id=admin.id,
        )
    )
    db_session.commit()

    assert compute_refund_dispute_rate(db_session, host.id) == Decimal("100.00")


def test_unknown_refund_uses_scoring_default_not_evidence(db_session: Session):
    host = _host(db_session, "refund-unknown")
    db_session.commit()
    inputs = ScoreInputs(
        average_verified_rating=None,
        review_count=0,
        completed_events=0,
        tickets_sold=0,
        verified_checkins=0,
        refund_dispute_rate=compute_refund_dispute_rate(db_session, host.id),
        events_hosted=0,
        followers=0,
        repeat_buyers_rate=compute_repeat_buyers_rate(db_session, host.id),
    )
    score, factors = compute_composite_score(inputs)
    assert inputs.refund_dispute_rate is None
    assert factors["refund_dispute_rate"] == Decimal("80.00")
    assert score == Decimal("8.00")
