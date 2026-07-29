"""CRM request/response schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class FollowRequest(BaseModel):
    host_id: UUID | None = None
    host_slug: str | None = None

    @model_validator(mode="after")
    def require_host_target(self) -> FollowRequest:
        slug = (self.host_slug or "").strip()
        if self.host_id is None and not slug:
            raise ValueError("host_id or host_slug is required")
        if slug:
            self.host_slug = slug.replace("@", "").split("/")[-1].lower()
        return self


class MarketingOptInUpdate(BaseModel):
    marketing_opt_in: bool


class FollowingHostPublic(BaseModel):
    host_id: UUID
    display_name: str
    username: str
    marketing_opt_in: bool
    followed_at: datetime


class AudienceMemberPublic(BaseModel):
    user_id: UUID
    display_name: str
    email: str
    marketing_opt_in: bool
    events_attended: int = 0
    tickets_purchased: int = 0
    last_order_at: datetime | None = None
    tags: list[str] = []
    gender: str | None = None
    gender_short: str | None = None
    gender_label: str | None = None
    gender_visible: bool = False


class AudienceStatsPublic(BaseModel):
    followers: int
    past_buyers: int
    repeat_buyers: int
    vip_buyers: int
    checked_in_attendees: int
    no_shows: int
    promo_code_buyers: int
    ambassador_referrals: int
    marketing_opted_in: int


class AudienceSegmentPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    segment_key: str
    description: str | None
    filters: dict | None
    is_system: bool
    created_at: datetime
    member_count: int = 0


class AudienceSegmentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    segment_key: str
    description: str | None = None
    filters: dict | None = None

    @field_validator("segment_key")
    @classmethod
    def valid_key(cls, value: str) -> str:
        allowed = {
            "followers",
            "past_buyers",
            "repeat_buyers",
            "vip_buyers",
            "checked_in_attendees",
            "no_shows",
            "promo_code_buyers",
            "ambassador_referrals",
            "superfans",
            "vault_subscribers",
        }
        if value not in allowed:
            raise ValueError("Invalid segment_key")
        return value


class AnnouncementCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    body_email: str = Field(min_length=5)
    body_whatsapp: str | None = None
    channel: str = "email"
    segment_id: UUID | None = None
    segment_key: str | None = None
    filters: dict | None = None

    @field_validator("channel")
    @classmethod
    def valid_channel(cls, value: str) -> str:
        if value not in {"email", "whatsapp", "both"}:
            raise ValueError("channel must be email, whatsapp, or both")
        return value


class AnnouncementUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    body_email: str | None = Field(default=None, min_length=5)
    body_whatsapp: str | None = None
    channel: str | None = None

    @field_validator("channel")
    @classmethod
    def valid_channel(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if value not in {"email", "whatsapp", "both"}:
            raise ValueError("channel must be email, whatsapp, or both")
        return value


class AnnouncementRecipientPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    email: str
    display_name: str
    channel: str
    status: str
    skip_reason: str | None


class AnnouncementPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    host_id: UUID
    segment_id: UUID | None
    title: str
    body_email: str
    body_whatsapp: str | None
    channel: str
    status: str
    delivery_status: str
    recipient_count: int
    created_at: datetime
    recipients: list[AnnouncementRecipientPublic] = []
    whatsapp_export: str | None = None


class AnnouncementDispatchResult(BaseModel):
    announcement_id: UUID
    emailed: int
    skipped: int
    delivery_status: str
    delivery_provider: str | None = None
