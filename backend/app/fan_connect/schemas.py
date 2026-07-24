"""Fan Connect API schemas — privacy-safe public fields only."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FanConnectSettingsPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    fan_connect_enabled: bool
    discoverable_for_same_events: bool
    discoverable_for_similar_interests: bool
    allow_connection_requests: bool
    show_shared_hosts: bool
    show_shared_categories: bool
    show_shared_public_events: bool
    show_public_city: bool
    hide_private_events_always: bool
    request_policy: str
    request_policies: list[str]


class FanConnectSettingsUpdate(BaseModel):
    fan_connect_enabled: bool | None = None
    discoverable_for_same_events: bool | None = None
    discoverable_for_similar_interests: bool | None = None
    allow_connection_requests: bool | None = None
    show_shared_hosts: bool | None = None
    show_shared_categories: bool | None = None
    show_shared_public_events: bool | None = None
    show_public_city: bool | None = None
    request_policy: str | None = None
    request_policies: list[str] | None = None


class SharedEventChip(BaseModel):
    event_id: UUID
    title: str
    slug: str
    path: str
    city: str | None = None


class SharedHostChip(BaseModel):
    host_id: str
    display_name: str
    username: str | None = None


class SharedContextPublic(BaseModel):
    events: list[SharedEventChip] = []
    hosts: list[SharedHostChip] = []
    categories: list[str] = []


class CanConnectPublic(BaseModel):
    allowed: bool
    reasons: list[str] = []
    denials: list[str] = []
    message: str | None = None
    shared_context: SharedContextPublic
    connection_status: str | None = None
    connection_id: UUID | None = None
    thread_id: UUID | None = None
    relationship_status: str | None = None
    can_send_connect_request: bool | None = None
    cannot_connect_reason: str | None = None
    cooldown_until: datetime | None = None
    viewer_declined_target: bool | None = None
    target_declined_viewer: bool | None = None
    has_incoming_request: bool | None = None
    has_outgoing_request: bool | None = None


class DeclineRequestBody(BaseModel):
    cooldown_days: int | None = Field(
        default=None,
        ge=0,
        le=365,
        description="Optional requester cooldown; platform default when omitted.",
    )


class DeclineCooldownOptionsPublic(BaseModel):
    default_cooldown_days: int
    selectable_days: list[int]


class CreateRequestBody(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    message: str | None = Field(default=None, max_length=280)
    context_event_id: UUID | None = None


class ConnectionPublic(BaseModel):
    id: UUID
    status: str
    direction: str
    counterpart: dict
    message: str | None = None
    score: float = 0
    reasons: list[dict] = []
    shared_context: SharedContextPublic | None = None
    thread_id: UUID | None = None
    created_at: datetime
    requested_at: datetime | None = None
    accepted_at: datetime | None = None
    responded_at: datetime | None = None


class ConnectionListPublic(BaseModel):
    items: list[ConnectionPublic]


class BlockBody(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    reason: str | None = Field(default=None, max_length=300)


class ReportBody(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    reason: str = Field(min_length=3, max_length=120)
    details: str | None = Field(default=None, max_length=2000)
    connection_id: UUID | None = None
    thread_id: UUID | None = None


class ReportPublic(BaseModel):
    id: UUID
    status: str
    reason: str
    created_at: datetime


class SuggestionReasonPublic(BaseModel):
    code: str
    label: str


class SuggestionBadgePublic(BaseModel):
    slug: str
    name: str


class SuggestionPublic(BaseModel):
    """Privacy-safe suggestion card — never phone/email/venue/payment/private IDs/GPS."""

    user_id: UUID | None = None
    display_name: str
    username: str
    avatar_url: str | None = None
    tagline: str | None = None
    public_city: str | None = None
    badges: list[SuggestionBadgePublic] = []
    match_label: str | None = None
    recommendation_label: str | None = None  # alias of match_label
    score: int = 0
    score_band: str = "hidden"
    reasons: list[SuggestionReasonPublic] = []
    distance_label: str | None = None
    mutual_connection_count: int | None = None
    connection_status: str | None = None
    cta_state: str = "unavailable"
    cooldown_until: datetime | None = None
    viewer_declined_target: bool | None = None
    can_send_connect_request: bool | None = None
    shared_context: SharedContextPublic


class SuggestionsPublic(BaseModel):
    items: list[SuggestionPublic]
    page: int = 1
    limit: int = 12
    total: int = 0
    next_cursor: str | None = None
    mode: str = "mixed"
    empty_title: str | None = None
    empty_description: str | None = None


class DismissSuggestionBody(BaseModel):
    reason: str | None = Field(default=None, max_length=120)


class SuggestionActionPublic(BaseModel):
    ok: bool = True
    target_user_id: UUID
    expires_at: datetime | None = None


class LocationPreferenceBody(BaseModel):
    city: str | None = Field(default=None, max_length=120)
    area: str | None = Field(default=None, max_length=120)
    country: str | None = Field(default=None, max_length=120)
    latitude_approx: str | None = Field(default=None, max_length=32)
    longitude_approx: str | None = Field(default=None, max_length=32)
    precision: str = Field(default="city", max_length=32)


class LocationPreferencePublic(BaseModel):
    city: str | None = None
    area: str | None = None
    country: str | None = None
    precision: str = "city"
    latitude_approx: str | None = None
    longitude_approx: str | None = None
    consented_at: datetime | None = None
    updated_at: datetime | None = None


class AdminDebugScorePublic(BaseModel):
    actor_user_id: UUID
    target_user_id: UUID
    score: int
    score_band: str
    show: bool
    hard_exclusions: list[str] = Field(default_factory=list)
    breakdown: dict[str, int] = Field(default_factory=dict)
    reasons: list[SuggestionReasonPublic] = Field(default_factory=list)
    distance_label: str | None = None
    buckets: list[str] = Field(default_factory=list)
    connection_status: str | None = None
    eligible: bool = False


class AdminResolveReportBody(BaseModel):
    resolution: str = Field(pattern="^(resolved|dismissed)$")
    admin_notes: str | None = Field(default=None, max_length=2000)


class AdminConnectContextPublic(BaseModel):
    """Safe connection context for admins — never orders/payments/private venues."""

    connection_status: str | None = None
    reason_labels: list[str] = Field(default_factory=list)
    pair_blocked: bool = False


class AdminReportPublic(BaseModel):
    id: UUID
    status: str
    reason: str
    details: str | None = None
    admin_notes: str | None = None
    reporter_user_id: UUID
    reported_user_id: UUID
    reporter_display_name: str
    reported_display_name: str
    reporter_username: str | None = None
    reported_username: str | None = None
    reported_connect_enabled: bool = False
    connection_id: UUID | None = None
    thread_id: UUID | None = None
    thread_type: str | None = None
    message_report_id: UUID | None = None
    connection_context: AdminConnectContextPublic | None = None
    created_at: datetime
    updated_at: datetime | None = None


class AdminDisableUserBody(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class AdminDisableUserPublic(BaseModel):
    user_id: UUID
    fan_connect_enabled: bool
    allow_connection_requests: bool
    disabled: bool = True


class ConnectEventPublic(BaseModel):
    event_id: UUID
    title: str
    slug: str
    path: str
    city: str | None = None
    start_datetime: datetime | None = None
    suggestion_count: int = 0


class ConnectEventListPublic(BaseModel):
    items: list[ConnectEventPublic]


class AdminOverviewPublic(BaseModel):
    connect_enabled_users: int
    pending_requests: int
    accepted_connections: int
    blocked_connections: int
    fan_fan_threads: int
    fan_fan_reports: int
    message_blocks: int
    open_reports: int = 0


class AdminFanConnectSettingsPublic(BaseModel):
    decline_cooldown_days_default: int
    decline_cooldown_days_min: int
    decline_cooldown_days_max: int
    decline_cooldown_user_options: list[int]


class AdminFanConnectSettingsUpdate(BaseModel):
    decline_cooldown_days_default: int = Field(ge=0, le=365)


class AdminBlockItem(BaseModel):
    id: str
    blocker_user_id: str | None = None
    blocked_user_id: str | None = None
    blocker_display_name: str
    blocker_username: str | None = None
    blocked_display_name: str
    blocked_username: str | None = None
    reason: str | None = None
    created_at: datetime


class AdminBlockListPublic(BaseModel):
    items: list[AdminBlockItem]
    page: int = 1
    limit: int = 50
    total: int = 0


class AdminReportItem(BaseModel):
    id: str
    thread_id: str | None = None
    thread_type: str | None = None
    message_report_id: str | None = None
    reason: str
    details: str | None = None
    status: str
    reporter_user_id: str
    reported_user_id: str
    reporter_display_name: str
    reported_display_name: str
    reporter_username: str | None = None
    reported_username: str | None = None
    reported_connect_enabled: bool = False
    connection_context: AdminConnectContextPublic | None = None
    created_at: datetime
    # Never include full message bodies here — use message_report_id → /admin/message-reports
    message_preview: str | None = None


class AdminReportListPublic(BaseModel):
    items: list[AdminReportItem]
    page: int = 1
    limit: int = 50
    total: int = 0


class AdminUserModerationHistoryPublic(BaseModel):
    user_id: UUID
    display_name: str
    username: str | None = None
    fan_connect_enabled: bool
    reports_about: list[AdminReportItem] = Field(default_factory=list)
    reports_filed: list[AdminReportItem] = Field(default_factory=list)
    blocks_as_blocker: list[AdminBlockItem] = Field(default_factory=list)
    blocks_as_blocked: list[AdminBlockItem] = Field(default_factory=list)
