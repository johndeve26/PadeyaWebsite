"""Legacy Page and tier schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.hosts.schemas import HostProfilePublic
from app.reviews.schemas import ReviewPublic


class LegacyTierPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    name: str
    rank: int
    min_score: Decimal
    description: str | None
    requirements: dict[str, Any] | None
    is_active: bool


class LegacyTierUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=80)
    min_score: Decimal | None = Field(default=None, ge=0, le=100)
    description: str | None = None
    requirements: dict[str, Any] | None = None
    is_active: bool | None = None


class LegacyStatsPublic(BaseModel):
    events_hosted: int
    tickets_sold: int
    verified_checkins: int
    average_verified_rating: Decimal | None
    review_count: int
    followers: int
    repeat_buyers_rate: Decimal | None
    refund_dispute_rate: Decimal | None
    legacy_status: str
    composite_score: Decimal | None = None
    completed_events: int | None = None
    # Merch proof aggregates — counts only; never buyer identities or spend
    merch_items_sold: int = 0
    fans_collected_merch: int = 0
    merch_proof_summaries: list[str] = Field(default_factory=list)


class LegacyEventCard(BaseModel):
    id: UUID
    title: str
    slug: str
    start_datetime: datetime
    end_datetime: datetime
    city: str | None
    banner_url: str | None
    status: str
    memory_path: str | None = None


class LegacyMemoryCard(BaseModel):
    id: UUID
    event_id: UUID
    event_title: str
    event_slug: str
    start_datetime: datetime
    city: str | None
    banner_url: str | None
    share_path: str
    verified_rating: Decimal | None = None


class LegacyContentBlockPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    host_id: UUID
    block_type: str
    title_override: str | None = None
    description_override: str | None = None
    is_visible: bool
    sort_order: int
    layout_style: str
    source_type: str
    item_limit: int | None = None
    config: dict[str, Any] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class LegacyFeaturedItemPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID | None = None
    host_id: UUID | None = None
    item_type: str
    item_id: UUID
    placement: str
    sort_order: int = 0
    created_at: datetime | None = None


class LegacySocialLinkPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID | None = None
    host_id: UUID | None = None
    platform: str
    url: str
    label: str | None = None
    sort_order: int = 0
    is_visible: bool = True
    created_at: datetime | None = None


class LegacyContactPublic(BaseModel):
    preference: str = "none"
    public_email: str | None = None
    show_contact_form: bool = False
    preferred_channel: str | None = None
    note: str | None = None
    id: UUID | None = None
    host_id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class LegacyPageSettingsPublic(BaseModel):
    tagline: str | None = None
    primary_category_slug: str | None = None
    host_type_slug: str | None = None
    service_areas: list[Any] = Field(default_factory=list)
    sponsorship_available: bool = False
    sponsorship_note: str | None = None
    primary_cta_label: str | None = None
    primary_cta_type: str | None = None
    primary_cta_value: str | None = None
    secondary_cta_label: str | None = None
    secondary_cta_type: str | None = None
    secondary_cta_value: str | None = None


class LegacyVaultPreviewCard(BaseModel):
    id: UUID
    title: str
    slug: str
    cover_url: str | None = None
    preview_text: str | None = None
    locked: bool = True
    has_access: bool = False
    featured: bool = False
    access_type: str | None = None
    content_type: str | None = None
    price: Decimal | None = None
    currency: str | None = None
    share_path: str


class LegacySponsorPackageCard(BaseModel):
    id: UUID
    title: str
    description: str
    price: Decimal
    currency: str
    slot_type: str
    accepting_sponsors: bool = False


class LegacyPagePublic(BaseModel):
    host_id: UUID
    display_name: str
    username: str
    status: str
    verified: bool
    legacy_status: str
    tier: LegacyTierPublic | None = None
    composite_score: Decimal | None = None
    profile: HostProfilePublic | None
    stats: LegacyStatsPublic
    about: str | None
    upcoming_events: list[LegacyEventCard]
    past_events: list[LegacyEventCard]
    event_memories: list[LegacyMemoryCard] = []
    reviews: list[ReviewPublic]
    follow_enabled: bool = False
    share_path: str
    tagline: str | None = None
    settings: LegacyPageSettingsPublic | None = None
    content_blocks: list[LegacyContentBlockPublic] = []
    featured_items: list[LegacyFeaturedItemPublic] = []
    social_links: list[LegacySocialLinkPublic] = []
    contact: LegacyContactPublic | None = None
    vault_preview: list[LegacyVaultPreviewCard] = []
    sponsor_packages: list[LegacySponsorPackageCard] = []
    reviews_block_hidden: bool = False
    trust_note: str | None = None


class LegacyProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=2, max_length=160)
    username: str | None = Field(default=None, min_length=2, max_length=180)
    bio: str | None = None
    website: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, max_length=120)
    country: str | None = Field(default=None, max_length=120)
    avatar_url: str | None = Field(default=None, max_length=500)
    cover_url: str | None = Field(default=None, max_length=500)
    social_links: list[dict[str, Any]] | dict[str, Any] | None = None
    tagline: str | None = Field(default=None, max_length=280)
    primary_category_slug: str | None = Field(default=None, max_length=120)
    host_type_slug: str | None = Field(default=None, max_length=120)
    host_type_slugs: list[str] | None = None
    category_slugs: list[str] | None = None
    audience_slugs: list[str] | None = None
    primary_city_slug: str | None = None
    service_area_slugs: list[str] | None = None
    service_areas: list[Any] | None = None
    niche_positioning: str | None = Field(default=None, max_length=280)
    sponsorship_available: bool | None = None
    sponsorship_note: str | None = None
    primary_cta_label: str | None = Field(default=None, max_length=80)
    primary_cta_type: str | None = Field(default=None, max_length=40)
    primary_cta_value: str | None = Field(default=None, max_length=500)
    secondary_cta_label: str | None = Field(default=None, max_length=80)
    secondary_cta_type: str | None = Field(default=None, max_length=40)
    secondary_cta_value: str | None = Field(default=None, max_length=500)
    contact: LegacyContactPublic | None = None


class LegacyContentBlockCreate(BaseModel):
    block_type: str
    title_override: str | None = Field(default=None, max_length=160)
    description_override: str | None = None
    is_visible: bool = True
    sort_order: int | None = None
    layout_style: str = "default"
    source_type: str = "automatic"
    item_limit: int | None = Field(default=None, ge=1, le=50)
    config: dict[str, Any] | None = None


class LegacyContentBlockUpdate(BaseModel):
    block_type: str | None = None
    title_override: str | None = Field(default=None, max_length=160)
    description_override: str | None = None
    is_visible: bool | None = None
    sort_order: int | None = None
    layout_style: str | None = None
    source_type: str | None = None
    item_limit: int | None = Field(default=None, ge=1, le=50)
    config: dict[str, Any] | None = None


class LegacyContentBlockReorder(BaseModel):
    ordered_ids: list[UUID]


class LegacyFeaturedItemUpsert(BaseModel):
    item_type: str
    item_id: UUID
    placement: str
    sort_order: int = 0


class RequirementItem(BaseModel):
    key: str
    label: str
    current: float
    required: float
    met: bool


class ScoreHistoryPublic(BaseModel):
    id: UUID
    tier_slug: str
    previous_tier_slug: str | None = None
    composite_score: Decimal
    previous_composite_score: Decimal | None = None
    reason: str
    created_at: datetime
    factor_scores: dict[str, Any] | None = None
    metrics_snapshot: dict[str, Any] | None = None
    host_id: UUID | None = None


class TierProgressPublic(BaseModel):
    host_id: UUID
    composite_score: Decimal
    factor_scores: dict[str, Any]
    current_tier: LegacyTierPublic | None
    next_tier: LegacyTierPublic | None
    progress_percentage: Decimal
    requirements_met: list[RequirementItem]
    requirements_remaining: list[RequirementItem]
    suggested_actions: list[str]
    metrics: dict[str, Any]
    history: list[ScoreHistoryPublic]


class HostDiscoveryNextEvent(BaseModel):
    title: str
    slug: str
    start_datetime: datetime
    city: str | None = None


class HostDiscoveryPublic(BaseModel):
    """Lightweight public host card for /hosts marketplace discovery."""

    host_id: UUID
    display_name: str
    username: str
    verified: bool
    legacy_tier: str
    legacy_status: str
    bio: str | None = None
    tagline: str | None = None
    avatar_url: str | None = None
    cover_url: str | None = None
    primary_city: str | None = None
    primary_category: str | None = None
    host_type: str | None = None
    upcoming_events_count: int = 0
    completed_events_count: int = 0
    verified_checkins_count: int = 0
    tickets_sold_count: int = 0
    average_rating: float | None = None
    review_count: int = 0
    followers_count: int = 0
    vault_items_count: int = 0
    sponsor_ready: bool = False
    next_upcoming_event: HostDiscoveryNextEvent | None = None
    share_path: str


class HostTierSummary(BaseModel):
    host_id: UUID
    display_name: str
    username: str
    composite_score: Decimal
    tier: LegacyTierPublic | None
    legacy_status: str
    updated_at: datetime


class RecalcAllResult(BaseModel):
    recalculated: int
