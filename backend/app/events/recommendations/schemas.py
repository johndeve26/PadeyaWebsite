"""Event recommendation API schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.events.schemas import EventPublic


class EventRecommendationReason(BaseModel):
    code: str
    label: str


class EventRecommendationFlags(BaseModel):
    from_followed_host: bool = False
    similar_to_attended: bool = False
    near_you: bool = False
    connected_fans_signal: bool = False
    category_match: bool = False


class EventRecommendationPublic(BaseModel):
    event: EventPublic
    score: int
    reasons: list[EventRecommendationReason]
    flags: EventRecommendationFlags = Field(default_factory=EventRecommendationFlags)


class EventRecommendationsPublic(BaseModel):
    events: list[EventRecommendationPublic]
    next_cursor: str | None = None
    mode: str
    generated_at: datetime
    empty_title: str | None = None
    empty_description: str | None = None


class EventRecommendationFeedbackBody(BaseModel):
    action: str = Field(min_length=1, max_length=32)
    category_slug: str | None = Field(default=None, max_length=120)


class EventRecommendationFeedbackPublic(BaseModel):
    ok: bool = True
    event_id: UUID


class EventRecommendationImpressionItem(BaseModel):
    event_id: UUID
    surface: str = Field(max_length=32)
    position: int | None = Field(default=None, ge=0, le=500)
    recommendation_score: int | None = Field(default=None, ge=0, le=100)
    reason_codes: list[str] | None = None


class EventRecommendationImpressionsBody(BaseModel):
    items: list[EventRecommendationImpressionItem] = Field(min_length=1, max_length=25)


class EventRecommendationImpressionsPublic(BaseModel):
    ok: bool = True
    recorded: int


class EventRecommendationDebugPublic(BaseModel):
    user_id: UUID
    enabled: bool
    config: dict
    candidate_count: int
    excluded_by_reason: dict[str, int]
    shown_count: int
    top: list[dict]
