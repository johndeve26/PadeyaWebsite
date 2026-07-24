"""Phase 19 checklist — WS / attachments / privacy gaps not covered elsewhere.

Companion coverage lives in:
- test_messaging_realtime_attachments.py
- test_messaging_ws_permissions.py
- test_messaging_attachments_validate.py
- test_messaging_attachment_privacy.py
- test_messaging_ws_bus.py
- test_demo_messaging_privacy.py
"""

from __future__ import annotations

import concurrent.futures
import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.crm.models import HostFollower
from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostProfile
from app.messaging import constants as MC
from app.messaging import service as messaging_svc
from app.messaging.attachments import (
    ATT_STATUS_READY,
    ATT_STATUS_REJECTED,
    AttachmentLimits,
    AttachmentValidationError,
    validate_attachment_bytes,
)
from app.messaging.models import MessageAttachment, MessageThread
from app.messaging.ws_hub import MessagingHub
from app.payments.models import Order, OrderItem
from app.tickets.models import Ticket
from app.tickets.qr import new_public_ticket_code
from app.users.models import User
from app.users.service import get_role_by_name

_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0"
    b"\x00\x00\x03\x01\x01\x00\xc9\xfe\x92\xef\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _auth(client: TestClient, email: str, name: str = "User") -> tuple[dict[str, str], str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass1", "full_name": name},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, token


def _user(db: Session, email: str) -> User:
    return db.query(User).filter(User.email == email).one()


def _seed_host(db: Session, email: str) -> Host:
    user = User(
        email=email,
        password_hash=hash_password("securepass1"),
        full_name="P19 Host",
        is_active=True,
    )
    user.roles.append(get_role_by_name(db, "host"))
    db.add(user)
    db.flush()
    host = Host(
        user_id=user.id,
        display_name="P19 Host",
        slug="p19-host-" + uuid4().hex[:6],
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


def _open_thread(client: TestClient, fan_h: dict, host: Host) -> str:
    r = client.post(
        "/api/v1/messages/threads",
        headers=fan_h,
        json={"host_id": str(host.id), "body": "Hello from Pàdéyá"},
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _recv(ws, *, timeout: float = 2.0) -> dict | None:
    """Receive one WS JSON event without deadlocking the TestClient on timeout.

    ``ThreadPoolExecutor`` context-manager shutdown waits for the worker; a
    timed-out ``receive_json`` would hang forever. Always ``shutdown(wait=False)``.
    """
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    fut = pool.submit(ws.receive_json)
    try:
        return fut.result(timeout=timeout)
    except Exception:
        return None
    finally:
        pool.shutdown(wait=False, cancel_futures=True)


def _drain_until(ws, typ: str, *, limit: int = 14, timeout: float = 2.0):
    for _ in range(limit):
        evt = _recv(ws, timeout=timeout)
        if evt is None:
            break
        if evt.get("type") == typ:
            return evt
    raise AssertionError(f"did not receive {typ}")


def _collect_types(ws, *, seconds: float = 1.5, limit: int = 20) -> list[dict]:
    out: list[dict] = []
    deadline = datetime.now(UTC).timestamp() + seconds
    while len(out) < limit and datetime.now(UTC).timestamp() < deadline:
        remaining = max(0.05, deadline - datetime.now(UTC).timestamp())
        evt = _recv(ws, timeout=min(remaining, 1.0))
        if evt is None:
            time.sleep(0.05)
            continue
        out.append(evt)
    return out


def _enable_connect(client: TestClient, headers: dict) -> None:
    r = client.patch(
        "/api/v1/fan-connect/settings",
        headers=headers,
        json={
            "fan_connect_enabled": True,
            "allow_connection_requests": True,
            "discoverable_for_same_events": True,
            "discoverable_for_similar_interests": True,
            "request_policy": "public_passports",
        },
    )
    assert r.status_code == 200, r.text


def _public_passport(db: Session, user: User, username: str) -> None:
    from app.passport.service import ensure_passport

    p = ensure_passport(db, user)
    p.username = username
    p.visibility = "public"
    p.display_name = user.full_name or username
    p.appear_in_directory = True
    p.favorite_categories = ["Afrobeats"]
    user.created_at = datetime.now(UTC) - timedelta(days=40)
    db.commit()


def _checked_in(db: Session, *, host: Host, buyer: User, slug: str) -> Event:
    category = db.query(EventCategory).first()
    start = datetime.now(UTC) - timedelta(days=2)
    event = Event(
        title=f"Night {slug}",
        slug=slug,
        description="Public night for Fan Connect shared context with enough text.",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=3),
        city="Lagos",
        venue_name="Public Hall",
        address="12 Secret Street",
        status="published",
        visibility="listed",
        event_type="public",
        location_visibility="city_only",
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
        reference=f"PDY-P19-{slug.upper()}-{uuid4().hex[:8]}",
        buyer_user_id=buyer.id,
        event_id=event.id,
        status="paid",
        currency="NGN",
        subtotal_amount=Decimal("5000.00"),
        discount_amount=Decimal("0"),
        total_amount=Decimal("5000.00"),
        buyer_email=buyer.email,
        buyer_name=buyer.full_name or "Buyer",
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


def _attend_existing(db: Session, *, buyer: User, event: Event) -> None:
    tt = db.query(TicketType).filter(TicketType.event_id == event.id).one()
    order = Order(
        reference=f"PDY-P19-ATT-{uuid4().hex[:10]}",
        buyer_user_id=buyer.id,
        event_id=event.id,
        status="paid",
        currency="NGN",
        subtotal_amount=Decimal("5000.00"),
        discount_amount=Decimal("0"),
        total_amount=Decimal("5000.00"),
        buyer_email=buyer.email,
        buyer_name=buyer.full_name or "Buyer",
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


# --- WebSocket gaps -----------------------------------------------------------------


def test_hub_dedupes_identical_payload_fingerprints():
    """Reconnect / dual user+thread channel delivery must not double-send."""
    hub = MessagingHub()
    payload = {
        "type": "message.created",
        "thread_id": str(uuid4()),
        "message": {"id": str(uuid4()), "body": "once"},
    }
    assert hub._is_duplicate(payload) is False
    assert hub._is_duplicate(payload) is True
    other = {**payload, "message": {"id": str(uuid4()), "body": "twice"}}
    assert hub._is_duplicate(other) is False


def test_ws_subscribe_plus_user_channel_does_not_duplicate_message(
    client: TestClient, db_session: Session
):
    """One REST send → one message.created even when subscribed (user+thread paths)."""
    host = _seed_host(db_session, "p19-dedupe-host@example.com")
    fan_h, _fan_token = _auth(client, "p19-dedupe-fan@example.com", "Dedupe Fan")
    host_token = client.post(
        "/api/v1/auth/login",
        json={"email": "p19-dedupe-host@example.com", "password": "securepass1"},
    ).json()["access_token"]
    fan = _user(db_session, "p19-dedupe-fan@example.com")
    _follow(db_session, fan=fan, host=host)
    thread_id = _open_thread(client, fan_h, host)

    with client.websocket_connect(f"/api/v1/messages/ws?token={host_token}") as host_ws:
        assert host_ws.receive_json()["type"] == "connected"
        host_ws.send_json({"type": "thread.subscribe", "thread_id": thread_id})
        _drain_until(host_ws, "thread.subscribed")

        def _send():
            return client.post(
                f"/api/v1/messages/{thread_id}/send",
                headers=fan_h,
                json={"body": "Single fan-out please"},
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            sent = pool.submit(_send).result(timeout=10)
        assert sent.status_code == 200, sent.text

        events = _collect_types(host_ws, seconds=2.0)
        created = [e for e in events if e.get("type") == "message.created"]
        assert len(created) == 1, f"expected 1 message.created, got {len(created)}: {events}"
        assert created[0]["message"]["body"] == "Single fan-out please"


def test_ws_typing_not_echoed_to_sender(client: TestClient, db_session: Session):
    host = _seed_host(db_session, "p19-type-host@example.com")
    fan_h, fan_token = _auth(client, "p19-type-fan@example.com", "Type Fan")
    host_token = client.post(
        "/api/v1/auth/login",
        json={"email": "p19-type-host@example.com", "password": "securepass1"},
    ).json()["access_token"]
    fan = _user(db_session, "p19-type-fan@example.com")
    _follow(db_session, fan=fan, host=host)
    thread_id = _open_thread(client, fan_h, host)

    with client.websocket_connect(f"/api/v1/messages/ws?token={host_token}") as host_ws:
        assert host_ws.receive_json()["type"] == "connected"
        with client.websocket_connect(
            f"/api/v1/messages/ws?token={fan_token}"
        ) as fan_ws:
            assert fan_ws.receive_json()["type"] == "connected"
            fan_ws.send_json({"type": "typing.start", "thread_id": thread_id})
            typing = _drain_until(host_ws, "message.typing")
            assert typing["is_typing"] is True
            echoed = _collect_types(fan_ws, seconds=0.8)
            assert not any(e.get("type") == "message.typing" for e in echoed)


def test_rest_mark_read_clears_unread_count(client: TestClient, db_session: Session):
    """Read receipt advances cursor and returns a lower unread_count (REST authority)."""
    host = _seed_host(db_session, "p19-read-host@example.com")
    fan_h, _fan_token = _auth(client, "p19-read-fan@example.com", "Read Fan")
    host_token = client.post(
        "/api/v1/auth/login",
        json={"email": "p19-read-host@example.com", "password": "securepass1"},
    ).json()["access_token"]
    host_h = {"Authorization": f"Bearer {host_token}"}
    fan = _user(db_session, "p19-read-fan@example.com")
    _follow(db_session, fan=fan, host=host)
    thread_id = _open_thread(client, fan_h, host)

    reply = client.post(
        f"/api/v1/host/messages/{thread_id}/send",
        headers=host_h,
        json={"body": "Host reply for unread"},
    )
    assert reply.status_code == 200, reply.text

    thread = db_session.get(MessageThread, UUID(thread_id))
    assert thread is not None and thread.last_message_at is not None
    thread.fan_last_read_at = thread.last_message_at - timedelta(minutes=5)
    db_session.commit()

    before = client.get("/api/v1/messages/unread-count", headers=fan_h)
    assert before.status_code == 200
    assert before.json()["unread_count"] >= 1

    marked = client.patch(f"/api/v1/messages/{thread_id}/read", headers=fan_h)
    assert marked.status_code == 200, marked.text
    assert marked.json()["unread_count"] < before.json()["unread_count"]


def test_publish_thread_read_emits_updated_and_unread(monkeypatch: pytest.MonkeyPatch):
    """Reader gets thread.updated (unread cleared) + unread_count; peers get message.read."""
    from app.messaging import ws_events
    from app.messaging.ws_events import (
        EVT_MESSAGE_READ,
        EVT_THREAD_UNREAD,
        EVT_THREAD_UPDATED,
    )

    published: list[tuple[list, dict]] = []

    def _capture(user_ids, payload):
        published.append((list(user_ids), dict(payload)))

    monkeypatch.setattr(ws_events, "publish_to_users", _capture)
    monkeypatch.setattr(
        ws_events,
        "publish_unread_count",
        lambda db, user_id: _capture(
            [user_id], {"type": EVT_THREAD_UNREAD, "unread_count": 0}
        ),
    )

    fan_id, host_id = uuid4(), uuid4()
    thread = MessageThread(
        id=uuid4(),
        thread_type=MC.THREAD_TYPE_FAN_HOST,
        fan_user_id=fan_id,
        host_user_id=host_id,
        host_id=uuid4(),
        status=MC.THREAD_STATUS_ACTIVE,
        last_message_preview="hi",
    )
    read_at = datetime.now(UTC)
    ws_events.publish_thread_read(
        db=None,  # type: ignore[arg-type]
        thread=thread,
        reader_id=host_id,
        read_at=read_at,
    )

    types = {p.get("type") for _, p in published}
    assert EVT_MESSAGE_READ in types
    assert EVT_THREAD_UPDATED in types
    assert EVT_THREAD_UNREAD in types

    read_evt = next(p for _, p in published if p.get("type") == EVT_MESSAGE_READ)
    assert read_evt["reader_id"] == str(host_id)
    assert fan_id in next(ids for ids, p in published if p.get("type") == EVT_MESSAGE_READ)

    updated = next(p for _, p in published if p.get("type") == EVT_THREAD_UPDATED)
    assert updated.get("unread") is False
    assert updated["thread_id"] == str(thread.id)
    assert host_id in next(
        ids for ids, p in published if p.get("type") == EVT_THREAD_UPDATED
    )


def test_fan_fan_attach_denied_without_accepted_connection(
    client: TestClient, db_session: Session
):
    """Thread row alone is not enough — Fan Connect must be accepted to attach."""
    h_a, _ = _auth(client, "p19-ff-att-a@example.com", "FF Att A")
    h_b, _ = _auth(client, "p19-ff-att-b@example.com", "FF Att B")
    a = _user(db_session, "p19-ff-att-a@example.com")
    b = _user(db_session, "p19-ff-att-b@example.com")
    orphan = messaging_svc.ensure_fan_fan_thread(
        db_session, user_a=a.id, user_b=b.id, for_accept=True
    )
    db_session.commit()
    pre_up = client.post(
        f"/api/v1/messages/threads/{orphan.id}/attachments",
        headers=h_a,
        files={"file": ("dot.png", _PNG, "image/png")},
    )
    assert pre_up.status_code == 403, pre_up.text
    assert "Fan Connect" in str(pre_up.json().get("detail", ""))
    pre_send = client.post(
        f"/api/v1/messages/{orphan.id}/send",
        headers=h_a,
        json={"body": "too early"},
    )
    assert pre_send.status_code == 403


def test_fan_fan_message_created_only_after_accept(
    client: TestClient, db_session: Session
):
    """No attach/send/message.created before Fan Connect accept; after, peer gets it."""
    host = _seed_host(db_session, "p19-ff-host@example.com")
    h_a, _token_a = _auth(client, "p19-ffa@example.com", "FF A")
    h_b, token_b = _auth(client, "p19-ffb@example.com", "FF B")
    a = _user(db_session, "p19-ffa@example.com")
    b = _user(db_session, "p19-ffb@example.com")
    _public_passport(db_session, a, "p19ffa")
    _public_passport(db_session, b, "p19ffb")
    _enable_connect(client, h_a)
    _enable_connect(client, h_b)
    shared = _checked_in(db_session, host=host, buyer=a, slug="p19-ff-night")
    _attend_existing(db_session, buyer=b, event=shared)

    # Pre-accept: cannot open fan_fan thread or send.
    from fastapi import HTTPException

    try:
        messaging_svc.ensure_fan_fan_thread(
            db_session, user_a=a.id, user_b=b.id, for_accept=False
        )
        assert False, "expected Fan Connect gate"
    except HTTPException as exc:
        assert exc.status_code == 403

    fake = str(uuid4())
    pre_up = client.post(
        f"/api/v1/messages/threads/{fake}/attachments",
        headers=h_a,
        files={"file": ("dot.png", _PNG, "image/png")},
    )
    assert pre_up.status_code in {403, 404}
    pre_send = client.post(
        f"/api/v1/messages/{fake}/send",
        headers=h_a,
        json={"body": "too early"},
    )
    assert pre_send.status_code in {403, 404}

    req = client.post(
        "/api/v1/fan-connect/requests",
        headers=h_a,
        json={"username": "p19ffb", "message": "Saw you at the same night"},
    )
    assert req.status_code == 200, req.text
    conn_id = req.json()["id"]
    acc = client.post(
        f"/api/v1/fan-connect/requests/{conn_id}/accept",
        headers=h_b,
    )
    assert acc.status_code == 200, acc.text
    thread_id = acc.json()["thread_id"]
    assert thread_id

    # After accept, image attach works.
    up = client.post(
        f"/api/v1/messages/threads/{thread_id}/attachments",
        headers=h_a,
        files={"file": ("dot.png", _PNG, "image/png")},
    )
    assert up.status_code == 201, up.text
    assert "storage_key" not in up.json()

    with client.websocket_connect(f"/api/v1/messages/ws?token={token_b}") as b_ws:
        assert b_ws.receive_json()["type"] == "connected"

        def _send():
            return client.post(
                f"/api/v1/messages/{thread_id}/send",
                headers=h_a,
                json={"body": "Connected hello on Pàdéyá"},
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            sent = pool.submit(_send).result(timeout=10)
        assert sent.status_code == 200, sent.text

        seen_types: set[str] = set()
        created = None
        deadline_errors = 0
        while "message.created" not in seen_types and deadline_errors < 6:
            pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            fut = pool.submit(b_ws.receive_json)
            try:
                evt = fut.result(timeout=2)
            except Exception:
                deadline_errors += 1
                pool.shutdown(wait=False)
                continue
            pool.shutdown(wait=False)
            seen_types.add(str(evt.get("type")))
            if evt.get("type") == "message.created":
                created = evt
        assert created is not None, f"expected fan-out, got {seen_types}"
        assert created["thread_id"] == thread_id
        assert created["message"]["body"] == "Connected hello on Pàdéyá"
        blob = str(created).lower()
        assert "secret street" not in blob
        assert "@example.com" not in blob
        assert "storage_key" not in blob


# --- Attachment gaps ----------------------------------------------------------------


def test_oversized_image_rejected(monkeypatch: pytest.MonkeyPatch):
    from app.messaging import attachments as att_mod

    monkeypatch.setattr(
        att_mod,
        "get_attachment_limits",
        lambda: AttachmentLimits(
            max_image_bytes=32,
            max_doc_bytes=128,
            max_total_bytes=256,
            max_count=4,
        ),
    )
    with pytest.raises(AttachmentValidationError, match="smaller"):
        validate_attachment_bytes(
            filename="big.png",
            declared_content_type="image/png",
            data=_PNG + b"\x00" * 40,
        )


def test_oversized_pdf_upload_http_rejected(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
):
    from app.messaging import attachments as att_mod

    monkeypatch.setattr(
        att_mod,
        "get_attachment_limits",
        lambda: AttachmentLimits(
            max_image_bytes=5 * 1024 * 1024,
            max_doc_bytes=80,
            max_total_bytes=200,
            max_count=4,
        ),
    )
    host = _seed_host(db_session, "p19-oversize-host@example.com")
    fan_h, _ = _auth(client, "p19-oversize-fan@example.com", "Over Fan")
    fan = _user(db_session, "p19-oversize-fan@example.com")
    _follow(db_session, fan=fan, host=host)
    thread_id = _open_thread(client, fan_h, host)

    huge = b"%PDF-1.4 " + (b"x" * 200)
    r = client.post(
        f"/api/v1/messages/threads/{thread_id}/attachments",
        headers=fan_h,
        files={"file": ("big.pdf", huge, "application/pdf")},
    )
    assert r.status_code == 400, r.text


def test_rejected_attachment_cannot_be_downloaded(
    client: TestClient, db_session: Session
):
    host = _seed_host(db_session, "p19-rej-host@example.com")
    fan_h, _ = _auth(client, "p19-rej-fan@example.com", "Rej Fan")
    fan = _user(db_session, "p19-rej-fan@example.com")
    _follow(db_session, fan=fan, host=host)
    thread_id = _open_thread(client, fan_h, host)

    up = client.post(
        f"/api/v1/messages/threads/{thread_id}/attachments",
        headers=fan_h,
        files={"file": ("dot.png", _PNG, "image/png")},
    )
    assert up.status_code == 201, up.text
    att_id = UUID(up.json()["id"])

    row = db_session.get(MessageAttachment, att_id)
    assert row is not None
    row.status = ATT_STATUS_REJECTED
    db_session.commit()

    dl = client.get(f"/api/v1/messages/attachments/{att_id}", headers=fan_h)
    assert dl.status_code == 404


def test_path_traversal_filename_rejected_on_upload(
    client: TestClient, db_session: Session
):
    host = _seed_host(db_session, "p19-trav-host@example.com")
    fan_h, _ = _auth(client, "p19-trav-fan@example.com", "Trav Fan")
    fan = _user(db_session, "p19-trav-fan@example.com")
    _follow(db_session, fan=fan, host=host)
    thread_id = _open_thread(client, fan_h, host)

    r = client.post(
        f"/api/v1/messages/threads/{thread_id}/attachments",
        headers=fan_h,
        files={"file": ("../../etc/passwd.png", _PNG, "image/png")},
    )
    assert r.status_code == 400, r.text


# --- Privacy ------------------------------------------------------------------------


def test_thread_payload_strips_private_location_order_contact(
    client: TestClient, db_session: Session
):
    """No hidden venue, private address, order/payment, phone/email, shipping."""
    host = _seed_host(db_session, "p19-priv-host@example.com")
    fan_h, _ = _auth(client, "p19-priv-fan@example.com", "Priv Fan")
    fan = _user(db_session, "p19-priv-fan@example.com")
    _follow(db_session, fan=fan, host=host)
    thread_id = _open_thread(client, fan_h, host)

    thread = db_session.get(MessageThread, UUID(thread_id))
    assert thread is not None
    category = db_session.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=3)
    event = Event(
        title="Private Venue Night",
        slug="p19-priv-event-" + uuid4().hex[:6],
        description="Event used to assert messaging privacy redaction rules.",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=3),
        city="Lagos",
        venue_name="Hidden Backroom",
        address="99 Secret Shipping Lane",
        status="published",
        visibility="unlisted",
        event_type="private",
        location_visibility="hidden_until_payment",
        featured=False,
        published_at=start - timedelta(days=1),
    )
    db_session.add(event)
    db_session.flush()
    thread.related_event_id = event.id
    db_session.commit()

    detail = client.get(f"/api/v1/messages/{thread_id}", headers=fan_h)
    assert detail.status_code == 200, detail.text
    blob = str(detail.json()).lower()
    for banned in (
        "secret shipping",
        "99 secret",
        "hidden backroom",
        "paystack",
        "order_id",
        "payment_id",
        "@example.com",
        "+234",
        "shipping_address",
        "storage_key",
        "/media/",
    ):
        assert banned not in blob, banned

    chip = detail.json().get("related_event") or {}
    chip_blob = str(chip).lower()
    assert "secret" not in chip_blob
    assert "shipping" not in chip_blob
    assert "address" not in chip
    assert "venue_name" not in chip


def test_attachment_public_payload_hides_storage_and_paths(
    client: TestClient, db_session: Session
):
    host = _seed_host(db_session, "p19-path-host@example.com")
    fan_h, _ = _auth(client, "p19-path-fan@example.com", "Path Fan")
    fan = _user(db_session, "p19-path-fan@example.com")
    _follow(db_session, fan=fan, host=host)
    thread_id = _open_thread(client, fan_h, host)

    up = client.post(
        f"/api/v1/messages/threads/{thread_id}/attachments",
        headers=fan_h,
        files={"file": ("dot.png", _PNG, "image/png")},
    )
    assert up.status_code == 201, up.text
    body = up.json()
    assert "storage_key" not in body
    assert "checksum" not in str(body).lower()
    assert body["url"].startswith("/api/v1/messages/attachments/")
    assert "/media/" not in body["url"]
    assert "storage/message_attachments" not in str(body)

    att_id = body["id"]
    send = client.post(
        f"/api/v1/messages/{thread_id}/send",
        headers=fan_h,
        json={"body": "", "attachment_ids": [att_id]},
    )
    assert send.status_code == 200, send.text
    msg_blob = str(send.json())
    assert "storage_key" not in msg_blob
    assert "/media/" not in msg_blob
    assert "storage/message_attachments" not in msg_blob

    row = db_session.get(MessageAttachment, UUID(att_id))
    assert row is not None and row.storage_key
    assert row.status == ATT_STATUS_READY
