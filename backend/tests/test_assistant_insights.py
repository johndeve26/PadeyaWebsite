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


def test_ambassador_summary_requires_auth(db_session, monkeypatch):
    enable_assistant(monkeypatch)
    result = execute_tool(
        db_session,
        tool_name="get_my_referral_summary",
        args={},
        user=None,
    )
    assert result["ok"] is False
    assert result["error"] == "auth_required"


def test_ambassador_summary_for_authenticated_user(db_session, monkeypatch):
    enable_assistant(monkeypatch)
    user = seed_user(db_session, email="ins-amb@example.com", role="buyer")
    result = execute_tool(
        db_session,
        tool_name="get_my_referral_summary",
        args={},
        user=user,
    )
    assert result["ok"] is True
    assert "summary" in result


def test_sponsor_tools_forbidden_for_fan(db_session, monkeypatch):
    enable_assistant(monkeypatch)
    fan = seed_user(db_session, email="ins-fan4@example.com", role="buyer")
    result = execute_tool(
        db_session,
        tool_name="get_my_sponsor_overview",
        args={},
        user=fan,
    )
    assert result["ok"] is False
    assert result["error"] in {"forbidden", "forbidden_role"}


def test_sponsor_overview_without_workspace(db_session, monkeypatch):
    enable_assistant(monkeypatch)
    sponsor = seed_user(db_session, email="ins-sp@example.com", role="sponsor")
    result = execute_tool(
        db_session,
        tool_name="get_my_sponsor_overview",
        args={},
        user=sponsor,
    )
    assert result["ok"] is False
    assert result["error"] == "not_found"


def test_host_segments_for_host(db_session, monkeypatch):
    enable_assistant(monkeypatch)
    _, user = seed_host(db_session, email="ins-host2@example.com", slug="ins-host2")
    result = execute_tool(
        db_session,
        tool_name="list_my_audience_segments",
        args={},
        user=user,
    )
    assert result["ok"] is True
    assert "count" in result


def test_past_tickets_for_fan(db_session, monkeypatch):
    enable_assistant(monkeypatch)
    fan = seed_user(db_session, email="ins-fan5@example.com", role="buyer")
    result = execute_tool(
        db_session,
        tool_name="list_my_past_tickets",
        args={},
        user=fan,
    )
    assert result["ok"] is True
    assert result["count"] == 0


def test_followed_host_events_empty_when_not_following(db_session, monkeypatch):
    enable_assistant(monkeypatch)
    fan = seed_user(db_session, email="ins-fan6@example.com", role="buyer")
    result = execute_tool(
        db_session,
        tool_name="list_upcoming_events_from_followed_hosts",
        args={},
        user=fan,
    )
    assert result["ok"] is True
    assert result["count"] == 0
    assert "not following" in result["summary"].lower()
