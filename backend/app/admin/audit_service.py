"""Admin read-only audit log listing (immutable — no delete/update)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import AuditLog


def list_audit_logs(
    db: Session,
    *,
    action: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[AuditLog]:
    limit = min(max(limit, 1), 200)
    offset = max(offset, 0)
    q = select(AuditLog)
    if action:
        q = q.where(AuditLog.action == action)
    if resource_type:
        q = q.where(AuditLog.resource_type == resource_type)
    if resource_id:
        q = q.where(AuditLog.resource_id == resource_id)
    q = q.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
    return list(db.scalars(q))
