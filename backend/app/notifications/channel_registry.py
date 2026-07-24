"""Central notification channel registry for Pàdéyá user-facing alerts.

Single source for which channels a notification kind supports. Email delivery
remains domain-specific via ``enqueue_template``; this registry governs in-app +
push defaults and documents product intent.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.push.templates import resolve_template_name

PrivacyLevel = Literal["standard", "critical", "internal"]
PreferenceGroup = Literal[
    "tickets",
    "merch",
    "messages",
    "fan_connect",
    "host",
    "sponsor",
    "admin",
    "ambassador",
    "security",
    "marketing",
    "support",
]


@dataclass(frozen=True)
class NotificationChannelSpec:
    key: str
    category: PreferenceGroup
    in_app: bool = True
    email: bool = True
    push: bool = True
    is_critical: bool = False
    preference_group: PreferenceGroup | None = None
    push_template: str | None = None  # None → resolve via KIND_ALIASES
    no_push_reason: str | None = None
    privacy_level: PrivacyLevel = "standard"


# Kinds that must never enqueue browser push (internal / unsafe).
_NO_PUSH: dict[str, str] = {
    # Reserved for future CRM/admin-only notes — not product-wired today.
    "admin.internal_note": "Internal admin notes are in-app/email only.",
    "crm.host_note": "Host CRM notes are not user notifications.",
}

# Explicit user-facing catalog (audit baseline). Unknown kinds default to push-on
# with generic template unless listed in _NO_PUSH.
USER_FACING_SPECS: tuple[NotificationChannelSpec, ...] = (
    # Tickets
    NotificationChannelSpec("ticket.confirmed", "tickets", email=True),
    NotificationChannelSpec("ticket.qr_ready", "tickets"),
    NotificationChannelSpec("ticket.event_reminder", "tickets"),
    NotificationChannelSpec("ticket.event_cancelled", "tickets"),
    NotificationChannelSpec("ticket.refund_update", "tickets"),
    NotificationChannelSpec("ticket.transferred", "tickets"),
    NotificationChannelSpec("ticket.transfer_accepted", "tickets"),
    NotificationChannelSpec("ticket.checked_in", "tickets"),
    NotificationChannelSpec("event.updated", "tickets"),
    NotificationChannelSpec("event.cancelled", "tickets"),
    NotificationChannelSpec("event.rescheduled", "tickets"),
    NotificationChannelSpec("event.reminder", "tickets"),
    # Merch
    NotificationChannelSpec("merch.confirmed", "merch"),
    NotificationChannelSpec("merch.paid", "merch"),
    NotificationChannelSpec("merch.ready_for_pickup", "merch"),
    NotificationChannelSpec("merch.shipped", "merch"),
    NotificationChannelSpec("merch.delivered", "merch"),
    NotificationChannelSpec("merch.picked_up", "merch"),
    NotificationChannelSpec("merch.refunded", "merch"),
    NotificationChannelSpec("merch.post_event_drop", "marketing"),
    NotificationChannelSpec("merch.cart_reminder", "marketing"),
    NotificationChannelSpec("merch.vault_unlocked", "merch"),
    NotificationChannelSpec("merch.host_sale", "host"),
    NotificationChannelSpec("host.ticket_sale", "host"),
    NotificationChannelSpec("host.merch_sale", "host"),
    NotificationChannelSpec("host.new_follower", "host"),
    NotificationChannelSpec("host.sponsor_inquiry", "sponsor"),
    NotificationChannelSpec("merch.review_received", "host"),
    # Vault / drops
    NotificationChannelSpec("vault.item_published", "marketing"),
    # Messaging
    NotificationChannelSpec("message.new", "messages"),
    NotificationChannelSpec("fan_connect.message", "messages"),
    NotificationChannelSpec("fan_connect.request", "fan_connect"),
    NotificationChannelSpec("fan_connect.accepted", "fan_connect"),
    NotificationChannelSpec("fan_connect.declined", "fan_connect"),
    NotificationChannelSpec("fan_connect.removed", "fan_connect"),
    # Support (user)
    NotificationChannelSpec("support.ticket_updated", "support"),
    # Sponsorship
    NotificationChannelSpec("sponsor.inquiry_received", "sponsor"),
    NotificationChannelSpec("sponsor.inquiry_status", "sponsor"),
    NotificationChannelSpec("sponsor.deal_proposal", "sponsor"),
    NotificationChannelSpec("sponsor.deal_active", "sponsor"),
    NotificationChannelSpec("sponsor.deliverable_submitted", "sponsor"),
    NotificationChannelSpec("sponsor.deliverable_approved", "sponsor"),
    NotificationChannelSpec("sponsor.deliverable_rejected", "sponsor"),
    NotificationChannelSpec("sponsor.deliverables_completed", "sponsor"),
    # Reviews
    NotificationChannelSpec("review.new", "host"),
    NotificationChannelSpec("review.reply", "host"),
    # Ambassadors
    NotificationChannelSpec("ambassador.joined", "ambassador"),
    NotificationChannelSpec("ambassador.first_sale", "ambassador"),
    NotificationChannelSpec("ambassador.reward_approved", "ambassador"),
    NotificationChannelSpec("ambassador.reward_rejected", "ambassador"),
    NotificationChannelSpec("ambassador.reward_reversed", "ambassador"),
    NotificationChannelSpec("ambassador.campaign_paused", "ambassador"),
    NotificationChannelSpec("ambassador.campaign_ended", "ambassador"),
    # Security / account
    NotificationChannelSpec(
        "account.suspended",
        "security",
        is_critical=True,
        privacy_level="critical",
    ),
    NotificationChannelSpec(
        "account.appeal_decision",
        "security",
        is_critical=True,
        privacy_level="critical",
    ),
    NotificationChannelSpec(
        "team.security_alert",
        "security",
        is_critical=True,
        privacy_level="critical",
    ),
    NotificationChannelSpec(
        "system.maintenance",
        "security",
        is_critical=True,
        privacy_level="critical",
    ),
    # Staff admin alerts (still user-facing for staff accounts)
    NotificationChannelSpec("admin_support_ticket", "admin"),
    NotificationChannelSpec("admin.report", "admin"),
    NotificationChannelSpec("admin.payment_issue", "admin"),
)

_SPECS_BY_KEY: dict[str, NotificationChannelSpec] = {
    s.key: s for s in USER_FACING_SPECS
}


def _category_for_admin_type(classification: str, key: str) -> PreferenceGroup:
    if classification == "critical" or key.startswith("account.") or key.startswith("appeal."):
        return "security"
    if "merch" in key or "vault" in key:
        return "merch"
    if "message" in key or "fan_connect" in key:
        return "messages" if "message" in key else "fan_connect"
    if "sponsor" in key:
        return "sponsor"
    if "ambassador" in key:
        return "ambassador"
    if "host" in key or "review" in key:
        return "host"
    if "support" in key:
        return "support"
    if classification == "marketing":
        return "marketing"
    return "tickets"


def _register_admin_catalog() -> None:
    """Ensure every admin notification type alias is in the channel registry."""
    try:
        from app.admin_notifications.registry import NOTIFICATION_TYPES
    except ImportError:
        return
    for type_def in NOTIFICATION_TYPES:
        group = _category_for_admin_type(type_def.classification, type_def.key)
        for alias in type_def.kind_aliases or (type_def.key,):
            if alias in _SPECS_BY_KEY or alias in _NO_PUSH:
                continue
            _SPECS_BY_KEY[alias] = NotificationChannelSpec(
                key=alias,
                category=group,
                is_critical=bool(type_def.critical),
                privacy_level="critical" if type_def.critical else "standard",
            )
        if type_def.key not in _SPECS_BY_KEY and type_def.key not in _NO_PUSH:
            _SPECS_BY_KEY[type_def.key] = NotificationChannelSpec(
                key=type_def.key,
                category=group,
                is_critical=bool(type_def.critical),
                privacy_level="critical" if type_def.critical else "standard",
            )


_register_admin_catalog()


def lookup_spec(kind: str) -> NotificationChannelSpec | None:
    k = (kind or "").strip()
    if not k:
        return None
    if k in _SPECS_BY_KEY:
        return _SPECS_BY_KEY[k]
    # Prefix fallbacks for dotted families
    for spec in USER_FACING_SPECS:
        if k.startswith(spec.key.split(".")[0] + ".") and spec.key.endswith(".*"):
            pass
    return None


def push_channel_allowed(kind: str) -> tuple[bool, str | None]:
    """Return (allowed, block_reason). Does not check user prefs or admin settings."""
    k = (kind or "").strip()
    if not k:
        return False, "empty_kind"
    if k in _NO_PUSH:
        return False, _NO_PUSH[k]
    spec = _SPECS_BY_KEY.get(k)
    if spec is not None and not spec.push:
        return False, spec.no_push_reason or "push_disabled_for_kind"
    return True, None


def resolved_push_template(kind: str) -> str:
    spec = _SPECS_BY_KEY.get(kind)
    if spec and spec.push_template:
        return spec.push_template
    return resolve_template_name(kind)


def all_user_facing_kinds() -> list[str]:
    return sorted(_SPECS_BY_KEY.keys())


def audit_push_coverage() -> list[dict[str, str | bool]]:
    """For tests/docs: each registered kind's push template resolution."""
    rows: list[dict[str, str | bool]] = []
    for key in all_user_facing_kinds():
        allowed, reason = push_channel_allowed(key)
        tmpl = resolved_push_template(key)
        rows.append(
            {
                "kind": key,
                "push_allowed": allowed,
                "no_push_reason": reason or "",
                "push_template": tmpl,
                "uses_generic": tmpl == "generic",
            }
        )
    return rows
