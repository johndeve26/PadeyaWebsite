"""WebSocket permission gates — server-side, never trust the frontend."""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.crm.models import HostFollower
from app.hosts.models import Host, HostProfile
from app.messaging import constants as C
from app.messaging.models import MessageBlock, MessageThread
from app.messaging.ws_permissions import (
    filter_event_recipients,
    user_may_emit_thread_action,
    user_may_receive_thread_event,
)
from app.users.models import User
from app.users.service import get_role_by_name


def _auth(client: TestClient, email: str, name: str = "User") -> tuple[dict, str]:
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


def _seed_host(db: Session, email: str = "perm-host@example.com") -> Host:
    user = User(
        email=email,
        password_hash=hash_password("securepass1"),
        full_name="Perm Host",
        is_active=True,
    )
    user.roles.append(get_role_by_name(db, "host"))
    db.add(user)
    db.flush()
    host = Host(
        user_id=user.id,
        display_name="Perm Host",
        slug="perm-host-" + uuid4().hex[:6],
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, bio="Host", city="Lagos"))
    db.commit()
    return host


def _open_thread(client: TestClient, fan_h: dict, host: Host) -> str:
    r = client.post(
        "/api/v1/messages/threads",
        headers=fan_h,
        json={"host_id": str(host.id), "body": "Hello permission check"},
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_receive_denied_for_non_participant_even_if_admin(
    client: TestClient, db_session: Session, assign_role
):
    host = _seed_host(db_session)
    fan_h, _ = _auth(client, "perm-fan@example.com", "Fan")
    fan = _user(db_session, "perm-fan@example.com")
    db_session.add(HostFollower(host_id=host.id, user_id=fan.id))
    db_session.commit()
    thread_id = _open_thread(client, fan_h, host)

    admin_h, _ = _auth(client, "perm-admin@example.com", "Admin")
    assign_role("perm-admin@example.com", "super_admin")
    admin = _user(db_session, "perm-admin@example.com")

    assert (
        user_may_receive_thread_event(
            db_session,
            user_id=admin.id,
            thread_id=UUID(thread_id),
            event_type="message.created",
        )
        is False
    )
    assert user_may_emit_thread_action(db_session, admin, UUID(thread_id)) is None


def test_blocked_pair_cannot_receive_active_events(
    client: TestClient, db_session: Session
):
    host = _seed_host(db_session, email="perm-block-host@example.com")
    fan_h, _ = _auth(client, "perm-block-fan@example.com", "Fan")
    fan = _user(db_session, "perm-block-fan@example.com")
    db_session.add(HostFollower(host_id=host.id, user_id=fan.id))
    db_session.commit()
    thread_id = UUID(_open_thread(client, fan_h, host))

    db_session.add(
        MessageBlock(
            blocker_user_id=host.user_id,
            blocked_user_id=fan.id,
            reason="test",
        )
    )
    thread = db_session.get(MessageThread, thread_id)
    assert thread is not None
    thread.status = C.THREAD_STATUS_BLOCKED
    db_session.commit()

    assert (
        user_may_receive_thread_event(
            db_session,
            user_id=fan.id,
            thread_id=thread_id,
            event_type="message.created",
        )
        is False
    )
    assert (
        user_may_receive_thread_event(
            db_session,
            user_id=fan.id,
            thread_id=thread_id,
            event_type="message.typing",
        )
        is False
    )
    # Lifecycle still allowed so UI can disable the thread
    assert (
        user_may_receive_thread_event(
            db_session,
            user_id=fan.id,
            thread_id=thread_id,
            event_type="thread.disabled",
        )
        is True
    )


def test_filter_recipients_drops_unauthorized(client: TestClient, db_session: Session):
    host = _seed_host(db_session, email="perm-filter-host@example.com")
    fan_h, _ = _auth(client, "perm-filter-fan@example.com", "Fan")
    stranger_h, _ = _auth(client, "perm-stranger@example.com", "Stranger")
    fan = _user(db_session, "perm-filter-fan@example.com")
    stranger = _user(db_session, "perm-stranger@example.com")
    db_session.add(HostFollower(host_id=host.id, user_id=fan.id))
    db_session.commit()
    thread_id = UUID(_open_thread(client, fan_h, host))

    allowed = filter_event_recipients(
        db_session,
        [fan.id, stranger.id, host.user_id],
        thread_id=thread_id,
        event_type="message.created",
    )
    assert set(allowed) == {fan.id, host.user_id}
    assert stranger.id not in allowed


def test_ws_subscribe_denied_for_stranger(client: TestClient, db_session: Session):
    host = _seed_host(db_session, email="perm-sub-host@example.com")
    fan_h, _ = _auth(client, "perm-sub-fan@example.com", "Fan")
    stranger_h, stranger_token = _auth(
        client, "perm-sub-stranger@example.com", "Stranger"
    )
    fan = _user(db_session, "perm-sub-fan@example.com")
    db_session.add(HostFollower(host_id=host.id, user_id=fan.id))
    db_session.commit()
    thread_id = _open_thread(client, fan_h, host)

    with client.websocket_connect(
        f"/api/v1/messages/ws?token={stranger_token}"
    ) as ws:
        assert ws.receive_json()["type"] == "connected"
        ws.send_json({"type": "thread.subscribe", "thread_id": thread_id})
        evt = ws.receive_json()
        assert evt["type"] == "thread.subscribe_denied"
        assert evt["thread_id"] == thread_id


def test_ws_typing_emit_denied_when_blocked(client: TestClient, db_session: Session):
    host = _seed_host(db_session, email="perm-type-host@example.com")
    fan_h, _ = _auth(client, "perm-type-fan@example.com", "Fan")
    host_token = client.post(
        "/api/v1/auth/login",
        json={"email": "perm-type-host@example.com", "password": "securepass1"},
    ).json()["access_token"]
    fan = _user(db_session, "perm-type-fan@example.com")
    db_session.add(HostFollower(host_id=host.id, user_id=fan.id))
    db_session.commit()
    thread_id = __import__("uuid").UUID(_open_thread(client, fan_h, host))

    client.post(
        "/api/v1/host/messages/block",
        headers={"Authorization": f"Bearer {host_token}"},
        json={"blocked_user_id": str(fan.id), "reason": "stop"},
    )

    assert (
        user_may_emit_thread_action(
            db_session, fan, thread_id, require_can_reply=True
        )
        is None
    )
