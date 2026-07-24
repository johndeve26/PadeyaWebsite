"""Notification API schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class InAppNotificationPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    kind: str
    title: str
    body: str
    link_path: str | None = None
    thread_id: UUID | None = None
    read_at: datetime | None = None
    archived_at: datetime | None = None
    popup_shown_at: datetime | None = None
    created_at: datetime


class NotificationListResponse(BaseModel):
    items: list[InAppNotificationPublic]
    total: int
    unread_count: int = 0


class PopupMarkRequest(BaseModel):
    notification_ids: list[UUID] = Field(default_factory=list)


class PushSubscriptionCreate(BaseModel):
    endpoint: str
    p256dh: str
    auth: str
    user_agent: str | None = None
    device_label: str | None = None
    platform: str | None = None


class PushSubscriptionDelete(BaseModel):
    endpoint: str | None = None
    subscription_id: UUID | None = None


class PushSubscriptionPublic(BaseModel):
    id: UUID
    device_label: str | None = None
    platform: str | None = None
    user_agent: str | None = None
    endpoint_hint: str | None = None
    is_active: bool = True
    revoked_at: datetime | None = None
    last_success_at: datetime | None = None
    last_failure_at: datetime | None = None
    failure_count: int = 0
    created_at: datetime
    updated_at: datetime


class PushSubscriptionListResponse(BaseModel):
    items: list[PushSubscriptionPublic]
    total: int


class PushPreferencesPublic(BaseModel):
    push_enabled: bool = False
    push_ticket_updates: bool = True
    push_merch_updates: bool = True
    push_event_reminders: bool = True
    push_messages: bool = False
    push_message_previews: bool = False
    push_fan_connect: bool = False
    push_sponsor_updates: bool = True
    push_host_activity: bool = True
    push_reviews: bool = True
    push_marketing: bool = False
    push_security: bool = True


class PushPreferencesUpdate(BaseModel):
    push_enabled: bool | None = None
    push_ticket_updates: bool | None = None
    push_merch_updates: bool | None = None
    push_event_reminders: bool | None = None
    push_messages: bool | None = None
    push_message_previews: bool | None = None
    push_fan_connect: bool | None = None
    push_sponsor_updates: bool | None = None
    push_host_activity: bool | None = None
    push_reviews: bool | None = None
    push_marketing: bool | None = None
    push_security: bool | None = None


class PushProviderSettingsPublic(BaseModel):
    id: UUID
    is_active: bool
    push_enabled: bool
    provider: str = "log"
    vapid_public_key: str | None = None
    vapid_subject: str | None = None
    vapid_private_configured: bool = False
    vapid_private_hint: str | None = None
    last_test_status: str | None = None
    last_test_error: str | None = None
    last_test_at: datetime | None = None
    created_by_user_id: UUID | None = None
    updated_by_user_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class PushProviderSettingsUpdate(BaseModel):
    push_enabled: bool | None = None
    provider: str | None = None
    vapid_public_key: str | None = None
    vapid_private_key: str | None = None
    vapid_subject: str | None = None
    generate_vapid_keys: bool | None = None


class PushTestRequest(BaseModel):
    """Admin self-test. Copy is fixed server-side; body may be empty."""

    model_config = {"extra": "ignore"}


class PushDeliveryEventPublic(BaseModel):
    id: UUID
    user_id: UUID | None = None
    subscription_id: UUID | None = None
    notification_id: UUID | None = None
    kind: str
    status: str
    error_message: str | None = None
    created_at: datetime
    sent_at: datetime | None = None


class PushDeliveryListResponse(BaseModel):
    items: list[PushDeliveryEventPublic]
    total: int
    summary: dict[str, int] = Field(default_factory=dict)
