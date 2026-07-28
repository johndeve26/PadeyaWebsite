"""Phase 6 helpers — event lifecycle, sales windows, reservation expiry."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostProfile
from app.users.models import User
from app.users.service import get_role_by_name
from tests.phase45.helpers import login, run_barriered  # noqa: F401

PHASE6_POSTGRES = os.environ.get("PHASE45_POSTGRES", "").strip() == "1"
ITERATIONS = int(
    os.environ.get(
        "PHASE6_ITERATIONS",
        os.environ.get("PHASE45_ITERATIONS", "20"),
    )
)


def create_user(
    db: Session,
    email: str,
    *,
    role: str = "buyer",
    name: str = "User",
) -> User:
    user = User(
        email=email.lower(),
        password_hash=hash_password("securepass1"),
        full_name=name,
        is_active=True,
        is_verified=True,
    )
    r = get_role_by_name(db, role)
    if r is not None:
        user.roles.append(r)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def seed_published_event(
    db: Session,
    *,
    price: str = "1000.00",
    qty: int = 10,
    capacity: int | None = None,
    status: str = "published",
    sale_start: datetime | None = None,
    sale_end: datetime | None = None,
    reservation_hold_minutes: int | None = 15,
    check_in_start: datetime | None = None,
    check_in_end: datetime | None = None,
    start_offset_hours: int = 48,
    end_offset_hours: int = 52,
    location_visibility: str = "full_public",
    address: str = "12 Admiralty Way",
    latitude: float | None = 6.4312,
    longitude: float | None = 3.4219,
) -> tuple[Event, TicketType, User, Host]:
    suffix = uuid4().hex[:10]
    host_user = create_user(
        db, f"p6-host-{suffix}@example.com", role="host", name="P6 Host"
    )
    host = Host(
        user_id=host_user.id,
        display_name="P6 Host",
        slug=f"p6-host-{suffix}",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, city="Lagos"))
    category = db.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(hours=start_offset_hours)
    end = datetime.now(UTC) + timedelta(hours=end_offset_hours)
    event = Event(
        title="Phase6 Event",
        slug=f"p6-{suffix}",
        description="Phase 6 lifecycle event with enough description text for validation.",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=end,
        venue_name="Arena",
        address=address,
        city="Lagos",
        state="Lagos",
        country="Nigeria",
        latitude=latitude,
        longitude=longitude,
        location_visibility=location_visibility,
        status=status,
        featured=False,
        published_at=datetime.now(UTC) if status == "published" else None,
        capacity=capacity,
        check_in_start_time=check_in_start,
        check_in_end_time=check_in_end,
        timezone="Africa/Lagos",
    )
    db.add(event)
    db.flush()
    tt = TicketType(
        event_id=event.id,
        name="GA",
        type="regular",
        description="GA",
        price=Decimal(price),
        quantity=qty,
        quantity_sold=0,
        quantity_reserved=0,
        min_per_order=1,
        max_per_order=10,
        visibility="public",
        status="active",
        sale_start=sale_start,
        sale_end=sale_end,
        reservation_hold_minutes=reservation_hold_minutes,
    )
    db.add(tt)
    db.commit()
    db.refresh(event)
    db.refresh(tt)
    return event, tt, host_user, host


def pending_order(
    client: TestClient,
    headers: dict[str, str],
    *,
    event_id,
    ticket_type_id,
    quantity: int = 1,
    buyer_email: str = "buyer@example.com",
) -> dict:
    res = client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "event_id": str(event_id),
            "buyer_email": buyer_email,
            "buyer_name": "Buyer",
            "items": [
                {
                    "ticket_type_id": str(ticket_type_id),
                    "quantity": quantity,
                    "item_kind": "ticket",
                }
            ],
        },
    )
    assert res.status_code in {200, 201}, res.text
    return res.json()
