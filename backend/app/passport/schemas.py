"""Fan Passport request/response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.passport.privacy import ALLOWED_VISIBILITY, normalize_username


class FanBadgePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    name: str
    description: str
    criteria_key: str
    awarded_at: datetime | None = None
    earned: bool = False


class LoyaltyRecordPublic(BaseModel):
    host_id: UUID
    host_display_name: str
    host_username: str
    tickets_bought: int
    check_ins: int
    vip_purchases: int
    is_superfan: bool
    follows_host: bool


class PassportEventPublic(BaseModel):
    event_id: UUID
    title: str
    slug: str
    host_username: str | None
    start_datetime: datetime
    city: str | None
    ticket_status: str
    ticket_type_name: str
    checked_in: bool
    is_vip: bool


class PassportEventSafePublic(BaseModel):
    """Public Fan Passport event card — no ticket type, amounts, or venues."""

    event_id: UUID
    title: str
    slug: str
    host_username: str | None = None
    host_display_name: str | None = None
    start_datetime: datetime
    city: str | None = None
    checked_in: bool = True


class VaultSummaryPublic(BaseModel):
    paid_unlocks: int
    pending_unlocks: int
    unlocked_item_titles: list[str] = []


class VaultUnlockSafePublic(BaseModel):
    title: str
    host_username: str | None = None
    access_label: str = "Unlocked"


class PassportSettingsPublic(BaseModel):
    username: str | None = None
    display_name: str
    avatar_url: str | None = None
    tagline: str | None = None
    bio: str | None = None
    visibility: str = "public"
    appear_in_directory: bool = True
    show_attended_events: bool = True
    show_badges: bool = True
    show_followed_hosts: bool = True
    show_reviews: bool = True
    show_vault_unlocks: bool = True
    show_city_category_stats: bool = True
    hide_private_events_always: bool = True
    share_path: str | None = None


class PassportSettingsUpdate(BaseModel):
    username: str | None = None
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    avatar_url: str | None = Field(default=None, max_length=500)
    tagline: str | None = Field(default=None, max_length=200)
    bio: str | None = Field(default=None, max_length=2000)
    visibility: str | None = None
    appear_in_directory: bool | None = None
    show_attended_events: bool | None = None
    show_badges: bool | None = None
    show_followed_hosts: bool | None = None
    show_reviews: bool | None = None
    show_vault_unlocks: bool | None = None
    show_city_category_stats: bool | None = None
    hide_private_events_always: bool | None = None

    @field_validator("username")
    @classmethod
    def _username(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return normalize_username(v)

    @field_validator("visibility")
    @classmethod
    def _visibility(cls, v: str | None) -> str | None:
        if v is None:
            return None
        key = v.strip().lower()
        if key not in ALLOWED_VISIBILITY:
            raise ValueError("visibility must be private, unlisted, or public")
        return key


class FanPassportPublic(BaseModel):
    """Private dashboard Fan Passport payload."""

    id: UUID
    user_id: UUID
    display_name: str
    username: str | None = None
    avatar_url: str | None = None
    tagline: str | None = None
    bio: str | None = None
    visibility: str = "private"
    share_path: str | None = None
    tickets_bought: int
    events_attended: int
    hosts_followed: int
    vip_purchases: int
    vault_unlocks: int
    is_superfan: bool
    favorite_categories: list[str] | None
    favorite_cities: list[str] = []
    reviews_written: int = 0
    cities_explored: int = 0
    categories_explored: int = 0
    completion_score: int = 0
    badges_earned: list[FanBadgePublic]
    loyalty: list[LoyaltyRecordPublic]
    attended_events: list[PassportEventPublic]
    upcoming_tickets: list[PassportEventPublic]
    vip_history: list[PassportEventPublic]
    recent_checkins: list[PassportEventPublic] = []
    followed_hosts: list[dict]
    vault_summary: VaultSummaryPublic
    merch_proof_summaries: list[str] = []
    settings: PassportSettingsPublic
    created_at: datetime
    updated_at: datetime


class FanPassportPublicPage(BaseModel):
    """Public / unlisted Fan Passport page."""

    username: str
    user_id: UUID
    display_name: str
    avatar_url: str | None = None
    tagline: str | None = None
    bio: str | None = None
    visibility: str
    is_superfan: bool = False
    events_attended: int = 0
    hosts_followed: int = 0
    badges_earned_count: int = 0
    reviews_written: int = 0
    cities_explored: int = 0
    categories_explored: int = 0
    connections_count: int = 0
    favorite_categories: list[str] = []
    favorite_cities: list[str] = []
    badges: list[FanBadgePublic] = []
    attended_events: list[PassportEventSafePublic] = []
    followed_hosts: list[dict] = []
    reviews: list[dict] = []
    vault_unlocks: list[VaultUnlockSafePublic] = []
    merch_proof_summaries: list[str] = []
    share_path: str


class FanPassportActivityPublic(BaseModel):
    items: list[PassportEventSafePublic] = []


class FanReviewSafePublic(BaseModel):
    id: UUID
    rating: int
    body: str | None = None
    event_title: str | None = None
    host_username: str | None = None
    created_at: datetime


class FanDirectoryBadgeChip(BaseModel):
    slug: str
    name: str


class FanDirectoryCardPublic(BaseModel):
    """Strict public directory card — never includes email/order/payment data."""

    username: str
    user_id: UUID
    display_name: str
    avatar_url: str | None = None
    tagline: str | None = None
    city_label: str | None = None
    favorite_scene: str | None = None
    top_badges: list[FanDirectoryBadgeChip] = []
    events_attended: int = 0
    hosts_followed: int = 0
    reviews_written: int = 0
    cities_explored: int = 0
    connections_count: int = 0
    badges_earned_count: int = 0
    vault_unlocks_count: int = 0
    latest_badge_name: str | None = None
    is_superfan: bool = False
    share_path: str
    stats_limited: bool = False


class FanDirectoryListPublic(BaseModel):
    items: list[FanDirectoryCardPublic] = []
    page: int = 1
    limit: int = 24
    total: int = 0


class AdminFanRowPublic(BaseModel):
    user_id: str
    username: str | None = None
    display_name: str
    visibility: str
    appear_in_directory: bool
    admin_hidden: bool
    admin_hidden_at: datetime | None = None
    admin_hidden_reason: str | None = None
    user_active: bool
    share_path: str | None = None
    events_attended: int = 0


class AdminFanListPublic(BaseModel):
    items: list[AdminFanRowPublic] = []
    page: int = 1
    limit: int = 40
    total: int = 0


class AdminFanModerateBody(BaseModel):
    reason: str = Field(default="", max_length=500)


class AdminFanActionResult(BaseModel):
    user_id: str
    username: str | None = None
    admin_hidden: bool
    appear_in_directory: bool
    visibility: str
