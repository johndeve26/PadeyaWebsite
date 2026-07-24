"""Sponsor workspace report API schemas."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class InquiryCountsPublic(BaseModel):
    total: int
    new: int
    reviewing: int
    accepted: int
    declined: int
    closed: int
    pending: int


class LabelCountPublic(BaseModel):
    label: str
    count: int


class RecommendationEngagementPublic(BaseModel):
    clicked: int
    saved: int
    dismissed: int


class PlacementsSummaryPublic(BaseModel):
    count: int
    spend_committed_ngn: Decimal | None = None


class DealsSummaryPublic(BaseModel):
    committed_spend_ngn: Decimal | None = None
    paid_spend_ngn: Decimal | None = None
    pending_invoices: int
    active_deals: int
    completed_deals: int
    proposals_awaiting: int
    deliverables_pending: int = 0
    deliverables_completed: int = 0
    deliverables_overdue: int = 0
    deliverables_completion_rate: float | None = None


class PendingActionPublic(BaseModel):
    kind: str
    count: int
    label: str


class SponsorOverviewReportPublic(BaseModel):
    sponsor_id: UUID
    generated_at: datetime
    saved_opportunities_count: int
    inquiries: InquiryCountsPublic
    response_rate: float | None = None
    avg_response_hours: float | None = None
    campaigns_by_status: dict[str, int]
    top_categories: list[LabelCountPublic]
    top_locations: list[LabelCountPublic]
    recommendation_engagement: RecommendationEngagementPublic
    linked_placements: PlacementsSummaryPublic
    deals: DealsSummaryPublic
    estimated_reach: int | None = None
    pending_actions: list[PendingActionPublic]


class CampaignReportMetaPublic(BaseModel):
    campaign_id: UUID
    name: str
    objective: str
    status: str
    start_date: date | None
    end_date: date | None
    budget_min: Decimal | None = None
    budget_max: Decimal | None = None
    currency: str
    description: str | None = None


class CampaignReportPublic(BaseModel):
    campaign: CampaignReportMetaPublic
    generated_at: datetime
    saved_opportunities_count: int
    inquiries: InquiryCountsPublic
    response_rate: float | None = None
    avg_response_hours: float | None = None
    recommendation_engagement: RecommendationEngagementPublic
    linked_placements: PlacementsSummaryPublic
    deals: DealsSummaryPublic
    estimated_reach: int | None = None
    pending_actions: list[PendingActionPublic]
    top_categories: list[LabelCountPublic] = Field(default_factory=list)
    top_locations: list[LabelCountPublic] = Field(default_factory=list)
