"""Selective user restrictions — table-backed admin API + enforcement."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import AuditLog
from app.users.account_status_constants import FULL_SUSPENSION_RESTRICTIONS
from app.users.models import User, UserRestriction
from app.users.restrictions import (
    assert_can_checkout,
    assert_can_create_events,
    assert_can_message,
    assert_can_promote_as_ambassador,
    assert_can_scan_tickets,
    assert_can_submit_review,
    assert_can_use_fan_connect,
    user_has_restriction,
)


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


def _me_id(client: TestClient, headers: dict[str, str]) -> str:
    return client.get("/api/v1/users/me", headers=headers).json()["id"]


def _admin(client: TestClient, assign_role, email: str = "restrict-admin@example.com"):
    _auth(client, email, "Restrict Admin")
    assign_role(email, "super_admin")
    return _relogin(client, email)


def test_admin_add_cannot_message_and_blocks_send(
    client: TestClient, assign_role, db_session: Session
):
    target_h = _auth(client, "msg-target@example.com", "Msg Target")
    target_id = _me_id(client, target_h)
    admin = _admin(client, assign_role)

    added = client.post(
        f"/api/v1/admin/users/{target_id}/restrictions",
        headers=admin,
        json={
            "restriction_keys": ["cannot_message"],
            "reason": "Harassment report under review",
            "internal_note": "Case #1234",
        },
    )
    assert added.status_code == 200, added.text
    body = added.json()
    assert body["account_status"] == "restricted"
    assert "cannot_message" in body["active_keys"]
    assert any(i["restriction_key"] == "cannot_message" for i in body["items"])

    me = client.get("/api/v1/users/me", headers=target_h)
    assert me.status_code == 200
    assert "cannot_message" in me.json()["restriction_keys"]
    # Never leak admin notes to end-user /me
    assert "internal_note" not in me.json()
    assert "Case #1234" not in str(me.json())

    target = db_session.get(User, UUID(target_id))
    assert target is not None
    with pytest.raises(HTTPException) as exc:
        assert_can_message(db_session, target)
    assert exc.value.status_code == 403
    assert "cannot_message" in str(exc.value.detail)

    audits = list(
        db_session.scalars(
            select(AuditLog).where(
                AuditLog.action == "admin_user_restriction_added",
                AuditLog.resource_id == target_id,
            )
        ).all()
    )
    assert audits
    details = audits[-1].details or {}
    assert details.get("reason")
    assert details.get("internal_note_present") is True
    assert "Case #1234" not in str(details)


def test_revoke_restores_messaging(
    client: TestClient, assign_role, db_session: Session
):
    target_h = _auth(client, "msg-revoke@example.com")
    target_id = _me_id(client, target_h)
    admin = _admin(client, assign_role, "revoke-admin@example.com")

    added = client.post(
        f"/api/v1/admin/users/{target_id}/restrictions",
        headers=admin,
        json={
            "restriction_keys": ["cannot_message"],
            "reason": "Temp mute",
        },
    )
    assert added.status_code == 200
    rid = next(
        i["id"]
        for i in added.json()["items"]
        if i["restriction_key"] == "cannot_message" and i["status"] == "active"
    )

    revoked = client.post(
        f"/api/v1/admin/users/{target_id}/restrictions/{rid}/revoke",
        headers=admin,
        json={"reason": "Appeal accepted"},
    )
    assert revoked.status_code == 200, revoked.text
    assert revoked.json()["status"] == "revoked"

    listed = client.get(
        f"/api/v1/admin/users/{target_id}/restrictions", headers=admin
    )
    assert listed.status_code == 200
    assert "cannot_message" not in listed.json()["active_keys"]
    assert listed.json()["account_status"] == "active"

    target = db_session.get(User, UUID(target_id))
    assert_can_message(db_session, target)  # does not raise

    audits = list(
        db_session.scalars(
            select(AuditLog).where(
                AuditLog.action == "admin_user_restriction_revoked",
                AuditLog.resource_id == target_id,
            )
        ).all()
    )
    assert audits


def test_reason_required_and_cannot_restrict_self(
    client: TestClient, assign_role
):
    admin = _admin(client, assign_role, "self-admin@example.com")
    admin_id = _me_id(client, admin)

    no_reason = client.post(
        f"/api/v1/admin/users/{admin_id}/restrictions",
        headers=admin,
        json={"restriction_keys": ["cannot_message"], "reason": "ab"},
    )
    assert no_reason.status_code in {400, 422}

    self_hit = client.post(
        f"/api/v1/admin/users/{admin_id}/restrictions",
        headers=admin,
        json={
            "restriction_keys": ["cannot_message"],
            "reason": "Trying to restrict myself",
        },
    )
    assert self_hit.status_code == 400
    assert "own" in self_hit.json()["detail"].lower()


def test_normal_admin_cannot_restrict_super_admin(
    client: TestClient, assign_role, db_session: Session
):
    _auth(client, "platform-sa@example.com", "Platform SA")
    assign_role("platform-sa@example.com", "super_admin")
    sa_id = _me_id(client, _relogin(client, "platform-sa@example.com"))

    _auth(client, "normal-mod@example.com", "Normal Mod")
    assign_role("normal-mod@example.com", "support_agent")

    from app.users.models import Permission, Role

    role = db_session.scalar(select(Role).where(Role.name == "support_agent"))
    assert role is not None
    perms = list(role.permissions)
    for code in (
        "admin.users.add_restriction",
        "admin.users.view_restrictions",
        "admin.users.revoke_restriction",
        "admin.users.restrict",
    ):
        perm = db_session.scalar(select(Permission).where(Permission.code == code))
        if perm is None:
            perm = Permission(code=code, description=code)
            db_session.add(perm)
            db_session.flush()
        if perm not in perms:
            perms.append(perm)
    role.permissions = perms
    db_session.commit()

    mod = _relogin(client, "normal-mod@example.com")
    blocked = client.post(
        f"/api/v1/admin/users/{sa_id}/restrictions",
        headers=mod,
        json={
            "restriction_keys": ["cannot_message"],
            "reason": "Should not work on super_admin",
        },
    )
    assert blocked.status_code == 403


@pytest.mark.parametrize(
    "key,asserter",
    [
        ("cannot_checkout", assert_can_checkout),
        ("cannot_use_fan_connect", assert_can_use_fan_connect),
        ("cannot_submit_reviews", assert_can_submit_review),
        ("cannot_create_events", assert_can_create_events),
        ("cannot_scan_tickets", assert_can_scan_tickets),
        ("cannot_promote_events", assert_can_promote_as_ambassador),
    ],
)
def test_restriction_blocks_category_helper(
    client: TestClient, assign_role, db_session: Session, key, asserter
):
    target_h = _auth(client, f"{key}@example.com")
    target_id = _me_id(client, target_h)
    admin = _admin(client, assign_role, f"admin-{key}@example.com")

    resp = client.post(
        f"/api/v1/admin/users/{target_id}/restrictions",
        headers=admin,
        json={"restriction_keys": [key], "reason": f"Block {key}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["account_status"] == "restricted"

    target = db_session.get(User, UUID(target_id))
    with pytest.raises(HTTPException) as exc:
        if key == "cannot_scan_tickets":
            asserter(db_session, target)
        else:
            asserter(db_session, target)
    assert exc.value.status_code == 403
    assert key.split("_")[1] in str(exc.value.detail) or key in str(exc.value.detail)


def test_ends_at_expires_restriction(
    client: TestClient, assign_role, db_session: Session
):
    target_h = _auth(client, "expire-target@example.com")
    target_id = _me_id(client, target_h)
    admin = _admin(client, assign_role, "expire-admin@example.com")

    # Create with future ends_at then backdate in DB
    ends = (datetime.now(UTC) + timedelta(days=1)).isoformat().replace("+00:00", "Z")
    added = client.post(
        f"/api/v1/admin/users/{target_id}/restrictions",
        headers=admin,
        json={
            "restriction_keys": ["cannot_message"],
            "reason": "Temporary mute",
            "ends_at": ends,
        },
    )
    assert added.status_code == 200, added.text
    rid = UUID(added.json()["items"][0]["id"])

    row = db_session.get(UserRestriction, rid)
    assert row is not None
    row.ends_at = datetime.now(UTC) - timedelta(minutes=1)
    db_session.commit()

    assert user_has_restriction(db_session, UUID(target_id), "cannot_message") is False

    listed = client.get(
        f"/api/v1/admin/users/{target_id}/restrictions", headers=admin
    )
    assert listed.status_code == 200
    assert "cannot_message" not in listed.json()["active_keys"]


def test_full_suspension_preset_blocks_activity(
    client: TestClient, assign_role, db_session: Session
):
    target_h = _auth(client, "full-suspend@example.com")
    target_id = _me_id(client, target_h)
    admin = _admin(client, assign_role, "full-suspend-admin@example.com")

    resp = client.post(
        f"/api/v1/admin/users/{target_id}/restrictions",
        headers=admin,
        json={
            "restriction_keys": list(FULL_SUSPENSION_RESTRICTIONS[:3]),
            "reason": "Severe abuse — full suspension preset",
            "preset": "full_suspension",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["account_status"] == "suspended"
    # Major keys applied
    assert "cannot_message" in body["active_keys"]
    assert "cannot_checkout" in body["active_keys"]
    assert "read_only_account" in body["active_keys"]

    # /me is allowlisted for appeal/status; activity gates still block.
    me = client.get("/api/v1/users/me", headers=target_h)
    assert me.status_code == 200
    assert me.json()["account_status"] == "suspended"

    target = db_session.get(User, UUID(target_id))
    assert target is not None
    with pytest.raises(HTTPException) as exc:
        assert_can_message(db_session, target)
    assert exc.value.status_code == 403

    audits = list(
        db_session.scalars(
            select(AuditLog).where(
                AuditLog.action == "admin_user_restriction_preset_applied",
                AuditLog.resource_id == target_id,
            )
        ).all()
    )
    assert audits


def test_extend_restriction_audit(
    client: TestClient, assign_role, db_session: Session
):
    target_h = _auth(client, "extend-target@example.com")
    target_id = _me_id(client, target_h)
    admin = _admin(client, assign_role, "extend-admin@example.com")

    added = client.post(
        f"/api/v1/admin/users/{target_id}/restrictions",
        headers=admin,
        json={"restriction_keys": ["cannot_checkout"], "reason": "Fraud review"},
    )
    rid = added.json()["items"][0]["id"]
    new_end = (datetime.now(UTC) + timedelta(days=14)).isoformat().replace("+00:00", "Z")
    patched = client.patch(
        f"/api/v1/admin/users/{target_id}/restrictions/{rid}",
        headers=admin,
        json={"reason": "Extending while investigation continues", "ends_at": new_end},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["ends_at"] is not None

    audits = list(
        db_session.scalars(
            select(AuditLog).where(
                AuditLog.action == "admin_user_restriction_extended",
                AuditLog.resource_id == target_id,
            )
        ).all()
    )
    assert audits
