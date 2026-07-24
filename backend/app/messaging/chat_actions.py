"""Edit, reply, pin, star, and delete-for-me actions for in-app messaging.

Permission gates live in `app.messaging.permissions` — call those for new actions.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from app.messaging import constants as C
from app.messaging.models import (
    Message,
    MessageAttachment,
    MessageDeletion,
    MessageEdit,
    MessagePin,
    MessageStar,
    MessageThread,
)
from app.messaging.permissions import (
    assert_can_delete_message_for_me,
    assert_can_edit_message,
    assert_can_pin_message,
    assert_can_read_thread,
    assert_can_reply_to_message,
    assert_can_send_message,
    assert_can_star_message,
    can_send_message,
)
from app.users.models import User


def thread_can_reply(db: Session, user: User, thread: MessageThread) -> bool:
    """Backward-compatible alias of `can_send_message`."""
    return can_send_message(db, user, thread)


def assert_can_reply(db: Session, user: User, thread: MessageThread) -> None:
    """Backward-compatible alias — prefer `assert_can_send_message`."""
    try:
        assert_can_send_message(db, user, thread)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_403_FORBIDDEN:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="You cannot reply in this thread.",
            ) from exc
        raise


def _message_is_redacted(msg: Message) -> bool:
    return (
        msg.status
        in {C.MESSAGE_STATUS_HIDDEN, C.MESSAGE_STATUS_DELETED}
        or msg.moderation_status == C.MOD_HIDDEN
        or msg.deleted_at is not None
    )


def message_deleted_for_user_ids(
    db: Session, viewer_id: UUID, message_ids: list[UUID]
) -> set[UUID]:
    """Message ids the viewer has soft-deleted for themselves."""
    if not message_ids:
        return set()
    rows = db.scalars(
        select(MessageDeletion.message_id).where(
            MessageDeletion.user_id == viewer_id,
            MessageDeletion.message_id.in_(message_ids),
            MessageDeletion.delete_scope == C.DELETE_SCOPE_FOR_ME,
        )
    ).all()
    return set(rows)


def is_deleted_for_user(db: Session, message_id: UUID, viewer_id: UUID) -> bool:
    return (
        db.scalar(
            select(MessageDeletion.id).where(
                MessageDeletion.message_id == message_id,
                MessageDeletion.user_id == viewer_id,
                MessageDeletion.delete_scope == C.DELETE_SCOPE_FOR_ME,
            )
        )
        is not None
    )


def delete_message_for_me(
    db: Session,
    user: User,
    message_id: UUID,
    *,
    thread_id: UUID | None = None,
) -> Message:
    """Hide a message for the current user only — peer still sees the original."""
    from app.messaging.service import _now

    msg = db.get(Message, message_id)
    if msg is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Message not found.")
    if thread_id is not None and msg.thread_id != thread_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Message not found.")

    thread, _ = assert_can_read_thread(db, user, msg.thread_id)
    assert_can_delete_message_for_me(db, user, thread, msg)

    existing = db.scalar(
        select(MessageDeletion).where(
            MessageDeletion.message_id == message_id,
            MessageDeletion.user_id == user.id,
            MessageDeletion.delete_scope == C.DELETE_SCOPE_FOR_ME,
        )
    )
    if existing is None:
        db.add(
            MessageDeletion(
                message_id=message_id,
                user_id=user.id,
                delete_scope=C.DELETE_SCOPE_FOR_ME,
                deleted_at=_now(),
            )
        )
        # Soft-unstar so starred list does not keep a live pointer to content.
        star = db.scalar(
            select(MessageStar).where(
                MessageStar.user_id == user.id,
                MessageStar.message_id == message_id,
                MessageStar.unstarred_at.is_(None),
            )
        )
        if star is not None:
            star.unstarred_at = _now()
            db.add(star)
        db.commit()
    return msg


def _require_thread_message(
    db: Session, thread_id: UUID, message_id: UUID
) -> Message:
    msg = db.get(Message, message_id)
    if msg is None or msg.thread_id != thread_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Message not found.")
    return msg


def validate_reply_target(
    db: Session,
    user: User,
    *,
    thread_id: UUID,
    reply_to_message_id: UUID,
) -> Message:
    """Reply only to an accessible same-thread text/attachment message."""
    parent = _require_thread_message(db, thread_id, reply_to_message_id)
    thread, _ = assert_can_read_thread(db, user, thread_id)
    assert_can_reply_to_message(db, user, thread, parent)
    return parent


def edit_message(
    db: Session,
    user: User,
    message_id: UUID,
    body: str,
    *,
    thread_id: UUID | None = None,
) -> Message:
    """Edit own message body. Admins use hide/restore moderation — not this path."""
    from app.messaging import ws_events
    from app.messaging.service import (
        _load_attachments,
        _now,
        _preview,
        _soft_flag,
    )

    msg = db.get(Message, message_id)
    if msg is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Message not found.")
    if thread_id is not None and msg.thread_id != thread_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Message not found.")

    thread, _as_host = assert_can_read_thread(db, user, msg.thread_id)
    assert_can_edit_message(db, user, thread, msg)

    text = (body or "").strip()
    if not text:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Message body cannot be empty."
        )
    if len(text) > C.MAX_BODY_LENGTH:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid message body.")

    previous = msg.body or ""
    if previous == text:
        return msg

    db.add(
        MessageEdit(
            message_id=msg.id,
            editor_user_id=user.id,
            previous_body=previous,
            new_body=text,
            edited_at=_now(),
        )
    )
    msg.body = text
    msg.edited_at = _now()
    msg.edit_count = int(msg.edit_count or 0) + 1
    msg.last_edited_by_user_id = user.id
    msg.moderation_status = _soft_flag(text)
    db.add(msg)

    # Refresh thread preview when editing the latest message (inbox list).
    if thread.last_message_id == msg.id:
        atts = _load_attachments(db, msg.id)
        thread.last_message_preview = _preview(
            text,
            has_attachments=bool(atts),
            attachment_content_types=[a.mime_type for a in atts],
        )
        db.add(thread)

    db.commit()
    db.refresh(msg)
    ws_events.publish_message_updated(db, thread=thread, message=msg)
    if thread.last_message_id == msg.id:
        ws_events.publish_thread_updated(thread)
    return msg


def assert_can_pin(db: Session, user: User, thread: MessageThread) -> None:
    """Backward-compatible alias of `assert_can_pin_message`."""
    assert_can_pin_message(db, user, thread)


def pin_message(
    db: Session,
    user: User,
    message_id: UUID,
    *,
    thread_id: UUID | None = None,
) -> list[Message]:
    from app.messaging import ws_events
    from app.messaging.service import _now

    msg = db.get(Message, message_id)
    if msg is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Message not found.")
    if thread_id is not None and msg.thread_id != thread_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Message not found.")

    thread, _ = assert_can_read_thread(db, user, msg.thread_id)
    assert_can_pin_message(db, user, thread)
    if _message_is_redacted(msg) or is_deleted_for_user(db, msg.id, user.id):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Cannot pin a removed message."
        )

    existing = db.scalar(
        select(MessagePin).where(MessagePin.message_id == message_id)
    )
    if existing is not None and existing.unpinned_at is None:
        pinned = list_pinned_messages(db, thread.id)
        return pinned

    active_count = db.scalar(
        select(func.count())
        .select_from(MessagePin)
        .where(
            MessagePin.thread_id == thread.id,
            MessagePin.unpinned_at.is_(None),
        )
    )
    if existing is None and int(active_count or 0) >= C.MAX_PINS_PER_THREAD:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"At most {C.MAX_PINS_PER_THREAD} pinned messages allowed.",
        )
    if existing is None:
        db.add(
            MessagePin(
                thread_id=thread.id,
                message_id=message_id,
                pinned_by_user_id=user.id,
                pinned_at=_now(),
                unpinned_at=None,
            )
        )
    else:
        # Re-pin after soft unpin.
        if int(active_count or 0) >= C.MAX_PINS_PER_THREAD:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"At most {C.MAX_PINS_PER_THREAD} pinned messages allowed.",
            )
        existing.unpinned_at = None
        existing.pinned_by_user_id = user.id
        existing.pinned_at = _now()
        db.add(existing)
    db.commit()

    pinned = list_pinned_messages(db, thread.id)
    ws_events.publish_message_pinned(
        db, thread=thread, message_id=message_id, pinned=pinned, viewer_hint=user.id
    )
    ws_events.publish_thread_updated(thread)
    return pinned


def unpin_message(
    db: Session,
    user: User,
    message_id: UUID,
    *,
    thread_id: UUID | None = None,
) -> list[Message]:
    from app.messaging import ws_events
    from app.messaging.service import _now

    msg = db.get(Message, message_id)
    if msg is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Message not found.")
    if thread_id is not None and msg.thread_id != thread_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Message not found.")

    thread, _ = assert_can_read_thread(db, user, msg.thread_id)
    assert_can_pin_message(db, user, thread)
    row = db.scalar(
        select(MessagePin).where(
            MessagePin.message_id == message_id,
            MessagePin.unpinned_at.is_(None),
        )
    )
    if row is not None:
        row.unpinned_at = _now()
        db.add(row)
        db.commit()
    pinned = list_pinned_messages(db, thread.id)
    ws_events.publish_message_unpinned(
        db, thread=thread, message_id=message_id, pinned=pinned, viewer_hint=user.id
    )
    ws_events.publish_thread_updated(thread)
    return pinned


def list_pinned_messages(db: Session, thread_id: UUID) -> list[Message]:
    """Active public pins — hidden/deleted messages are excluded."""
    pins = list(
        db.scalars(
            select(MessagePin)
            .where(
                MessagePin.thread_id == thread_id,
                MessagePin.unpinned_at.is_(None),
            )
            .order_by(MessagePin.pinned_at.asc())
        ).all()
    )
    out: list[Message] = []
    for pin in pins:
        msg = db.get(Message, pin.message_id)
        if msg is None or _message_is_redacted(msg):
            # Soft-clear so deleted/hidden do not stay pinned publicly.
            if pin.unpinned_at is None:
                from app.messaging.service import _now

                pin.unpinned_at = _now()
                db.add(pin)
            continue
        out.append(msg)
    if any(p.unpinned_at is not None for p in pins):
        db.commit()
    return out


def list_pins_payload(
    db: Session, user: User, thread_id: UUID
) -> dict:
    from app.messaging.service import serialize_message

    thread, _ = assert_can_read_thread(db, user, thread_id)
    pinned = [
        m
        for m in list_pinned_messages(db, thread.id)
        if not is_deleted_for_user(db, m.id, user.id)
    ]
    pin_ids = {m.id for m in pinned}
    star_ids = starred_message_ids(db, user.id, [m.id for m in pinned])
    deleted_ids = message_deleted_for_user_ids(db, user.id, [m.id for m in pinned])
    return {
        "items": [
            serialize_message(
                db,
                m,
                viewer_id=user.id,
                pinned_ids=pin_ids,
                starred_ids=star_ids,
                deleted_for_me_ids=deleted_ids,
            )
            for m in pinned
        ],
        "total": len(pinned),
    }


def clear_pins_for_message(db: Session, message_id: UUID) -> None:
    row = db.scalar(
        select(MessagePin).where(
            MessagePin.message_id == message_id,
            MessagePin.unpinned_at.is_(None),
        )
    )
    if row is not None:
        from app.messaging.service import _now

        row.unpinned_at = _now()
        db.add(row)


def star_message(
    db: Session,
    user: User,
    message_id: UUID,
    *,
    thread_id: UUID | None = None,
) -> Message:
    """Personal star — never notifies peers; soft-reopens prior unstars."""
    from app.messaging.service import _now

    msg = db.get(Message, message_id)
    if msg is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Message not found.")
    if thread_id is not None and msg.thread_id != thread_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Message not found.")

    thread, _ = assert_can_read_thread(db, user, msg.thread_id)
    assert_can_star_message(db, user, thread, msg)

    existing = db.scalar(
        select(MessageStar).where(
            MessageStar.user_id == user.id,
            MessageStar.message_id == message_id,
        )
    )
    if existing is None:
        db.add(
            MessageStar(
                user_id=user.id,
                message_id=message_id,
                starred_at=_now(),
                unstarred_at=None,
            )
        )
        db.commit()
    elif existing.unstarred_at is not None:
        existing.unstarred_at = None
        existing.starred_at = _now()
        db.add(existing)
        db.commit()
    return msg


def unstar_message(
    db: Session,
    user: User,
    message_id: UUID,
    *,
    thread_id: UUID | None = None,
) -> Message:
    """Soft-unstar — row kept with unstarred_at; peer is never notified."""
    from app.messaging.service import _now

    msg = db.get(Message, message_id)
    if msg is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Message not found.")
    if thread_id is not None and msg.thread_id != thread_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Message not found.")

    assert_can_read_thread(db, user, msg.thread_id)
    row = db.scalar(
        select(MessageStar).where(
            MessageStar.user_id == user.id,
            MessageStar.message_id == message_id,
            MessageStar.unstarred_at.is_(None),
        )
    )
    if row is not None:
        row.unstarred_at = _now()
        db.add(row)
        db.commit()
    return msg


def starred_message_ids(
    db: Session, viewer_id: UUID, message_ids: list[UUID]
) -> set[UUID]:
    if not message_ids:
        return set()
    rows = db.scalars(
        select(MessageStar.message_id).where(
            MessageStar.user_id == viewer_id,
            MessageStar.message_id.in_(message_ids),
            MessageStar.unstarred_at.is_(None),
        )
    ).all()
    return set(rows)


def pinned_message_ids(db: Session, thread_id: UUID) -> set[UUID]:
    rows = db.scalars(
        select(MessagePin.message_id).where(
            MessagePin.thread_id == thread_id,
            MessagePin.unpinned_at.is_(None),
        )
    ).all()
    return set(rows)


def list_starred_for_user(
    db: Session, user: User, *, page: int = 1, limit: int = 30
) -> dict:
    """Active personal stars. Hidden/deleted bodies are redacted by serialize.

    Stars on threads the viewer can no longer access are omitted (not a bypass).
    """
    from app.messaging.service import (
        serialize_message,
        serialize_thread_list_item,
    )

    limit = min(max(limit, 1), 50)
    page = max(page, 1)
    # Personal star lists stay small — filter access in Python for accurate total.
    stars = list(
        db.scalars(
            select(MessageStar)
            .where(
                MessageStar.user_id == user.id,
                MessageStar.unstarred_at.is_(None),
            )
            .order_by(MessageStar.starred_at.desc())
            .limit(500)
        ).all()
    )
    accessible: list[dict] = []
    for star in stars:
        msg = db.get(Message, star.message_id)
        if msg is None:
            continue
        if is_deleted_for_user(db, msg.id, user.id):
            continue
        try:
            thread, as_host = assert_can_read_thread(db, user, msg.thread_id)
        except HTTPException:
            continue
        thread_item = serialize_thread_list_item(
            db, thread, viewer=user, as_host=as_host
        )
        # serialize_message redacts hidden/deleted content for the starred list.
        accessible.append(
            {
                "message": serialize_message(
                    db,
                    msg,
                    viewer_id=user.id,
                    starred_ids={msg.id},
                ),
                "thread_id": str(thread.id),
                "thread_type": thread.thread_type,
                "counterpart": thread_item["counterpart"],
                "starred_at": star.starred_at,
            }
        )
    total = len(accessible)
    start = (page - 1) * limit
    items = accessible[start : start + limit]
    return {"items": items, "page": page, "limit": limit, "total": total}


def _ilike_contains(needle: str) -> str:
    """Escape ILIKE wildcards for a simple contains match (no FTS index)."""
    escaped = (
        needle.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    )
    return f"%{escaped}%"


def search_thread_messages(
    db: Session,
    user: User,
    thread_id: UUID,
    *,
    q: str | None = None,
    starred: bool = False,
    pinned: bool = False,
    has_attachments: bool = False,
    limit: int = 40,
) -> dict:
    """Simple in-thread search — body ILIKE + optional star/pin/attachment filters.

    Scoped to one thread the viewer can access. No full-text index.
    """
    from app.messaging.service import serialize_message

    thread, _ = assert_can_read_thread(db, user, thread_id)
    limit = min(max(limit, 1), 50)
    needle = (q or "").strip()

    if not needle and not starred and not pinned and not has_attachments:
        return {"items": [], "total": 0, "q": "", "filters": {}}

    stmt = select(Message).where(Message.thread_id == thread.id)
    # Never match hidden/deleted bodies — serialize redaction is not enough for search.
    stmt = stmt.where(
        Message.status.notin_(
            [C.MESSAGE_STATUS_HIDDEN, C.MESSAGE_STATUS_DELETED]
        ),
        Message.moderation_status != C.MOD_HIDDEN,
        Message.deleted_at.is_(None),
    )

    if needle:
        stmt = stmt.where(
            Message.body.ilike(_ilike_contains(needle), escape="\\")
        )

    if starred:
        stmt = stmt.where(
            exists(
                select(MessageStar.id).where(
                    MessageStar.message_id == Message.id,
                    MessageStar.user_id == user.id,
                    MessageStar.unstarred_at.is_(None),
                )
            )
        )

    if pinned:
        stmt = stmt.where(
            exists(
                select(MessagePin.id).where(
                    MessagePin.message_id == Message.id,
                    MessagePin.thread_id == thread.id,
                    MessagePin.unpinned_at.is_(None),
                )
            )
        )

    if has_attachments:
        stmt = stmt.where(
            exists(
                select(MessageAttachment.id).where(
                    MessageAttachment.message_id == Message.id,
                    MessageAttachment.deleted_at.is_(None),
                    MessageAttachment.status == "ready",
                )
            )
        )

    # Never surface for_me-deleted rows in search (body still exists in DB).
    stmt = stmt.where(
        ~exists(
            select(MessageDeletion.id).where(
                MessageDeletion.message_id == Message.id,
                MessageDeletion.user_id == user.id,
                MessageDeletion.delete_scope == C.DELETE_SCOPE_FOR_ME,
            )
        )
    )

    stmt = stmt.order_by(Message.created_at.desc()).limit(limit)
    rows = list(db.scalars(stmt).all())
    pin_ids = pinned_message_ids(db, thread.id)
    star_ids = starred_message_ids(db, user.id, [m.id for m in rows])
    items = [
        serialize_message(
            db,
            m,
            viewer_id=user.id,
            pinned_ids=pin_ids,
            starred_ids=star_ids,
        )
        for m in rows
    ]
    return {
        "items": items,
        "total": len(items),
        "q": needle,
        "filters": {
            "starred": starred,
            "pinned": pinned,
            "has_attachments": has_attachments,
        },
    }
