"""Extra Event Memories coverage: wrong-event ticket, unauth, privacy, counts."""

from __future__ import annotations

import io
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.events.models import Event, TicketType
from app.hosts.models import Host, HostProfile
from app.memories.image_processing import process_memory_image
from app.memories.models import EventMemoryMedia
from app.payments.models import Order, OrderItem
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


def _png(size=(2400, 1600), color=(40, 90, 160)) -> bytes:
    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


def _seed_host_event(
    db: Session, *, email: str, slug: str, title: str = "Night"
) -> tuple[Host, User, Event]:
    user = User(
        email=email,
        password_hash=hash_password("securepass1"),
        full_name="Host",
        is_active=True,
    )
    user.roles.append(get_role_by_name(db, "host"))
    db.add(user)
    db.flush()
    host = Host(
        user_id=user.id, display_name="Host", slug=slug, status="active"
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, bio="x"))
    start = datetime.now(UTC) - timedelta(days=1)
    event = Event(
        title=title,
        slug=f"{slug}-evt",
        description="Completed event for memory eligibility tests on Pàdéyá.",
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=3),
        venue_name="Hall",
        city="Lagos",
        status="completed",
        visibility="listed",
        featured=False,
        published_at=start - timedelta(days=3),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return host, user, event


def _ticket_for(db: Session, event: Event, fan: User) -> Ticket:
    tt = TicketType(
        event_id=event.id,
        name="GA",
        type="regular",
        price=Decimal("2000.00"),
        quantity=50,
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
        reference=f"PDY-M-{uuid4().hex[:8].upper()}",
        buyer_user_id=fan.id,
        event_id=event.id,
        status="paid",
        currency="NGN",
        subtotal_amount=Decimal("2000.00"),
        discount_amount=Decimal("0"),
        total_amount=Decimal("2000.00"),
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
        unit_price=Decimal("2000.00"),
        line_total=Decimal("2000.00"),
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
    return ticket


def _fan(db: Session, email: str) -> User:
    user = User(
        email=email,
        password_hash=hash_password("securepass1"),
        full_name="Fan",
        is_active=True,
    )
    user.roles.append(get_role_by_name(db, "buyer"))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_unauthenticated_upload_rejected(client: TestClient, db_session: Session):
    _, _, event = _seed_host_event(
        db_session, email="unauth-host@example.com", slug="unauth-host"
    )
    resp = client.post(
        f"/api/v1/memories/events/{event.id}/photos",
        files={"file": ("x.jpg", _png(size=(200, 200)), "image/jpeg")},
    )
    assert resp.status_code in {401, 403}


def test_wrong_event_ticket_rejected(client: TestClient, db_session: Session):
    _, _, event_a = _seed_host_event(
        db_session, email="wa-host@example.com", slug="wa-host", title="A"
    )
    _, _, event_b = _seed_host_event(
        db_session, email="wb-host@example.com", slug="wb-host", title="B"
    )
    fan = _fan(db_session, "wrong-evt-fan@example.com")
    _ticket_for(db_session, event_a, fan)

    resp = client.post(
        f"/api/v1/memories/events/{event_b.id}/photos",
        headers=_login(client, fan.email),
        files={"file": ("x.jpg", _png(size=(400, 400)), "image/jpeg")},
    )
    assert resp.status_code == 403


def test_image_optimization_measurements_and_rejects(
    client: TestClient, db_session: Session
):
    raw = _png(size=(2400, 1600))
    processed = process_memory_image(
        data=raw,
        declared_content_type="image/jpeg",
        event_id=uuid4(),
    )
    # Report real measurements (assert qualities, not exact KB)
    assert processed.original_bytes == len(raw)
    assert processed.width <= 1800
    assert processed.height <= 1800
    assert processed.mime_type == "image/webp"
    assert processed.size_bytes < processed.original_bytes
    assert processed.size_bytes > 0
    print(
        f"\nImage optimization: input={processed.original_bytes}B "
        f"2400x1600 → stored={processed.size_bytes}B "
        f"{processed.width}x{processed.height} {processed.mime_type}"
    )

    # Corrupt
    from app.memories.image_processing import MemoryImageError
    import pytest

    with pytest.raises(MemoryImageError):
        process_memory_image(
            data=b"not-an-image",
            declared_content_type="image/jpeg",
            event_id=uuid4(),
        )

    # MIME spoof: PNG header declared as jpeg
    png = Image.new("RGB", (100, 100), (1, 2, 3))
    buf = io.BytesIO()
    png.save(buf, format="PNG")
    with pytest.raises(MemoryImageError):
        process_memory_image(
            data=buf.getvalue(),
            declared_content_type="image/jpeg",
            event_id=uuid4(),
        )

    # Oversized raw
    with pytest.raises(MemoryImageError):
        process_memory_image(
            data=b"\xff\xd8\xff" + b"0" * (11 * 1024 * 1024),
            declared_content_type="image/jpeg",
            event_id=uuid4(),
        )


def test_external_url_and_host_hide_counts(client: TestClient, db_session: Session):
    from app.memories.image_processing import validate_external_gallery_url
    import pytest

    assert validate_external_gallery_url("https://example.com/gallery")
    assert validate_external_gallery_url("http://example.com/g")
    with pytest.raises(ValueError):
        validate_external_gallery_url("javascript:alert(1)")
    with pytest.raises(ValueError):
        validate_external_gallery_url("data:text/html,hi")

    _, host_user, event = _seed_host_event(
        db_session, email="hide-host@example.com", slug="hide-host"
    )
    fan = _fan(db_session, "hide-fan@example.com")
    _ticket_for(db_session, event, fan)
    host_h = _login(client, host_user.email)
    fan_h = _login(client, fan.email)
    png = _png(size=(600, 400))

    assert (
        client.post(
            f"/api/v1/memories/host/events/{event.id}/photos",
            headers=host_h,
            files={"file": ("h.jpg", png, "image/jpeg")},
        ).status_code
        == 200
    )
    fan_up = client.post(
        f"/api/v1/memories/events/{event.id}/photos",
        headers=fan_h,
        files={"file": ("f.jpg", png, "image/jpeg")},
        data={"caption": "hi"},
    )
    assert fan_up.status_code == 200, fan_up.text
    album = client.get(f"/api/v1/memories/events/{event.slug}").json()
    assert album["counts"]["host_memory_count"] == 1
    assert album["counts"]["community_memory_count"] == 1
    assert album["counts"]["memory_count"] == 2
    assert album["counts"]["contributor_count"] == 1

    media_id = album["community_media"][0]["id"]
    assert (
        client.post(
            f"/api/v1/memories/host/events/{event.id}/photos/{media_id}/moderate",
            headers=host_h,
            json={"action": "hide"},
        ).status_code
        == 200
    )
    after = client.get(f"/api/v1/memories/events/{event.slug}").json()
    assert after["counts"]["community_memory_count"] == 0
    assert after["counts"]["memory_count"] == 1

    # Fan cannot patch host photo
    host_media_id = after["host_media"][0]["id"]
    deny = client.patch(
        f"/api/v1/memories/events/{event.id}/photos/{host_media_id}",
        headers=fan_h,
        json={"caption": "nope"},
    )
    assert deny.status_code == 403

    assert db_session.query(EventMemoryMedia).count() >= 2
