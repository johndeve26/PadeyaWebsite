"""Support Center / ticketing tests."""

from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.messaging.models import InAppNotification
from app.support.sanitize import sanitize_support_text


def _register(client: TestClient, email: str, name: str = "User") -> dict[str, str]:
    res = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password123!", "full_name": name},
    )
    assert res.status_code == 201, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def _role(client: TestClient, assign_role, email: str, role: str) -> dict[str, str]:
    headers = _register(client, email, role)
    assign_role(email, role)
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_sanitize_strips_html():
    clean = sanitize_support_text('<script>alert(1)</script>Hello <b>there</b>')
    assert "<script" not in clean.lower()
    assert "Hello" in clean
    assert "there" in clean


def test_user_can_create_and_view_own_ticket(client: TestClient, assign_role):
    user = _register(client, "fan-support@example.com", "Fan")
    created = client.post(
        "/api/v1/support/tickets",
        headers=user,
        json={
            "subject": "Cannot see ticket",
            "category": "tickets_orders",
            "body": "My QR is missing on Pàdéyá.",
            "priority": "normal",
        },
    )
    assert created.status_code == 201, created.text
    tid = created.json()["id"]
    assert created.json()["case_number"].startswith("SUP-")
    assert created.json()["requester_context"] in {"fan", "host", "admin"}

    mine = client.get("/api/v1/support/tickets", headers=user)
    assert mine.status_code == 200
    assert any(t["id"] == tid for t in mine.json())

    other = _register(client, "other-fan@example.com", "Other")
    blocked = client.get(f"/api/v1/support/tickets/{tid}", headers=other)
    assert blocked.status_code == 403


def test_visitor_public_ticket_and_lookup(client: TestClient):
    created = client.post(
        "/api/v1/support/tickets/public",
        json={
            "subject": "Visitor help",
            "category": "other",
            "body": "I need help signing up on Pàdéyá.",
            "requester_email": "visitor@example.com",
            "requester_name": "Visitor",
            "website": "",
        },
    )
    assert created.status_code == 201, created.text
    number = created.json()["case_number"]
    token = created.json().get("public_token")
    assert token

    bad = client.get(f"/api/v1/support/tickets/by-number/{number}")
    assert bad.status_code == 403

    ok = client.get(
        f"/api/v1/support/tickets/by-number/{number}",
        params={"email": "visitor@example.com"},
    )
    assert ok.status_code == 200
    assert ok.json()["internal_notes"] == []


def test_visitor_can_reply_on_public_track(client: TestClient, assign_role):
    created = client.post(
        "/api/v1/support/tickets/public",
        json={
            "subject": "Need account help",
            "category": "account_login",
            "body": "I need help with fixing my account.",
            "requester_email": "track-reply@example.com",
            "requester_name": "Abiodun",
            "website": "",
        },
    )
    assert created.status_code == 201, created.text
    number = created.json()["case_number"]
    tid = created.json()["id"]

    admin = _role(client, assign_role, "track-reply-admin@example.com", "support_agent")
    staff_reply = client.post(
        f"/api/v1/admin/support/tickets/{tid}/reply",
        headers=admin,
        json={"body": "Please reply with more details."},
    )
    assert staff_reply.status_code == 200
    assert staff_reply.json()["status"] == "waiting_on_user"

    denied = client.post(
        f"/api/v1/support/tickets/by-number/{number}/reply",
        json={"body": "Here are more details about my account."},
    )
    assert denied.status_code == 403

    replied = client.post(
        f"/api/v1/support/tickets/by-number/{number}/reply",
        json={
            "body": "Here are more details about my account.",
            "email": "track-reply@example.com",
        },
    )
    assert replied.status_code == 200, replied.text
    assert replied.json()["status"] == "pending"
    bodies = [m["body"] for m in replied.json()["messages"]]
    assert "Here are more details about my account." in bodies
    assert replied.json()["internal_notes"] == []


def test_honeypot_does_not_leak_real_ticket(client: TestClient, db_session: Session):
    from app.support.models import SupportCase

    before = db_session.scalars(select(SupportCase)).all()
    before_count = len(before)
    res = client.post(
        "/api/v1/support/tickets/public",
        json={
            "subject": "Spam bot",
            "category": "other",
            "body": "Buy cheap tickets now please spam",
            "requester_email": "bot@spam.test",
            "requester_name": "Bot",
            "website": "http://spam.example",
        },
    )
    assert res.status_code == 201
    after = db_session.scalars(select(SupportCase)).all()
    assert len(after) == before_count


def test_internal_notes_hidden_from_user(client: TestClient, assign_role):
    user = _register(client, "note-fan@example.com")
    created = client.post(
        "/api/v1/support/tickets",
        headers=user,
        json={
            "subject": "Payment stuck",
            "category": "payments_refunds",
            "body": "Payment pending for hours.",
        },
    )
    tid = created.json()["id"]
    admin = _role(client, assign_role, "note-admin@example.com", "super_admin")
    note = client.post(
        f"/api/v1/admin/support/tickets/{tid}/internal-note",
        headers=admin,
        json={"body": "INTERNAL: check Paystack webhook secretly"},
    )
    assert note.status_code == 200
    assert any("INTERNAL" in n["body"] for n in note.json()["internal_notes"])

    user_view = client.get(f"/api/v1/support/tickets/{tid}", headers=user)
    assert user_view.status_code == 200
    assert user_view.json()["internal_notes"] == []
    assert all(not m.get("is_internal") for m in user_view.json()["messages"])


def test_admin_assign_resolve_and_notifications(
    client: TestClient, assign_role, db_session: Session
):
    user = _register(client, "notif-fan@example.com", "Fan Notif")
    created = client.post(
        "/api/v1/support/tickets",
        headers=user,
        json={
            "subject": "Urgent login",
            "category": "account_login",
            "body": "Cannot log in to my account at all.",
            "priority": "urgent",
        },
    )
    tid = created.json()["id"]
    admin = _role(client, assign_role, "notif-admin@example.com", "support_agent")

    # Get admin user id from /me
    me = client.get("/api/v1/auth/me", headers=admin)
    assert me.status_code == 200
    admin_id = me.json()["id"]

    assigned = client.patch(
        f"/api/v1/admin/support/tickets/{tid}/assign",
        headers=admin,
        json={"assignee_user_id": admin_id},
    )
    assert assigned.status_code == 200, assigned.text
    assert assigned.json()["assignee_user_id"] == admin_id

    replied = client.post(
        f"/api/v1/admin/support/tickets/{tid}/reply",
        headers=admin,
        json={"body": "Please try resetting your password."},
    )
    assert replied.status_code == 200
    assert replied.json()["status"] == "waiting_on_user"

    resolved = client.post(
        f"/api/v1/admin/support/tickets/{tid}/resolve", headers=admin
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"

    # Fan should have notifications
    me_fan = client.get("/api/v1/auth/me", headers=user)
    fan_id = UUID(me_fan.json()["id"])
    notifs = db_session.scalars(
        select(InAppNotification).where(InAppNotification.user_id == fan_id)
    ).all()
    kinds = {n.kind for n in notifs}
    assert "support.ticket_updated" in kinds


def test_unauthorized_cannot_access_admin_queue(client: TestClient):
    user = _register(client, "no-admin-support@example.com")
    res = client.get("/api/v1/admin/support/tickets", headers=user)
    assert res.status_code in {401, 403}


def test_rate_limit_public_support(client: TestClient):
    payload = {
        "subject": "Rate limit probe",
        "category": "other",
        "body": "Testing rate limits for public form on Pàdéyá.",
        "requester_email": "rate@example.com",
        "requester_name": "Rate",
        "website": "",
    }
    codes = []
    for i in range(7):
        payload["requester_email"] = f"rate{i}@example.com"
        codes.append(
            client.post("/api/v1/support/tickets/public", json=payload).status_code
        )
    assert 429 in codes


def test_deflection_events_and_ticket_metadata(client: TestClient, assign_role):
    ev = client.post(
        "/api/v1/support/deflection-events",
        json={
            "event_type": "support_topic_selected",
            "topic": "tickets_orders",
            "session_key": "abc123session",
        },
    )
    assert ev.status_code == 201, ev.text
    assert ev.json()["ok"] is True

    shown = client.post(
        "/api/v1/support/deflection-events",
        json={
            "event_type": "support_help_articles_shown",
            "topic": "tickets_orders",
            "session_key": "abc123session",
            "meta": {"count": 3},
        },
    )
    assert shown.status_code == 201

    solved = client.post(
        "/api/v1/support/deflection-events",
        json={
            "event_type": "support_issue_solved_without_ticket",
            "topic": "tickets_orders",
            "session_key": "abc123session",
        },
    )
    assert solved.status_code == 201

    user = _register(client, "deflect-fan@example.com", "Fan")
    created = client.post(
        "/api/v1/support/tickets",
        headers=user,
        json={
            "subject": "Still cannot find QR",
            "category": "tickets_orders",
            "body": "I read Help but still cannot find my QR ticket.",
            "priority": "normal",
            "deflection": {
                "topic": "tickets_orders",
                "suggested_article_slugs": [
                    "how-to-find-your-qr-ticket",
                    "how-guest-checkout-works",
                ],
                "articles_clicked": ["how-to-find-your-qr-ticket"],
                "session_key": "abc123session",
                "help_suggestions_shown": True,
                "referrer": "https://padeya.example/help",
            },
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["help_suggestions_shown"] is True
    # Public serialize hides full deflection_meta for non-staff
    assert created.json().get("deflection_meta") in (None, {})

    admin = _role(client, assign_role, "deflect-admin@example.com", "super_admin")
    detail = client.get(
        f"/api/v1/admin/support/tickets/{created.json()['id']}", headers=admin
    )
    assert detail.status_code == 200, detail.text
    assert detail.json()["help_suggestions_shown"] is True
    meta = detail.json()["deflection_meta"]
    assert meta is not None
    assert meta["topic"] == "tickets_orders"
    assert "how-to-find-your-qr-ticket" in meta["suggested_article_slugs"]


def test_invalid_deflection_event_rejected(client: TestClient):
    bad = client.post(
        "/api/v1/support/deflection-events",
        json={"event_type": "not_a_real_event", "topic": "other"},
    )
    assert bad.status_code == 400
