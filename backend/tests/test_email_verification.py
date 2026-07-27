"""Email verification on signup, resend, and confirm."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import EmailVerificationToken
from app.core.security import hash_token
from app.email.models import EmailEvent
from app.users.models import User


def _register(client, *, email: str, username: str, password: str = "securepass1"):
    return client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "username": username},
    )


def test_register_sends_welcome_and_verify_email(client, db_session: Session):
    email = "verify-flow@example.com"
    response = _register(client, email=email, username="verify_flow")
    assert response.status_code == 201

    user = db_session.scalar(select(User).where(User.email == email))
    assert user is not None
    assert user.is_verified is False

    templates = {
        row.template
        for row in db_session.scalars(
            select(EmailEvent).where(EmailEvent.recipient_user_id == user.id)
        )
    }
    assert "welcome" in templates
    assert "verify_email" in templates

    token_row = db_session.scalar(
        select(EmailVerificationToken).where(EmailVerificationToken.user_id == user.id)
    )
    assert token_row is not None
    assert token_row.used_at is None


def test_login_works_before_email_verified(client):
    email = "unverified-login@example.com"
    reg = _register(client, email=email, username="unverified_login")
    assert reg.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={"login": email, "password": "securepass1"},
    )
    assert login.status_code == 200


def test_confirm_with_link_token(client, db_session: Session):
    email = "confirm-link@example.com"
    assert _register(client, email=email, username="confirm_link").status_code == 201

    raw_token = "test-email-verify-token-value-32chars!!"
    user = db_session.scalar(select(User).where(User.email == email))
    assert user is not None
    row = db_session.scalar(
        select(EmailVerificationToken).where(EmailVerificationToken.user_id == user.id)
    )
    assert row is not None
    row.token_hash = hash_token(raw_token)
    db_session.commit()

    confirm = client.post(
        "/api/v1/auth/email/verify/confirm",
        json={"token": raw_token},
    )
    assert confirm.status_code == 200
    assert confirm.json().get("access_token")
    assert confirm.json().get("refresh_token")
    db_session.refresh(user)
    assert user.is_verified is True
    db_session.refresh(row)
    assert row.used_at is not None


def test_confirm_with_code_while_signed_in(client, db_session: Session):
    email = "confirm-code@example.com"
    reg = _register(client, email=email, username="confirm_code")
    assert reg.status_code == 201
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    raw_code = "ABC234"
    user = db_session.scalar(select(User).where(User.email == email))
    assert user is not None
    row = db_session.scalar(
        select(EmailVerificationToken).where(EmailVerificationToken.user_id == user.id)
    )
    assert row is not None
    row.code_hash = hash_token(raw_code)
    db_session.commit()

    confirm = client.post(
        "/api/v1/auth/email/verify/confirm",
        headers=headers,
        json={"code": raw_code},
    )
    assert confirm.status_code == 200
    assert confirm.json().get("access_token")
    db_session.refresh(user)
    assert user.is_verified is True


def test_resend_verification_messages(client, db_session: Session):
    email = "resend@example.com"
    reg = _register(client, email=email, username="resend_verify")
    assert reg.status_code == 201
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    # Register already queued verify_email — immediate resend is rate-limited.
    cooled = client.post("/api/v1/auth/email/verify/request", headers=headers)
    assert cooled.status_code == 429
    assert "wait" in cooled.json()["detail"].lower()

    user = db_session.scalar(select(User).where(User.email == email))
    assert user is not None
    latest = db_session.scalar(
        select(EmailVerificationToken)
        .where(EmailVerificationToken.user_id == user.id)
        .order_by(EmailVerificationToken.created_at.desc())
        .limit(1)
    )
    assert latest is not None
    from datetime import UTC, datetime, timedelta

    latest.created_at = datetime.now(UTC) - timedelta(minutes=2)
    db_session.commit()

    tokens_before = len(
        list(
            db_session.scalars(
                select(EmailVerificationToken).where(
                    EmailVerificationToken.user_id == user.id
                )
            )
        )
    )

    sent = client.post("/api/v1/auth/email/verify/request", headers=headers)
    assert sent.status_code == 200
    assert "verification code" in sent.json()["message"].lower()
    tokens_after = len(
        list(
            db_session.scalars(
                select(EmailVerificationToken).where(
                    EmailVerificationToken.user_id == user.id
                )
            )
        )
    )
    assert tokens_after == tokens_before + 1

    user.is_verified = True
    db_session.commit()

    third = client.post("/api/v1/auth/email/verify/request", headers=headers)
    assert third.status_code == 200
    assert "already verified" in third.json()["message"].lower()


def test_change_password_requires_verified_email(client, db_session: Session):
    email = "pw-guard@example.com"
    reg = _register(client, email=email, username="pw_guard")
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    blocked = client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": "securepass1", "new_password": "newsecurepass9"},
    )
    assert blocked.status_code == 403

    from tests.helpers.email_verification import mark_user_email_verified

    mark_user_email_verified(db_session, email=email)
    ok = client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": "securepass1", "new_password": "newsecurepass9"},
    )
    assert ok.status_code == 200
