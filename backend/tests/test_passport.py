"""Fan Passport creation, attendance, and badge awarding tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.crm.models import HostFollower
from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostProfile
from app.passport.models import FanPassport, UserBadge
from app.payments.models import Order, OrderItem
from app.tickets.models import Ticket
from app.tickets.qr import new_public_ticket_code
from app.users.models import User
from app.users.service import get_role_by_name


def _register(client: TestClient, email: str, name: str = "Fan") -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass1", "full_name": name},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _seed_host(db: Session, *, email: str = "pp-host@example.com", slug: str = "pp-host") -> Host:
    host_user = User(
        email=email,
        password_hash=hash_password("securepass1"),
        full_name="Passport Host",
        is_active=True,
    )
    host_user.roles.append(get_role_by_name(db, "host"))
    db.add(host_user)
    db.flush()
    host = Host(
        user_id=host_user.id,
        display_name="Passport Host",
        slug=slug,
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, bio="Passport host"))
    db.commit()
    return host


def _seed_ticket(
    db: Session,
    *,
    host: Host,
    buyer: User,
    status: str = "active",
    ticket_kind: str = "regular",
    category_slug: str | None = "music",
    days_offset: int = 3,
    event_slug: str = "pp-event",
) -> Ticket:
    category = None
    if category_slug:
        category = db.query(EventCategory).filter_by(slug=category_slug).first()
    start = datetime.now(UTC) + timedelta(days=days_offset)
    if status == "checked_in":
        start = datetime.now(UTC) - timedelta(days=abs(days_offset))
    event = Event(
        title=f"Event {event_slug}",
        slug=event_slug,
        description="Passport test event with enough description text.",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=3),
        city="Lagos",
        status="completed" if status == "checked_in" else "published",
        featured=False,
        published_at=datetime.now(UTC) - timedelta(days=10),
    )
    db.add(event)
    db.flush()
    tt = TicketType(
        event_id=event.id,
        name=ticket_kind.upper(),
        type=ticket_kind,
        price=Decimal("5000.00"),
        quantity=100,
        quantity_sold=1,
        quantity_reserved=0,
        min_per_order=1,
        max_per_order=4,
        visibility="public",
        status="active",
    )
    db.add(tt)
    db.flush()
    order = Order(
        reference=f"PDY-PP-{event_slug.upper()}",
        buyer_user_id=buyer.id,
        event_id=event.id,
        status="paid",
        currency="NGN",
        subtotal_amount=Decimal("5000.00"),
        discount_amount=Decimal("0"),
        total_amount=Decimal("5000.00"),
        buyer_email=buyer.email,
        buyer_name=buyer.full_name,
        paid_at=datetime.now(UTC),
    )
    db.add(order)
    db.flush()
    item = OrderItem(
        order_id=order.id,
        ticket_type_id=tt.id,
        quantity=1,
        unit_price=Decimal("5000.00"),
        line_total=Decimal("5000.00"),
        ticket_type_name=tt.name,
    )
    db.add(item)
    db.flush()
    ticket = Ticket(
        public_code=new_public_ticket_code(),
        order_id=order.id,
        order_item_id=item.id,
        event_id=event.id,
        ticket_type_id=tt.id,
        buyer_user_id=buyer.id,
        status=status,
        ticket_type_name=tt.name,
        holder_name=buyer.full_name,
        holder_email=buyer.email,
        checked_in_at=datetime.now(UTC) if status == "checked_in" else None,
    )
    db.add(ticket)
    db.commit()
    return ticket


def test_passport_creation(client: TestClient, db_session: Session):
    headers = _register(client, "passport-new@example.com", "New Fan")
    # Registration provisions a passport before the first /passport/me read.
    assert db_session.query(FanPassport).count() == 1

    response = client.get("/api/v1/passport/me", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["display_name"] == "New Fan"
    assert body["tickets_bought"] == 0
    assert body["events_attended"] == 0
    assert db_session.query(FanPassport).count() == 1


def test_attendance_and_checked_in_counts(client: TestClient, db_session: Session):
    host = _seed_host(db_session)
    headers = _register(client, "attend@example.com", "Attendee")
    buyer = db_session.query(User).filter_by(email="attend@example.com").one()

    _seed_ticket(
        db_session,
        host=host,
        buyer=buyer,
        status="active",
        event_slug="upcoming-pp",
        days_offset=5,
    )
    _seed_ticket(
        db_session,
        host=host,
        buyer=buyer,
        status="checked_in",
        event_slug="attended-pp",
        days_offset=2,
    )
    refunded = _seed_ticket(
        db_session,
        host=host,
        buyer=buyer,
        status="active",
        event_slug="refunded-pp",
        days_offset=1,
    )
    refunded.status = "refunded"
    db_session.commit()

    passport = client.get("/api/v1/passport/me", headers=headers).json()
    assert passport["tickets_bought"] == 2
    assert passport["events_attended"] == 1
    assert len(passport["attended_events"]) == 1
    assert passport["attended_events"][0]["checked_in"] is True
    assert len(passport["upcoming_tickets"]) == 1


def test_badge_awarding_first_and_verified(client: TestClient, db_session: Session):
    host = _seed_host(db_session)
    headers = _register(client, "badges@example.com", "Badge Fan")
    buyer = db_session.query(User).filter_by(email="badges@example.com").one()

    _seed_ticket(
        db_session,
        host=host,
        buyer=buyer,
        status="checked_in",
        event_slug="badge-event",
    )

    badges = client.get("/api/v1/passport/me/badges", headers=headers).json()
    by_slug = {b["slug"]: b for b in badges}
    assert by_slug["first-ticket"]["earned"] is True
    assert by_slug["verified-attendee"]["earned"] is True
    assert db_session.query(UserBadge).filter_by(user_id=buyer.id).count() >= 2


def test_vip_regular_badge(client: TestClient, db_session: Session):
    host = _seed_host(db_session)
    headers = _register(client, "vipfan@example.com", "VIP Fan")
    buyer = db_session.query(User).filter_by(email="vipfan@example.com").one()

    _seed_ticket(
        db_session,
        host=host,
        buyer=buyer,
        status="active",
        ticket_kind="vip",
        event_slug="vip-one",
    )
    _seed_ticket(
        db_session,
        host=host,
        buyer=buyer,
        status="checked_in",
        ticket_kind="vvip",
        event_slug="vip-two",
        days_offset=4,
    )

    passport = client.get("/api/v1/passport/me", headers=headers).json()
    assert passport["vip_purchases"] == 2
    slugs = {b["slug"] for b in passport["badges_earned"]}
    assert "vip-regular" in slugs
    assert len(passport["vip_history"]) == 2


def test_superfan_badge_logic(client: TestClient, db_session: Session):
    host = _seed_host(db_session)
    headers = _register(client, "super@example.com", "Super Fan")
    buyer = db_session.query(User).filter_by(email="super@example.com").one()

    for i in range(3):
        _seed_ticket(
            db_session,
            host=host,
            buyer=buyer,
            status="checked_in",
            event_slug=f"sf-event-{i}",
            days_offset=i + 1,
        )

    passport = client.get("/api/v1/passport/me", headers=headers).json()
    assert passport["events_attended"] == 3
    assert passport["is_superfan"] is True
    assert any(b["slug"] == "superfan" for b in passport["badges_earned"])
    assert passport["loyalty"][0]["is_superfan"] is True
    assert passport["loyalty"][0]["check_ins"] == 3

    db_session.add(HostFollower(host_id=host.id, user_id=buyer.id, marketing_opt_in=False))
    db_session.commit()
    badges = client.get("/api/v1/passport/me/badges", headers=headers).json()
    assert next(b for b in badges if b["slug"] == "day-one-fan")["earned"] is True
