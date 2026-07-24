"""Support ticket API schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SupportDeflectionMeta(BaseModel):
    """Help-first deflection context attached when opening a ticket."""

    topic: str | None = Field(default=None, max_length=64)
    suggested_article_ids: list[str] = Field(default_factory=list, max_length=20)
    suggested_article_slugs: list[str] = Field(default_factory=list, max_length=20)
    articles_clicked: list[str] = Field(default_factory=list, max_length=20)
    referrer: str | None = Field(default=None, max_length=500)
    session_key: str | None = Field(default=None, max_length=64)
    help_suggestions_shown: bool = True


class SupportCaseCreate(BaseModel):
    subject: str = Field(min_length=3, max_length=200)
    category: str = Field(min_length=2, max_length=64)
    body: str = Field(min_length=5, max_length=8000)
    priority: str = "normal"
    related_order_id: UUID | None = None
    related_event_id: UUID | None = None
    related_host_id: UUID | None = None
    requester_context: str | None = None
    deflection: SupportDeflectionMeta | None = None


class SupportPublicCreate(BaseModel):
    subject: str = Field(min_length=3, max_length=200)
    category: str = Field(min_length=2, max_length=64)
    body: str = Field(min_length=5, max_length=8000)
    requester_email: str = Field(min_length=5, max_length=320)
    requester_name: str = Field(min_length=2, max_length=160)
    priority: str = "normal"
    # Honeypot — must be empty
    website: str | None = Field(default="", max_length=200)
    deflection: SupportDeflectionMeta | None = None


class SupportDeflectionEventCreate(BaseModel):
    event_type: str = Field(min_length=2, max_length=64)
    topic: str | None = Field(default=None, max_length=64)
    session_key: str | None = Field(default=None, max_length=64)
    article_id: UUID | None = None
    article_slug: str | None = Field(default=None, max_length=200)
    meta: dict[str, Any] | None = None


class SupportMessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=8000)


class SupportInternalNoteCreate(BaseModel):
    body: str = Field(min_length=1, max_length=8000)


class SupportAssignRequest(BaseModel):
    assignee_user_id: UUID | None = None


class SupportEscalateRequest(BaseModel):
    escalation_level: str = Field(min_length=2, max_length=32)
    note: str | None = Field(default=None, max_length=2000)


class SupportStatusUpdate(BaseModel):
    status: str = Field(min_length=2, max_length=32)


class SupportPriorityUpdate(BaseModel):
    priority: str = Field(min_length=2, max_length=16)


class SupportCategoryUpdate(BaseModel):
    category: str = Field(min_length=2, max_length=64)


class SupportSettingsUpdate(BaseModel):
    auto_assign_enabled: bool | None = None
    notify_on_urgent: bool | None = None
    public_form_enabled: bool | None = None
    default_priority: str | None = None


class SupportMessagePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    case_id: UUID
    author_user_id: UUID | None = None
    author_name: str | None = None
    body: str
    is_internal: bool
    created_at: datetime


class SupportInternalNotePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    case_id: UUID
    author_user_id: UUID
    author_name: str | None = None
    body: str
    created_at: datetime


class SupportAttachmentPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    case_id: UUID
    filename: str
    content_type: str
    size_bytes: int
    is_internal: bool
    created_at: datetime


class SupportEventPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    case_id: UUID
    event_type: str
    summary: str
    is_public: bool
    created_at: datetime
    actor_user_id: UUID | None = None


class SupportCasePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    case_number: str
    ticket_number: str | None = None
    requester_user_id: UUID | None = None
    requester_email: str | None = None
    requester_name: str | None = None
    requester_context: str = "fan"
    assignee_user_id: UUID | None = None
    subject: str
    category: str
    status: str
    priority: str
    related_order_id: UUID | None = None
    related_event_id: UUID | None = None
    related_host_id: UUID | None = None
    escalation_level: str | None = None
    help_suggestions_shown: bool = False
    deflection_meta: dict[str, Any] | None = None
    resolved_at: datetime | None = None
    closed_at: datetime | None = None
    archived_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    messages: list[SupportMessagePublic] = []
    internal_notes: list[SupportInternalNotePublic] = []
    attachments: list[SupportAttachmentPublic] = []
    events: list[SupportEventPublic] = []
    public_token: str | None = None


class SupportSettingsPublic(BaseModel):
    auto_assign_enabled: bool = False
    notify_on_urgent: bool = True
    public_form_enabled: bool = True
    default_priority: str = "normal"
