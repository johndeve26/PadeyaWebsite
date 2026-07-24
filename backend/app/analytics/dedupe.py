"""Claim / check analytics dedupe keys (idempotency outside the raw stream)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.analytics.rollup_models import AnalyticsDedupeKey
from app.analytics.utils import generate_dedupe_key

# Re-export for callers that import from dedupe
build_dedupe_key = generate_dedupe_key


def claim_dedupe_key(
    db: Session,
    *,
    dedupe_key: str | None,
    scope: str,
    target_event_id: UUID | None = None,
    session_id: str | None = None,
    anonymous_id: str | None = None,
    ttl_hours: int | None = 48,
    window_seconds: int | None = None,
) -> bool:
    """Try to claim a dedupe key.

    Returns True if this is the first claim (proceed with write).
    Returns False if the key already exists within the active window.

    Expired keys (``expires_at`` in the past) are reclaimed.
    Uses a savepoint so a unique conflict does not abort the outer transaction.
    """
    if not dedupe_key:
        return True

    now = datetime.now(UTC)
    existing = db.scalar(
        select(AnalyticsDedupeKey).where(AnalyticsDedupeKey.dedupe_key == dedupe_key)
    )
    if existing is not None:
        expires = existing.expires_at
        if expires is not None:
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=UTC)
            if expires <= now:
                with db.begin_nested():
                    db.execute(
                        delete(AnalyticsDedupeKey).where(
                            AnalyticsDedupeKey.id == existing.id
                        )
                    )
                    db.flush()
            else:
                return False
        else:
            return False

    expires_at = None
    if window_seconds is not None and window_seconds > 0:
        expires_at = now + timedelta(seconds=window_seconds)
    elif ttl_hours is not None:
        expires_at = now + timedelta(hours=ttl_hours)

    row = AnalyticsDedupeKey(
        dedupe_key=dedupe_key[:191],
        scope=scope.strip().lower()[:64],
        target_event_id=target_event_id,
        session_id=(session_id.strip()[:64] if session_id and session_id.strip() else None),
        anonymous_id=(
            anonymous_id.strip()[:64] if anonymous_id and anonymous_id.strip() else None
        ),
        expires_at=expires_at,
    )
    try:
        with db.begin_nested():
            db.add(row)
            db.flush()
    except IntegrityError:
        return False
    return True


def claim_windowed(
    db: Session,
    *,
    scope: str,
    window_seconds: int,
    target_event_id: UUID | None = None,
    session_id: str | None = None,
    anonymous_id: str | None = None,
    user_id: UUID | None = None,
    order_id: UUID | None = None,
    list_context: str | None = None,
    request_id: str | None = None,
    extra: str | None = None,
) -> bool:
    """Claim a time-windowed dedupe key built from visitor + event dimensions."""
    key = generate_dedupe_key(
        scope,
        request_id=request_id,
        target_event_id=target_event_id,
        session_id=session_id,
        anonymous_id=anonymous_id,
        user_id=user_id,
        order_id=order_id,
        list_context=list_context,
        extra=extra,
    )
    return claim_dedupe_key(
        db,
        dedupe_key=key,
        scope=scope,
        target_event_id=target_event_id,
        session_id=session_id,
        anonymous_id=anonymous_id,
        window_seconds=window_seconds,
        ttl_hours=None,
    )
