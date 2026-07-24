"""Public buyer-facing fee quote (no host commercial terms)."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class BuyerFeeQuoteRequest(BaseModel):
    host_id: UUID
    ticket_subtotal: Decimal = Field(default=Decimal("0"), ge=0)
    merch_subtotal: Decimal = Field(default=Decimal("0"), ge=0)
    ticket_discount: Decimal = Field(default=Decimal("0"), ge=0)
    merch_discount: Decimal = Field(default=Decimal("0"), ge=0)
    shipping_amount: Decimal = Field(default=Decimal("0"), ge=0)
    currency: str = "NGN"


class BuyerFeeQuoteLine(BaseModel):
    fee_key: str
    label: str
    payer: str
    amount: Decimal
    currency: str = "NGN"


class BuyerFeeQuoteResponse(BaseModel):
    subtotal: Decimal
    discount_total: Decimal
    shipping_amount: Decimal
    buyer_fee_total: Decimal
    processing_fee_total: Decimal
    final_total: Decimal
    fee_breakdown: list[BuyerFeeQuoteLine] = []
