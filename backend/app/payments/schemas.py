"""Payment and order schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ShippingAddressIn(BaseModel):
    """Private shipping — stored encrypted; never echoed in public analytics."""

    recipient_name: str = Field(min_length=1, max_length=200)
    phone: str = Field(min_length=7, max_length=40)
    line1: str = Field(min_length=1, max_length=300)
    line2: str | None = Field(default=None, max_length=300)
    city: str = Field(min_length=1, max_length=80)
    state: str = Field(min_length=1, max_length=80)
    country: str = Field(min_length=1, max_length=80)
    postal_code: str | None = Field(default=None, max_length=32)
    notes: str | None = Field(default=None, max_length=500)

    @model_validator(mode="before")
    @classmethod
    def map_checkout_aliases(cls, data: object) -> object:
        """Accept FE-friendly names and map to stored field names."""
        if not isinstance(data, dict):
            return data
        out = dict(data)
        if not out.get("phone") and out.get("phone_number"):
            out["phone"] = out["phone_number"]
        if not out.get("line1") and out.get("address_line_1"):
            out["line1"] = out["address_line_1"]
        if out.get("line2") is None and out.get("address_line_2") is not None:
            out["line2"] = out["address_line_2"]
        if out.get("notes") is None and out.get("delivery_notes") is not None:
            out["notes"] = out["delivery_notes"]
        return out


class OrderItemCreate(BaseModel):
    item_kind: Literal["ticket", "merch", "bundle"] | None = None
    ticket_type_id: UUID | None = None
    merch_variant_id: UUID | None = None
    bundle_id: UUID | None = None
    quantity: int = Field(ge=1, le=50)

    @model_validator(mode="before")
    @classmethod
    def infer_item_kind(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        kind = data.get("item_kind")
        if kind:
            return data
        if data.get("bundle_id"):
            data["item_kind"] = "bundle"
        elif data.get("merch_variant_id") and not data.get("ticket_type_id"):
            data["item_kind"] = "merch"
        else:
            data["item_kind"] = "ticket"
        return data

    @model_validator(mode="after")
    def validate_kind_ids(self) -> "OrderItemCreate":
        kind = self.item_kind or "ticket"
        object.__setattr__(self, "item_kind", kind)
        if kind == "ticket":
            if self.ticket_type_id is None:
                raise ValueError("ticket_type_id is required for ticket items")
            if self.merch_variant_id is not None:
                raise ValueError("merch_variant_id must be omitted for ticket items")
            if self.bundle_id is not None:
                raise ValueError("bundle_id must be omitted for ticket items")
        elif kind == "merch":
            if self.merch_variant_id is None:
                raise ValueError("merch_variant_id is required for merch items")
            if self.ticket_type_id is not None:
                raise ValueError("ticket_type_id must be omitted for merch items")
            if self.bundle_id is not None:
                raise ValueError("bundle_id must be omitted for merch items")
        elif kind == "bundle":
            if self.bundle_id is None:
                raise ValueError("bundle_id is required for bundle items")
            if self.ticket_type_id is not None or self.merch_variant_id is not None:
                raise ValueError("bundle items expand server-side — omit ticket/merch ids")
        return self


class CheckoutAnswerIn(BaseModel):
    question_id: UUID
    value: str | list[str] = ""


class AttendeeAssignmentIn(BaseModel):
    """One attendee per purchased ticket unit (group mode)."""

    ticket_type_id: UUID
    unit_index: int = Field(ge=0, le=49)
    attendee_name: str = Field(min_length=2, max_length=200)
    attendee_email: str = Field(min_length=3, max_length=320)
    attendee_phone: str | None = Field(default=None, max_length=40)
    delivery_email: str | None = Field(default=None, max_length=320)
    delivery_phone: str | None = Field(default=None, max_length=40)


class OrderCreate(BaseModel):
    event_id: UUID | None = None
    host_id: UUID | None = None
    items: list[OrderItemCreate] = Field(min_length=1)
    promo_code: str | None = Field(default=None, max_length=64)
    merch_discount_code: str | None = Field(default=None, max_length=64)
    referral_code: str | None = Field(default=None, max_length=64)
    # Platform-wide fallback (host event campaign still wins per item when present)
    platform_referral_code: str | None = Field(default=None, max_length=64)
    # explicit | link | cookie — explicit checkout entry wins over cookie/link
    referral_source: Literal["explicit", "link", "cookie"] | None = None
    # Optional domain attribution from track-click / track-checkout-started
    ambassador_attribution_id: UUID | None = None
    referral_session_id: str | None = Field(default=None, max_length=128)
    fulfillment_method: Literal["pickup", "shipping"] | None = None
    shipping_address: ShippingAddressIn | None = None
    checkout_answers: list[CheckoutAnswerIn] | None = None
    # Purchase mode: self (default), other (gift), group (per-ticket attendees)
    purchase_mode: Literal["self", "other", "group"] = "self"
    attendee_name: str | None = Field(default=None, max_length=200)
    attendee_email: str | None = Field(default=None, max_length=320)
    attendee_phone: str | None = Field(default=None, max_length=40)
    recipient_name: str | None = Field(default=None, max_length=200)
    recipient_email: str | None = Field(default=None, max_length=320)
    recipient_phone: str | None = Field(default=None, max_length=40)
    gift_message: str | None = Field(default=None, max_length=1000)
    send_ticket_to_recipient: bool = False
    keep_buyer_copy: bool | None = None
    use_same_buyer_details_for_all: bool = False
    attendees: list[AttendeeAssignmentIn] | None = None
    # Guest checkout (required when not authenticated)
    guest_buyer_name: str | None = Field(default=None, max_length=200)
    guest_buyer_email: str | None = Field(default=None, max_length=320)
    guest_buyer_phone: str | None = Field(default=None, max_length=40)

    @model_validator(mode="after")
    def require_event_or_host(self) -> OrderCreate:
        if self.event_id is None and self.host_id is None:
            raise ValueError("event_id or host_id is required")
        return self


class OrderClaimRequest(BaseModel):
    token: str = Field(min_length=10, max_length=200)


class OrderClaimStart(BaseModel):
    """Re-send claim link to the guest buyer email (must match order)."""

    order_reference: str = Field(min_length=4, max_length=64)
    email: str = Field(min_length=3, max_length=320)


class OrderClaimStartPublic(BaseModel):
    status: str  # sent | on_account
    detail: str
    order_id: UUID | None = None


class OrderClaimPublic(BaseModel):
    order_id: UUID
    reference: str
    status: str
    claimed: bool
    buyer_email: str
    event_title: str | None = None
    ticket_count: int = 0
    message: str


class OrderAttendeePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ticket_type_id: UUID
    unit_index: int
    attendee_name: str
    attendee_email: str
    attendee_phone: str | None = None
    delivery_email: str | None = None
    delivery_phone: str | None = None


class OrderItemPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    item_kind: str = "ticket"
    ticket_type_id: UUID | None = None
    ticket_type_name: str | None = None
    merch_product_id: UUID | None = None
    merch_variant_id: UUID | None = None
    bundle_id: UUID | None = None
    product_name: str | None = None
    variant_label: str | None = None
    quantity: int
    unit_price: Decimal
    line_total: Decimal
    fulfillment_status: str | None = None
    pickup_code: str | None = None
    pickup_instructions: str | None = None


class OrderMerchFulfillmentPublic(BaseModel):
    id: UUID
    order_item_id: UUID
    status: str
    pickup_code: str
    pickup_instructions_snapshot: str | None = None
    product_name_snapshot: str
    variant_label_snapshot: str
    quantity: int
    fulfilled_at: datetime | None = None


class OrderCheckoutAnswerPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    question_id: UUID | None = None
    question_label: str
    question_type: str
    value: str


class PaymentPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    provider: str
    reference: str
    amount: Decimal
    currency: str
    status: str
    authorization_url: str | None = None
    paid_at: datetime | None = None
    created_at: datetime


class OrderFeeBreakdownLine(BaseModel):
    """Buyer-facing fee line (host commercial terms omitted)."""

    fee_key: str
    label: str
    payer: str
    amount: Decimal
    currency: str = "NGN"


class OrderPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    reference: str
    event_id: UUID | None = None
    status: str
    currency: str
    subtotal_amount: Decimal
    discount_amount: Decimal = Decimal("0")
    merch_discount_amount: Decimal = Decimal("0")
    shipping_amount: Decimal = Decimal("0")
    buyer_fee_total: Decimal = Decimal("0")
    host_fee_total: Decimal = Decimal("0")
    processing_fee_total: Decimal = Decimal("0")
    platform_revenue_total: Decimal = Decimal("0")
    host_net_estimate: Decimal = Decimal("0")
    total_amount: Decimal
    discount_total: Decimal | None = None
    final_total: Decimal | None = None
    fee_breakdown: list[OrderFeeBreakdownLine] = []
    promo_code_snapshot: str | None = None
    merch_discount_code_snapshot: str | None = None
    referral_code: str | None = None
    fulfillment_method: str | None = None
    buyer_email: str
    buyer_name: str
    is_guest_checkout: bool = False
    guest_buyer_email: str | None = None
    purchase_mode: str = "self"
    is_gift: bool = False
    purchased_for_someone_else: bool = False
    gift_message: str | None = None
    send_ticket_to_recipient: bool = False
    keep_buyer_copy: bool = True
    recipient_name: str | None = None
    recipient_email: str | None = None
    recipient_phone: str | None = None
    claimed_at: datetime | None = None
    created_at: datetime
    paid_at: datetime | None
    archived_at: datetime | None = None
    reservation_expires_at: datetime | None = None
    items: list[OrderItemPublic] = []
    payments: list[PaymentPublic] = []
    checkout_answers: list[OrderCheckoutAnswerPublic] = []
    attendees: list[OrderAttendeePublic] = []
    event_title: str | None = None
    event_slug: str | None = None
    host_id: UUID | None = None
    host_name: str | None = None
    host_slug: str | None = None
    merch_fulfillments: list[OrderMerchFulfillmentPublic] = []
    # Present only immediately after guest payment finalize (never stored client-side long-term)
    claim_token: str | None = None
    claim_path: str | None = None


class CheckoutInitializeRequest(BaseModel):
    """Optional Paystack customer email when account email is demo-only (.test)."""

    payment_email: str | None = Field(default=None, max_length=320)


class CheckoutResponse(BaseModel):
    order_id: UUID
    reference: str
    amount: Decimal
    currency: str
    free_checkout: bool = False
    authorization_url: str | None = None
    access_code: str | None = None
    public_key: str | None = None
    paystack_mode: Literal["test", "live"] | None = None
    paystack_customer_email: str | None = None
    buyer_fee_total: Decimal = Decimal("0")
    final_total: Decimal | None = None
    fee_breakdown: list[OrderFeeBreakdownLine] = []


class PaystackConfigPublic(BaseModel):
    """Safe client config — public key only, never secrets."""

    mode: Literal["test", "live"]
    public_key: str | None = None
    base_url: str = "https://api.paystack.co"


class CheckoutBuyerEmailCheck(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    event_id: UUID
    has_tickets: bool = False
    has_merch: bool = True


class CheckoutBuyerEmailCheckPublic(BaseModel):
    status: Literal["ok", "existing_account"]


class OrderPdfDownloadRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)


class OrderReferenceSummaryPublic(BaseModel):
    reference: str
    status: str
    pdf_available: bool = False
