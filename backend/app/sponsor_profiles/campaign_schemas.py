"""Sponsor campaign API schemas."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.sponsor_profiles.constants import (
    CAMPAIGN_OBJECTIVES,
    CAMPAIGN_STATUSES,
    CAMPAIGN_VISIBILITY,
)


class SponsorCampaignCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    objective: str
    description: str | None = Field(default=None, max_length=10000)
    target_categories: list[str] | None = None
    target_locations: list[str] | None = None
    target_audience: dict | None = None
    budget_min: Decimal | None = Field(default=None, ge=0)
    budget_max: Decimal | None = Field(default=None, ge=0)
    currency: str = Field(default="NGN", max_length=8)
    start_date: date | None = None
    end_date: date | None = None
    visibility: str = "private"
    sponsor_saved_item_id: UUID | None = None

    @field_validator("objective")
    @classmethod
    def valid_objective(cls, value: str) -> str:
        if value not in CAMPAIGN_OBJECTIVES:
            raise ValueError("Invalid campaign objective")
        return value

    @field_validator("visibility")
    @classmethod
    def valid_visibility(cls, value: str) -> str:
        if value not in CAMPAIGN_VISIBILITY:
            raise ValueError("Invalid campaign visibility")
        return value


class SponsorCampaignUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    objective: str | None = None
    description: str | None = Field(default=None, max_length=10000)
    target_categories: list[str] | None = None
    target_locations: list[str] | None = None
    target_audience: dict | None = None
    budget_min: Decimal | None = Field(default=None, ge=0)
    budget_max: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, max_length=8)
    start_date: date | None = None
    end_date: date | None = None
    visibility: str | None = None
    status: str | None = None

    @field_validator("objective")
    @classmethod
    def valid_objective(cls, value: str | None) -> str | None:
        if value is not None and value not in CAMPAIGN_OBJECTIVES:
            raise ValueError("Invalid campaign objective")
        return value

    @field_validator("visibility")
    @classmethod
    def valid_visibility(cls, value: str | None) -> str | None:
        if value is not None and value not in CAMPAIGN_VISIBILITY:
            raise ValueError("Invalid campaign visibility")
        return value

    @field_validator("status")
    @classmethod
    def valid_status(cls, value: str | None) -> str | None:
        if value is not None and value not in CAMPAIGN_STATUSES:
            raise ValueError("Invalid campaign status")
        return value


class CampaignSavedItemLinkCreate(BaseModel):
    sponsor_saved_item_id: UUID
    note: str | None = Field(default=None, max_length=2000)


class CampaignSavedItemPublic(BaseModel):
    id: UUID
    sponsor_saved_item_id: UUID
    item_type: str
    item_id: UUID
    title: str | None
    subtitle: str | None
    href: str | None
    available: bool
    note: str | None
    created_at: datetime


class CampaignInquiryPublic(BaseModel):
    id: UUID
    slot_id: UUID
    slot_title: str | None
    host_display_name: str | None
    status: str
    created_at: datetime


class SponsorCampaignListItem(BaseModel):
    id: UUID
    name: str
    public_ref: str
    objective: str
    status: str
    visibility: str
    moderation_status: str
    budget_min: Decimal | None
    budget_max: Decimal | None
    currency: str
    start_date: date | None
    end_date: date | None
    saved_items_count: int
    inquiries_count: int
    created_at: datetime
    updated_at: datetime


class SponsorCampaignDetail(SponsorCampaignListItem):
    description: str | None
    target_categories: list[str] | None
    target_locations: list[str] | None
    target_audience: dict | None
    rejection_reason: str | None
    saved_items: list[CampaignSavedItemPublic]
    inquiries: list[CampaignInquiryPublic]
    can_edit: bool


class SponsorCampaignListPublic(BaseModel):
    items: list[SponsorCampaignListItem]
    total: int


class AdminCampaignRejectRequest(BaseModel):
    rejection_reason: str = Field(min_length=3, max_length=2000)


class AdminCampaignListItem(BaseModel):
    id: UUID
    sponsor_id: UUID
    sponsor_name: str
    name: str
    objective: str
    status: str
    visibility: str
    moderation_status: str
    created_at: datetime


class AdminCampaignDetail(AdminCampaignListItem):
    description: str | None
    rejection_reason: str | None
    budget_min: Decimal | None
    budget_max: Decimal | None
    currency: str


class CampaignRecommendationReason(BaseModel):
    code: str
    label: str


class CampaignRecommendationItem(BaseModel):
    item_type: str
    item_id: UUID
    score: int
    score_label: str | None = None
    reasons: list[CampaignRecommendationReason]
    title: str | None = None
    subtitle: str | None = None
    href: str | None = None
    available: bool = False
    host_display_name: str | None = None
    slot_price: float | None = None
    audience_estimate: int | None = None


class CampaignRecommendationListPublic(BaseModel):
    items: list[CampaignRecommendationItem]
    total: int


class CampaignRecommendationFeedbackCreate(BaseModel):
    item_type: str
    action: str
