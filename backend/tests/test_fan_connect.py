"""Fan Connect — opt-in, privacy, accept→thread, block."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.crm.models import HostFollower
from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostProfile
from app.messaging import service as messaging_svc
from app.payments.models import Order, OrderItem
from app.tickets.models import Ticket
from app.tickets.qr import new_public_ticket_code
from app.users.models import User
from app.users.service import get_role_by_name
from app.passport.service import ensure_passport


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


def _user(db_session: Session, email: str) -> User:
    return db_session.query(User).filter(User.email == email).one()


def _enable_connect(
    client: TestClient,
    headers: dict[str, str],
    *,
    discoverable: bool = True,
) -> None:
    r = client.patch(
        "/api/v1/fan-connect/settings",
        headers=headers,
        json={
            "fan_connect_enabled": True,
            "allow_connection_requests": True,
            "discoverable_for_same_events": discoverable,
            "discoverable_for_similar_interests": discoverable,
            "request_policy": "public_passports",
        },
    )
    assert r.status_code == 200, r.text


def _public_passport(
    db_session: Session, user: User, username: str, *, categories: list[str] | None = None
) -> None:
    p = ensure_passport(db_session, user)
    p.username = username
    p.visibility = "public"
    p.display_name = user.full_name or username
    p.appear_in_directory = True
    if categories is not None:
        p.favorite_categories = categories
    db_session.commit()


def _seed_host(db_session: Session, email: str = "fc-host@example.com") -> Host:
    user = User(
        email=email,
        password_hash=hash_password("securepass1"),
        full_name="FC Host",
        is_active=True,
    )
    user.roles.append(get_role_by_name(db_session, "host"))
    db_session.add(user)
    db_session.flush()
    host = Host(
        user_id=user.id,
        display_name="FC Host",
        slug=email.split("@")[0].replace(".", "-"),
        status="active",
    )
    db_session.add(host)
    db_session.flush()
    db_session.add(HostProfile(host_id=host.id, bio="Host", city="Lagos"))
    db_session.commit()
    return host


def _checked_in(
    db_session: Session,
    *,
    host: Host,
    buyer: User,
    slug: str,
    visibility: str = "listed",
    event_type: str = "public",
) -> Event:
    category = db_session.query(EventCategory).first()
    start = datetime.now(UTC) - timedelta(days=2)
    event = Event(
        title=f"Night {slug}",
        slug=slug,
        description="Public night used for Fan Connect shared context tests with enough text.",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=3),
        city="Lagos",
        venue_name="Public Hall",
        address="12 Secret Street",
        status="published",
        visibility=visibility,
        event_type=event_type,
        location_visibility="city_only",
        featured=False,
        published_at=start - timedelta(days=1),
    )
    db_session.add(event)
    db_session.flush()
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
    db_session.add(tt)
    db_session.flush()
    order = Order(
        reference=f"PDY-FC-{slug.upper()}-{uuid4().hex[:8]}",
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
    db_session.add(order)
    db_session.flush()
    item = OrderItem(
        order_id=order.id,
        ticket_type_id=tt.id,
        quantity=1,
        unit_price=Decimal("5000.00"),
        line_total=Decimal("5000.00"),
        ticket_type_name=tt.name,
    )
    db_session.add(item)
    db_session.flush()
    db_session.add(
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
    db_session.commit()
    return event


def _attend_existing(db_session: Session, *, host: Host, buyer: User, event: Event) -> None:
    tt = db_session.query(TicketType).filter(TicketType.event_id == event.id).one()
    order = Order(
        reference=f"PDY-FC-ATT-{uuid4().hex[:10]}",
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
    db_session.add(order)
    db_session.flush()
    item = OrderItem(
        order_id=order.id,
        ticket_type_id=tt.id,
        quantity=1,
        unit_price=Decimal("5000.00"),
        line_total=Decimal("5000.00"),
        ticket_type_name=tt.name,
    )
    db_session.add(item)
    db_session.flush()
    db_session.add(
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
    db_session.commit()


def test_settings_defaults_on(client: TestClient, db_session: Session):
    headers = _auth(client, "fc-defaults@example.com")
    r = client.get("/api/v1/fan-connect/settings", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["fan_connect_enabled"] is True
    assert data["discoverable_for_same_events"] is True
    assert data["discoverable_for_similar_interests"] is True
    assert data["allow_connection_requests"] is True
    assert data["show_shared_hosts"] is True
    assert data["show_public_city"] is True
    assert data["hide_private_events_always"] is True
    assert data["request_policy"] == "same_event"
    assert data["request_policies"] == ["same_event"]


def test_settings_request_policies_multi_select(
    client: TestClient, db_session: Session
):
    headers = _auth(client, "fc-multi-policy@example.com")
    r = client.patch(
        "/api/v1/fan-connect/settings",
        headers=headers,
        json={"request_policies": ["same_event", "same_host"]},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["request_policies"] == ["same_event", "same_host"]
    assert data["request_policy"] == "same_host"

    r = client.patch(
        "/api/v1/fan-connect/settings",
        headers=headers,
        json={"request_policies": ["nobody", "same_event"]},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["request_policies"] == ["nobody"]
    assert data["request_policy"] == "nobody"

    # Legacy single-field write still works.
    r = client.patch(
        "/api/v1/fan-connect/settings",
        headers=headers,
        json={"request_policy": "public_passports"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["request_policies"] == ["public_passports"]
    assert data["request_policy"] == "public_passports"


def test_cannot_request_without_shared_context(client: TestClient, db_session: Session):
    h_a = _auth(client, "fc-a@example.com", "Fan A")
    h_b = _auth(client, "fc-b@example.com", "Fan B")
    a = _user(db_session, "fc-a@example.com")
    b = _user(db_session, "fc-b@example.com")
    _public_passport(db_session, a, "fana")
    _public_passport(db_session, b, "fanb")
    _enable_connect(client, h_a)
    _enable_connect(client, h_b)

    r = client.post(
        "/api/v1/fan-connect/requests",
        headers=h_a,
        json={"username": "fanb", "message": "Hey!"},
    )
    assert r.status_code == 403
    detail = r.json()["detail"]
    assert "no_shared_public_context" in detail["denials"]


def test_private_events_never_in_shared_context(client: TestClient, db_session: Session):
    host = _seed_host(db_session, "fc-priv-host@example.com")
    h_a = _auth(client, "fc-priv-a@example.com", "Priv A")
    h_b = _auth(client, "fc-priv-b@example.com", "Priv B")
    a = _user(db_session, "fc-priv-a@example.com")
    b = _user(db_session, "fc-priv-b@example.com")
    _public_passport(db_session, a, "priva")
    _public_passport(db_session, b, "privb")
    _enable_connect(client, h_a)
    _enable_connect(client, h_b)

    ev = _checked_in(
        db_session,
        host=host,
        buyer=a,
        slug="secret-fc-night",
        visibility="unlisted",
        event_type="private",
    )
    _attend_existing(db_session, host=host, buyer=b, event=ev)

    r = client.get("/api/v1/fan-connect/can-connect/privb", headers=h_a)
    assert r.status_code == 200
    data = r.json()
    assert data["allowed"] is False
    assert "no_shared_public_context" in data["denials"]
    assert data["shared_context"]["events"] == []
    blob = str(data).lower()
    assert "secret street" not in blob


def test_accept_unlocks_thread_pre_accept_denied(client: TestClient, db_session: Session):
    host = _seed_host(db_session, "fc-ok-host@example.com")
    h_a = _auth(client, "fc-ok-a@example.com", "Ok A")
    h_b = _auth(client, "fc-ok-b@example.com", "Ok B")
    a = _user(db_session, "fc-ok-a@example.com")
    b = _user(db_session, "fc-ok-b@example.com")
    _public_passport(db_session, a, "oka", categories=["Afrobeats"])
    _public_passport(db_session, b, "okb", categories=["Afrobeats"])
    _enable_connect(client, h_a)
    _enable_connect(client, h_b)

    shared = _checked_in(db_session, host=host, buyer=a, slug="shared-fc-night")
    _attend_existing(db_session, host=host, buyer=b, event=shared)

    can = client.get("/api/v1/fan-connect/can-connect/okb", headers=h_a)
    assert can.status_code == 200
    assert can.json()["allowed"] is True
    assert can.json()["shared_context"]["events"]
    blob = str(can.json()).lower()
    assert "secret street" not in blob
    assert "@example.com" not in blob

    # Pre-accept: no fan_fan thread may be created, and send is impossible.
    from fastapi import HTTPException

    try:
        messaging_svc.ensure_fan_fan_thread(db_session, user_a=a.id, user_b=b.id)
        assert False, "expected Fan Connect gate"
    except HTTPException as exc:
        assert exc.status_code == 403

    req = client.post(
        "/api/v1/fan-connect/requests",
        headers=h_a,
        json={"username": "okb", "message": "Saw you at the same night"},
    )
    assert req.status_code == 200, req.text
    conn_id = req.json()["id"]

    acc = client.post(
        f"/api/v1/fan-connect/requests/{conn_id}/accept",
        headers=h_b,
    )
    assert acc.status_code == 200, acc.text
    assert acc.json()["status"] == "connected"
    thread_id = acc.json()["thread_id"]
    assert thread_id

    detail = client.get(f"/api/v1/messages/{thread_id}", headers=h_a)
    assert detail.status_code == 200, detail.text
    detail_body = detail.json()
    assert detail_body["thread_type"] == "fan_fan"
    assert detail_body["connect_context"]
    assert detail_body["connect_context"]["badge"] == "Fan Connect"
    assert detail_body["connect_context"]["context_label"]
    sys_msgs = [
        m
        for m in detail_body["messages"]
        if m["message_type"] == "system"
        and "You connected through" in m["body"]
    ]
    assert sys_msgs, "accept should post a Fan Connect system message"
    blob = str(detail_body).lower()
    assert "vip" not in blob
    assert "secret street" not in blob
    assert "@example.com" not in blob

    # Request notified recipient; accept notified requester — no private details.
    from app.messaging.models import InAppNotification

    req_notes = (
        db_session.query(InAppNotification)
        .filter(
            InAppNotification.user_id == b.id,
            InAppNotification.kind == "fan_connect.request",
        )
        .all()
    )
    assert req_notes
    assert "Fan Connect request" in req_notes[-1].title
    assert "secret street" not in (req_notes[-1].body or "").lower()

    acc_notes = (
        db_session.query(InAppNotification)
        .filter(
            InAppNotification.user_id == a.id,
            InAppNotification.kind == "fan_connect.accepted",
        )
        .all()
    )
    assert acc_notes
    assert "accepted your Fan Connect request" in acc_notes[-1].title

    send = client.post(
        f"/api/v1/messages/{thread_id}/send",
        headers=h_a,
        json={"body": "Glad we connected on Pàdéyá — my secret VIP code is X"},
    )
    assert send.status_code == 200, send.text

    msg_notes = (
        db_session.query(InAppNotification)
        .filter(
            InAppNotification.user_id == b.id,
            InAppNotification.kind == "fan_connect.message",
        )
        .all()
    )
    assert msg_notes
    # Attachment-safe generic copy (no message body / VIP / contact leakage).
    assert "new message" in msg_notes[-1].title.lower()
    assert "pàdéyá" in msg_notes[-1].body.lower()
    assert "message bodies are never sent" in msg_notes[-1].body.lower()
    assert "vip" not in msg_notes[-1].body.lower()
    assert "secret" not in msg_notes[-1].body.lower()

    inbox = client.get("/api/v1/messages", headers=h_b)
    assert inbox.status_code == 200
    items = inbox.json()["items"]
    ids = {i["id"] for i in items}
    assert str(thread_id) in ids
    fan_item = next(i for i in items if i["id"] == str(thread_id))
    assert fan_item["thread_type"] == "fan_fan"
    assert fan_item["connect_context"]["badge"] == "Fan Connect"

    notif_api = client.get("/api/v1/messages/notifications", headers=h_b)
    assert notif_api.status_code == 200
    kinds = {n["kind"] for n in notif_api.json()["items"]}
    assert "fan_connect.request" in kinds
    assert "fan_connect.message" in kinds


def test_block_stops_request_and_messaging(client: TestClient, db_session: Session):
    host = _seed_host(db_session, "fc-blk-host@example.com")
    h_a = _auth(client, "fc-blk-a@example.com", "Blk A")
    h_b = _auth(client, "fc-blk-b@example.com", "Blk B")
    a = _user(db_session, "fc-blk-a@example.com")
    b = _user(db_session, "fc-blk-b@example.com")
    _public_passport(db_session, a, "blka")
    _public_passport(db_session, b, "blkb")
    _enable_connect(client, h_a)
    _enable_connect(client, h_b)
    db_session.add(HostFollower(host_id=host.id, user_id=a.id))
    db_session.add(HostFollower(host_id=host.id, user_id=b.id))
    db_session.commit()

    req = client.post(
        "/api/v1/fan-connect/requests",
        headers=h_a,
        json={"username": "blkb"},
    )
    assert req.status_code == 200, req.text
    conn_id = req.json()["id"]

    block = client.post(
        "/api/v1/fan-connect/block",
        headers=h_b,
        json={"username": "blka"},
    )
    assert block.status_code == 204

    acc = client.post(
        f"/api/v1/fan-connect/requests/{conn_id}/accept",
        headers=h_b,
    )
    assert acc.status_code in {400, 403}

    can = client.get("/api/v1/fan-connect/can-connect/blkb", headers=h_a)
    assert can.status_code == 200
    assert can.json()["allowed"] is False
    dens = can.json()["denials"]
    assert "blocked" in dens or "connection_blocked" in dens


def test_decline_cooldown_blocks_rerequest(client: TestClient, db_session: Session):
    from app.fan_connect import constants as C
    from app.fan_connect.models import FanConnection

    host = _seed_host(db_session, "fc-cd-host@example.com")
    h_a = _auth(client, "fc-cd-a@example.com", "Cd A")
    h_b = _auth(client, "fc-cd-b@example.com", "Cd B")
    a = _user(db_session, "fc-cd-a@example.com")
    b = _user(db_session, "fc-cd-b@example.com")
    _public_passport(db_session, a, "cda", categories=["Afrobeats"])
    _public_passport(db_session, b, "cdb", categories=["Afrobeats"])
    _enable_connect(client, h_a)
    _enable_connect(client, h_b)
    shared = _checked_in(db_session, host=host, buyer=a, slug="cd-shared-night")
    _attend_existing(db_session, host=host, buyer=b, event=shared)

    req = client.post(
        "/api/v1/fan-connect/requests",
        headers=h_a,
        json={"username": "cdb"},
    )
    assert req.status_code == 200, req.text
    conn_id = req.json()["id"]

    dec = client.post(
        f"/api/v1/fan-connect/requests/{conn_id}/decline",
        headers=h_b,
    )
    assert dec.status_code == 200
    assert dec.json()["status"] == "declined"

    again = client.post(
        "/api/v1/fan-connect/requests",
        headers=h_a,
        json={"username": "cdb"},
    )
    assert again.status_code == 403
    assert "decline_cooldown" in again.json()["detail"]["denials"]

    can = client.get("/api/v1/fan-connect/can-connect/cdb", headers=h_a)
    assert can.status_code == 200
    assert can.json()["allowed"] is False
    assert "decline_cooldown" in can.json()["denials"]

    # After cooldown expires, request is allowed again
    conn = db_session.get(FanConnection, UUID(conn_id))
    assert conn is not None
    conn.requester_cooldown_until = datetime.now(UTC) - timedelta(minutes=1)
    db_session.commit()

    ok = client.post(
        "/api/v1/fan-connect/requests",
        headers=h_a,
        json={"username": "cdb"},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["status"] == "request_sent"


def test_remove_disables_messaging(client: TestClient, db_session: Session):
    host = _seed_host(db_session, "fc-rm-host@example.com")
    h_a = _auth(client, "fc-rm-a@example.com", "Rm A")
    h_b = _auth(client, "fc-rm-b@example.com", "Rm B")
    a = _user(db_session, "fc-rm-a@example.com")
    b = _user(db_session, "fc-rm-b@example.com")
    _public_passport(db_session, a, "rma", categories=["Afrobeats"])
    _public_passport(db_session, b, "rmb", categories=["Afrobeats"])
    _enable_connect(client, h_a)
    _enable_connect(client, h_b)
    shared = _checked_in(db_session, host=host, buyer=a, slug="rm-shared-night")
    _attend_existing(db_session, host=host, buyer=b, event=shared)

    req = client.post(
        "/api/v1/fan-connect/requests",
        headers=h_a,
        json={"username": "rmb"},
    )
    assert req.status_code == 200, req.text
    conn_id = req.json()["id"]
    acc = client.post(
        f"/api/v1/fan-connect/requests/{conn_id}/accept",
        headers=h_b,
    )
    assert acc.status_code == 200
    thread_id = acc.json()["thread_id"]

    send_ok = client.post(
        f"/api/v1/messages/{thread_id}/send",
        headers=h_a,
        json={"body": "Before remove"},
    )
    assert send_ok.status_code == 200

    rem = client.post(
        f"/api/v1/fan-connect/connections/{conn_id}/remove",
        headers=h_a,
    )
    assert rem.status_code == 200
    assert rem.json()["status"] == "removed"

    send_denied = client.post(
        f"/api/v1/messages/{thread_id}/send",
        headers=h_a,
        json={"body": "After remove"},
    )
    assert send_denied.status_code == 403


def test_report_fan_creates_row(client: TestClient, db_session: Session):
    from app.fan_connect.models import FanConnectionReport

    host = _seed_host(db_session, "fc-rp-host@example.com")
    h_a = _auth(client, "fc-rp-a@example.com", "Rp A")
    h_b = _auth(client, "fc-rp-b@example.com", "Rp B")
    a = _user(db_session, "fc-rp-a@example.com")
    b = _user(db_session, "fc-rp-b@example.com")
    _public_passport(db_session, a, "rpa")
    _public_passport(db_session, b, "rpb")
    _enable_connect(client, h_a)
    _enable_connect(client, h_b)
    db_session.add(HostFollower(host_id=host.id, user_id=a.id))
    db_session.add(HostFollower(host_id=host.id, user_id=b.id))
    db_session.commit()

    r = client.post(
        "/api/v1/fan-connect/report",
        headers=h_a,
        json={"username": "rpb", "reason": "Spam intro", "details": "Unwanted pitch"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "open"
    assert data["reason"] == "Spam intro"

    row = db_session.get(FanConnectionReport, UUID(data["id"]))
    assert row is not None
    assert row.reporter_user_id == a.id
    assert row.reported_user_id == b.id


def test_admin_resolve_report_and_disable_user(
    client: TestClient, db_session: Session, assign_role
):
    from app.fan_connect.models import FanConnectSettings, FanConnectionReport

    host = _seed_host(db_session, "fc-adm-host@example.com")
    h_a = _auth(client, "fc-adm-a@example.com", "Adm A")
    h_b = _auth(client, "fc-adm-b@example.com", "Adm B")
    h_admin = _auth(client, "fc-adm-admin@example.com", "Adm Admin")
    assign_role("fc-adm-admin@example.com", "super_admin")
    a = _user(db_session, "fc-adm-a@example.com")
    b = _user(db_session, "fc-adm-b@example.com")
    _public_passport(db_session, a, "adma")
    _public_passport(db_session, b, "admb")
    _enable_connect(client, h_a)
    _enable_connect(client, h_b)
    db_session.add(HostFollower(host_id=host.id, user_id=a.id))
    db_session.add(HostFollower(host_id=host.id, user_id=b.id))
    db_session.commit()

    reported = client.post(
        "/api/v1/fan-connect/report",
        headers=h_a,
        json={"username": "admb", "reason": "Harassment threat"},
    )
    assert reported.status_code == 200, reported.text
    report_id = reported.json()["id"]

    overview = client.get("/api/v1/admin/fan-connect/overview", headers=h_admin)
    assert overview.status_code == 200, overview.text
    assert overview.json()["open_reports"] >= 1

    listed = client.get("/api/v1/admin/fan-connect/reports", headers=h_admin)
    assert listed.status_code == 200, listed.text
    item = next(i for i in listed.json()["items"] if i["id"] == report_id)
    assert item["reported_user_id"] == str(b.id)
    assert item["reporter_user_id"] == str(a.id)
    assert "connection_context" in item
    assert "order" not in (item.get("details") or "").lower()
    assert "payment" not in str(item).lower()

    detail = client.get(
        f"/api/v1/admin/fan-connect/reports/{report_id}", headers=h_admin
    )
    assert detail.status_code == 200, detail.text
    assert detail.json()["reported_user_id"] == str(b.id)
    assert detail.json()["connection_context"] is not None

    history = client.get(
        f"/api/v1/admin/fan-connect/users/{b.id}/moderation", headers=h_admin
    )
    assert history.status_code == 200, history.text
    assert history.json()["fan_connect_enabled"] is True
    assert any(r["id"] == report_id for r in history.json()["reports_about"])

    resolved = client.post(
        f"/api/v1/admin/fan-connect/reports/{report_id}/resolve",
        headers=h_admin,
        json={"resolution": "resolved", "admin_notes": "Actioned"},
    )
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["status"] == "resolved"
    row = db_session.get(FanConnectionReport, UUID(report_id))
    assert row is not None and row.status == "resolved"

    disabled = client.post(
        f"/api/v1/admin/fan-connect/users/{b.id}/disable",
        headers=h_admin,
        json={"reason": "Serious report"},
    )
    assert disabled.status_code == 200, disabled.text
    assert disabled.json()["disabled"] is True
    db_session.expire_all()
    settings = (
        db_session.query(FanConnectSettings)
        .filter(FanConnectSettings.user_id == b.id)
        .one()
    )
    assert settings.fan_connect_enabled is False
    assert settings.allow_connection_requests is False

    history_after = client.get(
        f"/api/v1/admin/fan-connect/users/{b.id}/moderation", headers=h_admin
    )
    assert history_after.json()["fan_connect_enabled"] is False


def _own_passport_user(client: TestClient, db_session: Session):
    h = _auth(client, "self-fan@example.com", "Self Fan")
    user = _user(db_session, "self-fan@example.com")
    _public_passport(db_session, user, "selffan")
    _enable_connect(client, h)
    return h, user


def test_user_cannot_send_fan_connect_request_to_self(
    client: TestClient, db_session: Session
):
    from app.fan_connect import constants as C
    from app.fan_connect.eligibility import classify_fan_connect

    h, user = _own_passport_user(client, db_session)

    can = client.get("/api/v1/fan-connect/can-connect/selffan", headers=h)
    assert can.status_code == 200, can.text
    body = can.json()
    assert body["allowed"] is False
    assert "self" in body["denials"]
    assert body.get("message") == C.SELF_CONNECT_DETAIL

    pack = classify_fan_connect(db_session, actor=user, target=user)
    assert pack["allowed"] is False
    assert "self" in pack["denials"]

    req = client.post(
        "/api/v1/fan-connect/requests",
        headers=h,
        json={"username": "selffan", "message": "Hello me"},
    )
    assert req.status_code == 400, req.text
    assert req.json()["detail"] == C.SELF_CONNECT_DETAIL

    # Other fan is not denied as self.
    h_b = _auth(client, "other-fan@example.com", "Other Fan")
    other = _user(db_session, "other-fan@example.com")
    _public_passport(db_session, other, "otherfan")
    _enable_connect(client, h_b)
    can_other = client.get("/api/v1/fan-connect/can-connect/selffan", headers=h_b)
    assert can_other.status_code == 200, can_other.text
    assert "self" not in can_other.json().get("denials", [])


def test_user_cannot_create_fan_to_fan_message_thread_with_self(
    client: TestClient, db_session: Session
):
    from fastapi import HTTPException

    from app.messaging import constants as MC

    _, user = _own_passport_user(client, db_session)
    try:
        messaging_svc.ensure_fan_fan_thread(
            db_session, user_a=user.id, user_b=user.id, for_accept=True
        )
        raise AssertionError("expected self fan_fan block")
    except HTTPException as exc:
        assert exc.status_code == 400
        assert exc.detail == MC.SELF_MESSAGE_DETAIL


def test_user_cannot_report_self(client: TestClient, db_session: Session):
    from app.fan_connect import constants as C

    h, _ = _own_passport_user(client, db_session)
    report = client.post(
        "/api/v1/fan-connect/report",
        headers=h,
        json={"username": "selffan", "reason": "testing self"},
    )
    assert report.status_code == 400, report.text
    assert report.json()["detail"] == C.SELF_REPORT_DETAIL


def test_user_cannot_block_self(client: TestClient, db_session: Session):
    from app.fan_connect import constants as C
    from app.messaging import constants as MC

    h, user = _own_passport_user(client, db_session)
    block = client.post(
        "/api/v1/fan-connect/block",
        headers=h,
        json={"username": "selffan"},
    )
    assert block.status_code == 400, block.text
    assert block.json()["detail"] == C.SELF_BLOCK_DETAIL

    msg_block = client.post(
        "/api/v1/messages/block",
        headers=h,
        json={"blocked_user_id": str(user.id)},
    )
    assert msg_block.status_code == 400, msg_block.text
    assert msg_block.json()["detail"] == MC.SELF_BLOCK_DETAIL


def test_self_excluded_from_fan_connect_suggestions(
    client: TestClient, db_session: Session
):
    h, user = _own_passport_user(client, db_session)
    sug = client.get("/api/v1/fan-connect/suggestions", headers=h)
    assert sug.status_code == 200, sug.text
    for item in sug.json().get("items") or []:
        assert item.get("username") != "selffan"
        assert item.get("user_id") != str(user.id)


def test_self_not_counted_as_connection(client: TestClient, db_session: Session):
    from app.fan_connect import constants as C
    from app.fan_connect.models import FanConnection
    from app.passport.public_service import count_fan_connections

    _, user = _own_passport_user(client, db_session)
    db_session.add(
        FanConnection(
            user_low_id=user.id,
            user_high_id=user.id,
            requester_user_id=user.id,
            recipient_user_id=user.id,
            status=C.STATUS_CONNECTED,
        )
    )
    db_session.commit()
    assert count_fan_connections(db_session, user.id) == 0
