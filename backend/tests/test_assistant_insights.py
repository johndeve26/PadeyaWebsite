"""Assistant insight / analytics tool tests."""

from __future__ import annotations

from app.assistant.tools.executor import execute_tool
from tests.assistant_helpers import enable_assistant, seed_host, seed_user


def test_following_summary_for_fan(db_session, monkeypatch):
    enable_assistant(monkeypatch)
    fan = seed_user(db_session, email="ins-fan@example.com", role="buyer")
    result = execute_tool(
        db_session,
        tool_name="get_my_following_summary",
        args={},
        user=fan,
    )
    assert result["ok"] is True
    assert result["following_count"] == 0
    assert "0 host" in result["summary"]


def test_audience_summary_for_host(db_session, monkeypatch):
    enable_assistant(monkeypatch)
    host, user = seed_host(db_session, email="ins-host@example.com", slug="ins-host")
    result = execute_tool(
        db_session,
        tool_name="get_my_audience_summary",
        args={},
        user=user,
    )
    assert result["ok"] is True
    assert "followers" in result["stats"]
    assert "followers" in result["summary"]
    _ = host


def test_audience_summary_forbidden_for_fan(db_session, monkeypatch):
    enable_assistant(monkeypatch)
    fan = seed_user(db_session, email="ins-fan2@example.com", role="buyer")
    result = execute_tool(
        db_session,
        tool_name="get_my_audience_summary",
        args={},
        user=fan,
    )
    assert result["ok"] is False
    assert result["error"] in {"forbidden", "forbidden_role"}
