"""Admin internal notes MVP — types, admin-only, audited, no secrets."""

from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import AuditLog
from app.users.models import UserAdminNote
from app.users.note_constants import NOTE_TYPES


def _auth(client: TestClient, email: str, name: str = "User") -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass1", "full_name": name},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _relogin(client: TestClient, email: str) -> dict[str, str]:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_internal_notes_mvp(
    client: TestClient, assign_role, db_session: Session
):
    target_h = _auth(client, "notes-target@example.com", "Notes Target")
    user_id = client.get("/api/v1/users/me", headers=target_h).json()["id"]

    # Target cannot list their own admin notes (admin-only route).
    denied = client.get(
        f"/api/v1/users/admin/{user_id}/notes",
        headers=target_h,
    )
    assert denied.status_code in {401, 403}

    me = client.get("/api/v1/users/me", headers=target_h)
    assert me.status_code == 200
    assert "internal_notes" not in me.json()
    assert "admin_notes" not in me.json()

    admin_email = "notes-admin@example.com"
    _auth(client, admin_email, "Notes Admin")
    assign_role(admin_email, "super_admin")
    admin = _relogin(client, admin_email)

    bad_type = client.post(
        f"/api/v1/users/admin/{user_id}/notes",
        headers=admin,
        json={"note_type": "gossip", "body": "Not a valid type"},
    )
    assert bad_type.status_code == 400

    secret = client.post(
        f"/api/v1/users/admin/{user_id}/notes",
        headers=admin,
        json={
            "note_type": "security",
            "body": "User password: hunter2 please rotate",
        },
    )
    assert secret.status_code == 400

    tokenish = client.post(
        f"/api/v1/users/admin/{user_id}/notes",
        headers=admin,
        json={
            "note_type": "security",
            "body": "access_token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.aaa.bbb",
        },
    )
    assert tokenish.status_code == 400

    created = client.post(
        f"/api/v1/users/admin/{user_id}/notes",
        headers=admin,
        json={
            "note_type": "fraud",
            "body": "Reviewed refund trail — no abuse found",
        },
    )
    assert created.status_code == 200, created.text
    note = created.json()
    assert note["note_type"] == "fraud"
    assert note["body"] == "Reviewed refund trail — no abuse found"
    assert note["created_by_admin_id"]
    assert note["updated_at"] is None
    assert "author_user_id" not in note
    note_id = note["id"]

    row = db_session.get(UserAdminNote, UUID(note_id))
    assert row is not None
    assert row.note_type == "fraud"
    assert row.updated_at is None

    audits = list(
        db_session.scalars(
            select(AuditLog).where(
                AuditLog.action == "admin_user_note_created",
                AuditLog.resource_id == user_id,
            )
        ).all()
    )
    assert audits
    assert audits[0].details["after_json"]["note_type"] == "fraud"
    assert "body" not in (audits[0].details or {})
    assert "body" not in (audits[0].details.get("after_json") or {})

    listed = client.get(
        f"/api/v1/users/admin/{user_id}/notes",
        headers=admin,
    )
    assert listed.status_code == 200
    assert any(item["id"] == note_id for item in listed.json())

    detail = client.get(f"/api/v1/users/admin/{user_id}", headers=admin)
    assert detail.status_code == 200
    notes = detail.json()["moderation"]["internal_notes"]
    assert any(n["id"] == note_id and n["note_type"] == "fraud" for n in notes)

    assert len(NOTE_TYPES) == 6
