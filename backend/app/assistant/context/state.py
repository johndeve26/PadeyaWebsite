"""Structured conversation state stored in session metadata."""

from __future__ import annotations

import copy
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.assistant.constants import MAX_CONVERSATION_RESULT_ITEMS, MODE_AUTHENTICATED
from app.assistant.models import AssistantSession
from app.assistant.privacy import redact_dict, scrub_prompt_text
from app.users.models import User

_HOST_PRIVATE_ENTITY_TYPES = frozenset(
    {
        "host_audience",
        "host_event_private",
        "host_analytics",
        "host_segment",
        "host_announcement",
    }
)
_FAN_PRIVATE_ENTITY_TYPES = frozenset({"ticket", "order"})


def _empty_state() -> dict[str, Any]:
    return {
        "current_intent": None,
        "active_search_filters": {},
        "last_result_type": None,
        "last_results": [],
        "selected_entity": None,
        "pending_clarification": None,
        "draft_reference": None,
        "active_workflow": None,
        "pending_confirmation_ids": [],
    }


def _conversation_root(metadata: dict[str, Any] | None) -> dict[str, Any]:
    meta = metadata if isinstance(metadata, dict) else {}
    conv = meta.get("conversation")
    if not isinstance(conv, dict):
        conv = {}
    return conv


def get_conversation_state(session: AssistantSession) -> dict[str, Any]:
    conv = _conversation_root(session.metadata_json)
    state = conv.get("state")
    if not isinstance(state, dict):
        return _empty_state()
    merged = _empty_state()
    merged.update(state)
    if not isinstance(merged.get("last_results"), list):
        merged["last_results"] = []
    if not isinstance(merged.get("active_search_filters"), dict):
        merged["active_search_filters"] = {}
    if not isinstance(merged.get("pending_confirmation_ids"), list):
        merged["pending_confirmation_ids"] = []
    return merged


def get_session_summary_text(session: AssistantSession) -> str:
    conv = _conversation_root(session.metadata_json)
    summary = conv.get("summary")
    return scrub_prompt_text(str(summary or "").strip()[:3200])


def save_conversation_state(
    session: AssistantSession,
    *,
    state: dict[str, Any] | None = None,
    summary: str | None = None,
) -> None:
    meta = copy.deepcopy(session.metadata_json) if isinstance(session.metadata_json, dict) else {}
    conv = _conversation_root(meta)
    if state is not None:
        conv["state"] = _sanitize_state_dict(state)
    if summary is not None:
        conv["summary"] = scrub_prompt_text(summary.strip()[:3200])
        conv["summary_updated_at"] = datetime.now(UTC).isoformat()
    meta["conversation"] = conv
    session.metadata_json = meta


def _sanitize_state_dict(state: dict[str, Any]) -> dict[str, Any]:
    clean = _empty_state()
    clean.update(state)
    clean["active_search_filters"] = redact_dict(
        clean.get("active_search_filters") or {}, max_depth=2
    )
    results = clean.get("last_results") or []
    if isinstance(results, list):
        clean["last_results"] = [
            _sanitize_result_item(item)
            for item in results[:MAX_CONVERSATION_RESULT_ITEMS]
            if isinstance(item, dict)
        ]
    else:
        clean["last_results"] = []
    if clean.get("selected_entity") and isinstance(clean["selected_entity"], dict):
        clean["selected_entity"] = _sanitize_result_item(clean["selected_entity"])
    else:
        clean["selected_entity"] = None
    if clean.get("pending_clarification"):
        clean["pending_clarification"] = scrub_prompt_text(
            str(clean["pending_clarification"])[:240]
        )
    if clean.get("draft_reference"):
        clean["draft_reference"] = scrub_prompt_text(str(clean["draft_reference"])[:120])
    ids = clean.get("pending_confirmation_ids") or []
    clean["pending_confirmation_ids"] = [str(i)[:64] for i in ids if i][:10]
    return clean


def _sanitize_result_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "position": int(item.get("position") or 0),
        "entity_type": scrub_prompt_text(str(item.get("entity_type") or "unknown"))[:32],
        "label": scrub_prompt_text(str(item.get("label") or ""))[:120],
        "slug": scrub_prompt_text(str(item.get("slug") or ""))[:120] or None,
        "url": scrub_prompt_text(str(item.get("url") or ""))[:240] or None,
        "route_key": scrub_prompt_text(str(item.get("route_key") or ""))[:64] or None,
        "public_id": scrub_prompt_text(str(item.get("public_id") or ""))[:64] or None,
    }


def _result_from_row(row: dict[str, Any], *, position: int, entity_type: str) -> dict[str, Any]:
    title = row.get("title") or row.get("display_name") or row.get("event_title")
    slug = row.get("slug") or row.get("event_slug") or row.get("username")
    url = row.get("url") or row.get("path")
    if not url and slug and entity_type == "event":
        url = f"/events/{slug}"
    elif not url and slug and entity_type == "host":
        url = f"/hosts/{slug}"
    return _sanitize_result_item(
        {
            "position": position,
            "entity_type": entity_type,
            "label": title,
            "slug": slug,
            "url": url,
            "route_key": row.get("route_key"),
            "public_id": row.get("id") or row.get("event_id") or row.get("ticket_id"),
        }
    )


def _infer_entity_type(tool_name: str, row: dict[str, Any]) -> str:
    if tool_name in {
        "search_public_events",
        "get_public_event",
        "list_upcoming_events_from_followed_hosts",
        "get_my_event_recommendations",
    }:
        return "event"
    if tool_name in {"search_public_hosts", "get_my_following_summary", "list_my_saved_events"}:
        return "host"
    if tool_name in {"list_my_upcoming_tickets", "list_my_past_tickets", "get_my_ticket_summary"}:
        return "ticket"
    if tool_name in {"list_my_events", "get_my_event_summary", "get_my_event_analytics"}:
        return "host_event_private"
    if tool_name in {"get_my_audience_summary", "list_my_audience_segments"}:
        return "host_audience"
    if row.get("event_title") or row.get("event_slug"):
        return "ticket"
    return "unknown"


def _extract_search_filters(tool_name: str, args: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    filters: dict[str, Any] = {}
    query = str(args.get("query") or args.get("q") or "").strip()
    if query:
        filters["query"] = query[:120]
    if result.get("query"):
        filters["query"] = str(result["query"])[:120]
    city = args.get("city") or result.get("city")
    if city:
        filters["city"] = str(city)[:64]
    return redact_dict(filters, max_depth=1)


def update_state_after_turn(
    state: dict[str, Any],
    *,
    intent: str,
    tool_results: list[dict[str, Any]],
    tool_args_by_name: dict[str, dict[str, Any]] | None = None,
    confirmation_id: UUID | None = None,
) -> dict[str, Any]:
    updated = copy.deepcopy(state)
    updated["current_intent"] = intent
    updated["pending_clarification"] = None
    tool_args_by_name = tool_args_by_name or {}

    if confirmation_id is not None:
        ids = list(updated.get("pending_confirmation_ids") or [])
        cid = str(confirmation_id)
        if cid not in ids:
            ids.append(cid)
        updated["pending_confirmation_ids"] = ids[-10:]

    last_results: list[dict[str, Any]] = []
    last_type: str | None = None
    filters = dict(updated.get("active_search_filters") or {})

    for tr in tool_results:
        if not tr.get("ok"):
            continue
        name = str(tr.get("tool_name") or "")
        args = tool_args_by_name.get(name) or {}
        rows = tr.get("results") or []
        if isinstance(rows, list) and rows:
            entity_type = _infer_entity_type(name, rows[0] if isinstance(rows[0], dict) else {})
            last_type = entity_type
            for idx, row in enumerate(rows[:MAX_CONVERSATION_RESULT_ITEMS], start=1):
                if isinstance(row, dict):
                    last_results.append(
                        _result_from_row(row, position=idx, entity_type=entity_type)
                    )
        single = tr.get("result")
        if isinstance(single, dict):
            entity_type = _infer_entity_type(name, single)
            last_type = entity_type
            last_results = [_result_from_row(single, position=1, entity_type=entity_type)]
        if name == "search_public_events":
            filters.update(_extract_search_filters(name, args, tr))

    if last_results:
        updated["last_results"] = last_results
        updated["last_result_type"] = last_type
        updated["selected_entity"] = last_results[0]
    updated["active_search_filters"] = filters
    return _sanitize_state_dict(updated)


def sanitize_state_for_role(
    state: dict[str, Any],
    *,
    roles: list[str],
    permissions: list[str],
) -> dict[str, Any]:
    """Drop entity references the active role cannot access."""
    _ = permissions
    clean = copy.deepcopy(state)
    role_set = set(roles or [])
    is_host = "host" in role_set or "super_admin" in role_set
    is_fan = user_is_fan_like(role_set)

    def _keep(item: dict[str, Any]) -> bool:
        et = item.get("entity_type")
        if et in _HOST_PRIVATE_ENTITY_TYPES and not is_host:
            return False
        if et in _FAN_PRIVATE_ENTITY_TYPES and not is_fan:
            return False
        if et == "host_event_private" and not is_host:
            return False
        return True

    clean["last_results"] = [
        item for item in (clean.get("last_results") or []) if _keep(item)
    ]
    selected = clean.get("selected_entity")
    if isinstance(selected, dict) and not _keep(selected):
        clean["selected_entity"] = clean["last_results"][0] if clean["last_results"] else None
    clean["draft_reference"] = None if not is_host else clean.get("draft_reference")
    clean["active_workflow"] = None
    return _sanitize_state_dict(clean)


def user_is_fan_like(role_set: set[str]) -> bool:
    return bool(role_set & {"buyer", "fan", "user", "ambassador", "sponsor", "host", "super_admin"})


def handle_role_transition(
    session: AssistantSession,
    *,
    new_role: str | None,
    roles: list[str],
    permissions: list[str],
) -> None:
    old_role = session.active_role
    if not new_role or new_role == old_role:
        return
    state = sanitize_state_for_role(
        get_conversation_state(session), roles=roles, permissions=permissions
    )
    save_conversation_state(session, state=state)
    session.active_role = new_role[:64]


def attach_anonymous_session(
    db: Session,
    *,
    session: AssistantSession,
    user: User,
    roles: list[str],
    permissions: list[str],
) -> None:
    if session.user_id is not None:
        return
    session.user_id = user.id
    session.mode = MODE_AUTHENTICATED
    session.anonymous_session_id = None
    state = sanitize_state_for_role(
        get_conversation_state(session), roles=roles, permissions=permissions
    )
    save_conversation_state(session, state=state)
    db.flush()


def cancel_pending_confirmations(
    db: Session,
    *,
    session: AssistantSession,
    user: User | None,
) -> None:
    if user is None:
        return
    from app.assistant import confirmation as confirmation_svc

    state = get_conversation_state(session)
    for raw_id in list(state.get("pending_confirmation_ids") or []):
        try:
            confirmation_svc.cancel_action(
                db, confirmation_id=UUID(str(raw_id)), user=user
            )
        except Exception:
            pass
    state["pending_confirmation_ids"] = []
    save_conversation_state(session, state=state)


def format_conversation_state(state: dict[str, Any]) -> str:
    """Compact JSON-like text for prompts."""
    parts: list[str] = []
    if state.get("current_intent"):
        parts.append(f"intent={state['current_intent']}")
    if state.get("last_result_type"):
        parts.append(f"last_result_type={state['last_result_type']}")
    filters = state.get("active_search_filters") or {}
    if filters:
        parts.append(f"filters={filters}")
    if state.get("selected_entity"):
        parts.append(f"selected={state['selected_entity']}")
    results = state.get("last_results") or []
    if results:
        labels = [
            f"{r.get('position')}. {r.get('label')} ({r.get('entity_type')})"
            for r in results[:MAX_CONVERSATION_RESULT_ITEMS]
        ]
        parts.append("results=" + "; ".join(labels))
    if state.get("pending_clarification"):
        parts.append(f"pending_clarification={state['pending_clarification']}")
    if state.get("draft_reference"):
        parts.append(f"draft_reference={state['draft_reference']}")
    return "\n".join(parts)
