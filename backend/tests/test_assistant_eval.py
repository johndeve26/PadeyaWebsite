"""Runner for versioned assistant evaluation cases."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.assistant.constants import SOFT_HIGH_RISK_TOOLS
from app.assistant.intent import classify_intent
from app.assistant.tools.executor import execute_tool
from app.assistant.tools.registry import list_tools_for_context

_EVAL_PATH = Path(__file__).parent / "eval" / "assistant_eval_cases.json"


def _load_cases() -> list[dict]:
    data = json.loads(_EVAL_PATH.read_text(encoding="utf-8"))
    assert data.get("version"), "eval dataset must be versioned"
    return list(data["cases"])


def _as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


@pytest.mark.parametrize("case", _load_cases(), ids=lambda c: c["id"])
def test_assistant_eval_case(case: dict, db_session):
    message = case["message"]
    authenticated = bool(case.get("authenticated", False))
    roles = list(case.get("roles") or [])
    permissions = list(case.get("permissions") or [])

    result = classify_intent(
        message,
        authenticated=authenticated,
        roles=roles,
        permissions=permissions,
    )

    expected_intents = _as_list(case["expected_intent"])
    assert result.intent in expected_intents, (
        f"{case['id']}: intent {result.intent!r} not in {expected_intents}"
    )

    if "expected_reason" in case:
        assert result.reason == case["expected_reason"]

    if case.get("refuse") is True:
        assert result.refuse is True

    if case.get("expected_route_key"):
        assert result.route_key == case["expected_route_key"]

    if "required_tool_hints" in case and case["required_tool_hints"] is not None:
        for hint in case["required_tool_hints"]:
            assert hint in result.tool_hints

    flags = {
        "assistant_actions_enabled": True,
        "assistant_event_search_enabled": True,
        "assistant_support_drafts_enabled": True,
        "assistant_admin_enabled": True,
    }
    allowed = {
        t.name
        for t in list_tools_for_context(
            authenticated=authenticated,
            roles=roles or (["buyer"] if authenticated else []),
            permissions=permissions,
            flags=flags,
        )
    }

    prohibited = list(case.get("prohibited_tools") or [])
    for tool_name in prohibited:
        if tool_name in SOFT_HIGH_RISK_TOOLS:
            assert tool_name not in allowed
        if tool_name not in allowed or result.refuse:
            exec_result = execute_tool(
                db_session,
                tool_name=tool_name,
                args={},
                user=None,
            )
            assert exec_result.get("ok") is not True
            assert exec_result.get("error") in {
                "forbidden_tool",
                "auth_required",
                "forbidden_role",
                "forbidden_permission",
                "unknown_tool",
                "handler_missing",
                "confirmation_required",
                "forbidden",
            }
