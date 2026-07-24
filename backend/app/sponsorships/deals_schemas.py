"""Sponsorship deal API schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class SponsorshipDealCreate(BaseModel):
    inquiry_id: UUID | None = None
    sponsor_id: UUID
    slot_id: UUID | None = None
    event_id: UUID | None = None
    campaign_id: UUID | None = None
    title: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    package_type: str = Field(min_length=2, max_length=64)
    deliverables: list[str] | None = None
    amount: Decimal = Field(ge=0)
    currency: str = "NGN"
    starts_at: datetime | None = None
    ends_at: datetime | None = None


class SponsorshipDealUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    package_type: str | None = Field(default=None, max_length=64)
    deliverables: list[str] | None = None
    amount: Decimal | None = Field(default=None, ge=0)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    campaign_id: UUID | None = None


class SponsorshipInvoicePublic(BaseModel):
    id: UUID
    invoice_number: str
    amount: Decimal
    currency: str
    status: str
    due_at: datetime | None
    paid_at: datetime | None
    payment_url: str | None = None


class SponsorshipDealPublic(BaseModel):
    id: UUID
    sponsor_id: UUID
    host_id: UUID
    event_id: UUID | None
    campaign_id: UUID | None
    inquiry_id: UUID | None
    slot_id: UUID | None
    placement_id: UUID | None
    title: str
    description: str | None
    package_type: str
    deliverables: list[str] | None
    amount: Decimal
    currency: str
    status: str
    accepted_at: datetime | None
    starts_at: datetime | None
    ends_at: datetime | None
    created_at: datetime
    updated_at: datetime
    host_display_name: str | None = None
    sponsor_display_name: str | None = None
    invoice: SponsorshipInvoicePublic | None = None
    can_edit: bool = False
    can_accept: bool = False
    can_pay: bool = False


class SponsorshipDealPayResponse(BaseModel):
    payment_url: str
    invoice_id: UUID
    message: str = "Complete payment on Paystack. Status updates after verified webhook only."


class HostSponsorshipRevenueReport(BaseModel):
    revenue_pending_ngn: Decimal | None
    revenue_paid_ngn: Decimal | None
    active_placements: int
    active_deals: int = 0
    pending_deliverables: int = 0
    overdue_deliverables: int = 0
    completed_deliverables: int = 0
    deliverables_completion_rate: float | None = None
