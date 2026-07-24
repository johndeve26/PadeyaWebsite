"""Admin email provider settings — encryption, override, fallbacks."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.encryption import decrypt_secret, encrypt_secret
from app.email.config import email_runtime
from app.email.provider import LogEmailProvider, get_email_provider
from app.email.queue import drain_email_outbox
from app.email.service import enqueue_template
from app.email.settings_service import (
    get_active_provider_settings,
    update_provider_settings,
)
from app.users.seed import seed_roles_and_permissions


def test_encrypt_secret_roundtrip_not_plaintext():
    token = encrypt_secret("smtp-password-value")
    assert "smtp-password-value" not in token
    assert decrypt_secret(token) == "smtp-password-value"


def test_db_settings_override_env(db_session: Session, monkeypatch):
    from app.core.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "smtp_host", "env.example.com")
    monkeypatch.setattr(settings, "email_provider", "log")
    monkeypatch.setattr(settings, "email_dev_mode", True)

    env_cfg = email_runtime(settings, db=db_session)
    assert env_cfg.smtp_host == "env.example.com"

    update_provider_settings(
        db_session,
        updates={
            "provider": "smtp",
            "dev_mode": False,
            "email_enabled": True,
            "smtp_host": "db.example.com",
            "smtp_port": 587,
            "smtp_from_email": "noreply@padeya.com",
            "smtp_from_name": "Pàdéyá",
            "smtp_username": "user@padeya.com",
            "smtp_password": "db-secret",
            "smtp_use_tls": True,
            "smtp_use_ssl": False,
        },
        actor_user_id=None,
        commit=True,
    )
    cfg = email_runtime(settings, db=db_session)
    assert cfg.smtp_host == "db.example.com"
    assert cfg.smtp_password == "db-secret"
    assert cfg.provider == "smtp"


def test_fallback_to_log_when_no_db_and_log_env(db_session: Session, monkeypatch):
    from app.core.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "email_provider", "log")
    monkeypatch.setattr(settings, "email_dev_mode", True)
    monkeypatch.setattr(settings, "email_enabled", True)
    provider = get_email_provider(db=db_session)
    assert isinstance(provider, LogEmailProvider)


def test_worker_drain_uses_active_db_provider(db_session: Session):
    seed_roles_and_permissions(db_session)
    update_provider_settings(
        db_session,
        updates={
            "provider": "log",
            "dev_mode": True,
            "email_enabled": True,
            "smtp_from_email": "noreply@padeya.com",
            "smtp_from_name": "Pàdéyá",
        },
        actor_user_id=None,
        commit=True,
    )
    enqueue_template(
        db_session,
        template="welcome",
        to="worker-settings@example.com",
        context={"full_name": "Worker"},
        dedupe_key="worker-settings:1",
    )
    db_session.commit()
    stats = drain_email_outbox(db_session, limit=5, commit=True)
    assert stats.sent >= 1
    assert "log" in stats.provider_mode or stats.provider_mode == "dev_log (configured_provider=log)"


def test_invalid_smtp_fails_safely(db_session: Session, monkeypatch):
    from app.core.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "app_env", "production")
    update_provider_settings(
        db_session,
        updates={
            "provider": "smtp",
            "dev_mode": False,
            "email_enabled": True,
            "smtp_host": "",
            "smtp_from_email": "noreply@padeya.com",
            "smtp_username": "u",
            "smtp_password": "p",
        },
        actor_user_id=None,
        commit=True,
    )
    from app.email.config import production_email_ready

    ok, err = production_email_ready(settings, db=db_session)
    assert ok is False
    assert err and "SMTP host" in err


def test_admin_test_endpoint_uses_saved_settings(
    client: TestClient, db_session: Session, assign_role
):
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "test-smtp@example.com",
            "password": "Password123!",
            "full_name": "Test SMTP",
        },
    )
    assert reg.status_code == 201
    assign_role("test-smtp@example.com", "super_admin")
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    client.patch(
        "/api/v1/admin/email/settings",
        headers=headers,
        json={
            "provider": "log",
            "dev_mode": True,
            "email_enabled": True,
            "smtp_from_email": "noreply@padeya.com",
            "smtp_from_name": "Pàdéyá",
        },
    )
    res = client.post(
        "/api/v1/admin/email/settings/test",
        headers=headers,
        json={"test_recipient_email": "probe@example.com"},
    )
    assert res.status_code == 200, res.text
    assert res.json()["ok"] is True
    assert "smtp_password" not in res.json()

    active = get_active_provider_settings(db_session)
    assert active is not None
    assert active.last_test_status == "success"
