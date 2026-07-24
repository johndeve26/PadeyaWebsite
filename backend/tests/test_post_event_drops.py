"""Post-event merch drops — schedule, audience gates, checkout path."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostProfile
from app.merch.access import assert_buyer_can_purchase, buyer_eligible_for_product
from app.merch.models import EventMerchProduct, EventMerchVariant
from app.merch.post_event_drops import notify_post_event_drop_live
from app.messaging.models import InAppNotification
from app.payments.models import Order, OrderItem
from app.tickets.models import Ticket
from app.users.models import User
from app.users.service import get_role_by_name
import uuid


def _login(client: TestClient, email: str, password: str = "securepass1") -> dict[str, str]:
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _seed_ended_event(db: Session) -> tuple[User, Host, Event, TicketType, TicketType]:
    host_user = User(
        email="drop-host@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Drop Host",
        is_active=True,
    )
    role = get_role_by_name(db, "host")
    assert role is not None
    host_user.roles.append(role)
    db.add(host_user)
    db.flush()

    host = Host(
        user_id=host_user.id,
        display_name="Drop Host",
        slug="drop-host",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(
        HostProfile(
            host_id=host.id,
            city="Lagos",
            merch_storefront_enabled=True,
            merch_storefront_visibility="public",
        )
    )

    category = db.query(EventCategory).first()
    end = datetime.now(UTC) - timedelta(days=1)
    event = Event(
        title="Afrobeats Night Live",
        slug="afrobeats-night-live-drops",
        description="Ended event for post-event drop tests with enough detail.",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=end - timedelta(hours=4),
        end_datetime=end,
        venue_name="Yard",
        city="Lagos",
        state="Lagos",
        status="completed",
        featured=False,
        published_at=end - timedelta(days=10),
    )
    db.add(event)
    db.flush()

    ga = TicketType(
        event_id=event.id,
        name="GA",
        type="regular",
        description="Entry",
        price=Decimal("3000.00"),
        quantity=50,
        quantity_sold=0,
        quantity_reserved=0,
        min_per_order=1,
        max_per_order=5,
        visibility="public",
        status="active",
    )
    vip = TicketType(
        event_id=event.id,
        name="VIP",
        type="vip",
        description="VIP",
        price=Decimal("10000.00"),
        quantity=20,
        quantity_sold=0,
        quantity_reserved=0,
        min_per_order=1,
        max_per_order=2,
        visibility="public",
        status="active",
    )
    db.add(ga)
    db.add(vip)
    db.commit()
    db.refresh(host)
    db.refresh(event)
    return host_user, host, event, ga, vip


def _buyer(db: Session, email: str) -> User:
    user = User(
        email=email,
        password_hash=hash_password("securepass1"),
        full_name="Drop Buyer",
        is_active=True,
    )
    role = get_role_by_name(db, "buyer")
    if role is not None:
        user.roles.append(role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _add_ticket(
    db: Session,
    *,
    event: Event,
    ticket_type: TicketType,
    buyer: User,
    status: str = "active",
) -> Ticket:
    order = Order(
        reference=f"PDY-DROP-{uuid.uuid4().hex[:10].upper()}",
        buyer_user_id=buyer.id,
        event_id=event.id,
        status="paid",
        currency="NGN",
        subtotal_amount=ticket_type.price,
        total_amount=ticket_type.price,
        buyer_email=buyer.email,
        buyer_name=buyer.full_name,
        paid_at=datetime.now(UTC),
    )
    db.add(order)
    db.flush()
    item = OrderItem(
        order_id=order.id,
        ticket_type_id=ticket_type.id,
        quantity=1,
        unit_price=ticket_type.price,
        line_total=ticket_type.price,
        ticket_type_name=ticket_type.name,
    )
    db.add(item)
    db.flush()
    ticket = Ticket(
        public_code=f"T-{uuid.uuid4().hex[:12].upper()}",
        order_id=order.id,
        order_item_id=item.id,
        event_id=event.id,
        ticket_type_id=ticket_type.id,
        buyer_user_id=buyer.id,
        status=status,
        ticket_type_name=ticket_type.name,
        holder_name=buyer.full_name or "Buyer",
        holder_email=buyer.email,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def _make_drop(
    db: Session,
    *,
    event: Event,
    host: Host,
    name: str = "Recap Tee",
    post_event_drop_at: datetime | None = None,
    requires_ticket: bool = False,
    requires_vip: bool = False,
    requires_check_in: bool = False,
    status: str = "active",
) -> EventMerchProduct:
    product = EventMerchProduct(
        event_id=event.id,
        host_id=host.id,
        name=name,
        slug=name.lower().replace(" ", "-"),
        description="Recap souvenir",
        short_description="Recap souvenir",
        product_type="souvenir",
        base_price=Decimal("5000.00"),
        currency="NGN",
        status=status,
        is_event_linked=True,
        storefront_visibility="post_event_drop",
        post_event_drop_at=post_event_drop_at or (datetime.now(UTC) - timedelta(minutes=5)),
        requires_ticket=requires_ticket,
        requires_vip=requires_vip,
        requires_check_in=requires_check_in,
        required_access_type=(
            "vip_ticket_holder"
            if requires_vip
            else "checked_in_attendee"
            if requires_check_in
            else "ticket_holder"
            if requires_ticket
            else None
        ),
        moderation_status="clear",
        pickup_enabled=True,
        shipping_enabled=True,
    )
    db.add(product)
    db.flush()
    db.add(
        EventMerchVariant(
            product_id=product.id,
            label="M",
            inventory_count=10,
            reserved_quantity=0,
            sold_quantity=0,
            status="active",
        )
    )
    db.commit()
    db.refresh(product)
    return product


def test_drop_before_schedule_blocked(db_session: Session):
    _host_user, host, event, _ga, _vip = _seed_ended_event(db_session)
    buyer = _buyer(db_session, "early@example.com")
    product = _make_drop(
        db_session,
        event=event,
        host=host,
        post_event_drop_at=datetime.now(UTC) + timedelta(days=2),
        requires_ticket=True,
    )
    _add_ticket(db_session, event=event, ticket_type=_ga, buyer=buyer)

    ok, reason = buyer_eligible_for_product(
        db_session, product=product, buyer_user_id=buyer.id
    )
    assert ok is False
    assert reason == "drop_not_started"


def test_wrong_audience_blocked(db_session: Session):
    _host_user, host, event, ga, vip = _seed_ended_event(db_session)
    ga_buyer = _buyer(db_session, "ga@example.com")
    _add_ticket(db_session, event=event, ticket_type=ga, buyer=ga_buyer)

    vip_drop = _make_drop(
        db_session,
        event=event,
        host=host,
        name="VIP Recap",
        requires_vip=True,
    )
    ok, reason = buyer_eligible_for_product(
        db_session, product=vip_drop, buyer_user_id=ga_buyer.id
    )
    assert ok is False
    assert reason == "vip_ticket_required"

    checked_drop = _make_drop(
        db_session,
        event=event,
        host=host,
        name="Check-in Recap",
        requires_check_in=True,
    )
    ok2, reason2 = buyer_eligible_for_product(
        db_session, product=checked_drop, buyer_user_id=ga_buyer.id
    )
    assert ok2 is False
    assert reason2 == "check_in_required"


def test_eligible_buyer_can_pass_checkout_gate(db_session: Session):
    _host_user, host, event, ga, vip = _seed_ended_event(db_session)
    buyer = _buyer(db_session, "eligible@example.com")
    _add_ticket(db_session, event=event, ticket_type=ga, buyer=buyer)
    product = _make_drop(
        db_session,
        event=event,
        host=host,
        requires_ticket=True,
    )
    ok, reason = buyer_eligible_for_product(
        db_session, product=product, buyer_user_id=buyer.id
    )
    assert ok is True
    assert reason is None
    assert_buyer_can_purchase(db_session, product=product, buyer_user_id=buyer.id)

    vip_buyer = _buyer(db_session, "vip@example.com")
    _add_ticket(db_session, event=event, ticket_type=vip, buyer=vip_buyer)
    vip_drop = _make_drop(
        db_session,
        event=event,
        host=host,
        name="VIP Only Drop",
        requires_vip=True,
    )
    assert_buyer_can_purchase(
        db_session, product=vip_drop, buyer_user_id=vip_buyer.id
    )


def test_host_create_list_patch_drop(client: TestClient, db_session: Session):
    host_user, _host, event, _ga, _vip = _seed_ended_event(db_session)
    headers = _login(client, host_user.email)

    create = client.post(
        f"/api/v1/host/events/{event.id}/post-event-drops",
        headers=headers,
        json={
            "name": "Afterglow Tee",
            "base_price": "7500.00",
            "audience": "ticket_buyers",
            "drop_description": "Limited recap tee",
            "post_event_drop_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
            "status": "draft",
            "inventory_count": 25,
        },
    )
    assert create.status_code == 200, create.text
    body = create.json()
    assert body["storefront_visibility"] == "post_event_drop"
    assert body["audience"] == "ticket_buyers"
    assert body["requires_ticket"] is True
    assert body["is_drop_live"] is False
    product_id = body["id"]

    listed = client.get(
        f"/api/v1/host/events/{event.id}/post-event-drops",
        headers=headers,
    )
    assert listed.status_code == 200, listed.text
    assert len(listed.json()) == 1

    patched = client.patch(
        f"/api/v1/host/events/{event.id}/post-event-drops/{product_id}",
        headers=headers,
        json={
            "status": "active",
            "post_event_drop_at": (datetime.now(UTC) - timedelta(minutes=1)).isoformat(),
            "audience": "vip",
        },
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["requires_vip"] is True
    assert patched.json()["is_drop_live"] is True


def test_notify_drop_live_is_idempotent(db_session: Session):
    _host_user, host, event, ga, _vip = _seed_ended_event(db_session)
    buyer = _buyer(db_session, "notify@example.com")
    _add_ticket(db_session, event=event, ticket_type=ga, buyer=buyer)
    product = _make_drop(
        db_session,
        event=event,
        host=host,
        requires_ticket=True,
        status="active",
    )
    sent = notify_post_event_drop_live(db_session, product_id=product.id)
    assert sent == 1
    notes = (
        db_session.query(InAppNotification)
        .filter(
            InAppNotification.user_id == buyer.id,
            InAppNotification.kind == "merch.post_event_drop",
        )
        .all()
    )
    assert len(notes) == 1
    assert "Afrobeats Night Live" in notes[0].title
    assert "Ticket holders can now access the recap merch drop" in notes[0].body

    sent_again = notify_post_event_drop_live(db_session, product_id=product.id)
    assert sent_again == 0
