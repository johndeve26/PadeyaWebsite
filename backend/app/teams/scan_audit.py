"""Immutable audit trail for ticket and merch desk scans."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, Session, mapped_column
from sqlalchemy.types import JSON, Uuid

from app.core.database import Base

ScanResult = Literal[
    "allowed",
    "denied",
    "success",
    "invalid",
    "duplicate",
    "error",
]


class DeskScanAuditLog(Base):
    """Every desk scan attempt (auth + outcome), including denials."""

    __tablename__ = "desk_scan_audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Product: host profile id → hosts.id
    host_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("hosts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("events.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    ticket_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True, index=True
    )
    merch_order_item_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    result: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    denial_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


def write_desk_scan_audit(
    db: Session,
    *,
    actor_user_id: uuid.UUID | None,
    host_profile_id: uuid.UUID | None,
    event_id: uuid.UUID | None,
    action: str,
    result: str,
    ticket_id: uuid.UUID | None = None,
    merch_order_item_id: uuid.UUID | None = None,
    denial_reason: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> DeskScanAuditLog:
    from app.teams.team_audit import sanitize_audit_metadata

    row = DeskScanAuditLog(
        actor_user_id=actor_user_id,
        host_id=host_profile_id,
        event_id=event_id,
        ticket_id=ticket_id,
        merch_order_item_id=merch_order_item_id,
        action=action,
        result=result,
        denial_reason=denial_reason,
        metadata_json=sanitize_audit_metadata(metadata),
    )
    db.add(row)
    db.flush()
    return row
