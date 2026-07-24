"""Fan Connect ORM models — discoverability on by default; fans can disable."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON, Uuid

from app.core.database import Base


def _default_request_policies() -> list[str]:
    return ["same_event"]


class FanConnectSettings(Base):
    __tablename__ = "fan_connect_settings"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_fan_connect_settings_user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fan_connect_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    discoverable_for_same_events: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    discoverable_for_similar_interests: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    allow_connection_requests: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    show_shared_hosts: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    show_shared_categories: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    show_shared_public_events: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    show_public_city: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    hide_private_events_always: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    # Legacy single policy — kept in sync with the most permissive selected value.
    # same_event | same_host | public_passports | nobody
    request_policy: Mapped[str] = mapped_column(
        String(32), default="same_event", nullable=False
    )
    # Multi-select policies (OR). ``nobody`` is exclusive.
    request_policies: Mapped[list[Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=_default_request_policies,
        nullable=False,
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


class FanConnection(Base):
    """One row per unordered fan pair (canonical user_low / user_high)."""

    __tablename__ = "fan_connections"
    __table_args__ = (
        UniqueConstraint(
            "user_low_id",
            "user_high_id",
            name="uq_fan_connections_pair",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Canonical unordered pair for uniqueness (not exposed in public API).
    user_low_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_high_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requester_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recipient_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # suggested | request_sent | connected | declined | blocked | removed
    status: Mapped[str] = mapped_column(
        String(32), default="suggested", nullable=False, index=True
    )
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    # Safe public reason codes only — never private venue/ticket/order/payment.
    reasons_json: Mapped[list[Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    related_event_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("events.id", ondelete="SET NULL"),
        nullable=True,
    )
    related_host_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("hosts.id", ondelete="SET NULL"),
        nullable=True,
    )
    request_message: Mapped[str | None] = mapped_column(String(280), nullable=True)
    # Messaging unlock after accept (product; not private data).
    message_thread_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("message_threads.id", ondelete="SET NULL"),
        nullable=True,
    )
    requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    declined_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    declined_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    requester_cooldown_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    removed_at: Mapped[datetime | None] = mapped_column(
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


class FanConnectionBlock(Base):
    __tablename__ = "fan_connection_blocks"
    __table_args__ = (
        UniqueConstraint(
            "blocker_user_id",
            "blocked_user_id",
            name="uq_fan_connection_blocks_pair",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    blocker_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    blocked_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reason: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class FanConnectionReport(Base):
    __tablename__ = "fan_connection_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    reporter_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reported_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    connection_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("fan_connections.id", ondelete="SET NULL"),
        nullable=True,
    )
    thread_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("message_threads.id", ondelete="SET NULL"),
        nullable=True,
    )
    reason: Mapped[str] = mapped_column(String(120), nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    # open | reviewing | resolved | dismissed
    status: Mapped[str] = mapped_column(
        String(32), default="open", nullable=False, index=True
    )
    admin_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class FanConnectSuggestion(Base):
    """Optional cache of privacy-safe suggestion rows."""

    __tablename__ = "fan_connect_suggestions"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "suggested_user_id",
            name="uq_fan_connect_suggestions_pair",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    suggested_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    reasons_json: Mapped[list[Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
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


class FanConnectSuggestionDismissal(Base):
    """Actor dismissed a suggestion target — exclude while expires_at active; else −30."""

    __tablename__ = "fan_connect_suggestion_dismissals"
    __table_args__ = (
        UniqueConstraint(
            "actor_user_id",
            "target_user_id",
            name="uq_fan_connect_suggestion_dismissals_pair",
        ),
        Index(
            "ix_fan_connect_suggestion_dismissals_actor_dismissed",
            "actor_user_id",
            "dismissed_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    actor_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reason: Mapped[str | None] = mapped_column(String(120), nullable=True)
    dismissed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )


class FanConnectSuggestionFeedback(Base):
    """Privacy-safe suggestion interaction trail for personalization."""

    __tablename__ = "fan_connect_suggestion_feedback"
    __table_args__ = (
        Index(
            "ix_fan_connect_suggestion_feedback_actor_created",
            "actor_user_id",
            "created_at",
        ),
        Index(
            "ix_fan_connect_suggestion_feedback_actor_action",
            "actor_user_id",
            "action",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    actor_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # impression | click | dismiss | more_like_this | connect_request
    action: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    context: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class FanConnectLocationPreference(Base):
    """Opt-in approximate city/area preference — never raw browser GPS by default."""

    __tablename__ = "fan_connect_location_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_fan_connect_location_preferences_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    area: Mapped[str | None] = mapped_column(String(120), nullable=True)
    country: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # Coarse centroids only when precision=approximate and user explicitly saved.
    latitude_approx: Mapped[str | None] = mapped_column(String(32), nullable=True)
    longitude_approx: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # city | area | approximate
    precision: Mapped[str] = mapped_column(String(32), default="city", nullable=False)
    consented_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
