"""Account suspension public metadata + appeals (soft lifecycle)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.database import Base

SUSPENSION_STATUS_ACTIVE = "active"
SUSPENSION_STATUS_LIFTED = "lifted"

APPEAL_STATUS_PENDING = "pending"
APPEAL_STATUS_APPROVED = "approved"
APPEAL_STATUS_REJECTED = "rejected"
APPEAL_STATUS_WITHDRAWN = "withdrawn"

# User-facing categories only — never fraud internals.
SUSPENSION_REASON_CATEGORIES = frozenset(
    {
        "policy_violation",
        "abuse_or_harassment",
        "safety",
        "account_security",
        "terms_of_service",
        "other",
    }
)

SUSPENSION_CATEGORY_LABELS = {
    "policy_violation": "Policy violation",
    "abuse_or_harassment": "Abuse or harassment",
    "safety": "Safety",
    "account_security": "Account security",
    "terms_of_service": "Terms of service",
    "other": "Other",
}


class AccountSuspension(Base):
    """Public-safe suspension record (no internal admin notes)."""

    __tablename__ = "account_suspensions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=SUSPENSION_STATUS_ACTIVE, index=True
    )
    reason_category: Mapped[str] = mapped_column(String(64), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by_admin_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    lifted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    lifted_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    appeals: Mapped[list[AccountAppeal]] = relationship(
        back_populates="suspension",
        cascade="all, delete-orphan",
    )


class AccountAppeal(Base):
    """User appeal against an active suspension — soft status only."""

    __tablename__ = "account_appeals"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    suspension_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("account_suspensions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=APPEAL_STATUS_PENDING, index=True
    )
    admin_reply: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    reviewed_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    suspension: Mapped[AccountSuspension] = relationship(back_populates="appeals")
