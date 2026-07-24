"""Canonical ambassador referral click rows (total vs unique metrics)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, func
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.core.database import Base


class ReferralClick(Base):
    """Privacy-safe referral landing events for ambassador analytics."""

    __tablename__ = "referral_clicks"
    __table_args__ = (
        Index("ix_referral_clicks_ambassador_created", "ambassador_id", "created_at"),
        Index("ix_referral_clicks_participant_created", "participant_id", "created_at"),
        Index("ix_referral_clicks_campaign_created", "campaign_id", "created_at"),
        Index("ix_referral_clicks_unique_key_created", "unique_click_key", "created_at"),
        Index("ix_referral_clicks_total_key_created", "total_click_key", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    ambassador_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ambassadors.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    participant_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ambassador_participants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ambassador_campaigns.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("events.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    merch_product_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("event_merch_products.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    host_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("hosts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    referral_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # event | merch | host | campaign | checkout
    target_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    target_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    # event_page | merch_page | checkout | host_page | campaign_link
    source: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    visitor_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    total_click_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    unique_click_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_unique_24h: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_duplicate_30s: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_qualified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    metadata_json: Mapped[dict | None] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=True,
    )
