"""Admin host workspace soft lifecycle: suspend / restore / force-delete."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.hosts.models import Host
from app.hosts.service import get_host_by_id
from app.users.models import User
from app.users.service import user_has_permission

HOST_STATUS_ACTIVE = "active"
HOST_STATUS_PENDING = "pending_verification"
HOST_STATUS_SUSPENDED = "suspended"
HOST_STATUS_DELETED = "deleted"

_SUSPENDABLE = frozenset({HOST_STATUS_ACTIVE, HOST_STATUS_PENDING})


def _require_perm(admin: User, code: str) -> None:
    if not user_has_permission(admin, code):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permission",
        )


def _require_reason(reason: str | None, *, label: str = "reason") -> str:
    cleaned = (reason or "").strip()
    if len(cleaned) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A {label} of at least 3 characters is required",
        )
    return cleaned


def suspend_host(
    db: Session,
    *,
    admin: User,
    host_id: uuid.UUID,
    reason: str,
) -> Host:
    _require_perm(admin, "hosts.suspend")
    cleaned = _require_reason(reason, label="reason for suspension")
    host = get_host_by_id(db, host_id)
    if host is None:
        raise HTTPException(status_code=404, detail="Host not found")
    if host.status == HOST_STATUS_SUSPENDED:
        return host
    if host.status == HOST_STATUS_DELETED:
        raise HTTPException(
            status_code=400,
            detail="Deleted host workspaces cannot be suspended",
        )
    if host.status not in _SUSPENDABLE:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot suspend host with status '{host.status}'",
        )

    before = host.status
    host.status = HOST_STATUS_SUSPENDED
    write_audit_log(
        db,
        action="hosts.suspend",
        actor_user_id=admin.id,
        resource_type="host",
        resource_id=str(host.id),
        details={
            "before_status": before,
            "after_status": HOST_STATUS_SUSPENDED,
            "reason": cleaned,
        },
    )
    db.commit()
    db.refresh(host)
    return host


def restore_host(
    db: Session,
    *,
    admin: User,
    host_id: uuid.UUID,
    reason: str | None = None,
) -> Host:
    _require_perm(admin, "hosts.suspend")
    cleaned = (reason or "").strip() or "Restored by admin"
    host = get_host_by_id(db, host_id)
    if host is None:
        raise HTTPException(status_code=404, detail="Host not found")
    if host.status == HOST_STATUS_ACTIVE:
        return host
    if host.status == HOST_STATUS_DELETED:
        raise HTTPException(
            status_code=400,
            detail="Deleted host workspaces cannot be restored",
        )
    if host.status != HOST_STATUS_SUSPENDED:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot restore host with status '{host.status}'",
        )

    before = host.status
    host.status = HOST_STATUS_ACTIVE
    write_audit_log(
        db,
        action="hosts.restore",
        actor_user_id=admin.id,
        resource_type="host",
        resource_id=str(host.id),
        details={
            "before_status": before,
            "after_status": HOST_STATUS_ACTIVE,
            "reason": cleaned,
        },
    )
    db.commit()
    db.refresh(host)
    return host


def force_delete_host(
    db: Session,
    *,
    admin: User,
    host_id: uuid.UUID,
    reason: str,
) -> Host:
    """Soft EOL: set ``status=deleted``. Requires prior suspension."""
    _require_perm(admin, "hosts.force_delete")
    cleaned = _require_reason(reason, label="reason for force delete")
    host = get_host_by_id(db, host_id)
    if host is None:
        raise HTTPException(status_code=404, detail="Host not found")
    if host.status == HOST_STATUS_DELETED:
        raise HTTPException(
            status_code=400, detail="Host workspace is already deleted"
        )
    if host.status != HOST_STATUS_SUSPENDED:
        raise HTTPException(
            status_code=400,
            detail="Host must be suspended before force delete",
        )

    before = host.status
    host.status = HOST_STATUS_DELETED
    write_audit_log(
        db,
        action="hosts.force_delete",
        actor_user_id=admin.id,
        resource_type="host",
        resource_id=str(host.id),
        details={
            "before_status": before,
            "after_status": HOST_STATUS_DELETED,
            "reason": cleaned,
            "force_delete": True,
        },
    )
    db.commit()
    db.refresh(host)
    return host
