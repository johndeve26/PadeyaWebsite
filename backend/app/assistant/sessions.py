"""Assistant session lifecycle helpers."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.assistant.constants import (
    DEFAULT_PUBLIC_SESSION_RETENTION_HOURS,
    DEFAULT_SESSION_RETENTION_DAYS,
    MODE_AUTHENTICATED,
    MODE_PUBLIC,
)
from app.assistant.models import (
    AssistantFeedback,
    AssistantMessage,
    AssistantSession,
)
from app.core.config import get_settings
from app.users.models import User


def new_anonymous_session_id() -> str:
    return secrets.token_urlsafe(24)


def _retention_delta(*, authenticated: bool) -> timedelta:
    settings = get_settings()
    if authenticated:
        days = int(
            getattr(settings, "assistant_session_retention_days", None)
            or DEFAULT_SESSION_RETENTION_DAYS
        )
        return timedelta(days=days)
    hours = int(
        getattr(settings, "assistant_public_session_retention_hours", None)
        or DEFAULT_PUBLIC_SESSION_RETENTION_HOURS
    )
    return timedelta(hours=hours)


def create_session(
    db: Session,
    *,
    user: User | None,
    anonymous_session_id: str | None = None,
    active_role: str | None = None,
    title: str | None = None,
    metadata_json: dict | None = None,
) -> AssistantSession:
    authenticated = user is not None
    now = datetime.now(UTC)
    session = AssistantSession(
        user_id=user.id if user else None,
        anonymous_session_id=(
            None if authenticated else (anonymous_session_id or new_anonymous_session_id())
        ),
        mode=MODE_AUTHENTICATED if authenticated else MODE_PUBLIC,
        active_role=(active_role or None)[:64] if active_role else None,
        title=(title or None)[:200] if title else None,
        expires_at=now + _retention_delta(authenticated=authenticated),
        metadata_json=metadata_json,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session_for_actor(
    db: Session,
    *,
    session_id: UUID,
    user: User | None,
    anonymous_session_id: str | None = None,
) -> AssistantSession:
    session = db.get(AssistantSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    now = datetime.now(UTC)
    if session.expires_at and session.expires_at <= now:
        raise HTTPException(status_code=410, detail="Session expired")
    if user is not None:
        if session.user_id is not None and session.user_id != user.id:
            raise HTTPException(status_code=403, detail="Session not owned by user")
        return session
    # Anonymous
    if session.user_id is not None:
        raise HTTPException(status_code=403, detail="Session requires authentication")
    if (
        anonymous_session_id
        and session.anonymous_session_id
        and session.anonymous_session_id != anonymous_session_id
    ):
        raise HTTPException(status_code=403, detail="Session not owned")
    return session


def list_sessions_for_user(
    db: Session, *, user: User, limit: int = 30
) -> list[AssistantSession]:
    return list(
        db.scalars(
            select(AssistantSession)
            .where(AssistantSession.user_id == user.id)
            .order_by(AssistantSession.updated_at.desc())
            .limit(min(limit, 100))
        ).all()
    )


def delete_session(
    db: Session,
    *,
    session_id: UUID,
    user: User | None,
    anonymous_session_id: str | None = None,
) -> None:
    session = get_session_for_actor(
        db,
        session_id=session_id,
        user=user,
        anonymous_session_id=anonymous_session_id,
    )
    db.delete(session)
    db.commit()


def add_message(
    db: Session,
    *,
    session: AssistantSession,
    role: str,
    content: str,
    structured_content_json: dict | None = None,
    model: str | None = None,
    token_count: int | None = None,
    safety_status: str | None = None,
    trace_id: str | None = None,
) -> AssistantMessage:
    msg = AssistantMessage(
        session_id=session.id,
        role=role,
        content=content or "",
        structured_content_json=structured_content_json,
        model=model,
        token_count=token_count,
        safety_status=safety_status,
        trace_id=trace_id,
    )
    db.add(msg)
    session.updated_at = datetime.now(UTC)
    # Extend expiry on activity
    session.expires_at = datetime.now(UTC) + _retention_delta(
        authenticated=session.user_id is not None
    )
    if not session.title and role == "user" and content:
        session.title = content.strip()[:80]
    db.commit()
    db.refresh(msg)
    return msg


def message_count(db: Session, session_id: UUID) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(AssistantMessage)
            .where(AssistantMessage.session_id == session_id)
        )
        or 0
    )


def cleanup_expired_sessions(db: Session, *, limit: int = 500) -> int:
    """Delete expired sessions (cascade messages/tool calls via FK)."""
    now = datetime.now(UTC)
    rows = list(
        db.scalars(
            select(AssistantSession)
            .where(AssistantSession.expires_at.is_not(None))
            .where(AssistantSession.expires_at <= now)
            .limit(limit)
        ).all()
    )
    for row in rows:
        db.delete(row)
    if rows:
        db.commit()
    return len(rows)


def record_feedback(
    db: Session,
    *,
    session_id: UUID,
    message_id: UUID,
    rating: str,
    reason: str | None,
    comment: str | None,
    user: User | None,
    anonymous_session_id: str | None = None,
) -> AssistantFeedback:
    session = get_session_for_actor(
        db,
        session_id=session_id,
        user=user,
        anonymous_session_id=anonymous_session_id,
    )
    msg = db.get(AssistantMessage, message_id)
    if msg is None or msg.session_id != session.id:
        raise HTTPException(status_code=404, detail="Message not found")
    row = AssistantFeedback(
        session_id=session.id,
        message_id=message_id,
        rating=rating,
        reason=(reason or None)[:120] if reason else None,
        comment=(comment or None)[:2000] if comment else None,
        user_id=user.id if user else None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
