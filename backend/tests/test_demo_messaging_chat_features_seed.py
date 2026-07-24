"""Demo chat-feature enrichment — edit / reply / pin / star / reported reply."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.demo.messaging_chat_features_seed import (
    enrich_chidi_bayo_chat_features,
    enrich_reported_thread_chat_features,
    enrich_tolu_maze_chat_features,
)
from app.hosts.models import Host, HostProfile
from app.messaging import constants as MC
from app.messaging.models import (
    Message,
    MessageEdit,
    MessagePin,
    MessageStar,
    MessageThread,
)
from app.users.models import User
from app.users.service import get_role_by_name


def _now() -> datetime:
    return datetime.now(UTC)


def _user(db: Session, email: str, name: str) -> User:
    u = User(
        email=email,
        password_hash=hash_password("securepass1"),
        full_name=name,
        is_active=True,
    )
    u.roles.append(get_role_by_name(db, "buyer"))
    db.add(u)
    db.flush()
    return u


def _host(db: Session, owner: User) -> Host:
    host = Host(
        user_id=owner.id,
        display_name="DJ Maze",
        slug="djmaze-cf-" + uuid4().hex[:6],
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, bio="Host", city="Lagos"))
    db.flush()
    return host


def _msg(
    db: Session,
    *,
    thread: MessageThread,
    sender: User,
    role: str,
    body: str,
    mins: int,
    message_type: str = MC.MESSAGE_TYPE_TEXT,
) -> Message:
    created = _now() - timedelta(minutes=mins)
    msg = Message(
        thread_id=thread.id,
        sender_user_id=sender.id,
        sender_role=role,
        body=body,
        message_type=message_type,
        status=MC.MESSAGE_STATUS_SENT,
        moderation_status=MC.MOD_CLEAN,
        created_at=created,
        updated_at=created,
    )
    db.add(msg)
    db.flush()
    return msg


def test_enrich_tolu_maze_sets_edit_reply_pin_star(db_session: Session):
    maze_owner = _user(db_session, "maze-cf@example.com", "Maze")
    maze_owner.roles.append(get_role_by_name(db_session, "host"))
    tolu = _user(db_session, "tolu-cf@example.com", "Tolu")
    host = _host(db_session, maze_owner)
    thread = MessageThread(
        thread_type=MC.THREAD_TYPE_FAN_HOST,
        fan_user_id=tolu.id,
        host_id=host.id,
        host_user_id=maze_owner.id,
        status=MC.THREAD_STATUS_ACTIVE,
        initiated_by_user_id=tolu.id,
    )
    db_session.add(thread)
    db_session.flush()

    _msg(
        db_session,
        thread=thread,
        sender=maze_owner,
        role="system",
        body="This conversation is connected to Afrobeats Night Live.",
        mins=100,
        message_type=MC.MESSAGE_TYPE_SYSTEM,
    )
    doors = _msg(
        db_session,
        thread=thread,
        sender=maze_owner,
        role="host",
        body="Hey Tolu, thanks for getting your ticket. Doors open at 7 PM and check-in is fastest before 8:30 PM.",
        mins=80,
    )
    edited = _msg(
        db_session,
        thread=thread,
        sender=maze_owner,
        role="host",
        body="Yes — open your Pàdéyá ticket and use your QR code at check-in.",
        mins=60,
    )
    reply = _msg(
        db_session,
        thread=thread,
        sender=tolu,
        role="fan",
        body="Thanks — I’ll aim for 7:15 PM so check-in is easy.",
        mins=5,
    )
    db_session.commit()

    counts = enrich_tolu_maze_chat_features(
        db_session, thread=thread, tolu=tolu, maze_user=maze_owner
    )
    db_session.commit()

    assert counts["edits"] == 1
    assert counts["replies"] == 1
    assert counts["pins"] == 1
    assert counts["stars"] == 1

    from sqlalchemy import func, select

    db_session.refresh(edited)
    db_session.refresh(reply)
    assert edited.edited_at is not None
    assert edited.edit_count >= 1
    assert reply.reply_to_message_id == doors.id
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(MessagePin)
            .where(MessagePin.thread_id == thread.id)
        )
        == 1
    )
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(MessageStar)
            .where(
                MessageStar.user_id == tolu.id,
                MessageStar.message_id == edited.id,
            )
        )
        == 1
    )
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(MessageEdit)
            .where(MessageEdit.message_id == edited.id)
        )
        == 1
    )


def test_enrich_chidi_bayo_and_reported_reply(db_session: Session):
    chidi = _user(db_session, "chidi-cf@example.com", "Chidi")
    bayo = _user(db_session, "bayo-cf@example.com", "Bayo")
    # Stable low/high for read columns (host_user_id mirrors high fan for fan_fan).
    low, high = (chidi, bayo) if chidi.id < bayo.id else (bayo, chidi)
    thread = MessageThread(
        thread_type=MC.THREAD_TYPE_FAN_FAN,
        fan_user_id=low.id,
        fan_b_user_id=high.id,
        host_user_id=high.id,
        status=MC.THREAD_STATUS_ACTIVE,
        initiated_by_user_id=chidi.id,
    )
    db_session.add(thread)
    db_session.flush()
    _msg(
        db_session,
        thread=thread,
        sender=chidi,
        role="system",
        body="You connected through Product Demo Night on Pàdéyá.",
        mins=60,
        message_type=MC.MESSAGE_TYPE_SYSTEM,
    )
    parent = _msg(
        db_session,
        thread=thread,
        sender=bayo,
        role="fan",
        body="Yes, I want to watch first and maybe pitch next time.",
        mins=40,
    )
    _msg(
        db_session,
        thread=thread,
        sender=chidi,
        role="fan",
        body="Same here. I’m mostly going to meet other builders.",
        mins=30,
    )
    _msg(
        db_session,
        thread=thread,
        sender=bayo,
        role="fan",
        body="Cool. See you there.",
        mins=20,
    )
    reply = _msg(
        db_session,
        thread=thread,
        sender=chidi,
        role="fan",
        body="Perfect — I’ll look for you near the demo circle.",
        mins=10,
    )
    db_session.commit()

    counts = enrich_chidi_bayo_chat_features(
        db_session, thread=thread, chidi=chidi, bayo=bayo
    )
    db_session.commit()
    db_session.refresh(thread)
    db_session.refresh(reply)

    assert counts["pins"] == 1
    assert counts["stars"] == 1
    assert counts["replies"] == 1
    assert counts["edits"] == 1
    assert reply.reply_to_message_id == parent.id
    assert thread.fan_last_read_at is not None
    assert thread.host_last_read_at is not None
    assert thread.host_last_read_at <= thread.fan_last_read_at

    # Reported reply context
    host_u = _user(db_session, "tech-cf@example.com", "Tech")
    host_u.roles.append(get_role_by_name(db_session, "host"))
    host = _host(db_session, host_u)
    reported = MessageThread(
        thread_type=MC.THREAD_TYPE_FAN_HOST,
        fan_user_id=bayo.id,
        host_id=host.id,
        host_user_id=host_u.id,
        status=MC.THREAD_STATUS_REPORTED,
        initiated_by_user_id=bayo.id,
    )
    db_session.add(reported)
    db_session.flush()
    q = _msg(
        db_session,
        thread=reported,
        sender=host_u,
        role="host",
        body="Sure, what would you like to know?",
        mins=30,
    )
    late = _msg(
        db_session,
        thread=reported,
        sender=bayo,
        role="fan",
        body="Can I still attend if I arrive late?",
        mins=20,
    )
    db_session.commit()
    assert enrich_reported_thread_chat_features(db_session, thread=reported)[
        "replies"
    ] == 1
    db_session.refresh(late)
    assert late.reply_to_message_id == q.id
