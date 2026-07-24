"""Sponsorship deliverable lifecycle constants."""

DELIVERABLE_TYPES = frozenset(
    {
        "logo_placement",
        "stage_mention",
        "booth_space",
        "social_post",
        "email_feature",
        "push_feature",
        "merch_collab",
        "banner_ad",
        "product_sampling",
        "custom",
    }
)

DELIVERABLE_STATUSES = frozenset(
    {
        "pending",
        "in_progress",
        "submitted",
        "approved",
        "rejected",
        "completed",
        "cancelled",
    }
)

HOST_EDIT_STATUSES = frozenset({"pending", "in_progress", "rejected"})
SPONSOR_REVIEW_STATUSES = frozenset({"submitted"})
TERMINAL_STATUSES = frozenset({"completed", "cancelled"})
OPEN_STATUSES = frozenset({"pending", "in_progress", "submitted", "approved", "rejected"})
