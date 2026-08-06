"""Assistant privacy redaction / page-context sanitization."""

from __future__ import annotations

from app.assistant.privacy import (
    SAFE_PAGE_CONTEXT_KEYS,
    redact_dict,
    sanitize_page_context,
    sanitize_tool_args_for_log,
    sanitize_user_message,
)


def test_redact_dict_strips_tokens_passwords():
    raw = {
        "title": "Lagos Night",
        "password": "secret123",
        "access_token": "tok_abc",
        "api_key": "sk-live-1234567890",
        "nested": {
            "refresh_token": "rrr",
            "city": "Lagos",
            "authorization": "Bearer xyz",
        },
        "safe_note": "Bring friends",
    }
    cleaned = redact_dict(raw)
    assert "password" not in cleaned
    assert "access_token" not in cleaned
    assert "api_key" not in cleaned
    assert cleaned.get("title") == "Lagos Night"
    assert cleaned.get("safe_note") == "Bring friends"
    nested = cleaned.get("nested") or {}
    assert "refresh_token" not in nested
    assert "authorization" not in nested
    assert nested.get("city") == "Lagos"


def test_sanitize_page_context_drops_forbidden_keys():
    raw = {
        "route_key": "events",
        "page_title": "Events",
        "role": "fan",
        "password": "nope",
        "cookie": "sid=1",
        "user_email": "a@b.com",
        "authorization_header": "Bearer x",
        "raw_html": "<script>x</script>",
        "active_tab": "upcoming",
        "ui_errors": ["TICKET_SOLD_OUT"],
        "feature_flags": {"x": True},
        "available_actions": ["buy"],
        "bank": "001",
    }
    clean = sanitize_page_context(raw)
    assert set(clean.keys()) <= SAFE_PAGE_CONTEXT_KEYS
    assert clean["route_key"] == "events"
    assert clean["page_title"] == "Events"
    assert "password" not in clean
    assert "cookie" not in clean
    assert "user_email" not in clean
    assert "raw_html" not in clean
    assert "bank" not in clean
    assert clean["ui_errors"] == ["TICKET_SOLD_OUT"]


def test_pii_redaction_in_messages_and_args():
    msg = sanitize_user_message("My password: hunter2 and api_key: sk-abcdefghijklmnop")
    assert "[redacted]" in msg
    assert "sk-abcdefghijklmnop" not in msg

    args = sanitize_tool_args_for_log(
        {
            "query": "Lagos",
            "user_id": "should-drop",
            "buyer_user_id": "drop-me",
            "token": "abc",
            "email": "fan@example.com",
        }
    )
    assert "user_id" not in args
    assert "buyer_user_id" not in args
    assert "token" not in args
    assert "email" not in args
    assert args.get("query") == "Lagos"
