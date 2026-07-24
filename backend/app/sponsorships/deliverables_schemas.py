"""Sponsorship deliverable API schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SponsorshipDeliverablePublic(BaseModel):
    id: UUID
    deal_id: UUID
    placement_id: UUID | None
    title: str
    description: str | None
    deliverable_type: str
    due_at: datetime | None
    status: str
    proof_url: str | None = None
    proof_notes: str | None = None
    submitted_at: datetime | None = None
    approved_at: datetime | None = None
    rejection_reason: str | None = None
    created_at: datetime
    updated_at: datetime
    can_host_edit: bool = False
    can_host_submit: bool = False
    can_sponsor_review: bool = False


class HostDeliverablePatch(BaseModel):
    status: str | None = Field(default=None, max_length=32)
    proof_notes: str | None = Field(default=None, max_length=5000)
    description: str | None = Field(default=None, max_length=5000)


class HostDeliverableSubmit(BaseModel):
    proof_url: str = Field(min_length=8, max_length=500)
    proof_notes: str | None = Field(default=None, max_length=5000)


class SponsorDeliverableReject(BaseModel):
    rejection_reason: str = Field(min_length=3, max_length=2000)


class AdminDeliverablePatch(BaseModel):
    status: str | None = Field(default=None, max_length=32)
    due_at: datetime | None = None
    rejection_reason: str | None = Field(default=None, max_length=2000)


class DeliverablesSummaryPublic(BaseModel):
    pending: int
    in_progress: int
    submitted: int
    completed: int
    overdue: int
    completion_rate: float | None = None
