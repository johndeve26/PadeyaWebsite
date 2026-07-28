"""Phase 5 helpers — ticket/check-in fixtures and Postgres race utilities."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostProfile
from app.payments.models import Order, OrderItem
from app.tickets.models import Ticket, TicketQrToken
from app.tickets.qr import create_signed_qr_payload, hash_jti, new_public_ticket_code, new_qr_jti
from app.users.models import User
from app.users.service import get_role_by_name
from tests.phase45.helpers import login, run_barriered  # noqa: F401


def create_user(
    db: Session,
    email: str,
    *,
    role: str = "buyer",
    name: str = "User",
    verified: bool = True,
) -> User:
    user = User(
        email=email.lower(),
        password_hash=hash_password("securepass1"),
        full_name=name,
        is_active=True,
        is_verified=verified,
    )
    r = get_role_by_name(db, role)
    if r is not None:
        user.roles.append(r)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def seed_event_with_ticket(
    db: Session,
    *,
    host_email: str | None = None,
    buyer_email: str | None = None,
    ticket_status: str = "active",
    event_status: str = "published",
    slug: str | None = None,
    rotating: bool = False,
) -> tuple[Event, Host, User, User, Ticket, str]:
    suffix = uuid4().hex[:10]
    host_email = host_email or f"p5-host-{suffix}@example.com"
    buyer_email = buyer_email or f"p5-buyer-{suffix}@example.com"

    host_user = create_user(db, host_email, role="host", name="P5 Host")
    host = Host(
        user_id=host_user.id,
        display_name="P5 Host",
        slug=f"p5-host-{suffix}",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, city="Lagos"))

    category = db.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(hours=2)
    event = Event(
        title="Phase5 Gate",
        slug=slug or f"p5-{suffix}",
        description="Phase 5 admission integrity event with enough description text.",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=4),
        venue_name="Arena",
        city="Lagos",
        state="Lagos",
        status=event_status,
        featured=False,
        published_at=datetime.now(UTC) if event_status == "published" else None,
    )
    db.add(event)
    db.flush()

    tt = TicketType(
        event_id=event.id,
        name="GA",
        type="regular",
        description="GA",
        price=Decimal("1000.00"),
        quantity=50,
        quantity_sold=1,
        quantity_reserved=0,
        min_per_order=1,
        max_per_order=10,
        visibility="public",
        status="active",
    )
    db.add(tt)
    db.flush()

    buyer = create_user(db, buyer_email, role="buyer", name="P5 Buyer")
    order = Order(
        reference=f"PDY-P5-{suffix.upper()}",
        buyer_user_id=buyer.id,
        event_id=event.id,
        status="paid",
        currency="NGN",
        subtotal_amount=Decimal("1000.00"),
        total_amount=Decimal("1000.00"),
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
        unit_price=Decimal("1000.00"),
        line_total=Decimal("1000.00"),
        ticket_type_name="GA",
    )
    db.add(item)
    db.flush()

    code = new_public_ticket_code()
    ticket = Ticket(
        public_code=code,
        order_id=order.id,
        order_item_id=item.id,
        event_id=event.id,
        ticket_type_id=tt.id,
        buyer_user_id=buyer.id,
        status=ticket_status,
        ticket_type_name="GA",
        holder_name=buyer.full_name,
        holder_email=buyer.email,
        qr_mode="rotating" if rotating else "static",
        checked_in_at=datetime.now(UTC) if ticket_status == "checked_in" else None,
    )
    db.add(ticket)
    db.flush()

    jti = new_qr_jti()
    expires_kwargs: dict = {"expires_days": 30}
    if rotating:
        expires_kwargs = {"expires_seconds": 90}
    signed = create_signed_qr_payload(
        public_code=code,
        event_id=event.id,
        jti=jti,
        rotation_version=1,
        **expires_kwargs,
    )
    db.add(
        TicketQrToken(
            ticket_id=ticket.id,
            jti_hash=hash_jti(jti),
            signed_payload=signed,
            expires_at=datetime.now(UTC)
            + (timedelta(seconds=90) if rotating else timedelta(days=30)),
            is_rotating=rotating,
            rotation_version=1,
        )
    )
    db.commit()
    db.refresh(ticket)
    return event, host, host_user, buyer, ticket, signed


def host_headers(client: TestClient, email: str) -> dict[str, str]:
    return login(client, email)


def scan(
    client: TestClient,
    headers: dict[str, str],
    *,
    event_id,
    qr_payload: str | None = None,
    public_code: str | None = None,
    session_id: str | None = None,
) -> dict:
    body: dict = {"event_id": str(event_id)}
    if qr_payload is not None:
        body["qr_payload"] = qr_payload
    if public_code is not None:
        body["public_code"] = public_code
    if session_id is not None:
        body["session_id"] = session_id
    res = client.post("/api/v1/checkins/scan", headers=headers, json=body)
    assert res.status_code == 200, res.text
    return res.json()
