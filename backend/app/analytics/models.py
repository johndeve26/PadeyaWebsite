"""Analytics tracking tables: events, views, impressions, clicks, conversions.

Rollup / dedupe models live in ``rollup_models`` and are re-exported here so
``from app.analytics import models`` still registers full metadata for create_all.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON, Uuid

from app.core.database import Base

# Re-export rollup / dedupe models for Base.metadata registration.
from app.analytics.rollup_models import (  # noqa: E402, F401
    AnalyticsDedupeKey,
    EventDailyAnalytics,
    EventGeoDeviceAnalytics,
    EventSourceAnalytics,
    EventTicketTypeAnalytics,
)


class AnalyticsEvent(Base):
    """Append-only analytics action stream.

    ``event_name`` stores the taxonomy ``tracked_action`` / ``analytics_event_name``.
    ``target_event_id`` is the product event the action relates to.

    Never UPDATE or DELETE rows in application code — use rollups for aggregates.
    """

    __tablename__ = "analytics_events"
    __table_args__ = (
        Index("ix_analytics_events_name_created", "event_name", "created_at"),
        Index("ix_analytics_events_name_occurred", "event_name", "occurred_at"),
        Index("ix_analytics_events_host_created", "host_id", "created_at"),
        Index("ix_analytics_events_host_occurred", "host_id", "occurred_at"),
        Index("ix_analytics_events_target_occurred", "target_event_id", "occurred_at"),
        Index("ix_analytics_events_session_occurred", "session_id", "occurred_at"),
        Index("ix_analytics_events_anonymous_occurred", "anonymous_id", "occurred_at"),
        Index("ix_analytics_events_user_occurred", "user_id", "occurred_at"),
        Index("ix_analytics_events_entity", "entity_type", "entity_id"),
        Index("ix_analytics_events_source_campaign", "source", "campaign"),
        Index("ix_analytics_events_utm_source_campaign", "utm_source", "utm_campaign"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Canonical analytics action name (tracked_action)
    event_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    target_event_id: Mapped[uuid.UUID | None] = mapped_column(
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
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    anonymous_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    request_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, unique=True, index=True
    )
    occurred_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    # Attribution — ``source``/``medium``/… kept for BC; ``utm_*`` mirrored on write
    source: Mapped[str | None] = mapped_column(String(120), nullable=True)
    medium: Mapped[str | None] = mapped_column(String(120), nullable=True)
    campaign: Mapped[str | None] = mapped_column(String(160), nullable=True)
    term: Mapped[str | None] = mapped_column(String(160), nullable=True)
    content: Mapped[str | None] = mapped_column(String(160), nullable=True)
    utm_source: Mapped[str | None] = mapped_column(String(120), nullable=True)
    utm_medium: Mapped[str | None] = mapped_column(String(120), nullable=True)
    utm_campaign: Mapped[str | None] = mapped_column(String(160), nullable=True)
    utm_term: Mapped[str | None] = mapped_column(String(160), nullable=True)
    utm_content: Mapped[str | None] = mapped_column(String(160), nullable=True)
    referrer: Mapped[str | None] = mapped_column(String(500), nullable=True)
    landing_page: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # ``path`` is canonical; ``current_path`` kept for BC and mirrored on write
    path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    current_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    previous_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    user_agent_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    device_type: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    browser: Mapped[str | None] = mapped_column(String(64), nullable=True)
    os: Mapped[str | None] = mapped_column(String(64), nullable=True)
    country: Mapped[str | None] = mapped_column(String(64), nullable=True)
    city: Mapped[str | None] = mapped_column(String(96), nullable=True)
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Legacy bag — mirrored from event_metadata for older readers
    properties: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    # Preferred JSONB metadata (event-specific dimensions)
    event_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )
    is_bot: Mapped[bool] = mapped_column(
        Boolean(), default=False, server_default="0", nullable=False
    )
    environment: Mapped[str | None] = mapped_column(String(32), nullable=True)
    app_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class PageView(Base):
    __tablename__ = "page_views"
    __table_args__ = (
        Index("ix_page_views_path_created", "path", "created_at"),
        Index("ix_page_views_host_created", "host_id", "created_at"),
        Index("ix_page_views_event_created", "event_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    path: Mapped[str] = mapped_column(String(500), nullable=False)
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
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    referrer: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class EventImpression(Base):
    __tablename__ = "event_impressions"
    __table_args__ = (
        Index("ix_event_impressions_event_created", "event_id", "created_at"),
        Index("ix_event_impressions_host_created", "host_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    host_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("hosts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class EventClick(Base):
    __tablename__ = "event_clicks"
    __table_args__ = (
        Index("ix_event_clicks_event_created", "event_id", "created_at"),
        Index("ix_event_clicks_host_created", "host_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    host_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("hosts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    click_target: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class ConversionEvent(Base):
    __tablename__ = "conversion_events"
    __table_args__ = (
        Index("ix_conversion_events_event_stage_created", "event_id", "stage", "created_at"),
        Index("ix_conversion_events_host_stage_created", "host_id", "stage", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
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
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    stage: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
    )
    amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


__all__ = [
    "AnalyticsEvent",
    "PageView",
    "EventImpression",
    "EventClick",
    "ConversionEvent",
    "EventDailyAnalytics",
    "EventSourceAnalytics",
    "EventTicketTypeAnalytics",
    "EventGeoDeviceAnalytics",
    "AnalyticsDedupeKey",
]
