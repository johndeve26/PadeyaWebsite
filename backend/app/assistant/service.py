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
    INTENT_SEARCH_EVENTS,
    MODE_AUTHENTICATED,
    MODE_PUBLIC,
    PUBLIC_PRODUCT_NAME,
)
from app.assistant.context import (
    attach_anonymous_session,
    build_context_user_prompt,
    get_conversation_state,
    get_session_summary,
    handle_role_transition,
    load_scrubbed_history,
    maybe_update_summary,
    resolve_follow_up,
    resolve_output_token_limit,
    save_conversation_state,
    update_state_after_turn,
)
from app.assistant.context.tokens import load_context_budgets, trim_knowledge_citations
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


def public_status(db: Session | None = None) -> dict[str, Any]:
    flags = assistant_flags()
    payload: dict[str, Any] = {
        "assistant_enabled": flags[FLAG_ASSISTANT_ENABLED],
        "public_enabled": flags[FLAG_ASSISTANT_PUBLIC_ENABLED],
        "authenticated_enabled": flags[FLAG_ASSISTANT_AUTHENTICATED_ENABLED],
        "actions_enabled": flags[FLAG_ASSISTANT_ACTIONS_ENABLED],
        "event_search_enabled": flags[FLAG_ASSISTANT_EVENT_SEARCH_ENABLED],
        "product_public": PUBLIC_PRODUCT_NAME,
        "product_authenticated": AUTH_PRODUCT_NAME,
        "ai_feature_enabled": False,
        "ai_provider_ready": False,
    }
    if db is None:
        return payload

    from app.ai.constants import FEATURE_PLATFORM_ASSISTANT_CHAT
    from app.ai.feature_routing import (
        ensure_default_provider_profiles,
        get_or_create_feature_route,
        invoke_config_for_profile,
    )
    from app.ai.feature_toggles import is_feature_enabled
    from app.ai.models import AIProviderProfile
    from app.core.config import get_settings

    ensure_default_provider_profiles(db)
    route = get_or_create_feature_route(db, FEATURE_PLATFORM_ASSISTANT_CHAT)
    db.commit()
    primary = (
        db.get(AIProviderProfile, route.primary_provider_id)
        if route.primary_provider_id
        else None
    )
    payload["ai_feature_enabled"] = is_feature_enabled(
        FEATURE_PLATFORM_ASSISTANT_CHAT, db=db
    )
    env_key = bool((get_settings().ai_api_key or "").strip())
    provider_ready = env_key
    if primary and primary.provider_type != "template_fallback":
        cfg = invoke_config_for_profile(
            primary, model_override=None, max_tokens_override=None
        )
        provider_ready = provider_ready or bool(cfg.api_key)
    payload["ai_provider_ready"] = provider_ready
    return payload


def _call_provider(
    db: Session,
    *,
    system_prompt: str,
    user_prompt: str,
    max_output_tokens: int | None = None,
) -> tuple[str, str | None, str | None, bool, int]:
    """Route through AI Control Center (provider profiles + runtime settings)."""
    from fastapi import HTTPException

    from app.ai.admin_controls import assert_spend_allows_network
    from app.ai.constants import FEATURE_PLATFORM_ASSISTANT_CHAT
    from app.ai.feature_routing import complete_for_feature
    from app.ai.feature_toggles import assert_ai_globally_available, is_feature_enabled

    applied_limit = resolve_output_token_limit(task_limit=max_output_tokens)

    try:
        assert_ai_globally_available()
    except HTTPException:
        logger.info("assistant.provider_skipped kill_switch")
        return "", "none", None, True, applied_limit

    if not is_feature_enabled(FEATURE_PLATFORM_ASSISTANT_CHAT, db=db):
        logger.info("assistant.provider_skipped feature_disabled")
        return "", "none", None, True, applied_limit

    force_template = False
    try:
        spend = assert_spend_allows_network(db)
        force_template = bool(spend.get("force_template_fallback"))
    except HTTPException as exc:
        logger.warning("assistant.spend_gate_blocked: %s", exc.detail)
        return "", "none", None, True, applied_limit
    except Exception as exc:
        logger.warning("assistant.spend_gate_blocked: %s", exc)
        return "", "none", None, True, applied_limit

    try:
        routed = complete_for_feature(
            db,
            feature_key=FEATURE_PLATFORM_ASSISTANT_CHAT,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            force_template_only=force_template,
            max_tokens_override=applied_limit,
        )
        result = routed.result
        text = (result.text or "").strip()
        if result.used_fallback and result.error_message:
            logger.warning(
                "assistant.provider_fallback provider=%s error=%s chain=%s",
                result.provider,
                result.error_message,
                ",".join(routed.chain[-3:]),
            )
        return (
            text,
            result.provider,
            result.model_name,
            bool(result.used_fallback),
            applied_limit,
        )
    except Exception:
        logger.exception("assistant.provider_failed")
        return "", "none", None, True, applied_limit


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
        if tr.get("tool_name") == "get_my_ticket_summary" and tr.get("ok"):
            return str(
                tr.get("summary")
                or f"You have {tr.get('total_tickets', 0)} ticket(s) on your account."
            )
        if tr.get("tool_name") == "get_my_following_summary" and tr.get("ok"):
            return str(tr.get("summary") or "You are not following any hosts yet.")
        if tr.get("tool_name") == "list_upcoming_events_from_followed_hosts" and tr.get("ok"):
            return str(
                tr.get("summary")
                or "No upcoming events from hosts you follow right now."
            )
        if tr.get("tool_name") == "get_my_audience_summary" and tr.get("ok"):
            return str(tr.get("summary") or "Audience stats loaded.")
        if tr.get("tool_name") == "get_my_event_analytics" and tr.get("ok"):
            return str(tr.get("summary") or "Event analytics loaded.")
        if tr.get("tool_name") == "get_my_fan_connect_summary" and tr.get("ok"):
            return str(tr.get("summary") or "Fan Connect summary loaded.")
        if tr.get("tool_name") == "get_my_fan_connect_inbox_summary" and tr.get("ok"):
            return str(tr.get("summary") or "Fan Connect inbox summary loaded.")
        if tr.get("tool_name") == "list_my_past_tickets" and tr.get("ok"):
            count = tr.get("count") or len(tr.get("results") or [])
            if count:
                return str(
                    tr.get("summary")
                    or f"You have {count} past ticket(s) on your account."
                )
            return "You have no past tickets on your account yet."
        if tr.get("tool_name") == "list_my_audience_segments" and tr.get("ok"):
            return str(tr.get("summary") or "Audience segments loaded.")
        if tr.get("tool_name") == "get_my_announcements_summary" and tr.get("ok"):
            return str(tr.get("summary") or "Announcements summary loaded.")
        if tr.get("tool_name") == "get_my_host_ambassador_analytics" and tr.get("ok"):
            return str(tr.get("summary") or "Ambassador program analytics loaded.")
        if tr.get("tool_name") == "get_my_referral_summary" and tr.get("ok"):
            return str(tr.get("summary") or "Referral summary loaded.")
        if tr.get("tool_name") == "get_my_ambassador_earnings" and tr.get("ok"):
            return str(tr.get("summary") or "Ambassador earnings loaded.")
        if tr.get("tool_name") == "list_my_ambassador_campaigns" and tr.get("ok"):
            return str(tr.get("summary") or "Ambassador campaigns loaded.")
        if tr.get("tool_name") == "list_my_referral_links" and tr.get("ok"):
            return str(tr.get("summary") or "Referral links loaded.")
        if tr.get("tool_name") == "get_my_sponsor_overview" and tr.get("ok"):
            return str(tr.get("summary") or "Sponsor overview loaded.")
        if tr.get("tool_name") == "list_my_sponsor_campaigns" and tr.get("ok"):
            return str(tr.get("summary") or "Sponsor campaigns loaded.")
        if tr.get("tool_name") == "list_my_sponsor_deals" and tr.get("ok"):
            return str(tr.get("summary") or "Sponsor deals loaded.")
        if tr.get("tool_name") == "list_my_sponsor_applications" and tr.get("ok"):
            return str(tr.get("summary") or "Sponsor applications pipeline loaded.")
        if tr.get("tool_name") == "list_my_sponsor_workspaces" and tr.get("ok"):
            return str(tr.get("summary") or "Sponsor workspaces loaded.")
        if tr.get("tool_name") == "search_public_sponsors" and tr.get("ok"):
            count = tr.get("count") or len(tr.get("results") or [])
            if count:
                names = ", ".join(
                    str(r.get("display_name"))
                    for r in (tr.get("results") or [])[:3]
                    if r.get("display_name")
                )
                return f"Found {count} sponsor profile(s): {names}."
            return "No public sponsor profiles matched that search."
        if tr.get("tool_name") == "get_public_pricing" and tr.get("ok"):
            summary = tr.get("summary")
            if summary:
                return str(summary)
            host_rows = tr.get("host_fee_categories") or []
            if host_rows:
                bits = [
                    f"{row.get('label')}: {row.get('description')}"
                    for row in host_rows[:3]
                    if isinstance(row, dict)
                ]
                return (
                    "Host fees on Pàdéyá are deducted from earnings on successful sales. "
                    + " ".join(bits)
                    + " See /pricing for the full public breakdown."
                )
        if tr.get("tool_name") == "get_my_order_summary" and tr.get("ok"):
            count = tr.get("count") or len(tr.get("results") or [])
            return f"You have {count} recent order(s) on your account."
        if tr.get("tool_name") == "list_my_upcoming_tickets" and tr.get("ok"):
            count = tr.get("count") or len(tr.get("results") or [])
            if count:
                titles = ", ".join(
                    str(r.get("event_title"))
                    for r in (tr.get("results") or [])[:3]
                    if r.get("event_title")
                )
                return f"You have {count} upcoming ticket(s): {titles}."
            return "You have no upcoming tickets right now."
        if tr.get("tool_name") == "search_help" and tr.get("ok"):
            support = tr.get("support") or {}
            hub = tr.get("hub") or {}
            support_url = support.get("url") or "/support"
            help_url = hub.get("url") or "/help"
            results = tr.get("results") or []
            if results:
                first = results[0]
                return (
                    f"Browse Help at {help_url} or contact Support at {support_url}. "
                    f"Relevant article: {first.get('title')} ({first.get('url')})."
                )
            return (
                f"Contact Support at {support_url}, or browse the Help Center at {help_url}."
            )
        if tr.get("tool_name") == "search_public_events" and tr.get("ok"):
            if tr.get("summary"):
                return str(tr["summary"])
            if tr.get("results"):
                titles = ", ".join(
                    str(r.get("title")) for r in tr["results"][:3] if r.get("title")
                )
                return f"Here are some upcoming events I found: {titles}."
            return (
                "I could not find matching upcoming events. "
                "Tell me a city, when (tonight / this weekend), or a vibe and I will search again."
            )
        if tr.get("tool_name") == "get_my_event_recommendations" and tr.get("ok"):
            return str(
                tr.get("summary")
                or "Tell me your city and vibe so I can recommend better events."
            )
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
        try:
            session = session_svc.get_session_for_actor(
                db,
                session_id=session_id,
                user=user,
                anonymous_session_id=anon_sid,
            )
        except HTTPException as exc:
            # Stale browser session_id + rotated anonymous cookie → start fresh
            # instead of failing the follow-up turn.
            if exc.status_code in {403, 404, 410} and user is None:
                session = session_svc.create_session(
                    db,
                    user=None,
                    anonymous_session_id=anon_sid,
                    active_role=page_context.get("role"),
                    metadata_json={"timezone": timezone} if timezone else None,
                )
                anon_sid = session.anonymous_session_id or anon_sid
            elif exc.status_code in {403, 404, 410} and user is not None:
                session = session_svc.create_session(
                    db,
                    user=user,
                    anonymous_session_id=None,
                    active_role=page_context.get("role"),
                    metadata_json={"timezone": timezone} if timezone else None,
                )
            else:
                raise
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

    if user is not None and session.user_id is None and session.anonymous_session_id:
        if anon_sid and session.anonymous_session_id == anon_sid:
            attach_anonymous_session(
                db,
                session=session,
                user=user,
                roles=roles,
                permissions=permissions,
            )
            anon_sid = session_svc.new_anonymous_session_id()

    handle_role_transition(
        session,
        new_role=page_context.get("role"),
        roles=roles,
        permissions=permissions,
    )

    recent_history = load_scrubbed_history(db, session=session)
    conversation_state = get_conversation_state(session)
    session_summary = get_session_summary(session)

    intent = classify_intent(
        clean_message,
        authenticated=user is not None,
        roles=roles,
        permissions=permissions,
        page_context=page_context,
    )
    follow_up = resolve_follow_up(
        clean_message, state=conversation_state, intent=intent
    )

    if follow_up.clarification and follow_up.skip_provider:
        trace_id = secrets.token_hex(8)
        session_svc.add_message(
            db,
            session=session,
            role="user",
            content=clean_message,
            safety_status="ok",
            trace_id=trace_id,
        )
        clarification = follow_up.clarification
        conversation_state["pending_clarification"] = clarification
        save_conversation_state(session, state=conversation_state)
        db.commit()
        db.refresh(session)
        assistant_msg = session_svc.add_message(
            db,
            session=session,
            role="assistant",
            content=clarification,
            structured_content_json={"intent": intent.intent, "clarification": True},
            safety_status="ok",
            trace_id=trace_id,
        )
        response = AssistantResponse(
            session_id=session.id,
            message_id=assistant_msg.id,
            mode=mode,
            product_name=AUTH_PRODUCT_NAME if mode == MODE_AUTHENTICATED else PUBLIC_PRODUCT_NAME,
            text=clarification,
            citations=[],
            cards=[],
            actions=[],
            safety_status="ok",
            used_fallback=False,
            provider=None,
            model=None,
            intent=intent.intent,
            confirmation_id=None,
            trace_id=trace_id,
        )
        return response, [], anon_sid or ""

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
    tool_args_by_name: dict[str, dict[str, Any]] = {}
    citations: list[Citation] = []
    cards: list[Card] = []
    actions: list[Action] = []
    confirmation_id: UUID | None = None

    max_steps = int(getattr(get_settings(), "assistant_max_tool_steps", None) or 4)
    ctx_budgets = load_context_budgets()

    if not intent.refuse:
        hints = list(follow_up.tool_hints or intent.tool_hints)
        if intent.intent in {"search_events", "unknown"} and flags[
            FLAG_ASSISTANT_EVENT_SEARCH_ENABLED
        ]:
            if "search_public_events" not in hints:
                hints.insert(0, "search_public_events")
        # Prefer live search over bare navigation for event discovery.
        if (
            intent.route_key
            and "navigate_to_route" not in hints
            and intent.intent != INTENT_SEARCH_EVENTS
        ):
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

        from app.assistant.tools.public_search import extract_event_search_query

        for name in hints[:max_steps]:
            if name not in allowed:
                continue
            args: dict[str, Any] = {"query": clean_message, "q": clean_message}
            if name in {"search_public_events", "get_my_event_recommendations"}:
                needle, needs_prefs, filters = extract_event_search_query(clean_message)
                args = {
                    "query": needle,
                    "q": needle,
                    "browse_upcoming": needs_prefs,
                    **filters,
                }
            if follow_up.tool_args:
                args.update(follow_up.tool_args)
            if intent.route_key and name == "navigate_to_route":
                args["route_key"] = intent.route_key
            tool_args_by_name[name] = args
            stream_meta.append({"event": "tool_started", "data": {"tool_name": name}})
            result = execute_tool(
                db,
                tool_name=name,
                args=args,
                user=user,
                page_context=page_context,
                confirmed=False,
            )
            result["tool_name"] = name
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
                            subtitle=(
                                item.get("host_display_name")
                                or item.get("city")
                                or item.get("status")
                            ),
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
            if (
                name == "get_my_ticket_summary"
                and result.get("ok")
                and intent.path
            ):
                actions.append(
                    Action(
                        type="navigate",
                        label="Open My tickets",
                        route_key=intent.route_key or "fan_tickets",
                        url=intent.path or "/dashboard/tickets",
                    )
                )
            if name == "get_my_audience_summary" and result.get("ok"):
                actions.append(
                    Action(
                        type="navigate",
                        label="Open Audience CRM",
                        route_key="host_audience",
                        url="/host/audience",
                    )
                )
            if name == "get_public_pricing" and result.get("ok"):
                actions.append(
                    Action(
                        type="navigate",
                        label="Open Pricing",
                        route_key="pricing",
                        url=result.get("url") or "/pricing",
                    )
                )

        # Knowledge retrieval for informational intents
        if intent.intent in {
            "search_pages",
            "search_resources",
            "unknown",
            "explain_page",
            "chitchat",
            "pricing",
            "tickets",
            "orders",
            "support",
            "insights",
        }:
            for hit in retrieve_knowledge(
                db, query=clean_message, top_k=ctx_budgets.knowledge_top_k
            ):
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

        citations = trim_knowledge_citations(
            citations,
            top_k=ctx_budgets.knowledge_top_k,
            absolute_max=ctx_budgets.knowledge_max,
        )

        if follow_up.navigate_url:
            actions.append(
                Action(
                    type="navigate",
                    label=follow_up.navigate_label or "Open",
                    url=follow_up.navigate_url,
                )
            )

    conversation_state = update_state_after_turn(
        conversation_state,
        intent=intent.intent,
        tool_results=tool_results,
        tool_args_by_name=tool_args_by_name,
        confirmation_id=confirmation_id,
    )
    save_conversation_state(session, state=conversation_state)
    session_summary = maybe_update_summary(
        db,
        session=session,
        recent_turn_count=len(recent_history),
        state=conversation_state,
    )

    system_prompt = get_system_prompt(mode, page_context.get("role"))
    user_prompt = build_context_user_prompt(
        message=clean_message,
        intent=intent,
        tool_results=tool_results,
        citations=citations,
        page_context=page_context,
        session_summary=session_summary,
        recent_turns=recent_history,
        conversation_state=conversation_state,
    )

    text = ""
    provider = None
    model = None
    used_fallback = True
    output_token_limit = resolve_output_token_limit()
    if not intent.refuse:
        text, provider, model, used_fallback, output_token_limit = _call_provider(
            db,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_output_tokens=output_token_limit,
        )
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
            "output_token_limit": output_token_limit,
            "context_turns": len(recent_history),
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
