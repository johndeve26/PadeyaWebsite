"""Authenticated route registry for Pàdéyá Copilot navigation."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class AuthRouteEntry:
    key: str
    path: str
    title: str
    description: str
    required_roles: tuple[str, ...] = ()
    required_permissions: tuple[str, ...] = ()
    synonyms: tuple[str, ...] = ()
    common_questions: tuple[str, ...] = ()
    navigation_only: bool = False


AUTH_ROUTE_REGISTRY: dict[str, AuthRouteEntry] = {
    "fan_tickets": AuthRouteEntry(
        key="fan_tickets",
        path="/dashboard/tickets",
        title="My tickets",
        description="Upcoming and past tickets for the signed-in fan.",
        required_roles=("fan", "user"),
        synonyms=("my tickets", "upcoming tickets", "ticket wallet"),
        common_questions=("Where are my tickets?", "Show my upcoming events"),
    ),
    "fan_orders": AuthRouteEntry(
        key="fan_orders",
        path="/dashboard/orders",
        title="My orders",
        description="Ticket and merch order history.",
        required_roles=("fan", "user"),
        synonyms=("my orders", "order history", "purchases"),
        common_questions=("Where is my order?", "Show my purchases"),
    ),
    "fan_saved": AuthRouteEntry(
        key="fan_saved",
        path="/dashboard/saved",
        title="Saved",
        description="Saved events and hosts.",
        required_roles=("fan", "user"),
        synonyms=("saved", "wishlist", "bookmarks", "saved events"),
        common_questions=("Where are my saved events?",),
    ),
    "host_events": AuthRouteEntry(
        key="host_events",
        path="/host/events",
        title="Host events",
        description="Manage your hosted events.",
        required_roles=("host",),
        synonyms=("my events", "host events", "event studio list"),
        common_questions=("Show my events", "Where do I manage events?"),
    ),
    "host_audience": AuthRouteEntry(
        key="host_audience",
        path="/host/audience",
        title="Audience CRM",
        description="Followers, buyers, and marketing opt-ins for your host profile.",
        required_roles=("host",),
        synonyms=("audience", "followers", "crm", "marketing opt in"),
        common_questions=(
            "How many followers do I have?",
            "How many people opted in?",
        ),
    ),
    "host_events_create": AuthRouteEntry(
        key="host_events_create",
        path="/host/events/new",
        title="Create event",
        description="Start a new event draft in Host Studio.",
        required_roles=("host",),
        required_permissions=("events.create",),
        synonyms=("create event", "new event", "host an event"),
        common_questions=("How do I create an event?",),
    ),
    "ambassador_dashboard": AuthRouteEntry(
        key="ambassador_dashboard",
        path="/ambassador",
        title="Ambassador dashboard",
        description="Referrals and ambassador performance.",
        required_roles=("ambassador",),
        synonyms=("ambassador", "my referrals", "referral dashboard"),
        common_questions=("Where is my referral dashboard?",),
    ),
    "sponsor_dashboard": AuthRouteEntry(
        key="sponsor_dashboard",
        path="/sponsor",
        title="Sponsor dashboard",
        description="Sponsorship opportunities and applications.",
        required_roles=("sponsor",),
        synonyms=("sponsor", "sponsor dashboard", "my sponsorships"),
        common_questions=("Where are my sponsorship applications?",),
    ),
    "admin_home": AuthRouteEntry(
        key="admin_home",
        path="/admin",
        title="Admin",
        description="Admin control center (navigation only via assistant).",
        required_permissions=("admin.full_access",),
        synonyms=("admin", "control center", "admin home"),
        common_questions=("Open admin",),
        navigation_only=True,
    ),
    "admin_ai": AuthRouteEntry(
        key="admin_ai",
        path="/admin/ai",
        title="Admin AI",
        description="AI Control Center (navigation only).",
        required_permissions=("admin.ai.manage_settings", "admin.full_access"),
        synonyms=("ai settings", "ai control", "copilot admin"),
        common_questions=("Open AI settings",),
        navigation_only=True,
    ),
    "account": AuthRouteEntry(
        key="account",
        path="/account",
        title="Account",
        description="Account settings and profile.",
        synonyms=("account", "my account", "profile settings"),
        common_questions=("Where are my account settings?",),
    ),
    "notifications": AuthRouteEntry(
        key="notifications",
        path="/notifications",
        title="Notifications",
        description="In-app notifications inbox.",
        synonyms=("notifications", "alerts", "inbox notifications"),
        common_questions=("Show my notifications",),
    ),
}


def get_auth_route_by_key(key: str) -> AuthRouteEntry | None:
    return AUTH_ROUTE_REGISTRY.get((key or "").strip().lower())


def _role_ok(entry: AuthRouteEntry, roles: set[str]) -> bool:
    if not entry.required_roles:
        return True
    if "super_admin" in roles:
        return True
    return bool(roles.intersection(entry.required_roles) or "user" in entry.required_roles and roles)


def _perm_ok(entry: AuthRouteEntry, permissions: set[str]) -> bool:
    if not entry.required_permissions:
        return True
    if "admin.full_access" in permissions or "super_admin" in permissions:
        return True
    return any(p in permissions for p in entry.required_permissions)


def resolve_auth_route(
    query: str,
    roles: list[str] | set[str] | None = None,
    permissions: list[str] | set[str] | None = None,
) -> AuthRouteEntry | None:
    """Match a query to an auth route the user is allowed to see."""
    q = (query or "").strip().lower()
    if not q:
        return None
    role_set = {r.lower() for r in (roles or [])}
    perm_set = {p for p in (permissions or [])}

    best: AuthRouteEntry | None = None
    best_score = 0
    tokens = set(re.findall(r"[a-z0-9']+", q))
    for entry in AUTH_ROUTE_REGISTRY.values():
        if not _role_ok(entry, role_set):
            continue
        if not _perm_ok(entry, perm_set):
            continue
        score = 0
        for syn in entry.synonyms:
            syn_l = syn.lower()
            if syn_l in q:
                score += 3 + len(syn_l.split())
            elif set(syn_l.split()) <= tokens:
                score += 2
        if entry.title.lower() in q:
            score += 2
        for question in entry.common_questions:
            if question.lower() in q:
                score += 4
        if score > best_score:
            best_score = score
            best = entry
    return best if best_score >= 2 else None
