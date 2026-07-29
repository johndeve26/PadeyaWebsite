"""Canonical host team API surface (`/host/team`, `/me`, `/admin/teams`)."""

from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.email.models import EmailEvent
from app.hosts.models import Host
from app.teams.workspace_pref import UserActiveWorkspace


def _auth(client: TestClient, email: str, name: str = "User") -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass1", "full_name": name, "gender": "prefer_not_to_say"},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _onboard(client: TestClient, headers: dict[str, str], name: str) -> dict:
    r = client.post(
        "/api/v1/hosts/onboard",
        headers=headers,
        json={
            "display_name": name,
            "bio": "Team host",
            "city": "Lagos",
            "state": "Lagos",
            "country": "Nigeria",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _invite_token(db: Session, email: str) -> str:
    email_row = db.scalar(
        select(EmailEvent)
        .where(
            EmailEvent.recipient_email == email,
            EmailEvent.template == "team_invite",
        )
        .order_by(EmailEvent.created_at.desc())
    )
    assert email_row is not None
    path = (email_row.context_json or {})["invite_path"]
    return path.rsplit("/", 1)[-1]


def test_team_invite_list_accept_via_canonical_paths(
    client: TestClient, db_session: Session
):
    host_h = _auth(client, "api-host@example.com", "API Host")
    host = _onboard(client, host_h, "API Host Co")

    roles = client.get("/api/v1/host/team/roles", headers=host_h)
    assert roles.status_code == 200
    assert any(r["role"] == "scanner" for r in roles.json())

    perms = client.get("/api/v1/host/team/permissions", headers=host_h)
    assert perms.status_code == 200
    assert "events.view" in perms.json()["keys"]

    created = client.post(
        "/api/v1/host/team/invites",
        headers=host_h,
        json={
            "invite_identifier": "api-member@example.com",
            "role": "scanner",
            "permissions_json": {"tickets.scan_qr": True},
            "scope_json": {"type": "host_wide", "event_ids": []},
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    invite_id = body["invite_id"]
    assert body["invite_method"] == "email"
    assert body["status"] == "pending"
    assert body["masked_email"]
    assert "api-member@example.com" not in body["masked_email"]
    assert body.get("username") is None

    invites = client.get("/api/v1/host/team/invites", headers=host_h)
    assert invites.status_code == 200
    assert any(i["id"] == invite_id for i in invites.json())

    members = client.get("/api/v1/host/team", headers=host_h)
    assert members.status_code == 200
    assert all(m["status"] != "pending" for m in members.json())

    token = _invite_token(db_session, "api-member@example.com")
    preview = client.get(f"/api/v1/team/invites/{token}")
    assert preview.status_code == 200
    assert preview.json()["status"] == "pending"

    member_h = _auth(client, "api-member@example.com", "API Member")
    accepted = client.post(
        f"/api/v1/team/invites/{token}/accept",
        headers=member_h,
    )
    assert accepted.status_code == 200, accepted.text
    member_id = accepted.json()["id"]
    assert accepted.json()["status"] == "active"
    assert member_id != invite_id

    members_after = client.get(
        f"/api/v1/host/team?host_id={host['id']}",
        headers=host_h,
    )
    assert any(m["id"] == member_id for m in members_after.json())

    patched = client.patch(
        f"/api/v1/host/team/members/{member_id}?host_id={host['id']}",
        headers=host_h,
        json={"role": "viewer", "role_label": "Viewer"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["role"] == "viewer"

    suspended = client.post(
        f"/api/v1/host/team/members/{member_id}/suspend?host_id={host['id']}",
        headers=host_h,
    )
    assert suspended.status_code == 200
    assert suspended.json()["status"] == "suspended"

    removed = client.post(
        f"/api/v1/host/team/members/{member_id}/remove?host_id={host['id']}",
        headers=host_h,
    )
    assert removed.status_code == 200
    assert removed.json()["status"] == "removed"

    audit = client.get(
        f"/api/v1/host/team/audit-log?host_id={host['id']}",
        headers=host_h,
    )
    assert audit.status_code == 200
    assert len(audit.json()) >= 1


def test_revoke_invite_canonical_path(client: TestClient):
    host_h = _auth(client, "revoke-api-host@example.com", "Revoke Host")
    _onboard(client, host_h, "Revoke Host Co")

    created = client.post(
        "/api/v1/host/team/invites",
        headers=host_h,
        json={"invite_identifier": "revoke-api@example.com", "role": "scanner"},
    )
    assert created.status_code == 201
    invite_id = created.json()["invite_id"]

    revoked = client.post(
        f"/api/v1/host/team/invites/{invite_id}/revoke",
        headers=host_h,
    )
    assert revoked.status_code == 200
    # Public status maps revoked → declined for invitee-facing vocabulary.
    assert revoked.json()["status"] in {"revoked", "declined"}


def test_me_workspaces_and_active_workspace(client: TestClient, db_session: Session):
    host_h = _auth(client, "ws-host@example.com", "WS Host")
    host = _onboard(client, host_h, "WS Host Co")

    listed = client.get("/api/v1/me/team-workspaces", headers=host_h)
    assert listed.status_code == 200
    assert any(w["host_id"] == host["id"] for w in listed.json())

    set_active = client.post(
        "/api/v1/me/active-workspace",
        headers=host_h,
        json={"host_id": host["id"]},
    )
    assert set_active.status_code == 200, set_active.text
    assert set_active.json()["host_id"] == host["id"]

    host_row = db_session.get(Host, UUID(host["id"]))
    assert host_row is not None
    pref = db_session.get(UserActiveWorkspace, host_row.user_id)
    assert pref is not None
    assert pref.host_id == host_row.id

    again = client.get("/api/v1/me/team-workspaces", headers=host_h)
    active_flags = [w for w in again.json() if w["host_id"] == host["id"]]
    assert active_flags and active_flags[0]["is_active"] is True


def test_admin_teams_list_and_audit(client: TestClient, assign_role):
    host_h = _auth(client, "admin-teams-host@example.com", "Admin Teams Host")
    host = _onboard(client, host_h, "Admin Teams Co")
    client.post(
        "/api/v1/host/team/invites",
        headers=host_h,
        json={"email": "admin-teams-invitee@example.com", "role": "scanner"},
    )

    admin_h = _auth(client, "admin-teams-admin@example.com", "Platform Admin")
    assign_role("admin-teams-admin@example.com", "super_admin")

    teams = client.get("/api/v1/admin/teams", headers=admin_h)
    assert teams.status_code == 200, teams.text
    assert any(t["host_id"] == host["id"] for t in teams.json())

    audit = client.get("/api/v1/admin/teams/audit", headers=admin_h)
    assert audit.status_code == 200
    assert isinstance(audit.json(), list)
