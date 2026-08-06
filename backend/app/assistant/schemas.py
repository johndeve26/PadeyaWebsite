"""Pydantic schemas for the Pàdéyá conversational assistant."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PageContext(BaseModel):
    """Safe page context — never include secrets, tokens, emails, or PII."""

    model_config = ConfigDict(extra="ignore")

    route_key: str | None = None
    page_title: str | None = None
    role: str | None = None
    entity_public_id: str | None = None
    active_tab: str | None = None
    ui_errors: list[str] = Field(default_factory=list)
    feature_flags: dict[str, bool] = Field(default_factory=dict)
    available_actions: list[str] = Field(default_factory=list)


class ChatStreamRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    message: str = Field(min_length=1, max_length=4000)
    session_id: UUID | None = None
    page_context: PageContext | dict[str, Any] | None = None
    timezone: str | None = Field(default=None, max_length=64)


class Citation(BaseModel):
    title: str
    url: str
    snippet: str | None = None
    source_type: str | None = None
    route_key: str | None = None


class Card(BaseModel):
    type: str
    title: str
    subtitle: str | None = None
    url: str | None = None
    image_url: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class Action(BaseModel):
    type: str
    label: str
    route_key: str | None = None
    url: str | None = None
    tool_name: str | None = None
    confirmation_id: UUID | None = None
    requires_confirmation: bool = False
    meta: dict[str, Any] = Field(default_factory=dict)


class AssistantResponse(BaseModel):
    """Non-stream envelope fields shared with SSE `done` payload."""

    session_id: UUID
    message_id: UUID | None = None
    mode: str
    product_name: str
    text: str = ""
    citations: list[Citation] = Field(default_factory=list)
    cards: list[Card] = Field(default_factory=list)
    actions: list[Action] = Field(default_factory=list)
    safety_status: str | None = None
    used_fallback: bool = False
    provider: str | None = None
    model: str | None = None
    intent: str | None = None
    confirmation_id: UUID | None = None
    trace_id: str | None = None


class FeedbackCreate(BaseModel):
    session_id: UUID
    message_id: UUID
    rating: Literal["up", "down", "helpful", "not_helpful"]
    reason: str | None = Field(default=None, max_length=120)
    comment: str | None = Field(default=None, max_length=2000)


class ConfirmAction(BaseModel):
    idempotency_key: str | None = Field(default=None, max_length=128)


class SessionPublic(BaseModel):
    id: UUID
    mode: str
    title: str | None = None
    active_role: str | None = None
    expires_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class MessagePublic(BaseModel):
    id: UUID
    role: str
    content: str
    structured_content_json: dict[str, Any] | None = None
    safety_status: str | None = None
    created_at: datetime


class SessionDetailPublic(SessionPublic):
    messages: list[MessagePublic] = Field(default_factory=list)


class KnowledgeSyncReport(BaseModel):
    started_at: datetime
    finished_at: datetime | None = None
    urls_seen: int = 0
    documents_created: int = 0
    documents_updated: int = 0
    documents_unchanged: int = 0
    documents_archived: int = 0
    documents_failed: int = 0
    chunks_upserted: int = 0
    errors: list[str] = Field(default_factory=list)


class KnowledgeStatus(BaseModel):
    enabled: bool
    document_count: int = 0
    active_count: int = 0
    archived_count: int = 0
    failed_count: int = 0
    chunk_count: int = 0
    last_indexed_at: datetime | None = None
    sitemap_url: str | None = None


class AssistantStatusPublic(BaseModel):
    assistant_enabled: bool = False
    public_enabled: bool = False
    authenticated_enabled: bool = False
    actions_enabled: bool = False
    event_search_enabled: bool = False
    product_public: str = "Ask Pàdéyá"
    product_authenticated: str = "Pàdéyá Copilot"
    ai_feature_enabled: bool = False
    ai_provider_ready: bool = False
