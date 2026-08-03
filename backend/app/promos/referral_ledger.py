"""Authoritative referral attributions and append-only commission ledger."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.core.database import Base


class ReferralAttribution(Base):
    """Referral attribution per order item and payer (host and/or platform)."""

    __tablename__ = "referral_attributions"
    __table_args__ = (
        UniqueConstraint(
            "order_id",
            "attribution_item_key",
            "payer_type",
            name="uq_referral_attributions_order_item_payer",
        ),
        UniqueConstraint(
            "idempotency_key",
            name="uq_referral_attributions_idempotency",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_item_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("order_items.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Stable identity: prefer order_item UUID string; legacy uses synthetic keys
    attribution_item_key: Mapped[str] = mapped_column(String(120), nullable=False)
    program_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("referral_programs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ambassador_campaigns.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    enrollment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ambassadors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ambassador_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("events.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    host_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("hosts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # ticket | merchandise
    product_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True
    )
    # host | platform
    payer_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    # event | platform
    winning_scope: Mapped[str] = mapped_column(String(32), nullable=False)
    # explicit_code | touch | cookie | legacy
    attribution_source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
    resolved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ReferralCommissionEntry(Base):
    """Append-only referral commission ledger. Monetary fields are immutable."""

    __tablename__ = "referral_commission_entries"
    __table_args__ = (
        UniqueConstraint(
            "idempotency_key",
            name="uq_referral_commission_entries_idempotency",
        ),
        Index(
            "ix_referral_commission_entries_ambassador_created",
            "ambassador_user_id",
            "created_at",
        ),
        Index(
            "ix_referral_commission_entries_payer_status",
            "payer_type",
            "status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    attribution_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("referral_attributions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    program_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("referral_programs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ambassador_campaigns.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    rule_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("referral_program_rules.id", ondelete="SET NULL"),
        nullable=True,
    )
    enrollment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ambassadors.id", ondelete="SET NULL"),
        nullable=False,
        index=True,
    )
    ambassador_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_item_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("order_items.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    attribution_item_key: Mapped[str] = mapped_column(String(120), nullable=False)
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("events.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    host_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("hosts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    product_type: Mapped[str] = mapped_column(String(32), nullable=False)
    # host | platform
    payer_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    # earning | reversal | adjustment | payout
    entry_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    original_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("referral_commission_entries.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    gross_item_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    eligible_commission_base: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    commission_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    commission_rate: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False, default=Decimal("0")
    )
    commission_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False
    )
    currency: Mapped[str] = mapped_column(String(8), default="NGN", nullable=False)
    # pending | approved | payable | paid | disputed
    status: Mapped[str] = mapped_column(
        String(32), default="pending", nullable=False, index=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    source_event_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    payable_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
