"""Fan Connect connection lifecycle — statuses, transitions, cooldowns.

Statuses
--------
suggested         System recommendation; no messaging.
request_sent      Requester sent; no messaging (DB store for open requests).
request_received  Viewer-facing alias for recipient of request_sent.
connected         Mutual accept; fan_fan messaging allowed.
declined          Declined; requester-only cooldown before re-request.
blocked           Excluded from suggestions; messaging disabled.
removed           Connection ended; messaging disabled until reconnected.

Actions → status
----------------
send request      → request_sent  (from suggested | declined-after-cooldown | removed)
accept request    → connected
decline request   → declined (+ requester_cooldown_until)
cancel request    → removed      (no decline cooldown)
remove connection → removed
block fan         → blocked
report fan        → report row (status unchanged unless also blocked)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from app.fan_connect import constants as C
from app.fan_connect.models import FanConnection


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def requester_cooldown_active(
    conn: FanConnection | None,
    viewer_id: UUID,
    *,
    db: Session | None = None,
) -> bool:
    """True when viewer is the original requester and decline cooldown blocks re-request."""
    if conn is None or conn.status != C.STATUS_DECLINED:
        return False
    if viewer_id != conn.requester_user_id:
        return False
    until = _aware(conn.requester_cooldown_until)
    if until is not None:
        return _now() < until
    # Legacy rows: derive from declined_at + platform default
    declined = _aware(conn.declined_at)
    if declined is None:
        return True
    from app.fan_connect.platform_settings import get_default_decline_cooldown_days

    days = get_default_decline_cooldown_days(db)
    if days <= 0:
        return False
    return _now() < declined + timedelta(days=days)


def requester_cooldown_until(
    conn: FanConnection | None,
    *,
    db: Session | None = None,
) -> datetime | None:
    """When the requester may send again (UTC), or None if no active cooldown."""
    if conn is None or conn.status != C.STATUS_DECLINED:
        return None
    until = _aware(conn.requester_cooldown_until)
    if until is not None:
        return until if _now() < until else None
    declined = _aware(conn.declined_at)
    if declined is None:
        return None
    from app.fan_connect.platform_settings import get_default_decline_cooldown_days

    days = get_default_decline_cooldown_days(db)
    if days <= 0:
        return None
    until_legacy = declined + timedelta(days=days)
    return until_legacy if _now() < until_legacy else None


def decline_cooldown_active(conn: FanConnection | None) -> bool:
    """Backward-compatible pair check — prefer requester_cooldown_active(viewer_id)."""
    if conn is None or conn.status != C.STATUS_DECLINED:
        return False
    until = _aware(conn.requester_cooldown_until)
    if until is not None:
        return _now() < until
    declined = _aware(conn.declined_at)
    if declined is None:
        return True
    return _now() < declined + timedelta(days=C.DECLINE_COOLDOWN_DAYS)


def messaging_allowed(conn: FanConnection | None) -> bool:
    """fan_fan chat only when connected and not removed."""
    return bool(
        conn
        and conn.status == C.STATUS_CONNECTED
        and conn.removed_at is None
    )


def can_send_request(
    conn: FanConnection | None,
    viewer_id: UUID,
    *,
    db: Session | None = None,
) -> tuple[bool, str | None]:
    """Whether viewer may send a new request to the other fan in this pair."""
    if conn is None:
        return True, None
    if conn.status == C.STATUS_CONNECTED:
        return False, "already_connected"
    if conn.status in C.OPEN_REQUEST_STATUSES:
        return False, "request_pending"
    if conn.status == C.STATUS_BLOCKED:
        return False, "connection_blocked"
    if conn.status == C.STATUS_DECLINED and requester_cooldown_active(
        conn, viewer_id, db=db
    ):
        return False, "decline_cooldown"
    if conn.status in {C.STATUS_SUGGESTED, C.STATUS_REMOVED, C.STATUS_DECLINED}:
        return True, None
    return True, None


def can_suggest(conn: FanConnection | None) -> tuple[bool, str | None]:
    """Whether this pair may appear in suggestions / marketplace discovery."""
    if conn is None:
        return True, None
    if conn.status == C.STATUS_CONNECTED:
        return False, "already_connected"
    if conn.status in C.OPEN_REQUEST_STATUSES:
        return False, "request_pending"
    if conn.status == C.STATUS_BLOCKED:
        return False, "connection_blocked"
    # Declined history does not hide either fan from discovery.
    return True, None


def other_user_id(conn: FanConnection, viewer_id: UUID) -> UUID:
    if conn.requester_user_id == viewer_id:
        return conn.recipient_user_id
    return conn.requester_user_id
