"""Deterministic token estimation and budgeting for assistant prompts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.assistant.constants import (
    ABSOLUTE_MAX_OUTPUT_TOKENS,
    DEFAULT_KNOWLEDGE_MAX,
    DEFAULT_KNOWLEDGE_TOP_K,
    DEFAULT_MAX_OUTPUT_TOKENS,
    DEFAULT_RECENT_HISTORY_TOKEN_BUDGET,
    DEFAULT_RECENT_TURN_LIMIT,
    DEFAULT_SESSION_SUMMARY_TOKEN_BUDGET,
)
from app.core.config import get_settings


def estimate_tokens(text: str) -> int:
    """Conservative token estimate when provider tokenizer is unavailable."""
    if not text:
        return 0
    # ~4 chars per token for English prose; round up.
    return max(1, (len(text) + 3) // 4)


def truncate_to_token_budget(text: str, budget: int) -> str:
    if budget <= 0 or not text:
        return ""
    est = estimate_tokens(text)
    if est <= budget:
        return text
    max_chars = budget * 4
    trimmed = text[:max_chars].rstrip()
    return trimmed + "…"


@dataclass(frozen=True)
class ContextBudgets:
    recent_turn_limit: int
    recent_history_tokens: int
    session_summary_tokens: int
    knowledge_top_k: int
    knowledge_max: int
    output_tokens: int


def load_context_budgets() -> ContextBudgets:
    settings = get_settings()
    output = resolve_output_token_limit()
    return ContextBudgets(
        recent_turn_limit=int(
            getattr(settings, "assistant_recent_turn_limit", None)
            or DEFAULT_RECENT_TURN_LIMIT
        ),
        recent_history_tokens=int(
            getattr(settings, "assistant_recent_history_token_budget", None)
            or DEFAULT_RECENT_HISTORY_TOKEN_BUDGET
        ),
        session_summary_tokens=int(
            getattr(settings, "assistant_session_summary_token_budget", None)
            or DEFAULT_SESSION_SUMMARY_TOKEN_BUDGET
        ),
        knowledge_top_k=int(
            getattr(settings, "assistant_knowledge_top_k", None)
            or DEFAULT_KNOWLEDGE_TOP_K
        ),
        knowledge_max=int(
            getattr(settings, "assistant_knowledge_max", None)
            or DEFAULT_KNOWLEDGE_MAX
        ),
        output_tokens=output,
    )


def resolve_output_token_limit(*, task_limit: int | None = None) -> int:
    """Server-side output cap; browser/model cannot raise it."""
    settings = get_settings()
    configured = int(
        getattr(settings, "assistant_max_output_tokens", None)
        or DEFAULT_MAX_OUTPUT_TOKENS
    )
    absolute = int(
        getattr(settings, "assistant_absolute_max_output_tokens", None)
        or ABSOLUTE_MAX_OUTPUT_TOKENS
    )
    cap = min(configured, absolute)
    if task_limit is not None:
        cap = min(cap, max(1, int(task_limit)))
    return max(1, cap)


def apply_history_token_budget(
    turns: list[dict[str, str]],
    *,
    token_budget: int,
    turn_limit: int,
) -> list[dict[str, str]]:
    """Trim oldest turns / verbosity to fit budget."""
    if not turns:
        return []
    limited = turns[-turn_limit * 2 :] if turn_limit else turns
    # Pair user+assistant; keep most recent first when trimming.
    while limited and estimate_tokens(_format_turns(limited)) > token_budget:
        if len(limited) >= 2:
            limited = limited[2:]
        else:
            content = limited[0].get("content") or ""
            limited[0] = {
                **limited[0],
                "content": truncate_to_token_budget(
                    content, max(32, token_budget // max(1, len(limited)))
                ),
            }
            break
    return limited


def _format_turns(turns: list[dict[str, str]]) -> str:
    return "\n".join(f"{t.get('role', '?')}: {t.get('content', '')}" for t in turns)


def trim_knowledge_citations(
    citations: list[Any],
    *,
    top_k: int,
    absolute_max: int,
) -> list[Any]:
    k = min(top_k, absolute_max, len(citations))
    return citations[:k]
