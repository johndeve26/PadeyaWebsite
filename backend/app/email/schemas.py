"""Email API schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EmailPreferencesPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    email_ticket_updates: bool
    email_merch_updates: bool
    email_event_reminders: bool
    email_messages: bool
    email_fan_connect: bool
    email_sponsor_updates: bool
    email_host_activity: bool
    email_marketing: bool
    email_security: bool = True
    unsubscribed_marketing_at: datetime | None = None


class EmailPreferencesUpdate(BaseModel):
    email_ticket_updates: bool | None = None
    email_merch_updates: bool | None = None
    email_event_reminders: bool | None = None
    email_messages: bool | None = None
    email_fan_connect: bool | None = None
    email_sponsor_updates: bool | None = None
    email_host_activity: bool | None = None
    email_marketing: bool | None = None
    # Ignored if false — security cannot be disabled
    email_security: bool | None = None


class UnsubscribeRequest(BaseModel):
    token: str
    marketing_only: bool = True


class EmailEventPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    template: str
    recipient_email: str
    recipient_user_id: UUID | None
    subject: str
    status: str
    provider: str | None
    provider_message_id: str | None
    error_message: str | None
    attempts: int
    last_attempt_at: datetime | None
    sent_at: datetime | None
    dedupe_key: str | None
    preference_key: str | None
    created_at: datetime
    updated_at: datetime
    # Body only when admin + (dev or explicit allow)
    body_text: str | None = None
    body_html: str | None = None


class EmailEventListResponse(BaseModel):
    items: list[EmailEventPublic]
    total: int


class ResendResponse(BaseModel):
    id: UUID
    status: str
    message: str = Field(default="Queued for resend")


class EnqueueResult(BaseModel):
    id: UUID | None = None
    status: str
    skipped_reason: str | None = None


class EmailProviderSettingsPublic(BaseModel):
    """Masked admin view of email/SMTP settings — never includes secrets."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    provider: str
    is_active: bool = True
    email_enabled: bool
    dev_mode: bool = False
    smtp_host: str | None = None
    smtp_port: int | None = None
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False
    smtp_from_email: str | None = None
    smtp_from_name: str | None = None
    smtp_reply_to: str | None = None
    smtp_username_masked: str | None = None
    smtp_username_last4: str | None = None
    smtp_password_configured: bool = False
    smtp_password_last4: str | None = None
    smtp_password_hint: str | None = None
    last_test_status: str | None = None
    last_test_error: str | None = None
    last_test_at: datetime | None = None
    last_successful_send_at: datetime | None = None
    pending_emails_count: int = 0
    failed_emails_count: int = 0
    created_by_user_id: UUID | None = None
    updated_by_user_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
    source: str = "admin_db"


class EmailProviderSettingsUpdate(BaseModel):
    provider: str | None = None
    email_enabled: bool | None = None
    # Legacy alias
    enabled: bool | None = None
    dev_mode: bool | None = None
    smtp_host: str | None = None
    smtp_port: int | None = Field(default=None, ge=1, le=65535)
    smtp_use_tls: bool | None = None
    smtp_use_ssl: bool | None = None
    smtp_from_email: str | None = None
    smtp_from_name: str | None = None
    smtp_reply_to: str | None = None
    # Legacy aliases
    from_email: str | None = None
    from_name: str | None = None
    reply_to: str | None = None
    smtp_username: str | None = None
    # Omit or blank to keep existing password
    smtp_password: str | None = None
    clear_smtp_password: bool | None = None
    clear_smtp_username: bool | None = None


class EmailSettingsTestSendRequest(BaseModel):
    test_recipient_email: str | None = Field(default=None, min_length=3, max_length=320)
    # Legacy alias
    to: str | None = Field(default=None, min_length=3, max_length=320)


class EmailSettingsActivateRequest(BaseModel):
    settings_id: UUID | None = None


class EmailSettingsTestResponse(BaseModel):
    ok: bool
    status: str | None = None
    error: str | None = None
    provider: str | None = None
    skipped: bool | None = None
    """True only when a real SMTP (or future ESP) send succeeded."""
    delivered_to_inbox: bool | None = None
    to: str | None = None
    smtp_host: str | None = None
    smtp_port: int | None = None
    email_event_id: UUID | None = None
