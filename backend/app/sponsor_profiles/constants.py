"""Sponsor profile workspace constants."""

SPONSOR_TYPES = frozenset(
    {
        "brand",
        "business",
        "agency",
        "creator",
        "media_partner",
        "community",
        "ngo",
        "government",
        "other",
    }
)

SPONSOR_STATUSES = frozenset(
    {"active", "under_review", "restricted", "suspended", "archived"}
)

VERIFICATION_STATUSES = frozenset(
    {"unverified", "pending", "verified", "rejected"}
)

VISIBILITY_VALUES = frozenset({"public", "unlisted", "private"})

ONBOARDING_STATUSES = frozenset({"draft", "pending", "active", "legacy"})

SPONSOR_TEAM_ROLES = frozenset({"owner", "admin", "campaign_manager", "viewer"})

SAVED_ITEM_TYPES = frozenset({"host", "event", "sponsorship_slot"})

CAMPAIGN_OBJECTIVES = frozenset(
    {
        "brand_awareness",
        "product_launch",
        "event_activation",
        "lead_generation",
        "community_engagement",
        "campus_activation",
        "merch_collaboration",
        "media_partnership",
        "other",
    }
)

CAMPAIGN_STATUSES = frozenset(
    {
        "draft",
        "active",
        "paused",
        "completed",
        "archived",
        "under_review",
        "rejected",
    }
)

CAMPAIGN_VISIBILITY = frozenset(
    {"private", "shared_with_hosts", "public_case_study"}
)

CAMPAIGN_MODERATION_STATUSES = frozenset(
    {"not_required", "pending", "approved", "rejected"}
)

VISIBILITY_REQUIRES_MODERATION = frozenset({"public_case_study"})

SPONSOR_TEAM_INVITE_ROLES = frozenset({"admin", "campaign_manager", "viewer"})

SPONSOR_TEAM_PERMISSIONS = frozenset(
    {
        "sponsors.view_own",
        "sponsors.edit_own",
        "sponsors.manage_team",
        "sponsors.manage_campaigns",
        "sponsors.view_inquiries",
        "sponsors.save_items",
    }
)

DEFAULT_ROLE_PERMISSIONS: dict[str, dict[str, bool]] = {
    "owner": {k: True for k in SPONSOR_TEAM_PERMISSIONS},
    "admin": {
        "sponsors.view_own": True,
        "sponsors.edit_own": True,
        "sponsors.manage_team": True,
        "sponsors.manage_campaigns": True,
        "sponsors.view_inquiries": True,
        "sponsors.save_items": True,
    },
    "campaign_manager": {
        "sponsors.view_own": True,
        "sponsors.edit_own": False,
        "sponsors.manage_team": False,
        "sponsors.manage_campaigns": True,
        "sponsors.view_inquiries": True,
        "sponsors.save_items": True,
    },
    "viewer": {
        "sponsors.view_own": True,
        "sponsors.edit_own": False,
        "sponsors.manage_team": False,
        "sponsors.manage_campaigns": False,
        "sponsors.view_inquiries": True,
        "sponsors.save_items": False,
    },
}
