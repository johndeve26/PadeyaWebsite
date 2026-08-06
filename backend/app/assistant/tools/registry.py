"""Tool definitions for the Pàdéyá assistant."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.assistant.constants import (
    SAFETY_LEVEL_AUTH_READ,
    SAFETY_LEVEL_DRAFT,
    SAFETY_LEVEL_FORBIDDEN,
    SAFETY_LEVEL_MUTATE_CONFIRM,
    SAFETY_LEVEL_NAVIGATE,
    SAFETY_LEVEL_PUBLIC_READ,
    SOFT_HIGH_RISK_TOOLS,
)


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    safety_level: int
    requires_auth: bool = False
    required_permissions: tuple[str, ...] = ()
    required_roles: tuple[str, ...] = ()
    confirmation_required: bool = False
    timeout_seconds: int = 8
    feature_flag: str | None = None
    args_schema: dict[str, Any] = field(default_factory=dict)


def _t(
    name: str,
    description: str,
    safety_level: int,
    *,
    requires_auth: bool = False,
    required_permissions: tuple[str, ...] = (),
    required_roles: tuple[str, ...] = (),
    confirmation_required: bool = False,
    timeout_seconds: int = 8,
    feature_flag: str | None = None,
) -> ToolDefinition:
    return ToolDefinition(
        name=name,
        description=description,
        safety_level=safety_level,
        requires_auth=requires_auth,
        required_permissions=required_permissions,
        required_roles=required_roles,
        confirmation_required=confirmation_required,
        timeout_seconds=timeout_seconds,
        feature_flag=feature_flag,
    )


TOOL_REGISTRY: dict[str, ToolDefinition] = {
    # Public search
    "search_public_events": _t(
        "search_public_events",
        "Search listed public upcoming events.",
        SAFETY_LEVEL_PUBLIC_READ,
        feature_flag="assistant_event_search_enabled",
    ),
    "get_public_event": _t(
        "get_public_event",
        "Get a public event by slug or public id.",
        SAFETY_LEVEL_PUBLIC_READ,
        feature_flag="assistant_event_search_enabled",
    ),
    "search_public_hosts": _t(
        "search_public_hosts",
        "Search discoverable hosts.",
        SAFETY_LEVEL_PUBLIC_READ,
    ),
    "search_public_pages": _t(
        "search_public_pages",
        "Search public marketing/help pages via registry and knowledge.",
        SAFETY_LEVEL_PUBLIC_READ,
    ),
    "search_public_resources": _t(
        "search_public_resources",
        "Search blog and help resources.",
        SAFETY_LEVEL_PUBLIC_READ,
    ),
    "search_public_products": _t(
        "search_public_products",
        "Search public merch/marketplace products.",
        SAFETY_LEVEL_PUBLIC_READ,
    ),
    "search_public_memories": _t(
        "search_public_memories",
        "Search public memory albums.",
        SAFETY_LEVEL_PUBLIC_READ,
    ),
    "get_public_pricing": _t(
        "get_public_pricing",
        "Get public fee structure for hosts and buyers from live pricing settings.",
        SAFETY_LEVEL_PUBLIC_READ,
    ),
    # Navigation
    "navigate_to_route": _t(
        "navigate_to_route",
        "Resolve a route key or query to a safe navigation target.",
        SAFETY_LEVEL_NAVIGATE,
    ),
    "explain_current_page": _t(
        "explain_current_page",
        "Explain the current page using page context and help registry.",
        SAFETY_LEVEL_NAVIGATE,
    ),
    "search_help": _t(
        "search_help",
        "Search help topics and FAQs.",
        SAFETY_LEVEL_PUBLIC_READ,
    ),
    # Account
    "get_my_account_summary": _t(
        "get_my_account_summary",
        "Minimal account summary for the signed-in user.",
        SAFETY_LEVEL_AUTH_READ,
        requires_auth=True,
    ),
    "get_my_roles": _t(
        "get_my_roles",
        "List roles for the signed-in user.",
        SAFETY_LEVEL_AUTH_READ,
        requires_auth=True,
    ),
    "get_my_notifications_summary": _t(
        "get_my_notifications_summary",
        "Unread notification count for the signed-in user.",
        SAFETY_LEVEL_AUTH_READ,
        requires_auth=True,
    ),
    # Fan
    "list_my_upcoming_tickets": _t(
        "list_my_upcoming_tickets",
        "List upcoming tickets owned by the signed-in user.",
        SAFETY_LEVEL_AUTH_READ,
        requires_auth=True,
    ),
    "get_my_ticket_summary": _t(
        "get_my_ticket_summary",
        "Count total, upcoming, and past tickets for the signed-in user.",
        SAFETY_LEVEL_AUTH_READ,
        requires_auth=True,
    ),
    "get_my_order_summary": _t(
        "get_my_order_summary",
        "Summarize recent orders for the signed-in user.",
        SAFETY_LEVEL_AUTH_READ,
        requires_auth=True,
    ),
    "list_my_saved_events": _t(
        "list_my_saved_events",
        "List hosts the signed-in fan follows (alias for following summary).",
        SAFETY_LEVEL_AUTH_READ,
        requires_auth=True,
    ),
    "get_my_following_summary": _t(
        "get_my_following_summary",
        "Count hosts the signed-in fan follows and marketing opt-ins.",
        SAFETY_LEVEL_AUTH_READ,
        requires_auth=True,
    ),
    "get_my_fan_connect_summary": _t(
        "get_my_fan_connect_summary",
        "Count Fan Connect peer connections for the signed-in user.",
        SAFETY_LEVEL_AUTH_READ,
        requires_auth=True,
        required_permissions=("fan_connect.use",),
    ),
    # Host
    "list_my_events": _t(
        "list_my_events",
        "List events owned by the signed-in host.",
        SAFETY_LEVEL_AUTH_READ,
        requires_auth=True,
        required_roles=("host",),
    ),
    "get_my_event_summary": _t(
        "get_my_event_summary",
        "Summarize one owned event (no finance mutations).",
        SAFETY_LEVEL_AUTH_READ,
        requires_auth=True,
        required_roles=("host",),
    ),
    "get_my_audience_summary": _t(
        "get_my_audience_summary",
        "Host audience aggregates: followers, opt-ins, buyers, check-ins.",
        SAFETY_LEVEL_AUTH_READ,
        requires_auth=True,
        required_roles=("host",),
    ),
    "get_my_event_analytics": _t(
        "get_my_event_analytics",
        "Per-event sales metrics for an owned event (tickets sold, check-ins, traffic).",
        SAFETY_LEVEL_AUTH_READ,
        requires_auth=True,
        required_roles=("host",),
    ),
    "create_event_draft": _t(
        "create_event_draft",
        "Create an event draft (confirmation required). Never publishes.",
        SAFETY_LEVEL_MUTATE_CONFIRM,
        requires_auth=True,
        required_roles=("host",),
        required_permissions=("events.create",),
        confirmation_required=True,
        feature_flag="assistant_actions_enabled",
    ),
    "draft_event_description": _t(
        "draft_event_description",
        "Draft event description copy (suggestion only).",
        SAFETY_LEVEL_DRAFT,
        requires_auth=True,
        required_roles=("host",),
    ),
    # Ambassador
    "get_my_referral_summary": _t(
        "get_my_referral_summary",
        "Referral summary for the signed-in ambassador.",
        SAFETY_LEVEL_AUTH_READ,
        requires_auth=True,
        required_roles=("ambassador",),
    ),
    # Sponsor
    "list_my_sponsor_opportunities": _t(
        "list_my_sponsor_opportunities",
        "List sponsorship opportunities visible to the sponsor.",
        SAFETY_LEVEL_AUTH_READ,
        requires_auth=True,
        required_roles=("sponsor",),
    ),
    "list_my_sponsor_applications": _t(
        "list_my_sponsor_applications",
        "List the sponsor's own applications.",
        SAFETY_LEVEL_AUTH_READ,
        requires_auth=True,
        required_roles=("sponsor",),
    ),
    # Support
    "create_support_ticket_draft": _t(
        "create_support_ticket_draft",
        "Draft a support ticket body (does not submit).",
        SAFETY_LEVEL_DRAFT,
        requires_auth=True,
        feature_flag="assistant_support_drafts_enabled",
    ),
    "create_support_ticket": _t(
        "create_support_ticket",
        "Create a support ticket after confirmation.",
        SAFETY_LEVEL_MUTATE_CONFIRM,
        requires_auth=True,
        confirmation_required=True,
        feature_flag="assistant_actions_enabled",
    ),
    # Admin navigation-only
    "admin_navigate": _t(
        "admin_navigate",
        "Resolve admin navigation targets only — no mutations.",
        SAFETY_LEVEL_NAVIGATE,
        requires_auth=True,
        required_permissions=("admin.full_access", "admin.ai.manage_settings"),
        feature_flag="assistant_admin_enabled",
    ),
    "admin_explain": _t(
        "admin_explain",
        "Explain an admin page (navigation/help only).",
        SAFETY_LEVEL_NAVIGATE,
        requires_auth=True,
        required_permissions=("admin.full_access", "admin.ai.manage_settings"),
        feature_flag="assistant_admin_enabled",
    ),
}

# Register soft high-risk stubs as forbidden (never execute)
for _name in SOFT_HIGH_RISK_TOOLS:
    if _name not in TOOL_REGISTRY:
        TOOL_REGISTRY[_name] = _t(
            _name,
            "Forbidden high-risk tool — never execute.",
            SAFETY_LEVEL_FORBIDDEN,
            requires_auth=True,
        )


def get_tool(name: str) -> ToolDefinition | None:
    return TOOL_REGISTRY.get((name or "").strip())


def list_tools_for_context(
    *,
    authenticated: bool,
    roles: list[str] | set[str] | None = None,
    permissions: list[str] | set[str] | None = None,
    flags: dict[str, bool] | None = None,
) -> list[ToolDefinition]:
    role_set = {r.lower() for r in (roles or [])}
    perm_set = set(permissions or [])
    flag_map = flags or {}
    out: list[ToolDefinition] = []
    for tool in TOOL_REGISTRY.values():
        if tool.safety_level >= SAFETY_LEVEL_FORBIDDEN:
            continue
        if tool.requires_auth and not authenticated:
            continue
        if tool.required_roles and not (
            role_set.intersection(tool.required_roles) or "super_admin" in role_set
        ):
            continue
        if tool.required_permissions and not (
            "admin.full_access" in perm_set
            or any(p in perm_set for p in tool.required_permissions)
        ):
            continue
        if tool.feature_flag and not flag_map.get(tool.feature_flag, False):
            # Default: event search flag True when assistant on handled by caller
            if tool.feature_flag == "assistant_event_search_enabled":
                if not flag_map.get(tool.feature_flag, True):
                    continue
            else:
                continue
        out.append(tool)
    return out
