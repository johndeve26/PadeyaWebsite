"""Phase 3 auth/ownership personas and resource factories."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostProfile, HostTeamMember
from app.hosts.team_permissions import pack_scope_json, permissions_for_role
from app.payments.models import Order, OrderItem
from app.tickets.models import Ticket
from app.tickets.qr import new_public_ticket_code
from app.users.models import User
from app.users.service import get_role_by_name
from tests.helpers.auth import register_json


PASSWORD = "securepass1"


@dataclass
class Persona:
    email: str
    user_id: str
    headers: dict[str, str]
    full_name: str


@dataclass
class HostBundle:
    persona: Persona
    host: Host
    event: Event
    ticket_type: TicketType


@dataclass
class OrderBundle:
    order: Order
    ticket: Ticket | None
    buyer: Persona


def register_persona(
    client: TestClient,
    *,
    email: str,
    full_name: str,
    assign_role=None,
    role: str | None = None,
) -> Persona:
    reg = client.post(
        "/api/v1/auth/register",
        json=register_json(email=email, password=PASSWORD, full_name=full_name),
    )
    assert reg.status_code in {200, 201}, reg.text
    if assign_role is not None and role is not None:
        assign_role(email, role)
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200, me.text
    return Persona(
        email=email,
        user_id=me.json()["id"],
        headers={"Authorization": f"Bearer {token}"},
        full_name=full_name,
    )


def seed_host_with_event(
    db: Session,
    *,
    email: str,
    slug_suffix: str,
    title: str = "Phase3 Night",
    status: str = "published",
) -> tuple[User, Host, Event, TicketType]:
    user = User(
        email=email,
        password_hash=hash_password(PASSWORD),
        full_name=f"Host {slug_suffix}",
        is_active=True,
        is_verified=True,
    )
    role = get_role_by_name(db, "host")
    assert role is not None
    user.roles.append(role)
    db.add(user)
    db.flush()
    host = Host(
        user_id=user.id,
        display_name=f"Host {slug_suffix}",
        slug=f"p3-host-{slug_suffix}",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, city="Lagos"))
    category = db.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=10)
    event = Event(
        title=title,
        slug=f"p3-event-{slug_suffix}-{uuid4().hex[:6]}",
        description="Phase 3 ownership fixture event with enough description text.",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=3),
        venue_name="Arena",
        city="Lagos",
        state="Lagos",
        status=status,
        featured=False,
        published_at=datetime.now(UTC) if status == "published" else None,
    )
    db.add(event)
    db.flush()
    ticket_type = TicketType(
        event_id=event.id,
        name="General",
        type="regular",
        price=Decimal("1000.00"),
        quantity=100,
        quantity_sold=0,
        quantity_reserved=0,
        min_per_order=1,
        max_per_order=4,
        visibility="public",
        status="active",
    )
    db.add(ticket_type)
    db.commit()
    db.refresh(user)
    db.refresh(host)
    db.refresh(event)
    db.refresh(ticket_type)
    return user, host, event, ticket_type


def login_existing(client: TestClient, email: str) -> dict[str, str]:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def add_team_member(
    db: Session,
    *,
    host_id,
    email: str,
    client: TestClient,
    permission_overrides: dict[str, bool],
) -> dict[str, str]:
    headers = register_persona(
        client, email=email, full_name=f"Team {email.split('@')[0]}"
    ).headers
    user = db.query(User).filter(User.email == email.lower()).one()
    perms = permissions_for_role("viewer")
    perms.update(permission_overrides)
    db.add(
        HostTeamMember(
            host_id=host_id,
            user_id=user.id,
            role="viewer",
            role_label="Viewer",
            status="active",
            permissions_json=perms,
            scope_json=pack_scope_json("host_wide"),
            joined_at=datetime.now(UTC),
        )
    )
    db.commit()
    return headers


def seed_paid_order_with_ticket(
    db: Session,
    *,
    buyer: User,
    event: Event,
    ticket_type: TicketType,
    qty: int = 1,
) -> tuple[Order, Ticket]:
    unit = ticket_type.price
    total = unit * qty
    order = Order(
        buyer_user_id=buyer.id,
        buyer_email=buyer.email,
        buyer_name=buyer.full_name or "Buyer",
        event_id=event.id,
        host_id=event.host_id,
        status="paid",
        currency="NGN",
        subtotal_amount=total,
        discount_amount=Decimal("0"),
        total_amount=total,
        reference=f"PDY-P3-{uuid4().hex[:12].upper()}",
        paid_at=datetime.now(UTC),
    )
    db.add(order)
    db.flush()
    item = OrderItem(
        order_id=order.id,
        ticket_type_id=ticket_type.id,
        quantity=qty,
        unit_price=unit,
        line_total=total,
    )
    db.add(item)
    db.flush()
    ticket = Ticket(
        public_code=new_public_ticket_code(),
        order_id=order.id,
        order_item_id=item.id,
        event_id=event.id,
        ticket_type_id=ticket_type.id,
        buyer_user_id=buyer.id,
        status="active",
        ticket_type_name=ticket_type.name,
        holder_name=buyer.full_name or "Buyer",
        holder_email=buyer.email,
    )
    db.add(ticket)
    ticket_type.quantity_sold = (ticket_type.quantity_sold or 0) + qty
    db.commit()
    db.refresh(order)
    db.refresh(ticket)
    return order, ticket
