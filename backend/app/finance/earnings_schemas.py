"""Schemas for host / admin earnings reports (net after Pàdéyá deductions)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class HostFeeTermPublic(BaseModel):
    """Resolved fee term for the viewing host only (never other hosts)."""

    fee_key: str
    label: str
    category: str
    fee_type: str
    percentage_value: Decimal | None = None
    fixed_value_major: Decimal | None = None
    currency: str = "NGN"
    payer: str
    source: str
    enabled: bool = True


class EarningsOrderRow(BaseModel):
    """Per-order (or vault unlock) earnings line for host/admin tables."""

    model_config = ConfigDict(from_attributes=True)

    row_kind: str = "order"  # order | vault
    order_id: UUID | None = None
    reference: str
    event_id: UUID | None = None
    event_title: str | None = None
    item_label: str
    paid_at: datetime | None = None
    payment_status: str
    payout_status: str

    buyer_paid_total: Decimal
    item_subtotal: Decimal
    discount_total: Decimal
    shipping_amount: Decimal = Decimal("0")
    host_gross: Decimal
    buyer_fee_total: Decimal
    host_fee_total: Decimal
    processing_fee_host: Decimal = Decimal("0")
    ambassador_reward: Decimal = Decimal("0")
    refund_amount: Decimal = Decimal("0")
    platform_revenue: Decimal
    host_net: Decimal


class EarningsSummary(BaseModel):
    host_id: UUID
    host_display_name: str | None = None
    event_id: UUID | None = None
    event_title: str | None = None
    currency: str = "NGN"

    gross_ticket_sales: Decimal = Decimal("0")
    gross_merch_sales: Decimal = Decimal("0")
    gross_vault_sales: Decimal = Decimal("0")
    discounts_total: Decimal = Decimal("0")
    shipping_total: Decimal = Decimal("0")
    # Item subtotal after discounts (+ shipping), before host-paid deductions.
    # Buyer-paid platform fees are excluded.
    host_gross: Decimal = Decimal("0")

    padeya_commission: Decimal = Decimal("0")
    processing_fees_host_paid: Decimal = Decimal("0")
    other_host_paid_fees: Decimal = Decimal("0")
    ambassador_rewards: Decimal = Decimal("0")
    refunds_total: Decimal = Decimal("0")
    deductions_total: Decimal = Decimal("0")

    # Buyer-paid fees kept by platform — never inflate host gross.
    buyer_platform_fees: Decimal = Decimal("0")
    platform_revenue_total: Decimal = Decimal("0")

    net_earnings: Decimal = Decimal("0")
    pending_payout: Decimal = Decimal("0")
    paid_out: Decimal = Decimal("0")
    available_balance: Decimal = Decimal("0")

    paid_order_count: int = 0
    vault_sale_count: int = 0


class HostEarningsReport(BaseModel):
    summary: EarningsSummary
    fee_terms: list[HostFeeTermPublic] = Field(default_factory=list)
    rows: list[EarningsOrderRow] = Field(default_factory=list)
    note: str = (
        "Host earnings are calculated after platform deductions. "
        "Buyer-paid service fees belong to Pàdéyá and are not included in host gross."
    )
