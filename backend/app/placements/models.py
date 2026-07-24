"""Featured placements — Primary/Secondary Spotlight rows for Pàdéyá Picks."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.core.database import Base


class FeaturedPlacement(Base):
    __tablename__ = "featured_placements"
    __table_args__ = (
        UniqueConstraint(
            "placement_key",
            "slot_number",
            name="uq_featured_placements_key_slot",
        ),
        CheckConstraint("slot_number IN (1, 2)", name="ck_featured_placements_slot"),
        CheckConstraint(
            "placement_type IN ("
            "'homepage', 'events_page', 'country_page', 'state_page', "
            "'city_page', 'area_page', 'category_page', 'city_category_page'"
            ")",
            name="ck_featured_placements_type",
        ),
        CheckConstraint(
            "status IN ('draft', 'active', 'scheduled', 'expired', 'archived')",
            name="ck_featured_placements_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Stable lookup key, e.g. homepage | city_page:{uuid} | city_category_page:{city}:{cat}
    placement_key: Mapped[str] = mapped_column(String(220), nullable=False, index=True)
    placement_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    context_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    context_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True, index=True
    )
    country_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("locations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    state_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("locations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    city_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("locations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    area_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("locations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("event_categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Nullable so draft/empty slots can exist; required for active/scheduled.
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("events.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    slot_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title_override: Mapped[str | None] = mapped_column(String(200), nullable=True)
    subtitle_override: Mapped[str | None] = mapped_column(String(255), nullable=True)
    badge_text: Mapped[str | None] = mapped_column(String(80), nullable=True)
    starts_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="draft", index=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
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


# Back-compat alias while callers migrate.
FeaturedPlacementSlot = FeaturedPlacement
