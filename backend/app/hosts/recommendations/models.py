"""ORM for fan host recommendation dismissals, feedback, impressions, category hides."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON, Uuid

from app.core.database import Base


class HostRecommendationDismissal(Base):
    __tablename__ = "host_recommendation_dismissals"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "host_id",
            name="uq_host_recommendation_dismissals_pair",
        ),
        Index(
            "ix_host_recommendation_dismissals_user_dismissed",
            "user_id",
            "dismissed_at",
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
    host_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("hosts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reason: Mapped[str | None] = mapped_column(String(120), nullable=True)
    dismissed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class HostRecommendationFeedback(Base):
    __tablename__ = "host_recommendation_feedback"
    __table_args__ = (
        Index(
            "ix_host_recommendation_feedback_user_created",
            "user_id",
            "created_at",
        ),
        Index(
            "ix_host_recommendation_feedback_user_action",
            "user_id",
            "action",
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
    host_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("hosts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    context: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class HostRecommendationImpression(Base):
    """Lightweight shown-at trail for ignored-host detection."""

    __tablename__ = "host_recommendation_impressions"
    __table_args__ = (
        Index(
            "ix_host_recommendation_impressions_user_shown",
            "user_id",
            "shown_at",
        ),
        Index(
            "ix_host_recommendation_impressions_user_host",
            "user_id",
            "host_id",
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
    host_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("hosts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    surface: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recommendation_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reason_codes: Mapped[list[Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )
    shown_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class HostRecommendationCategoryHide(Base):
    __tablename__ = "host_recommendation_category_hides"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "category_slug",
            name="uq_host_recommendation_category_hides_pair",
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
    category_slug: Mapped[str] = mapped_column(String(120), nullable=False)
    hidden_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
