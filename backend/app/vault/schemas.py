"""Vault request/response schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.vault.constants import (
    ACCESS_TYPES,
    CONTENT_TYPES,
    HOST_CREATE_STATUSES,
    HOST_UPDATE_STATUSES,
    LEGACY_ITEM_STATUS_MAP,
    MODERATION_ACTIONS,
    normalize_content_type,
)


class VaultMediaInput(BaseModel):
    url: str = Field(min_length=1, max_length=500)
    media_type: str = Field(min_length=2, max_length=64)
    label: str | None = None
    is_preview: bool = False
    sort_order: int = 0
    filename: str | None = None


class VaultAccessRuleInput(BaseModel):
    access_type: str
    price: Decimal | None = None
    currency: str | None = "NGN"
    required_event_id: UUID | None = None
    # Backward-compatible alias for required_event_id
    event_id: UUID | None = None
    required_ticket_type_id: UUID | None = None
    ticket_type_ids: list[UUID] | None = None
    require_check_in: bool = False
    required_legacy_tier: str | None = Field(default=None, max_length=64)
    access_code: str | None = Field(default=None, max_length=128)
    max_unlocks: int | None = Field(default=None, ge=1)
    starts_at: datetime | None = None
    ends_at: datetime | None = None

    @field_validator("access_type")
    @classmethod
    def valid_access(cls, value: str) -> str:
        if value not in ACCESS_TYPES:
            raise ValueError("Invalid access_type")
        return value

    @model_validator(mode="after")
    def normalize_event_id(self) -> "VaultAccessRuleInput":
        if self.required_event_id is None and self.event_id is not None:
            self.required_event_id = self.event_id
        if self.access_type == "invite_only" and not (self.access_code or "").strip():
            # Allow empty on draft saves; host should set a code before publish
            pass
        if (
            self.starts_at
            and self.ends_at
            and self.starts_at > self.ends_at
        ):
            raise ValueError("starts_at must be before ends_at")
        return self


class VaultInviteRedeemRequest(BaseModel):
    access_code: str = Field(min_length=1, max_length=128)


class VaultManualGrantRequest(BaseModel):
    user_id: UUID


def _normalize_tags(value: list[str] | None) -> list[str] | None:
    if value is None:
        return None
    cleaned: list[str] = []
    seen: set[str] = set()
    for raw in value:
        tag = " ".join(str(raw).strip().split())
        if not tag:
            continue
        key = tag.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(tag[:64])
        if len(cleaned) >= 20:
            break
    return cleaned


class VaultItemCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    slug: str | None = None
    content_type: str
    description: str | None = None
    preview_text: str | None = None
    body: str | None = None
    cover_url: str | None = None
    file_url: str | None = None
    external_url: str | None = None
    related_event_id: UUID | None = None
    related_memory_id: UUID | None = None
    tags: list[str] | None = None
    price: Decimal = Decimal("0")
    currency: str = "NGN"
    status: str = "draft"
    expires_at: datetime | None = None
    access: VaultAccessRuleInput
    media: list[VaultMediaInput] = []

    @field_validator("content_type")
    @classmethod
    def valid_content(cls, value: str) -> str:
        normalized = normalize_content_type(value)
        if normalized not in CONTENT_TYPES:
            raise ValueError("Invalid content_type")
        return normalized

    @field_validator("status")
    @classmethod
    def valid_status(cls, value: str) -> str:
        normalized = LEGACY_ITEM_STATUS_MAP.get(value, value)
        if normalized not in HOST_CREATE_STATUSES:
            raise ValueError("status must be draft, published, or scheduled")
        return normalized

    @field_validator("tags")
    @classmethod
    def valid_tags(cls, value: list[str] | None) -> list[str] | None:
        return _normalize_tags(value)

    @model_validator(mode="after")
    def type_specific_urls(self) -> "VaultItemCreate":
        if self.content_type == "external_link" and not (self.external_url or "").strip():
            raise ValueError("external_link items require external_url")
        if self.status == "scheduled":
            starts = self.access.starts_at if self.access else None
            if starts is None:
                raise ValueError("scheduled items require access.starts_at")
        return self


class VaultItemUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    slug: str | None = Field(default=None, min_length=2, max_length=220)
    content_type: str | None = None
    description: str | None = None
    preview_text: str | None = None
    body: str | None = None
    cover_url: str | None = None
    file_url: str | None = None
    external_url: str | None = None
    related_event_id: UUID | None = None
    related_memory_id: UUID | None = None
    tags: list[str] | None = None
    price: Decimal | None = None
    status: str | None = None
    expires_at: datetime | None = None
    access: VaultAccessRuleInput | None = None
    media: list[VaultMediaInput] | None = None

    @field_validator("content_type")
    @classmethod
    def valid_content(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = normalize_content_type(value)
        if normalized not in CONTENT_TYPES:
            raise ValueError("Invalid content_type")
        return normalized

    @field_validator("status")
    @classmethod
    def valid_status(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = LEGACY_ITEM_STATUS_MAP.get(value, value)
        if normalized not in HOST_UPDATE_STATUSES:
            raise ValueError(
                "Invalid status — use publish/unpublish/schedule/archive/restore actions"
            )
        return normalized

    @field_validator("tags")
    @classmethod
    def valid_tags(cls, value: list[str] | None) -> list[str] | None:
        return _normalize_tags(value)


class VaultMediaPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    media_type: str
    url: str | None
    label: str | None
    is_preview: bool
    sort_order: int
    locked: bool = False


class VaultAccessRulePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    access_type: str
    price: Decimal = Decimal("0")
    currency: str = "NGN"
    required_event_id: UUID | None = None
    event_id: UUID | None = None  # alias of required_event_id
    required_ticket_type_id: UUID | None = None
    ticket_type_ids: list | None = None
    require_check_in: bool = False
    required_legacy_tier: str | None = None
    access_code: str | None = None  # always null in API responses
    access_code_set: bool = False
    max_unlocks: int | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None


class VaultRelatedEventPublic(BaseModel):
    id: str
    title: str
    slug: str
    href: str


class VaultRelatedMemoryPublic(BaseModel):
    id: str
    event_id: str
    event_title: str
    event_slug: str
    host_username: str
    href: str


class VaultCatalogCard(BaseModel):
    """Public catalog row — preview fields only."""

    id: UUID
    host_username: str | None = None
    title: str
    slug: str
    preview_text: str | None = None
    cover_url: str | None = None
    content_type: str = "text_post"
    access_type: str
    locked: bool = True
    has_access: bool = False
    price: Decimal | None = None
    currency: str | None = None
    related_event: VaultRelatedEventPublic | None = None
    related_memory: VaultRelatedMemoryPublic | None = None
    share_path: str | None = None
    cta_label: str = "View"
    expired: bool = False
    featured: bool = False


class VaultItemPublic(BaseModel):
    id: UUID
    host_id: UUID
    host_username: str | None = None
    host_display_name: str | None = None
    title: str
    slug: str
    content_type: str
    status: str
    description: str | None = None
    preview_text: str | None
    body: str | None = None
    cover_url: str | None
    file_url: str | None = None
    external_url: str | None = None
    related_event_id: UUID | None = None
    related_memory_id: UUID | None = None
    related_event: VaultRelatedEventPublic | None = None
    related_memory: VaultRelatedMemoryPublic | None = None
    tags: list[str] = []
    price: Decimal
    currency: str
    moderation_status: str
    moderation_note: str | None = None
    moderated_at: datetime | None = None
    published_at: datetime | None
    expires_at: datetime | None = None
    archived_at: datetime | None = None
    created_at: datetime
    access: VaultAccessRulePublic | None = None
    media: list[VaultMediaPublic] = []
    has_access: bool = False
    access_reason: str | None = None
    lock_reason: str | None = None
    locked: bool = True
    expired: bool = False
    share_path: str | None = None
    cta_label: str | None = None

    @field_validator("status")
    @classmethod
    def normalize_status(cls, value: str) -> str:
        return LEGACY_ITEM_STATUS_MAP.get(value, value)


class VaultAdminItemPublic(VaultItemPublic):
    """Admin moderation row with unlock/purchase summary."""

    view_count: int = 0
    unlock_count: int = 0
    paid_purchase_count: int = 0
    grant_count: int = 0
    gross_revenue: Decimal = Decimal("0")
    report_count: int = 0
    access_type: str | None = None


class VaultPurchasePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    vault_item_id: UUID
    host_id: UUID
    amount: Decimal
    currency: str
    status: str
    payment_reference: str
    authorization_url: str | None
    access_code: str | None
    paid_at: datetime | None
    created_at: datetime
    item_title: str | None = None
    item_slug: str | None = None
    free_checkout: bool = False


class VaultCheckoutResponse(BaseModel):
    purchase: VaultPurchasePublic
    public_key: str | None = None


class VaultScheduleRequest(BaseModel):
    starts_at: datetime | None = None


class VaultModerateRequest(BaseModel):
    action: str
    note: str | None = None

    @field_validator("action")
    @classmethod
    def valid_action(cls, value: str) -> str:
        if value not in MODERATION_ACTIONS:
            raise ValueError(
                "Invalid moderation action — use flag, approve, hide, "
                "archive, remove, restore"
            )
        # disable is a legacy alias for hide
        return "hide" if value == "disable" else value


class VaultEarningsPublic(BaseModel):
    host_id: UUID
    currency: str = "NGN"
    gross_revenue: Decimal
    purchase_count: int
    paid_purchase_count: int
    view_count: int
    published_item_count: int


class VaultStudioItemPublic(VaultItemPublic):
    """Host studio row with performance stats."""

    view_count: int = 0
    unlock_count: int = 0
    earnings: Decimal = Decimal("0")
    is_access_gated: bool = False
    is_paid: bool = False
    is_ticket_gated: bool = False
    is_expired: bool = False
    is_archived: bool = False
    is_scheduled: bool = False
    is_hidden_by_admin: bool = False


class VaultStudioTopItem(BaseModel):
    id: UUID
    title: str
    slug: str
    cover_url: str | None = None
    view_count: int = 0
    unlock_count: int = 0
    earnings: Decimal = Decimal("0")
    access_type: str | None = None


class VaultStudioStats(BaseModel):
    total_items: int = 0
    published_items: int = 0
    locked_items: int = 0
    free_items: int = 0
    paid_unlocks: int = 0
    view_count: int = 0
    gross_revenue: Decimal = Decimal("0")
    draft_items: int = 0
    archived_items: int = 0
    expired_items: int = 0
    paid_items: int = 0
    ticket_holder_items: int = 0


class VaultStudioSummary(BaseModel):
    host_id: UUID
    host_username: str
    share_path: str
    earnings: VaultEarningsPublic
    stats: VaultStudioStats
    items: list[VaultStudioItemPublic]
    top_item: VaultStudioTopItem | None = None
    featured_vault_item_id: UUID | None = None
    legacy_vault_block_visible: bool = True


class VaultLibraryItemPublic(VaultItemPublic):
    """Buyer library row with fan-facing access label."""

    access_label: str = "Exclusive"
    library_group: str = "unlocked"


class VaultLibraryActivityPublic(BaseModel):
    id: str
    kind: str
    title: str
    detail: str | None = None
    at: datetime
    href: str | None = None
    access_label: str | None = None
    host_username: str | None = None


class VaultLibraryStats(BaseModel):
    unlocked_count: int = 0
    followed_count: int = 0
    ticket_count: int = 0
    unlockable_count: int = 0
    purchase_count: int = 0


class VaultLibrarySummary(BaseModel):
    unlocked: list[VaultLibraryItemPublic]
    followed_host_drops: list[VaultLibraryItemPublic]
    ticket_holder_content: list[VaultLibraryItemPublic]
    unlockable: list[VaultLibraryItemPublic]
    activity: list[VaultLibraryActivityPublic]
    purchases: list[VaultPurchasePublic]
    stats: VaultLibraryStats


class VaultSubscriptionCreate(BaseModel):
    host_id: UUID
    plan_label: str = Field(default="standard", max_length=80)
    price: Decimal = Field(default=Decimal("0.00"), ge=0)
    currency: str = Field(default="NGN", min_length=3, max_length=8)


class VaultSubscriptionPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    host_id: UUID
    buyer_user_id: UUID
    status: str
    plan_label: str
    price: Decimal
    currency: str
    started_at: datetime | None
    ends_at: datetime | None
    cancelled_at: datetime | None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime
