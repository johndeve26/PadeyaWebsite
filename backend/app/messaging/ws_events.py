"""Typed WebSocket fan-out. REST remains send authority.

Event names use dotted form (message.created, thread.updated, …).
Message bodies and attachment URLs are only sent to authorized thread participants.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.messaging import constants as C
from app.messaging.models import Message, MessageAttachment, MessageThread
from app.messaging.ws_hub import messaging_hub
from app.users.models import User

# Canonical server → client event types
EVT_MESSAGE_CREATED = "message.created"
EVT_MESSAGE_UPDATED = "message.updated"
EVT_MESSAGE_DELETED = "message.deleted"
EVT_MESSAGE_READ = "message.read"
EVT_MESSAGE_TYPING = "message.typing"
EVT_THREAD_UPDATED = "thread.updated"
EVT_THREAD_UNREAD = "thread.unread_count_updated"
EVT_THREAD_DISABLED = "thread.disabled"
EVT_CONNECTION_ACCEPTED = "connection.accepted"
EVT_CONNECTION_REMOVED = "connection.removed"
EVT_ATTACHMENT_READY = "attachment.ready"
EVT_ATTACHMENT_FAILED = "attachment.failed"
EVT_MESSAGE_PINNED = "message.pinned"
EVT_MESSAGE_UNPINNED = "message.unpinned"
EVT_NOTIFICATION_CREATED = "notification.created"


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def participants(thread: MessageThread) -> list[UUID]:
    from app.messaging.ws_permissions import thread_participant_ids

    return thread_participant_ids(thread)


def publish_to_users(
    user_ids: list[UUID],
    payload: dict[str, Any],
    *,
    db: Session | None = None,
) -> None:
    """Fan-out after server-side receive permission filter (never trust FE).

    When the caller already holds a Session (REST/accept paths), pass it in.
    Nested SessionLocal() on StaticPool shares one SQLite connection and can
    interleave cursors during filter queries (IndexError in row processors).
    """
    from app.core import database as database_module
    from app.messaging.ws_permissions import (
        PERSONAL_EVENTS,
        filter_event_recipients,
    )

    event_type = str(payload.get("type") or "")
    thread_id: UUID | None = None
    raw_tid = payload.get("thread_id")
    if raw_tid is not None:
        try:
            thread_id = UUID(str(raw_tid))
        except (TypeError, ValueError):
            thread_id = None

    targets = list(user_ids)
    if thread_id is not None and event_type not in PERSONAL_EVENTS:
        owns_session = False
        filter_db = db
        if filter_db is None:
            filter_db = database_module.SessionLocal()
            owns_session = True
        try:
            targets = filter_event_recipients(
                filter_db,
                targets,
                thread_id=thread_id,
                event_type=event_type,
            )
        finally:
            if owns_session:
                filter_db.close()
    if not targets:
        return
    messaging_hub.publish(targets, payload)


def _normalize_message_public(payload_msg: dict[str, Any]) -> dict[str, Any]:
    def _iso_field(value: Any) -> Any:
        return value.isoformat() if hasattr(value, "isoformat") else value

    out = {
        **payload_msg,
        "created_at": _iso_field(payload_msg.get("created_at")),
        "edited_at": _iso_field(payload_msg.get("edited_at")),
    }
    reply = payload_msg.get("reply_to")
    if isinstance(reply, dict):
        out["reply_to"] = {
            **reply,
            "reply_created_at": _iso_field(reply.get("reply_created_at")),
        }
    return out


def publish_unread_count(db: Session, user_id: UUID) -> None:
    from app.messaging.service import unread_count_for_user
    from app.users.service import get_user_by_id

    user = get_user_by_id(db, user_id)
    if user is None:
        return
    n = unread_count_for_user(db, user)
    publish_to_users(
        [user_id],
        {
            "type": EVT_THREAD_UNREAD,
            "unread_count": n,
        },
        db=db,
    )


def publish_thread_updated(
    thread: MessageThread,
    *,
    viewer_ids: list[UUID] | None = None,
    unread_for: UUID | None = None,
    extra: dict[str, Any] | None = None,
    db: Session | None = None,
) -> None:
    targets = viewer_ids or participants(thread)
    for uid in targets:
        payload: dict[str, Any] = {
            "type": EVT_THREAD_UPDATED,
            "thread_id": str(thread.id),
            "status": thread.status,
            "is_request": thread.status == C.THREAD_STATUS_REQUEST,
            "blocked": thread.status == C.THREAD_STATUS_BLOCKED,
            "can_reply": thread.status
            not in {
                C.THREAD_STATUS_BLOCKED,
                C.THREAD_STATUS_CLOSED,
                C.THREAD_STATUS_REPORTED,
            },
            # Preview only — never a full message body on thread.updated
            "last_message_preview": thread.last_message_preview,
            "last_message_at": _iso(thread.last_message_at),
            "unread": bool(unread_for is not None and uid == unread_for),
        }
        if extra:
            payload.update(extra)
        publish_to_users([uid], payload, db=db)


def publish_new_message(
    db: Session,
    *,
    thread: MessageThread,
    message: Message,
    sender_id: UUID,
) -> None:
    """message.created — full body only to authorized participants."""
    from app.messaging.service import serialize_message

    participant_ids = participants(thread)
    for uid in participant_ids:
        # Authorization gate: only participants receive the body/attachment URLs.
        # Publish on user channels so every worker holding that user's socket gets it
        # (inbox open without thread.subscribe still works).
        payload_msg = serialize_message(db, message, viewer_id=uid)
        publish_to_users(
            [uid],
            {
                "type": EVT_MESSAGE_CREATED,
                "thread_id": str(thread.id),
                "message": _normalize_message_public(payload_msg),
            },
            db=db,
        )

    for uid in participant_ids:
        publish_thread_updated(
            thread,
            viewer_ids=[uid],
            unread_for=uid if uid != sender_id else None,
            db=db,
        )

    for uid in participant_ids:
        publish_unread_count(db, uid)

    recipients = [uid for uid in participant_ids if uid != sender_id]
    if any(messaging_hub.is_online(uid) for uid in recipients):
        if message.status == C.MESSAGE_STATUS_SENT:
            message.status = C.MESSAGE_STATUS_DELIVERED
            db.add(message)
            try:
                db.commit()
            except Exception:  # noqa: BLE001
                db.rollback()
        publish_to_users(
            [sender_id],
            {
                "type": EVT_MESSAGE_UPDATED,
                "thread_id": str(thread.id),
                "message_id": str(message.id),
                "status": C.MESSAGE_STATUS_DELIVERED,
            },
            db=db,
        )


def publish_message_updated(
    db: Session,
    *,
    thread: MessageThread,
    message: Message,
) -> None:
    from app.messaging.service import serialize_message

    for uid in participants(thread):
        payload_msg = serialize_message(db, message, viewer_id=uid)
        publish_to_users(
            [uid],
            {
                "type": EVT_MESSAGE_UPDATED,
                "thread_id": str(thread.id),
                "message": _normalize_message_public(payload_msg),
            },
            db=db,
        )


def publish_message_deleted(
    db: Session,
    *,
    thread: MessageThread,
    message: Message,
) -> None:
    from app.messaging.service import serialize_message

    for uid in participants(thread):
        # Redacted body/attachments via serializer for hidden/deleted
        payload_msg = serialize_message(db, message, viewer_id=uid)
        publish_to_users(
            [uid],
            {
                "type": EVT_MESSAGE_DELETED,
                "thread_id": str(thread.id),
                "message_id": str(message.id),
                "message": _normalize_message_public(payload_msg),
            },
            db=db,
        )


def _pinned_payload(
    db: Session,
    *,
    thread: MessageThread,
    message_id: UUID,
    pinned: list[Message],
    event_type: str,
) -> None:
    from app.messaging.service import serialize_message

    for uid in participants(thread):
        pinned_public = [
            _normalize_message_public(
                serialize_message(db, m, viewer_id=uid)
            )
            for m in pinned
        ]
        publish_to_users(
            [uid],
            {
                "type": event_type,
                "thread_id": str(thread.id),
                "message_id": str(message_id),
                "pinned_messages": pinned_public,
            },
            db=db,
        )


def publish_message_pinned(
    db: Session,
    *,
    thread: MessageThread,
    message_id: UUID,
    pinned: list[Message],
    viewer_hint: UUID | None = None,
) -> None:
    del viewer_hint  # reserved for future per-viewer pin metadata
    _pinned_payload(
        db,
        thread=thread,
        message_id=message_id,
        pinned=pinned,
        event_type=EVT_MESSAGE_PINNED,
    )


def publish_message_unpinned(
    db: Session,
    *,
    thread: MessageThread,
    message_id: UUID,
    pinned: list[Message],
    viewer_hint: UUID | None = None,
) -> None:
    del viewer_hint
    _pinned_payload(
        db,
        thread=thread,
        message_id=message_id,
        pinned=pinned,
        event_type=EVT_MESSAGE_UNPINNED,
    )


def publish_thread_read(
    db: Session,
    thread: MessageThread,
    *,
    reader_id: UUID,
    read_at: datetime,
) -> None:
    """Thread-level read receipt (fan_last_read_at / host_last_read_at).

    - Receipt event goes only to other valid participants (never self-spoof).
    - Reader gets thread.updated with unread cleared + unread_count refresh.
    - reader_id is always the authenticated marker from mark_read — never client-supplied.
    """
    participant_ids = participants(thread)
    others = [uid for uid in participant_ids if uid != reader_id]
    if others:
        publish_to_users(
            others,
            {
                "type": EVT_MESSAGE_READ,
                "thread_id": str(thread.id),
                "reader_id": str(reader_id),
                "read_at": _iso(read_at),
            },
            db=db,
        )
    # Clear unread on the reader's inbox row in real time.
    publish_thread_updated(
        thread,
        viewer_ids=[reader_id],
        unread_for=None,
        extra={"unread": False},
        db=db,
    )
    for uid in participant_ids:
        publish_unread_count(db, uid)


def publish_typing(
    *,
    thread_id: UUID,
    from_user_id: UUID,
    participant_ids: list[UUID],
    is_typing: bool = True,
    display_name: str | None = None,
) -> None:
    """Ephemeral typing fan-out — never persisted; peers only (not sender)."""
    others = [uid for uid in participant_ids if uid != from_user_id]
    if not others:
        return
    # Prefer user channels for multi-worker reliability (works without thread.subscribe).
    # display_name is safe public label only (no email/phone/contact).
    payload: dict[str, Any] = {
        "type": EVT_MESSAGE_TYPING,
        "thread_id": str(thread_id),
        "user_id": str(from_user_id),
        "is_typing": is_typing,
    }
    name = (display_name or "").strip()
    if name:
        payload["display_name"] = name[:80]
    publish_to_users(others, payload)


def publish_message_request(
    thread: MessageThread,
    *,
    event: str,
    notify_user_ids: list[UUID] | None = None,
    db: Session | None = None,
) -> None:
    """Request lifecycle folded into thread.updated (+ request_event)."""
    targets = notify_user_ids or participants(thread)
    publish_thread_updated(
        thread,
        viewer_ids=targets,
        extra={"request_event": event},
        db=db,
    )


def publish_connection_accepted(
    *,
    thread: MessageThread,
    connection_id: UUID,
    user_ids: list[UUID],
    system_message: Message | None,
    db: Session,
) -> None:
    publish_to_users(
        user_ids,
        {
            "type": EVT_CONNECTION_ACCEPTED,
            "thread_id": str(thread.id),
            "connection_id": str(connection_id),
            "status": "connected",
        },
        db=db,
    )
    if system_message is not None:
        publish_new_message(
            db,
            thread=thread,
            message=system_message,
            sender_id=system_message.sender_user_id,
        )
    else:
        publish_thread_updated(thread, viewer_ids=user_ids, db=db)


def publish_connection_removed(
    *,
    user_ids: list[UUID],
    connection_id: UUID | None = None,
    reason: str = "removed",
) -> None:
    payload: dict[str, Any] = {
        "type": EVT_CONNECTION_REMOVED,
        "reason": reason,
    }
    if connection_id is not None:
        payload["connection_id"] = str(connection_id)
    publish_to_users(user_ids, payload)


def publish_thread_disabled(
    thread: MessageThread,
    *,
    reason: str,
    user_ids: list[UUID] | None = None,
    db: Session | None = None,
) -> None:
    targets = user_ids or participants(thread)
    publish_to_users(
        targets,
        {
            "type": EVT_THREAD_DISABLED,
            "thread_id": str(thread.id),
            "reason": reason,
            "status": thread.status,
            "can_reply": False,
            "blocked": thread.status == C.THREAD_STATUS_BLOCKED
            or reason in {"blocked", "removed"},
        },
        db=db,
    )
    publish_thread_updated(
        thread,
        viewer_ids=targets,
        extra={"disabled_reason": reason},
        db=db,
    )


def publish_attachment_ready(user_id: UUID, attachment: MessageAttachment) -> None:
    """Uploader-only — allowlisted metadata + viewer-scoped signed URL."""
    from app.messaging.attachment_privacy import serialize_attachment_public

    public = serialize_attachment_public(
        attachment, viewer_id=user_id, ready_only=False
    )
    if public is None:
        return
    publish_to_users(
        [user_id],
        {
            "type": EVT_ATTACHMENT_READY,
            "attachment": public,
        },
    )


def publish_attachment_failed(user_id: UUID, *, detail: str) -> None:
    publish_to_users(
        [user_id],
        {
            "type": EVT_ATTACHMENT_FAILED,
            "detail": (detail or "Upload failed")[:240],
        },
    )


def user_is_thread_participant(
    db: Session, user: User, thread_id: UUID
) -> list[UUID] | None:
    """Return participant ids if user may act on the thread over WS; else None."""
    from app.messaging.ws_permissions import (
        thread_participant_ids,
        user_may_emit_thread_action,
    )

    thread = user_may_emit_thread_action(db, user, thread_id, require_can_reply=False)
    if thread is None:
        return None
    return thread_participant_ids(thread)
