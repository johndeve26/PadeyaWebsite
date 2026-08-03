"""Finance request/response schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.finance.constants import REFUND_POLICY_TYPES


class RefundEscalate(BaseModel):
    note: str = Field(min_length=3, max_length=2000)


class RefundLineAllocationIn(BaseModel):
    """Authoritative per-order-item refund allocation for commission reversal."""

    order_item_id: UUID
    refunded_quantity: int = Field(ge=1)
    refunded_item_subtotal: Decimal = Field(gt=0)
    allocation_id: str | None = Field(default=None, max_length=128)
    provider_refund_reference: str | None = Field(default=None, max_length=128)


class RefundRequestCreate(BaseModel):
    order_id: UUID
    reason: str = Field(min_length=5, max_length=2000)
    refund_type: str = "full"
    amount: Decimal | None = None
    ticket_ids: list[UUID] | None = None
    line_allocations: list[RefundLineAllocationIn] | None = None

    @field_validator("refund_type")
    @classmethod
    def valid_type(cls, value: str) -> str:
        if value not in {"full", "partial"}:
            raise ValueError("refund_type must be full or partial")
        return value


class RefundReview(BaseModel):
    action: str
    note: str | None = None
    line_allocations: list[RefundLineAllocationIn] | None = None

    @field_validator("action")
    @classmethod
    def valid_action(cls, value: str) -> str:
        if value not in {"approve", "reject"}:
            raise ValueError("action must be approve or reject")
        return value


class RefundRequestPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_id: UUID
    payment_id: UUID | None
    buyer_user_id: UUID
    host_id: UUID
    event_id: UUID
    status: str
    refund_type: str
    requested_amount: Decimal
    currency: str
    reason: str
    policy_snapshot: str
    ticket_ids: list | None
    line_allocations: list | None = None
    requires_referral_refund_allocation: bool = False
    escalation_note: str | None
    review_note: str | None
    reviewed_by_user_id: UUID | None
    reviewed_at: datetime | None
    created_at: datetime
    order_reference: str | None = None
    event_title: str | None = None


class RefundPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    refund_request_id: UUID
    order_id: UUID
    host_id: UUID
    amount: Decimal
    currency: str
    status: str
    processed_by_user_id: UUID
    ledger_entry_id: UUID | None
    created_at: datetime


class HostBalancePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    host_id: UUID
    currency: str
    available_balance: Decimal
    pending_payout_balance: Decimal
    lifetime_earned: Decimal
    lifetime_refunded: Decimal
    lifetime_paid_out: Decimal
    updated_at: datetime


class LedgerEntryPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    host_id: UUID
    entry_type: str
    direction: str
    amount: Decimal
    currency: str
    available_balance_after: Decimal
    pending_payout_balance_after: Decimal
    reference_type: str | None
    reference_id: str | None
    description: str | None
    created_by_user_id: UUID | None
    created_at: datetime


class BankDetails(BaseModel):
    bank_name: str = Field(min_length=2, max_length=120)
    account_name: str = Field(min_length=2, max_length=160)
    account_number: str = Field(min_length=6, max_length=32)


class PayoutRequestCreate(BaseModel):
    amount: Decimal = Field(gt=0)
    bank: BankDetails
    note: str | None = Field(default=None, max_length=2000)


class PayoutReview(BaseModel):
    action: str
    note: str | None = None

    @field_validator("action")
    @classmethod
    def valid_action(cls, value: str) -> str:
        if value not in {"approve", "reject", "under_review"}:
            raise ValueError("action must be approve, reject, or under_review")
        return value


class PayoutMarkPaid(BaseModel):
    bank_transfer_reference: str = Field(min_length=3, max_length=128)
    evidence_file_url: str = Field(min_length=5, max_length=500)
    admin_note: str | None = Field(default=None, max_length=2000)
    paid_at: datetime | None = None


class PayoutEvidencePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    payout_request_id: UUID
    bank_transfer_reference: str
    evidence_file_url: str
    admin_note: str | None
    paid_at: datetime
    paid_by_user_id: UUID
    recipient_bank_snapshot: dict
    created_at: datetime


class PayoutRequestPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    host_id: UUID
    amount: Decimal
    currency: str
    status: str
    recipient_bank_snapshot: dict
    host_note: str | None
    review_note: str | None
    rejection_reason: str | None
    requested_by_user_id: UUID
    reviewed_by_user_id: UUID | None
    reviewed_at: datetime | None
    created_at: datetime
    host_display_name: str | None = None
    evidence: PayoutEvidencePublic | None = None


class SettlementReportPublic(BaseModel):
    host_id: UUID | None = None
    currency: str = "NGN"
    total_earned: Decimal
    total_refunded: Decimal
    total_paid_out: Decimal
    available_balance: Decimal
    pending_payout_balance: Decimal
    open_refund_requests: int
    open_payout_requests: int
    ledger_entry_count: int


class RefundPolicyInfo(BaseModel):
    policies: list[str] = list(REFUND_POLICY_TYPES)


class PlatformRevenueSummary(BaseModel):
    currency: str = "NGN"
    gross_payment_volume: Decimal
    platform_revenue: Decimal
    ticket_commission_revenue: Decimal
    buyer_service_fee_revenue: Decimal
    merch_commission_revenue: Decimal
    vault_commission_revenue: Decimal
    processing_fee_revenue: Decimal = Decimal("0")
    ticket_revenue: Decimal = Decimal("0")
    merch_revenue: Decimal = Decimal("0")
    vault_revenue: Decimal = Decimal("0")
    refunds: Decimal
    ambassador_rewards: Decimal = Decimal("0")
    host_net_payable: Decimal
    payouts_completed: Decimal
    pending_payouts: Decimal
    open_payout_requests: int = 0
    entry_count: int = 0


class PlatformLedgerEntryPublic(BaseModel):
    id: str
    entry_type: str
    direction: str
    amount: Decimal
    currency: str
    order_id: str | None = None
    host_id: str | None = None
    event_id: str | None = None
    description: str | None = None
    reference_type: str | None = None
    reference_id: str | None = None
    payment_reference_masked: str | None = None
    category: str | None = None
    created_at: datetime


class PlatformRevenueReportPublic(BaseModel):
    summary: PlatformRevenueSummary
    filters: dict
    entries: list[PlatformLedgerEntryPublic] = []
