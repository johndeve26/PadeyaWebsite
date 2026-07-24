from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

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


def test_change_email(client: TestClient, db_session: Session):
    email = "change-em@example.com"
    token = _register_and_token(client, db_session, email, username="change_em")
    headers = {"Authorization": f"Bearer {token}"}
    updated = client.post(
        "/api/v1/auth/change-email",
        headers=headers,
        json={
            "new_email": "changed-em@example.com",
            "current_password": "securepass1",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["email"] == "changed-em@example.com"
    login = client.post(
        "/api/v1/auth/login",
        json={"login": "changed-em@example.com", "password": "securepass1"},
    )
    assert login.status_code == 200
