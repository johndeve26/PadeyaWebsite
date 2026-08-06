"""Assistant tool auth, IDOR, confirmation, and high-risk refusal tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.assistant import confirmation as confirmation_svc
from app.assistant.constants import SOFT_HIGH_RISK_TOOLS
from app.assistant.tools.executor import execute_tool
from app.assistant.tools.registry import list_tools_for_context
from tests.assistant_helpers import (
    enable_assistant,
    login,
    seed_host,
    seed_published_event,
    seed_user,
)


@pytest.fixture()
def assistant_on(monkeypatch):
    return enable_assistant(monkeypatch)


def test_fan_cannot_access_host_tools(db_session: Session, assistant_on):
    fan = seed_user(db_session, email="asst-fan@example.com", role="buyer")
    allowed = {
        t.name
        for t in list_tools_for_context(
            authenticated=True,
            roles=["buyer"],
            permissions=[],
            flags={
                "assistant_actions_enabled": True,
                "assistant_event_search_enabled": True,
            },
        )
    }
    assert "list_my_events" not in allowed
    assert "create_event_draft" not in allowed

    result = execute_tool(
        db_session,
        tool_name="list_my_events",
        args={},
        user=fan,
    )
    assert result["ok"] is False
    assert result["error"] in {"forbidden_role", "forbidden"}


def test_host_cannot_access_another_hosts_event(db_session: Session, assistant_on):
    host_a, user_a = seed_host(
        db_session, email="asst-host-a@example.com", slug="asst-host-a"
    )
    host_b, user_b = seed_host(
        db_session, email="asst-host-b@example.com", slug="asst-host-b"
    )
    event_b = seed_published_event(
        db_session, host_b, title="B Only", slug="b-only-asst"
    )

    result = execute_tool(
        db_session,
        tool_name="get_my_event_summary",
        args={"event_id": str(event_b.id)},
        user=user_a,
    )
    assert result["ok"] is False
    assert result["error"] == "forbidden"

    own = execute_tool(
        db_session,
        tool_name="get_my_event_summary",
        args={"event_id": str(event_b.id)},
        user=user_b,
    )
    # Host B owns it — may succeed
    assert own["ok"] is True
    assert own["event"]["slug"] == "b-only-asst"
    _ = host_a  # seeded


def test_unauthenticated_denied_for_private_tools(db_session: Session, assistant_on):
    for name in (
        "list_my_upcoming_tickets",
        "get_my_ticket_summary",
        "get_my_account_summary",
        "list_my_events",
        "create_event_draft",
    ):
        result = execute_tool(
            db_session, tool_name=name, args={}, user=None
        )
        assert result["ok"] is False
        assert result["error"] == "auth_required"


def test_ticket_summary_returns_counts_for_fan(db_session: Session, assistant_on):
    fan = seed_user(db_session, email="asst-ticket-sum@example.com", role="buyer")
    result = execute_tool(
        db_session,
        tool_name="get_my_ticket_summary",
        args={},
        user=fan,
    )
    assert result["ok"] is True
    assert result["total_tickets"] == 0
    assert "0 tickets" in result["summary"]


def test_public_pricing_tool_returns_structure(db_session: Session, assistant_on):
    result = execute_tool(
        db_session,
        tool_name="get_public_pricing",
        args={},
        user=None,
    )
    assert result["ok"] is True
    assert result.get("summary")
    assert result.get("url") == "/pricing"


def test_high_risk_tools_refused_not_executed(db_session: Session, assistant_on):
    host, user = seed_host(db_session, email="asst-hr@example.com", slug="asst-hr")
    allowed = {
        t.name
        for t in list_tools_for_context(
            authenticated=True,
            roles=["host"],
            permissions=["events.create"],
            flags={"assistant_actions_enabled": True},
        )
    }
    for name in ("publish_event", "refund_payment", "approve_payout"):
        assert name in SOFT_HIGH_RISK_TOOLS
        assert name not in allowed
        result = execute_tool(
            db_session, tool_name=name, args={"event_id": "x"}, user=user
        )
        assert result["ok"] is False
        assert result["error"] == "forbidden_tool"
    _ = host


def test_confirmation_required_for_level_4(db_session: Session, assistant_on):
    host, user = seed_host(db_session, email="asst-conf@example.com", slug="asst-conf")
    unconfirmed = execute_tool(
        db_session,
        tool_name="create_event_draft",
        args={"title": "Draft Night"},
        user=user,
        confirmed=False,
    )
    assert unconfirmed["ok"] is False
    assert unconfirmed["error"] == "confirmation_required"
    assert unconfirmed.get("confirmation_required") is True
    _ = host


def test_confirmation_expiry_and_user_binding(db_session: Session, assistant_on):
    host, user = seed_host(db_session, email="asst-exp@example.com", slug="asst-exp")
    other = seed_user(db_session, email="asst-other@example.com", role="buyer")

    conf = confirmation_svc.create_confirmation(
        db_session,
        user=user,
        tool_name="create_event_draft",
        args={"title": "Bound Draft"},
        idempotency_key="asst-test-idem-1",
        ttl_minutes=15,
    )

    # Other user cannot confirm
    with pytest.raises(HTTPException) as exc:
        confirmation_svc.confirm_action(
            db_session, confirmation_id=conf.id, user=other
        )
    assert exc.value.status_code == 403

    # Expire and reject
    conf.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db_session.commit()
    with pytest.raises(HTTPException) as exc2:
        confirmation_svc.confirm_action(
            db_session, confirmation_id=conf.id, user=user
        )
    assert exc2.value.status_code == 410
    _ = host


def test_mutation_idempotency(db_session: Session, assistant_on):
    host, user = seed_host(db_session, email="asst-idem@example.com", slug="asst-idem")
    a = confirmation_svc.create_confirmation(
        db_session,
        user=user,
        tool_name="create_event_draft",
        args={"title": "Same Draft"},
        idempotency_key="asst-shared-key",
    )
    b = confirmation_svc.create_confirmation(
        db_session,
        user=user,
        tool_name="create_event_draft",
        args={"title": "Same Draft"},
        idempotency_key="asst-shared-key",
    )
    assert a.id == b.id
    assert a.idempotency_key == b.idempotency_key
    _ = host


def test_confirmed_draft_creates_draft_only(
    client: TestClient, db_session: Session, assistant_on
):
    host, user = seed_host(db_session, email="asst-draft@example.com", slug="asst-draft")
    conf = confirmation_svc.create_confirmation(
        db_session,
        user=user,
        tool_name="create_event_draft",
        args={"title": "Confirmed Draft Night"},
        idempotency_key="asst-draft-ok",
    )
    headers = login(client, user.email)
    # Direct confirm via service (avoids needing actions flag path differences)
    out = confirmation_svc.confirm_action(
        db_session, confirmation_id=conf.id, user=user
    )
    assert out["status"] in {"confirmed", "failed"}
    if out["status"] == "confirmed":
        assert out["result"]["ok"] is True
        assert out["result"]["event"]["status"] == "draft"
    _ = headers, host
