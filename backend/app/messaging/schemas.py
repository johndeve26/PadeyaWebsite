"""Messaging API schemas — privacy-safe public shapes."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.messaging import constants as C


class BlockedUserPublic(BaseModel):
    user_id: str
    display_name: str
    username: str | None = None
    role: str = "user"
    reason: str | None = None
    created_at: datetime


class MessageSettingsPublic(BaseModel):
    allow_messages_from_hosts_i_follow: bool = True
    allow_messages_from_hosts_i_attended: bool = True
    allow_messages_from_public: bool = False
    message_requests_enabled: bool = True
    allow_messages_from_followers: bool = True
    allow_messages_from_ticket_buyers: bool = True
    allow_messages_from_public_host: bool = True
    allow_event_inquiries: bool = True
    auto_reply_enabled: bool = False
    auto_reply_message: str | None = None
    blocked_users: list[BlockedUserPublic] = Field(default_factory=list)


class MessageSettingsUpdate(BaseModel):
    allow_messages_from_hosts_i_follow: bool | None = None
    allow_messages_from_hosts_i_attended: bool | None = None
    allow_messages_from_public: bool | None = None
    message_requests_enabled: bool | None = None
    allow_messages_from_followers: bool | None = None
    allow_messages_from_ticket_buyers: bool | None = None
    allow_messages_from_public_host: bool | None = None
    allow_event_inquiries: bool | None = None
    auto_reply_enabled: bool | None = None
    auto_reply_message: str | None = Field(default=None, max_length=500)


class CreateThreadBody(BaseModel):
    host_id: UUID | None = None
    host_username: str | None = None
    fan_user_id: UUID | None = None
    fan_username: str | None = None
    related_event_id: UUID | None = None
    related_merch_order_item_id: UUID | None = None
    subject: str | None = Field(default=None, max_length=200)
    body: str = Field(min_length=1, max_length=2000)


class SendMessageBody(BaseModel):
    body: str = Field(default="", max_length=2000)
    attachment_ids: list[UUID] = Field(default_factory=list)
    reply_to_message_id: UUID | None = None

    @model_validator(mode="after")
    def require_body_or_attachments(self) -> SendMessageBody:
        from app.messaging.attachments import get_attachment_limits

        text = (self.body or "").strip()
        ids = list(self.attachment_ids or [])
        max_count = get_attachment_limits().max_count
        if len(ids) > max_count:
            raise ValueError(f"At most {max_count} attachments allowed.")
        if not text and not ids:
            raise ValueError("Message body or attachments required.")
        self.body = text
        self.attachment_ids = ids
        return self


class EditMessageBody(BaseModel):
    body: str = Field(min_length=1, max_length=2000)

    @model_validator(mode="after")
    def strip_body(self) -> EditMessageBody:
        text = (self.body or "").strip()
        if not text:
            raise ValueError("Message body cannot be empty.")
        if len(text) > C.MAX_BODY_LENGTH:
            raise ValueError("Invalid message body.")
        self.body = text
        return self


class MessageAttachmentPublic(BaseModel):
    """Allowlisted attachment metadata only (no storage keys / paths / checksums)."""

    id: str
    url: str | None = None
    content_type: str  # mime_type
    byte_size: int  # file_size
    original_filename: str | None = None
    width: int | None = None
    height: int | None = None
    status: str = "ready"
    reviewed_at: str | None = None


class AttachmentUploadPublic(BaseModel):
    """Uploader staging / admin moderation response — allowlisted fields only."""

    id: str
    url: str | None = None
    content_type: str
    byte_size: int
    original_filename: str | None = None
    width: int | None = None
    height: int | None = None
    status: str = "ready"
    reviewed_at: str | None = None


class BlockUserBody(BaseModel):
    blocked_user_id: UUID
    reason: str | None = Field(default=None, max_length=300)


class ReportThreadBody(BaseModel):
    reason: str = Field(min_length=3, max_length=120)
    details: str | None = Field(default=None, max_length=2000)
    message_id: UUID | None = None


class AcceptRequestBody(BaseModel):
    accept: bool = True


class ReplyToPublic(BaseModel):
    """Safe quote preview — no emails, phones, storage keys, or private URLs."""

    reply_message_id: str
    reply_author_display_name: str = ""
    reply_body_preview: str | None = None
    reply_attachment_preview: str | None = None
    reply_created_at: datetime | None = None
    reply_is_unavailable: bool = False


class MessagePublic(BaseModel):
    id: str
    thread_id: str
    sender_role: str
    sender_display_name: str
    body: str
    message_type: str
    status: str
    moderation_status: str
    created_at: datetime
    is_mine: bool
    attachments: list[MessageAttachmentPublic] = Field(default_factory=list)
    edited_at: datetime | None = None
    reply_to: ReplyToPublic | None = None
    is_pinned: bool = False
    is_starred: bool = False
    deleted_for_me: bool = False


class DeleteMessageBody(BaseModel):
    """v1: only `for_me` is accepted. `for_everyone` is not product-approved."""

    scope: str = "for_me"


class PinnedListPublic(BaseModel):
    items: list[MessagePublic] = Field(default_factory=list)
    total: int = 0


class ThreadSearchFiltersPublic(BaseModel):
    starred: bool = False
    pinned: bool = False
    has_attachments: bool = False


class ThreadSearchPublic(BaseModel):
    items: list[MessagePublic] = Field(default_factory=list)
    total: int = 0
    q: str = ""
    filters: ThreadSearchFiltersPublic = Field(
        default_factory=ThreadSearchFiltersPublic
    )


class RelatedEventChip(BaseModel):
    id: str
    title: str
    slug: str
    path: str
    banner_url: str | None = None


class ParticipantPublic(BaseModel):
    display_name: str
    username: str | None = None
    role: str
    legacy_path: str | None = None
    passport_path: str | None = None
    avatar_url: str | None = None
    gender: str | None = None
    gender_short: str | None = None
    gender_label: str | None = None
    gender_visible: bool = False


class StarredMessagePublic(BaseModel):
    message: MessagePublic
    thread_id: str
    thread_type: str = "fan_host"
    counterpart: ParticipantPublic
    starred_at: datetime


class StarredListPublic(BaseModel):
    items: list[StarredMessagePublic] = []
    page: int = 1
    limit: int = 30
    total: int = 0


class ConnectContextPublic(BaseModel):
    badge: str = "Fan Connect"
    context_label: str
    reasons: list[dict] = []


class ThreadListItemPublic(BaseModel):
    id: str
    status: str
    subject: str | None = None
    last_message_preview: str | None = None
    last_message_at: datetime | None = None
    unread: bool = False
    is_request: bool = False
    archived: bool = False
    blocked: bool = False
    related_event: RelatedEventChip | None = None
    counterpart: ParticipantPublic
    thread_type: str = "fan_host"
    connect_context: ConnectContextPublic | None = None
    created_at: datetime


class ThreadListPublic(BaseModel):
    items: list[ThreadListItemPublic] = []
    page: int = 1
    limit: int = 30
    total: int = 0
    unread_count: int = 0


class ThreadDetailPublic(BaseModel):
    id: str
    status: str
    subject: str | None = None
    is_request: bool = False
    can_reply: bool = True
    can_attach: bool = False
    blocked: bool = False
    archived: bool = False
    counterpart_user_id: str | None = None
    related_event: RelatedEventChip | None = None
    counterpart: ParticipantPublic
    thread_type: str = "fan_host"
    connect_context: ConnectContextPublic | None = None
    messages: list[MessagePublic] = []
    pinned_messages: list[MessagePublic] = Field(default_factory=list)
    privacy_reminder: str = (
        "Keep this conversation on Pàdéyá. Do not share phone numbers, emails, "
        "WhatsApp, bank details, or payment links. Report fraud or anything "
        "suspicious from this conversation."
    )
    peer_read_at: datetime | None = None
    created_at: datetime


class UnreadCountPublic(BaseModel):
    unread_count: int


class AdminReportListItem(BaseModel):
    id: str
    thread_id: str
    reason: str
    status: str
    reporter_display_name: str
    reported_display_name: str
    host_display_name: str | None = None
    thread_type: str | None = None
    created_at: datetime
    message_preview: str | None = None


class AdminReportListPublic(BaseModel):
    items: list[AdminReportListItem] = []
    page: int = 1
    limit: int = 40
    total: int = 0


class AdminReportDetailPublic(BaseModel):
    id: str
    thread_id: str
    reason: str
    details: str | None = None
    status: str
    admin_notes: str | None = None
    reporter_display_name: str
    reported_display_name: str
    host_display_name: str | None = None
    thread_type: str | None = None
    connect_context: dict | None = None
    messages: list[MessagePublic] = []
    created_at: datetime
    # Intentionally omit emails, phones, orders, payments


class AdminReportPatch(BaseModel):
    status: str | None = None
    admin_notes: str | None = Field(default=None, max_length=2000)


class NotificationPublic(BaseModel):
    id: str
    kind: str
    title: str
    body: str
    link_path: str | None = None
    read_at: datetime | None = None
    created_at: datetime


class NotificationListPublic(BaseModel):
    items: list[NotificationPublic] = []
