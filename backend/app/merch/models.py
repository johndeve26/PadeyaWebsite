"""SQLAlchemy models for event-linked merchandise.

Commerce stays on shared `orders` / `order_items` / `payments`.
Merch-specific pickup/shipping/POD state lives on `merch_fulfillments`
(not a parallel payments ledger). Snapshots keep historical names/prices
stable after host edits.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base


class MerchCategory(Base):
    """Admin-managed browse categories for the merch marketplace."""

    __tablename__ = "merch_categories"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MerchSizeChart(Base):
    __tablename__ = "merch_size_charts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    host_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("hosts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    product_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    units: Mapped[str] = mapped_column(String(16), nullable=False, default="cm")
    chart_json: Mapped[dict[str, Any] | list[Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict
    )
    fit_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class EventMerchProduct(Base):
    __tablename__ = "event_merch_products"
    __table_args__ = (
        UniqueConstraint("event_id", "slug", name="uq_event_merch_products_event_slug"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # Nullable when is_event_linked=false (host storefront evergreen).
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), nullable=True, index=True
    )
    host_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("hosts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    short_description: Mapped[str | None] = mapped_column(String(280), nullable=True)
    product_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    base_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="NGN")
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    image_media: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    gallery_urls: Mapped[list[Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", index=True)
    sales_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sales_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pickup_instructions: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pickup_location_label: Mapped[str | None] = mapped_column(String(160), nullable=True)
    pickup_time_window: Mapped[str | None] = mapped_column(String(160), nullable=True)
    fulfillment_notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    show_on_event_page: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_ticket: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    max_per_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_per_buyer: Mapped[int | None] = mapped_column(Integer, nullable=True)
    restock_on_refund: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    moderation_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="clear", index=True
    )
    moderation_note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    moderated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    moderated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Commerce expansion
    is_event_linked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    storefront_visibility: Mapped[str] = mapped_column(
        String(32), nullable=False, default="event_only", index=True
    )
    is_merch_only_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_vault_exclusive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    required_vault_item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("vault_items.id", ondelete="SET NULL"), nullable=True
    )
    required_access_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    is_sponsor_branded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sponsor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sponsors.id", ondelete="SET NULL"), nullable=True
    )
    sponsor_brand_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    sponsor_logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sponsor_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sponsor_split_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    sponsor_split_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    requires_check_in: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_vip: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_vault_access: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    related_fan_badge_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    post_event_drop_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    drop_live_notified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    pickup_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    shipping_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    print_on_demand_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    size_chart_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("merch_size_charts.id", ondelete="SET NULL"), nullable=True
    )
    low_stock_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=5)

    # Marketplace discovery (host required; event optional)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    tags: Mapped[list[Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    marketplace_kind: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    marketplace_listed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    variants: Mapped[list[EventMerchVariant]] = relationship(
        "EventMerchVariant",
        back_populates="product",
        cascade="all, delete-orphan",
    )


class MerchProductReport(Base):
    """Buyer reports (requested optional event_merch_reports)."""

    __tablename__ = "merch_product_reports"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("event_merch_products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reporter_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    reason: Mapped[str] = mapped_column(String(1000), nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open", index=True)
    admin_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolution_note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class EventMerchVariant(Base):
    __tablename__ = "event_merch_variants"
    __table_args__ = (
        UniqueConstraint("product_id", "label", name="uq_event_merch_variants_product_label"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("event_merch_products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    sku: Mapped[str | None] = mapped_column(String(80), nullable=True)
    size: Mapped[str | None] = mapped_column(String(40), nullable=True)
    color: Mapped[str | None] = mapped_column(String(40), nullable=True)
    option_1_name: Mapped[str | None] = mapped_column(String(40), nullable=True)
    option_1_value: Mapped[str | None] = mapped_column(String(80), nullable=True)
    option_2_name: Mapped[str | None] = mapped_column(String(40), nullable=True)
    option_2_value: Mapped[str | None] = mapped_column(String(80), nullable=True)
    price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    inventory_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reserved_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sold_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)
    low_stock_threshold: Mapped[int | None] = mapped_column(Integer, nullable=True)
    print_on_demand_variant_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    product: Mapped[EventMerchProduct] = relationship(
        "EventMerchProduct", back_populates="variants"
    )


class MerchBundle(Base):
    __tablename__ = "merch_bundles"
    __table_args__ = (
        UniqueConstraint("event_id", "slug", name="uq_merch_bundles_event_slug"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    host_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("hosts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    bundle_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="NGN")
    ticket_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ticket_types.id", ondelete="RESTRICT"), nullable=False
    )
    merch_variant_rules: Mapped[list[Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False, default=list
    )
    inventory_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quantity_reserved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quantity_sold: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_per_buyer: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sales_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sales_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MerchDiscountCode(Base):
    __tablename__ = "merch_discount_codes"
    __table_args__ = (
        UniqueConstraint("host_id", "code", name="uq_merch_discount_codes_host_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    host_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("hosts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), nullable=True, index=True
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    discount_type: Mapped[str] = mapped_column(String(32), nullable=False)
    discount_value: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    applies_to: Mapped[str] = mapped_column(String(40), nullable=False, default="merch_only")
    product_ids: Mapped[list[Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    min_order_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    usage_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    per_buyer_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    usage_count_paid: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MerchDiscountRedemption(Base):
    __tablename__ = "merch_discount_redemptions"
    __table_args__ = (
        UniqueConstraint("order_id", name="uq_merch_discount_redemptions_order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    discount_code_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("merch_discount_codes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    buyer_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class MerchShippingZone(Base):
    __tablename__ = "merch_shipping_zones"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    host_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("hosts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    country: Mapped[str] = mapped_column(String(80), nullable=False)
    state: Mapped[str | None] = mapped_column(String(80), nullable=True)
    city: Mapped[str | None] = mapped_column(String(80), nullable=True)
    flat_fee: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="NGN")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class MerchShippingAddress(Base):
    """Private order shipping — encrypted PII columns, never public/analytics."""

    __tablename__ = "merch_shipping_addresses"
    __table_args__ = (
        UniqueConstraint("order_id", name="uq_merch_shipping_addresses_order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    buyer_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recipient_name_enc: Mapped[str] = mapped_column(Text, nullable=False)
    phone_enc: Mapped[str] = mapped_column(Text, nullable=False)
    line1_enc: Mapped[str] = mapped_column(Text, nullable=False)
    line2_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str] = mapped_column(String(80), nullable=False)
    state: Mapped[str] = mapped_column(String(80), nullable=False)
    country: Mapped[str] = mapped_column(String(80), nullable=False)
    postal_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class MerchFulfillment(Base):
    """Merch pickup/shipping/POD projection for a polymorphic merch order_item (1:1)."""

    __tablename__ = "merch_fulfillments"
    __table_args__ = (
        UniqueConstraint("pickup_code", name="uq_merch_fulfillments_pickup_code"),
        UniqueConstraint("order_item_id", name="uq_merch_fulfillments_order_item"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("order_items.id", ondelete="CASCADE"), nullable=False
    )
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), nullable=True, index=True
    )
    host_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("hosts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    buyer_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    merch_variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("event_merch_variants.id", ondelete="RESTRICT"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="awaiting_pickup", index=True
    )
    fulfillment_method: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pickup"
    )
    pickup_code: Mapped[str] = mapped_column(String(40), nullable=False)
    pickup_qr_token_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    pickup_instructions_snapshot: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pickup_location_label_snapshot: Mapped[str | None] = mapped_column(String(160), nullable=True)
    pickup_time_window_snapshot: Mapped[str | None] = mapped_column(String(160), nullable=True)
    fulfillment_notes_snapshot: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    product_name_snapshot: Mapped[str] = mapped_column(String(160), nullable=False)
    variant_label_snapshot: Mapped[str] = mapped_column(String(120), nullable=False)
    shipping_address_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("merch_shipping_addresses.id", ondelete="SET NULL"), nullable=True
    )
    tracking_number: Mapped[str | None] = mapped_column(String(120), nullable=True)
    carrier: Mapped[str | None] = mapped_column(String(80), nullable=True)
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pod_job_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    bundle_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("merch_bundles.id", ondelete="SET NULL"), nullable=True
    )
    fulfilled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fulfilled_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class MerchFulfillmentEvent(Base):
    """Append-only desk timeline for a merch fulfillment row."""

    __tablename__ = "event_merch_fulfillment_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    merch_fulfillment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("merch_fulfillments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class MerchCart(Base):
    __tablename__ = "merch_carts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    buyer_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    anonymous_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("events.id", ondelete="SET NULL"), nullable=True
    )
    host_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("hosts.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"), nullable=True
    )
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    recovery_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    items: Mapped[list[MerchCartItem]] = relationship(
        "MerchCartItem",
        back_populates="cart",
        cascade="all, delete-orphan",
    )


class MerchCartItem(Base):
    __tablename__ = "merch_cart_items"
    __table_args__ = (
        UniqueConstraint("cart_id", "variant_id", name="uq_merch_cart_items_cart_variant"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    cart_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("merch_carts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("event_merch_products.id", ondelete="CASCADE"), nullable=False
    )
    variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("event_merch_variants.id", ondelete="CASCADE"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_snapshot: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    product_name_snapshot: Mapped[str] = mapped_column(String(160), nullable=False)
    variant_label_snapshot: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    cart: Mapped[MerchCart] = relationship("MerchCart", back_populates="items")


class MerchReview(Base):
    __tablename__ = "merch_reviews"
    __table_args__ = (UniqueConstraint("order_item_id", name="uq_merch_reviews_order_item"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("event_merch_products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("order_items.id", ondelete="CASCADE"), nullable=False
    )
    buyer_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    host_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("hosts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("events.id", ondelete="SET NULL"), nullable=True
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="published", index=True
    )
    host_reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    host_replied_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    admin_note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class MerchStockAlert(Base):
    __tablename__ = "merch_stock_alerts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    host_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("hosts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), nullable=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("event_merch_products.id", ondelete="CASCADE"), nullable=False
    )
    variant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("event_merch_variants.id", ondelete="CASCADE"), nullable=True
    )
    alert_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    threshold: Mapped[int | None] = mapped_column(Integer, nullable=True)
    available_snapshot: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open", index=True)
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class MerchRevenueSplit(Base):
    """Append-only revenue snapshot per paid merch line — never mutates amounts."""

    __tablename__ = "merch_revenue_splits"
    __table_args__ = (
        UniqueConstraint("order_item_id", name="uq_merch_revenue_splits_order_item"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("order_items.id", ondelete="CASCADE"), nullable=False
    )
    host_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("hosts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("events.id", ondelete="SET NULL"), nullable=True
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("event_merch_products.id", ondelete="SET NULL"), nullable=True
    )
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="NGN")
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    platform_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    host_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    sponsor_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    print_partner_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    fulfillment_method: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_sponsor_branded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    bundle_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("merch_bundles.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="payable")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class MerchPodIntegration(Base):
    __tablename__ = "merch_print_on_demand_integrations"
    __table_args__ = (
        UniqueConstraint(
            "host_id", "provider", name="uq_merch_pod_integrations_host_provider"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    host_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("hosts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(40), nullable=False, default="manual")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="disabled")
    provider_store_ref: Mapped[str | None] = mapped_column(String(160), nullable=True)
    credentials_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    sync_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class MerchPodJob(Base):
    __tablename__ = "merch_pod_jobs"
    __table_args__ = (UniqueConstraint("order_item_id", name="uq_merch_pod_jobs_order_item"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    order_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("order_items.id", ondelete="CASCADE"), nullable=False
    )
    merch_fulfillment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("merch_fulfillments.id", ondelete="SET NULL"), nullable=True
    )
    host_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("hosts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(40), nullable=False, default="manual")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    provider_ref: Mapped[str | None] = mapped_column(String(160), nullable=True)
    error_note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    manual_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    fulfilled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
