"""Pydantic schemas for detailed per-event analytics reports."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class EventAnalyticsFilterEcho(BaseModel):
    date_from: datetime
    date_to: datetime
    source: str | None = None
    medium: str | None = None
    campaign: str | None = None
    ticket_type_id: UUID | None = None
    device_type: str | None = None
    city: str | None = None
    include_bots: bool = False


class ConversionRates(BaseModel):
    impression_to_click: Decimal | None = None
    click_to_detail: Decimal | None = None
    detail_to_ticket_selection: Decimal | None = None
    ticket_selection_to_checkout: Decimal | None = None
    checkout_to_purchase: Decimal | None = None
    view_to_purchase: Decimal | None = None
    impression_to_purchase: Decimal | None = None


class EventAnalyticsOverview(BaseModel):
    event_id: UUID
    host_id: UUID
    title: str
    filters: EventAnalyticsFilterEcho
    impressions: int
    unique_impressions: int
    event_card_clicks: int
    event_detail_views: int
    unique_visitors: int
    ticket_selections: int
    checkout_starts: int
    purchases: int
    tickets_sold: int
    revenue: Decimal
    conversion_rates: ConversionRates
    average_order_value: Decimal | None = None
    refund_count: int = 0
    refund_rate: Decimal | None = None
    check_in_count: int = 0
    check_in_rate: Decimal | None = None
    review_count: int = 0
    average_rating: Decimal | None = None
    # Where funnel traffic counts came from (commerce still from orders/tickets).
    traffic_source: Literal["rollup", "live"] = "live"


class EventAnalyticsFunnel(BaseModel):
    event_id: UUID
    host_id: UUID
    filters: EventAnalyticsFilterEcho
    impressions: int
    card_clicks: int
    detail_views: int
    ticket_selections: int
    checkout_starts: int
    payment_starts: int
    purchases: int
    tickets_issued: int
    check_ins: int
    reviews: int
    dropoffs: dict[str, int] = Field(default_factory=dict)


class TimeseriesPoint(BaseModel):
    bucket: str
    impressions: int = 0
    views: int = 0
    checkout_starts: int = 0
    purchases: int = 0
    revenue: Decimal = Decimal("0.00")


class EventAnalyticsTimeseries(BaseModel):
    event_id: UUID
    host_id: UUID
    filters: EventAnalyticsFilterEcho
    granularity: Literal["hour", "day", "week"]
    points: list[TimeseriesPoint]


class SourceBreakdownRow(BaseModel):
    source_bucket: str
    impressions: int = 0
    clicks: int = 0
    detail_views: int = 0
    checkout_starts: int = 0
    purchases: int = 0
    revenue: Decimal = Decimal("0.00")


class UtmCampaignRow(BaseModel):
    source: str | None = None
    medium: str | None = None
    campaign: str | None = None
    impressions: int = 0
    clicks: int = 0
    detail_views: int = 0
    checkout_starts: int = 0
    purchases: int = 0


class EventAnalyticsSources(BaseModel):
    event_id: UUID
    host_id: UUID
    filters: EventAnalyticsFilterEcho
    buckets: list[SourceBreakdownRow]
    utm_campaigns: list[UtmCampaignRow]


class TicketTypeAnalyticsRow(BaseModel):
    ticket_type_id: UUID
    name: str
    price: Decimal = Decimal("0.00")
    impressions: int = 0
    selections: int = 0
    sold: int = 0
    revenue: Decimal = Decimal("0.00")
    conversion_rate: Decimal | None = None
    remaining_inventory: int = 0
    sell_through_rate: Decimal | None = None


class EventAnalyticsTickets(BaseModel):
    event_id: UUID
    host_id: UUID
    filters: EventAnalyticsFilterEcho
    ticket_types: list[TicketTypeAnalyticsRow]


class AudienceBucketRow(BaseModel):
    key: str
    visitors: int = 0
    detail_views: int = 0
    purchases: int = 0


class EventAnalyticsAudience(BaseModel):
    event_id: UUID
    host_id: UUID
    filters: EventAnalyticsFilterEcho
    new_vs_returning: list[AudienceBucketRow]
    auth_status: list[AudienceBucketRow]
    devices: list[AudienceBucketRow]
    cities: list[AudienceBucketRow]
    countries: list[AudienceBucketRow]
    browsers: list[AudienceBucketRow]
    follower_conversion: dict[str, Any] | None = None


class EventPromoAnalyticsRow(BaseModel):
    promo_code_id: UUID
    code: str
    redemptions: int
    discount_total: Decimal
    orders: int


class EventAmbassadorAnalyticsRow(BaseModel):
    ambassador_id: UUID
    name: str
    referral_code: str
    clicks: int
    tickets_sold: int
    revenue: Decimal
    commission_owed: Decimal = Decimal("0.00")
    conversion_rate: Decimal | None = None


class EventAnalyticsPromos(BaseModel):
    event_id: UUID
    host_id: UUID
    filters: EventAnalyticsFilterEcho
    promos: list[EventPromoAnalyticsRow]


class EventAnalyticsAmbassadors(BaseModel):
    event_id: UUID
    host_id: UUID
    filters: EventAnalyticsFilterEcho
    ambassadors: list[EventAmbassadorAnalyticsRow]


class AdminEventAnalyticsBundle(BaseModel):
    """Admin single-event bundle: overview + funnel + compact slices."""

    overview: EventAnalyticsOverview
    funnel: EventAnalyticsFunnel
    sources: EventAnalyticsSources
    tickets: EventAnalyticsTickets


class AdminEventLeaderboardRow(BaseModel):
    event_id: UUID
    host_id: UUID
    title: str
    host_display_name: str | None = None
    impressions: int = 0
    detail_views: int = 0
    checkout_starts: int = 0
    purchases: int = 0
    tickets_sold: int = 0
    revenue: Decimal = Decimal("0.00")
    conversion_rate: Decimal | None = None


class AdminEventLeaderboard(BaseModel):
    filters: EventAnalyticsFilterEcho
    sort_by: str
    events: list[AdminEventLeaderboardRow]


class AdminEventCompare(BaseModel):
    filters: EventAnalyticsFilterEcho
    events: list[EventAnalyticsOverview]


class AdminChannelBucket(BaseModel):
    source_bucket: str
    impressions: int = 0
    clicks: int = 0
    detail_views: int = 0
    checkout_starts: int = 0
    purchases: int = 0


class AdminChannelPerformance(BaseModel):
    filters: EventAnalyticsFilterEcho
    buckets: list[AdminChannelBucket]
