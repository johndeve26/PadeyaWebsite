"""Promo and ambassador schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PromoCodeCreate(BaseModel):
    code: str = Field(min_length=2, max_length=64)
    discount_type: str
    discount_value: Decimal = Field(gt=0)
    usage_limit: int | None = Field(default=None, ge=1)
    expires_at: datetime | None = None
    event_id: UUID | None = None
    ticket_type_id: UUID | None = None
    status: str = "active"
    max_per_user: int = Field(default=1, ge=1, le=50)

    @field_validator("discount_type")
    @classmethod
    def valid_type(cls, value: str) -> str:
        if value not in {"percentage", "fixed"}:
            raise ValueError("discount_type must be percentage or fixed")
        return value

    @field_validator("status")
    @classmethod
    def valid_status(cls, value: str) -> str:
        if value not in {"active", "inactive"}:
            raise ValueError("status must be active or inactive")
        return value

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()


class PromoCodeUpdate(BaseModel):
    discount_type: str | None = None
    discount_value: Decimal | None = Field(default=None, gt=0)
    usage_limit: int | None = Field(default=None, ge=1)
    expires_at: datetime | None = None
    event_id: UUID | None = None
    ticket_type_id: UUID | None = None
    status: str | None = None
    max_per_user: int | None = Field(default=None, ge=1, le=50)

    @field_validator("discount_type")
    @classmethod
    def valid_type(cls, value: str | None) -> str | None:
        if value is not None and value not in {"percentage", "fixed"}:
            raise ValueError("discount_type must be percentage or fixed")
        return value

    @field_validator("status")
    @classmethod
    def valid_status(cls, value: str | None) -> str | None:
        if value is not None and value not in {"active", "inactive"}:
            raise ValueError("status must be active or inactive")
        return value


class PromoCodePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    host_id: UUID
    code: str
    discount_type: str
    discount_value: Decimal
    usage_limit: int | None
    usage_count: int
    expires_at: datetime | None
    event_id: UUID | None
    ticket_type_id: UUID | None
    status: str
    max_per_user: int
    created_at: datetime


class PromoValidateRequest(BaseModel):
    code: str
    event_id: UUID
    items: list[dict] = Field(min_length=1)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()


class PromoValidateResponse(BaseModel):
    valid: bool
    code: str | None = None
    discount_amount: Decimal = Decimal("0")
    subtotal_amount: Decimal = Decimal("0")
    total_amount: Decimal = Decimal("0")
    reason: str | None = None


class AmbassadorCreate(BaseModel):
    referral_code: str = Field(min_length=2, max_length=64)
    display_name: str = Field(min_length=2, max_length=160)
    email: str | None = Field(default=None, max_length=320)
    user_email: str | None = Field(default=None, max_length=320)
    event_id: UUID | None = None
    commission_rate_percent: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    status: str = "active"

    @field_validator("referral_code")
    @classmethod
    def normalize_ref(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("status")
    @classmethod
    def valid_status(cls, value: str) -> str:
        if value not in {"active", "inactive"}:
            raise ValueError("status must be active or inactive")
        return value


class AmbassadorUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=2, max_length=160)
    email: str | None = None
    event_id: UUID | None = None
    commission_rate_percent: Decimal | None = Field(default=None, ge=0, le=100)
    status: str | None = None

    @field_validator("status")
    @classmethod
    def valid_status(cls, value: str | None) -> str | None:
        if value is not None and value not in {"active", "inactive"}:
            raise ValueError("status must be active or inactive")
        return value


class AmbassadorPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    host_id: UUID
    event_id: UUID | None = None
    campaign_id: UUID | None = None
    user_id: UUID | None
    program_kind: str = "host_curated"
    campaign_type: str | None = None
    campaign_type_label: str | None = None
    referral_code: str
    referral_code_display: str | None = None
    display_name: str
    email: str | None
    status: str
    commission_rate_percent: Decimal
    created_at: datetime
    event_title: str | None = None
    event_slug: str | None = None
    clicks: int = 0
    total_clicks: int = 0
    unique_clicks: int = 0
    qualified_clicks: int = 0
    tickets_sold: int = 0
    merch_units_sold: int = 0
    revenue_generated: Decimal = Decimal("0")
    conversion_rate: Decimal = Decimal("0")
    commission_owed: Decimal = Decimal("0")


class OpenAmbassadorCampaignOption(BaseModel):
    id: UUID
    campaign_type: str
    campaign_type_label: str
    commission_percent: Decimal
    commission_type: str = "percentage"
    commission_value: Decimal = Decimal("5.00")
    applies_to: str = "tickets"
    merch_included: bool
    is_live: bool = True


class OpenAmbassadorProgramPublic(BaseModel):
    event_id: UUID
    enabled: bool
    commission_percent: Decimal
    commission_type: str = "percentage"
    commission_value: Decimal = Decimal("5.00")
    event_slug: str | None = None
    event_title: str | None = None
    terms_version: str
    campaign_id: UUID | None = None
    campaign_type: str = "event_tickets"
    merch_included: bool = False
    campaigns: list[OpenAmbassadorCampaignOption] = Field(default_factory=list)


class OpenAmbassadorJoinRequest(BaseModel):
    """Join requires explicit acceptance of Ambassador terms."""

    accept_terms: bool = False
    campaign_type: str | None = None
    campaign_id: UUID | None = None


class ReferralClickRequest(BaseModel):
    referral_code: str
    event_id: UUID | None = None
    landing_path: str | None = Field(default=None, max_length=500)
    source: str | None = Field(
        default=None,
        max_length=32,
        description="event_page | merch_page | host_page | campaign_link",
    )
    anonymous_visitor_id: str | None = Field(default=None, max_length=64)

    @field_validator("referral_code")
    @classmethod
    def normalize_ref(cls, value: str) -> str:
        return value.strip().lower()


class AmbassadorSaleSelfPublic(BaseModel):
    """Ambassador self view — allowlisted metrics only (phase 13).

    Never includes order_id, order_reference, buyer PII, QRs, or venue/shipping.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ambassador_id: UUID
    tickets_sold: int
    merch_units_sold: int = 0
    revenue_amount: Decimal
    commission_owed: Decimal
    commission_type: str | None = None
    hold_until: datetime | None = None
    status: str
    created_at: datetime
    event_title: str | None = None


class AmbassadorSaleHostPublic(BaseModel):
    """Host ops view — may include order reference; still no buyer PII."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ambassador_id: UUID
    order_id: UUID | None = None
    event_id: UUID
    tickets_sold: int
    merch_units_sold: int = 0
    revenue_amount: Decimal
    commission_owed: Decimal
    commission_type: str | None = None
    hold_until: datetime | None = None
    status: str
    created_at: datetime
    event_title: str | None = None
    order_reference: str | None = None


# Back-compat alias for host detail; prefer AmbassadorSaleHostPublic.
AmbassadorSalePublic = AmbassadorSaleHostPublic


class AmbassadorSelfDashboard(BaseModel):
    ambassador: AmbassadorPublic
    sales: list[AmbassadorSaleSelfPublic]
    clicks: int
    tickets_sold: int
    merch_units_sold: int = 0
    revenue_generated: Decimal
    conversion_rate: Decimal
    commission_owed: Decimal


class AmbassadorHostDashboard(BaseModel):
    ambassador: AmbassadorPublic
    sales: list[AmbassadorSaleHostPublic]
    clicks: int
    tickets_sold: int
    merch_units_sold: int = 0
    revenue_generated: Decimal
    conversion_rate: Decimal
    commission_owed: Decimal


# Back-compat: host detail historically used AmbassadorDashboard.
AmbassadorDashboard = AmbassadorHostDashboard


class AmbassadorEnrollmentList(BaseModel):
    enrollments: list[AmbassadorSelfDashboard]


class EligibleAmbassadorEventPublic(BaseModel):
    id: UUID
    title: str
    slug: str
    city: str | None = None
    start_datetime: datetime
    banner_url: str | None = None
    host_display_name: str | None = None
    open_ambassador_commission_percent: Decimal
    open_ambassadors_enabled: bool = True


class AmbassadorEarningsSummary(BaseModel):
    clicks: int
    total_clicks: int = 0
    unique_clicks: int = 0
    tickets_sold: int
    merch_units_sold: int
    confirmed_sales: int
    revenue_generated: Decimal
    estimated_earnings: Decimal
    approved_earnings: Decimal
    payable_earnings: Decimal
    paid_earnings: Decimal
    payout_status: str
    payout_status_label: str
    enrollments_active: int


class AmbassadorCampaignCreate(BaseModel):
    event_id: UUID
    name: str = Field(default="Event Ambassadors", min_length=2, max_length=200)
    campaign_type: str = "event_tickets"
    commission_type: str = "percentage"
    # Prefer this; legacy clients may send commission_percent only.
    commission_value: Decimal | None = Field(default=None, ge=0)
    commission_percent: Decimal = Field(default=Decimal("5.00"), ge=0, le=100)
    applies_to: str | None = None
    hold_period_days: int = Field(default=7, ge=0, le=365)
    payout_minimum: Decimal | None = Field(default=None, ge=0)
    max_commission_per_order: Decimal | None = Field(default=None, ge=0)
    free_ticket_after_sales: int | None = Field(default=None, ge=1)
    leaderboard_reward_enabled: bool = False
    leaderboard_reward_description: str | None = Field(default=None, max_length=500)
    allow_host_owner_commission: bool = False
    # Ignored on write — derived from campaign_type. Kept for older clients.
    merch_included: bool | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    status: str = "public_open"


class AmbassadorCampaignUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    commission_type: str | None = None
    commission_value: Decimal | None = Field(default=None, ge=0)
    commission_percent: Decimal | None = Field(default=None, ge=0, le=100)
    applies_to: str | None = None
    hold_period_days: int | None = Field(default=None, ge=0, le=365)
    payout_minimum: Decimal | None = Field(default=None, ge=0)
    max_commission_per_order: Decimal | None = Field(default=None, ge=0)
    free_ticket_after_sales: int | None = Field(default=None, ge=1)
    leaderboard_reward_enabled: bool | None = None
    leaderboard_reward_description: str | None = Field(default=None, max_length=500)
    allow_host_owner_commission: bool | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    status: str | None = None


class AmbassadorCampaignPublic(BaseModel):
    id: UUID
    host_id: UUID
    event_id: UUID
    name: str
    status: str
    source: str = "host"
    created_by_user_id: UUID | None = None
    host_display_name: str | None = None
    campaign_type: str = "event_tickets"
    campaign_type_label: str = "Event Ambassador"
    commission_percent: Decimal
    commission_type: str = "percentage"
    commission_value: Decimal = Decimal("5.00")
    applies_to: str = "tickets"
    hold_period_days: int = 7
    payout_minimum: Decimal | None = None
    max_commission_per_order: Decimal | None = None
    free_ticket_after_sales: int | None = None
    leaderboard_reward_enabled: bool = False
    leaderboard_reward_description: str | None = None
    allow_host_owner_commission: bool = False
    merch_included: bool
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    event_title: str | None = None
    event_slug: str | None = None
    is_live: bool = False
    active_ambassadors: int = 0
    total_ambassadors: int = 0
    clicks: int = 0
    total_clicks: int = 0
    unique_clicks: int = 0
    confirmed_sales: int = 0
    tickets_sold: int = 0
    merch_units_sold: int = 0
    revenue_generated: Decimal = Decimal("0")
    conversion_rate: Decimal = Decimal("0")
    commission_owed: Decimal = Decimal("0")
    estimated_earnings: Decimal = Decimal("0")
    approved_earnings: Decimal = Decimal("0")
    payable_earnings: Decimal = Decimal("0")
    paid_earnings: Decimal = Decimal("0")


class AmbassadorPlatformSettingsPublic(BaseModel):
    enabled: bool
    updated_at: datetime | None = None
    updated_by_user_id: UUID | None = None


class AdminAmbassadorRow(BaseModel):
    id: UUID
    host_id: UUID
    event_id: UUID | None = None
    campaign_id: UUID | None = None
    user_id: UUID | None = None
    program_kind: str
    referral_code: str
    display_name: str
    email: str | None = None
    status: str
    commission_rate_percent: Decimal
    created_at: datetime
    event_title: str | None = None
    ambassadors_blocked: bool = False


class AmbassadorConversionAdmin(BaseModel):
    id: UUID
    ambassador_id: UUID
    # Host-facing responses omit order_id; admin oversight may include it.
    order_id: UUID | None = None
    event_id: UUID
    tickets_sold: int
    merch_units_sold: int = 0
    revenue_amount: Decimal
    eligible_sale_amount: Decimal | None = None
    commission_owed: Decimal
    commission_amount: Decimal | None = None
    commission_type: str | None = None
    hold_until: datetime | None = None
    status: str
    payout_status: str | None = None
    created_at: datetime
    reversed_at: datetime | None = None
    reversed_by_user_id: UUID | None = None
    reversal_reason: str | None = None
    rejection_reason: str | None = None
    payout_reference: str | None = None
    payout_note: str | None = None
    reward_status_updated_at: datetime | None = None
    event_title: str | None = None
    campaign_id: UUID | None = None
    campaign_name: str | None = None
    host_id: UUID | None = None
    ambassador_display_name: str | None = None
    ambassador_referral_code: str | None = None
    ambassador_user_id: UUID | None = None


class AmbassadorReportsSummary(BaseModel):
    feature_enabled: bool
    campaigns_total: int
    campaigns_live: int
    campaigns_paused: int
    campaigns_platform: int
    ambassadors_total: int
    ambassadors_active: int
    clicks: int
    total_clicks: int = 0
    unique_clicks: int = 0
    conversions_total: int
    conversions_active: int
    conversions_reversed: int
    revenue_generated: Decimal
    commission_owed: Decimal
    estimated_earnings: Decimal
    approved_earnings: Decimal
    payable_earnings: Decimal
    paid_earnings: Decimal


class CampaignLeaderboardRow(BaseModel):
    ambassador_id: UUID
    display_name: str
    referral_code: str
    status: str
    clicks: int
    confirmed_sales: int
    tickets_sold: int
    merch_units_sold: int
    revenue_generated: Decimal
    conversion_rate: Decimal
    commission_owed: Decimal
