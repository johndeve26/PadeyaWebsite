"""Legacy tiers, host scores, score history, and Content Studio models."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

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
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON, Uuid

from app.core.database import Base


class LegacyTier(Base):
    __tablename__ = "legacy_tiers"
    __table_args__ = (UniqueConstraint("slug", name="uq_legacy_tiers_slug"),)

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    slug: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    min_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    requirements: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
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


class HostLegacyScore(Base):
    __tablename__ = "host_legacy_scores"
    __table_args__ = (UniqueConstraint("host_id", name="uq_host_legacy_scores_host_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    host_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("hosts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tier_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("legacy_tiers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    events_hosted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_events: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tickets_sold: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    verified_checkins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    average_verified_rating: Mapped[Decimal | None] = mapped_column(
        Numeric(3, 2), nullable=True
    )
    review_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    followers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    repeat_buyers_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    refund_dispute_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    composite_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("0"), nullable=False
    )
    factor_scores: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    # Synced to current tier name for Legacy Page display
    legacy_status: Mapped[str] = mapped_column(
        String(64), default="New Host", nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class HostLegacyScoreHistory(Base):
    __tablename__ = "host_legacy_score_history"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    host_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("hosts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tier_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("legacy_tiers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    previous_tier_slug: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tier_slug: Mapped[str] = mapped_column(String(64), nullable=False)
    composite_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    previous_composite_score: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    factor_scores: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    metrics_snapshot: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    reason: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class HostLegacyPage(Base):
    """Host-managed Legacy Page settings (reputation + monetization hub)."""

    __tablename__ = "host_legacy_pages"
    __table_args__ = (UniqueConstraint("host_id", name="uq_host_legacy_pages_host_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    host_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("hosts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tagline: Mapped[str | None] = mapped_column(String(280), nullable=True)
    primary_category_slug: Mapped[str | None] = mapped_column(String(120), nullable=True)
    host_type_slug: Mapped[str | None] = mapped_column(String(120), nullable=True)
    service_areas: Mapped[list[Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    sponsorship_available: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    sponsorship_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    primary_cta_label: Mapped[str | None] = mapped_column(String(80), nullable=True)
    primary_cta_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    primary_cta_value: Mapped[str | None] = mapped_column(String(500), nullable=True)
    secondary_cta_label: Mapped[str | None] = mapped_column(String(80), nullable=True)
    secondary_cta_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    secondary_cta_value: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class HostLegacyContentBlock(Base):
    __tablename__ = "host_legacy_content_blocks"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    host_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("hosts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    block_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title_override: Mapped[str | None] = mapped_column(String(160), nullable=True)
    description_override: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)
    layout_style: Mapped[str] = mapped_column(
        String(64), default="default", nullable=False
    )
    source_type: Mapped[str] = mapped_column(
        String(32), default="automatic", nullable=False
    )
    item_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    config: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
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


class HostLegacyFeaturedItem(Base):
    __tablename__ = "host_legacy_featured_items"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    host_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("hosts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    item_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    placement: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class HostSocialLink(Base):
    __tablename__ = "host_social_links"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    host_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("hosts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    platform: Mapped[str] = mapped_column(String(64), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class HostContactSettings(Base):
    __tablename__ = "host_contact_settings"
    __table_args__ = (
        UniqueConstraint("host_id", name="uq_host_contact_settings_host_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    host_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("hosts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    preference: Mapped[str] = mapped_column(
        String(40), default="none", nullable=False
    )
    public_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    show_contact_form: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    preferred_channel: Mapped[str | None] = mapped_column(String(64), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
