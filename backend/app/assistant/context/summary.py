"""Deterministic session summary for context beyond recent turns."""

from __future__ import annotations

from typing import Any

from app.assistant.context.history import extract_topic_keywords, load_session_messages
from app.assistant.context.state import (
    format_conversation_state,
    get_session_summary_text,
    save_conversation_state,
)
from app.assistant.context.tokens import estimate_tokens, load_context_budgets, truncate_to_token_budget
from app.assistant.models import AssistantSession
from sqlalchemy.orm import Session


def get_session_summary(session: AssistantSession) -> str:
    return get_session_summary_text(session)


def maybe_update_summary(
    db: Session,
    *,
    session: AssistantSession,
    recent_turn_count: int,
    state: dict[str, Any],
    topic_changed: bool = False,
) -> str:
    """Update summary deterministically when budget or topic warrants it."""
    budgets = load_context_budgets()
    existing = get_session_summary_text(session)
    messages = load_session_messages(db, session_id=session.id)
    turn_pairs = sum(1 for m in messages if m.role == "user")

    should_update = (
        not existing
        or turn_pairs > budgets.recent_turn_limit
        or recent_turn_count > budgets.recent_turn_limit
        or topic_changed
        or bool(state.get("draft_reference"))
    )
    if not should_update:
        return existing

    summary = _build_deterministic_summary(
        session=session,
        messages=messages,
        state=state,
        prior=existing,
    )
    trimmed = truncate_to_token_budget(summary, budgets.session_summary_tokens)
    save_conversation_state(session, summary=trimmed)
    return trimmed


def _build_deterministic_summary(
    *,
    session: AssistantSession,
    messages: list[Any],
    state: dict[str, Any],
    prior: str,
) -> str:
    keywords = extract_topic_keywords(messages)
    goal = keywords[0] if keywords else (session.title or "General assistance")
    constraints: list[str] = []
    filters = state.get("active_search_filters") or {}
    if filters.get("query"):
        constraints.append(f"query={filters['query']}")
    if filters.get("city"):
        constraints.append(f"city={filters['city']}")
    if filters.get("paid") == "free":
        constraints.append("free events only")

    entities: list[str] = []
    for item in (state.get("last_results") or [])[:5]:
        label = item.get("label")
        if label:
            entities.append(str(label))

    lines = [
        f"Goal: {goal}.",
    ]
    if constraints:
        lines.append("Constraints: " + ", ".join(constraints) + ".")
    if entities:
        lines.append("Referenced: " + ", ".join(entities) + ".")
    if state.get("draft_reference"):
        lines.append(f"Draft in progress: {state['draft_reference']}.")
    if state.get("pending_clarification"):
        lines.append(f"Unresolved: {state['pending_clarification']}.")
    if prior and prior not in lines[0]:
        lines.append(f"Prior: {prior[:400]}")
    state_line = format_conversation_state(state)
    if state_line:
        lines.append(f"State: {state_line}")
    return " ".join(lines)


def summary_token_count(session: AssistantSession) -> int:
    return estimate_tokens(get_session_summary_text(session))
