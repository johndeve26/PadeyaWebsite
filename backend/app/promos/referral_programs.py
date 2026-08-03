"""Referral programs — parent umbrella for event campaigns + platform-wide programs."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.core.database import Base


class ReferralProgram(Base):
    """Top-level referral/ambassador program (event-scoped or platform-wide)."""

    __tablename__ = "referral_programs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    public_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # event | platform
    scope: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    # host | platform
    owner_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    owner_host_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("hosts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    # draft | scheduled | active | paused | ended | archived
    status: Mapped[str] = mapped_column(
        String(32), default="active", nullable=False, index=True
    )
    # invite_only | application | manual_enrollment | public_open
    enrollment_mode: Mapped[str] = mapped_column(
        String(32), default="manual_enrollment", nullable=False
    )
    starts_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    attribution_window_days: Mapped[int] = mapped_column(
        Integer, default=30, nullable=False
    )
    # homepage | events | shop | curated path (internal only)
    default_landing_path: Mapped[str] = mapped_column(
        String(500), default="/events", nullable=False
    )
    hold_period_days: Mapped[int] = mapped_column(Integer, default=7, nullable=False)
    budget_total: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    per_ambassador_cap: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2), nullable=True
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
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


class ReferralProgramRule(Base):
    """Earning rule under a program (tickets and/or merchandise)."""

    __tablename__ = "referral_program_rules"
    __table_args__ = (
        UniqueConstraint(
            "program_id",
            "product_type",
            name="uq_referral_program_rules_program_product",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    program_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("referral_programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # ticket | merchandise
    product_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    # percentage | fixed
    commission_mode: Mapped[str] = mapped_column(
        String(32), default="percentage", nullable=False
    )
    commission_value: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("5.00"), nullable=False
    )
    maximum_commission_per_item: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    minimum_order_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class ReferralProgramExclusion(Base):
    """Host/event exclusions for platform-wide programs."""

    __tablename__ = "referral_program_exclusions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    program_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("referral_programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    host_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("hosts.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
