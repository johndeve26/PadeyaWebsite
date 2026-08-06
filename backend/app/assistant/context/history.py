"""Server-side conversation history reconstruction."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.assistant.constants import (
    HISTORY_EXCLUDED_MESSAGE_ROLES,
    HISTORY_EXCLUDED_SAFETY_STATUSES,
)
from app.assistant.models import AssistantMessage, AssistantSession
from app.assistant.privacy import scrub_prompt_text
from app.assistant.context.tokens import apply_history_token_budget, load_context_budgets


def _scrub_history_content(content: str) -> str:
    return scrub_prompt_text((content or "").strip()[:2000])


def _message_include_in_history(msg: AssistantMessage) -> bool:
    if msg.role in HISTORY_EXCLUDED_MESSAGE_ROLES:
        return False
    if msg.safety_status in HISTORY_EXCLUDED_SAFETY_STATUSES:
        return False
    if msg.role not in {"user", "assistant"}:
        return False
    if msg.role == "assistant" and not (msg.content or "").strip():
        return False
    return True


def load_session_messages(
    db: Session,
    *,
    session_id: UUID,
    exclude_message_id: UUID | None = None,
) -> list[AssistantMessage]:
    stmt = (
        select(AssistantMessage)
        .where(AssistantMessage.session_id == session_id)
        .order_by(AssistantMessage.created_at.asc())
    )
    rows = list(db.scalars(stmt).all())
    if exclude_message_id:
        rows = [r for r in rows if r.id != exclude_message_id]
    return [r for r in rows if _message_include_in_history(r)]


def load_scrubbed_history(
    db: Session,
    *,
    session: AssistantSession,
    exclude_message_id: UUID | None = None,
) -> list[dict[str, str]]:
    """Return bounded, scrubbed turns for prompt construction."""
    budgets = load_context_budgets()
    messages = load_session_messages(
        db, session_id=session.id, exclude_message_id=exclude_message_id
    )
    turns: list[dict[str, str]] = []
    for msg in messages:
        turns.append(
            {
                "role": msg.role,
                "content": _scrub_history_content(msg.content),
            }
        )
    return apply_history_token_budget(
        turns,
        token_budget=budgets.recent_history_tokens,
        turn_limit=budgets.recent_turn_limit,
    )


def format_recent_conversation(turns: list[dict[str, str]]) -> str:
    if not turns:
        return ""
    lines: list[str] = []
    for turn in turns:
        role = turn.get("role") or "user"
        label = "User" if role == "user" else "Assistant"
        content = turn.get("content") or ""
        if content:
            lines.append(f"{label}: {content}")
    return "\n".join(lines)


def extract_topic_keywords(messages: list[AssistantMessage]) -> list[str]:
    """Deterministic keywords for summary updates."""
    words: list[str] = []
    for msg in messages[-6:]:
        if msg.role != "user":
            continue
        for token in (msg.content or "").lower().split():
            t = token.strip(".,?!\"'")
            if len(t) >= 4 and t not in words:
                words.append(t[:40])
            if len(words) >= 12:
                return words
    return words
