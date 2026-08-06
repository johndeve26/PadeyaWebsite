"""Orchestrate Ask Pàdéyá / Pàdéyá Copilot chat turns."""

from __future__ import annotations

import logging
import secrets
from typing import Any, Iterator
from uuid import UUID

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from app.assistant import confirmation as confirmation_svc
from app.assistant import sessions as session_svc
from app.assistant.constants import (
    AUTH_PRODUCT_NAME,
    FLAG_ASSISTANT_ACTIONS_ENABLED,
    FLAG_ASSISTANT_AUTHENTICATED_ENABLED,
    FLAG_ASSISTANT_ENABLED,
    FLAG_ASSISTANT_EVENT_SEARCH_ENABLED,
    FLAG_ASSISTANT_PUBLIC_ENABLED,
    MODE_AUTHENTICATED,
    MODE_PUBLIC,
    PUBLIC_PRODUCT_NAME,
)
from app.assistant.intent import IntentResult, classify_intent
from app.assistant.knowledge.retrieve import retrieve_knowledge
from app.assistant.privacy import sanitize_page_context, sanitize_user_message
from app.assistant.prompts import get_system_prompt
from app.assistant.rate_limit import check_assistant_rate_limit
from app.assistant.schemas import Action, AssistantResponse, Card, Citation
from app.assistant.tools.executor import execute_tool
from app.assistant.tools.registry import list_tools_for_context
from app.core.config import get_settings
from app.users.models import User
from app.users.service import user_permission_codes, user_role_names

logger = logging.getLogger(__name__)


def _flag(name: str, default: bool = False) -> bool:
    return bool(getattr(get_settings(), name, default))


def assistant_flags() -> dict[str, bool]:
    enabled = _flag(FLAG_ASSISTANT_ENABLED, False)
    return {
        FLAG_ASSISTANT_ENABLED: enabled,
        FLAG_ASSISTANT_PUBLIC_ENABLED: enabled and _flag(FLAG_ASSISTANT_PUBLIC_ENABLED, False),
        FLAG_ASSISTANT_AUTHENTICATED_ENABLED: enabled
        and _flag(FLAG_ASSISTANT_AUTHENTICATED_ENABLED, False),
        FLAG_ASSISTANT_ACTIONS_ENABLED: enabled
        and _flag(FLAG_ASSISTANT_ACTIONS_ENABLED, False),
        FLAG_ASSISTANT_EVENT_SEARCH_ENABLED: enabled
        and _flag(FLAG_ASSISTANT_EVENT_SEARCH_ENABLED, True),
        "assistant_support_drafts_enabled": enabled
        and _flag("assistant_support_drafts_enabled", False),
        "assistant_admin_enabled": enabled and _flag("assistant_admin_enabled", False),
    }


def assert_assistant_allowed(*, user: User | None) -> dict[str, bool]:
    flags = assistant_flags()
    if not flags[FLAG_ASSISTANT_ENABLED]:
        raise HTTPException(status_code=404, detail="Assistant is not available")
    if user is None and not flags[FLAG_ASSISTANT_PUBLIC_ENABLED]:
        raise HTTPException(status_code=404, detail="Ask Pàdéyá is not available")
    if user is not None and not flags[FLAG_ASSISTANT_AUTHENTICATED_ENABLED]:
        # Authenticated users may still use public mode if public is on
        if not flags[FLAG_ASSISTANT_PUBLIC_ENABLED]:
            raise HTTPException(status_code=404, detail="Pàdéyá Copilot is not available")
    return flags


def public_status() -> dict[str, Any]:
    flags = assistant_flags()
    return {
        "assistant_enabled": flags[FLAG_ASSISTANT_ENABLED],
        "public_enabled": flags[FLAG_ASSISTANT_PUBLIC_ENABLED],
        "authenticated_enabled": flags[FLAG_ASSISTANT_AUTHENTICATED_ENABLED],
        "actions_enabled": flags[FLAG_ASSISTANT_ACTIONS_ENABLED],
        "event_search_enabled": flags[FLAG_ASSISTANT_EVENT_SEARCH_ENABLED],
        "product_public": PUBLIC_PRODUCT_NAME,
        "product_authenticated": AUTH_PRODUCT_NAME,
    }


def _call_provider(system_prompt: str, user_prompt: str) -> tuple[str, str | None, str | None, bool]:
    settings = get_settings()
    try:
        from app.ai.providers import get_ai_provider

        provider = get_ai_provider(settings)
        completion = provider.complete(
            system_prompt=system_prompt, user_prompt=user_prompt
        )
        text = (completion.text or "").strip()
        return (
            text,
            completion.provider,
            completion.model_name,
            bool(completion.used_fallback),
        )
    except Exception:
        logger.exception("assistant.provider_failed")
        return "", "none", None, True


def _build_user_prompt(
    *,
    message: str,
    intent: IntentResult,
    tool_results: list[dict[str, Any]],
    citations: list[Citation],
    page_context: dict[str, Any],
) -> str:
    parts = [f"User message:\n{message}"]
    parts.append(f"\nDetected intent: {intent.intent} (confidence={intent.confidence})")
    if page_context:
        parts.append(f"\nPage context (safe): {page_context}")
    if tool_results:
        # Keep tool payloads compact and already sanitized
        compact = []
        for tr in tool_results[:4]:
            compact.append(
                {
                    "tool": tr.get("tool_name"),
                    "ok": tr.get("ok"),
                    "count": tr.get("count"),
                    "results": (tr.get("results") or tr.get("result") or tr.get("summary")) ,
                    "error": tr.get("error"),
                }
            )
        parts.append(f"\nTool results:\n{compact}")
    if citations:
        parts.append(
            "\nCitations:\n"
            + "\n".join(f"- {c.title}: {c.url}" for c in citations[:6])
        )
    parts.append(
        "\nRespond helpfully. Do not invent prices, routes, or private data. "
        "Cite sources when using knowledge. Prefer short actionable answers."
    )
    return "\n".join(parts)


def _fallback_text(
    *,
    intent: IntentResult,
    tool_results: list[dict[str, Any]],
    citations: list[Citation],
) -> str:
    if intent.refuse:
        if intent.intent in {"injection", "abuse"}:
            return (
                "I can't help with that request. "
                "If you need product help, ask about events, pages, or open Support."
            )
        return (
            "I can't perform high-risk or finance actions. "
            "Use the Pàdéyá product UI for publishing, refunds, and payouts — "
            "or contact Support if you're stuck."
        )
    for tr in tool_results:
        if tr.get("tool_name") == "search_public_events" and tr.get("results"):
            titles = ", ".join(
                str(r.get("title")) for r in tr["results"][:3] if r.get("title")
            )
            return f"Here are some upcoming events I found: {titles}."
        if tr.get("path"):
            return f"You can open {tr.get('title') or 'that page'} at {tr.get('path')}."
        if tr.get("summary"):
            return str(tr["summary"])
    if citations:
        return (
            f"I found related info on {citations[0].title}. "
            f"See {citations[0].url}."
        )
    if intent.reason == "auth_required_for_intent":
        return "Sign in to view your account-specific information in Pàdéyá Copilot."
    return (
        "I can help you find events, pages, and help articles on Pàdéyá. "
        "Try asking about events near you, or say “open help”."
    )


def run_chat_turn(
    db: Session,
    *,
    request: Request,
    user: User | None,
    message: str,
    session_id: UUID | None,
    page_context_raw: dict[str, Any] | None,
    anonymous_session_id: str | None,
    timezone: str | None = None,
) -> tuple[AssistantResponse, list[dict[str, Any]], str]:
    """
    Execute one chat turn. Returns (response, stream_events_meta, anonymous_sid).

    stream_events_meta is a list of SSE event dicts collected during the turn
    (tools/citations) for the streaming layer to replay.
    """
    flags = assert_assistant_allowed(user=user)
    anon_sid = anonymous_session_id
    if user is None and not anon_sid:
        anon_sid = session_svc.new_anonymous_session_id()

    check_assistant_rate_limit(
        request, user_id=user.id if user else None, anonymous_session_id=anon_sid
    )

    page_context = sanitize_page_context(page_context_raw)
    clean_message = sanitize_user_message(message)
    if not clean_message:
        raise HTTPException(status_code=400, detail="Message required")

    if session_id:
        session = session_svc.get_session_for_actor(
            db,
            session_id=session_id,
            user=user,
            anonymous_session_id=anon_sid,
        )
    else:
        session = session_svc.create_session(
            db,
            user=user,
            anonymous_session_id=anon_sid,
            active_role=page_context.get("role"),
            metadata_json={"timezone": timezone} if timezone else None,
        )
        anon_sid = session.anonymous_session_id or anon_sid

    mode = (
        MODE_AUTHENTICATED
        if user is not None and flags[FLAG_ASSISTANT_AUTHENTICATED_ENABLED]
        else MODE_PUBLIC
    )
    roles = user_role_names(user) if user else []
    permissions = user_permission_codes(user) if user else []
    intent = classify_intent(
        clean_message,
        authenticated=user is not None,
        roles=roles,
        permissions=permissions,
        page_context=page_context,
    )
    trace_id = secrets.token_hex(8)
    stream_meta: list[dict[str, Any]] = []

    session_svc.add_message(
        db,
        session=session,
        role="user",
        content=clean_message,
        safety_status="ok" if not intent.refuse else intent.reason,
        trace_id=trace_id,
    )

    tool_results: list[dict[str, Any]] = []
    citations: list[Citation] = []
    cards: list[Card] = []
    actions: list[Action] = []
    confirmation_id: UUID | None = None

    max_steps = int(getattr(get_settings(), "assistant_max_tool_steps", None) or 4)

    if not intent.refuse:
        hints = list(intent.tool_hints)
        if intent.intent in {"search_events", "unknown"} and flags[
            FLAG_ASSISTANT_EVENT_SEARCH_ENABLED
        ]:
            if "search_public_events" not in hints:
                hints.insert(0, "search_public_events")
        if intent.route_key and "navigate_to_route" not in hints:
            hints.append("navigate_to_route")

        allowed = {
            t.name
            for t in list_tools_for_context(
                authenticated=user is not None,
                roles=roles,
                permissions=permissions,
                flags=flags,
            )
        }

        for name in hints[:max_steps]:
            if name not in allowed:
                continue
            args: dict[str, Any] = {"query": clean_message, "q": clean_message}
            if intent.route_key:
                args["route_key"] = intent.route_key
            stream_meta.append({"event": "tool_started", "data": {"tool_name": name}})
            result = execute_tool(
                db,
                tool_name=name,
                args=args,
                user=user,
                page_context=page_context,
                confirmed=False,
            )
            tool_results.append(result)
            stream_meta.append(
                {
                    "event": "tool_completed",
                    "data": {
                        "tool_name": name,
                        "ok": result.get("ok"),
                        "error": result.get("error"),
                        "duration_ms": result.get("duration_ms"),
                    },
                }
            )

            if result.get("error") == "confirmation_required" and user is not None:
                if flags[FLAG_ASSISTANT_ACTIONS_ENABLED]:
                    conf = confirmation_svc.create_confirmation(
                        db, user=user, tool_name=name, args=args
                    )
                    confirmation_id = conf.id
                    actions.append(
                        Action(
                            type="confirm",
                            label=f"Confirm {name.replace('_', ' ')}",
                            tool_name=name,
                            confirmation_id=conf.id,
                            requires_confirmation=True,
                        )
                    )
                    stream_meta.append(
                        {
                            "event": "confirmation",
                            "data": {
                                "confirmation_id": str(conf.id),
                                "tool_name": name,
                                "expires_at": conf.expires_at.isoformat(),
                            },
                        }
                    )

            # Cards from event/host results
            for item in (result.get("results") or [])[:4]:
                if not isinstance(item, dict):
                    continue
                title = item.get("title") or item.get("display_name")
                url = item.get("url") or item.get("path")
                if title and url:
                    cards.append(
                        Card(
                            type="result",
                            title=str(title),
                            subtitle=item.get("city") or item.get("status"),
                            url=str(url),
                        )
                    )
            if result.get("path") and result.get("title"):
                actions.append(
                    Action(
                        type="navigate",
                        label=f"Open {result['title']}",
                        route_key=result.get("route_key"),
                        url=result.get("path"),
                    )
                )

        # Knowledge retrieval for informational intents
        if intent.intent in {
            "search_pages",
            "search_resources",
            "unknown",
            "explain_page",
            "chitchat",
        }:
            for hit in retrieve_knowledge(db, query=clean_message, top_k=4):
                cit = Citation(
                    title=str(hit.get("title") or "Pàdéyá"),
                    url=str(hit.get("url") or "/"),
                    snippet=hit.get("snippet"),
                    source_type=hit.get("source_type"),
                    route_key=hit.get("route_key"),
                )
                citations.append(cit)
                stream_meta.append(
                    {
                        "event": "citation",
                        "data": cit.model_dump(),
                    }
                )

    system_prompt = get_system_prompt(mode, page_context.get("role"))
    user_prompt = _build_user_prompt(
        message=clean_message,
        intent=intent,
        tool_results=tool_results,
        citations=citations,
        page_context=page_context,
    )

    text = ""
    provider = None
    model = None
    used_fallback = True
    if not intent.refuse:
        text, provider, model, used_fallback = _call_provider(system_prompt, user_prompt)
    if not text:
        text = _fallback_text(
            intent=intent, tool_results=tool_results, citations=citations
        )
        used_fallback = True

    product = AUTH_PRODUCT_NAME if mode == MODE_AUTHENTICATED else PUBLIC_PRODUCT_NAME
    safety = "refused" if intent.refuse else "ok"
    assistant_msg = session_svc.add_message(
        db,
        session=session,
        role="assistant",
        content=text,
        structured_content_json={
            "citations": [c.model_dump() for c in citations],
            "cards": [c.model_dump() for c in cards],
            "actions": [a.model_dump(mode="json") for a in actions],
            "intent": intent.intent,
        },
        model=model,
        safety_status=safety,
        trace_id=trace_id,
    )

    response = AssistantResponse(
        session_id=session.id,
        message_id=assistant_msg.id,
        mode=mode,
        product_name=product,
        text=text,
        citations=citations,
        cards=cards,
        actions=actions,
        safety_status=safety,
        used_fallback=used_fallback,
        provider=provider,
        model=model,
        intent=intent.intent,
        confirmation_id=confirmation_id,
        trace_id=trace_id,
    )
    return response, stream_meta, anon_sid or ""
