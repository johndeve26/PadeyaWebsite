"""Idempotent edit / reply / pin / star enrichment for demo messaging threads.

Runs after scripted bodies exist. Never seeds phone, email, WhatsApp, bank links,
private venues, order/payment IDs, storage keys, or locked Vault content.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.demo.messaging_privacy import assert_safe_demo_copy
from app.messaging import constants as MC
from app.messaging.models import (
    Message,
    MessageEdit,
    MessagePin,
    MessageStar,
    MessageThread,
)
from app.users.models import User


def _now() -> datetime:
    return datetime.now(UTC)


def _message_by_body(
    db: Session, thread_id: UUID, body_substr: str
) -> Message | None:
    return db.scalar(
        select(Message)
        .where(
            Message.thread_id == thread_id,
            Message.body.contains(body_substr),
        )
        .order_by(Message.created_at.asc())
        .limit(1)
    )


def _ensure_edit(
    db: Session,
    *,
    message: Message,
    editor: User,
    previous_body: str,
    new_body: str,
    edited_minutes_ago: int = 50,
) -> None:
    assert_safe_demo_copy(previous_body, context="demo edit previous")
    assert_safe_demo_copy(new_body, context="demo edit new")
    message.body = new_body
    message.edited_at = _now() - timedelta(minutes=edited_minutes_ago)
    message.edit_count = max(int(message.edit_count or 0), 1)
    message.last_edited_by_user_id = editor.id
    existing = db.scalar(
        select(MessageEdit).where(MessageEdit.message_id == message.id).limit(1)
    )
    if existing is None:
        db.add(
            MessageEdit(
                message_id=message.id,
                editor_user_id=editor.id,
                previous_body=previous_body,
                new_body=new_body,
                edited_at=message.edited_at,
            )
        )
    else:
        existing.previous_body = previous_body
        existing.new_body = new_body
        existing.editor_user_id = editor.id
        existing.edited_at = message.edited_at
    db.flush()


def _ensure_reply(db: Session, *, message: Message, parent: Message) -> None:
    if parent.thread_id != message.thread_id:
        return
    message.reply_to_message_id = parent.id
    db.flush()


def _ensure_pin(
    db: Session,
    *,
    thread: MessageThread,
    message: Message,
    pinned_by: User,
) -> None:
    if message.thread_id != thread.id:
        return
    row = db.scalar(
        select(MessagePin).where(MessagePin.message_id == message.id).limit(1)
    )
    if row is None:
        db.add(
            MessagePin(
                thread_id=thread.id,
                message_id=message.id,
                pinned_by_user_id=pinned_by.id,
                pinned_at=_now() - timedelta(hours=2),
                unpinned_at=None,
            )
        )
    else:
        row.thread_id = thread.id
        row.pinned_by_user_id = pinned_by.id
        row.unpinned_at = None
        if row.pinned_at is None:
            row.pinned_at = _now() - timedelta(hours=2)
    db.flush()


def _ensure_star(
    db: Session,
    *,
    user: User,
    message: Message,
) -> None:
    row = db.scalar(
        select(MessageStar).where(
            MessageStar.user_id == user.id,
            MessageStar.message_id == message.id,
        )
    )
    if row is None:
        db.add(
            MessageStar(
                user_id=user.id,
                message_id=message.id,
                starred_at=_now() - timedelta(hours=1),
                unstarred_at=None,
            )
        )
    else:
        row.unstarred_at = None
        if row.starred_at is None:
            row.starred_at = _now() - timedelta(hours=1)
    db.flush()


def enrich_tolu_maze_chat_features(
    db: Session,
    *,
    thread: MessageThread,
    tolu: User,
    maze_user: User,
) -> dict[str, int]:
    """Tolu ↔ DJ Maze: edit, reply, pin, star (attachment seeded separately)."""
    counts = {"edits": 0, "replies": 0, "pins": 0, "stars": 0}

    edited = _message_by_body(db, thread.id, "use your QR code at check-in")
    if edited is None:
        edited = _message_by_body(db, thread.id, "show your QR code at check-in")
    if edited is None:
        edited = _message_by_body(db, thread.id, "Open your Pàdéyá ticket")
    if edited is not None and edited.sender_user_id == maze_user.id:
        _ensure_edit(
            db,
            message=edited,
            editor=maze_user,
            previous_body=(
                "Yes — open your Pàdéyá ticket and show your QR code at check-in."
            ),
            new_body=(
                "Yes — open your Pàdéyá ticket and use your QR code at check-in."
            ),
            edited_minutes_ago=55,
        )
        counts["edits"] = 1
        _ensure_star(db, user=tolu, message=edited)
        counts["stars"] = 1

    doors = _message_by_body(db, thread.id, "Doors open at 7 PM")
    reply = _message_by_body(db, thread.id, "I’ll aim for 7:15")
    if reply is None:
        reply = _message_by_body(db, thread.id, "aim for 7:15")
    if doors is not None and reply is not None:
        _ensure_reply(db, message=reply, parent=doors)
        counts["replies"] = 1

    pin_target = _message_by_body(
        db, thread.id, "connected to Afrobeats Night Live"
    )
    if pin_target is None:
        pin_target = doors
    if pin_target is not None:
        _ensure_pin(
            db, thread=thread, message=pin_target, pinned_by=maze_user
        )
        counts["pins"] = 1

    return counts


def enrich_chidi_bayo_chat_features(
    db: Session,
    *,
    thread: MessageThread,
    chidi: User,
    bayo: User,
) -> dict[str, int]:
    """Chidi ↔ Bayo: reply, pin event-context, edit, star, read/unread demo."""
    counts = {"edits": 0, "replies": 0, "pins": 0, "stars": 0}

    edited = _message_by_body(db, thread.id, "meet other builders")
    if edited is not None and edited.sender_user_id == chidi.id:
        _ensure_edit(
            db,
            message=edited,
            editor=chidi,
            previous_body="Same here. I’m mostly going to network.",
            new_body="Same here. I’m mostly going to meet other builders.",
            edited_minutes_ago=25,
        )
        counts["edits"] = 1

    parent = _message_by_body(db, thread.id, "watch first")
    reply = _message_by_body(db, thread.id, "look for you near the demo circle")
    if parent is not None and reply is not None:
        _ensure_reply(db, message=reply, parent=parent)
        counts["replies"] = 1

    # Pin the Fan Connect system / event-context line when present.
    pin_target = db.scalar(
        select(Message)
        .where(
            Message.thread_id == thread.id,
            Message.message_type == MC.MESSAGE_TYPE_SYSTEM,
        )
        .order_by(Message.created_at.asc())
        .limit(1)
    )
    if pin_target is None:
        pin_target = _message_by_body(db, thread.id, "Product Demo Night")
    if pin_target is not None:
        _ensure_pin(db, thread=thread, message=pin_target, pinned_by=chidi)
        counts["pins"] = 1

    star_target = parent or _message_by_body(db, thread.id, "See you there")
    if star_target is not None:
        _ensure_star(db, user=chidi, message=star_target)
        counts["stars"] = 1

    # Read receipt demo: low-UUID column set is fully caught up; high lags one message.
    msgs = list(
        db.scalars(
            select(Message)
            .where(Message.thread_id == thread.id)
            .order_by(Message.created_at.asc())
        ).all()
    )
    if len(msgs) >= 2:
        latest = msgs[-1]
        previous = msgs[-2]
        thread.fan_last_read_at = latest.created_at
        thread.host_last_read_at = previous.created_at
        db.flush()

    return counts


def enrich_reported_thread_chat_features(
    db: Session,
    *,
    thread: MessageThread,
) -> dict[str, int]:
    """Reported Bayo↔Tech: keep a reply link for admin moderation context."""
    counts = {"replies": 0}
    parent = _message_by_body(db, thread.id, "what would you like to know")
    child = _message_by_body(db, thread.id, "arrive late")
    if parent is not None and child is not None:
        _ensure_reply(db, message=child, parent=parent)
        counts["replies"] = 1
    return counts
