"""Event Memories request/response schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.memories.constants import EXTERNAL_GALLERY_LABELS
from app.reviews.schemas import ReviewPublic


class MemoryMediaPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    media_type: str
    url: str
    thumbnail_url: str | None = None
    storage_key: str | None = None
    label: str | None = None
    caption: str | None = None
    sort_order: int
    uploader_role: str = "host"
    is_cover: bool = False
    status: str = "active"
    width: int | None = None
    height: int | None = None
    mime_type: str | None = None
    size_bytes: int | None = None
    attribution: str | None = None
    verified_attendee: bool = False
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


class MemoryCounts(BaseModel):
    memory_count: int = 0
    host_memory_count: int = 0
    community_memory_count: int = 0
    contributor_count: int = 0


class EventMemoryPublic(BaseModel):
    id: UUID
    event_id: UUID
    host_id: UUID
    status: str
    host_recap_note: str | None
    external_gallery_url: str | None = None
    external_gallery_label: str | None = None
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
    host_media: list[MemoryMediaPublic] = []
    community_media: list[MemoryMediaPublic] = []
    counts: MemoryCounts = Field(default_factory=MemoryCounts)
    upcoming_events: list[MemoryUpcomingEvent]
    share_path: str
    memories_path: str | None = None
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime
    seo_indexable: bool = False


class EventMemoryUpdate(BaseModel):
    host_recap_note: str | None = Field(default=None, max_length=5000)
    external_gallery_url: str | None = Field(default=None, max_length=500)
    external_gallery_label: str | None = Field(default=None, max_length=64)

    @field_validator("external_gallery_label")
    @classmethod
    def _label(cls, value: str | None) -> str | None:
        if value is None or value.strip() == "":
            return None
        cleaned = value.strip().lower()
        if cleaned not in EXTERNAL_GALLERY_LABELS:
            raise ValueError(
                f"external_gallery_label must be one of {EXTERNAL_GALLERY_LABELS}"
            )
        return cleaned


class MemoryMediaCreate(BaseModel):
    url: str = Field(min_length=1, max_length=500)
    media_type: str = Field(default="image", min_length=2, max_length=64)
    label: str | None = Field(default=None, max_length=160)
    caption: str | None = Field(default=None, max_length=280)
    sort_order: int | None = None


class MemoryPhotoPatch(BaseModel):
    caption: str | None = Field(default=None, max_length=280)
    sort_order: int | None = None
    is_cover: bool | None = None


class MemoryPhotoModerateRequest(BaseModel):
    action: str = Field(pattern="^(hide|restore|remove)$")
    note: str | None = Field(default=None, max_length=1000)


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


class MemoryAlbumCard(BaseModel):
    event_id: UUID
    event_slug: str
    event_title: str
    start_datetime: datetime
    end_datetime: datetime
    city: str | None = None
    host_display_name: str
    host_username: str
    cover_url: str | None = None
    cover_thumbnail_url: str | None = None
    counts: MemoryCounts
    memories_path: str
    share_path: str


class MemoryAlbumsResponse(BaseModel):
    items: list[MemoryAlbumCard]
    next_cursor: str | None = None


class MemoryEligibility(BaseModel):
    authenticated: bool
    ticket_verified: bool = False
    event_started: bool = False
    can_upload: bool = False
    role: str | None = None
    used: int = 0
    limit: int = 0
    remaining: int = 0
    host_limit: int = 10


class AdminMemoryPhoto(BaseModel):
    id: UUID
    memory_id: UUID
    event_id: UUID
    event_title: str
    event_slug: str
    uploader_role: str
    uploader_user_id: UUID | None
    status: str
    url: str
    thumbnail_url: str | None = None
    caption: str | None = None
    created_at: datetime
    hidden_by: str | None = None
