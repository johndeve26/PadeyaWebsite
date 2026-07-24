"""Pydantic schemas for event-linked merchandise."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

_SponsorModelT = TypeVar("_SponsorModelT", bound=BaseModel)

_SPONSOR_SPLIT_TYPES = frozenset({"percent", "fixed"})


def _validate_sponsor_fields(model: _SponsorModelT) -> _SponsorModelT:
    """Public brand fields + optional revenue split — never private sponsor contact."""
    branded = bool(getattr(model, "is_sponsor_branded", False))
    split_type = getattr(model, "sponsor_split_type", None)
    split_value = getattr(model, "sponsor_split_value", None)
    brand_name = getattr(model, "sponsor_brand_name", None)

    if split_type is not None:
        normalized = str(split_type).strip().lower() or None
        if normalized is not None and normalized not in _SPONSOR_SPLIT_TYPES:
            raise ValueError("sponsor_split_type must be percent or fixed")
        object.__setattr__(model, "sponsor_split_type", normalized)
        split_type = normalized

    if branded:
        name = (brand_name or "").strip() if brand_name else ""
        if not name:
            raise ValueError("sponsor_brand_name is required for sponsor-branded merch")
        object.__setattr__(model, "sponsor_brand_name", name)
        if split_type and split_value is None:
            raise ValueError("sponsor_split_value is required when sponsor_split_type is set")
        if split_type == "percent" and split_value is not None and split_value > 100:
            raise ValueError("sponsor_split_value percent cannot exceed 100")
    elif getattr(model, "is_sponsor_branded", None) is False:
        # Explicit off — clear brand presentation; split cleared with branding.
        object.__setattr__(model, "sponsor_brand_name", None)
        object.__setattr__(model, "sponsor_logo_url", None)
        object.__setattr__(model, "sponsor_description", None)
        object.__setattr__(model, "sponsor_split_type", None)
        object.__setattr__(model, "sponsor_split_value", None)
        object.__setattr__(model, "sponsor_id", None)

    return model


class MerchVariantCreate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=120)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    sku: str | None = Field(default=None, max_length=80)
    size: str | None = Field(default=None, max_length=40)
    color: str | None = Field(default=None, max_length=40)
    option_1_name: str | None = Field(default=None, max_length=40)
    option_1_value: str | None = Field(default=None, max_length=80)
    option_2_name: str | None = Field(default=None, max_length=40)
    option_2_value: str | None = Field(default=None, max_length=80)
    price: Decimal | None = Field(default=None, ge=0)
    price_override: Decimal | None = Field(default=None, ge=0)
    inventory_count: int = Field(default=0, ge=0)
    stock_quantity: int | None = Field(default=None, ge=0)
    status: str = Field(default="active", max_length=32)
    print_on_demand_variant_ref: str | None = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def require_label_or_name(self) -> MerchVariantCreate:
        if not (self.label or self.name):
            raise ValueError("label or name is required")
        return self


class MerchVariantUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=120)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    sku: str | None = Field(default=None, max_length=80)
    size: str | None = Field(default=None, max_length=40)
    color: str | None = Field(default=None, max_length=40)
    option_1_name: str | None = Field(default=None, max_length=40)
    option_1_value: str | None = Field(default=None, max_length=80)
    option_2_name: str | None = Field(default=None, max_length=40)
    option_2_value: str | None = Field(default=None, max_length=80)
    price: Decimal | None = Field(default=None, ge=0)
    price_override: Decimal | None = Field(default=None, ge=0)
    inventory_count: int | None = Field(default=None, ge=0)
    stock_quantity: int | None = Field(default=None, ge=0)
    status: str | None = Field(default=None, max_length=32)
    print_on_demand_variant_ref: str | None = Field(default=None, max_length=120)


class MerchVariantPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    label: str
    name: str | None = None
    sku: str | None = None
    size: str | None = None
    color: str | None = None
    option_1_name: str | None = None
    option_1_value: str | None = None
    option_2_name: str | None = None
    option_2_value: str | None = None
    price: Decimal | None = None
    price_override: Decimal | None = None
    effective_price: Decimal
    inventory_count: int
    stock_quantity: int | None = None
    reserved_quantity: int = 0
    sold_quantity: int = 0
    available_quantity: int | None = None
    status: str
    print_on_demand_variant_ref: str | None = None
    archived_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class MerchProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=4000)
    short_description: str | None = Field(default=None, max_length=280)
    product_type: str | None = Field(default=None, max_length=64)
    base_price: Decimal = Field(ge=0)
    currency: str = Field(default="NGN", max_length=8)
    image_url: str | None = Field(default=None, max_length=500)
    cover_image_url: str | None = Field(default=None, max_length=500)
    gallery_urls: list[str] = Field(default_factory=list, max_length=20)
    status: str = Field(default="draft", max_length=32)
    sales_start_at: datetime | None = None
    sales_end_at: datetime | None = None
    pickup_instructions: str | None = Field(default=None, max_length=500)
    pickup_location_label: str | None = Field(default=None, max_length=160)
    pickup_time_window: str | None = Field(default=None, max_length=160)
    fulfillment_notes: str | None = Field(default=None, max_length=1000)
    show_on_event_page: bool = True
    is_featured: bool = False
    requires_ticket: bool = False
    pickup_enabled: bool = True
    shipping_enabled: bool = False
    print_on_demand_enabled: bool = False
    max_per_order: int | None = Field(default=None, ge=1, le=50)
    max_per_buyer: int | None = Field(default=None, ge=1, le=100)
    restock_on_refund: bool = False
    size_chart_id: UUID | None = None
    is_sponsor_branded: bool = False
    sponsor_id: UUID | None = None
    sponsor_brand_name: str | None = Field(default=None, max_length=160)
    sponsor_logo_url: str | None = Field(default=None, max_length=500)
    sponsor_description: str | None = Field(default=None, max_length=500)
    sponsor_split_type: str | None = Field(default=None, max_length=16)
    sponsor_split_value: Decimal | None = Field(default=None, ge=0)
    is_vault_exclusive: bool = False
    requires_vault_access: bool = False
    required_vault_item_id: UUID | None = None
    required_access_type: str | None = Field(default=None, max_length=40)
    requires_check_in: bool = False
    storefront_visibility: str | None = Field(default=None, max_length=32)
    post_event_drop_at: datetime | None = None
    marketplace_kind: str | None = Field(default=None, max_length=40)
    category: str | None = Field(default=None, max_length=64)
    tags: list[str] = Field(default_factory=list, max_length=20)
    marketplace_listed: bool = True
    variants: list[MerchVariantCreate] = Field(default_factory=list, max_length=40)

    @model_validator(mode="after")
    def require_fulfillment_channel(self) -> MerchProductCreate:
        if (
            not self.pickup_enabled
            and not self.shipping_enabled
            and not self.print_on_demand_enabled
        ):
            raise ValueError("Enable pickup, shipping, and/or print on demand")
        return self

    @model_validator(mode="after")
    def validate_sponsor_branding(self) -> MerchProductCreate:
        return _validate_sponsor_fields(self)


class MerchProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=4000)
    short_description: str | None = Field(default=None, max_length=280)
    product_type: str | None = Field(default=None, max_length=64)
    base_price: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, max_length=8)
    image_url: str | None = Field(default=None, max_length=500)
    cover_image_url: str | None = Field(default=None, max_length=500)
    gallery_urls: list[str] | None = None
    status: str | None = Field(default=None, max_length=32)
    sales_start_at: datetime | None = None
    sales_end_at: datetime | None = None
    pickup_instructions: str | None = Field(default=None, max_length=500)
    pickup_location_label: str | None = Field(default=None, max_length=160)
    pickup_time_window: str | None = Field(default=None, max_length=160)
    fulfillment_notes: str | None = Field(default=None, max_length=1000)
    show_on_event_page: bool | None = None
    is_featured: bool | None = None
    requires_ticket: bool | None = None
    pickup_enabled: bool | None = None
    shipping_enabled: bool | None = None
    print_on_demand_enabled: bool | None = None
    max_per_order: int | None = Field(default=None, ge=1, le=50)
    max_per_buyer: int | None = Field(default=None, ge=1, le=100)
    restock_on_refund: bool | None = None
    size_chart_id: UUID | None = None
    is_sponsor_branded: bool | None = None
    sponsor_id: UUID | None = None
    sponsor_brand_name: str | None = Field(default=None, max_length=160)
    sponsor_logo_url: str | None = Field(default=None, max_length=500)
    sponsor_description: str | None = Field(default=None, max_length=500)
    sponsor_split_type: str | None = Field(default=None, max_length=16)
    sponsor_split_value: Decimal | None = Field(default=None, ge=0)
    is_vault_exclusive: bool | None = None
    requires_vault_access: bool | None = None
    required_vault_item_id: UUID | None = None
    required_access_type: str | None = Field(default=None, max_length=40)
    requires_check_in: bool | None = None
    storefront_visibility: str | None = Field(default=None, max_length=32)
    post_event_drop_at: datetime | None = None
    marketplace_kind: str | None = Field(default=None, max_length=40)
    category: str | None = Field(default=None, max_length=64)
    tags: list[str] | None = None
    marketplace_listed: bool | None = None

    @model_validator(mode="after")
    def validate_sponsor_branding(self) -> MerchProductUpdate:
        if (
            self.is_sponsor_branded is None
            and self.sponsor_split_type is None
            and self.sponsor_split_value is None
            and self.sponsor_brand_name is None
        ):
            return self
        return _validate_sponsor_fields(self)


class MerchProductPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID | None = None
    host_id: UUID
    name: str
    slug: str
    description: str | None = None
    short_description: str | None = None
    product_type: str | None = None
    base_price: Decimal
    currency: str
    image_url: str | None = None
    cover_image_url: str | None = None
    gallery_urls: list[str] = []
    status: str
    sales_start_at: datetime | None = None
    sales_end_at: datetime | None = None
    pickup_instructions: str | None = None
    pickup_location_label: str | None = None
    pickup_time_window: str | None = None
    fulfillment_notes: str | None = None
    show_on_event_page: bool = True
    is_featured: bool = False
    requires_ticket: bool = False
    pickup_enabled: bool = True
    shipping_enabled: bool = False
    print_on_demand_enabled: bool = False
    max_per_order: int | None = None
    max_per_buyer: int | None = None
    restock_on_refund: bool = False
    size_chart_id: UUID | None = None
    moderation_status: str = "clear"
    moderation_note: str | None = None
    moderated_at: datetime | None = None
    archived_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    variants: list[MerchVariantPublic] = []
    variant_count: int = 0
    total_inventory: int = 0
    sold_count: int = 0
    price_min: Decimal | None = None
    price_max: Decimal | None = None
    event_title: str | None = None
    is_sponsor_branded: bool = False
    sponsor_id: UUID | None = None
    sponsor_brand_name: str | None = None
    sponsor_logo_url: str | None = None
    sponsor_description: str | None = None
    sponsor_split_type: str | None = None
    sponsor_split_value: Decimal | None = None
    is_vault_exclusive: bool = False
    requires_vault_access: bool = False
    required_vault_item_id: UUID | None = None
    required_access_type: str | None = None
    requires_check_in: bool = False
    requires_vip: bool = False
    is_event_linked: bool = True
    is_post_event_drop: bool = False
    storefront_visibility: str = "event_only"
    post_event_drop_at: datetime | None = None
    marketplace_kind: str | None = None
    category: str | None = None
    tags: list[str] = []
    marketplace_listed: bool = True


class MerchAdminProductPublic(MerchProductPublic):
    host_name: str | None = None
    host_status: str | None = None
    event_status: str | None = None
    open_report_count: int = 0
    report_count: int = 0


class MerchModerateRequest(BaseModel):
    action: str = Field(pattern="^(flag|clear|hide|remove|archive|restore)$")
    note: str | None = Field(default=None, max_length=1000)


class MerchDeactivateUnsafeRequest(BaseModel):
    note: str | None = Field(default=None, max_length=1000)


class MerchAdminOrderPublic(BaseModel):
    """Admin merch order/fulfillment row — no payment amounts or gateway IDs."""

    id: UUID
    order_id: UUID
    order_reference: str | None = None
    order_status: str | None = None
    event_id: UUID
    event_title: str | None = None
    event_status: str | None = None
    host_id: UUID
    host_name: str | None = None
    host_status: str | None = None
    buyer_name: str | None = None
    product_name: str
    variant_label: str
    quantity: int
    status: str
    pickup_code: str
    fulfilled_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    is_issue: bool = False


class MerchReportCreate(BaseModel):
    reason: str = Field(min_length=8, max_length=1000)
    details: str | None = Field(default=None, max_length=4000)


class MerchReportResolve(BaseModel):
    resolution: str = Field(pattern="^(resolved|dismissed)$")
    note: str | None = Field(default=None, max_length=1000)
    admin_notes: str | None = Field(default=None, max_length=4000)
    moderate_action: str | None = Field(
        default=None, pattern="^(flag|clear|hide|remove|archive|restore)$"
    )


class MerchReportUpdate(BaseModel):
    status: str | None = Field(default=None, pattern="^(open|reviewing)$")
    admin_notes: str | None = Field(default=None, max_length=4000)


class MerchReportProductSnapshot(BaseModel):
    id: str
    name: str
    status: str
    moderation_status: str
    product_type: str | None = None
    base_price: str
    currency: str
    image_url: str | None = None
    short_description: str | None = None
    moderation_note: str | None = None


class MerchReportPublic(BaseModel):
    id: UUID
    product_id: UUID
    product_name: str | None = None
    product_status: str | None = None
    moderation_status: str | None = None
    product_snapshot: MerchReportProductSnapshot | None = None
    event_id: UUID | None = None
    event_title: str | None = None
    host_id: UUID | None = None
    host_name: str | None = None
    reporter_user_id: UUID
    reporter_name: str | None = None
    reason: str
    details: str | None = None
    status: str
    admin_notes: str | None = None
    resolved_at: datetime | None = None
    resolved_by_user_id: UUID | None = None
    resolved_by_name: str | None = None
    resolution_note: str | None = None
    created_at: datetime
    updated_at: datetime | None = None


class MerchCatalogProduct(BaseModel):
    """Public catalog row — locked Vault teasers omit variants/body secrets."""

    id: UUID
    event_id: UUID | None = None
    name: str
    slug: str
    description: str | None = None
    short_description: str | None = None
    product_type: str | None = None
    base_price: Decimal
    currency: str
    image_url: str | None = None
    cover_image_url: str | None = None
    gallery_urls: list[str] = []
    show_on_event_page: bool = True
    is_featured: bool = False
    requires_ticket: bool = False
    pickup_enabled: bool = True
    shipping_enabled: bool = False
    pickup_location_label: str | None = None
    pickup_time_window: str | None = None
    pickup_instructions: str | None = None
    max_per_order: int | None = None
    max_per_buyer: int | None = None
    is_sponsor_branded: bool = False
    sponsor_brand_name: str | None = None
    sponsor_logo_url: str | None = None
    sponsor_description: str | None = None
    is_vault_exclusive: bool = False
    requires_vault_access: bool = False
    requires_check_in: bool = False
    requires_vip: bool = False
    required_access_type: str | None = None
    required_vault_item_id: UUID | None = None
    is_event_linked: bool = True
    is_post_event_drop: bool = False
    post_event_drop_at: datetime | None = None
    storefront_visibility: str | None = None
    access_eligible: bool = True
    access_reason: str | None = None
    access_locked: bool = False
    teaser_only: bool = False
    access_label: str | None = None
    access_requirements: list[str] = []
    unlock_hint: str | None = None
    availability: str | None = None
    is_drop_live: bool = True
    variants: list[MerchVariantPublic] = []
    size_chart: dict[str, Any] | None = None


class MerchFulfillmentPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_id: UUID
    order_item_id: UUID
    event_id: UUID | None = None
    host_id: UUID
    buyer_user_id: UUID
    merch_variant_id: UUID
    quantity: int
    status: str
    fulfillment_method: str | None = "pickup"
    display_status: str | None = None
    pickup_code: str = ""
    pickup_instructions_snapshot: str | None = None
    pickup_location_label: str | None = None
    pickup_time_window: str | None = None
    fulfillment_notes: str | None = None
    product_name_snapshot: str
    variant_label_snapshot: str
    product_image_url: str | None = None
    tracking_number: str | None = None
    carrier: str | None = None
    shipped_at: datetime | None = None
    delivered_at: datetime | None = None
    bundle_id: UUID | None = None
    qr_token: str | None = None
    qr_typ: str | None = "padeya.merch.pickup"
    shipping_address: dict | None = None
    fulfilled_at: datetime | None = None
    fulfilled_by_user_id: UUID | None = None
    fulfilled_by_name: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
    event_title: str | None = None
    event_slug: str | None = None
    host_name: str | None = None
    host_slug: str | None = None
    order_reference: str | None = None
    order_status: str | None = None
    buyer_email: str | None = None
    buyer_name: str | None = None
    has_ticket: bool | None = None
    ticket_count: int | None = None


class MerchFulfillStatusUpdate(BaseModel):
    status: str = Field(
        pattern=(
            "^(awaiting_pickup|collect_at_stand|awaiting_shipment|packed|"
            "shipped|delivered|fulfilled|"
            "pending|ready_for_pickup|picked_up)$"
        )
    )


class MerchFulfillmentNoteCreate(BaseModel):
    note: str = Field(min_length=2, max_length=1000)


class MerchHostEventStats(BaseModel):
    event_id: UUID
    event_title: str
    sales_status: str
    currency: str = "NGN"
    total_merch_revenue: Decimal
    items_sold: int
    pending_pickup: int
    picked_up: int
    active_products: int
    sold_out_variants: int
    product_count: int
