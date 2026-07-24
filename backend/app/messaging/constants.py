"""Messaging constants and limits."""

from app.messaging.attachments import ALLOWED_CONTENT_TYPES, get_attachment_limits

THREAD_TYPE_FAN_HOST = "fan_host"
THREAD_TYPE_FAN_FAN = "fan_fan"

# Exact API copy when a user tries to message themselves (fan↔fan or direct).
SELF_MESSAGE_DETAIL = "You can’t message yourself."
# Shared with Fan Connect — keep identical.
SELF_BLOCK_DETAIL = "You can’t block yourself."
SELF_REPORT_DETAIL = "You can’t report yourself."

THREAD_STATUS_ACTIVE = "active"
THREAD_STATUS_REQUEST = "request"
THREAD_STATUS_ARCHIVED = "archived"
THREAD_STATUS_BLOCKED = "blocked"
THREAD_STATUS_REPORTED = "reported"
THREAD_STATUS_CLOSED = "closed"

MESSAGE_TYPE_TEXT = "text"
MESSAGE_TYPE_SYSTEM = "system"
MESSAGE_TYPE_IMAGE = "image"
MESSAGE_TYPE_ATTACHMENT = "attachment"

# Chat attachments — validated in messaging/attachments.py (no SVG/HTML/ZIP/exec).
CHAT_ALLOWED_CONTENT_TYPES = ALLOWED_CONTENT_TYPES


def max_attachments_per_message() -> int:
    return get_attachment_limits().max_count


# Default; runtime limit comes from settings via max_attachments_per_message().
MAX_ATTACHMENTS_PER_MESSAGE = 4
ATTACHMENT_PREVIEW_LABEL = "Sent an attachment"

MESSAGE_STATUS_SENT = "sent"
MESSAGE_STATUS_DELIVERED = "delivered"
MESSAGE_STATUS_HIDDEN = "hidden"
MESSAGE_STATUS_DELETED = "deleted"

# Per-viewer soft delete (row kept for moderation/audit).
DELETE_SCOPE_FOR_ME = "for_me"
# Reserved — not exposed until product-approved.
DELETE_SCOPE_FOR_EVERYONE = "for_everyone"
DELETED_FOR_ME_BODY = "Message deleted"

MOD_CLEAN = "clean"
MOD_FLAGGED = "flagged"
MOD_HIDDEN = "hidden"

SENDER_FAN = "fan"
SENDER_HOST = "host"
SENDER_SUPPORT = "support"
SENDER_ADMIN = "admin"

REPORT_OPEN = "open"
REPORT_REVIEWING = "reviewing"
REPORT_RESOLVED = "resolved"
REPORT_DISMISSED = "dismissed"

MAX_BODY_LENGTH = 2000
MAX_PINS_PER_THREAD = 3
MESSAGE_EDIT_WINDOW_HOURS = 24
THREAD_CREATE_PER_HOUR = 8
MESSAGES_PER_MINUTE = 20

# Soft-flag phrases (review, do not auto-block normal talk)
CONTACT_PRESSURE_PATTERNS = (
    "whatsapp",
    "wa.me",
    "telegram",
    "call me",
    "my number is",
    "my phone is",
    "text me at",
    "email me",
    "send money",
    "bank transfer",
    "bank details",
    "account number",
    "wire me",
    "paystack",
    "payment link",
    "outside padeya",
    "move to whatsapp",
)

PRIVACY_REMINDER = (
    "Keep this conversation on Pàdéyá. Do not share phone numbers, emails, "
    "WhatsApp, bank details, or payment links. Report fraud or anything "
    "suspicious from this conversation."
)

FAN_CONNECT_BADGE = "Fan Connect"
FAN_CONNECT_SYSTEM_PREFIX = "You connected through "
