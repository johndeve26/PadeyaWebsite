"""Email outbox, provider settings, and notification preference models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON, Uuid

from app.core.database import Base


class EmailEvent(Base):
    """Queued transactional email — never hard-delete; status is the lifecycle."""

    __tablename__ = "email_events"
    __table_args__ = (
        UniqueConstraint(
            "dedupe_key",
            name="uq_email_events_dedupe_key",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    template: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    recipient_email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    recipient_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending", index=True
    )
    provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    context_json: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dedupe_key: Mapped[str | None] = mapped_column(String(200), nullable=True)
    preference_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class EmailProviderSettings(Base):
    """Admin-managed email provider / SMTP settings.

    Sensitive fields use Fernet (`smtp_*_encrypted`). Prefer deactivate over
    hard-delete. Only one row should be ``is_active`` at a time.
    """

    __tablename__ = "email_provider_settings"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="log")
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, index=True
    )
    email_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # When true, real SMTP/API providers are never used (log-only)
    dev_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    smtp_host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    smtp_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    smtp_use_tls: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    smtp_use_ssl: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    smtp_username_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    smtp_password_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    smtp_from_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    smtp_from_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    smtp_reply_to: Mapped[str | None] = mapped_column(String(320), nullable=True)

    smtp_username_last4: Mapped[str | None] = mapped_column(String(8), nullable=True)
    smtp_username_first4: Mapped[str | None] = mapped_column(String(8), nullable=True)
    smtp_password_last4: Mapped[str | None] = mapped_column(String(8), nullable=True)
    smtp_password_first4: Mapped[str | None] = mapped_column(String(8), nullable=True)

    last_test_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_test_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_test_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_successful_send_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class EmailAdminTemplate(Base):
    """Admin-editable overrides for platform admin notification emails."""

    __tablename__ = "email_admin_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    key: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    category: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    preview_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    html_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    text_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    variables_schema: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False, default=list
    )
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_enabled: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    default_recipient_group: Mapped[str] = mapped_column(String(32), nullable=False)
    recipient_mode: Mapped[str] = mapped_column(String(24), nullable=False, default="group")
    recipient_group: Mapped[str | None] = mapped_column(String(32), nullable=True)
    custom_recipient_emails: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False, default=list
    )
    delivery_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="instant")
    threshold_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    updated_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class EmailAdminNotificationSettings(Base):
    """Global admin notification email settings (digest, master switch)."""

    __tablename__ = "email_admin_notification_settings"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    master_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    digest_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    digest_hour_utc: Mapped[int] = mapped_column(Integer, nullable=False, default=8)
    updated_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UserEmailPreferences(Base):
    """Per-user email notification preferences."""

    __tablename__ = "user_email_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_user_email_preferences_user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email_ticket_updates: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_merch_updates: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_event_reminders: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_messages: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_fan_connect: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_sponsor_updates: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_host_activity: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_marketing: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_security: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Browser push preferences (channel separate from email; all categories on by default)
    push_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    push_ticket_updates: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    push_merch_updates: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    push_event_reminders: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    push_messages: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    push_message_previews: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    push_fan_connect: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    push_sponsor_updates: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    push_host_activity: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    push_reviews: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    push_marketing: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    push_security: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    unsubscribed_marketing_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
