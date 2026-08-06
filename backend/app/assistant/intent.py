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
    INTENT_PRICING,
    INTENT_INSIGHTS,
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


_FEE_PRICING_PATTERNS = (
    r"\b(fee|fees|commission|pricing|platform fee|service fee|processing fee)\b",
    r"\bhow much (does|do|is|are)\b.{0,40}\b(cost|charge|fee|fees|pay|take)\b",
    r"\bwhat (?:do|does|are) (?:hosts?|hosting) (?:pay|cost|charge)\b",
    r"\bhost(?:ing)? fee\b",
    r"\bfor event hosting\b",
    r"\bi mean\b.{0,40}\bhosting\b",
    r"\bhosting events?\b.{0,30}\b(fee|fees|cost|price|pricing|pay|charge)\b",
    r"\b(fee|fees|cost|price|pricing)\b.{0,30}\bhosting events?\b",
)

_BECOME_HOST_PATTERNS = (
    r"\bhow (?:to|do i) become a host\b",
    r"\bbecome a host\b",
    r"\bstart hosting\b",
    r"\bhost on p[aà]d[eé]y[aá]\b",
)

_FOLLOWING_PATTERNS = (
    r"\bhow many hosts?\b.{0,40}\b(follow|following)\b",
    r"\bhosts? (?:am i|i'?m|i am) following\b",
    r"\bhow many (?:people|hosts?) (?:do )?i follow\b",
)

_FOLLOWED_HOST_EVENTS_PATTERNS = (
    r"\b(?:which|what) (?:of )?(?:the )?hosts?\b.{0,40}\b(hosting|event|soon|upcoming)\b",
    r"\bhosts? (?:i|you) follow\b.{0,60}\b(event|upcoming|soon|hosting)\b",
    r"\bevents? from (?:hosts? )?(?:i|you) follow\b",
    r"\bfollowed hosts?\b.{0,40}\b(event|upcoming|soon|hosting)\b",
    r"\bupcoming events? from (?:my )?followed\b",
    r"\bwhich host\b.{0,30}\b(hosting|event|soon)\b",
)

_FOLLOWER_PATTERNS = (
    r"\bhow many followers?\b",
    r"\bfollower count\b",
    r"\bhow many follow(?:ers)? do i have\b",
)

_AUDIENCE_PATTERNS = (
    r"\bhow many (?:people|fans|audience|customers)\b",
    r"\bmarketing opt.?in\b",
    r"\bopted? in\b",
    r"\baudience size\b",
    r"\bmy audience\b",
)

_EVENT_SALES_PATTERNS = (
    r"\bhow many tickets?\b.{0,50}\b(sold|sales)\b",
    r"\btickets? sold\b",
    r"\bhow many (?:people|tickets?) (?:bought|purchased)\b",
    r"\bsales for (?:my |this |the )?event\b",
)

_FAN_CONNECT_PATTERNS = (
    r"\bfan connect\b",
    r"\bhow many connections?\b",
    r"\bconnections do i have\b",
    r"\b(?:incoming|outgoing) requests?\b",
    r"\bpending (?:fan )?connect\b",
)

_AMBASSADOR_PATTERNS = (
    r"\bmy referral\b",
    r"\breferral (?:link|code|earnings|commission|stats)\b",
    r"\bambassador earnings\b",
    r"\bmy ambassador campaigns?\b",
    r"\bhow much (?:have i|did i) earn\b",
    r"\bcommission (?:owed|earned|paid)\b",
)

_SPONSOR_PATTERNS = (
    r"\bmy sponsorship\b",
    r"\bsponsor(?:ship)? (?:deal|deals|application|applications|inquir)\b",
    r"\bhow many (?:deals|inquiries|applications)\b",
    r"\bsponsor (?:overview|dashboard|workspace|campaigns?)\b",
    r"\bsaved opportunities\b",
)

_HOST_CRM_PATTERNS = (
    r"\baudience segments?\b",
    r"\bmy segments?\b",
    r"\bannouncements?\b",
    r"\bambassador program\b",
    r"\bmy ambassadors\b",
    r"\bambassador analytics\b",
)

_PAST_TICKET_PATTERNS = (
    r"\bpast tickets?\b",
    r"\bprevious tickets?\b",
    r"\btickets? i (?:attended|went to)\b",
    r"\bevents? i (?:attended|went to)\b",
)

_PUBLIC_SPONSOR_PATTERNS = (
    r"\bfind sponsors?\b",
    r"\bsearch sponsors?\b",
    r"\bbrand partners?\b",
)

_TICKET_COUNT_PATTERNS = (
    r"\bhow many tickets?\b",
    r"\bnumber of tickets?\b",
    r"\bticket count\b",
    r"\btickets? (?:have|has|did|i'?ve|i have) (?:i )?(?:purchased|bought)\b",
    r"\bhow many (?:events?|shows?) (?:have|has|did) i (?:purchased|bought|attended)\b",
)

_TICKET_WALLET_PATTERNS = (
    r"\bmy tickets?\b",
    r"\bupcoming tickets?\b",
    r"\bticket wallet\b",
    r"\bwhere is my ticket\b",
    r"\bshow (?:me )?my tickets?\b",
)


def _matches_fee_pricing_query(lower: str) -> bool:
    return _match_any(lower, _FEE_PRICING_PATTERNS)


def _matches_become_host_query(lower: str) -> bool:
    return _match_any(lower, _BECOME_HOST_PATTERNS)


def _matches_following_query(lower: str) -> bool:
    return _match_any(lower, _FOLLOWING_PATTERNS)


def _matches_followed_host_events_query(lower: str) -> bool:
    return _match_any(lower, _FOLLOWED_HOST_EVENTS_PATTERNS)


def _matches_follower_query(lower: str) -> bool:
    return _match_any(lower, _FOLLOWER_PATTERNS)


def _matches_audience_query(lower: str) -> bool:
    return _match_any(lower, _AUDIENCE_PATTERNS)


def _matches_event_sales_query(lower: str) -> bool:
    return _match_any(lower, _EVENT_SALES_PATTERNS)


def _matches_fan_connect_query(lower: str) -> bool:
    return _match_any(lower, _FAN_CONNECT_PATTERNS)


def _matches_ambassador_query(lower: str) -> bool:
    return _match_any(lower, _AMBASSADOR_PATTERNS)


def _matches_sponsor_query(lower: str) -> bool:
    return _match_any(lower, _SPONSOR_PATTERNS)


def _matches_host_crm_query(lower: str) -> bool:
    return _match_any(lower, _HOST_CRM_PATTERNS)


def _matches_past_ticket_query(lower: str) -> bool:
    return _match_any(lower, _PAST_TICKET_PATTERNS)


def _matches_public_sponsor_query(lower: str) -> bool:
    return _match_any(lower, _PUBLIC_SPONSOR_PATTERNS)


def _matches_ticket_count_query(lower: str) -> bool:
    return _match_any(lower, _TICKET_COUNT_PATTERNS)


def _matches_ticket_wallet_query(lower: str) -> bool:
    return _match_any(lower, _TICKET_WALLET_PATTERNS)


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

    if _matches_followed_host_events_query(lower):
        if not authenticated:
            return IntentResult(
                intent=INTENT_SEARCH_EVENTS,
                confidence=0.9,
                tool_hints=[],
                reason="auth_required_for_intent",
            )
        return IntentResult(
            intent=INTENT_SEARCH_EVENTS,
            confidence=0.9,
            tool_hints=[
                "list_upcoming_events_from_followed_hosts",
                "get_my_following_summary",
            ],
            route_key="fan_saved",
            path="/dashboard/saved",
        )

    if _matches_fee_pricing_query(lower):
        return IntentResult(
            intent=INTENT_PRICING,
            confidence=0.88,
            route_key="pricing",
            path="/pricing",
            tool_hints=["get_public_pricing", "search_help", "search_public_pages"],
        )

    if _matches_become_host_query(lower):
        return IntentResult(
            intent=INTENT_SEARCH_PAGES,
            confidence=0.88,
            route_key="for_hosts",
            path="/for-hosts",
            tool_hints=["search_help", "search_public_pages", "navigate_to_route"],
        )

    if _matches_public_sponsor_query(lower) and not authenticated:
        return IntentResult(
            intent=INTENT_SEARCH_PAGES,
            confidence=0.8,
            route_key="sponsors",
            path="/sponsors",
            tool_hints=["search_public_sponsors", "search_public_pages"],
        )

    if _matches_ambassador_query(lower):
        if not authenticated:
            return IntentResult(
                intent=INTENT_INSIGHTS,
                confidence=0.9,
                tool_hints=[],
                reason="auth_required_for_intent",
            )
        return IntentResult(
            intent=INTENT_INSIGHTS,
            confidence=0.9,
            tool_hints=[
                "get_my_referral_summary",
                "get_my_ambassador_earnings",
                "list_my_ambassador_campaigns",
                "list_my_referral_links",
            ],
            route_key="ambassador_dashboard",
            path="/ambassador",
        )

    if _matches_sponsor_query(lower):
        if not authenticated:
            return IntentResult(
                intent=INTENT_INSIGHTS,
                confidence=0.9,
                tool_hints=[],
                reason="auth_required_for_intent",
            )
        return IntentResult(
            intent=INTENT_INSIGHTS,
            confidence=0.9,
            tool_hints=[
                "get_my_sponsor_overview",
                "list_my_sponsor_deals",
                "list_my_sponsor_campaigns",
                "list_my_sponsor_applications",
            ],
            route_key="sponsor_dashboard",
            path="/sponsor",
        )

    if _matches_host_crm_query(lower):
        if not authenticated:
            return IntentResult(
                intent=INTENT_INSIGHTS,
                confidence=0.88,
                tool_hints=[],
                reason="auth_required_for_intent",
            )
        tools = ["list_my_audience_segments", "get_my_announcements_summary"]
        if "ambassador" in lower:
            tools.insert(0, "get_my_host_ambassador_analytics")
        return IntentResult(
            intent=INTENT_INSIGHTS,
            confidence=0.88,
            tool_hints=tools,
            route_key="host_audience",
            path="/host/audience",
        )

    if _matches_past_ticket_query(lower):
        if not authenticated:
            return IntentResult(
                intent=INTENT_TICKETS,
                confidence=0.85,
                tool_hints=[],
                reason="auth_required_for_intent",
            )
        return IntentResult(
            intent=INTENT_TICKETS,
            confidence=0.85,
            tool_hints=["list_my_past_tickets", "get_my_ticket_summary"],
            route_key="fan_tickets",
            path="/dashboard/tickets",
        )

    if _matches_following_query(lower):
        if not authenticated:
            return IntentResult(
                intent=INTENT_INSIGHTS,
                confidence=0.9,
                tool_hints=[],
                reason="auth_required_for_intent",
            )
        return IntentResult(
            intent=INTENT_INSIGHTS,
            confidence=0.9,
            tool_hints=["get_my_following_summary"],
        )

    if _matches_fan_connect_query(lower):
        if not authenticated:
            return IntentResult(
                intent=INTENT_INSIGHTS,
                confidence=0.85,
                tool_hints=[],
                reason="auth_required_for_intent",
            )
        return IntentResult(
            intent=INTENT_INSIGHTS,
            confidence=0.85,
            tool_hints=["get_my_fan_connect_inbox_summary", "get_my_fan_connect_summary"],
        )

    if _matches_event_sales_query(lower):
        if not authenticated:
            return IntentResult(
                intent=INTENT_INSIGHTS,
                confidence=0.9,
                tool_hints=[],
                reason="auth_required_for_intent",
            )
        return IntentResult(
            intent=INTENT_INSIGHTS,
            confidence=0.9,
            tool_hints=["get_my_event_analytics", "list_my_events"],
            route_key="host_events",
            path="/host/events",
        )

    if _matches_follower_query(lower) or _matches_audience_query(lower):
        if not authenticated:
            return IntentResult(
                intent=INTENT_INSIGHTS,
                confidence=0.9,
                tool_hints=[],
                reason="auth_required_for_intent",
            )
        return IntentResult(
            intent=INTENT_INSIGHTS,
            confidence=0.9,
            tool_hints=["get_my_audience_summary"],
            route_key="host_audience",
            path="/host/audience",
        )

    if _matches_ticket_count_query(lower) or _matches_ticket_wallet_query(lower):
        tools = (
            ["get_my_ticket_summary", "list_my_upcoming_tickets"]
            if _matches_ticket_count_query(lower)
            else ["list_my_upcoming_tickets", "get_my_ticket_summary"]
        )
        if not authenticated:
            return IntentResult(
                intent=INTENT_TICKETS,
                confidence=0.9,
                tool_hints=[],
                reason="auth_required_for_intent",
            )
        return IntentResult(
            intent=INTENT_TICKETS,
            confidence=0.9,
            tool_hints=tools,
            route_key="fan_tickets",
            path="/dashboard/tickets",
        )

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
        (INTENT_TICKETS, ("my ticket", "upcoming ticket", "ticket wallet", "where is my ticket"), ["list_my_upcoming_tickets", "get_my_ticket_summary"], 0.9),
        (INTENT_ORDERS, ("my order", "order history", "my purchase", "purchased", "my purchases"), ["get_my_order_summary", "get_my_ticket_summary"], 0.85),
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
        (INTENT_SEARCH_EVENTS, ("what's on", "tonight", "concert", "party", "find events", "events in", "upcoming events"), ["search_public_events"], 0.8),
        (INTENT_SEARCH_HOSTS, ("find hosts", "host directory", "discover hosts", "promoter", "legacy page"), ["search_public_hosts"], 0.75),
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
