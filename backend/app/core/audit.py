"""Audit log model and helper for admin/finance-sensitive actions."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, Session, mapped_column
from sqlalchemy.types import JSON, Uuid

from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    resource_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"))
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


def write_audit_log(
    db: Session,
    *,
    action: str,
    actor_user_id: uuid.UUID | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    # During audited impersonation, attribute actions to the real admin and
    # retain the effective (impersonated) user in details — never drop trails.
    merged_details = dict(details) if details else {}
    resolved_actor = actor_user_id
    try:
        from app.auth.impersonation_context import get_impersonation_context

        ctx = get_impersonation_context()
    except Exception:  # pragma: no cover - defensive import isolation
        ctx = None

    if ctx is not None and not str(action).startswith("admin_impersonation_"):
        if resolved_actor is None or resolved_actor == ctx.target_user_id:
            resolved_actor = ctx.impersonator_id
        merged_details.setdefault("impersonation", True)
        merged_details.setdefault("impersonation_id", str(ctx.impersonation_id))
        merged_details.setdefault("impersonated_user_id", str(ctx.target_user_id))

    entry = AuditLog(
        actor_user_id=resolved_actor,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=merged_details or None,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(entry)
    return entry
