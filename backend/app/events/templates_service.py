"""Host event template CRUD with archive/restore."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.events.models import EventTemplate
from app.hosts.service import require_user_host
from app.users.models import User


def list_templates(
    db: Session, *, user: User, include_archived: bool = False
) -> list[EventTemplate]:
    host = require_user_host(db, user)
    q = select(EventTemplate).where(EventTemplate.host_id == host.id)
    if not include_archived:
        q = q.where(EventTemplate.archived_at.is_(None))
    return list(db.scalars(q.order_by(EventTemplate.updated_at.desc())))


def get_template(db: Session, *, user: User, template_id: uuid.UUID) -> EventTemplate:
    host = require_user_host(db, user)
    row = db.get(EventTemplate, template_id)
    if row is None or row.host_id != host.id:
        raise HTTPException(status_code=404, detail="Event template not found")
    return row


def create_template(
    db: Session,
    *,
    user: User,
    name: str,
    description: str | None,
    payload: dict[str, Any],
) -> EventTemplate:
    host = require_user_host(db, user)
    row = EventTemplate(
        host_id=host.id,
        name=name.strip(),
        description=description,
        payload=payload or {},
        status="active",
        created_by=user.id,
        updated_by=user.id,
    )
    db.add(row)
    db.flush()
    write_audit_log(
        db,
        action="events.template_create",
        actor_user_id=user.id,
        resource_type="event_template",
        resource_id=str(row.id),
        details={"name": row.name},
    )
    db.commit()
    db.refresh(row)
    return row


def update_template(
    db: Session,
    *,
    user: User,
    template_id: uuid.UUID,
    name: str | None = None,
    description: str | None = None,
    payload: dict[str, Any] | None = None,
) -> EventTemplate:
    row = get_template(db, user=user, template_id=template_id)
    if row.archived_at is not None:
        raise HTTPException(status_code=400, detail="Restore template before updating")
    if name is not None:
        row.name = name.strip()
    if description is not None:
        row.description = description
    if payload is not None:
        row.payload = payload
    row.updated_by = user.id
    write_audit_log(
        db,
        action="events.template_update",
        actor_user_id=user.id,
        resource_type="event_template",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    return row


def archive_template(
    db: Session, *, user: User, template_id: uuid.UUID
) -> EventTemplate:
    row = get_template(db, user=user, template_id=template_id)
    if row.archived_at is not None:
        return row
    row.status = "archived"
    row.archived_at = datetime.now(UTC)
    row.archived_by = user.id
    row.updated_by = user.id
    write_audit_log(
        db,
        action="events.template_archive",
        actor_user_id=user.id,
        resource_type="event_template",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    return row


def restore_template(
    db: Session, *, user: User, template_id: uuid.UUID
) -> EventTemplate:
    row = get_template(db, user=user, template_id=template_id)
    row.status = "active"
    row.archived_at = None
    row.archived_by = None
    row.updated_by = user.id
    write_audit_log(
        db,
        action="events.template_restore",
        actor_user_id=user.id,
        resource_type="event_template",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    return row


def delete_template_blocked() -> None:
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail="Hard delete blocked; use POST .../archive",
    )
