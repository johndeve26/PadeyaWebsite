"""Account status + selective restriction catalog (source of truth for codes)."""

from __future__ import annotations

ACCOUNT_STATUS_ACTIVE = "active"
ACCOUNT_STATUS_UNDER_REVIEW = "under_review"
ACCOUNT_STATUS_RESTRICTED = "restricted"
ACCOUNT_STATUS_SUSPENDED = "suspended"
ACCOUNT_STATUS_BANNED = "banned"
ACCOUNT_STATUS_DELETED = "deleted"

ACCOUNT_STATUSES = frozenset(
    {
        ACCOUNT_STATUS_ACTIVE,
        ACCOUNT_STATUS_UNDER_REVIEW,
        ACCOUNT_STATUS_RESTRICTED,
        ACCOUNT_STATUS_SUSPENDED,
        ACCOUNT_STATUS_BANNED,
        ACCOUNT_STATUS_DELETED,
    }
)

# Writable transitions: restricted + banned included; suspend remains login block.
ALLOWED_STATUS_TRANSITIONS: frozenset[tuple[str, str]] = frozenset(
    {
        # Soft / partial among themselves
        (ACCOUNT_STATUS_ACTIVE, ACCOUNT_STATUS_UNDER_REVIEW),
        (ACCOUNT_STATUS_ACTIVE, ACCOUNT_STATUS_RESTRICTED),
        (ACCOUNT_STATUS_UNDER_REVIEW, ACCOUNT_STATUS_ACTIVE),
        (ACCOUNT_STATUS_UNDER_REVIEW, ACCOUNT_STATUS_RESTRICTED),
        (ACCOUNT_STATUS_RESTRICTED, ACCOUNT_STATUS_ACTIVE),
        (ACCOUNT_STATUS_RESTRICTED, ACCOUNT_STATUS_UNDER_REVIEW),
        # Global blocks
        (ACCOUNT_STATUS_ACTIVE, ACCOUNT_STATUS_SUSPENDED),
        (ACCOUNT_STATUS_ACTIVE, ACCOUNT_STATUS_BANNED),
        (ACCOUNT_STATUS_UNDER_REVIEW, ACCOUNT_STATUS_SUSPENDED),
        (ACCOUNT_STATUS_UNDER_REVIEW, ACCOUNT_STATUS_BANNED),
        (ACCOUNT_STATUS_RESTRICTED, ACCOUNT_STATUS_SUSPENDED),
        (ACCOUNT_STATUS_RESTRICTED, ACCOUNT_STATUS_BANNED),
        # Restore
        (ACCOUNT_STATUS_SUSPENDED, ACCOUNT_STATUS_ACTIVE),
        (ACCOUNT_STATUS_BANNED, ACCOUNT_STATUS_ACTIVE),
    }
)

# --- Restriction row lifecycle (user_restrictions.status) ---
RESTRICTION_STATUS_ACTIVE = "active"
RESTRICTION_STATUS_EXPIRED = "expired"
RESTRICTION_STATUS_REVOKED = "revoked"
RESTRICTION_STATUSES = frozenset(
    {
        RESTRICTION_STATUS_ACTIVE,
        RESTRICTION_STATUS_EXPIRED,
        RESTRICTION_STATUS_REVOKED,
    }
)

# --- Catalog (exact keys) ---
ACCOUNT_RESTRICTIONS: tuple[str, ...] = (
    # Personal / buyer
    "cannot_buy_tickets",
    "cannot_buy_merch",
    "cannot_checkout",
    "cannot_transfer_tickets",
    "cannot_request_refunds",
    "cannot_submit_reviews",
    "cannot_edit_passport",
    "cannot_use_vault",
    # Community
    "cannot_message",
    "cannot_use_fan_connect",
    "cannot_follow_hosts",
    "cannot_follow_fans",
    "cannot_report_users",
    # Host
    "cannot_create_events",
    "cannot_publish_events",
    "cannot_manage_events",
    "cannot_manage_tickets",
    "cannot_scan_tickets",
    "cannot_manage_merch",
    "cannot_fulfill_merch",
    "cannot_invite_host_team",
    "cannot_manage_sponsorships",
    "cannot_manage_host_ambassadors",
    "cannot_view_host_finance",
    # Ambassador
    "cannot_join_ambassador_campaigns",
    "cannot_promote_events",
    "cannot_receive_ambassador_rewards",
    "cannot_request_ambassador_payouts",
    # Account / security
    "force_password_reset",
    "require_email_verification",
    "require_support_review",
    "read_only_account",
    # Admin / support
    "cannot_access_admin",
    "cannot_access_support_tools",
)
ACCOUNT_RESTRICTION_SET = frozenset(ACCOUNT_RESTRICTIONS)

# Legacy JSON / ambassadors_blocked sync code → current catalog key
LEGACY_RESTRICTION_ALIASES: dict[str, str] = {
    "cannot_promote_as_ambassador": "cannot_join_ambassador_campaigns",
}

AMBASSADOR_RESTRICTION_KEYS: frozenset[str] = frozenset(
    {
        "cannot_join_ambassador_campaigns",
        "cannot_promote_events",
        "cannot_receive_ambassador_rewards",
        "cannot_request_ambassador_payouts",
    }
)

# Grouped for Admin UI / docs parity (exported for FE)
ACCOUNT_RESTRICTION_GROUPS: dict[str, tuple[str, ...]] = {
    "personal": (
        "cannot_buy_tickets",
        "cannot_buy_merch",
        "cannot_checkout",
        "cannot_transfer_tickets",
        "cannot_request_refunds",
        "cannot_submit_reviews",
        "cannot_edit_passport",
        "cannot_use_vault",
    ),
    "community": (
        "cannot_message",
        "cannot_use_fan_connect",
        "cannot_follow_hosts",
        "cannot_follow_fans",
        "cannot_report_users",
    ),
    "host": (
        "cannot_create_events",
        "cannot_publish_events",
        "cannot_manage_events",
        "cannot_manage_tickets",
        "cannot_scan_tickets",
        "cannot_manage_merch",
        "cannot_fulfill_merch",
        "cannot_invite_host_team",
        "cannot_manage_sponsorships",
        "cannot_manage_host_ambassadors",
        "cannot_view_host_finance",
    ),
    "ambassador": tuple(sorted(AMBASSADOR_RESTRICTION_KEYS)),
    "account": (
        "force_password_reset",
        "require_email_verification",
        "require_support_review",
        "read_only_account",
    ),
    "admin": (
        "cannot_access_admin",
        "cannot_access_support_tools",
    ),
}

ACCOUNT_RESTRICTION_LABELS: dict[str, str] = {
    "cannot_buy_tickets": "Cannot buy tickets",
    "cannot_buy_merch": "Cannot buy merch",
    "cannot_checkout": "Cannot checkout",
    "cannot_transfer_tickets": "Cannot transfer tickets",
    "cannot_request_refunds": "Cannot request refunds",
    "cannot_submit_reviews": "Cannot submit reviews",
    "cannot_edit_passport": "Cannot edit passport",
    "cannot_use_vault": "Cannot use vault",
    "cannot_message": "Cannot message",
    "cannot_use_fan_connect": "Cannot use Fan Connect",
    "cannot_follow_hosts": "Cannot follow hosts",
    "cannot_follow_fans": "Cannot follow fans",
    "cannot_report_users": "Cannot report users",
    "cannot_create_events": "Cannot create events",
    "cannot_publish_events": "Cannot publish events",
    "cannot_manage_events": "Cannot manage events",
    "cannot_manage_tickets": "Cannot manage tickets",
    "cannot_scan_tickets": "Cannot scan tickets",
    "cannot_manage_merch": "Cannot manage merch",
    "cannot_fulfill_merch": "Cannot fulfill merch",
    "cannot_invite_host_team": "Cannot invite host team",
    "cannot_manage_sponsorships": "Cannot manage sponsorships",
    "cannot_manage_host_ambassadors": "Cannot manage host ambassadors",
    "cannot_view_host_finance": "Cannot view host finance",
    "cannot_join_ambassador_campaigns": "Cannot join ambassador campaigns",
    "cannot_promote_events": "Cannot promote events",
    "cannot_receive_ambassador_rewards": "Cannot receive ambassador rewards",
    "cannot_request_ambassador_payouts": "Cannot request ambassador payouts",
    "force_password_reset": "Force password reset",
    "require_email_verification": "Require email verification",
    "require_support_review": "Require support review",
    "read_only_account": "Read-only account",
    "cannot_access_admin": "Cannot access admin",
    "cannot_access_support_tools": "Cannot access support tools",
}

ACCOUNT_RESTRICTION_GROUP_LABELS: dict[str, str] = {
    "personal": "Personal / buyer",
    "community": "Community",
    "host": "Host",
    "ambassador": "Ambassador",
    "account": "Account / security",
    "admin": "Admin / support",
}

# Admin UI presets — exported for FE/docs parity
ADMIN_RESTRICTION_PRESETS: dict[str, tuple[str, ...]] = {
    "messaging": (
        "cannot_message",
        "cannot_use_fan_connect",
    ),
    "buyer": (
        "cannot_buy_tickets",
        "cannot_buy_merch",
        "cannot_checkout",
        "cannot_transfer_tickets",
    ),
    "host": (
        "cannot_create_events",
        "cannot_publish_events",
        "cannot_manage_events",
        "cannot_scan_tickets",
        "cannot_manage_merch",
        "cannot_invite_host_team",
        "cannot_manage_sponsorships",
        "cannot_manage_host_ambassadors",
    ),
    "ambassador": (
        "cannot_join_ambassador_campaigns",
        "cannot_promote_events",
        "cannot_receive_ambassador_rewards",
        "cannot_request_ambassador_payouts",
    ),
    "read_only": ("read_only_account",),
}

# Full suspension = all major activity cannot_* + read_only_account
# (API also sets account_status=suspended when this preset is applied.)
FULL_SUSPENSION_RESTRICTIONS: tuple[str, ...] = tuple(
    code
    for code in ACCOUNT_RESTRICTIONS
    if code.startswith("cannot_") or code == "read_only_account"
)
ADMIN_RESTRICTION_PRESETS = {
    **ADMIN_RESTRICTION_PRESETS,
    "full_suspension": FULL_SUSPENSION_RESTRICTIONS,
}

ACCOUNT_STATUS_LABELS: dict[str, str] = {
    ACCOUNT_STATUS_ACTIVE: "Active",
    ACCOUNT_STATUS_UNDER_REVIEW: "Under review",
    ACCOUNT_STATUS_RESTRICTED: "Restricted",
    ACCOUNT_STATUS_SUSPENDED: "Suspended",
    ACCOUNT_STATUS_BANNED: "Banned",
    ACCOUNT_STATUS_DELETED: "Deleted",
}


def canonicalize_restriction_key(raw: str) -> str:
    """Normalize + map legacy aliases to current catalog keys."""
    code = (raw or "").strip().lower().replace(" ", "_")
    return LEGACY_RESTRICTION_ALIASES.get(code, code)
