"""Event and ticket type enumerations."""

import re

EVENT_STATUSES = (
    "draft",
    "published",
    "paused",
    "completed",
    "cancelled",
    "rejected",
    "archived",
)

EVENT_TYPES = (
    "public",
    "private",
    "invite_only",
    "secret_location",
    "online",
    "hybrid",
)

EVENT_VISIBILITY = (
    "listed",
    "unlisted",
    "password_protected",
    "approval_required",
)

LOCATION_VISIBILITY = (
    "full_public",
    "area_only",
    "hidden_until_payment",
    "hidden_until_24h_before",
    "hidden_until_manual_approval",
    "online_only",
)

REVEAL_TIMING = (
    "immediately",
    "after_payment",
    "twenty_four_hours_before",
    "manual_approval",
    "event_day",
)

ONLINE_URL_REVEAL_RULES = (
    "immediately",
    "after_payment",
    "twenty_four_hours_before",
    "manual_approval",
    "event_day",
)

AGENDA_ITEM_TYPES = (
    "doors_open",
    "performance",
    "speaker",
    "break",
    "networking",
    "after_party",
    "other",
)

CHECKOUT_QUESTION_TYPES = (
    "short_text",
    "long_text",
    "dropdown",
    "checkbox",
    "phone",
    "email",
)

REFUND_POLICY_TYPES = (
    "no_refunds",
    "refund_until_7_days_before",
    "refund_until_24_hours_before",
    "partial_refund_only",
    "cancelled_event_only",
    "admin_controlled",
    "custom",
)

TICKET_TYPE_KINDS = (
    "free",
    "free_rsvp",
    "regular",
    "early_bird",
    "vip",
    "vvip",
    "table",
    "group",
    "invite_only",
    "hidden",
    "donation",
)

# Preset kinds stay recommended; hosts may also supply a custom slug-like type.
TICKET_TYPE_KIND_MAX_LENGTH = 32


def normalize_ticket_type_kind(value: str) -> str:
    """Accept preset or custom ticket kinds (slug-safe, max 32 chars)."""
    raw = (value or "").strip().lower().replace(" ", "_")
    cleaned = re.sub(r"[^a-z0-9_-]+", "_", raw)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_-")
    if not cleaned:
        raise ValueError("type is required")
    if len(cleaned) > TICKET_TYPE_KIND_MAX_LENGTH:
        raise ValueError(
            f"type must be at most {TICKET_TYPE_KIND_MAX_LENGTH} characters"
        )
    return cleaned

TICKET_VISIBILITY = ("public", "hidden", "invite_only")
TICKET_STATUSES = ("active", "inactive", "sold_out")
MEDIA_TYPES = (
    "banner",
    "mobile_banner",
    "gallery",
    "teaser",
    "sponsor",
    "social_share",
    "other",
)

DEFAULT_CATEGORIES: list[tuple[str, str, str]] = [
    ("Music", "music", "Concerts, festivals, and live performances"),
    ("Nightlife", "nightlife", "Clubs, parties, and late-night events"),
    ("Comedy", "comedy", "Stand-up and sketch shows"),
    ("Arts & Culture", "arts-culture", "Theatre, exhibitions, and cultural nights"),
    ("Sports & Fitness", "sports-fitness", "Games, tournaments, and fitness events"),
    ("Business", "business", "Conferences, networking, and workshops"),
    ("Community", "community", "Local gatherings and meetups"),
    ("Tech", "tech", "Product demos, meetups, and founder sessions"),
    ("Gospel", "gospel", "Worship nights and faith gatherings"),
    ("Conference", "conference", "Multi-session conferences and summits"),
    ("Food & Drink", "food-drink", "Food festivals and tasting events"),
    ("Campus", "campus", "Student and campus community events"),
    ("Lifestyle", "lifestyle", "Games nights, socials, and lifestyle experiences"),
    ("Sports", "sports", "Sports watch parties and tournaments"),
    ("Other", "other", "Everything else"),
]
