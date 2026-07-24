"""Admin editable email template API schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AdminEmailTemplatePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    title: str
    category: str
    is_required: bool
    is_enabled: bool
    default_enabled: bool
    recipient_mode: str
    recipient_group: str
    default_recipient_group: str
    custom_recipient_emails: list[str] = Field(default_factory=list)
    recipient_emails_display: str | None = None
    resolved_recipient_count: int = 0
    max_recipients: int = 20
    delivery_mode: str
    threshold_amount: float | None = None
    variables: list[str] = Field(default_factory=list)
    subject: str
    default_subject: str
    preview_text: str
    default_preview_text: str
    headline: str
    html_body: str | None = None
    text_body: str | None = None
    registry_subject: str
    updated_at: datetime
    updated_by_admin_id: UUID | None = None


class AdminEmailTemplateListResponse(BaseModel):
    items: list[AdminEmailTemplatePublic]


class AdminEmailTemplateUpdate(BaseModel):
    subject: str | None = None
    preview_text: str | None = None
    html_body: str | None = None
    text_body: str | None = None
    is_enabled: bool | None = None
    recipient_mode: str | None = None
    recipient_group: str | None = None
    custom_recipient_emails: list[str] | None = None
    recipient_emails: str | None = None
    delivery_mode: str | None = None
    threshold_amount: float | None = None


class AdminEmailTemplatePreviewRequest(BaseModel):
    context: dict[str, str] | None = None
    test_recipient_emails: str | None = None


class AdminEmailTemplateTestSendResponse(BaseModel):
    recipient_count: int


class AdminEmailTemplatePreviewResponse(BaseModel):
    subject: str
    text: str
    html: str


class AdminEmailNotificationSettingsPublic(BaseModel):
    master_enabled: bool
    digest_enabled: bool
    digest_hour_utc: int
    updated_at: datetime


class AdminEmailNotificationSettingsUpdate(BaseModel):
    master_enabled: bool | None = None
    digest_enabled: bool | None = None
    digest_hour_utc: int | None = Field(default=None, ge=0, le=23)
