"""Sponsorship marketplace constants."""

SLOT_TYPES = (
    "logo_event_page",
    "logo_ticket_email",
    "banner_legacy_page",
    "booth_at_event",
    "sponsored_vault_content",
    "sponsored_memory_page",
)

SLOT_STATUSES = ("draft", "published", "disabled")
MODERATION_STATUSES = ("none", "flagged", "approved", "removed")
INQUIRY_STATUSES = ("new", "reviewing", "accepted", "declined", "closed")
PLACEMENT_STATUSES = ("planned", "active", "completed", "cancelled")
SPONSOR_STATUSES = ("active", "disabled")

SLOT_TYPE_LABELS: dict[str, str] = {
    "logo_event_page": "Logo on event page",
    "logo_ticket_email": "Logo on ticket email",
    "banner_legacy_page": "Banner on Legacy Page",
    "booth_at_event": "Booth at event",
    "sponsored_vault_content": "Sponsored Vault content",
    "sponsored_memory_page": "Sponsored event memory page",
}
