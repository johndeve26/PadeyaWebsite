"""Schemas for Featured Placements / Pàdéyá Picks."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.events.schemas import EventPublic


class FeaturedPlacementSlotPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    placement_key: str
    context_key: str | None = None
    placement_type: str
    context_type: str
    context_id: UUID | None = None
    location_id: UUID | None = None
    country_id: UUID | None = None
    state_id: UUID | None = None
    city_id: UUID | None = None
    area_id: UUID | None = None
    category_id: UUID | None = None
    slot_number: int
    slot_index: int | None = None
    slot_label: str
    event_id: UUID | None
    title_override: str | None = None
    subtitle_override: str | None = None
    badge_text: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    status: str
    created_by: UUID | None = None
    updated_by: UUID | None = None
    created_at: datetime
    updated_at: datetime
    event: EventPublic | None = None


class FeaturedPlacementAssign(BaseModel):
    context_type: str = Field(
        description=(
            "placement_type or legacy alias: homepage | events_page | country_page | … "
            "or global_homepage | events | country | …"
        ),
    )
    location_id: UUID | None = Field(
        default=None,
        description="Primary location for country/state/city/city_category pages",
    )
    category_id: UUID | None = Field(
        default=None,
        description="Required for category_page and city_category_page",
    )
    event_id: UUID | None = Field(
        default=None,
        description="Published listed event id, or null to clear the slot",
    )
    title_override: str | None = None
    subtitle_override: str | None = None
    badge_text: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    status: str | None = Field(
        default=None,
        description="Optional: draft | active | scheduled | expired | archived",
    )


class FeaturedPlacementContextPublic(BaseModel):
    id: UUID | None = Field(
        default=None,
        description="Stable set id (Primary Spotlight row id) for admin edit routes",
    )
    context_key: str
    placement_key: str | None = None
    context_type: str
    placement_type: str | None = None
    context_label: str
    location_id: UUID | None = None
    country_id: UUID | None = None
    state_id: UUID | None = None
    city_id: UUID | None = None
    area_id: UUID | None = None
    category_id: UUID | None = None
    location_name: str | None = None
    location_slug: str | None = None
    location_kind: str | None = None
    category_name: str | None = None
    category_slug: str | None = None
    display_title: str
    status: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    title_override: str | None = None
    subtitle_override: str | None = None
    badge_text: str | None = None
    slots: list[FeaturedPlacementSlotPublic]


class FeaturedPlacementSlotInput(BaseModel):
    event_id: UUID | None = None


class FeaturedPlacementSetUpsert(BaseModel):
    context_type: str = Field(
        description="placement_type or legacy alias",
    )
    location_id: UUID | None = None
    category_id: UUID | None = None
    slot_1: FeaturedPlacementSlotInput = Field(default_factory=FeaturedPlacementSlotInput)
    slot_2: FeaturedPlacementSlotInput = Field(default_factory=FeaturedPlacementSlotInput)
    title_override: str | None = None
    subtitle_override: str | None = None
    badge_text: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    status: str | None = Field(
        default=None,
        description="draft | active | scheduled | expired | archived",
    )


class FeaturedPlacementSetStatusUpdate(BaseModel):
    status: str = Field(description="active | draft | archived")


class ListingPadeyaPickRequest(BaseModel):
    """Assign a listing into a global Pàdéyá Pick slot from listing admin."""

    event_id: UUID
    context_type: str = Field(
        default="homepage",
        description="homepage or events_page (legacy aliases accepted)",
    )
    slot_number: int | None = Field(
        default=None,
        ge=1,
        le=2,
        description="Optional Primary (1) or Secondary (2); defaults to first empty slot",
    )


class ListingPadeyaPickClearRequest(BaseModel):
    event_id: UUID
    context_type: str = Field(
        default="homepage",
        description="homepage or events_page (legacy aliases accepted)",
    )


class ListingPadeyaPickSwapRequest(BaseModel):
    context_type: str = Field(
        default="homepage",
        description="homepage or events_page (legacy aliases accepted)",
    )

