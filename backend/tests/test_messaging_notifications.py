"""Messaging notification copy + coalesce (no attachment URLs/contents)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.hosts.models import Host, HostProfile
from app.messaging.models import InAppNotification, MessageThread
from app.messaging.notifications import (
    BODY_NEW_MESSAGE,
    BODY_NEW_MESSAGE_WITH_ATTACHMENT,
    notification_copy,
    notify_new_chat_message,
)
from app.users.models import User
from app.users.service import get_role_by_name


def _seed_pair(db: Session) -> tuple[User, MessageThread]:
    fan = User(
        email=f"notif-fan-{uuid4().hex[:8]}@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Notif Fan",
        is_active=True,
    )
    host_user = User(
        email=f"notif-host-{uuid4().hex[:8]}@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Notif Host",
        is_active=True,
    )
    host_user.roles.append(get_role_by_name(db, "host"))
    db.add_all([fan, host_user])
    db.flush()
    host = Host(
        user_id=host_user.id,
        display_name="Notif Host",
        slug="notif-host-" + uuid4().hex[:6],
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, bio="Host", city="Lagos"))
    thread = MessageThread(
        thread_type="fan_host",
        fan_user_id=fan.id,
        host_id=host.id,
        host_user_id=host_user.id,
        status="active",
        initiated_by_user_id=fan.id,
    )
    db.add(thread)
    db.commit()
    db.refresh(thread)
    return fan, thread


def test_notification_copy_attachment_safe():
    title, body = notification_copy(has_attachments=False)
    assert title == "You have a new message."
    assert body == BODY_NEW_MESSAGE

    title_a, body_a = notification_copy(has_attachments=True)
    assert title_a == "You have a new message."
    assert body_a == BODY_NEW_MESSAGE_WITH_ATTACHMENT
    assert "http" not in body_a
    assert "/media/" not in body_a
    assert "/api/" not in body_a
    assert "storage" not in body_a.lower()


def test_notify_coalesces_rapid_duplicates(db_session: Session):
    fan, thread = _seed_pair(db_session)

    created = notify_new_chat_message(
        db_session,
        recipient_user_id=fan.id,
        thread_id=thread.id,
        kind="fan_reply",
        link_path=f"/dashboard/messages/{thread.id}",
        has_attachments=True,
    )
    db_session.commit()
    assert created is True

    created2 = notify_new_chat_message(
        db_session,
        recipient_user_id=fan.id,
        thread_id=thread.id,
        kind="fan_reply",
        link_path=f"/dashboard/messages/{thread.id}",
        has_attachments=True,
    )
    db_session.commit()
    assert created2 is False

    rows = list(
        db_session.scalars(
            select(InAppNotification).where(
                InAppNotification.user_id == fan.id,
                InAppNotification.thread_id == thread.id,
            )
        ).all()
    )
    assert len(rows) == 1
    assert rows[0].body == BODY_NEW_MESSAGE_WITH_ATTACHMENT
    assert "/messages/attachments/" not in (rows[0].body or "")


def test_notify_allows_after_coalesce_window(db_session: Session):
    fan, thread = _seed_pair(db_session)

    notify_new_chat_message(
        db_session,
        recipient_user_id=fan.id,
        thread_id=thread.id,
        kind="host_reply",
        link_path=f"/dashboard/messages/{thread.id}",
        has_attachments=False,
    )
    db_session.commit()
    row = db_session.scalar(
        select(InAppNotification).where(InAppNotification.user_id == fan.id)
    )
    assert row is not None
    row.created_at = datetime.now(UTC) - timedelta(seconds=120)
    db_session.commit()

    created = notify_new_chat_message(
        db_session,
        recipient_user_id=fan.id,
        thread_id=thread.id,
        kind="host_reply",
        link_path=f"/dashboard/messages/{thread.id}",
        has_attachments=False,
    )
    db_session.commit()
    assert created is True
    count = len(
        list(
            db_session.scalars(
                select(InAppNotification).where(
                    InAppNotification.user_id == fan.id
                )
            ).all()
        )
    )
    assert count == 2


def test_send_with_attachment_writes_safe_notification(
    client, db_session: Session
):
    """End-to-end: attachment send → in-app body uses safe attachment copy."""
    from fastapi.testclient import TestClient

    from app.crm.models import HostFollower
    from tests.test_messaging_realtime_attachments import (
        _PNG,
        _auth,
        _follow,
        _open_thread,
        _seed_host,
        _upload_att,
        _user,
    )

    assert isinstance(client, TestClient)
    host = _seed_host(db_session, email="notif-e2e-host@example.com")
    fan_h, _ = _auth(client, "notif-e2e-fan@example.com", "E2E Fan")
    fan = _user(db_session, "notif-e2e-fan@example.com")
    _follow(db_session, fan=fan, host=host)
    # silence unused import if follow helper already commits
    assert db_session.query(HostFollower).count() >= 1
    thread_id = _open_thread(client, fan_h, host)

    # Opening the thread already notified the host — age it so attach-send isn't coalesced.
    for note in db_session.scalars(
        select(InAppNotification).where(
            InAppNotification.user_id == host.user_id
        )
    ).all():
        note.created_at = datetime.now(UTC) - timedelta(seconds=120)
    db_session.commit()

    up = _upload_att(
        client, fan_h, thread_id, name="dot.png", data=_PNG, ctype="image/png"
    )
    assert up.status_code == 201
    att_id = up.json()["id"]
    sent = client.post(
        f"/api/v1/messages/{thread_id}/send",
        headers=fan_h,
        json={"body": "", "attachment_ids": [att_id]},
    )
    assert sent.status_code == 200, sent.text

    notes = list(
        db_session.scalars(
            select(InAppNotification)
            .where(InAppNotification.user_id == host.user_id)
            .order_by(InAppNotification.created_at.desc())
        ).all()
    )
    assert notes
    latest = notes[0]
    assert latest.body == BODY_NEW_MESSAGE_WITH_ATTACHMENT
    assert "/messages/attachments/" not in latest.body
    assert "http" not in latest.body.lower()
