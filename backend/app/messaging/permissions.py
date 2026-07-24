"""Shared messaging permission layer for chat features.

UX may feel modern (reply / pin / star / edit), but gates stay strict:

- fan_host: own relationship rules only (participant + not blocked/closed;
  requests may still message) — never Fan Connect rules
- fan_fan: connection-only after accepted Fan Connect; removed/blocked
  disables send
- pins: shared thread state (both participants); requires pin gate
- stars: personal to the viewer (never peer-visible / never fan-out)
- replies: same-thread + can_send_message + safe preview checks

Boolean helpers are the source of truth. Assert helpers raise HTTP 403/404 for routers.

Package path: `app.messaging` (not `app.messages`).
"""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.messaging import constants as C
from app.messaging.models import Message, MessageDeletion, MessageThread
from app.messaging.ws_permissions import (
    counterpart_user_id,
    is_thread_participant,
)
from app.users.models import User


def _pair_blocked(db: Session, user_id: UUID, other_id: UUID | None) -> bool:
    if other_id is None:
        return False
    from app.messaging.service import is_blocked

    return is_blocked(db, a=user_id, b=other_id)


def _fan_fan_connected(db: Session, user_id: UUID, other_id: UUID | None) -> bool:
    if other_id is None:
        return False
    from app.fan_connect.service import connection_accepted

    return bool(connection_accepted(db, user_id, other_id))


def _message_is_redacted(msg: Message) -> bool:
    return (
        msg.status
        in {C.MESSAGE_STATUS_HIDDEN, C.MESSAGE_STATUS_DELETED}
        or msg.moderation_status == C.MOD_HIDDEN
        or msg.deleted_at is not None
    )


def _deleted_for_me(db: Session, message_id: UUID, viewer_id: UUID) -> bool:
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


def _within_edit_window(msg: Message) -> bool:
    from app.messaging.service import _now

    created = msg.created_at
    if created is None:
        return False
    now = _now()
    created_cmp = created if created.tzinfo else created.replace(tzinfo=now.tzinfo)
    return now - created_cmp <= timedelta(hours=C.MESSAGE_EDIT_WINDOW_HOURS)


def can_read_thread(db: Session, user: User, thread: MessageThread) -> bool:
    """Participant of the thread (fan/host or fan/fan). Admins are not implied."""
    return is_thread_participant(db, user.id, thread)


def assert_can_read_thread(
    db: Session, user: User, thread_id: UUID
) -> tuple[MessageThread, bool]:
    """Load thread and require participation. Returns (thread, as_host)."""
    from app.messaging.service import _require_participant

    return _require_participant(db, thread_id, user)


_SEND_DENIED_STATUSES = frozenset(
    {
        C.THREAD_STATUS_BLOCKED,
        C.THREAD_STATUS_CLOSED,
        C.THREAD_STATUS_REPORTED,
    }
)


def can_send_message(db: Session, user: User, thread: MessageThread) -> bool:
    """May send / reply in this thread (same gates as ThreadDetail.can_reply)."""
    if not can_read_thread(db, user, thread):
        return False

    other_id = counterpart_user_id(thread, user.id)

    if thread.thread_type == C.THREAD_TYPE_FAN_FAN:
        if other_id is None:
            return False
        if _pair_blocked(db, user.id, other_id):
            return False
        if thread.status in _SEND_DENIED_STATUSES:
            return False
        return _fan_fan_connected(db, user.id, other_id)

    # fan_host — participant with open (or request) thread; blocked/closed/reported deny.
    if _pair_blocked(db, user.id, other_id):
        return False
    if thread.status in _SEND_DENIED_STATUSES:
        return False
    return True


def assert_can_send_message(db: Session, user: User, thread: MessageThread) -> None:
    """Raise with the same detail strings historically used by `send_in_thread`."""
    if not can_read_thread(db, user, thread):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="You cannot send messages in this thread.",
        )

    other_id = counterpart_user_id(thread, user.id)

    if thread.thread_type == C.THREAD_TYPE_FAN_FAN:
        if other_id is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Invalid thread.")
        if _pair_blocked(db, user.id, other_id):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, detail="Messaging is blocked."
            )
        if thread.status == C.THREAD_STATUS_REPORTED:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="This conversation is under review.",
            )
        if thread.status in {C.THREAD_STATUS_BLOCKED, C.THREAD_STATUS_CLOSED}:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Thread is closed.")
        if not _fan_fan_connected(db, user.id, other_id):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="Fan Connect required before messaging.",
            )
        return

    if _pair_blocked(db, user.id, other_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Messaging is blocked.")
    if thread.status == C.THREAD_STATUS_REPORTED:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="This conversation is under review.",
        )
    if thread.status in {C.THREAD_STATUS_BLOCKED, C.THREAD_STATUS_CLOSED}:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Thread is closed.")

    if thread.thread_type == C.THREAD_TYPE_FAN_HOST and thread.host_id is not None:
        from app.teams.permissions import (
            host_team_or_owner_allows,
            is_host_owner,
        )

        acting_as_host = user.id == thread.host_user_id or host_team_or_owner_allows(
            db, user.id, thread.host_id, "messages.view", "messages.reply"
        )
        if acting_as_host and not (
            is_host_owner(db, user.id, thread.host_id)
            or user.id == thread.host_user_id
            or host_team_or_owner_allows(
                db, user.id, thread.host_id, "messages.reply"
            )
        ):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="Missing permission: messages.reply",
            )


def can_edit_message(
    db: Session, user: User, thread: MessageThread, message: Message
) -> bool:
    """Sender-only body edit within the edit window on an open thread."""
    if message.thread_id != thread.id:
        return False
    if not can_send_message(db, user, thread):
        return False
    if message.sender_user_id != user.id:
        return False
    if message.message_type == C.MESSAGE_TYPE_SYSTEM or message.sender_role == "system":
        return False
    if _message_is_redacted(message):
        return False
    if _deleted_for_me(db, message.id, user.id):
        return False
    return _within_edit_window(message)


def assert_can_edit_message(
    db: Session, user: User, thread: MessageThread, message: Message
) -> None:
    if message.thread_id != thread.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Message not found.")
    if not can_read_thread(db, user, thread):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Message not found.")
    if thread.status in {C.THREAD_STATUS_BLOCKED, C.THREAD_STATUS_CLOSED}:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="You cannot edit messages in this thread.",
        )
    if not can_send_message(db, user, thread):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="You cannot edit messages in this thread.",
        )
    if message.sender_user_id != user.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="You can only edit your own messages."
        )
    if message.message_type == C.MESSAGE_TYPE_SYSTEM or message.sender_role == "system":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="System messages cannot be edited."
        )
    if _message_is_redacted(message) or _deleted_for_me(db, message.id, user.id):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="This message cannot be edited."
        )
    if not _within_edit_window(message):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Messages can only be edited within "
                f"{C.MESSAGE_EDIT_WINDOW_HOURS} hours."
            ),
        )


def can_pin_message(db: Session, user: User, thread: MessageThread) -> bool:
    """Pin/unpin on an open thread the user can access (fan_fan needs Connect)."""
    if not can_read_thread(db, user, thread):
        return False
    if thread.status in _SEND_DENIED_STATUSES:
        return False
    if thread.thread_type == C.THREAD_TYPE_FAN_FAN:
        return can_send_message(db, user, thread)
    other_id = counterpart_user_id(thread, user.id)
    return not _pair_blocked(db, user.id, other_id)


def assert_can_pin_message(db: Session, user: User, thread: MessageThread) -> None:
    if not can_pin_message(db, user, thread):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="You cannot pin messages in this thread.",
        )


def can_star_message(
    db: Session, user: User, thread: MessageThread, message: Message
) -> bool:
    """Personal star — any participant who can read the message content."""
    if message.thread_id != thread.id:
        return False
    if not can_read_thread(db, user, thread):
        return False
    if _message_is_redacted(message):
        return False
    if _deleted_for_me(db, message.id, user.id):
        return False
    return True


def assert_can_star_message(
    db: Session, user: User, thread: MessageThread, message: Message
) -> None:
    if message.thread_id != thread.id or not can_read_thread(db, user, thread):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Message not found.")
    if _message_is_redacted(message) or _deleted_for_me(db, message.id, user.id):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Cannot star a removed message."
        )


def can_reply_to_message(
    db: Session,
    user: User,
    thread: MessageThread,
    parent: Message,
) -> bool:
    """May send a reply targeting `parent` in this thread."""
    if parent.thread_id != thread.id:
        return False
    if not can_send_message(db, user, thread):
        return False
    if parent.message_type == C.MESSAGE_TYPE_SYSTEM or parent.sender_role == "system":
        return False
    if parent.message_type not in {
        C.MESSAGE_TYPE_TEXT,
        C.MESSAGE_TYPE_IMAGE,
        C.MESSAGE_TYPE_ATTACHMENT,
    }:
        return False
    if _message_is_redacted(parent):
        return False
    if _deleted_for_me(db, parent.id, user.id):
        return False
    return True


def assert_can_reply_to_message(
    db: Session,
    user: User,
    thread: MessageThread,
    parent: Message,
) -> None:
    if parent.thread_id != thread.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Message not found.")
    assert_can_send_message(db, user, thread)
    if parent.message_type == C.MESSAGE_TYPE_SYSTEM or parent.sender_role == "system":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Cannot reply to a system message.",
        )
    if parent.message_type not in {
        C.MESSAGE_TYPE_TEXT,
        C.MESSAGE_TYPE_IMAGE,
        C.MESSAGE_TYPE_ATTACHMENT,
    }:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Cannot reply to this message type.",
        )
    if _message_is_redacted(parent) or _deleted_for_me(db, parent.id, user.id):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Cannot reply to a removed message.",
        )


def can_delete_message_for_me(
    db: Session, user: User, thread: MessageThread, message: Message
) -> bool:
    """Soft hide for the current viewer only (not delete-for-everyone)."""
    if message.thread_id != thread.id:
        return False
    if not can_read_thread(db, user, thread):
        return False
    if message.message_type == C.MESSAGE_TYPE_SYSTEM or message.sender_role == "system":
        return False
    return not _deleted_for_me(db, message.id, user.id)


def assert_can_delete_message_for_me(
    db: Session, user: User, thread: MessageThread, message: Message
) -> None:
    if message.thread_id != thread.id or not can_read_thread(db, user, thread):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Message not found.")
    if message.message_type == C.MESSAGE_TYPE_SYSTEM or message.sender_role == "system":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="System messages cannot be deleted this way.",
        )
