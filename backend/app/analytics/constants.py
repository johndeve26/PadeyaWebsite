"""Analytics constants, fee placeholders, and taxonomy re-exports."""

from decimal import Decimal

from app.analytics.taxonomy import (  # noqa: F401
    ACTION_TO_CONVERSION_STAGE,
    ANALYTICS_EVENT_NAMES,
    CONVERSION_STAGES,
    FORBIDDEN_CLIENT_METADATA_KEYS,
    LEGACY_ACTION_ALIASES,
    SERVER_ONLY_ACTIONS,
    TRACKED_ACTIONS,
    TRACKED_ACTION_META,
    TrackedAction,
    conversion_stage_for_action,
    funnel_group,
    is_known_tracked_action,
    is_server_only_action,
    normalize_tracked_action,
    require_known_tracked_action,
    trust_level,
)

# Placeholder until fee take-rate is productized in finance.
PLATFORM_FEE_RATE = Decimal("0.00")

OWNED_TICKET_STATUSES = ("active", "checked_in")
ATTENDED_TICKET_STATUSES = ("checked_in",)
NO_SHOW_TICKET_STATUSES = ("active",)

DEFAULT_RANGE_DAYS = 90
MAX_EXPORT_ROWS = 5000
