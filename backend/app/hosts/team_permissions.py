"""Host-scoped team roles and grouped permission toggles.

Owner is not a team role — the host profile owner always has full access.
Scanner/merch desk defaults to per-event assignment (host-wide scan off).
Permissions remain editable after a role preset is applied.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.hosts.models import HostTeamMember

TEAM_ROLES = (
    "admin",
    "event_manager",
    "ambassador_manager",
    "finance_manager",
    "scanner",
    "merch_staff",
    "support_staff",
    "sponsor_manager",
    "viewer",
)

ROLE_LABELS: dict[str, str] = {
    "admin": "Admin",
    "event_manager": "Event Manager",
    "ambassador_manager": "Ambassador Manager",
    "finance_manager": "Finance Manager",
    "scanner": "Scanner Staff",
    "merch_staff": "Merch Staff",
    "support_staff": "Support Staff",
    "sponsor_manager": "Sponsor Manager",
    "viewer": "Viewer",
}

PERMISSION_GROUPS: dict[str, tuple[str, ...]] = {
    "events": (
        "events.view",
        "events.create",
        "events.edit",
        "events.publish",
        "events.cancel",
        "events.archive",
    ),
    "tickets": (
        "tickets.view",
        "tickets.scan_qr",
        "tickets.check_in",
        "tickets.manage_pricing",
        "tickets.manage_capacity",
        "tickets.export_attendees",
        "tickets.view_refunds",
    ),
    "merch": (
        "merch.view",
        "merch.create",
        "merch.edit",
        "merch.manage_inventory",
        "merch.scan_pickup_qr",
        "merch.mark_picked_up",
        "merch.fulfill_orders",
        "merch.manage_shipping",
        "merch.manage_discounts",
        "merch.manage_bundles",
    ),
    "messages": (
        "messages.view",
        "messages.reply",
        "messages.manage_templates",
        "messages.report_or_escalate",
    ),
    "sponsors": (
        "sponsors.view",
        "sponsors.reply",
        "sponsors.manage_slots",
        "sponsors.accept_or_reject",
    ),
    "analytics": (
        "analytics.view_events",
        "analytics.view_merch",
        "analytics.view_sponsors",
        "analytics.export",
    ),
    "team": (
        "team.view",
        "team.invite",
        "team.edit_permissions",
        "team.remove_members",
    ),
    "finance": (
        "finance.view_sales_summary",
        "finance.view_payouts",
        "finance.manage_payouts",
        "finance.manage_payout_settings",
    ),
    "ambassadors": (
        "ambassadors.view",
        "ambassadors.create_campaigns",
        "ambassadors.edit_campaigns",
        "ambassadors.pause_campaigns",
        "ambassadors.remove_participants",
        "ambassadors.view_conversions",
        "ambassadors.view_payouts",
        "ambassadors.approve_rewards",
        "ambassadors.reject_rewards",
        "ambassadors.mark_rewards_paid",
        "ambassadors.reverse_rewards",
        "ambassadors.export",
    ),
}

PERMISSION_KEYS: tuple[str, ...] = tuple(
    key for keys in PERMISSION_GROUPS.values() for key in keys
)

# Owner-only unless the owner explicitly grants on a membership.
OWNER_ONLY_PERMISSION_KEYS = frozenset({"finance.manage_payout_settings"})

# Expand legacy flat keys stored before the grouped catalog.
_LEGACY_EXPAND: dict[str, tuple[str, ...]] = {
    "scan_tickets": ("tickets.scan_qr", "tickets.check_in"),
    "scan_merch": (
        "merch.scan_pickup_qr",
        "merch.mark_picked_up",
        "merch.fulfill_orders",
    ),
    "view_attendees": ("tickets.view", "tickets.export_attendees"),
    "manage_event_staff": ("events.edit",),
    "manage_events": PERMISSION_GROUPS["events"],
    "manage_tickets": (
        "tickets.view",
        "tickets.manage_pricing",
        "tickets.manage_capacity",
        "tickets.export_attendees",
        "tickets.view_refunds",
    ),
    "view_analytics": PERMISSION_GROUPS["analytics"],
    "manage_team": PERMISSION_GROUPS["team"],
    "manage_payouts": ("finance.view_payouts", "finance.manage_payouts"),
    "manage_bank": ("finance.manage_payout_settings",),
    "manage_messages": PERMISSION_GROUPS["messages"],
    "view_order_context": ("tickets.view",),
    "manage_sponsors": PERMISSION_GROUPS["sponsors"],
    "view_assigned": (
        "events.view",
        "tickets.view",
        "merch.view",
        "analytics.view_events",
        "sponsors.view",
        "messages.view",
    ),
    # Pre-granular Ambassadors catalog keys
    "ambassadors.manage_campaigns": (
        "ambassadors.create_campaigns",
        "ambassadors.edit_campaigns",
        "ambassadors.pause_campaigns",
    ),
    "ambassadors.manage_participants": ("ambassadors.remove_participants",),
}

_FALSE = {key: False for key in PERMISSION_KEYS}


def _p(*enabled: str) -> dict[str, bool]:
    base = dict(_FALSE)
    for key in enabled:
        if key in base:
            base[key] = True
    return base


def _group(*group_names: str, extra: tuple[str, ...] = ()) -> dict[str, bool]:
    keys: list[str] = []
    for name in group_names:
        keys.extend(PERMISSION_GROUPS[name])
    keys.extend(extra)
    return _p(*keys)


# Campaign ops (no payout mark/export) — Admin safer default includes these + approve/reject/reverse.
_AMBASSADOR_CAMPAIGN_OPS = (
    "ambassadors.view",
    "ambassadors.create_campaigns",
    "ambassadors.edit_campaigns",
    "ambassadors.pause_campaigns",
    "ambassadors.remove_participants",
    "ambassadors.view_conversions",
)

_AMBASSADOR_MANAGER_DEFAULTS = (
    *_AMBASSADOR_CAMPAIGN_OPS,
    "ambassadors.view_payouts",
    "ambassadors.approve_rewards",
    "ambassadors.reject_rewards",
    "ambassadors.reverse_rewards",
    # mark_rewards_paid / export stay off unless host grants
)

ROLE_DEFAULTS: dict[str, dict[str, bool]] = {
    # Near-full host ops. Desk scan + payout/bank + mark-paid/export stay off (safer).
    "admin": _group(
        "events",
        "tickets",
        "merch",
        "messages",
        "sponsors",
        "analytics",
        "team",
        "ambassadors",
        extra=("finance.view_sales_summary",),
    ),
    "event_manager": _p(
        *PERMISSION_GROUPS["events"],
        *PERMISSION_GROUPS["tickets"],
        "analytics.view_events",
        "ambassadors.view",
        "ambassadors.view_conversions",
    ),
    "ambassador_manager": _p(*_AMBASSADOR_MANAGER_DEFAULTS),
    "finance_manager": _p(
        "finance.view_sales_summary",
        "finance.view_payouts",
        "finance.manage_payouts",
        "ambassadors.view_payouts",
        "ambassadors.mark_rewards_paid",
    ),
    # Host-wide desk off — use event_staff_assignments by default.
    "scanner": _p("events.view", "tickets.view"),
    "merch_staff": _p("events.view", "merch.view"),
    "support_staff": _p(
        "events.view",
        "tickets.view",
        *PERMISSION_GROUPS["messages"],
    ),
    "sponsor_manager": _p(*PERMISSION_GROUPS["sponsors"], "analytics.view_sponsors"),
    # ambassadors.view only if host grants it (not in preset).
    "viewer": _p(
        "events.view",
        "tickets.view",
        "merch.view",
        "messages.view",
        "sponsors.view",
        "analytics.view_events",
        "team.view",
        "finance.view_sales_summary",
    ),
}

# Admin preset: desk scan + payout/bank + mark-paid/export off unless toggled.
# Approve/reject/reverse remain on (from ambassadors group) for host-owned campaigns.
for _safer_off in (
    "tickets.scan_qr",
    "tickets.check_in",
    "merch.scan_pickup_qr",
    "merch.mark_picked_up",
    "merch.fulfill_orders",
    "finance.view_payouts",
    "finance.manage_payouts",
    "finance.manage_payout_settings",
    "ambassadors.view_payouts",
    "ambassadors.mark_rewards_paid",
    "ambassadors.export",
):
    ROLE_DEFAULTS["admin"][_safer_off] = False

# Event Manager: tickets.* includes desk keys — keep host-wide desk off by default.
for _em_desk_off in ("tickets.scan_qr", "tickets.check_in"):
    ROLE_DEFAULTS["event_manager"][_em_desk_off] = False


def normalize_role(role: str | None) -> str:
    value = (role or "scanner").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "owner": "admin",
        "co_host": "admin",
        "cohost": "admin",
        "manager": "admin",
        "ops": "event_manager",
        "operations": "event_manager",
        "staff": "event_manager",
        "scanner_staff": "scanner",
        "door": "scanner",
        "merch": "merch_staff",
        "merchandise": "merch_staff",
        "support": "support_staff",
        "sponsor": "sponsor_manager",
        "sponsors": "sponsor_manager",
        "ambassador": "ambassador_manager",
        "ambassadors": "ambassador_manager",
        "promo_manager": "ambassador_manager",
        "finance": "finance_manager",
        "payouts": "finance_manager",
        "read_only": "viewer",
        "readonly": "viewer",
    }
    value = aliases.get(value, value)
    if value not in TEAM_ROLES:
        return "scanner"
    return value


def default_role_label(role: str | None) -> str:
    key = normalize_role(role)
    return ROLE_LABELS.get(key, key)


def empty_permissions() -> dict[str, bool]:
    return dict(_FALSE)


def permissions_for_role(role: str | None) -> dict[str, bool]:
    return dict(ROLE_DEFAULTS[normalize_role(role)])


def merge_permissions(
    role: str | None,
    overrides: dict[str, Any] | None = None,
) -> dict[str, bool]:
    base = permissions_for_role(role)
    if not overrides:
        return base
    expanded = _expand_raw(overrides)
    for key in PERMISSION_KEYS:
        if key in expanded:
            base[key] = bool(expanded[key])
    return base


def _expand_raw(raw: dict[str, Any]) -> dict[str, bool]:
    """Map legacy + namespaced keys into the current catalog."""
    out: dict[str, bool] = {}
    for key, value in raw.items():
        if key in _LEGACY_EXPAND and value:
            for mapped in _LEGACY_EXPAND[key]:
                out[mapped] = True
        elif key in _LEGACY_EXPAND and not value:
            # Explicit false on legacy key does not force-clear expanded keys
            # unless the new key is also present.
            continue
        elif key in PERMISSION_KEYS:
            out[key] = bool(value)
    return out


def normalize_permissions_dict(raw: dict[str, Any] | None) -> dict[str, bool]:
    base = empty_permissions()
    if not raw:
        return base
    expanded = _expand_raw(raw)
    for key in PERMISSION_KEYS:
        if key in expanded:
            base[key] = bool(expanded[key])
        elif key in raw:
            base[key] = bool(raw[key])
    return base


def apply_permission_update(
    *,
    role: str | None,
    current: dict[str, Any] | None,
    overrides: dict[str, Any] | None,
    actor_is_owner: bool,
) -> dict[str, bool]:
    """Merge role + overrides; non-owners cannot change owner-only keys."""
    merged = merge_permissions(role, overrides)
    if actor_is_owner:
        return merged
    current_norm = normalize_permissions_dict(current)
    for key in OWNER_ONLY_PERMISSION_KEYS:
        merged[key] = current_norm[key]
    return merged


def get_active_team_membership(
    db: Session, *, user_id: uuid.UUID, host_id: uuid.UUID
) -> HostTeamMember | None:
    return db.scalar(
        select(HostTeamMember).where(
            HostTeamMember.host_id == host_id,
            HostTeamMember.user_id == user_id,
            HostTeamMember.status == "active",
            HostTeamMember.removed_at.is_(None),
        )
    )


def is_active_host_team_member(
    db: Session, *, user_id: uuid.UUID, host_id: uuid.UUID
) -> bool:
    return get_active_team_membership(db, user_id=user_id, host_id=host_id) is not None


def team_permission_allows(
    db: Session,
    *,
    user_id: uuid.UUID,
    host_id: uuid.UUID,
    permission: str,
) -> bool:
    row = get_active_team_membership(db, user_id=user_id, host_id=host_id)
    if row is None:
        return False
    perms = normalize_permissions_dict(row.permissions_json)
    if permission in perms:
        return bool(perms[permission])
    # Accept legacy key checks from older call sites.
    if permission in _LEGACY_EXPAND:
        return any(perms.get(k) for k in _LEGACY_EXPAND[permission])
    return False


def team_permission_allows_any(
    db: Session,
    *,
    user_id: uuid.UUID,
    host_id: uuid.UUID,
    permissions: tuple[str, ...] | list[str],
) -> bool:
    return any(
        team_permission_allows(
            db, user_id=user_id, host_id=host_id, permission=p
        )
        for p in permissions
    )


# --- Scope model (host-wide vs selected events) ---

SCOPE_HOST_WIDE = "host_wide"
SCOPE_SELECTED_EVENTS = "selected_events"
TEAM_SCOPES = (SCOPE_HOST_WIDE, SCOPE_SELECTED_EVENTS)

ROLE_DEFAULT_SCOPES: dict[str, str] = {
    "admin": SCOPE_HOST_WIDE,
    "event_manager": SCOPE_HOST_WIDE,  # may be narrowed to selected_events
    "ambassador_manager": SCOPE_HOST_WIDE,
    "finance_manager": SCOPE_HOST_WIDE,
    "scanner": SCOPE_SELECTED_EVENTS,
    "merch_staff": SCOPE_SELECTED_EVENTS,
    "support_staff": SCOPE_HOST_WIDE,  # may be narrowed to selected_events
    "sponsor_manager": SCOPE_HOST_WIDE,
    "viewer": SCOPE_SELECTED_EVENTS,
}


def default_scope_for_role(role: str | None) -> str:
    return ROLE_DEFAULT_SCOPES[normalize_role(role)]


def normalize_scope(scope: str | None, *, role: str | None = None) -> str:
    value = (scope or "").strip().lower().replace("-", "_")
    if value in {"host", "all", "workspace", "org"}:
        value = SCOPE_HOST_WIDE
    if value in {"event", "events", "selected", "per_event", "event_specific"}:
        value = SCOPE_SELECTED_EVENTS
    if value in TEAM_SCOPES:
        return value
    return default_scope_for_role(role)


def parse_scoped_event_ids(raw: Any) -> list[uuid.UUID]:
    if not raw:
        return []
    out: list[uuid.UUID] = []
    seen: set[uuid.UUID] = set()
    for item in raw:
        try:
            eid = uuid.UUID(str(item))
        except (TypeError, ValueError):
            continue
        if eid in seen:
            continue
        seen.add(eid)
        out.append(eid)
    return out


def scoped_event_ids_as_str(ids: list[uuid.UUID]) -> list[str]:
    return [str(eid) for eid in ids]


def pack_scope_json(
    scope: str, event_ids: list[uuid.UUID] | list[str] | None = None
) -> dict[str, Any]:
    return {
        "type": normalize_scope(scope),
        "event_ids": [str(eid) for eid in parse_scoped_event_ids(event_ids or [])],
    }


def unpack_scope_json(
    raw: Any, *, role: str | None = None
) -> tuple[str, list[uuid.UUID]]:
    """Read ``scope_json`` or legacy ``scope`` / ``scoped_event_ids_json`` fields."""
    if isinstance(raw, dict):
        scope = normalize_scope(
            raw.get("type") or raw.get("scope"), role=role
        )
        ids = parse_scoped_event_ids(
            raw.get("event_ids") or raw.get("scoped_event_ids") or []
        )
        return scope, ids
    if isinstance(raw, str):
        return normalize_scope(raw, role=role), []
    return normalize_scope(None, role=role), []


def membership_scope(row: HostTeamMember) -> tuple[str, list[uuid.UUID]]:
    if getattr(row, "scope_json", None):
        return unpack_scope_json(row.scope_json, role=row.role)
    # Legacy in-memory / pre-migration attributes
    scope = normalize_scope(getattr(row, "scope", None), role=row.role)
    ids = parse_scoped_event_ids(getattr(row, "scoped_event_ids_json", None))
    return scope, ids


def membership_covers_event(
    db: Session,
    row: HostTeamMember,
    event_id: uuid.UUID,
) -> bool:
    """Whether this membership's scope includes the event.

    selected_events → ``scope_json.event_ids`` **or** ``event_staff_assignments``.
    """
    scope, scoped = membership_scope(row)
    if scope == SCOPE_HOST_WIDE:
        return True

    if event_id in scoped:
        return True

    if row.user_id is None:
        return False

    from app.teams.permissions import has_event_staff_assignment

    return has_event_staff_assignment(
        db, user_id=row.user_id, event_id=event_id, permission=None
    )


def team_permission_allows_for_event(
    db: Session,
    *,
    user_id: uuid.UUID,
    host_id: uuid.UUID,
    permission: str,
    event_id: uuid.UUID,
) -> bool:
    """Host-wide team permission that also respects membership scope for an event."""
    row = get_active_team_membership(db, user_id=user_id, host_id=host_id)
    if row is None:
        return False
    if not team_permission_allows(
        db, user_id=user_id, host_id=host_id, permission=permission
    ):
        return False
    return membership_covers_event(db, row, event_id)


def team_permission_allows_any_for_event(
    db: Session,
    *,
    user_id: uuid.UUID,
    host_id: uuid.UUID,
    permissions: tuple[str, ...] | list[str],
    event_id: uuid.UUID,
) -> bool:
    return any(
        team_permission_allows_for_event(
            db,
            user_id=user_id,
            host_id=host_id,
            permission=p,
            event_id=event_id,
        )
        for p in permissions
    )
