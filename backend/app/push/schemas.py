"""Push API schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

# Re-export shared preference / settings schemas used by routers
from app.notifications.schemas import (  # noqa: F401
    PushDeliveryEventPublic,
    PushDeliveryListResponse,
    PushPreferencesPublic,
    PushPreferencesUpdate,
    PushProviderSettingsPublic,
    PushProviderSettingsUpdate,
    PushSubscriptionCreate,
    PushSubscriptionDelete,
    PushSubscriptionListResponse,
    PushSubscriptionPublic,
    PushTestRequest,
)


class PushEventPublic(BaseModel):
    id: UUID
    recipient_user_id: UUID
    template: str
    title: str
    body: str
    action_url: str | None = None
    status: str
    attempts: int = 0
    error_message: str | None = None
    last_attempt_at: datetime | None = None
    sent_at: datetime | None = None
    dedupe_key: str | None = None
    notification_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class PushEventListResponse(BaseModel):
    items: list[PushEventPublic]
    total: int
    summary: dict[str, int] = Field(default_factory=dict)


class PushTestByEmailRequest(BaseModel):
    """Admin test to a selected user. Copy is fixed server-side."""

    email: str | None = None
    user_id: UUID | None = None


class PushUserSubscriptionStatus(BaseModel):
    user_id: UUID
    email: str | None = None
    full_name: str | None = None
    active_subscription_count: int = 0
    has_active_device: bool = False
    devices: list[PushSubscriptionPublic] = Field(default_factory=list)
