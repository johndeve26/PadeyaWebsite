"""Server-side WebSocket permission gates for messaging.

Mirrors REST thread rules. Never trust the frontend.
Admins do not gain private-thread WS access unless they are a participant.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.hosts.models import Host
from app.messaging import constants as C
from app.messaging.models import MessageThread
from app.users.models import User

# Content / activity on an open conversation
ACTIVE_THREAD_EVENTS = frozenset(
    {
        "message.created",
        "message.updated",
        "message.deleted",
        "message.read",
        "message.typing",
        "thread.updated",
    }
)

# Participants may always learn the thread was closed/blocked/accepted
LIFECYCLE_THREAD_EVENTS = frozenset(
    {
        "thread.disabled",
        "connection.accepted",
        "connection.removed",
    }
)

# No thread scope (or uploader-only) — not gated by thread membership
PERSONAL_EVENTS = frozenset(
    {
        "thread.unread_count_updated",
        "notification.created",
        "attachment.ready",
        "attachment.failed",
        "connected",
        "pong",
        "thread.subscribed",
        "thread.unsubscribed",
        "thread.subscribe_denied",
    }
)


def thread_participant_ids(thread: MessageThread) -> list[UUID]:
    if thread.thread_type == C.THREAD_TYPE_FAN_FAN:
        ids = [thread.fan_user_id]
        if thread.fan_b_user_id:
            ids.append(thread.fan_b_user_id)
        return ids
    ids = [thread.fan_user_id]
    if thread.host_user_id:
        ids.append(thread.host_user_id)
    return ids


def is_thread_participant(db: Session, user_id: UUID, thread: MessageThread) -> bool:
    """True only for the fan/host (or fan/fan) parties — not admins by role."""
    if thread.thread_type == C.THREAD_TYPE_FAN_FAN:
        return user_id in {thread.fan_user_id, thread.fan_b_user_id}
    if user_id == thread.fan_user_id or user_id == thread.host_user_id:
        return True
    if thread.host_id is not None:
        from app.teams.permissions import host_team_or_owner_allows

        if host_team_or_owner_allows(
            db, user_id, thread.host_id, "messages.view", "messages.reply"
        ):
            return True
    return False


def counterpart_user_id(thread: MessageThread, user_id: UUID) -> UUID | None:
    if thread.thread_type == C.THREAD_TYPE_FAN_FAN:
        if user_id == thread.fan_user_id:
            return thread.fan_b_user_id
        if user_id == thread.fan_b_user_id:
            return thread.fan_user_id
        return None
    if user_id == thread.fan_user_id:
        return thread.host_user_id
    if user_id == thread.host_user_id:
        return thread.fan_user_id
    # Host account linked via host_id
    return thread.fan_user_id


def _pair_blocked(db: Session, user_id: UUID, other_id: UUID | None) -> bool:
    if other_id is None:
        return False
    from app.messaging.service import is_blocked

    return is_blocked(db, a=user_id, b=other_id)


def _fan_fan_connected(db: Session, user_id: UUID, other_id: UUID | None) -> bool:
    if other_id is None:
        return False
    from app.fan_connect.service import connection_accepted

    return connection_accepted(db, user_id, other_id)


def user_may_receive_thread_event(
    db: Session,
    *,
    user_id: UUID,
    thread_id: UUID | None,
    event_type: str,
) -> bool:
    """Return True if this user may be delivered this WS event."""
    if event_type in PERSONAL_EVENTS or not thread_id:
        return True

    thread = db.get(MessageThread, thread_id)
    if thread is None:
        return False

    # Admin / support never join private threads via WS unless they are a party.
    if not is_thread_participant(db, user_id, thread):
        return False

    other_id = counterpart_user_id(thread, user_id)

    if event_type in LIFECYCLE_THREAD_EVENTS:
        return True

    if event_type not in ACTIVE_THREAD_EVENTS:
        # Unknown thread-scoped event: deny by default
        return False

    # Active events: blocked / closed / removed connection cannot receive.
    if thread.status == C.THREAD_STATUS_BLOCKED:
        return False
    if thread.status == C.THREAD_STATUS_CLOSED:
        return False
    if _pair_blocked(db, user_id, other_id):
        return False

    if thread.thread_type == C.THREAD_TYPE_FAN_FAN:
        # Only connected Fan Connect pairs exchange active events.
        # Reported: still a participant conversation under moderation rules
        # (bodies may be redacted by serializers); connection must remain.
        if not _fan_fan_connected(db, user_id, other_id):
            return False

    # fan_host reported threads: keep existing moderation behavior (participant
    # still receives; REST can_reply may still allow depending on status).
    return True


def user_may_emit_thread_action(
    db: Session,
    user: User,
    thread_id: UUID,
    *,
    require_can_reply: bool = False,
) -> MessageThread | None:
    """
    Gate client→server WS actions (typing, subscribe, message.read).

    Returns the thread when allowed, else None.
    """
    thread = db.get(MessageThread, thread_id)
    if thread is None:
        return None
    if not is_thread_participant(db, user.id, thread):
        return None

    other_id = counterpart_user_id(thread, user.id)
    if thread.status == C.THREAD_STATUS_BLOCKED:
        return None
    if _pair_blocked(db, user.id, other_id):
        return None

    if thread.thread_type == C.THREAD_TYPE_FAN_FAN:
        if thread.status == C.THREAD_STATUS_CLOSED:
            return None
        if not _fan_fan_connected(db, user.id, other_id):
            return None
    elif thread.status == C.THREAD_STATUS_CLOSED:
        return None

    if require_can_reply:
        # Typing requires an open reply path (not reported-as-disabled for fan_fan
        # closed/blocked — already handled). For request threads, initiator/recipient
        # may still type when REST would allow reply.
        if thread.status == C.THREAD_STATUS_REPORTED:
            return None
        if thread.thread_type == C.THREAD_TYPE_FAN_FAN:
            return thread
        # fan_host request: allowed to interact
        return thread

    return thread


def filter_event_recipients(
    db: Session,
    user_ids: list[UUID],
    *,
    thread_id: UUID | None,
    event_type: str,
) -> list[UUID]:
    """Filter a fan-out list through receive gates."""
    allowed: list[UUID] = []
    seen: set[UUID] = set()
    for uid in user_ids:
        if uid in seen:
            continue
        seen.add(uid)
        if user_may_receive_thread_event(
            db, user_id=uid, thread_id=thread_id, event_type=event_type
        ):
            allowed.append(uid)
    return allowed
