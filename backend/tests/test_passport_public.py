"""Public Fan Passport privacy and settings tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostProfile
from app.passport.models import FanPassport
from app.passport.privacy import VISIBILITY_PRIVATE, VISIBILITY_PUBLIC, VISIBILITY_UNLISTED
from app.payments.models import Order, OrderItem
from app.tickets.models import Ticket
from app.tickets.qr import new_public_ticket_code
from app.users.models import User
from app.users.service import get_role_by_name


def _auth(client: TestClient, email: str, name: str = "Fan") -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass1", "full_name": name},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _seed_host(db: Session) -> Host:
    host_user = User(
        email="pub-passport-host@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Pub Host",
        is_active=True,
    )
    host_user.roles.append(get_role_by_name(db, "host"))
    db.add(host_user)
    db.flush()
    host = Host(
        user_id=host_user.id,
        display_name="Pub Host",
        slug="pub-passport-host",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, bio="Host", city="Lagos"))
    db.commit()
    return host


def _seed_checked_in(
    db: Session,
    *,
    host: Host,
    buyer: User,
    event_slug: str,
    visibility: str = "listed",
    event_type: str = "public",
    location_visibility: str = "city_only",
    venue_name: str = "Secret Hall",
) -> Event:
    category = db.query(EventCategory).first()
    start = datetime.now(UTC) - timedelta(days=2)
    event = Event(
        title=f"Night {event_slug}",
        slug=event_slug,
        description="Passport privacy test event with enough description text.",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=3),
        city="Lagos",
        venue_name=venue_name,
        address="12 Hidden Street",
        status="published",
        visibility=visibility,
        event_type=event_type,
        location_visibility=location_visibility,
        featured=False,
        published_at=start - timedelta(days=1),
    )
    db.add(event)
    db.flush()
    tt = TicketType(
        event_id=event.id,
        name="GA",
        type="regular",
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
    db.add(
        Ticket(
            public_code=new_public_ticket_code(),
            order_id=order.id,
            order_item_id=item.id,
            event_id=event.id,
            ticket_type_id=tt.id,
            buyer_user_id=buyer.id,
            status="checked_in",
            ticket_type_name=tt.name,
            holder_name=buyer.full_name,
            holder_email=buyer.email,
            checked_in_at=datetime.now(UTC),
        )
    )
    db.commit()
    return event


def test_private_passport_not_public(client: TestClient, db_session: Session) -> None:
    headers = _auth(client, "private-pp@example.com", "Private Fan")
    me = client.get("/api/v1/passport/me", headers=headers)
    assert me.status_code == 200
    username = me.json()["username"]
    assert username
    assert me.json()["visibility"] == VISIBILITY_PRIVATE

    public = client.get(f"/api/v1/f/{username}")
    assert public.status_code == 404


def test_public_passport_loads_and_hides_secret_events(
    client: TestClient, db_session: Session
) -> None:
    host = _seed_host(db_session)
    headers = _auth(client, "public-pp@example.com", "Public Fan")
    me = client.get("/api/v1/passport/me", headers=headers)
    user_id = UUID(me.json()["user_id"])
    buyer = db_session.get(User, user_id)
    assert buyer is not None

    _seed_checked_in(db_session, host=host, buyer=buyer, event_slug="pp-public-night")
    _seed_checked_in(
        db_session,
        host=host,
        buyer=buyer,
        event_slug="pp-secret-night",
        event_type="secret_location",
        visibility="unlisted",
        venue_name="Ultra Secret Venue",
    )

    patch = client.patch(
        "/api/v1/dashboard/passport/settings",
        headers=headers,
        json={
            "username": "publicfan",
            "visibility": VISIBILITY_PUBLIC,
            "show_attended_events": True,
            "tagline": "Shareable nights",
        },
    )
    assert patch.status_code == 200
    assert patch.json()["visibility"] == VISIBILITY_PUBLIC

    page = client.get("/api/v1/f/publicfan")
    assert page.status_code == 200
    body = page.json()
    assert body["username"] == "publicfan"
    assert body["user_id"] == str(user_id)
    assert body["display_name"]
    titles = [e["title"] for e in body["attended_events"]]
    assert any("pp-public-night" in e["slug"] for e in body["attended_events"])
    assert not any("pp-secret-night" in e["slug"] for e in body["attended_events"])
    blob = str(body)
    assert "Ultra Secret Venue" not in blob
    assert "Hidden Street" not in blob
    assert "5000" not in blob
    for ev in body["attended_events"]:
        assert "ticket_type_name" not in ev
        assert "venue" not in ev


def test_unlisted_passport_loads_by_direct_link(
    client: TestClient, db_session: Session
) -> None:
    headers = _auth(client, "unlisted-pp@example.com", "Unlisted Fan")
    client.get("/api/v1/passport/me", headers=headers)
    patch = client.patch(
        "/api/v1/passport/me/settings",
        headers=headers,
        json={"username": "unlistedfan", "visibility": VISIBILITY_UNLISTED},
    )
    assert patch.status_code == 200
    page = client.get("/api/v1/f/unlistedfan")
    assert page.status_code == 200
    assert page.json()["visibility"] == VISIBILITY_UNLISTED


def test_settings_update_and_cannot_take_other_username(
    client: TestClient, db_session: Session
) -> None:
    a = _auth(client, "pp-a@example.com", "Fan A")
    b = _auth(client, "pp-b@example.com", "Fan B")
    client.get("/api/v1/passport/me", headers=a)
    client.get("/api/v1/passport/me", headers=b)
    assert (
        client.patch(
            "/api/v1/passport/me/settings",
            headers=a,
            json={"username": "sharedname"},
        ).status_code
        == 200
    )
    clash = client.patch(
        "/api/v1/passport/me/settings",
        headers=b,
        json={"username": "sharedname"},
    )
    assert clash.status_code == 409


def test_user_cannot_edit_another_passport(
    client: TestClient, db_session: Session
) -> None:
    a = _auth(client, "pp-owner@example.com", "Owner")
    b = _auth(client, "pp-other@example.com", "Other")
    client.get("/api/v1/passport/me", headers=a)
    client.patch(
        "/api/v1/passport/me/settings",
        headers=a,
        json={"username": "ownerfan", "display_name": "Owner Fan"},
    )
    # Other user updates only their own passport
    other = client.patch(
        "/api/v1/passport/me/settings",
        headers=b,
        json={"display_name": "Hijack Attempt"},
    )
    assert other.status_code == 200
    assert other.json()["display_name"] == "Hijack Attempt"
    owner = client.get("/api/v1/f/ownerfan")
    # Public + directory by default; other user's PATCH must not rewrite owner.
    assert owner.status_code == 200
    assert owner.json()["display_name"] == "Owner Fan"
    me_a = client.get("/api/v1/passport/me", headers=a)
    assert me_a.json()["display_name"] == "Owner Fan"
