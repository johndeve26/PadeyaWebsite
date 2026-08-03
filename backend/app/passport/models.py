"""Fan Passport, badges, and loyalty ORM models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON, Uuid

from app.core.database import Base


class FanPassport(Base):
    __tablename__ = "fan_passports"
    __table_args__ = (UniqueConstraint("user_id", name="uq_fan_passports_user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    username: Mapped[str | None] = mapped_column(
        String(64), unique=True, nullable=True, index=True
    )
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    avatar_media: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    tagline: Mapped[str | None] = mapped_column(String(200), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    # private | unlisted (direct link) | public (default)
    visibility: Mapped[str] = mapped_column(
        String(16), default="public", nullable=False, index=True
    )
    show_attended_events: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    show_badges: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    show_followed_hosts: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    show_reviews: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    show_vault_unlocks: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    show_city_category_stats: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    hide_private_events_always: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    # On by default; forced off when visibility is not public
    appear_in_directory: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, index=True
    )
    admin_hidden_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    admin_hidden_reason: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    # Cached counters refreshed on passport load
    tickets_bought: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    events_attended: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    hosts_followed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    vip_purchases: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    vault_unlocks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_superfan: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    favorite_categories: Mapped[list[Any] | None] = mapped_column(
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


class FanBadge(Base):
    __tablename__ = "fan_badges"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    criteria_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class UserBadge(Base):
    __tablename__ = "user_badges"
    __table_args__ = (
        UniqueConstraint("user_id", "badge_id", name="uq_user_badges_user_badge"),
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
    badge_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("fan_badges.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    awarded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    meta: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )


class LoyaltyRecord(Base):
    __tablename__ = "loyalty_records"
    __table_args__ = (
        UniqueConstraint("user_id", "host_id", name="uq_loyalty_records_user_host"),
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
    host_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("hosts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tickets_bought: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    check_ins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    vip_purchases: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_superfan: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    follows_host: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
