"""Sanitize assistant inputs/outputs — reuse AI context scrubber patterns."""

from __future__ import annotations

from typing import Any

from app.ai.context_scrubber import (
    FORBIDDEN_CONTEXT_KEYS,
    scrub_prompt_text,
    scrub_value,
)

# Extra keys forbidden specifically in page context / tool args
_ASSISTANT_EXTRA_FORBIDDEN = frozenset(
    {
        "cookie",
        "cookies",
        "session",
        "session_id",
        "csrf",
        "csrf_token",
        "authorization_header",
        "raw_html",
        "inner_html",
        "dom",
        "local_storage",
        "user_email",
        "user_phone",
        "full_name",
        "bank",
        "iban",
        "account_number",
    }
)

SAFE_PAGE_CONTEXT_KEYS = frozenset(
    {
        "route_key",
        "page_title",
        "role",
        "entity_public_id",
        "active_tab",
        "ui_errors",
        "feature_flags",
        "available_actions",
    }
)


def _is_forbidden_key(key: str) -> bool:
    k = key.strip().lower().replace("-", "_")
    if k in FORBIDDEN_CONTEXT_KEYS or k in _ASSISTANT_EXTRA_FORBIDDEN:
        return True
    for bad in FORBIDDEN_CONTEXT_KEYS | _ASSISTANT_EXTRA_FORBIDDEN:
        if bad in k and bad not in {"qr"}:
            return True
        if bad == "qr" and (k == "qr" or k.startswith("qr_") or k.endswith("_qr")):
            return True
    return False


def is_safe_page_context_key(key: str) -> bool:
    if not isinstance(key, str) or not key.strip():
        return False
    k = key.strip().lower().replace("-", "_")
    if _is_forbidden_key(k):
        return False
    return k in SAFE_PAGE_CONTEXT_KEYS


def redact_dict(
    raw: dict[str, Any] | None,
    *,
    allowlist: frozenset[str] | None = None,
    max_depth: int = 4,
) -> dict[str, Any]:
    """Deep-redact a dict: drop forbidden keys, scrub string values."""
    if not raw or not isinstance(raw, dict):
        return {}
    return _redact_value(raw, allowlist=allowlist, depth=0, max_depth=max_depth)  # type: ignore[return-value]


def _redact_value(
    value: Any,
    *,
    allowlist: frozenset[str] | None,
    depth: int,
    max_depth: int,
) -> Any:
    if depth > max_depth:
        return "[truncated]"
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                continue
            if _is_forbidden_key(key):
                continue
            k = key.strip().lower().replace("-", "_")
            if allowlist is not None and key not in allowlist and k not in allowlist:
                continue
            out[key] = _redact_value(
                item, allowlist=None, depth=depth + 1, max_depth=max_depth
            )
        return out
    if isinstance(value, list):
        return [
            _redact_value(item, allowlist=None, depth=depth + 1, max_depth=max_depth)
            for item in value[:50]
        ]
    if isinstance(value, str):
        return scrub_value(value, max_len=1000)
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return scrub_value(str(value), max_len=200)


def sanitize_tool_args_for_log(args: dict[str, Any] | None) -> dict[str, Any]:
    """Args safe to persist / stream — never trust model-supplied user_id."""
    cleaned = redact_dict(args)
    cleaned.pop("user_id", None)
    cleaned.pop("buyer_user_id", None)
    cleaned.pop("actor_user_id", None)
    return cleaned


def sanitize_page_context(raw: dict[str, Any] | None) -> dict[str, Any]:
    """Allowlisted page context for prompts and storage."""
    if not raw or not isinstance(raw, dict):
        return {}
    out: dict[str, Any] = {}
    for key, value in raw.items():
        if not is_safe_page_context_key(str(key)):
            continue
        if key in ("ui_errors", "available_actions") and isinstance(value, list):
            out[key] = [scrub_value(str(v), max_len=80) for v in value[:20] if v]
        elif key == "feature_flags" and isinstance(value, dict):
            out[key] = {
                str(k)[:64]: bool(v)
                for k, v in list(value.items())[:40]
                if isinstance(k, str)
            }
        else:
            scrubbed = scrub_value(value, max_len=300)
            if scrubbed and scrubbed != "[redacted]":
                out[key] = scrubbed
    return out


def sanitize_user_message(text: str) -> str:
    return scrub_prompt_text((text or "").strip()[:4000])
