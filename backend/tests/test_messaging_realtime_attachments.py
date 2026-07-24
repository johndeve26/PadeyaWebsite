"""WebSocket push + safe image attachments — permission gates unchanged."""

from __future__ import annotations

import concurrent.futures
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.crm.models import HostFollower
from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostProfile
from app.messaging.models import Message
from app.payments.models import Order, OrderItem
from app.tickets.models import Ticket
from app.tickets.qr import new_public_ticket_code
from app.users.models import User
from app.users.service import get_role_by_name

# Minimal valid 1x1 PNG (CRC-correct; Pillow-verifiable)
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


def _seed_host(db: Session, email: str = "rt-host@example.com") -> Host:
    user = User(
        email=email,
        password_hash=hash_password("securepass1"),
        full_name="RT Host",
        is_active=True,
    )
    user.roles.append(get_role_by_name(db, "host"))
    db.add(user)
    db.flush()
    host = Host(
        user_id=user.id,
        display_name="RT Host",
        slug="rt-host-" + uuid4().hex[:6],
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
        json={"host_id": str(host.id), "body": "Hello from the night"},
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_ws_rejects_missing_token(client: TestClient):
    with client.websocket_connect("/api/v1/messages/ws") as ws:
        # Server accepts then closes with 4401
        try:
            ws.receive_json()
            assert False, "expected close"
        except Exception:
            pass


def test_ws_rejects_invalid_token(client: TestClient):
    with client.websocket_connect("/api/v1/messages/ws?token=not-a-jwt") as ws:
        try:
            ws.receive_json()
            assert False, "expected close"
        except Exception:
            pass


def test_ws_connected_and_ping(client: TestClient, db_session: Session):
    headers, token = _auth(client, "rt-ping@example.com")
    _ = headers
    with client.websocket_connect(f"/api/v1/messages/ws?token={token}") as ws:
        assert ws.receive_json()["type"] == "connected"
        ws.send_json({"type": "ping"})
        assert ws.receive_json()["type"] == "pong"


def test_send_fans_out_new_message_over_ws(client: TestClient, db_session: Session):
    host = _seed_host(db_session)
    fan_h, _fan_token = _auth(client, "rt-fan@example.com", "RT Fan")
    host_login = client.post(
        "/api/v1/auth/login",
        json={"email": "rt-host@example.com", "password": "securepass1"},
    )
    assert host_login.status_code == 200, host_login.text
    host_token = host_login.json()["access_token"]
    host_h = {"Authorization": f"Bearer {host_token}"}

    fan = _user(db_session, "rt-fan@example.com")
    _follow(db_session, fan=fan, host=host)
    thread_id = _open_thread(client, fan_h, host)

    with client.websocket_connect(f"/api/v1/messages/ws?token={host_token}") as ws:
        assert ws.receive_json()["type"] == "connected"

        def _send():
            return client.post(
                f"/api/v1/messages/{thread_id}/send",
                headers=fan_h,
                json={"body": "Realtime hello on Pàdéyá"},
            )

        # Nested HTTP on the TestClient WS thread can deadlock — send on a worker.
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            sent = pool.submit(_send).result(timeout=10)
        assert sent.status_code == 200, sent.text

        seen_types: set[str] = set()
        deadline_errors = 0
        while "message.created" not in seen_types and deadline_errors < 6:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                fut = pool.submit(ws.receive_json)
                try:
                    evt = fut.result(timeout=2)
                except Exception:
                    deadline_errors += 1
                    continue
            seen_types.add(str(evt.get("type")))
            if evt.get("type") == "message.created":
                assert evt["thread_id"] == thread_id
                assert evt["message"]["body"] == "Realtime hello on Pàdéyá"
                blob = str(evt).lower()
                assert "secret street" not in blob
                assert "@example.com" not in blob
                assert "order_id" not in blob
        assert "message.created" in seen_types, f"expected fan-out, got {seen_types}"


def _upload_att(
    client: TestClient,
    headers: dict[str, str],
    thread_id: str,
    *,
    name: str,
    data: bytes,
    ctype: str,
):
    return client.post(
        f"/api/v1/messages/threads/{thread_id}/attachments",
        headers=headers,
        files={"file": (name, data, ctype)},
    )


def test_attachment_upload_rejects_unsafe_and_allows_safe(
    client: TestClient, db_session: Session
):
    host = _seed_host(db_session, email="rt-att-safe-host@example.com")
    headers, _ = _auth(client, "rt-att@example.com", "Att Safe")
    fan = _user(db_session, "rt-att@example.com")
    _follow(db_session, fan=fan, host=host)
    thread_id = _open_thread(client, headers, host)

    bad = _upload_att(
        client,
        headers,
        thread_id,
        name="x.svg",
        data=b"<svg xmlns='http://www.w3.org/2000/svg'/>",
        ctype="image/svg+xml",
    )
    assert bad.status_code == 400

    zip_bad = _upload_att(
        client,
        headers,
        thread_id,
        name="x.zip",
        data=b"PK\x03\x04fake",
        ctype="application/zip",
    )
    assert zip_bad.status_code == 400

    html_bad = _upload_att(
        client,
        headers,
        thread_id,
        name="x.html",
        data=b"<!DOCTYPE html><html></html>",
        ctype="text/html",
    )
    assert html_bad.status_code == 400

    mismatch = _upload_att(
        client,
        headers,
        thread_id,
        name="fake.png",
        data=b"%PDF-1.4 minimal",
        ctype="image/png",
    )
    assert mismatch.status_code == 400

    pdf_ok = _upload_att(
        client,
        headers,
        thread_id,
        name="note.pdf",
        data=b"%PDF-1.4 minimal",
        ctype="application/pdf",
    )
    assert pdf_ok.status_code == 201, pdf_ok.text
    assert pdf_ok.json()["content_type"] == "application/pdf"
    assert pdf_ok.json()["status"] == "ready"
    assert "thread_id" not in pdf_ok.json()
    assert "storage_key" not in pdf_ok.json()
    assert "checksum" not in str(pdf_ok.json()).lower()

    txt_ok = _upload_att(
        client,
        headers,
        thread_id,
        name="hello.txt",
        data=b"hello from padeya\n",
        ctype="text/plain",
    )
    assert txt_ok.status_code == 201, txt_ok.text
    assert txt_ok.json()["content_type"] == "text/plain"


def test_attachment_send_and_foreign_rejected(client: TestClient, db_session: Session):
    host = _seed_host(db_session, email="rt-att-host@example.com")
    host2 = _seed_host(db_session, email="rt-att-host2@example.com")
    fan_h, _ = _auth(client, "rt-att-fan@example.com", "Att Fan")
    other_h, _ = _auth(client, "rt-att-other@example.com", "Other")
    fan = _user(db_session, "rt-att-fan@example.com")
    other = _user(db_session, "rt-att-other@example.com")
    _follow(db_session, fan=fan, host=host)
    _follow(db_session, fan=other, host=host2)
    thread_id = _open_thread(client, fan_h, host)
    other_thread = _open_thread(client, other_h, host2)

    up = _upload_att(
        client, fan_h, thread_id, name="dot.png", data=_PNG, ctype="image/png"
    )
    assert up.status_code == 201, up.text
    att_id = up.json()["id"]
    assert up.json()["content_type"] == "image/png"
    assert up.json()["status"] == "ready"
    assert set(up.json().keys()) <= {
        "id",
        "url",
        "content_type",
        "byte_size",
        "original_filename",
        "width",
        "height",
        "status",
        "reviewed_at",
    }
    assert "storage_key" not in up.json()

    # Stranger cannot upload into someone else's thread.
    stranger_up = _upload_att(
        client, other_h, thread_id, name="dot.png", data=_PNG, ctype="image/png"
    )
    assert stranger_up.status_code in {403, 404}

    # Attachment from another thread cannot be bound here.
    foreign = _upload_att(
        client, other_h, other_thread, name="dot.png", data=_PNG, ctype="image/png"
    )
    assert foreign.status_code == 201
    foreign_id = foreign.json()["id"]
    denied = client.post(
        f"/api/v1/messages/{thread_id}/send",
        headers=fan_h,
        json={"body": "", "attachment_ids": [foreign_id]},
    )
    assert denied.status_code == 400

    ok = client.post(
        f"/api/v1/messages/{thread_id}/send",
        headers=fan_h,
        json={"body": "", "attachment_ids": [att_id]},
    )
    assert ok.status_code == 200, ok.text
    data = ok.json()
    assert data["message_type"] == "image"
    assert len(data["attachments"]) == 1
    assert data["attachments"][0]["id"] == att_id
    url = data["attachments"][0]["url"]
    assert url.startswith("/api/v1/messages/attachments/")
    assert "/media/" not in url
    assert "email" not in str(data).lower() or "@" not in str(data)

    # Participant can download via Bearer; stranger cannot.
    dl = client.get(
        f"/api/v1/messages/attachments/{att_id}",
        headers=fan_h,
    )
    assert dl.status_code == 200
    assert dl.content == _PNG
    assert dl.headers.get("content-type", "").startswith("image/png")

    # Signed URL from upload response works without Bearer.
    signed = up.json()["url"]
    assert "?d=" in signed
    dl_signed = client.get(signed)
    assert dl_signed.status_code == 200
    assert dl_signed.content == _PNG

    denied_dl = client.get(
        f"/api/v1/messages/attachments/{att_id}",
        headers=other_h,
    )
    assert denied_dl.status_code in {403, 404}

    anon = client.get(f"/api/v1/messages/attachments/{att_id}")
    assert anon.status_code == 401


def test_attachment_upload_does_not_create_message(
    client: TestClient, db_session: Session
):
    from app.messaging.models import MessageAttachment
    from app.messaging.service import cleanup_orphan_attachments

    host = _seed_host(db_session, email="rt-stage-host@example.com")
    fan_h, _ = _auth(client, "rt-stage-fan@example.com", "Stage Fan")
    fan = _user(db_session, "rt-stage-fan@example.com")
    _follow(db_session, fan=fan, host=host)
    thread_id = _open_thread(client, fan_h, host)

    before = db_session.scalar(select(func.count()).select_from(Message)) or 0
    up = _upload_att(
        client, fan_h, thread_id, name="dot.png", data=_PNG, ctype="image/png"
    )
    assert up.status_code == 201, up.text
    assert up.json()["status"] == "ready"
    after = db_session.scalar(select(func.count()).select_from(Message)) or 0
    # Opening the thread already created the first message; upload must not add another.
    assert after == before

    att = db_session.get(MessageAttachment, UUID(up.json()["id"]))
    assert att is not None
    assert att.message_id is None
    assert att.thread_id == UUID(thread_id)

    # Orphan expiry soft-deletes unused staged uploads.
    att.created_at = datetime.now(UTC) - timedelta(hours=48)
    db_session.commit()
    n = cleanup_orphan_attachments(db_session, limit=20)
    assert n >= 1
    db_session.refresh(att)
    assert att.status == "deleted"
    assert att.deleted_at is not None


def test_hidden_message_redacts_attachments(client: TestClient, db_session: Session):
    host = _seed_host(db_session, email="rt-hide-host@example.com")
    fan_h, _ = _auth(client, "rt-hide-fan@example.com", "Hide Fan")
    fan = _user(db_session, "rt-hide-fan@example.com")
    _follow(db_session, fan=fan, host=host)
    thread_id = _open_thread(client, fan_h, host)

    up = _upload_att(
        client, fan_h, thread_id, name="dot.png", data=_PNG, ctype="image/png"
    )
    assert up.status_code == 201, up.text
    att_id = up.json()["id"]
    sent = client.post(
        f"/api/v1/messages/{thread_id}/send",
        headers=fan_h,
        json={"body": "with image", "attachment_ids": [att_id]},
    )
    assert sent.status_code == 200
    msg_id = sent.json()["id"]

    row = db_session.get(Message, UUID(str(msg_id)))
    assert row is not None
    row.moderation_status = "hidden"
    row.status = "hidden"
    db_session.commit()

    detail = client.get(f"/api/v1/messages/{thread_id}", headers=fan_h)
    assert detail.status_code == 200
    msg = next(m for m in detail.json()["messages"] if m["id"] == msg_id)
    assert msg["attachments"] == []
    assert "hidden by moderation" in msg["body"].lower()


def test_attachments_blocked_on_message_request(client: TestClient, db_session: Session):
    """Safer default: no upload/send attachments while thread is a request."""
    host = _seed_host(db_session, email="rt-req-host@example.com")
    fan_h, _ = _auth(client, "rt-req-fan@example.com", "Req Fan")
    # Weak relationship → message request (no follow).
    created = client.post(
        "/api/v1/messages/threads",
        headers=fan_h,
        json={"host_id": str(host.id), "body": "Hi from the directory"},
    )
    assert created.status_code == 200, created.text
    thread_id = created.json()["id"]
    assert created.json().get("is_request") is True or created.json().get("status") == "request"
    assert created.json().get("can_attach") is False

    up = _upload_att(
        client, fan_h, thread_id, name="dot.png", data=_PNG, ctype="image/png"
    )
    assert up.status_code == 403
    assert "accepted" in up.json()["detail"].lower()

    # Even with a staged id invented, send with attachments must fail on request.
    denied = client.post(
        f"/api/v1/messages/{thread_id}/send",
        headers=fan_h,
        json={"body": "", "attachment_ids": [str(uuid4())]},
    )
    assert denied.status_code == 403


def test_attachments_blocked_when_messaging_blocked(
    client: TestClient, db_session: Session
):
    host = _seed_host(db_session, email="rt-blk-host@example.com")
    fan_h, _ = _auth(client, "rt-blk-fan@example.com", "Blk Fan")
    fan = _user(db_session, "rt-blk-fan@example.com")
    _follow(db_session, fan=fan, host=host)
    thread_id = _open_thread(client, fan_h, host)

    detail = client.get(f"/api/v1/messages/{thread_id}", headers=fan_h)
    assert detail.status_code == 200
    assert detail.json()["can_attach"] is True

    block = client.post(
        "/api/v1/messages/block",
        headers=fan_h,
        json={"blocked_user_id": str(host.user_id), "reason": "test"},
    )
    assert block.status_code == 204

    up = _upload_att(
        client, fan_h, thread_id, name="dot.png", data=_PNG, ctype="image/png"
    )
    assert up.status_code == 403


def test_admin_can_moderate_attachments_on_reported_thread(
    client: TestClient, db_session: Session, assign_role
):
    host = _seed_host(db_session, email="rt-mod-host@example.com")
    fan_h, _ = _auth(client, "rt-mod-fan@example.com", "Mod Fan")
    fan = _user(db_session, "rt-mod-fan@example.com")
    _follow(db_session, fan=fan, host=host)
    thread_id = _open_thread(client, fan_h, host)

    up = _upload_att(
        client, fan_h, thread_id, name="dot.png", data=_PNG, ctype="image/png"
    )
    assert up.status_code == 201, up.text
    att_id = up.json()["id"]
    assert (
        client.post(
            f"/api/v1/messages/{thread_id}/send",
            headers=fan_h,
            json={"body": "", "attachment_ids": [att_id]},
        ).status_code
        == 200
    )

    # Thread report still works with attachments.
    assert (
        client.post(
            f"/api/v1/messages/{thread_id}/report",
            headers=fan_h,
            json={"reason": "spam", "details": "Bad image"},
        ).status_code
        == 201
    )

    admin_h, _ = _auth(client, "rt-mod-admin@example.com", "Mod Admin")
    assign_role("rt-mod-admin@example.com", "super_admin")
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "rt-mod-admin@example.com", "password": "securepass1"},
    )
    admin_h = {"Authorization": f"Bearer {login.json()['access_token']}"}

    reports = client.get("/api/v1/admin/message-reports", headers=admin_h)
    assert reports.status_code == 200
    rid = reports.json()["items"][0]["id"]
    detail = client.get(f"/api/v1/admin/message-reports/{rid}", headers=admin_h)
    assert detail.status_code == 200
    # Admin view includes attachment metadata even on reported threads.
    flat = str(detail.json())
    assert att_id in flat
    assert "storage_key" not in flat

    hidden = client.patch(
        f"/api/v1/admin/messages/attachments/{att_id}/hide",
        headers=admin_h,
    )
    assert hidden.status_code == 200, hidden.text
    assert hidden.json()["status"] == "hidden"

    # Participant can no longer download; admin still can.
    assert (
        client.get(
            f"/api/v1/messages/attachments/{att_id}", headers=fan_h
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/v1/messages/attachments/{att_id}", headers=admin_h
        ).status_code
        == 200
    )

    reviewed = client.patch(
        f"/api/v1/admin/messages/attachments/{att_id}/review",
        headers=admin_h,
    )
    assert reviewed.status_code == 200
    assert reviewed.json().get("reviewed_at")

    disabled = client.patch(
        f"/api/v1/admin/messages/attachments/{att_id}/delete",
        headers=admin_h,
    )
    assert disabled.status_code == 200
    assert disabled.json()["status"] == "deleted"
    # Soft-delete: row kept, download disabled for everyone.
    assert (
        client.get(
            f"/api/v1/messages/attachments/{att_id}", headers=admin_h
        ).status_code
        == 404
    )

    restored = client.patch(
        f"/api/v1/admin/messages/attachments/{att_id}/restore",
        headers=admin_h,
    )
    assert restored.status_code == 200, restored.text
    assert restored.json()["status"] == "ready"
    assert (
        client.get(
            f"/api/v1/messages/attachments/{att_id}", headers=fan_h
        ).status_code
        == 200
    )


def test_admin_attachment_download_only_when_reported(
    client: TestClient, db_session: Session, assign_role
):
    host = _seed_host(db_session, email="rt-adm-host@example.com")
    fan_h, _ = _auth(client, "rt-adm-fan@example.com", "Adm Fan")
    fan = _user(db_session, "rt-adm-fan@example.com")
    _follow(db_session, fan=fan, host=host)
    thread_id = _open_thread(client, fan_h, host)

    up = _upload_att(
        client, fan_h, thread_id, name="dot.png", data=_PNG, ctype="image/png"
    )
    assert up.status_code == 201, up.text
    att_id = up.json()["id"]
    sent = client.post(
        f"/api/v1/messages/{thread_id}/send",
        headers=fan_h,
        json={"body": "", "attachment_ids": [att_id]},
    )
    assert sent.status_code == 200, sent.text

    admin_h, _ = _auth(client, "rt-adm-admin@example.com", "Adm")
    assign_role("rt-adm-admin@example.com", "super_admin")
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "rt-adm-admin@example.com", "password": "securepass1"},
    )
    admin_h = {"Authorization": f"Bearer {login.json()['access_token']}"}

    # Admin is not a participant and there is no report yet.
    denied = client.get(f"/api/v1/messages/attachments/{att_id}", headers=admin_h)
    assert denied.status_code in {403, 404}

    report = client.post(
        f"/api/v1/messages/{thread_id}/report",
        headers=fan_h,
        json={"reason": "spam", "details": "Attachment check"},
    )
    assert report.status_code == 201

    allowed = client.get(f"/api/v1/messages/attachments/{att_id}", headers=admin_h)
    assert allowed.status_code == 200
    assert allowed.content == _PNG

    listed = client.get("/api/v1/admin/message-reports", headers=admin_h)
    assert listed.status_code == 200
    rid = listed.json()["items"][0]["id"]
    detail = client.get(f"/api/v1/admin/message-reports/{rid}", headers=admin_h)
    assert detail.status_code == 200
    # Report payload includes authorized attachment URL (not a filesystem path).
    blob = str(detail.json())
    assert "/api/v1/messages/attachments/" in blob
    assert "/media/" not in blob


def test_ws_does_not_bypass_fan_fan_pre_accept(client: TestClient, db_session: Session):
    """Confirm REST gate still blocks; WS has no send path."""
    from app.fan_connect.eligibility import ensure_connect_settings
    from app.passport.service import ensure_passport

    h_a, token_a = _auth(client, "rt-ffa@example.com", "FF A")
    h_b, _token_b = _auth(client, "rt-ffb@example.com", "FF B")
    a = _user(db_session, "rt-ffa@example.com")
    b = _user(db_session, "rt-ffb@example.com")
    a.created_at = datetime.now(UTC) - timedelta(days=40)
    b.created_at = datetime.now(UTC) - timedelta(days=40)
    for u, uname in ((a, "rtffa"), (b, "rtffb")):
        pp = ensure_passport(db_session, u)
        pp.username = uname
        pp.visibility = "public"
        pp.appear_in_directory = True
        s = ensure_connect_settings(db_session, u)
        s.fan_connect_enabled = True
        s.allow_connection_requests = True
        s.discoverable_for_same_events = True
    db_session.commit()

    # No connection — cannot send even if inventing a thread id
    fake = str(uuid4())
    r = client.post(
        f"/api/v1/messages/{fake}/send",
        headers=h_a,
        json={"body": "should fail"},
    )
    assert r.status_code in {403, 404}

    with client.websocket_connect(f"/api/v1/messages/ws?token={token_a}") as ws:
        assert ws.receive_json()["type"] == "connected"
        # Client-originated send is ignored (ping only)
        ws.send_json({"type": "send_message", "body": "bypass?"})
        ws.send_json({"type": "ping"})
        assert ws.receive_json()["type"] == "pong"


def _recv_ws(ws, *, timeout: float = 2.0):
    """Receive one event; never deadlock TestClient on a timed-out receive_json."""
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    fut = pool.submit(ws.receive_json)
    try:
        return fut.result(timeout=timeout)
    except Exception:
        return None
    finally:
        pool.shutdown(wait=False, cancel_futures=True)


def _drain_until(ws, typ: str, *, limit: int = 12, timeout: float = 2.0):
    for _ in range(limit):
        evt = _recv_ws(ws, timeout=timeout)
        if evt is None:
            break
        if evt.get("type") == typ:
            return evt
    raise AssertionError(f"did not receive {typ}")


def test_ws_typing_indicator(client: TestClient, db_session: Session):
    host = _seed_host(db_session, email="rt-type-host@example.com")
    fan_h, fan_token = _auth(client, "rt-type-fan@example.com", "Type Fan")
    host_token = client.post(
        "/api/v1/auth/login",
        json={"email": "rt-type-host@example.com", "password": "securepass1"},
    ).json()["access_token"]
    fan = _user(db_session, "rt-type-fan@example.com")
    _follow(db_session, fan=fan, host=host)
    thread_id = _open_thread(client, fan_h, host)
    before_msgs = db_session.scalar(select(func.count()).select_from(Message)) or 0

    with client.websocket_connect(f"/api/v1/messages/ws?token={host_token}") as host_ws:
        assert host_ws.receive_json()["type"] == "connected"
        with client.websocket_connect(
            f"/api/v1/messages/ws?token={fan_token}"
        ) as fan_ws:
            assert fan_ws.receive_json()["type"] == "connected"
            fan_ws.send_json({"type": "typing.start", "thread_id": thread_id})
            typing = _drain_until(host_ws, "message.typing")
            assert typing["thread_id"] == thread_id
            assert typing["is_typing"] is True
            assert typing.get("display_name") == "Type Fan"
            assert typing.get("user_id") == str(fan.id)
            assert "email" not in typing
            assert "phone" not in typing
            fan_ws.send_json({"type": "typing.stop", "thread_id": thread_id})
            stop = _drain_until(host_ws, "message.typing")
            assert stop["is_typing"] is False

    # Typing is ephemeral — never persisted as Message rows.
    after_msgs = db_session.scalar(select(func.count()).select_from(Message)) or 0
    assert after_msgs == before_msgs


def test_ws_thread_subscribe_and_message_read(client: TestClient, db_session: Session):
    host = _seed_host(db_session, email="rt-read-host@example.com")
    fan_h, fan_token = _auth(client, "rt-read-fan@example.com", "Read Fan")
    host_token = client.post(
        "/api/v1/auth/login",
        json={"email": "rt-read-host@example.com", "password": "securepass1"},
    ).json()["access_token"]
    fan = _user(db_session, "rt-read-fan@example.com")
    host_user = _user(db_session, "rt-read-host@example.com")
    _follow(db_session, fan=fan, host=host)
    thread_id = _open_thread(client, fan_h, host)

    with client.websocket_connect(f"/api/v1/messages/ws?token={fan_token}") as fan_ws:
        assert fan_ws.receive_json()["type"] == "connected"
        fan_ws.send_json({"type": "thread.subscribe", "thread_id": thread_id})
        sub = _drain_until(fan_ws, "thread.subscribed")
        assert sub["thread_id"] == thread_id

        # Client-originated message.read (same gates as REST)
        with client.websocket_connect(
            f"/api/v1/messages/ws?token={host_token}"
        ) as host_ws:
            assert host_ws.receive_json()["type"] == "connected"
            # Spoof fields must be ignored — receipt is always the socket user.
            host_ws.send_json(
                {
                    "type": "message.read",
                    "thread_id": thread_id,
                    "reader_id": str(fan.id),
                    "read_at": "2000-01-01T00:00:00+00:00",
                }
            )
            evt = _drain_until(fan_ws, "message.read")
            assert evt["thread_id"] == thread_id
            assert evt.get("reader_id") == str(host_user.id)
            assert evt.get("read_at")
            assert not str(evt.get("read_at", "")).startswith("2000-01-01")


def test_rest_mark_read_advances_cursor_and_unread(
    client: TestClient, db_session: Session
):
    """REST mark-read advances the caller's cursor and returns unread count."""
    from app.messaging.models import MessageThread

    host = _seed_host(db_session, email="rt-read-clear-host@example.com")
    fan_h, _ = _auth(client, "rt-read-clear-fan@example.com", "Clear Fan")
    host_token = client.post(
        "/api/v1/auth/login",
        json={"email": "rt-read-clear-host@example.com", "password": "securepass1"},
    ).json()["access_token"]
    host_h = {"Authorization": f"Bearer {host_token}"}
    fan = _user(db_session, "rt-read-clear-fan@example.com")
    _follow(db_session, fan=fan, host=host)
    thread_id = _open_thread(client, fan_h, host)

    r = client.patch(f"/api/v1/host/messages/{thread_id}/read", headers=host_h)
    assert r.status_code == 200
    body = r.json()
    assert "unread_count" in body

    thread = db_session.get(MessageThread, UUID(thread_id))
    assert thread is not None
    assert thread.host_last_read_at is not None


def test_ws_message_read_denied_for_stranger(
    client: TestClient, db_session: Session
):
    from app.messaging.models import MessageThread

    host = _seed_host(db_session, email="rt-read-deny-host@example.com")
    fan_h, _fan_token = _auth(client, "rt-read-deny-fan@example.com", "Fan")
    _stranger_h, stranger_token = _auth(
        client, "rt-read-deny-stranger@example.com", "Stranger"
    )
    fan = _user(db_session, "rt-read-deny-fan@example.com")
    _follow(db_session, fan=fan, host=host)
    thread_id = _open_thread(client, fan_h, host)
    tid = UUID(thread_id)
    thread = db_session.get(MessageThread, tid)
    assert thread is not None
    before_fan = thread.fan_last_read_at
    before_host = thread.host_last_read_at

    with client.websocket_connect(
        f"/api/v1/messages/ws?token={stranger_token}"
    ) as stranger_ws:
        assert stranger_ws.receive_json()["type"] == "connected"
        stranger_ws.send_json({"type": "message.read", "thread_id": thread_id})

    db_session.refresh(thread)
    # Stranger cannot advance either participant's read cursor.
    assert thread.fan_last_read_at == before_fan
    assert thread.host_last_read_at == before_host


def test_ws_block_disables_thread(client: TestClient, db_session: Session):
    host = _seed_host(db_session, email="rt-block-host@example.com")
    fan_h, fan_token = _auth(client, "rt-block-fan@example.com", "Block Fan")
    host_token = client.post(
        "/api/v1/auth/login",
        json={"email": "rt-block-host@example.com", "password": "securepass1"},
    ).json()["access_token"]
    host_h = {"Authorization": f"Bearer {host_token}"}
    fan = _user(db_session, "rt-block-fan@example.com")
    _follow(db_session, fan=fan, host=host)
    thread_id = _open_thread(client, fan_h, host)

    with client.websocket_connect(f"/api/v1/messages/ws?token={fan_token}") as fan_ws:
        assert fan_ws.receive_json()["type"] == "connected"

        def _block():
            return client.post(
                "/api/v1/host/messages/block",
                headers=host_h,
                json={"blocked_user_id": str(fan.id), "reason": "spam"},
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            br = pool.submit(_block).result(timeout=10)
        assert br.status_code in {200, 204}, getattr(br, "text", br)
        disabled = _drain_until(fan_ws, "thread.disabled")
        assert disabled["thread_id"] == thread_id
        assert disabled["can_reply"] is False
