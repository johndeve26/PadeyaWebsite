"""Phase 7 helpers — memory upload fixtures and concurrency utilities."""

from __future__ import annotations

import io
import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.events.models import Event
from app.hosts.models import Host, HostProfile
from app.memories.constants import FAN_MEMORY_PHOTO_LIMIT, HOST_MEMORY_PHOTO_LIMIT
from app.payments.models import Order, OrderItem
from app.tickets.models import Ticket
from app.tickets.qr import new_public_ticket_code
from app.users.models import User
from app.users.service import get_role_by_name
from tests.phase45.helpers import login, run_barriered

ITERATIONS = int(
    os.environ.get("PHASE7_ITERATIONS", os.environ.get("PHASE46_ITERATIONS", "20"))
)


def png_bytes(*, color=(20, 120, 200), size=(800, 600)) -> bytes:
    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def seed_memory_event(
    db: Session,
    *,
    email_prefix: str = "p7",
    status: str = "completed",
    started: bool = True,
) -> tuple[Host, User, Event]:
    suffix = uuid4().hex[:8]
    user = User(
        email=f"{email_prefix}-{suffix}@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Phase7 Host",
        is_active=True,
        is_verified=True,
    )
    role = get_role_by_name(db, "host")
    if role:
        user.roles.append(role)
    db.add(user)
    db.flush()
    host = Host(
        user_id=user.id,
        display_name="P7 Host",
        slug=f"p7-host-{suffix}",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, bio="Phase 7"))
    if started:
        start = datetime.now(UTC) - timedelta(days=1)
    else:
        start = datetime.now(UTC) + timedelta(days=3)
    event = Event(
        title="Phase7 Memory Event",
        slug=f"p7-event-{suffix}",
        description="Phase 7 memory audit event with enough description text.",
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


def seed_fan_with_ticket(db: Session, event: Event, *, email: str | None = None) -> tuple[User, Ticket]:
    fan = User(
        email=email or f"p7-fan-{uuid4().hex[:8]}@example.com",
        password_hash=hash_password("securepass1"),
        full_name="P7 Fan",
        is_active=True,
        is_verified=True,
    )
    buyer = get_role_by_name(db, "buyer")
    if buyer:
        fan.roles.append(buyer)
    db.add(fan)
    db.flush()
    from app.events.models import TicketType

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
        reference=f"PDY-P7-{uuid4().hex[:8].upper()}",
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


def upload_fan_photo(client: TestClient, headers: dict, event_id, png: bytes) -> int:
    return client.post(
        f"/api/v1/memories/events/{event_id}/photos",
        headers=headers,
        files={"file": ("p7.png", png, "image/png")},
    ).status_code


def upload_host_photo(client: TestClient, headers: dict, event_id, png: bytes) -> int:
    return client.post(
        f"/api/v1/memories/host/events/{event_id}/photos",
        headers=headers,
        files={"file": ("p7.png", png, "image/png")},
    ).status_code


__all__ = [
    "FAN_MEMORY_PHOTO_LIMIT",
    "HOST_MEMORY_PHOTO_LIMIT",
    "ITERATIONS",
    "login",
    "png_bytes",
    "run_barriered",
    "seed_fan_with_ticket",
    "seed_memory_event",
    "upload_fan_photo",
    "upload_host_photo",
]
