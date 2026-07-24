"""Pydantic schemas for admin notification APIs."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ChannelFlags(BaseModel):
    in_app: bool | None = None
    push: bool | None = None
    email: bool | None = None


class NotificationSettingUpdate(BaseModel):
    enabled: bool | None = None
    channels: ChannelFlags | None = None
    audience: str | None = None
    template_id: UUID | None = None
    cooldown_seconds: int | None = Field(default=None, ge=0, le=604800)
    send_mode: str | None = None
    classification: str | None = None
    respect_user_prefs: bool | None = None
    audience_filters: dict[str, Any] | None = None


class NotificationTemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    title_template: str = Field(min_length=1, max_length=200)
    body_template: str = Field(min_length=1, max_length=500)
    type_key: str | None = None
    cta_text: str | None = Field(default=None, max_length=80)
    cta_url_template: str | None = Field(default=None, max_length=300)
    email_template_key: str | None = None


class NotificationTemplateUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    title_template: str | None = Field(default=None, max_length=200)
    body_template: str | None = Field(default=None, max_length=500)
    type_key: str | None = None
    cta_text: str | None = Field(default=None, max_length=80)
    cta_url_template: str | None = Field(default=None, max_length=300)
    email_template_key: str | None = None


class CampaignCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1, max_length=500)
    cta_text: str | None = Field(default=None, max_length=80)
    cta_url: str | None = Field(default=None, max_length=300)
    channels: ChannelFlags | None = None
    audience_mode: str = "selected_users"
    audience_filters: dict[str, Any] | None = None
    user_ids: list[UUID] | None = None
    scheduled_at: datetime | None = None


class AudiencePreviewRequest(BaseModel):
    audience_mode: str = "selected_users"
    audience_filters: dict[str, Any] | None = None
    user_ids: list[UUID] | None = None
