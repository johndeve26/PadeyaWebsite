"""Ambassadors API request/response schemas (phase 10)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AmbassadorJoinRequest(BaseModel):
    accept_terms: bool = False
    campaign_id: UUID | None = None
    event_id: UUID | None = None


class TrackClickRequest(BaseModel):
    ambassador_code: str = Field(min_length=2, max_length=64)
    campaign_id: UUID | None = None
    event_id: UUID | None = None
    merch_product_id: UUID | None = None
    session_id: str | None = Field(default=None, max_length=128)
    landing_url: str = Field(min_length=1, max_length=1000)
    referrer_url: str | None = Field(default=None, max_length=1000)
    visitor_fingerprint: str | None = Field(default=None, max_length=256)

    @field_validator("ambassador_code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().lower()


class TrackCheckoutStartedRequest(BaseModel):
    ambassador_code: str | None = Field(default=None, max_length=64)
    campaign_id: UUID | None = None
    event_id: UUID | None = None
    merch_product_id: UUID | None = None
    session_id: str | None = Field(default=None, max_length=128)
    source: str = Field(default="code", max_length=32)

    @field_validator("ambassador_code")
    @classmethod
    def normalize_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().lower()


class HostCampaignCreate(BaseModel):
    event_id: UUID | None = None
    merch_product_id: UUID | None = None
    name: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    campaign_type: str = "event"
    commission_type: str = "percentage"
    commission_value: Decimal | None = Field(default=None, ge=0)
    commission_percent: Decimal = Field(default=Decimal("5.00"), ge=0, le=100)
    applies_to: str | None = None
    hold_period_days: int = Field(default=7, ge=0, le=365)
    cookie_window_days: int = Field(default=30, ge=1, le=365)
    visibility: str = "public_open"
    status: str = "active"
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    payout_minimum: Decimal | None = Field(default=None, ge=0)
    max_commission_per_order: Decimal | None = Field(default=None, ge=0)
    allow_host_owner_commission: bool = False


class HostCampaignUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    commission_type: str | None = None
    commission_value: Decimal | None = Field(default=None, ge=0)
    commission_percent: Decimal | None = Field(default=None, ge=0, le=100)
    applies_to: str | None = None
    hold_period_days: int | None = Field(default=None, ge=0, le=365)
    cookie_window_days: int | None = Field(default=None, ge=1, le=365)
    visibility: str | None = None
    status: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    payout_minimum: Decimal | None = Field(default=None, ge=0)
    max_commission_per_order: Decimal | None = Field(default=None, ge=0)
    allow_host_owner_commission: bool | None = None


class ReverseConversionRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class BlockParticipantRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class EligibleEventPublic(BaseModel):
    id: UUID
    title: str
    slug: str
    city: str | None = None
    start_datetime: datetime
    banner_url: str | None = None
    host_display_name: str | None = None
    campaign_id: UUID
    campaign_type: str
    commission_type: str
    commission_value: Decimal
    visibility: str


class ProfilePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    status: str
    public_code_base: str | None = None
    terms_accepted_at: datetime | None = None
    created_at: datetime


class CampaignPublic(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    campaign_type: str
    status: str
    visibility: str
    commission_type: str
    commission_value: Decimal
    applies_to: str
    hold_period_days: int
    cookie_window_days: int
    event_id: UUID | None = None
    event_title: str | None = None
    event_slug: str | None = None
    merch_product_id: UUID | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    is_joinable: bool = False
    allow_host_owner_commission: bool = False
    created_at: datetime
    updated_at: datetime


class FraudFlagPublic(BaseModel):
    id: UUID
    flag_type: str
    campaign_id: UUID | None = None
    participant_id: UUID | None = None
    ambassador_code: str | None = None
    ip_hash: str | None = None
    click_count: int = 0
    window_start: datetime | None = None
    window_end: datetime | None = None
    status: str
    details: dict = Field(default_factory=dict)
    created_at: datetime


class ParticipantPublic(BaseModel):
    id: UUID
    campaign_id: UUID
    ambassador_profile_id: UUID
    user_id: UUID
    ambassador_code: str
    status: str
    joined_at: datetime
    campaign_name: str | None = None
    event_title: str | None = None
    event_slug: str | None = None


class AmbassadorLinkPublic(BaseModel):
    participant_id: UUID
    campaign_id: UUID
    ambassador_code: str
    event_id: UUID | None = None
    event_slug: str | None = None
    event_path: str | None = None
    merch_path: str | None = None
    share_url_path: str | None = None


class EarningsSummaryPublic(BaseModel):
    confirmed_conversions: int
    pending_amount: Decimal
    approved_amount: Decimal
    payable_amount: Decimal
    paid_amount: Decimal
    reversed_amount: Decimal
    gross_eligible: Decimal


class EventAmbassadorStatusPublic(BaseModel):
    event_id: UUID
    event_slug: str
    enabled: bool
    campaign_id: UUID | None = None
    campaign_type: str | None = None
    commission_type: str | None = None
    commission_value: Decimal | None = None
    joined: bool = False
    participant_id: UUID | None = None
    ambassador_code: str | None = None
    terms_version: str


class EventAmbassadorLinkPublic(BaseModel):
    event_id: UUID
    event_slug: str
    campaign_id: UUID
    participant_id: UUID
    ambassador_code: str
    event_path: str
    merch_path: str | None = None


class TrackResultPublic(BaseModel):
    ok: bool = True
    click_id: UUID | None = None
    attribution_id: UUID | None = None
    participant_id: UUID | None = None
    campaign_id: UUID | None = None
    expires_at: datetime | None = None


class HostParticipantRow(BaseModel):
    id: UUID
    campaign_id: UUID
    user_id: UUID
    ambassador_code: str
    status: str
    joined_at: datetime
    display_name: str | None = None
    clicks: int = 0
    total_clicks: int = 0
    unique_clicks: int = 0
    conversions: int = 0
    commission_amount: Decimal = Decimal("0")


class HostAnalyticsPublic(BaseModel):
    campaigns: int
    active_participants: int
    clicks: int
    total_clicks: int = 0
    unique_clicks: int = 0
    conversions: int
    commission_owed: Decimal
    commission_paid: Decimal


class PayoutPublic(BaseModel):
    id: UUID
    ambassador_profile_id: UUID
    user_id: UUID
    amount: Decimal
    status: str
    payout_method: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
    display_name: str | None = None


class ConversionAdminPublic(BaseModel):
    id: UUID
    campaign_id: UUID
    participant_id: UUID
    buyer_user_id: UUID | None = None
    order_id: UUID | None = None
    conversion_type: str
    gross_amount: Decimal
    eligible_amount: Decimal
    commission_amount: Decimal
    status: str
    dedupe_key: str
    verified_at: datetime | None = None
    refunded_at: datetime | None = None
    created_at: datetime
    ambassador_code: str | None = None
    campaign_name: str | None = None


class AdminAmbassadorRow(BaseModel):
    profile_id: UUID
    user_id: UUID
    status: str
    email: str | None = None
    full_name: str | None = None
    participants_active: int = 0
    created_at: datetime


class MessagePublic(BaseModel):
    message: str
