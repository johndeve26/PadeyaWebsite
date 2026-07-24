"""Admin host verification approve/reject lifecycle."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.audit import write_audit_log
from app.events.models import Event
from app.hosts.models import Host, HostVerification
from app.users.models import User
from app.users.service import user_has_permission


def list_verifications(
    db: Session, *, status_filter: str | None = None
) -> list[HostVerification]:
    q = select(HostVerification).options(selectinload(HostVerification.host))
    if status_filter:
        # Demo seed uses "verified"; approve path writes "approved".
        if status_filter == "approved":
            q = q.where(HostVerification.status.in_(("approved", "verified")))
        else:
            q = q.where(HostVerification.status == status_filter)
    return list(db.scalars(q.order_by(HostVerification.created_at.desc())))


def serialize_verification(
    db: Session, row: HostVerification
) -> dict[str, Any]:
    """Safe admin verification row including host name + owner links."""
    host = row.host
    if host is None:
        host = db.get(Host, row.host_id)

    owner: User | None = None
    if host is not None:
        owner = db.get(User, host.user_id)

    events_count = 0
    if host is not None:
        events_count = int(
            db.scalar(
                select(func.count(Event.id)).where(Event.host_id == host.id)
            )
            or 0
        )

    return {
        "id": row.id,
        "host_id": row.host_id,
        "status": row.status,
        "notes": row.notes,
        "reviewed_by": row.reviewed_by,
        "reviewed_at": row.reviewed_at,
        "created_at": row.created_at,
        "host_display_name": host.display_name if host else None,
        "host_slug": host.slug if host else None,
        "host_status": host.status if host else None,
        "owner_user_id": host.user_id if host else None,
        "owner_full_name": owner.full_name if owner else None,
        "owner_email": owner.email if owner else None,
        "events_count": events_count,
    }


def approve_verification(
    db: Session, *, admin: User, verification_id: uuid.UUID
) -> HostVerification:
    if not user_has_permission(admin, "hosts.verify"):
        raise HTTPException(status_code=403, detail="Insufficient permission")
    row = db.get(HostVerification, verification_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Verification not found")
    if row.status in {"approved", "verified"}:
        return row
    row.status = "approved"
    row.reviewed_by = admin.id
    row.reviewed_at = datetime.now(UTC)
    row.notes = None
    host = db.get(Host, row.host_id)
    if host is not None and host.status == "pending_verification":
        host.status = "active"
    write_audit_log(
        db,
        action="hosts.verification_approve",
        actor_user_id=admin.id,
        resource_type="host_verification",
        resource_id=str(row.id),
        details={"host_id": str(row.host_id)},
    )
    db.commit()
    db.refresh(row)
    return row


def reject_verification(
    db: Session, *, admin: User, verification_id: uuid.UUID, notes: str
) -> HostVerification:
    if not user_has_permission(admin, "hosts.verify"):
        raise HTTPException(status_code=403, detail="Insufficient permission")
    row = db.get(HostVerification, verification_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Verification not found")
    row.status = "rejected"
    row.notes = notes.strip()
    row.reviewed_by = admin.id
    row.reviewed_at = datetime.now(UTC)
    write_audit_log(
        db,
        action="hosts.verification_reject",
        actor_user_id=admin.id,
        resource_type="host_verification",
        resource_id=str(row.id),
        details={"host_id": str(row.host_id), "notes": notes.strip()},
    )
    db.commit()
    db.refresh(row)
    return row
