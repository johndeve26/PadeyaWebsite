"""Fan Connect trusted analytics — privacy-safe metadata only.

Never include: private attendance, hidden venues, ticket types, order/payment
IDs, spend, phone/email, shipping, locked Vault content, or message bodies.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.analytics.taxonomy import TrackedAction
from app.analytics.trusted import track_server_event
from app.fan_connect import constants as C

logger = logging.getLogger(__name__)


def _safe_reason_code_count(reasons: list | None) -> int:
    count = 0
    for raw in reasons or []:
        if not isinstance(raw, dict):
            continue
        code = str(raw.get("code") or "").strip()
        if code in C.SAFE_REASON_CODES:
            count += 1
    return count


def _emit(
    db: Session,
    *,
    action: str,
    user_id: UUID | None,
    metadata: dict[str, Any] | None = None,
    target_event_id: UUID | None = None,
    request_id: str | None = None,
) -> None:
    try:
        track_server_event(
            db,
            event_name=action,
            user_id=user_id,
            target_event_id=target_event_id,
            metadata=metadata,
            request_id=request_id,
        )
    except Exception:
        logger.exception("Fan Connect analytics emit failed: %s", action)


def emit_fan_connect_enabled(db: Session, *, user_id: UUID) -> None:
    _emit(
        db,
        action=TrackedAction.FAN_CONNECT_ENABLED,
        user_id=user_id,
        metadata={"fan_connect_enabled": True},
    )


def emit_fan_connect_disabled(db: Session, *, user_id: UUID) -> None:
    _emit(
        db,
        action=TrackedAction.FAN_CONNECT_DISABLED,
        user_id=user_id,
        metadata={"fan_connect_enabled": False},
    )


def emit_request_sent(
    db: Session,
    *,
    user_id: UUID,
    connection_id: UUID,
    counterpart_username: str | None,
    target_event_id: UUID | None,
    reasons: list | None,
) -> None:
    _emit(
        db,
        action=TrackedAction.FAN_CONNECT_REQUEST_SENT,
        user_id=user_id,
        target_event_id=target_event_id,
        metadata={
            "connection_id": str(connection_id),
            "counterpart_username": counterpart_username,
            "reason_code_count": _safe_reason_code_count(reasons),
        },
        request_id=f"fc:request_sent:{connection_id}",
    )


def emit_request_accepted(
    db: Session,
    *,
    user_id: UUID,
    connection_id: UUID,
    thread_id: UUID | None,
) -> None:
    _emit(
        db,
        action=TrackedAction.FAN_CONNECT_REQUEST_ACCEPTED,
        user_id=user_id,
        metadata={
            "connection_id": str(connection_id),
            "thread_id": str(thread_id) if thread_id else None,
        },
        request_id=f"fc:request_accepted:{connection_id}",
    )


def emit_request_declined(
    db: Session, *, user_id: UUID, connection_id: UUID
) -> None:
    _emit(
        db,
        action=TrackedAction.FAN_CONNECT_REQUEST_DECLINED,
        user_id=user_id,
        metadata={"connection_id": str(connection_id)},
        request_id=f"fc:request_declined:{connection_id}",
    )


def emit_connection_removed(
    db: Session, *, user_id: UUID, connection_id: UUID
) -> None:
    _emit(
        db,
        action=TrackedAction.FAN_CONNECT_CONNECTION_REMOVED,
        user_id=user_id,
        metadata={"connection_id": str(connection_id)},
        request_id=f"fc:removed:{connection_id}",
    )


def emit_blocked(
    db: Session,
    *,
    user_id: UUID,
    counterpart_username: str | None,
) -> None:
    _emit(
        db,
        action=TrackedAction.FAN_CONNECT_BLOCKED,
        user_id=user_id,
        metadata={"counterpart_username": counterpart_username},
    )


def emit_reported(
    db: Session,
    *,
    user_id: UUID,
    counterpart_username: str | None,
    connection_id: UUID | None,
) -> None:
    _emit(
        db,
        action=TrackedAction.FAN_CONNECT_REPORTED,
        user_id=user_id,
        metadata={
            "counterpart_username": counterpart_username,
            "connection_id": str(connection_id) if connection_id else None,
        },
    )


def emit_fan_fan_thread_created(
    db: Session, *, user_id: UUID, thread_id: UUID
) -> None:
    _emit(
        db,
        action=TrackedAction.FAN_FAN_MESSAGE_THREAD_CREATED,
        user_id=user_id,
        metadata={"thread_id": str(thread_id)},
        request_id=f"fc:thread_created:{thread_id}",
    )


def emit_fan_fan_message_sent(
    db: Session, *, user_id: UUID, thread_id: UUID
) -> None:
    _emit(
        db,
        action=TrackedAction.FAN_FAN_MESSAGE_SENT,
        user_id=user_id,
        metadata={"thread_id": str(thread_id)},
        # Allow multiple sends — include short uniqueness via time window in request_id
        request_id=None,
    )
