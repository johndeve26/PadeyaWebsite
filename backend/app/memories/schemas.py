"""Event Memories request/response schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.reviews.schemas import ReviewPublic


class MemoryMediaPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    media_type: str
    url: str
    storage_key: str | None = None
    label: str | None = None
    sort_order: int
    created_at: datetime


class MemoryAttendanceStats(BaseModel):
    tickets_sold: int
    checked_in: int
    check_in_rate: Decimal | None = None


class MemoryUpcomingEvent(BaseModel):
    id: UUID
    title: str
    slug: str
    start_datetime: datetime
    city: str | None = None
    banner_url: str | None = None


class EventMemoryPublic(BaseModel):
    id: UUID
    event_id: UUID
    host_id: UUID
    status: str
    host_recap_note: str | None
    moderation_status: str
    event_title: str
    event_slug: str
    start_datetime: datetime
    end_datetime: datetime
    venue_name: str | None
    city: str | None
    banner_url: str | None
    host_display_name: str
    host_username: str
    attendance: MemoryAttendanceStats
    verified_rating: Decimal | None
    review_count: int
    top_reviews: list[ReviewPublic]
    media: list[MemoryMediaPublic]
    upcoming_events: list[MemoryUpcomingEvent]
    share_path: str
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime


class EventMemoryUpdate(BaseModel):
    host_recap_note: str | None = Field(default=None, max_length=5000)


class MemoryMediaCreate(BaseModel):
    url: str = Field(min_length=1, max_length=500)
    media_type: str = Field(default="image", min_length=2, max_length=64)
    label: str | None = Field(default=None, max_length=160)
    sort_order: int | None = None


class MemoryModerateRequest(BaseModel):
    action: str = Field(pattern="^(hide|unhide|flag|approve)$")
    note: str | None = Field(default=None, max_length=1000)


class LegacyMemoryCard(BaseModel):
    id: UUID
    event_id: UUID
    event_title: str
    event_slug: str
    start_datetime: datetime
    city: str | None
    banner_url: str | None
    share_path: str
    verified_rating: Decimal | None = None
