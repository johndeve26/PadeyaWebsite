"""Public Ask Pàdéyá HTTP API tests."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.assistant.rate_limit import _buckets
from app.assistant.tools.executor import execute_tool
from app.assistant.tools.navigation import navigate_to_route
from tests.assistant_helpers import (
    enable_assistant,
    parse_sse_events,
    seed_host,
    seed_published_event,
)


@pytest.fixture()
def assistant_public(monkeypatch):
    settings = enable_assistant(
        monkeypatch,
        assistant_enabled=True,
        assistant_public_enabled=True,
        assistant_authenticated_enabled=True,
        assistant_event_search_enabled=True,
        assistant_actions_enabled=False,
        ai_enabled=True,
        ai_provider="template",
    )
    # Lower anonymous limit for rate-limit test convenience
    monkeypatch.setattr(settings, "assistant_anonymous_rate_limit_per_hour", 30)
    return settings


def test_status_endpoint_returns_flags(client: TestClient, assistant_public):
    resp = client.get("/api/v1/assistant/status")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["assistant_enabled"] is True
    assert body["public_enabled"] is True
    assert body["event_search_enabled"] is True
    assert "Ask" in body["product_public"] or "Pàdéyá" in body["product_public"]


def test_disabled_assistant_returns_404(client: TestClient, monkeypatch):
    enable_assistant(
        monkeypatch,
        assistant_enabled=False,
        assistant_public_enabled=False,
    )
    status = client.get("/api/v1/assistant/status")
    assert status.status_code == 200
    assert status.json()["assistant_enabled"] is False

    chat = client.post(
        "/api/v1/assistant/chat/stream",
        json={"message": "Hello"},
    )
    assert chat.status_code == 404


def test_chat_stream_works_when_enabled(
    client: TestClient, db_session: Session, assistant_public
):
    resp = client.post(
        "/api/v1/assistant/chat/stream",
        json={"message": "Hello there"},
    )
    assert resp.status_code == 200, resp.text
    assert "text/event-stream" in resp.headers.get("content-type", "")
    events = parse_sse_events(resp.text)
    names = [e[0] for e in events]
    assert "session" in names or "status" in names
    assert "done" in names or "token" in names


def test_event_search_via_lagos_intent(
    client: TestClient, db_session: Session, assistant_public
):
    host, _ = seed_host(db_session, email="asst-lagos@example.com", slug="asst-lagos")
    event = seed_published_event(
        db_session, host, title="Lagos Rooftop", slug="lagos-rooftop-asst", city="Lagos"
    )

    # Direct tool path (query should match city/title fragment)
    tool = execute_tool(
        db_session,
        tool_name="search_public_events",
        args={"query": "Lagos"},
        user=None,
    )
    assert tool["ok"] is True
    titles = [r.get("title") for r in tool.get("results") or []]
    assert any("Lagos" in (t or "") for t in titles), tool
    assert tool["count"] >= 1

    resp = client.post(
        "/api/v1/assistant/chat/stream",
        json={"message": "Events in Lagos"},
    )
    assert resp.status_code == 200, resp.text
    raw = resp.text
    # Tool path or cards should surface in SSE
    assert (
        "search_public_events" in raw
        or "Lagos" in raw
        or "tool_started" in raw
        or "tool_completed" in raw
        or event.title in raw
    )


def test_anonymous_rate_limit_friendly_message(
    client: TestClient, monkeypatch, assistant_public
):
    monkeypatch.setattr(assistant_public, "assistant_anonymous_rate_limit_per_hour", 2)
    _buckets.clear()

    headers = {"X-Forwarded-For": "203.0.113.77"}
    r1 = client.post(
        "/api/v1/assistant/chat/stream",
        json={"message": "Hi one"},
        headers=headers,
    )
    r2 = client.post(
        "/api/v1/assistant/chat/stream",
        json={"message": "Hi two"},
        headers=headers,
    )
    r3 = client.post(
        "/api/v1/assistant/chat/stream",
        json={"message": "Hi three"},
        headers=headers,
    )
    assert r1.status_code == 200
    assert r2.status_code == 200
    # Rate limit is enforced inside the SSE generator → HTTP 429 or SSE error
    if r3.status_code == 429:
        detail = r3.json().get("detail", "")
    else:
        assert r3.status_code == 200
        detail = r3.text
        assert '"status_code": 429' in detail or "429" in detail
    assert "rate limit" in detail.lower()
    assert "try again" in detail.lower()


def test_public_answers_can_include_citations(
    client: TestClient, db_session: Session, assistant_public
):
    # Registry-backed retrieval for help-ish queries
    from app.assistant.knowledge.retrieve import retrieve_knowledge

    hits = retrieve_knowledge(db_session, query="How do I become an ambassador?")
    assert hits
    assert any(
        h.get("source_type") == "registry" or "ambassador" in (h.get("url") or "").lower()
        for h in hits
    )

    resp = client.post(
        "/api/v1/assistant/chat/stream",
        json={"message": "Where is the help center?"},
    )
    assert resp.status_code == 200
    # May include citation events or navigation to /help
    assert "help" in resp.text.lower() or "citation" in resp.text.lower()


def test_invent_route_refusal_registry_only(db_session: Session, assistant_public):
    # Unknown invented path must not be accepted as navigation
    result = navigate_to_route(
        db_session,
        args={"query": "open /super-secret-admin-portal-xyz"},
        authenticated=False,
    )
    assert result["ok"] is False
    assert result.get("error") in {"no_match", "unknown_route_key"}

    # Registry route works
    ok = navigate_to_route(
        db_session,
        args={"route_key": "ambassadors"},
        authenticated=False,
    )
    assert ok["ok"] is True
    assert ok["path"] == "/ambassadors"

    # Invented route_key refused
    bad = navigate_to_route(
        db_session,
        args={"route_key": "totally_fake_route"},
        authenticated=False,
    )
    assert bad["ok"] is False
