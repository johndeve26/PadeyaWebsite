"""Persisted active host workspace per user."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, Session, mapped_column
from sqlalchemy.types import Uuid

from app.core.database import Base
from app.hosts.models import Host
from app.hosts.workspace_service import list_user_workspaces
from app.users.models import User


class UserActiveWorkspace(Base):
    __tablename__ = "user_active_workspaces"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    host_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("hosts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


def get_active_workspace_id(db: Session, *, user_id: uuid.UUID) -> uuid.UUID | None:
    row = db.get(UserActiveWorkspace, user_id)
    return row.host_id if row is not None else None


def set_active_workspace(
    db: Session, *, user: User, host_id: uuid.UUID
) -> dict:
    workspaces = list_user_workspaces(db, user=user)
    match = next((w for w in workspaces if w["host_id"] == host_id), None)
    if match is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    host = db.get(Host, host_id)
    if host is None or host.status != "active":
        raise HTTPException(status_code=404, detail="Host not found")

    row = db.get(UserActiveWorkspace, user.id)
    if row is None:
        row = UserActiveWorkspace(user_id=user.id, host_id=host_id)
        db.add(row)
    else:
        row.host_id = host_id
    db.commit()
    return {
        "host_id": host.id,
        "display_name": host.display_name,
        "slug": host.slug,
        "kind": match["kind"],
        "role": match["role"],
        "role_label": match["role_label"],
        "is_owner": match["is_owner"],
    }


def resolve_host_id_for_request(
    db: Session,
    *,
    user: User,
    host_id: uuid.UUID | None = None,
    header_host_id: uuid.UUID | None = None,
) -> uuid.UUID | None:
    """Explicit host_id → header → persisted active → owned host (None = owned)."""
    if host_id is not None:
        return host_id
    if header_host_id is not None:
        return header_host_id
    active = get_active_workspace_id(db, user_id=user.id)
    if active is not None:
        return active
    return None  # team_access treats None as owned host
