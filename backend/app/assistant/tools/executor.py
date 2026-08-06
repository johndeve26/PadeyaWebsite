"""Execute assistant tools with auth derived from CurrentUser only."""

from __future__ import annotations

import logging
import time
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.assistant.constants import SAFETY_LEVEL_FORBIDDEN, SOFT_HIGH_RISK_TOOLS
from app.assistant.privacy import sanitize_tool_args_for_log
from app.assistant.tools import (
    account,
    admin,
    ambassador,
    fan,
    host,
    navigation,
    public_search,
    sponsor,
    support,
)
from app.assistant.tools.registry import ToolDefinition, get_tool
from app.users.models import User
from app.users.service import user_has_permission, user_has_role, user_permission_codes, user_role_names

logger = logging.getLogger(__name__)

Handler = Callable[..., dict[str, Any]]

_HANDLERS: dict[str, Handler] = {
    "search_public_events": public_search.search_public_events,
    "get_public_event": public_search.get_public_event,
    "search_public_hosts": public_search.search_public_hosts,
    "search_public_pages": public_search.search_public_pages,
    "search_public_resources": public_search.search_public_resources,
    "search_public_products": public_search.search_public_products,
    "search_public_memories": public_search.search_public_memories,
    "navigate_to_route": navigation.navigate_to_route,
    "explain_current_page": navigation.explain_current_page,
    "search_help": navigation.search_help,
    "get_my_account_summary": account.get_my_account_summary,
    "get_my_roles": account.get_my_roles,
    "get_my_notifications_summary": account.get_my_notifications_summary,
    "list_my_upcoming_tickets": fan.list_my_upcoming_tickets,
    "get_my_order_summary": fan.get_my_order_summary,
    "list_my_saved_events": fan.list_my_saved_events,
    "list_my_events": host.list_my_events,
    "get_my_event_summary": host.get_my_event_summary,
    "create_event_draft": host.create_event_draft,
    "draft_event_description": host.draft_event_description,
    "get_my_referral_summary": ambassador.get_my_referral_summary,
    "list_my_sponsor_opportunities": sponsor.list_my_sponsor_opportunities,
    "list_my_sponsor_applications": sponsor.list_my_sponsor_applications,
    "create_support_ticket_draft": support.create_support_ticket_draft,
    "create_support_ticket": support.create_support_ticket,
    "admin_navigate": admin.admin_navigate,
    "admin_explain": admin.admin_explain,
}


def _auth_ok(tool: ToolDefinition, user: User | None) -> tuple[bool, str | None]:
    if tool.safety_level >= SAFETY_LEVEL_FORBIDDEN or tool.name in SOFT_HIGH_RISK_TOOLS:
        return False, "forbidden_tool"
    if tool.requires_auth and user is None:
        return False, "auth_required"
    if user is None:
        return True, None
    if tool.required_roles and not user_has_role(user, *tool.required_roles):
        return False, "forbidden_role"
    if tool.required_permissions:
        if not any(user_has_permission(user, p) for p in tool.required_permissions):
            return False, "forbidden_permission"
    return True, None


def execute_tool(
    db: Session,
    *,
    tool_name: str,
    args: dict[str, Any] | None,
    user: User | None,
    page_context: dict[str, Any] | None = None,
    confirmed: bool = False,
) -> dict[str, Any]:
    """
    Run a registered tool.

    User identity is taken only from ``user`` (CurrentUser). Any model-supplied
    ``user_id`` in args is stripped and ignored.
    """
    tool = get_tool(tool_name)
    if tool is None:
        return {
            "ok": False,
            "error": "unknown_tool",
            "tool_name": tool_name,
            "sanitized_arguments": sanitize_tool_args_for_log(args),
        }

    ok, err = _auth_ok(tool, user)
    if not ok:
        return {
            "ok": False,
            "error": err,
            "tool_name": tool.name,
            "sanitized_arguments": sanitize_tool_args_for_log(args),
        }

    if tool.confirmation_required and not confirmed:
        return {
            "ok": False,
            "error": "confirmation_required",
            "tool_name": tool.name,
            "confirmation_required": True,
            "sanitized_arguments": sanitize_tool_args_for_log(args),
        }

    handler = _HANDLERS.get(tool.name)
    if handler is None:
        return {
            "ok": False,
            "error": "handler_missing",
            "tool_name": tool.name,
            "sanitized_arguments": sanitize_tool_args_for_log(args),
        }

    clean_args = dict(args or {})
    clean_args.pop("user_id", None)
    clean_args.pop("buyer_user_id", None)
    clean_args.pop("actor_user_id", None)

    roles = user_role_names(user) if user else []
    permissions = user_permission_codes(user) if user else []

    started = time.perf_counter()
    try:
        result = handler(
            db,
            user=user,
            args=clean_args,
            page_context=page_context,
            authenticated=user is not None,
            roles=roles,
            permissions=permissions,
            confirmed=confirmed,
        )
    except Exception:
        logger.exception("assistant.tool_failed name=%s", tool.name)
        return {
            "ok": False,
            "error": "tool_exception",
            "tool_name": tool.name,
            "duration_ms": int((time.perf_counter() - started) * 1000),
            "sanitized_arguments": sanitize_tool_args_for_log(clean_args),
        }

    if not isinstance(result, dict):
        result = {"ok": True, "result": result}
    result.setdefault("tool_name", tool.name)
    result.setdefault(
        "sanitized_arguments", sanitize_tool_args_for_log(clean_args)
    )
    result["duration_ms"] = int((time.perf_counter() - started) * 1000)
    return result
