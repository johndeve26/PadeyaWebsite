"""Vault content and access enumerations."""

CONTENT_TYPES = (
    "text_post",
    "image_gallery",
    "video",
    "audio",
    "file_download",
    "early_access",
    "discount_drop",
    "ticket_holder_recap",
    "vip_content",
    "external_link",
    "announcement",
)

# Accepted on read/update for items created before content-type rename.
CONTENT_TYPE_ALIASES = {
    "file": "file_download",
    "livestream_replay": "ticket_holder_recap",
}

ACCESS_TYPES = (
    "free",
    "followers_only",
    "ticket_holder_only",
    "checked_in_attendee_only",
    "vip_ticket_holder_only",
    "one_time_unlock",
    "invite_only",
    "admin_hidden",
)

ITEM_STATUSES = (
    "draft",
    "published",
    "scheduled",
    "expired",
    "archived",
    "hidden_by_admin",
)
# Legacy stored values → canonical ITEM_STATUSES
LEGACY_ITEM_STATUS_MAP = {
    "disabled": "archived",
    "flagged": "draft",
}
HOST_CREATE_STATUSES = ("draft", "published", "scheduled")
HOST_UPDATE_STATUSES = ("draft", "published", "scheduled", "archived")
MODERATION_ACTIONS = (
    "flag",
    "approve",
    "hide",
    "archive",
    "remove",
    "restore",
    "disable",
)
# Actions that require a non-empty moderation reason
MODERATION_ACTIONS_REQUIRE_NOTE = frozenset(
    {"hide", "archive", "remove", "restore"}
)
MODERATION_STATUSES = ("none", "flagged", "approved", "removed")
PURCHASE_STATUSES = ("pending", "paid", "failed", "refunded")


def normalize_content_type(value: str) -> str:
    return CONTENT_TYPE_ALIASES.get(value, value)
