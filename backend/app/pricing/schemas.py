"""Public-safe pricing response schemas."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PublicPricingFeeRow(BaseModel):
    """One public-safe fee or fee-category row for the marketing pricing page."""

    model_config = ConfigDict(from_attributes=True)

    fee_key: str
    label: str
    category: str
    payer: str
    fee_type: str | None = None
    public_description: str
    appears_at: list[str] = Field(default_factory=list)
    configurable: bool = True
    may_vary_by_host: bool = True
    rates_public: bool = False
    enabled: bool = True
    # Only populated when rates_public is True (buyer-facing publishable rates).
    percentage_value: Decimal | None = None
    fixed_value_major: Decimal | None = None
    currency: str = "NGN"
    display_rate: str | None = None


class PublicPricingResponse(BaseModel):
    currency: str = "NGN"
    note: str
    fees: list[PublicPricingFeeRow]
    categories: list[PublicPricingFeeRow]
