"""Review request/response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ReviewCreate(BaseModel):
    ticket_id: UUID
    rating: int = Field(ge=1, le=5)
    title: str | None = Field(default=None, max_length=160)
    body: str = Field(min_length=10, max_length=5000)


class ReviewUpdate(BaseModel):
    rating: int | None = Field(default=None, ge=1, le=5)
    title: str | None = Field(default=None, max_length=160)
    body: str | None = Field(default=None, min_length=10, max_length=5000)


class ReviewReplyCreate(BaseModel):
    body: str = Field(min_length=2, max_length=3000)


class ReviewReportCreate(BaseModel):
    reason: str = Field(min_length=5, max_length=2000)


class ReviewModerateRequest(BaseModel):
    action: str
    reason: str = Field(min_length=5, max_length=2000)

    @field_validator("action")
    @classmethod
    def valid_action(cls, value: str) -> str:
        if value not in {"hide", "restore"}:
            raise ValueError("action must be hide or restore")
        return value


class ReviewReplyPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    body: str
    author_name: str | None = None
    created_at: datetime


class ReviewPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID
    host_id: UUID
    reviewer_user_id: UUID
    ticket_id: UUID
    rating: int
    title: str | None
    body: str
    status: str
    event_title: str | None = None
    event_slug: str | None = None
    reviewer_name: str | None = None
    created_at: datetime
    reply: ReviewReplyPublic | None = None
    report_count: int = 0
    moderation_reason: str | None = None


class ReviewEligibility(BaseModel):
    eligible: bool
    reason: str | None = None
    ticket_id: UUID | None = None
    event_id: UUID | None = None
    event_title: str | None = None
    host_id: UUID | None = None


class ReviewReportPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    review_id: UUID
    reporter_user_id: UUID
    reason: str
    status: str
    created_at: datetime
    review: ReviewPublic | None = None
