"""Deterministic follow-up reference resolution before the main model."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.assistant.intent import IntentResult


@dataclass
class FollowUpResolution:
    matched: bool = False
    clarification: str | None = None
    tool_hints: list[str] = field(default_factory=list)
    tool_args: dict[str, Any] = field(default_factory=dict)
    extra_tool_names: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    navigate_url: str | None = None
    navigate_label: str | None = None
    skip_provider: bool = False
    augmented_message: str | None = None


_ORDINAL_WORDS = {
    "first": 1,
    "1st": 1,
    "one": 1,
    "second": 2,
    "2nd": 2,
    "two": 2,
    "third": 3,
    "3rd": 3,
    "three": 3,
    "fourth": 4,
    "4th": 4,
    "last": -1,
}

_ORDINAL_PATTERNS = (
    r"\b(?:the )?(first|1st|second|2nd|third|3rd|fourth|4th|last)\b",
    r"\b(?:tell me about|show|open|go to)\b.{0,20}\b(?:the )?(first|second|third|one)\b",
)

_REFERENCE_PATTERNS = (
    r"\bthat (?:event|host|ticket|one)\b",
    r"\bthis (?:event|host|ticket|one)\b",
    r"\bthe other one\b",
    r"\bthat host\b",
    r"\bthat event\b",
    r"\bthis ticket\b",
)

_FILTER_PATTERNS = (
    (r"\bonly free\b", {"paid": "free"}),
    (r"\bfree ones?\b", {"paid": "free"}),
    (r"\bfree events?\b", {"paid": "free"}),
    (r"\bmake it free\b", {"paid": "free"}),
    (r"\bchange it to lagos\b", {"city": "Lagos", "query": "Lagos"}),
    (r"\bin lagos\b", {"city": "Lagos", "query": "Lagos"}),
    (r"\bnext weekend\b", {"date_range": "weekend"}),
    (r"\bthis weekend\b", {"date_range": "weekend"}),
    (r"\bsame city\b", {"reuse_city": True}),
)


def _parse_ordinal(lower: str) -> int | None:
    for pattern in _ORDINAL_PATTERNS:
        m = re.search(pattern, lower)
        if m:
            word = m.group(1).lower()
            return _ORDINAL_WORDS.get(word)
    m = re.search(r"\bnumber (\d+)\b", lower)
    if m:
        return int(m.group(1))
    return None


def _is_reference_query(lower: str) -> bool:
    if _parse_ordinal(lower) is not None:
        return True
    return any(re.search(p, lower) for p in _REFERENCE_PATTERNS)


def _pick_result(state: dict[str, Any], ordinal: int | None) -> dict[str, Any] | None:
    results = state.get("last_results") or []
    if not results:
        return state.get("selected_entity") if isinstance(state.get("selected_entity"), dict) else None
    if ordinal is None:
        return results[0] if len(results) == 1 else None
    if ordinal == -1:
        return results[-1]
    if 1 <= ordinal <= len(results):
        return results[ordinal - 1]
    return None


def _entity_tool_plan(item: dict[str, Any]) -> tuple[list[str], dict[str, Any], str | None, str | None]:
    entity_type = item.get("entity_type")
    slug = item.get("slug")
    url = item.get("url")
    label = item.get("label") or "Open"
    hints: list[str] = []
    args: dict[str, Any] = {}
    if entity_type == "event" and slug:
        hints = ["get_public_event"]
        args = {"slug": slug, "event_slug": slug}
        url = url or f"/events/{slug}"
    elif entity_type == "host" and slug:
        hints = ["search_public_hosts"]
        args = {"query": slug, "q": slug}
        url = url or f"/hosts/{slug}"
    elif entity_type == "ticket" and url:
        hints = ["list_my_upcoming_tickets"]
        url = url if url.startswith("/") else "/dashboard/tickets"
    elif entity_type == "host_event_private" and slug:
        hints = ["get_my_event_summary"]
        args = {"slug": slug, "event_slug": slug}
        url = url or "/host/events"
    return hints, args, url, label


def resolve_follow_up(
    message: str,
    *,
    state: dict[str, Any],
    intent: IntentResult,
) -> FollowUpResolution:
    lower = (message or "").strip().lower()
    if not lower:
        return FollowUpResolution()

    # Filter-only follow-ups (reuse search)
    for pattern, patch in _FILTER_PATTERNS:
        if re.search(pattern, lower):
            filters = dict(state.get("active_search_filters") or {})
            filters.update({k: v for k, v in patch.items() if k != "reuse_city"})
            if patch.get("reuse_city") and filters.get("city"):
                patch = {"city": filters["city"], "query": filters.get("query") or filters["city"]}
            query = filters.get("query") or message
            return FollowUpResolution(
                matched=True,
                tool_hints=["search_public_events"],
                tool_args={"query": query, "q": query, **{k: v for k, v in filters.items() if k != "query"}},
                augmented_message=message,
            )

    if not _is_reference_query(lower):
        return FollowUpResolution()

    results = state.get("last_results") or []
    ordinal = _parse_ordinal(lower)

    if "other one" in lower or "the other" in lower:
        if len(results) < 2:
            return FollowUpResolution(
                matched=True,
                clarification="Which one do you mean? I only have one result from the last search.",
                skip_provider=True,
            )
        if ordinal is None and len(results) >= 2:
            return FollowUpResolution(
                matched=True,
                clarification=(
                    "Do you mean the first or the second result? "
                    f"1) {results[0].get('label')} 2) {results[1].get('label')}"
                ),
                skip_provider=True,
            )

    item = _pick_result(state, ordinal)
    if item is None:
        if results:
            return FollowUpResolution(
                matched=True,
                clarification="Which result do you mean — first, second, or last?",
                skip_provider=True,
            )
        return FollowUpResolution()

    hints, args, url, label = _entity_tool_plan(item)
    if "open" in lower or "go to" in lower or "take me" in lower:
        return FollowUpResolution(
            matched=True,
            tool_hints=hints,
            tool_args=args,
            navigate_url=url,
            navigate_label=f"Open {label}",
            augmented_message=f"{message}\n[Resolved reference: {label}]",
        )

    return FollowUpResolution(
        matched=True,
        tool_hints=hints or list(intent.tool_hints),
        tool_args=args,
        augmented_message=f"{message}\n[Resolved reference: {label}]",
    )
