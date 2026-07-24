"""Sponsor profile workspace Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.sponsor_profiles.constants import SPONSOR_TYPES


class SponsorCreateRequest(BaseModel):
    display_name: str = Field(min_length=2, max_length=200)
    sponsor_type: str = Field(default="brand")
    industry: str | None = Field(default=None, max_length=120)
    categories: list[str] = Field(default_factory=list)
    website_url: str | None = Field(default=None, max_length=255)
    short_bio: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=5000)
    logo_url: str | None = Field(default=None, max_length=500)
    cover_image_url: str | None = Field(default=None, max_length=500)
    target_locations: list[str] = Field(default_factory=list)
    campaign_goals: list[str] = Field(default_factory=list)
    budget_range: str | None = Field(default=None, max_length=64)
    contact_email: EmailStr | None = None
    contact_phone: str | None = Field(default=None, max_length=32)
    submit_for_review: bool = False

    @field_validator("sponsor_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in SPONSOR_TYPES:
            raise ValueError("Invalid sponsor_type")
        return v


class SponsorProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=2, max_length=200)
    sponsor_type: str | None = None
    industry: str | None = Field(default=None, max_length=120)
    categories: list[str] | None = None
    website_url: str | None = Field(default=None, max_length=255)
    short_bio: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=5000)
    logo_url: str | None = Field(default=None, max_length=500)
    cover_image_url: str | None = Field(default=None, max_length=500)
    target_locations: list[str] | None = None
    campaign_goals: list[str] | None = None
    budget_range: str | None = Field(default=None, max_length=64)
    contact_email: EmailStr | None = None
    contact_phone: str | None = Field(default=None, max_length=32)
    visibility: str | None = None
    submit_for_review: bool | None = None

    @field_validator("sponsor_type")
    @classmethod
    def validate_type(cls, v: str | None) -> str | None:
        if v is not None and v not in SPONSOR_TYPES:
            raise ValueError("Invalid sponsor_type")
        return v


class SponsorWorkspacePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sponsor_id: UUID
    display_name: str
    slug: str | None
    role: str
    is_owner: bool
    permissions: dict[str, bool]
    verification_status: str
    status: str
    onboarding_status: str


class SponsorPrivate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_user_id: UUID | None
    display_name: str
    slug: str | None
    sponsor_type: str | None
    logo_url: str | None
    cover_image_url: str | None
    short_bio: str | None
    description: str | None
    website_url: str | None
    industry: str | None
    categories: list[str] | None
    target_locations: list[str] | None
    budget_range: str | None
    campaign_goals: list[str] | None
    contact_email: str
    contact_phone: str | None
    verification_status: str
    status: str
    visibility: str
    onboarding_status: str
    sponsor_ready_score: int | None
    created_at: datetime
    updated_at: datetime


class SponsorPublicSummaryCard(BaseModel):
    label: str
    value: str


class SponsorPublicCampaignCard(BaseModel):
    id: UUID
    name: str
    objective: str
    objective_label: str
    status: str
    status_label: str
    target_categories: list[str]
    target_locations: list[str]
    description: str | None = None
    linked_sponsored_events_count: int = 0


class SponsorPublicSponsoredEvent(BaseModel):
    event_id: UUID | None = None
    event_title: str
    event_slug: str | None = None
    host_id: UUID
    host_slug: str | None = None
    host_display_name: str
    host_verified: bool = False
    category: str | None = None
    city: str | None = None
    area: str | None = None
    starts_at: datetime | None = None
    placement_status: str
    placement_status_label: str
    deliverable_labels: list[str] = Field(default_factory=list)


class SponsorPublicPartnerHost(BaseModel):
    host_id: UUID
    slug: str | None = None
    display_name: str
    city: str | None = None
    categories: list[str] = Field(default_factory=list)
    verified: bool = False
    sponsored_events_together: int = 0


class SponsorPublicRelatedSponsor(BaseModel):
    slug: str
    display_name: str
    industry: str | None = None
    logo_url: str | None = None
    categories: list[str] = Field(default_factory=list)


class SponsorPublicProfile(BaseModel):
    id: UUID
    display_name: str
    slug: str
    sponsor_type: str | None
    logo_url: str | None
    cover_image_url: str | None
    use_cover_fallback: bool = True
    short_bio: str | None
    description: str | None
    website_url: str | None
    industry: str | None
    categories: list[str]
    target_locations: list[str] = Field(default_factory=list)
    campaign_goals: list[str] = Field(default_factory=list)
    verification_status: str
    verified: bool
    show_contact_cta: bool
    accepting_inquiries: bool = False
    partnership_blurb: str | None = None
    summary_cards: list[SponsorPublicSummaryCard] = Field(default_factory=list)
    public_campaigns: list[SponsorPublicCampaignCard] = Field(default_factory=list)
    sponsored_events: list[SponsorPublicSponsoredEvent] = Field(default_factory=list)
    partnered_hosts: list[SponsorPublicPartnerHost] = Field(default_factory=list)
    related_sponsors: list[SponsorPublicRelatedSponsor] = Field(default_factory=list)


class SponsorDirectoryItem(BaseModel):
    id: UUID
    display_name: str
    slug: str
    sponsor_type: str | None
    logo_url: str | None
    use_logo_fallback: bool = True
    industry: str | None
    categories: list[str]
    short_bio: str | None
    verified: bool
    target_locations: list[str]
    accepting_inquiries: bool = False
    public_campaigns_count: int = 0
    sponsored_events_count: int = 0
    partnered_hosts_count: int = 0
    partnership_hint: str | None = None


class SponsorAdminListItem(BaseModel):
    id: UUID
    display_name: str
    slug: str | None
    sponsor_type: str | None
    owner_user_id: UUID | None
    verification_status: str
    status: str
    visibility: str
    onboarding_status: str
    created_at: datetime


class SponsorAdminDetail(SponsorPrivate):
    internal_notes: str | None
    owner_email: str | None


class SponsorAdminVerifyRequest(BaseModel):
    action: str = Field(description="approve | reject")
    notes: str | None = Field(default=None, max_length=2000)


class SponsorAdminStatusRequest(BaseModel):
    status: str
    notes: str | None = Field(default=None, max_length=2000)


class SponsorAdminNotesUpdate(BaseModel):
    internal_notes: str | None = Field(default=None, max_length=10000)


class SponsorInquiryOwnPublic(BaseModel):
    id: UUID
    slot_id: UUID
    campaign_id: UUID | None = None
    slot_title: str | None
    host_display_name: str | None
    status: str
    message: str
    created_at: datetime
    updated_at: datetime
