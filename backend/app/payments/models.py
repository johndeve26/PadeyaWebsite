"""Order and payment ORM models."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

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
from sqlalchemy.types import JSON, Uuid

from app.core.database import Base

if TYPE_CHECKING:
    from app.tickets.models import Ticket


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    reference: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    buyer_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    # Nullable for host-shop / standalone merch-only orders (no event).
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    host_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("hosts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(8), default="NGN", nullable=False)
    subtotal_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), nullable=False
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    promo_code_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("promo_codes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    promo_code_snapshot: Mapped[str | None] = mapped_column(String(64), nullable=True)
    merch_discount_code_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("merch_discount_codes.id", ondelete="SET NULL"),
        nullable=True,
    )
    merch_discount_code_snapshot: Mapped[str | None] = mapped_column(String(64), nullable=True)
    merch_discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), nullable=False
    )
    shipping_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), nullable=False
    )
    # Fee summary (major units). Snapshots in order_fee_snapshots are source of detail.
    buyer_fee_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), nullable=False
    )
    host_fee_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), nullable=False
    )
    processing_fee_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), nullable=False
    )
    platform_revenue_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), nullable=False
    )
    host_net_estimate: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), nullable=False
    )
    shipping_address_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True
    )
    fulfillment_method: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ambassador_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ambassadors.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Domain Ambassadors (phase 11) — set at checkout; commission only after paid webhook
    ambassador_participant_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ambassador_participants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    ambassador_attribution_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ambassador_attributions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    referral_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Platform-wide fallback code (event-scoped code still preferred per item)
    platform_referral_code: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    # explicit | link | cookie — explicit checkout code is never overwritten
    referral_attribution_source: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )
    buyer_email: Mapped[str] = mapped_column(String(320), nullable=False)
    buyer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    # Guest checkout (nullable buyer_user_id) — never auto-create accounts
    is_guest_checkout: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    guest_buyer_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    guest_buyer_email: Mapped[str | None] = mapped_column(String(320), nullable=True, index=True)
    guest_buyer_phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    claim_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    claim_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Pending inventory hold TTL — release reserved seats/stock after this instant.
    reservation_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    claimed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # self | other | group — who the tickets are assigned to
    purchase_mode: Mapped[str] = mapped_column(
        String(16), default="self", nullable=False
    )
    is_gift: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    purchased_for_someone_else: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    gift_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    send_ticket_to_recipient: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    keep_buyer_copy: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    recipient_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    recipient_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    recipient_phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # Never set from email alone — only explicit verified linking rules
    recipient_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
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
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    items: Mapped[list[OrderItem]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
    )
    payments: Mapped[list[Payment]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
    )
    tickets: Mapped[list[Ticket]] = relationship(back_populates="order")
    checkout_answers: Mapped[list[OrderCheckoutAnswer]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
    )
    attendees: Mapped[list[OrderAttendee]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
    )


class OrderAttendee(Base):
    """Per-ticket attendee assignment captured at checkout (immutable after create)."""

    __tablename__ = "order_attendees"
    __table_args__ = (
        UniqueConstraint(
            "order_id",
            "ticket_type_id",
            "unit_index",
            name="uq_order_attendees_order_type_unit",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ticket_type_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ticket_types.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    unit_index: Mapped[int] = mapped_column(Integer, nullable=False)
    attendee_name: Mapped[str] = mapped_column(String(200), nullable=False)
    attendee_email: Mapped[str] = mapped_column(String(320), nullable=False)
    attendee_phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    delivery_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    delivery_phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # Never claim an account by email alone
    recipient_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    order: Mapped[Order] = relationship(back_populates="attendees")


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_kind: Mapped[str] = mapped_column(
        String(16), default="ticket", nullable=False, index=True
    )
    ticket_type_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ticket_types.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    merch_product_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("event_merch_products.id", ondelete="RESTRICT"),
        nullable=True,
    )
    merch_variant_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("event_merch_variants.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    bundle_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("merch_bundles.id", ondelete="SET NULL"),
        nullable=True,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    ticket_type_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    product_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    variant_label: Mapped[str | None] = mapped_column(String(120), nullable=True)

    order: Mapped[Order] = relationship(back_populates="items")


class OrderCheckoutAnswer(Base):
    """Snapshot of a checkout question answer at purchase time (immutable)."""

    __tablename__ = "order_checkout_answers"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("event_checkout_questions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    question_label: Mapped[str] = mapped_column(String(255), nullable=False)
    question_type: Mapped[str] = mapped_column(String(32), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    order: Mapped[Order] = relationship(back_populates="checkout_answers")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(32), default="paystack", nullable=False)
    reference: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="NGN", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    provider_payment_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    authorization_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    access_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    raw_response: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
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
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    order: Mapped[Order] = relationship(back_populates="payments")


class PaymentWebhookEvent(Base):
    __tablename__ = "payment_webhook_events"
    __table_args__ = (
        UniqueConstraint("provider", "event_key", name="uq_payment_webhook_events_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    provider: Mapped[str] = mapped_column(String(32), default="paystack", nullable=False)
    event_key: Mapped[str] = mapped_column(String(191), nullable=False, index=True)
    reference: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    event_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False
    )
    processing_status: Mapped[str] = mapped_column(
        String(32), default="received", nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
