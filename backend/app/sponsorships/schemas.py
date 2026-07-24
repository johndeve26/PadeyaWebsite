"""Sponsorship marketplace schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.sponsorships.constants import INQUIRY_STATUSES, PLACEMENT_STATUSES, SLOT_TYPES


class HostSponsorshipSettingsPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    host_id: UUID
    accepting_sponsors: bool
    contact_email: str | None
    pitch: str | None
    audience_notes: str | None


class HostSponsorshipSettingsUpdate(BaseModel):
    accepting_sponsors: bool | None = None
    contact_email: str | None = Field(default=None, max_length=320)
    pitch: str | None = Field(default=None, max_length=4000)
    audience_notes: str | None = Field(default=None, max_length=4000)


class SponsorshipSlotCreate(BaseModel):
    slot_type: str
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(min_length=10, max_length=5000)
    price: Decimal = Field(ge=0)
    currency: str = Field(default="NGN", max_length=8)
    event_id: UUID | None = None
    status: str = "draft"

    @field_validator("slot_type")
    @classmethod
    def valid_slot_type(cls, value: str) -> str:
        if value not in SLOT_TYPES:
            raise ValueError("Invalid slot_type")
        return value


class SponsorshipSlotUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, min_length=10, max_length=5000)
    price: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, max_length=8)
    event_id: UUID | None = None
    status: str | None = None
    slot_type: str | None = None

    @field_validator("slot_type")
    @classmethod
    def valid_slot_type(cls, value: str | None) -> str | None:
        if value is not None and value not in SLOT_TYPES:
            raise ValueError("Invalid slot_type")
        return value


class SponsorshipSlotPublic(BaseModel):
    id: UUID
    host_id: UUID
    event_id: UUID | None
    slot_type: str
    slot_type_label: str
    title: str
    description: str
    price: Decimal
    currency: str
    status: str
    moderation_status: str
    host_display_name: str | None = None
    host_username: str | None = None
    host_verified: bool = False
    event_title: str | None = None
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SponsorshipInquiryCreate(BaseModel):
    company_name: str = Field(min_length=2, max_length=200)
    contact_name: str = Field(min_length=2, max_length=160)
    contact_email: str = Field(min_length=3, max_length=320)
    website: str | None = Field(default=None, max_length=255)
    message: str = Field(min_length=10, max_length=5000)
    proposed_budget: Decimal | None = Field(default=None, ge=0)
    campaign_id: UUID | None = None
    sponsor_id: UUID | None = None


class SponsorshipInquiryUpdate(BaseModel):
    status: str
    host_note: str | None = Field(default=None, max_length=2000)

    @field_validator("status")
    @classmethod
    def valid_status(cls, value: str) -> str:
        if value not in INQUIRY_STATUSES:
            raise ValueError("Invalid inquiry status")
        return value


class SponsorshipInquiryPublic(BaseModel):
    id: UUID
    slot_id: UUID
    sponsor_id: UUID | None
    campaign_id: UUID | None = None
    company_name: str
    contact_name: str
    contact_email: str
    website: str | None
    message: str
    proposed_budget: Decimal | None
    status: str
    host_note: str | None
    slot_title: str | None = None
    created_at: datetime
    updated_at: datetime


class SponsorshipPlacementCreate(BaseModel):
    slot_id: UUID
    sponsor_id: UUID
    inquiry_id: UUID | None = None
    status: str = "planned"
    asset_url: str | None = Field(default=None, max_length=500)
    starts_at: datetime | None = None
    ends_at: datetime | None = None

    @field_validator("status")
    @classmethod
    def valid_status(cls, value: str) -> str:
        if value not in PLACEMENT_STATUSES:
            raise ValueError("Invalid placement status")
        return value


class SponsorshipAnalyticsPublic(BaseModel):
    placement_id: UUID
    impressions: int
    clicks: int
    inquiries_attributed: int


class SponsorshipPlacementPublic(BaseModel):
    id: UUID
    slot_id: UUID
    sponsor_id: UUID
    inquiry_id: UUID | None
    status: str
    asset_url: str | None
    starts_at: datetime | None
    ends_at: datetime | None
    company_name: str | None = None
    slot_title: str | None = None
    analytics: SponsorshipAnalyticsPublic | None = None
    created_at: datetime


class SponsorshipModerateRequest(BaseModel):
    action: str = Field(pattern="^(flag|approve|disable|remove)$")
    note: str | None = Field(default=None, max_length=1000)


class SponsorHostPublic(BaseModel):
    host_id: UUID
    display_name: str
    username: str
    verified: bool
    city: str | None
    bio: str | None
    accepting_sponsors: bool
    pitch: str | None
    open_slots: int
