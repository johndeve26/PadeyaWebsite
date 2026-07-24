"""Safe demo attachment seed — placeholders only, no private venue data."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_password
from app.demo.constants import DEMO_EMAIL_DOMAIN, DEMO_PASSWORD
from app.demo.messaging_attachments_seed import (
    _demo_pdf_bytes,
    _demo_png_bytes,
    _entry_flow_png_bytes,
    ensure_message_attachment,
    seed_chidi_bayo_attachments,
    seed_reported_thread_attachments,
    seed_tolu_maze_attachments,
)
from app.demo.messaging_privacy import assert_safe_demo_copy
from app.hosts.models import Host, HostProfile
from app.messaging import constants as MC
from app.messaging.models import Message, MessageAttachment, MessageThread
from app.users.models import User
from app.users.service import get_role_by_name


@pytest.fixture()
def demo_settings(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("FRONTEND_URL", "http://localhost:3000")
    get_settings.cache_clear()
    yield get_settings()
    get_settings.cache_clear()


def _user(db, *, email: str, name: str) -> User:
    role = get_role_by_name(db, "buyer")
    u = User(
        email=email,
        full_name=name,
        password_hash=hash_password(DEMO_PASSWORD),
        is_active=True,
    )
    if role is not None:
        u.roles.append(role)
    db.add(u)
    db.flush()
    return u


def test_placeholder_bytes_are_safe_and_valid(demo_settings) -> None:
    png = _demo_png_bytes(label="product-demo-night-agenda", fill=(18, 48, 32))
    assert png[:8] == b"\x89PNG\r\n\x1a\n"

    entry = _entry_flow_png_bytes()
    assert entry[:8] == b"\x89PNG\r\n\x1a\n"

    pdf = _demo_pdf_bytes(title="Demo Night Schedule")
    assert pdf.startswith(b"%PDF")
    assert b"No private addresses" in pdf
    assert b"Padeya" in pdf

    for name in (
        "product-demo-night-agenda.png",
        "demo-night-schedule.pdf",
        "afrobeats-entry-map.png",
        "demo-moderation-sample.png",
    ):
        assert_safe_demo_copy(name, context="demo attachment filename")


def test_seed_helpers_attach_ready_files(demo_settings, db_session) -> None:
    fan_a = _user(db_session, email=f"attfan-a@{DEMO_EMAIL_DOMAIN}", name="Att Fan A")
    fan_b = _user(db_session, email=f"attfan-b@{DEMO_EMAIL_DOMAIN}", name="Att Fan B")
    host_user = _user(
        db_session, email=f"atthost@{DEMO_EMAIL_DOMAIN}", name="Att Host"
    )
    host = Host(
        user_id=host_user.id,
        display_name="Att Host",
        slug="att-host-" + uuid4().hex[:6],
        status="active",
    )
    db_session.add(host)
    db_session.flush()
    db_session.add(HostProfile(host_id=host.id, bio="Host", city="Lagos"))

    low, high = (
        (fan_a.id, fan_b.id)
        if str(fan_a.id) < str(fan_b.id)
        else (fan_b.id, fan_a.id)
    )
    fan_fan = MessageThread(
        thread_type=MC.THREAD_TYPE_FAN_FAN,
        fan_user_id=low,
        fan_b_user_id=high,
        host_id=None,
        host_user_id=high,
        status=MC.THREAD_STATUS_ACTIVE,
        subject="Product Demo Night",
        initiated_by_user_id=fan_a.id,
    )
    db_session.add(fan_fan)
    db_session.flush()
    m1 = Message(
        thread_id=fan_fan.id,
        sender_user_id=fan_a.id,
        sender_role="fan",
        message_type=MC.MESSAGE_TYPE_TEXT,
        body="Are you planning to join the demo circle?",
    )
    m2 = Message(
        thread_id=fan_fan.id,
        sender_user_id=fan_b.id,
        sender_role="fan",
        message_type=MC.MESSAGE_TYPE_TEXT,
        body="Yes, I want to watch first and maybe pitch next time.",
    )
    db_session.add_all([m1, m2])
    db_session.flush()

    n = seed_chidi_bayo_attachments(
        db_session, thread=fan_fan, chidi=fan_a, bayo=fan_b
    )
    assert n == 2

    fan_host = MessageThread(
        thread_type=MC.THREAD_TYPE_FAN_HOST,
        fan_user_id=fan_a.id,
        host_id=host.id,
        host_user_id=host_user.id,
        status=MC.THREAD_STATUS_ACTIVE,
        subject="Check-in",
        initiated_by_user_id=fan_a.id,
    )
    db_session.add(fan_host)
    db_session.flush()
    host_msg = Message(
        thread_id=fan_host.id,
        sender_user_id=host_user.id,
        sender_role="host",
        message_type=MC.MESSAGE_TYPE_TEXT,
        body="Doors open at 7 PM and check-in is fastest before 8:30 PM.",
    )
    late = Message(
        thread_id=fan_host.id,
        sender_user_id=fan_a.id,
        sender_role="fan",
        message_type=MC.MESSAGE_TYPE_TEXT,
        body="Can I still attend if I arrive late?",
    )
    db_session.add_all([host_msg, late])
    db_session.flush()

    assert (
        seed_tolu_maze_attachments(db_session, thread=fan_host, maze_user=host_user)
        == 1
    )
    assert seed_reported_thread_attachments(db_session, thread=fan_host, uploader=fan_a) == 1

    names = {
        a.original_filename
        for a in db_session.scalars(
            select(MessageAttachment).where(MessageAttachment.deleted_at.is_(None))
        ).all()
    }
    assert "product-demo-night-agenda.png" in names
    assert "demo-night-schedule.pdf" in names
    assert "afrobeats-entry-map.png" in names
    assert "demo-moderation-sample.png" in names

    ready = db_session.scalars(
        select(MessageAttachment).where(MessageAttachment.status == "ready")
    ).all()
    assert len(ready) >= 4
    for row in ready:
        assert row.storage_key
        assert row.url and "/api/v1/messages/attachments/" in row.url
        assert row.checksum_sha256

    # Idempotent re-seed returns existing rows (still counted)
    assert (
        seed_chidi_bayo_attachments(
            db_session, thread=fan_fan, chidi=fan_a, bayo=fan_b
        )
        == 2
    )
    again = ensure_message_attachment(
        db_session,
        message=host_msg,
        uploader=host_user,
        filename="afrobeats-entry-map.png",
        content_type="image/png",
        extension=".png",
        data=_entry_flow_png_bytes(),
        width=640,
        height=400,
    )
    assert again is not None
