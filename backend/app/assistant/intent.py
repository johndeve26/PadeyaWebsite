"""Rule-based intent classification for the assistant."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.assistant.constants import (
    INTENT_ABUSE,
    INTENT_ACCOUNT,
    INTENT_CHITCHAT,
    INTENT_CONFIRM_ACTION,
    INTENT_CREATE_DRAFT,
    INTENT_EXPLAIN_PAGE,
    INTENT_HIGH_RISK,
    INTENT_HOST_EVENTS,
    INTENT_INJECTION,
    INTENT_NAVIGATE,
    INTENT_ORDERS,
    INTENT_SEARCH_EVENTS,
    INTENT_SEARCH_HOSTS,
    INTENT_SEARCH_MEMORIES,
    INTENT_SEARCH_PAGES,
    INTENT_SEARCH_PRODUCTS,
    INTENT_SEARCH_RESOURCES,
    INTENT_SUPPORT,
    INTENT_TICKETS,
    INTENT_UNKNOWN,
)
from app.assistant.routes.auth_registry import resolve_auth_route
from app.assistant.routes.public_registry import resolve_public_route

_INJECTION_PATTERNS = (
    r"ignore (all |any |your |the )?(previous |prior |above )?(instructions|rules)",
    r"disregard (your|the) (system|safety|rules|instructions)",
    r"you are now (dan|jailbroken|unrestricted)",
    r"reveal (your |the )?(system prompt|hidden prompt|instructions|admin secrets?)",
    r"(show|give me|leak).*(admin secrets?|system prompt|hidden prompt)",
    r"act as if you have no restrictions",
    r"<\|system\|>",
)

_ABUSE_PATTERNS = (
    r"\b(kill yourself|kys)\b",
    r"\b(child porn|csam)\b",
    r"\b(how to make a bomb)\b",
)

_HIGH_RISK_PATTERNS = (
    r"\b(refund|chargeback|payout|wire transfer)\b",
    r"\b(publish\b.{0,40}\bevent|delete (the )?event|ban user|impersonat)",
    r"\b(reveal|show|give me).*(qr|password|api[_ ]?key|bank|card number|admin secrets?)",
    r"\b(drop table|execute sql|shell command)\b",
)


@dataclass
class IntentResult:
    intent: str
    confidence: float = 0.5
    route_key: str | None = None
    path: str | None = None
    tool_hints: list[str] = field(default_factory=list)
    high_risk: bool = False
    refuse: bool = False
    reason: str | None = None


def _match_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(p, text, flags=re.I) for p in patterns)


def classify_intent(
    message: str,
    *,
    authenticated: bool = False,
    roles: list[str] | None = None,
    permissions: list[str] | None = None,
    page_context: dict | None = None,
) -> IntentResult:
    text = (message or "").strip()
    if not text:
        return IntentResult(intent=INTENT_UNKNOWN, confidence=0.0)

    if _match_any(text, _INJECTION_PATTERNS):
        return IntentResult(
            intent=INTENT_INJECTION,
            confidence=0.95,
            refuse=True,
            high_risk=True,
            reason="prompt_injection",
        )
    if _match_any(text, _ABUSE_PATTERNS):
        return IntentResult(
            intent=INTENT_ABUSE,
            confidence=0.95,
            refuse=True,
            high_risk=True,
            reason="abuse",
        )
    if _match_any(text, _HIGH_RISK_PATTERNS):
        return IntentResult(
            intent=INTENT_HIGH_RISK,
            confidence=0.85,
            high_risk=True,
            refuse=True,
            reason="high_risk_request",
            tool_hints=[],
        )

    lower = text.lower()
    public = resolve_public_route(text)

    if page_context and any(
        w in lower for w in ("this page", "current page", "what is this", "explain this", "help with this")
    ):
        return IntentResult(
            intent=INTENT_EXPLAIN_PAGE,
            confidence=0.85,
            route_key=(page_context or {}).get("route_key"),
            tool_hints=["explain_current_page"],
        )

    # Auth-sensitive intents before navigate shortcuts ("where is my ticket?")
    auth_rules: list[tuple[str, tuple[str, ...], list[str], float]] = [
        (INTENT_TICKETS, ("my ticket", "upcoming ticket", "ticket wallet", "where is my ticket"), ["list_my_upcoming_tickets"], 0.9),
        (INTENT_ORDERS, ("my order", "order history", "my purchase"), ["get_my_order_summary"], 0.85),
        (INTENT_HOST_EVENTS, ("my events", "host studio", "manage events"), ["list_my_events"], 0.8),
        (INTENT_ACCOUNT, ("my account", "my roles", "who am i"), ["get_my_account_summary", "get_my_roles"], 0.75),
        (INTENT_CREATE_DRAFT, ("draft description", "create event", "write description"), ["draft_event_description", "create_event_draft"], 0.7),
    ]
    for intent, needles, tools, conf in auth_rules:
        if any(n in lower for n in needles):
            if not authenticated:
                return IntentResult(
                    intent=intent,
                    confidence=conf,
                    tool_hints=[],
                    reason="auth_required_for_intent",
                )
            return IntentResult(
                intent=intent,
                confidence=conf,
                tool_hints=tools,
            )

    # Deterministic navigation
    if public and any(
        w in lower for w in ("go to", "open", "take me", "navigate", "where is", "show me")
    ):
        return IntentResult(
            intent=INTENT_NAVIGATE,
            confidence=0.9,
            route_key=public.key,
            path=public.path,
            tool_hints=["navigate_to_route"],
        )

    if authenticated:
        auth = resolve_auth_route(text, roles=roles, permissions=permissions)
        if auth and any(
            w in lower for w in ("go to", "open", "take me", "navigate", "where is", "show")
        ):
            return IntentResult(
                intent=INTENT_NAVIGATE,
                confidence=0.9,
                route_key=auth.key,
                path=auth.path,
                tool_hints=["navigate_to_route"],
            )

    rules: list[tuple[str, tuple[str, ...], list[str], float]] = [
        (INTENT_SEARCH_EVENTS, ("event", "what's on", "tonight", "concert", "party"), ["search_public_events"], 0.8),
        (INTENT_SEARCH_HOSTS, ("host", "promoter", "legacy page"), ["search_public_hosts"], 0.75),
        (INTENT_SEARCH_PRODUCTS, ("merch", "shop", "store", "buy hoodie"), ["search_public_products"], 0.75),
        (INTENT_SEARCH_MEMORIES, ("memory", "memories", "photos", "album"), ["search_public_memories"], 0.75),
        (INTENT_SEARCH_RESOURCES, ("blog", "article", "guide", "resource"), ["search_public_resources"], 0.7),
        (INTENT_SUPPORT, ("support", "help desk", "support ticket", "contact support"), ["create_support_ticket_draft", "search_help"], 0.8),
        (INTENT_CONFIRM_ACTION, ("confirm", "yes do it", "go ahead"), [], 0.6),
        (INTENT_CHITCHAT, ("hello", "hi ", "hey", "thanks", "thank you"), [], 0.55),
        (INTENT_SEARCH_PAGES, ("where can i", "how do i find", "how do i become", "page for"), ["search_public_pages", "navigate_to_route"], 0.65),
    ]

    for intent, needles, tools, conf in rules:
        if any(n in lower for n in needles):
            return IntentResult(
                intent=intent,
                confidence=conf,
                tool_hints=tools,
                route_key=public.key if public else None,
                path=public.path if public else None,
            )

    if public:
        return IntentResult(
            intent=INTENT_NAVIGATE,
            confidence=0.55,
            route_key=public.key,
            path=public.path,
            tool_hints=["navigate_to_route", "search_public_pages"],
        )

    return IntentResult(
        intent=INTENT_UNKNOWN,
        confidence=0.3,
        tool_hints=["search_public_pages", "search_help"],
    )
