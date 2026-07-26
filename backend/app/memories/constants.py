"""Event Memories constants."""

MEMORY_STATUSES = ("draft", "published", "hidden")
MEMORY_MODERATION_STATUSES = ("none", "flagged", "approved", "removed")

MEMORY_PHOTO_STATUSES = ("active", "hidden", "removed")
MEMORY_UPLOADER_ROLES = ("host", "fan")
MEMORY_HIDDEN_BY = ("host", "admin")

EXTERNAL_GALLERY_LABELS = (
    "instagram",
    "google_drive",
    "official",
    "other",
)

# Tickets that count toward verified sold / attendance stats
OWNED_TICKET_STATUSES = ("active", "checked_in")
ATTENDED_TICKET_STATUSES = ("checked_in",)

# Fan/host photo contribution eligibility
ELIGIBLE_TICKET_STATUSES = ("active", "checked_in")
ELIGIBLE_EVENT_STATUSES = ("published", "paused", "completed")

HOST_MEMORY_PHOTO_LIMIT = 10
FAN_MEMORY_PHOTO_LIMIT = 5

TOP_REVIEWS_LIMIT = 5

# SEO: album pages with at least this many active photos may be indexed
SEO_MIN_ACTIVE_PHOTOS = 1
