"""Analytics request/response schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.analytics.taxonomy import (
    CONVERSION_STAGES,
    FORBIDDEN_CLIENT_METADATA_KEYS,
    TRACKED_ACTIONS,
    conversion_stage_for_action,
    normalize_tracked_action,
    require_known_tracked_action,
)
from app.core.config import get_settings


def _validate_metadata_size(meta: dict[str, Any] | None) -> dict[str, Any] | None:
    if meta is None:
        return None
    settings = get_settings()
    if len(meta) > settings.analytics_metadata_max_keys:
        raise ValueError(
            f"metadata exceeds max keys ({settings.analytics_metadata_max_keys})"
        )
    # Rough serialized size check without importing json repeatedly for tiny bags
    size = sum(len(str(k)) + len(str(v)) for k, v in meta.items())
    if size > settings.analytics_metadata_max_bytes:
        raise ValueError(
            f"metadata exceeds max size ({settings.analytics_metadata_max_bytes} bytes)"
        )
    # Strip forbidden revenue keys early (client path); trusted path re-adds server-side
    cleaned = {
        k: v
        for k, v in meta.items()
        if str(k).strip().lower() not in FORBIDDEN_CLIENT_METADATA_KEYS
    }
    return cleaned


class AnalyticsDimensions(BaseModel):
    """Shared dimension bag accepted on every track write.

    Privacy: never send raw IP, card data, or private venue addresses.
    Server may hash a client IP from the request edge — clients should not
    put IP in metadata.
    """

    anonymous_id: str | None = Field(default=None, max_length=64)
    request_id: str | None = Field(
        default=None,
        max_length=64,
        description="Idempotency key — duplicate request_id is ignored.",
    )
    idempotency_key: str | None = Field(
        default=None,
        max_length=64,
        description="Alias of request_id.",
    )
    occurred_at: datetime | None = None
    # UTM / attribution
    source: str | None = Field(default=None, max_length=120)
    medium: str | None = Field(default=None, max_length=120)
    campaign: str | None = Field(default=None, max_length=160)
    term: str | None = Field(default=None, max_length=160)
    content: str | None = Field(default=None, max_length=160)
    utm_source: str | None = Field(default=None, max_length=120)
    utm_medium: str | None = Field(default=None, max_length=120)
    utm_campaign: str | None = Field(default=None, max_length=160)
    utm_term: str | None = Field(default=None, max_length=160)
    utm_content: str | None = Field(default=None, max_length=160)
    referrer: str | None = Field(default=None, max_length=500)
    landing_page: str | None = Field(default=None, max_length=500)
    path: str | None = Field(
        default=None,
        max_length=500,
        description="Canonical path; mirrors current_path when omitted.",
    )
    current_path: str | None = Field(default=None, max_length=500)
    previous_path: str | None = Field(default=None, max_length=500)
    user_agent: str | None = Field(default=None, max_length=500)
    device_type: str | None = Field(default=None, max_length=32)
    browser: str | None = Field(default=None, max_length=64)
    os: str | None = Field(default=None, max_length=64)
    country: str | None = Field(default=None, max_length=64)
    city: str | None = Field(default=None, max_length=96)
    metadata: dict[str, Any] | None = None
    properties: dict[str, Any] | None = None
    is_bot: bool | None = None
    environment: str | None = Field(default=None, max_length=32)
    app_version: str | None = Field(default=None, max_length=64)
    build_version: str | None = Field(default=None, max_length=64)

    @field_validator("metadata", "properties", mode="before")
    @classmethod
    def _size_check_meta(cls, value: Any) -> Any:
        if value is None:
            return None
        if not isinstance(value, dict):
            raise ValueError("metadata must be an object")
        return _validate_metadata_size(value)

    @model_validator(mode="after")
    def coalesce_utm_and_keys(self) -> "AnalyticsDimensions":
        object.__setattr__(
            self,
            "source",
            self.source or self.utm_source,
        )
        object.__setattr__(self, "medium", self.medium or self.utm_medium)
        object.__setattr__(self, "campaign", self.campaign or self.utm_campaign)
        object.__setattr__(self, "term", self.term or self.utm_term)
        object.__setattr__(self, "content", self.content or self.utm_content)
        path_val = self.path or self.current_path
        object.__setattr__(self, "path", path_val)
        object.__setattr__(self, "current_path", self.current_path or path_val)
        rid = self.request_id or self.idempotency_key
        object.__setattr__(self, "request_id", rid)
        object.__setattr__(self, "idempotency_key", rid)
        ver = self.app_version or self.build_version
        object.__setattr__(self, "app_version", ver)
        object.__setattr__(self, "build_version", ver)
        return self


class TrackEventRequest(AnalyticsDimensions):
    """Generic analytics write.

    Prefer ``tracked_action`` / ``analytics_event_name`` / ``event_name`` + ``target_event_id``.
    """

    tracked_action: str | None = Field(default=None, min_length=2, max_length=64)
    analytics_event_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=64,
        description="Alias of tracked_action (preferred product wording).",
    )
    event_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=64,
        description="Canonical or legacy action name.",
    )
    target_event_id: UUID | None = Field(
        default=None,
        description="Product event this action relates to.",
    )
    event_listing_id: UUID | None = Field(
        default=None,
        description="Optional listing-card id; usually same as target_event_id.",
    )
    entity_type: str | None = Field(default=None, max_length=64)
    entity_id: UUID | None = None
    host_id: UUID | None = None
    session_id: str | None = Field(default=None, max_length=64)
    # When true, unknown actions are rejected. Unified /track forces true.
    require_known_action: bool = False

    @model_validator(mode="after")
    def resolve_action_and_target(self) -> "TrackEventRequest":
        raw = self.tracked_action or self.analytics_event_name or self.event_name
        if not raw:
            raise ValueError(
                "event_name (or tracked_action / analytics_event_name) is required"
            )
        if self.require_known_action:
            resolved = require_known_tracked_action(raw)
        else:
            resolved = normalize_tracked_action(raw) or raw.strip().lower()[:64]
        object.__setattr__(self, "tracked_action", resolved)
        object.__setattr__(self, "analytics_event_name", resolved)
        object.__setattr__(self, "event_name", resolved)

        target = self.target_event_id or self.event_listing_id or self.entity_id
        if target is not None:
            object.__setattr__(self, "target_event_id", target)
            if self.entity_id is None:
                object.__setattr__(self, "entity_id", target)
            if self.entity_type is None:
                object.__setattr__(self, "entity_type", "event")
        return self


# Alias used by unified POST /analytics/track docs
TrackRequest = TrackEventRequest


class TrackBatchRequest(BaseModel):
    events: list[TrackEventRequest] = Field(default_factory=list, min_length=1)

    @model_validator(mode="after")
    def cap_batch(self) -> "TrackBatchRequest":
        settings = get_settings()
        max_items = settings.analytics_track_batch_max_items
        if len(self.events) > max_items:
            raise ValueError(f"batch exceeds max items ({max_items})")
        return self


class TrackBatchItemResult(BaseModel):
    accepted: bool = True
    id: UUID | None = None
    tracked_action: str | None = None
    error: str | None = None
    index: int


class TrackBatchResponse(BaseModel):
    accepted_count: int
    rejected_count: int
    results: list[TrackBatchItemResult]

class TrackPageViewRequest(AnalyticsDimensions):
    path: str = Field(min_length=1, max_length=500)
    host_id: UUID | None = None
    target_event_id: UUID | None = None
    event_id: UUID | None = Field(
        default=None, description="Legacy alias of target_event_id"
    )
    session_id: str | None = Field(default=None, max_length=64)
    tracked_action: str | None = Field(
        default=None,
        max_length=64,
        description="Defaults to event_detail_view or event_list_view from path",
    )

    @model_validator(mode="after")
    def resolve_target(self) -> "TrackPageViewRequest":
        target = self.target_event_id or self.event_id
        object.__setattr__(self, "target_event_id", target)
        object.__setattr__(self, "event_id", target)
        action = normalize_tracked_action(
            self.tracked_action or "page_view", path=self.path
        )
        object.__setattr__(self, "tracked_action", action)
        if not self.current_path:
            object.__setattr__(self, "current_path", self.path)
        return self


class TrackImpressionRequest(AnalyticsDimensions):
    target_event_id: UUID | None = None
    event_id: UUID | None = Field(
        default=None, description="Legacy alias of target_event_id"
    )
    event_listing_id: UUID | None = None
    session_id: str | None = Field(default=None, max_length=64)
    tracked_action: str = Field(
        default="event_card_impression",
        max_length=64,
        description="Typically event_card_impression or featured_event_impression",
    )

    @model_validator(mode="after")
    def resolve_target(self) -> "TrackImpressionRequest":
        target = self.target_event_id or self.event_listing_id or self.event_id
        if target is None:
            raise ValueError("target_event_id is required")
        object.__setattr__(self, "target_event_id", target)
        object.__setattr__(self, "event_id", target)
        object.__setattr__(
            self,
            "tracked_action",
            require_known_tracked_action(self.tracked_action),
        )
        return self


class TrackClickRequest(AnalyticsDimensions):
    target_event_id: UUID | None = None
    event_id: UUID | None = Field(
        default=None, description="Legacy alias of target_event_id"
    )
    event_listing_id: UUID | None = None
    session_id: str | None = Field(default=None, max_length=64)
    click_target: str | None = Field(default=None, max_length=120)
    tracked_action: str = Field(
        default="event_card_click",
        max_length=64,
        description="Typically event_card_click or featured_event_click",
    )

    @model_validator(mode="after")
    def resolve_target(self) -> "TrackClickRequest":
        target = self.target_event_id or self.event_listing_id or self.event_id
        if target is None:
            raise ValueError("target_event_id is required")
        object.__setattr__(self, "target_event_id", target)
        object.__setattr__(self, "event_id", target)
        object.__setattr__(
            self,
            "tracked_action",
            require_known_tracked_action(self.tracked_action),
        )
        return self


class TrackConversionRequest(AnalyticsDimensions):
    tracked_action: str | None = Field(
        default=None,
        min_length=2,
        max_length=64,
        description="Preferred taxonomy action (e.g. payment_success)",
    )
    stage: str | None = Field(
        default=None,
        min_length=2,
        max_length=64,
        description="Legacy conversion stage; still accepted",
    )
    target_event_id: UUID | None = None
    event_id: UUID | None = Field(
        default=None, description="Legacy alias of target_event_id"
    )
    host_id: UUID | None = None
    session_id: str | None = Field(default=None, max_length=64)
    order_id: UUID | None = None
    amount: Decimal | None = None

    @model_validator(mode="after")
    def resolve_stage(self) -> "TrackConversionRequest":
        target = self.target_event_id or self.event_id
        object.__setattr__(self, "target_event_id", target)
        object.__setattr__(self, "event_id", target)

        raw = (self.tracked_action or self.stage or "").strip().lower()
        if not raw:
            raise ValueError("tracked_action or stage is required")

        # Legacy short stage passed as-is
        if raw in CONVERSION_STAGES and raw not in TRACKED_ACTIONS:
            object.__setattr__(self, "stage", raw)
            object.__setattr__(self, "tracked_action", raw)
            return self

        # Taxonomy action (or legacy alias) → conversion stage
        try:
            action = require_known_tracked_action(raw)
        except ValueError:
            # Already a taxonomy-length stage string in CONVERSION_STAGES
            if raw in CONVERSION_STAGES:
                object.__setattr__(self, "stage", raw)
                object.__setattr__(self, "tracked_action", raw)
                return self
            raise ValueError("Invalid conversion tracked_action/stage") from None

        stage = conversion_stage_for_action(action) or action
        if stage not in CONVERSION_STAGES:
            raise ValueError("Invalid conversion tracked_action/stage")
        object.__setattr__(self, "stage", stage)
        object.__setattr__(self, "tracked_action", action)
        return self


class TrackAccepted(BaseModel):
    accepted: bool = True
    id: UUID
    tracked_action: str | None = None


class SeriesPoint(BaseModel):
    date: str
    value: Decimal | float | int


class TicketTypeBreakdown(BaseModel):
    ticket_type_id: UUID | None = None
    name: str
    tickets_sold: int
    revenue: Decimal


class PromoPerfRow(BaseModel):
    promo_code_id: UUID
    code: str
    redemptions: int
    discount_total: Decimal
    orders: int


class AmbassadorPerfRow(BaseModel):
    ambassador_id: UUID
    name: str
    referral_code: str
    clicks: int
    tickets_sold: int
    revenue: Decimal
    conversion_rate: Decimal | None = None


class HostAnalyticsSummary(BaseModel):
    host_id: UUID
    range_start: datetime
    range_end: datetime
    tickets_sold: int
    revenue: Decimal
    check_ins: int
    no_shows: int
    page_views: int
    event_impressions: int
    event_clicks: int
    unique_impressions: int = 0
    unique_clicks: int = 0
    unique_detail_views: int = 0
    checkout_starts: int
    checkout_completes: int
    conversion_rate: Decimal | None
    repeat_buyers: int
    unique_buyers: int
    vault_earnings: Decimal
    ticket_type_breakdown: list[TicketTypeBreakdown]
    promo_performance: list[PromoPerfRow]
    ambassador_performance: list[AmbassadorPerfRow]
    sales_over_time: list[SeriesPoint]
    page_views_over_time: list[SeriesPoint]
    legacy_score_trend: list[SeriesPoint]


class EventAnalyticsSummary(BaseModel):
    event_id: UUID
    host_id: UUID
    title: str
    tickets_sold: int
    revenue: Decimal
    check_ins: int
    no_shows: int
    page_views: int
    impressions: int
    clicks: int
    unique_impressions: int = 0
    unique_clicks: int = 0
    unique_detail_views: int = 0
    checkout_starts: int
    checkout_completes: int
    conversion_rate: Decimal | None
    ticket_type_breakdown: list[TicketTypeBreakdown]
    sales_over_time: list[SeriesPoint]


class AdminPlatformSummary(BaseModel):
    range_start: datetime
    range_end: datetime
    total_users: int
    total_hosts: int
    total_events: int
    tickets_sold: int
    gross_revenue: Decimal
    platform_fees: Decimal
    refund_rate: Decimal | None
    refund_amount: Decimal
    payout_totals: Decimal
    vault_revenue: Decimal
    failed_payments: int
    support_volume: int
    fraud_signals: list[dict[str, Any]]
    top_events: list[dict[str, Any]]
    top_hosts: list[dict[str, Any]]
    category_trends: list[dict[str, Any]]
    city_trends: list[dict[str, Any]]
    sales_over_time: list[SeriesPoint]


class AdminRevenueSummary(BaseModel):
    gross_revenue: Decimal
    platform_fees: Decimal
    refund_amount: Decimal
    payout_totals: Decimal
    vault_revenue: Decimal
    net_after_refunds: Decimal
    sales_over_time: list[SeriesPoint]


class AdminEventsSummary(BaseModel):
    total_events: int
    by_status: list[dict[str, Any]]
    top_events: list[dict[str, Any]]
    category_trends: list[dict[str, Any]]
    city_trends: list[dict[str, Any]]


class AdminHostsSummary(BaseModel):
    total_hosts: int
    active_hosts: int
    top_hosts: list[dict[str, Any]]


class AdminSupportSummary(BaseModel):
    support_volume: int
    open_refund_requests: int
    escalated_refunds: int
    note: str
    fraud_signals: list[dict[str, Any]]
