"""Authentication, roles, and permission tests."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.auth.models import PasswordResetToken
from app.passport.models import FanPassport
from app.hosts.models import Host
from app.users.models import User


def _register(
    client: TestClient,
    *,
    email: str = "buyer@example.com",
    password: str = "securepass1",
    full_name: str = "Test Buyer",
):
    return client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": full_name, "gender": "prefer_not_to_say"},
    )


def test_registration(client: TestClient):
    response = _register(client)
    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]
    assert len(body["refresh_token"]) >= 20


def test_registration_with_username(client: TestClient, db_session: Session):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "tolu@example.com",
            "password": "securepass1",
            "username": "tolu_afro",
        "gender": "prefer_not_to_say"},
    )
    assert response.status_code == 201
    user = db_session.scalar(select(User).where(User.email == "tolu@example.com"))
    assert user is not None
    assert user.full_name == "Tolu Afro"
    passport = db_session.scalar(
        select(FanPassport).where(FanPassport.user_id == user.id)
    )
    assert passport is not None
    assert passport.username == "tolu_afro"
    assert passport.display_name == "Tolu Afro"


def test_host_onboard_uses_passport_username_as_slug(
    client: TestClient, db_session: Session
):
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "host@example.com",
            "password": "securepass1",
            "username": "tolu_afro",
        "gender": "prefer_not_to_say"},
    )
    assert reg.status_code == 201
    token = reg.json()["access_token"]
    onboard = client.post(
        "/api/v1/hosts/onboard",
        headers={"Authorization": f"Bearer {token}"},
        json={"display_name": "Tolu Afro"},
    )
    assert onboard.status_code == 201
    host = db_session.scalar(select(Host).where(Host.slug == "tolu_afro"))
    assert host is not None


def test_registration_duplicate_username(client: TestClient):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "a@example.com",
            "password": "securepass1",
            "username": "same_handle",
        "gender": "prefer_not_to_say"},
    )
    again = client.post(
        "/api/v1/auth/register",
        json={
            "email": "b@example.com",
            "password": "securepass1",
            "username": "same_handle",
        "gender": "prefer_not_to_say"},
    )
    assert again.status_code == 409


def test_registration_duplicate_email(client: TestClient):
    assert _register(client).status_code == 201
    again = _register(client)
    assert again.status_code == 409
    assert "email" in again.json()["detail"].lower()


def test_registration_duplicate_username_message(client: TestClient):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "first@example.com",
            "password": "securepass1",
            "username": "dup_msg_user",
        "gender": "prefer_not_to_say"},
    )
    again = client.post(
        "/api/v1/auth/register",
        json={
            "email": "second@example.com",
            "password": "securepass1",
            "username": "dup_msg_user",
        "gender": "prefer_not_to_say"},
    )
    assert again.status_code == 409
    assert "username" in again.json()["detail"].lower()


def test_password_reset_request(client: TestClient, db_session: Session):
    _register(client, email="reset-me@example.com")
    response = client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "reset-me@example.com"},
    )
    assert response.status_code == 200
    assert "account exists" in response.json()["message"].lower()
    user = db_session.scalar(select(User).where(User.email == "reset-me@example.com"))
    assert user is not None
    token = db_session.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        )
    )
    assert token is not None


def test_password_reset_request_unknown_email_same_message(client: TestClient):
    known = client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "nobody-here@example.com"},
    )
    assert known.status_code == 200
    _register(client, email="known@example.com")
    registered = client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "known@example.com"},
    )
    assert registered.status_code == 200
    assert known.json()["message"] == registered.json()["message"]


def test_password_reset_request_cooldown(client: TestClient, monkeypatch):
    _register(client, email="cooldown@example.com")
    first = client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "cooldown@example.com"},
    )
    assert first.status_code == 200
    second = client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "cooldown@example.com"},
    )
    assert second.status_code == 429
    assert "wait" in second.json()["detail"].lower()


def test_password_reset_confirm_with_code(client: TestClient, monkeypatch):
    monkeypatch.setattr(
        "app.auth.password_reset.generate_password_reset_code",
        lambda: "ABC234",
    )
    _register(client, email="code-reset@example.com", password="securepass1")
    req = client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "code-reset@example.com"},
    )
    assert req.status_code == 200
    verify = client.post(
        "/api/v1/auth/password-reset/verify",
        json={"email": "code-reset@example.com", "code": "abc-234"},
    )
    assert verify.status_code == 200, verify.text
    confirm = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={
            "email": "code-reset@example.com",
            "code": "abc-234",
            "new_password": "newsecurepass9",
        },
    )
    assert confirm.status_code == 200, confirm.text
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "code-reset@example.com", "password": "newsecurepass9"},
    )
    assert login.status_code == 200


def test_login(client: TestClient):
    _register(client, email="login@example.com", password="securepass1")
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "login@example.com", "password": "securepass1"},
    )
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_login_with_username(client: TestClient):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "uname-login@example.com",
            "password": "securepass1",
            "username": "uname_login",
        "gender": "prefer_not_to_say"},
    )
    response = client.post(
        "/api/v1/auth/login",
        json={"login": "uname_login", "password": "securepass1"},
    )
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_login_invalid_password(client: TestClient):
    _register(client, email="badlogin@example.com")
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "badlogin@example.com", "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_login_survives_failed_admin_team_audit(
    client: TestClient, monkeypatch
):
    """Admin-team login audit must not 500 login when its SQL fails.

    Production bug: missing admin_team tables aborted the Postgres transaction;
    bare except swallowed the error but left the txn poisoned, so refresh_token
    INSERT/commit raised InFailedSqlTransaction. Login isolates that path in a
    SAVEPOINT (begin_nested).
    """
    _register(client, email="auditfail@example.com", password="securepass1")

    def boom(db: Session, *, user, ip_address=None, user_agent=None):
        db.execute(text("SELECT 1 FROM __missing_admin_audit_logs__"))

    monkeypatch.setattr(
        "app.admin_team.service.record_admin_login_if_applicable",
        boom,
    )
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "auditfail@example.com", "password": "securepass1"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["access_token"]


def test_refresh_token(client: TestClient):
    registered = _register(client, email="refresh@example.com").json()
    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": registered["refresh_token"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"] != registered["refresh_token"]

    # Concurrent refresh race: recently rotated tokens get a brief reuse grace.
    replay = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": registered["refresh_token"]},
    )
    assert replay.status_code == 200
    assert replay.json()["refresh_token"] != body["refresh_token"]


def test_refresh_token_reuse_after_grace_rejected(
    client: TestClient, db_session: Session
):
    from datetime import UTC, datetime, timedelta

    from app.auth.models import RefreshToken

    registered = _register(client, email="refresh-grace@example.com").json()
    first = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": registered["refresh_token"]},
    )
    assert first.status_code == 200

    # Age the revoked row past the reuse window.
    row = (
        db_session.query(RefreshToken)
        .filter(RefreshToken.revoked_at.is_not(None))
        .order_by(RefreshToken.revoked_at.desc())
        .first()
    )
    assert row is not None
    row.revoked_at = datetime.now(UTC) - timedelta(seconds=31)
    db_session.commit()

    replay = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": registered["refresh_token"]},
    )
    assert replay.status_code == 401


def test_me(client: TestClient):
    tokens = _register(client, email="me@example.com", full_name="Me User").json()
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "me@example.com"
    assert body["full_name"] == "Me User"
    assert "buyer" in body["roles"]


def test_me_requires_auth(client: TestClient):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_logout(client: TestClient):
    tokens = _register(client, email="logout@example.com").json()
    response = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert response.status_code == 200
    refreshed = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refreshed.status_code == 401


def test_role_checks(client: TestClient, assign_role):
    tokens = _register(client, email="roles@example.com").json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    denied = client.get("/api/v1/users/admin-check", headers=headers)
    assert denied.status_code == 403

    assign_role("roles@example.com", "finance_admin")
    # Role change requires a fresh token with updated claims is NOT required for
    # require_role — it loads roles from DB via get_current_user.
    allowed = client.get("/api/v1/users/admin-check", headers=headers)
    assert allowed.status_code == 200


def test_permission_checks(client: TestClient, assign_role, db_session):
    tokens = _register(client, email="perms@example.com").json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    denied = client.get("/api/v1/users/permission-check", headers=headers)
    assert denied.status_code == 403

    assign_role("perms@example.com", "support_agent")
    # MVP: support no longer seeds users.read (user mgmt uses admin.users.*).
    assert client.get("/api/v1/users/permission-check", headers=headers).status_code == 403

    from app.users.service import get_permission_by_code, get_role_by_name

    role = get_role_by_name(db_session, "support_agent")
    perm = get_permission_by_code(db_session, "users.read")
    assert role is not None and perm is not None
    if perm not in role.permissions:
        role.permissions.append(perm)
        db_session.commit()
    assert client.get("/api/v1/users/permission-check", headers=headers).status_code == 200

    # super_admin with admin.full_access also passes
    assign_role("perms@example.com", "super_admin")
    assert client.get("/api/v1/users/permission-check", headers=headers).status_code == 200
