"""Fan host recommendation API schemas."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from app.legacy.schemas import HostDiscoveryPublic


class HostRecommendationReason(BaseModel):
    code: str
    label: str


class HostRecommendationPublic(BaseModel):
    host: HostDiscoveryPublic
    score: int
    reasons: list[HostRecommendationReason]
    recommendation_label: str | None = None
    relationship: str = "none"


class HostRecommendationsPublic(BaseModel):
    items: list[HostRecommendationPublic]
    page: int
    limit: int
    total: int
    next_cursor: str | None = None
    empty_title: str | None = None
    empty_description: str | None = None


class DismissHostRecommendationBody(BaseModel):
    reason: str | None = Field(default=None, max_length=120)


class HostRecommendationActionPublic(BaseModel):
    ok: bool = True
    host_id: UUID | None = None
    category_slug: str | None = None


class HostRecommendationImpressionItem(BaseModel):
    host_id: UUID
    surface: str = Field(max_length=32)
    position: int | None = Field(default=None, ge=0, le=500)
    recommendation_score: int | None = Field(default=None, ge=0, le=100)
    reason_codes: list[str] | None = None


class HostRecommendationImpressionsBody(BaseModel):
    items: list[HostRecommendationImpressionItem] = Field(min_length=1, max_length=25)


class HideHostCategoryBody(BaseModel):
    category_slug: str = Field(min_length=1, max_length=120)


class HostRecommendationImpressionsPublic(BaseModel):
    ok: bool = True
    recorded: int


class HostRecommendationDebugPublic(BaseModel):
    user_id: UUID
    enabled: bool
    config: dict
    candidate_count: int
    excluded_by_reason: dict[str, int]
    shown_count: int
    top: list[dict]
