"""Event memory photo contributions: limits, ticket gate, optimization."""

from __future__ import annotations

import io
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.events.models import Event, TicketType
from app.hosts.models import Host, HostProfile
from app.memories.constants import FAN_MEMORY_PHOTO_LIMIT, HOST_MEMORY_PHOTO_LIMIT
from app.memories.image_processing import (
    process_memory_image,
    validate_external_gallery_url,
)
from app.memories.models import EventMemoryMedia
from app.tickets.models import Ticket
from app.tickets.qr import new_public_ticket_code
from app.users.models import User
from app.users.service import get_role_by_name


def _login(client: TestClient, email: str) -> dict[str, str]:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _png_bytes(color=(20, 120, 200), size=(1200, 800)) -> bytes:
    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _seed_host_event(
    db: Session,
    *,
    email: str,
    slug: str,
    status: str = "completed",
) -> tuple[Host, User, Event]:
    user = User(
        email=email,
        password_hash=hash_password("securepass1"),
        full_name="Photo Host",
        is_active=True,
    )
    user.roles.append(get_role_by_name(db, "host"))
    db.add(user)
    db.flush()
    host = Host(
        user_id=user.id,
        display_name="Photo Host",
        slug=slug,
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, bio="Photos"))
    start = datetime.now(UTC) - timedelta(days=2)
    event = Event(
        title="Photo Night",
        slug=f"{slug}-event",
        description="Completed event for memory photo contribution tests.",
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=4),
        venue_name="Hall",
        city="Lagos",
        status=status,
        visibility="listed",
        featured=False,
        published_at=start - timedelta(days=5),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return host, user, event


def _seed_fan_with_ticket(
    db: Session, event: Event, *, email: str
) -> tuple[User, Ticket]:
    from decimal import Decimal

    from app.payments.models import Order, OrderItem

    fan = User(
        email=email,
        password_hash=hash_password("securepass1"),
        full_name="Fan Guest",
        is_active=True,
    )
    fan.roles.append(get_role_by_name(db, "buyer"))
    db.add(fan)
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
        reference=f"PDY-MEM-{email.split('@')[0].upper()}",
        buyer_user_id=fan.id,
        event_id=event.id,
        status="paid",
        currency="NGN",
        subtotal_amount=Decimal("5000.00"),
        discount_amount=Decimal("0"),
        total_amount=Decimal("5000.00"),
        buyer_email=fan.email,
        buyer_name=fan.full_name,
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
        buyer_user_id=fan.id,
        status="active",
        ticket_type_name=tt.name,
        holder_name=fan.full_name,
        holder_email=fan.email,
    )
    db.add(ticket)
    db.commit()
    return fan, ticket


def test_process_memory_image_strips_and_resizes():
    raw = _png_bytes(size=(3000, 2000))
    processed = process_memory_image(
        data=raw,
        declared_content_type="image/png",
        event_id=uuid4(),
    )
    assert processed.mime_type == "image/webp"
    assert processed.width <= 1800
    assert processed.height <= 1800
    assert processed.size_bytes < processed.original_bytes
    assert processed.thumbnail_url
    assert processed.display_key.startswith("memories/events/")
    assert "/thumbs/" in processed.thumbnail_key


def test_external_gallery_url_rejects_javascript():
    with pytest.raises(ValueError):
        validate_external_gallery_url("javascript:alert(1)")
    assert validate_external_gallery_url("https://instagram.com/x")


def test_host_photo_limit(
    client: TestClient, db_session: Session
):
    host, host_user, event = _seed_host_event(
        db_session, email="photo-host@example.com", slug="photo-host"
    )
    headers = _login(client, host_user.email)
    png = _png_bytes()

    for i in range(HOST_MEMORY_PHOTO_LIMIT):
        resp = client.post(
            f"/api/v1/memories/host/events/{event.id}/photos",
            headers=headers,
            files={"file": (f"m{i}.png", png, "image/png")},
        )
        assert resp.status_code == 200, resp.text

    overflow = client.post(
        f"/api/v1/memories/host/events/{event.id}/photos",
        headers=headers,
        files={"file": ("overflow.png", png, "image/png")},
    )
    assert overflow.status_code == 400
    assert "limit" in overflow.json()["detail"].lower()

    album = client.get(f"/api/v1/memories/events/{event.slug}")
    assert album.status_code == 200
    body = album.json()
    assert body["counts"]["host_memory_count"] == HOST_MEMORY_PHOTO_LIMIT


def test_fan_requires_ticket_and_limit(
    client: TestClient, db_session: Session
):
    _, host_user, event = _seed_host_event(
        db_session, email="fan-gate-host@example.com", slug="fan-gate-host"
    )
    fan, _ticket = _seed_fan_with_ticket(
        db_session, event, email="fan-uploader@example.com"
    )
    stranger = User(
        email="stranger@example.com",
        password_hash=hash_password("securepass1"),
        full_name="No Ticket",
        is_active=True,
    )
    stranger.roles.append(get_role_by_name(db_session, "buyer"))
    db_session.add(stranger)
    db_session.commit()

    png = _png_bytes()
    blocked = client.post(
        f"/api/v1/memories/events/{event.id}/photos",
        headers=_login(client, stranger.email),
        files={"file": ("x.png", png, "image/png")},
    )
    assert blocked.status_code == 403

    fan_headers = _login(client, fan.email)
    for i in range(FAN_MEMORY_PHOTO_LIMIT):
        ok = client.post(
            f"/api/v1/memories/events/{event.id}/photos",
            headers=fan_headers,
            files={"file": (f"f{i}.png", png, "image/png")},
            data={"caption": f"shot {i}"},
        )
        assert ok.status_code == 200, ok.text

    sixth = client.post(
        f"/api/v1/memories/events/{event.id}/photos",
        headers=fan_headers,
        files={"file": ("f6.png", png, "image/png")},
    )
    assert sixth.status_code == 400

    album = client.get(f"/api/v1/memories/events/{event.slug}")
    assert album.status_code == 200
    community = album.json()["community_media"]
    assert len(community) == FAN_MEMORY_PHOTO_LIMIT
    # Private attribution fallback — no passport → Verified attendee flag
    assert community[0]["verified_attendee"] is True
    assert community[0].get("attribution") in (None, "")

    # Host hide
    host_headers = _login(client, host_user.email)
    media_id = community[0]["id"]
    hidden = client.post(
        f"/api/v1/memories/host/events/{event.id}/photos/{media_id}/moderate",
        headers=host_headers,
        json={"action": "hide"},
    )
    assert hidden.status_code == 200, hidden.text
    after = client.get(f"/api/v1/memories/events/{event.slug}")
    assert all(m["id"] != media_id for m in after.json()["community_media"])


def test_fan_before_event_start_rejected(
    client: TestClient, db_session: Session
):
    host, host_user, event = _seed_host_event(
        db_session,
        email="future-host@example.com",
        slug="future-host",
        status="published",
    )
    event.start_datetime = datetime.now(UTC) + timedelta(days=3)
    event.end_datetime = event.start_datetime + timedelta(hours=3)
    db_session.commit()
    fan, _ = _seed_fan_with_ticket(
        db_session, event, email="future-fan@example.com"
    )
    png = _png_bytes()
    resp = client.post(
        f"/api/v1/memories/events/{event.id}/photos",
        headers=_login(client, fan.email),
        files={"file": ("early.png", png, "image/png")},
    )
    assert resp.status_code == 400
    _ = host
    _ = host_user


def test_albums_list_and_completed_public_event(
    client: TestClient, db_session: Session
):
    _, host_user, event = _seed_host_event(
        db_session, email="album-host@example.com", slug="album-host"
    )
    headers = _login(client, host_user.email)
    png = _png_bytes()
    assert (
        client.post(
            f"/api/v1/memories/host/events/{event.id}/photos",
            headers=headers,
            files={"file": ("c.png", png, "image/png")},
        ).status_code
        == 200
    )

    albums = client.get("/api/v1/memories/albums")
    assert albums.status_code == 200
    slugs = [a["event_slug"] for a in albums.json()["items"]]
    assert event.slug in slugs

    # Completed event remains publicly reachable
    detail = client.get(f"/api/v1/events/{event.slug}")
    assert detail.status_code == 200
    assert detail.json()["status"] == "completed"

    count = db_session.query(EventMemoryMedia).count()
    assert count >= 1
