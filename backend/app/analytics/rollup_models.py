"""Persisted analytics rollups and dedupe keys.

Raw ``analytics_events`` stay append-only. These tables are upsert/recalculate targets.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.core.database import Base


class EventDailyAnalytics(Base):
    """Daily rollup per product event."""

    __tablename__ = "event_daily_analytics"
    __table_args__ = (
        UniqueConstraint("date", "event_id", name="uq_event_daily_analytics_date_event"),
        Index("ix_event_daily_analytics_event_date", "event_id", "date"),
        Index("ix_event_daily_analytics_host_date", "host_id", "date"),
        Index("ix_event_daily_analytics_date", "date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    date: Mapped[date] = mapped_column(Date(), nullable=False)
    event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
    )
    host_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("hosts.id", ondelete="SET NULL"),
        nullable=True,
    )
    impressions: Mapped[int] = mapped_column(Integer(), default=0, server_default="0")
    unique_impressions: Mapped[int] = mapped_column(Integer(), default=0, server_default="0")
    card_clicks: Mapped[int] = mapped_column(Integer(), default=0, server_default="0")
    detail_views: Mapped[int] = mapped_column(Integer(), default=0, server_default="0")
    unique_detail_views: Mapped[int] = mapped_column(Integer(), default=0, server_default="0")
    ticket_panel_views: Mapped[int] = mapped_column(Integer(), default=0, server_default="0")
    ticket_selections: Mapped[int] = mapped_column(Integer(), default=0, server_default="0")
    checkout_starts: Mapped[int] = mapped_column(Integer(), default=0, server_default="0")
    payment_starts: Mapped[int] = mapped_column(Integer(), default=0, server_default="0")
    payment_successes: Mapped[int] = mapped_column(Integer(), default=0, server_default="0")
    payment_failures: Mapped[int] = mapped_column(Integer(), default=0, server_default="0")
    tickets_sold: Mapped[int] = mapped_column(Integer(), default=0, server_default="0")
    gross_revenue: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0"), server_default="0"
    )
    net_revenue: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    promo_uses: Mapped[int] = mapped_column(Integer(), default=0, server_default="0")
    ambassador_sales: Mapped[int] = mapped_column(Integer(), default=0, server_default="0")
    shares: Mapped[int] = mapped_column(Integer(), default=0, server_default="0")
    saves: Mapped[int] = mapped_column(Integer(), default=0, server_default="0")
    follows: Mapped[int] = mapped_column(Integer(), default=0, server_default="0")
    reviews_submitted: Mapped[int] = mapped_column(Integer(), default=0, server_default="0")
    checkins: Mapped[int] = mapped_column(Integer(), default=0, server_default="0")
    conversion_impression_to_view: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 6), nullable=True
    )
    conversion_view_to_checkout: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 6), nullable=True
    )
    conversion_checkout_to_purchase: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 6), nullable=True
    )
    conversion_view_to_purchase: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 6), nullable=True
    )
    recalculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
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


class EventSourceAnalytics(Base):
    """Daily rollup by attribution source/channel."""

    __tablename__ = "event_source_analytics"
    __table_args__ = (
        UniqueConstraint(
            "date",
            "event_id",
            "source",
            "medium",
            "campaign",
            name="uq_event_source_analytics_dims",
        ),
        Index("ix_event_source_analytics_event_date", "event_id", "date"),
        Index("ix_event_source_analytics_source_date", "source", "date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    date: Mapped[date] = mapped_column(Date(), nullable=False)
    event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
    )
    source: Mapped[str] = mapped_column(String(120), nullable=False, default="(none)")
    medium: Mapped[str] = mapped_column(String(120), nullable=False, default="(none)")
    campaign: Mapped[str] = mapped_column(String(160), nullable=False, default="(none)")
    impressions: Mapped[int] = mapped_column(Integer(), default=0, server_default="0")
    clicks: Mapped[int] = mapped_column(Integer(), default=0, server_default="0")
    views: Mapped[int] = mapped_column(Integer(), default=0, server_default="0")
    checkout_starts: Mapped[int] = mapped_column(Integer(), default=0, server_default="0")
    purchases: Mapped[int] = mapped_column(Integer(), default=0, server_default="0")
    tickets_sold: Mapped[int] = mapped_column(Integer(), default=0, server_default="0")
    revenue: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0"), server_default="0"
    )
    conversion_rate: Mapped[Decimal | None] = mapped_column(Numeric(8, 6), nullable=True)
    recalculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
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


class EventTicketTypeAnalytics(Base):
    """Daily rollup by ticket type."""

    __tablename__ = "event_ticket_type_analytics"
    __table_args__ = (
        UniqueConstraint(
            "date",
            "event_id",
            "ticket_type_id",
            name="uq_event_ticket_type_analytics_dims",
        ),
        Index("ix_event_ticket_type_analytics_event_date", "event_id", "date"),
        Index("ix_event_ticket_type_analytics_ticket_date", "ticket_type_id", "date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    date: Mapped[date] = mapped_column(Date(), nullable=False)
    event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
    )
    ticket_type_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ticket_types.id", ondelete="CASCADE"),
        nullable=False,
    )
    impressions: Mapped[int] = mapped_column(Integer(), default=0, server_default="0")
    selections: Mapped[int] = mapped_column(Integer(), default=0, server_default="0")
    checkout_starts: Mapped[int] = mapped_column(Integer(), default=0, server_default="0")
    tickets_sold: Mapped[int] = mapped_column(Integer(), default=0, server_default="0")
    revenue: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0"), server_default="0"
    )
    conversion_rate: Mapped[Decimal | None] = mapped_column(Numeric(8, 6), nullable=True)
    recalculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
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


class EventGeoDeviceAnalytics(Base):
    """Daily rollup by country/city/device/browser."""

    __tablename__ = "event_geo_device_analytics"
    __table_args__ = (
        UniqueConstraint(
            "date",
            "event_id",
            "country",
            "city",
            "device_type",
            "browser",
            name="uq_event_geo_device_analytics_dims",
        ),
        Index("ix_event_geo_device_analytics_event_date", "event_id", "date"),
        Index("ix_event_geo_device_analytics_country_date", "country", "date"),
        Index("ix_event_geo_device_analytics_device_date", "device_type", "date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    date: Mapped[date] = mapped_column(Date(), nullable=False)
    event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
    )
    country: Mapped[str] = mapped_column(String(64), nullable=False, default="(none)")
    city: Mapped[str] = mapped_column(String(96), nullable=False, default="(none)")
    device_type: Mapped[str] = mapped_column(String(32), nullable=False, default="(none)")
    browser: Mapped[str] = mapped_column(String(64), nullable=False, default="(none)")
    views: Mapped[int] = mapped_column(Integer(), default=0, server_default="0")
    checkout_starts: Mapped[int] = mapped_column(Integer(), default=0, server_default="0")
    purchases: Mapped[int] = mapped_column(Integer(), default=0, server_default="0")
    tickets_sold: Mapped[int] = mapped_column(Integer(), default=0, server_default="0")
    revenue: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0"), server_default="0"
    )
    recalculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
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


class AnalyticsDedupeKey(Base):
    """Idempotency / impression-click dedupe keys (separate from raw stream)."""

    __tablename__ = "analytics_dedupe_keys"
    __table_args__ = (
        UniqueConstraint("dedupe_key", name="uq_analytics_dedupe_keys_key"),
        Index("ix_analytics_dedupe_keys_scope_created", "scope", "created_at"),
        Index("ix_analytics_dedupe_keys_event_created", "target_event_id", "created_at"),
        Index("ix_analytics_dedupe_keys_expires", "expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    dedupe_key: Mapped[str] = mapped_column(String(191), nullable=False)
    scope: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        doc="e.g. request_id, impression, click",
    )
    target_event_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("events.id", ondelete="SET NULL"),
        nullable=True,
    )
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    anonymous_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
