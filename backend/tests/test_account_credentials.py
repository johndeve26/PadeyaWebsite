from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import EmailChangeToken
from app.core.security import hash_token
from app.email.models import EmailEvent
from tests.helpers.email_verification import mark_user_email_verified


def _register_and_token(
    client: TestClient,
    db_session: Session,
    email: str,
    *,
    username: str,
    password: str = "securepass1",
):
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "username": username,
        },
    )
    assert reg.status_code == 201, reg.text
    mark_user_email_verified(db_session, email=email)
    login = client.post(
        "/api/v1/auth/login",
        json={"login": email, "password": password},
    )
    assert login.status_code == 200
    return login.json()["access_token"]


def test_change_password(client: TestClient, db_session: Session):
    email = "change-pw@example.com"
    token = _register_and_token(client, db_session, email, username="change_pw")
    headers = {"Authorization": f"Bearer {token}"}
    bad = client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": "wrong", "new_password": "newsecurepass9"},
    )
    assert bad.status_code == 401
    ok = client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": "securepass1", "new_password": "newsecurepass9"},
    )
    assert ok.status_code == 200
    login = client.post(
        "/api/v1/auth/login",
        json={"login": email, "password": "newsecurepass9"},
    )
    assert login.status_code == 200


def test_change_email_requires_code_confirmation(client: TestClient, db_session: Session):
    email = "change-em@example.com"
    new_email = "changed-em@example.com"
    token = _register_and_token(client, db_session, email, username="change_em")
    headers = {"Authorization": f"Bearer {token}"}

    pending = client.post(
        "/api/v1/auth/change-email",
        headers=headers,
        json={
            "new_email": new_email,
            "current_password": "securepass1",
        },
    )
    assert pending.status_code == 200, pending.text
    body = pending.json()
    assert body["pending_email"] == new_email
    assert "code" in body["message"].lower() or "confirmation" in body["message"].lower()

    # Email must not change until confirm.
    still_old = client.post(
        "/api/v1/auth/login",
        json={"login": email, "password": "securepass1"},
    )
    assert still_old.status_code == 200

    row = db_session.scalar(
        select(EmailChangeToken)
        .where(EmailChangeToken.new_email == new_email)
        .order_by(EmailChangeToken.created_at.desc())
    )
    assert row is not None
    assert row.used_at is None

    templates = {
        event.template
        for event in db_session.scalars(
            select(EmailEvent).where(EmailEvent.recipient_email == new_email)
        )
    }
    assert "confirm_email_change" in templates

    # Plant a known code for confirm.
    raw_code = "AB12CD"
    row.code_hash = hash_token(raw_code)
    db_session.commit()

    bad = client.post(
        "/api/v1/auth/change-email/confirm",
        headers=headers,
        json={"code": "ZZZZZZ"},
    )
    assert bad.status_code == 400

    confirmed = client.post(
        "/api/v1/auth/change-email/confirm",
        headers=headers,
        json={"code": raw_code},
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["email"] == new_email

    login = client.post(
        "/api/v1/auth/login",
        json={"login": new_email, "password": "securepass1"},
    )
    assert login.status_code == 200
