"""Rules-only sponsor campaign ↔ opportunity matching (no AI)."""

SCORE_MAX = 100
SCORE_MIN_SHOW = 25
RECOMMENDATIONS_CAP = 24
DISMISS_COOLDOWN_DAYS = 60

MAX_CATEGORY = 30
MAX_LOCATION = 20
MAX_BUDGET = 20
MAX_TRUST = 15
MAX_TIMING = 10
MAX_FEEDBACK = 10

REASON_CATEGORY = "category_fit"
REASON_LOCATION = "location_fit"
REASON_BUDGET = "budget_fit"
REASON_VERIFIED = "verified_host"
REASON_ACTIVITY = "strong_event_activity"
REASON_UPCOMING = "upcoming_event"
REASON_SAVED = "similar_saved"

REASON_LABELS: dict[str, str] = {
    REASON_CATEGORY: "Matches your campaign category",
    REASON_LOCATION: "Fits your target location",
    REASON_BUDGET: "Within your budget range",
    REASON_VERIFIED: "Verified host",
    REASON_ACTIVITY: "Strong event activity",
    REASON_UPCOMING: "Upcoming event opportunity",
    REASON_SAVED: "Similar to saved opportunities",
}

FEEDBACK_SAVED = "saved"
FEEDBACK_CLICKED = "clicked"
FEEDBACK_DISMISSED = "dismissed"
FEEDBACK_NOT_INTERESTED = "not_interested"
FEEDBACK_MORE_LIKE_THIS = "more_like_this"
FEEDBACK_CONTACTED = "contacted"

FEEDBACK_ACTIONS = frozenset(
    {
        FEEDBACK_SAVED,
        FEEDBACK_CLICKED,
        FEEDBACK_DISMISSED,
        FEEDBACK_NOT_INTERESTED,
        FEEDBACK_MORE_LIKE_THIS,
        FEEDBACK_CONTACTED,
    }
)

DISMISS_ACTIONS = frozenset({FEEDBACK_DISMISSED, FEEDBACK_NOT_INTERESTED})

ITEM_TYPES = frozenset({"host", "event", "sponsorship_slot"})

OBJECTIVE_CATEGORY_HINTS: dict[str, tuple[str, ...]] = {
    "brand_awareness": ("brand", "media", "lifestyle", "entertainment"),
    "product_launch": ("tech", "retail", "business", "product"),
    "event_activation": ("events", "nightlife", "experiences", "music"),
    "lead_generation": ("business", "professional", "tech"),
    "community_engagement": ("community", "culture", "social"),
    "campus_activation": ("campus", "education", "student"),
    "merch_collaboration": ("fashion", "retail", "merch"),
    "media_partnership": ("media", "creator", "entertainment"),
    "other": (),
}
