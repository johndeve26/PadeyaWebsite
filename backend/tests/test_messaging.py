"""Privacy-first fan ↔ host messaging tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.crm.models import HostFollower
from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostProfile
from app.payments.models import Order, OrderItem
from app.tickets.models import Ticket
from app.tickets.qr import new_public_ticket_code
from app.users.models import User
from app.users.service import get_role_by_name

from tests.helpers.auth import register_json


def _auth(client: TestClient, email: str, name: str = "User") -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json=register_json(email=email, full_name=name),
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _seed_host(db: Session, *, email: str = "msg-host@example.com") -> Host:
    user = User(
        email=email,
        password_hash=hash_password("securepass1"),
        full_name="Message Host",
        is_active=True,
    )
    user.roles.append(get_role_by_name(db, "host"))
    db.add(user)
    db.flush()
    host = Host(
        user_id=user.id,
        display_name="Message Host",
        slug="message-host",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, bio="Host", city="Lagos"))
    db.commit()
    return host


def _follow(db: Session, *, fan: User, host: Host) -> None:
    db.add(HostFollower(host_id=host.id, user_id=fan.id))
    db.commit()


def _ticket(db: Session, *, host: Host, buyer: User, slug: str = "msg-night") -> Event:
    category = db.query(EventCategory).first()
    start = datetime.now(UTC) - timedelta(days=1)
    event = Event(
        title="Message Night",
        slug=slug,
        description="Event used for messaging relationship tests with enough text.",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=3),
        city="Lagos",
        venue_name="Hall",
        address="12 Secret Street",
        status="published",
        visibility="listed",
        event_type="public",
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
        reference=f"PDY-MSG-{slug.upper()}",
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


def test_fan_can_message_host_when_allowed(
    client: TestClient, db_session: Session
) -> None:
    host = _seed_host(db_session)
    fan_h = _auth(client, "msg-fan1@example.com", "Fan One")
    me = client.get("/api/v1/auth/me", headers=fan_h)
    fan = db_session.get(User, UUID(me.json()["id"]))
    assert fan is not None
    _follow(db_session, fan=fan, host=host)

    created = client.post(
        "/api/v1/messages/threads",
        headers=fan_h,
        json={
            "host_id": str(host.id),
            "body": "What time do doors open?",
            "subject": "Entry time",
        },
    )
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["counterpart"]["display_name"] == "Message Host"
    assert "email" not in str(body).lower() or "buyer_email" not in str(body)
    assert fan.email not in str(body)
    assert "Secret Street" not in str(body)
    # Public messaging payloads never expose order/payment/CRM fields
    for banned_key in (
        "related_order_id",
        "related_ticket_id",
        "buyer_email",
        "holder_email",
        "crm",
        "order_id",
        "payment_id",
        "address",
    ):
        assert banned_key not in body
    assert "privacy_reminder" in body
    assert "Pàdéyá" in body["privacy_reminder"]
    assert "WhatsApp" in body["privacy_reminder"]


def test_host_cannot_message_unrelated_fan(
    client: TestClient, db_session: Session
) -> None:
    host = _seed_host(db_session)
    host_login = client.post(
        "/api/v1/auth/login",
        json={"email": "msg-host@example.com", "password": "securepass1"},
    )
    host_h = {"Authorization": f"Bearer {host_login.json()['access_token']}"}
    fan_h = _auth(client, "msg-stranger@example.com", "Stranger")
    me = client.get("/api/v1/auth/me", headers=fan_h)
    fan_id = me.json()["id"]

    denied = client.post(
        "/api/v1/host/messages/threads",
        headers=host_h,
        json={"fan_user_id": fan_id, "body": "Hey random fan"},
    )
    assert denied.status_code == 403


def test_host_can_message_follower(
    client: TestClient, db_session: Session
) -> None:
    host = _seed_host(db_session)
    host_login = client.post(
        "/api/v1/auth/login",
        json={"email": "msg-host@example.com", "password": "securepass1"},
    )
    host_h = {"Authorization": f"Bearer {host_login.json()['access_token']}"}
    fan_h = _auth(client, "msg-follower@example.com", "Follower")
    me = client.get("/api/v1/auth/me", headers=fan_h)
    fan = db_session.get(User, UUID(me.json()["id"]))
    assert fan is not None
    _follow(db_session, fan=fan, host=host)

    ok = client.post(
        "/api/v1/host/messages/threads",
        headers=host_h,
        json={"fan_user_id": str(fan.id), "body": "Thanks for following!"},
    )
    assert ok.status_code == 200, ok.text


def test_user_cannot_read_others_thread(
    client: TestClient, db_session: Session
) -> None:
    host = _seed_host(db_session)
    a = _auth(client, "msg-a@example.com", "A")
    b = _auth(client, "msg-b@example.com", "B")
    me = client.get("/api/v1/auth/me", headers=a)
    fan = db_session.get(User, UUID(me.json()["id"]))
    assert fan is not None
    _follow(db_session, fan=fan, host=host)
    created = client.post(
        "/api/v1/messages/threads",
        headers=a,
        json={"host_id": str(host.id), "body": "Private to A"},
    )
    thread_id = created.json()["id"]
    assert client.get(f"/api/v1/messages/{thread_id}", headers=b).status_code == 404


def test_block_prevents_send(client: TestClient, db_session: Session) -> None:
    host = _seed_host(db_session)
    host_login = client.post(
        "/api/v1/auth/login",
        json={"email": "msg-host@example.com", "password": "securepass1"},
    )
    host_h = {"Authorization": f"Bearer {host_login.json()['access_token']}"}
    fan_h = _auth(client, "msg-block@example.com", "Block Fan")
    me = client.get("/api/v1/auth/me", headers=fan_h)
    fan = db_session.get(User, UUID(me.json()["id"]))
    assert fan is not None
    _follow(db_session, fan=fan, host=host)
    created = client.post(
        "/api/v1/messages/threads",
        headers=fan_h,
        json={"host_id": str(host.id), "body": "Hello host"},
    )
    thread_id = created.json()["id"]
    host_user_id = str(host.user_id)
    assert (
        client.post(
            "/api/v1/messages/block",
            headers=fan_h,
            json={"blocked_user_id": host_user_id, "reason": "spam"},
        ).status_code
        == 204
    )
    blocked = client.post(
        f"/api/v1/messages/{thread_id}/send",
        headers=fan_h,
        json={"body": "Still trying"},
    )
    assert blocked.status_code == 403


def test_report_and_admin_view(
    client: TestClient, db_session: Session, assign_role
) -> None:
    host = _seed_host(db_session)
    fan_h = _auth(client, "msg-report@example.com", "Report Fan")
    me = client.get("/api/v1/auth/me", headers=fan_h)
    fan = db_session.get(User, UUID(me.json()["id"]))
    assert fan is not None
    _follow(db_session, fan=fan, host=host)
    created = client.post(
        "/api/v1/messages/threads",
        headers=fan_h,
        json={"host_id": str(host.id), "body": "Please report this later"},
    )
    thread_id = created.json()["id"]
    report = client.post(
        f"/api/v1/messages/{thread_id}/report",
        headers=fan_h,
        json={"reason": "harassment", "details": "Demo report"},
    )
    assert report.status_code == 201

    admin_h = _auth(client, "msg-admin@example.com", "Admin")
    assign_role("msg-admin@example.com", "super_admin")
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "msg-admin@example.com", "password": "securepass1"},
    )
    admin_h = {"Authorization": f"Bearer {login.json()['access_token']}"}
    listed = client.get("/api/v1/admin/message-reports", headers=admin_h)
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1
    rid = listed.json()["items"][0]["id"]
    detail = client.get(f"/api/v1/admin/message-reports/{rid}", headers=admin_h)
    assert detail.status_code == 200
    blob = str(detail.json())
    assert "Secret Street" not in blob
    assert "5000" not in blob
    assert fan.email not in blob


def test_public_request_from_weak_relationship(
    client: TestClient, db_session: Session
) -> None:
    host = _seed_host(db_session, email="msg-host2@example.com")
    # Fix slug uniqueness for second host
    host.slug = "message-host-2"
    db_session.commit()
    fan_h = _auth(client, "msg-public@example.com", "Public Fan")
    created = client.post(
        "/api/v1/messages/threads",
        headers=fan_h,
        json={"host_id": str(host.id), "body": "Hi from the directory"},
    )
    assert created.status_code == 200, created.text
    assert created.json()["is_request"] is True or created.json()["status"] == "request"


def test_archived_still_readable(client: TestClient, db_session: Session) -> None:
    host = _seed_host(db_session, email="msg-host3@example.com")
    host.slug = "message-host-3"
    db_session.commit()
    fan_h = _auth(client, "msg-arch@example.com", "Arch Fan")
    me = client.get("/api/v1/auth/me", headers=fan_h)
    fan = db_session.get(User, UUID(me.json()["id"]))
    assert fan is not None
    _follow(db_session, fan=fan, host=host)
    created = client.post(
        "/api/v1/messages/threads",
        headers=fan_h,
        json={"host_id": str(host.id), "body": "Archive me"},
    )
    thread_id = created.json()["id"]
    assert (
        client.patch(f"/api/v1/messages/{thread_id}/archive", headers=fan_h).status_code
        == 200
    )
    assert client.get(f"/api/v1/messages/{thread_id}", headers=fan_h).status_code == 200


def test_merch_order_item_context_on_thread(
    client: TestClient, db_session: Session
) -> None:
    host = _seed_host(db_session, email="msg-merch-host@example.com")
    host.slug = "message-merch-host"
    db_session.commit()
    fan_h = _auth(client, "msg-merch-fan@example.com", "Merch Fan")
    me = client.get("/api/v1/auth/me", headers=fan_h)
    fan = db_session.get(User, UUID(me.json()["id"]))
    assert fan is not None
    _follow(db_session, fan=fan, host=host)

    event = _ticket(db_session, host=host, buyer=fan, slug="msg-merch-night")
    order = Order(
        event_id=event.id,
        buyer_user_id=fan.id,
        buyer_name=fan.full_name,
        buyer_email=fan.email,
        status="paid",
        currency="NGN",
        subtotal_amount=Decimal("5000.00"),
        discount_amount=Decimal("0"),
        total_amount=Decimal("5000.00"),
        reference="MSG-MERCH-REF-1",
    )
    db_session.add(order)
    db_session.flush()
    item = OrderItem(
        order_id=order.id,
        item_kind="merch",
        quantity=1,
        unit_price=Decimal("5000.00"),
        line_total=Decimal("5000.00"),
        product_name="Neon Cap",
        variant_label="OS",
    )
    db_session.add(item)
    db_session.commit()

    created = client.post(
        "/api/v1/messages/threads",
        headers=fan_h,
        json={
            "host_id": str(host.id),
            "related_event_id": str(event.id),
            "related_merch_order_item_id": str(item.id),
            "body": "Where do I pick up the cap?",
            "subject": "Merch: Neon Cap",
        },
    )
    assert created.status_code == 200, created.text
    detail = created.json()
    assert fan.email not in str(detail)
    assert "Neon Cap" in str(detail.get("messages") or detail)
    messages = detail.get("messages") or []
    system = [
        m
        for m in messages
        if m.get("message_type") == "system"
        or "This conversation is about" in (m.get("body") or "")
    ]
    assert system
    assert "Neon Cap" in system[0]["body"]
    assert "@" not in system[0]["body"]
    assert "phone" not in system[0]["body"].lower()
