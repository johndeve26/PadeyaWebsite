"""Persistence helpers for admin impersonation sessions and audit rows."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.admin.impersonation_models import (
    IMPERSONATION_STATUS_ACTIVE,
    IMPERSONATION_STATUS_ENDED,
    IMPERSONATION_STATUS_EXPIRED,
    IMPERSONATION_STATUS_REVOKED,
    AdminImpersonationAuditLog,
    AdminImpersonationSession,
)


def create_impersonation_session(
    db: Session,
    *,
    session_id: UUID,
    actor_admin_id: UUID,
    target_user_id: UUID,
    reason: str,
    support_ticket_id: str | None,
    started_at: datetime,
    expires_at: datetime,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AdminImpersonationSession:
    row = AdminImpersonationSession(
        id=session_id,
        actor_admin_id=actor_admin_id,
        target_user_id=target_user_id,
        reason=reason,
        support_ticket_id=support_ticket_id,
        started_at=started_at,
        expires_at=expires_at,
        status=IMPERSONATION_STATUS_ACTIVE,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(row)
    db.flush()
    return row


def get_impersonation_session(
    db: Session, session_id: UUID
) -> AdminImpersonationSession | None:
    return db.get(AdminImpersonationSession, session_id)


def end_impersonation_session(
    db: Session,
    *,
    session_id: UUID,
    ended_by_admin_id: UUID,
    status: str = IMPERSONATION_STATUS_ENDED,
) -> AdminImpersonationSession | None:
    row = get_impersonation_session(db, session_id)
    if row is None:
        return None
    if row.status != IMPERSONATION_STATUS_ACTIVE:
        return row
    row.status = status
    row.ended_at = datetime.now(UTC)
    row.ended_by_admin_id = ended_by_admin_id
    db.add(row)
    return row


def mark_impersonation_session_expired(
    db: Session, *, session_id: UUID
) -> AdminImpersonationSession | None:
    row = get_impersonation_session(db, session_id)
    if row is None or row.status != IMPERSONATION_STATUS_ACTIVE:
        return row
    row.status = IMPERSONATION_STATUS_EXPIRED
    row.ended_at = datetime.now(UTC)
    db.add(row)
    return row


def revoke_impersonation_session(
    db: Session,
    *,
    session_id: UUID,
    ended_by_admin_id: UUID,
) -> AdminImpersonationSession | None:
    return end_impersonation_session(
        db,
        session_id=session_id,
        ended_by_admin_id=ended_by_admin_id,
        status=IMPERSONATION_STATUS_REVOKED,
    )


def write_impersonation_audit_log(
    db: Session,
    *,
    impersonation_id: UUID,
    actor_admin_id: UUID,
    target_user_id: UUID,
    action: str,
    method: str | None = None,
    path: str | None = None,
    status_code: int | None = None,
    metadata_json: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AdminImpersonationAuditLog:
    entry = AdminImpersonationAuditLog(
        impersonation_id=impersonation_id,
        actor_admin_id=actor_admin_id,
        target_user_id=target_user_id,
        action=action[:128],
        method=(method[:16] if method else None),
        path=(path[:512] if path else None),
        status_code=status_code,
        metadata_json=metadata_json,
        ip_address=ip_address,
        user_agent=(user_agent[:512] if user_agent else None),
    )
    db.add(entry)
    return entry


def list_impersonation_sessions_for_target(
    db: Session,
    *,
    target_user_id: UUID,
    limit: int = 50,
    offset: int = 0,
) -> list[AdminImpersonationSession]:
    return list(
        db.scalars(
            select(AdminImpersonationSession)
            .where(AdminImpersonationSession.target_user_id == target_user_id)
            .order_by(AdminImpersonationSession.started_at.desc())
            .offset(offset)
            .limit(limit)
        )
    )


def list_active_sessions_for_admin(
    db: Session, *, actor_admin_id: UUID
) -> list[AdminImpersonationSession]:
    return list(
        db.scalars(
            select(AdminImpersonationSession).where(
                AdminImpersonationSession.actor_admin_id == actor_admin_id,
                AdminImpersonationSession.status == IMPERSONATION_STATUS_ACTIVE,
            )
        )
    )


def expire_stale_active_sessions(
    db: Session,
    *,
    actor_admin_id: UUID | None = None,
    now: datetime | None = None,
) -> int:
    """Mark timed-out active sessions as expired. Returns count updated."""
    cutoff = now or datetime.now(UTC)
    q = select(AdminImpersonationSession).where(
        AdminImpersonationSession.status == IMPERSONATION_STATUS_ACTIVE,
    )
    if actor_admin_id is not None:
        q = q.where(AdminImpersonationSession.actor_admin_id == actor_admin_id)
    rows = list(db.scalars(q))
    updated = 0
    for row in rows:
        expires = row.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        if expires < cutoff:
            row.status = IMPERSONATION_STATUS_EXPIRED
            if row.ended_at is None:
                row.ended_at = cutoff
            db.add(row)
            updated += 1
    if updated:
        db.flush()
    return updated
