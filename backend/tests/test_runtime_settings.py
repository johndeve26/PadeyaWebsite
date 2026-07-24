"""Section 16 — Admin Runtime Settings (allowlist, secrets, audit, resolve)."""

from __future__ import annotations

import json
import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import AuditLog
from app.core.config import get_settings
from app.core.security import hash_password
from app.runtime_settings.models import RuntimeSetting
from app.runtime_settings.registry import is_class_a_key, validate_value, get_definition
from app.runtime_settings.service import (
    get_runtime_setting,
    invalidate_runtime_settings_cache,
    runtime_settings_service,
)
from app.users.models import Permission, Role, User
from app.users.service import get_role_by_name


BASE = "/api/v1/admin/settings/runtime"


def _register(client: TestClient, email: str) -> dict[str, str]:
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Password123!",
            "full_name": "Runtime Admin",
        },
    )
    assert res.status_code == 201, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def _grant_perms(db: Session, user: User, *codes: str) -> None:
    role = Role(name=f"tmp-rs-{uuid.uuid4().hex[:8]}", description="test")
    for code in codes:
        perm = db.scalar(select(Permission).where(Permission.code == code))
        assert perm is not None, f"missing permission {code}"
        role.permissions.append(perm)
    db.add(role)
    user.roles.append(role)
    db.commit()


def _super_headers(client: TestClient, db: Session, assign_role, email: str) -> dict[str, str]:
    headers = _register(client, email)
    assign_role(email, "super_admin")
    return headers


def test_boot_critical_envs_not_editable(
    client: TestClient, db_session: Session, assign_role
):
    headers = _super_headers(
        client, db_session, assign_role, "rs-class-a@example.com"
    )
    for key in ("secret_key", "database_url", "app_env", "ai_api_key"):
        assert is_class_a_key(key)
        res = client.put(
            f"{BASE}/runtime/{key}",
            headers=headers,
            json={"value": "x"},
        )
        # category mismatch or class A → 403/404
        assert res.status_code in {403, 404}, (key, res.text)

    res = client.put(
        f"{BASE}/security-runtime/secret_key",
        headers=headers,
        json={"value": "should-fail"},
    )
    assert res.status_code == 403
    assert "not editable" in res.json()["detail"].lower() or "boot-critical" in res.json()[
        "detail"
    ].lower()


def test_runtime_setting_can_be_saved(
    client: TestClient, db_session: Session, assign_role
):
    headers = _super_headers(client, db_session, assign_role, "rs-save@example.com")
    res = client.put(
        f"{BASE}/email/email_worker_poll_seconds",
        headers=headers,
        json={"value": 42},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["value"] == 42
    assert body["source"] == "db"
    assert body.get("value") != "secret"

    row = db_session.scalar(
        select(RuntimeSetting).where(RuntimeSetting.key == "email_worker_poll_seconds")
    )
    assert row is not None
    assert row.value_plain == 42


def test_runtime_secret_replaced_and_never_returned_raw(
    client: TestClient, db_session: Session, assign_role
):
    headers = _super_headers(client, db_session, assign_role, "rs-secret@example.com")
    secret = "smtp-super-secret-password-9911"
    res = client.put(
        f"{BASE}/email/smtp_password",
        headers=headers,
        json={"value": secret},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["is_secret"] is True
    assert body["value"] is None
    assert secret not in json.dumps(body)
    assert body.get("configured") is True
    assert body.get("masked_value")
    assert "9911" in (body.get("last_four") or body.get("masked_value") or "")

    listed = client.get(f"{BASE}/email", headers=headers)
    assert listed.status_code == 200
    assert secret not in listed.text


def test_clear_override_falls_back_to_env(
    client: TestClient, db_session: Session, assign_role, monkeypatch
):
    headers = _super_headers(client, db_session, assign_role, "rs-clear@example.com")
    settings = get_settings()
    monkeypatch.setattr(settings, "email_worker_batch_size", 17)
    monkeypatch.setenv("EMAIL_WORKER_BATCH_SIZE", "17")

    put = client.put(
        f"{BASE}/email/email_worker_batch_size",
        headers=headers,
        json={"value": 99},
    )
    assert put.status_code == 200
    assert put.json()["source"] == "db"
    assert get_runtime_setting("email_worker_batch_size", db=db_session) == 99

    cleared = client.delete(
        f"{BASE}/email/email_worker_batch_size/override",
        headers=headers,
    )
    assert cleared.status_code == 200, cleared.text
    invalidate_runtime_settings_cache()
    resolved = get_runtime_setting("email_worker_batch_size", db=db_session)
    assert resolved == 17
    assert cleared.json()["source"] in {"env", "default"}


def test_missing_optional_setting_does_not_break_startup(db_session: Session):
    """Resolver must degrade safely when key/table is empty."""
    invalidate_runtime_settings_cache()
    val = get_runtime_setting("email_queue_enabled", db=db_session)
    assert val is not None
    missing = get_runtime_setting("totally_unknown_optional_key", db=db_session)
    assert missing is None
    # App import path already succeeded via TestClient fixture.


def test_provider_resolver_uses_db_override_before_env(
    db_session: Session, monkeypatch
):
    settings = get_settings()
    monkeypatch.setattr(settings, "push_worker_poll_seconds", 20)
    monkeypatch.setenv("PUSH_WORKER_POLL_SECONDS", "20")
    assert (
        runtime_settings_service.get_runtime_setting(
            "push_worker_poll_seconds", db=db_session, settings=settings
        )
        == 20
    )

    runtime_settings_service.upsert(
        db_session,
        category="push",
        key="push_worker_poll_seconds",
        value=33,
        actor_user_id=None,
        commit=True,
    )
    invalidate_runtime_settings_cache()
    assert (
        runtime_settings_service.get_runtime_setting(
            "push_worker_poll_seconds", db=db_session, settings=settings
        )
        == 33
    )
    assert (
        runtime_settings_service.resolve_source(
            "push_worker_poll_seconds", db=db_session, settings=settings
        )
        == "db"
    )


def test_admin_without_permission_gets_403(client: TestClient, db_session: Session):
    headers = _register(client, "rs-noperm@example.com")
    # buyer only — no settings perms
    res = client.get(BASE, headers=headers)
    assert res.status_code == 403

    res = client.put(
        f"{BASE}/email/email_worker_poll_seconds",
        headers=headers,
        json={"value": 10},
    )
    assert res.status_code == 403


def test_edit_secret_requires_edit_secrets_permission(
    client: TestClient, db_session: Session
):
    headers = _register(client, "rs-edit-runtime-only@example.com")
    user = db_session.query(User).filter(
        User.email == "rs-edit-runtime-only@example.com"
    ).one()
    _grant_perms(
        db_session,
        user,
        "admin.settings.view",
        "admin.settings.edit_runtime",
        # intentionally omit edit_secrets
    )
    res = client.put(
        f"{BASE}/email/smtp_password",
        headers=headers,
        json={"value": "should-be-forbidden"},
    )
    assert res.status_code == 403
    assert "edit_secrets" in res.json()["detail"]


def test_audit_log_created_on_update_without_secret(
    client: TestClient, db_session: Session, assign_role
):
    headers = _super_headers(client, db_session, assign_role, "rs-audit@example.com")
    secret = "audit-must-not-store-this-password"
    res = client.put(
        f"{BASE}/email/smtp_password",
        headers=headers,
        json={"secret_value": secret},
    )
    assert res.status_code == 200, res.text

    logs = db_session.scalars(
        select(AuditLog)
        .where(AuditLog.action == "runtime_secret_replaced")
        .order_by(AuditLog.created_at.desc())
    ).all()
    assert logs
    blob = json.dumps(logs[0].details or {})
    assert secret not in blob
    assert "smtp-super" not in blob


def test_validation_rejects_invalid_smtp_port_url_boolean(
    client: TestClient, db_session: Session, assign_role
):
    headers = _super_headers(client, db_session, assign_role, "rs-validate@example.com")

    port = client.put(
        f"{BASE}/email/smtp_port",
        headers=headers,
        json={"value": 99999},
    )
    assert port.status_code == 400
    assert "65535" in port.json()["detail"] or ">=" in port.json()["detail"] or "<=" in port.json()[
        "detail"
    ]

    url = client.put(
        f"{BASE}/ai/ai_base_url",
        headers=headers,
        json={"value": "not-a-url"},
    )
    assert url.status_code == 400
    assert "http" in url.json()["detail"].lower()

    bad_bool = client.put(
        f"{BASE}/email/email_queue_enabled",
        headers=headers,
        json={"value": "maybe"},
    )
    assert bad_bool.status_code == 400
    assert "boolean" in bad_bool.json()["detail"].lower()

    # Unit-level validators
    defn_port = get_definition("smtp_port")
    assert defn_port is not None
    with pytest.raises(ValueError):
        validate_value(defn_port, 0)
    defn_url = get_definition("paystack_base_url")
    assert defn_url is not None
    with pytest.raises(ValueError):
        validate_value(defn_url, "ftp://bad")
    defn_bool = get_definition("email_queue_enabled")
    assert defn_bool is not None
    with pytest.raises(ValueError):
        validate_value(defn_bool, "not-bool")


def test_test_email_action_does_not_log_smtp_password(
    client: TestClient, db_session: Session, assign_role
):
    headers = _super_headers(client, db_session, assign_role, "rs-test-email@example.com")
    secret = "smtp-password-should-never-appear-in-audit"
    client.put(
        f"{BASE}/email/smtp_password",
        headers=headers,
        json={"value": secret},
    )
    res = client.post(f"{BASE}/email/test", headers=headers, json={})
    assert res.status_code == 200, res.text
    assert secret not in res.text
    assert "smtp_password" not in res.text or res.json().get("ok") is not None

    logs = db_session.scalars(
        select(AuditLog).where(AuditLog.action == "runtime_setting_tested")
    ).all()
    assert logs
    for log in logs:
        blob = json.dumps(log.details or {})
        assert secret not in blob
        assert "smtp-password-should-never" not in blob


def test_test_ai_action_does_not_log_api_key(
    client: TestClient, db_session: Session, assign_role, monkeypatch
):
    headers = _super_headers(client, db_session, assign_role, "rs-test-ai@example.com")
    settings = get_settings()
    api_key = "sk_test_ai_key_must_not_leak_xyz"
    monkeypatch.setattr(settings, "ai_enabled", True)
    monkeypatch.setattr(settings, "ai_provider", "template")
    monkeypatch.setattr(settings, "ai_api_key", api_key)

    res = client.post(f"{BASE}/ai/test", headers=headers, json={})
    assert res.status_code == 200, res.text
    assert api_key not in res.text
    body = res.json()
    details = body.get("details") or {}
    assert api_key not in json.dumps(details)
    assert details.get("ai_api_key_configured") in {True, False, None} or "ai_api_key" not in str(
        details.get("ai_api_key", "")
    )

    logs = db_session.scalars(
        select(AuditLog).where(AuditLog.action == "runtime_setting_tested")
    ).all()
    for log in logs:
        assert api_key not in json.dumps(log.details or {})


def test_dashboard_and_status_never_leak_class_a(
    client: TestClient, db_session: Session, assign_role
):
    headers = _super_headers(client, db_session, assign_role, "rs-dash@example.com")
    dash = client.get(BASE, headers=headers)
    assert dash.status_code == 200, dash.text
    data = dash.json()
    assert isinstance(data["categories"], list)
    assert data["categories"]
    assert isinstance(data["categories"][0], dict)
    assert "category" in data["categories"][0]
    text = dash.text
    assert get_settings().secret_key not in text
    assert "change-me-in-production" not in text or "secret_key" not in text.lower()

    status = client.get(f"{BASE}/status", headers=headers)
    assert status.status_code == 200
    st = status.json()
    assert "environment" in st
    assert "configured" in st
    assert isinstance(st["configured"].get("ai_api_key"), bool) or "ai_api_key" in st[
        "configured"
    ]
    assert get_settings().secret_key not in status.text


def test_storage_attachment_limits_admin_uses_mb(
    client: TestClient, db_session: Session, assign_role
):
    """Admin API exposes/edits attachment limits in MB; DB stores bytes."""
    headers = _super_headers(client, db_session, assign_role, "rs-mb@example.com")
    cat = client.get(f"{BASE}/storage", headers=headers)
    assert cat.status_code == 200, cat.text
    by_key = {s["key"]: s for s in cat.json()["settings"]}
    image = by_key["messaging_attachment_max_image_bytes"]
    assert image["admin_unit"] == "mb"
    assert image["value"] == 5  # default 5 MiB
    assert image["label"].endswith("(MB)")

    put = client.put(
        f"{BASE}/storage/messaging_attachment_max_image_bytes",
        headers=headers,
        json={"value": 8},
    )
    assert put.status_code == 200, put.text
    assert put.json()["value"] == 8

    row = db_session.scalar(
        select(RuntimeSetting).where(
            RuntimeSetting.key == "messaging_attachment_max_image_bytes"
        )
    )
    assert row is not None
    assert int(row.value_plain) == 8 * 1024 * 1024

    resolved = get_runtime_setting(
        "messaging_attachment_max_image_bytes", db=db_session
    )
    assert resolved == 8 * 1024 * 1024


def test_paystack_keys_editable_in_admin_masked(
    client: TestClient, db_session: Session, assign_role
):
    """Paystack secret/webhook/public can be set from Payment integration admin."""
    headers = _super_headers(client, db_session, assign_role, "rs-paystack@example.com")
    secret = "sk_test_admin_runtime_secret_key_xyz"
    put = client.put(
        f"{BASE}/payments/paystack_secret_key",
        headers=headers,
        json={"value": secret},
    )
    assert put.status_code == 200, put.text
    body = put.json()
    assert body["is_secret"] is True
    assert body["configured"] is True
    assert body["value"] is None
    assert secret not in put.text
    masked = body.get("masked_value") or ""
    assert "Configured ·" in masked
    assert "sk_t" in masked
    assert masked.count("…") == 1

    pub = client.put(
        f"{BASE}/payments/paystack_public_key",
        headers=headers,
        json={"value": "pk_test_admin_public_key"},
    )
    assert pub.status_code == 200, pub.text
    pub_body = pub.json()
    assert pub_body["value"] is None
    assert pub_body.get("fingerprint_display") is True
    assert "pk_t" in (pub_body.get("masked_value") or "")

    from app.payments.config import paystack_runtime

    cfg = paystack_runtime(db_session)
    assert cfg.secret_key == secret
    assert cfg.public_key == "pk_test_admin_public_key"
    assert cfg.mode == "test"
    assert secret not in client.get(f"{BASE}/payments", headers=headers).text


def test_paystack_mode_selects_live_keys(
    client: TestClient, db_session: Session, assign_role
):
    headers = _super_headers(client, db_session, assign_role, "rs-paystack-live@example.com")
    client.put(
        f"{BASE}/payments/paystack_secret_key",
        headers=headers,
        json={"value": "sk_test_only_for_test_mode"},
    )
    client.put(
        f"{BASE}/payments/paystack_public_key",
        headers=headers,
        json={"value": "pk_test_only_for_test_mode"},
    )
    client.put(
        f"{BASE}/payments/paystack_live_secret_key",
        headers=headers,
        json={"value": "sk_live_runtime_test_secret_key"},
    )
    client.put(
        f"{BASE}/payments/paystack_live_public_key",
        headers=headers,
        json={"value": "pk_live_runtime_test_public_key"},
    )
    mode = client.put(
        f"{BASE}/payments/paystack_mode",
        headers=headers,
        json={"value": "live"},
    )
    assert mode.status_code == 200, mode.text

    from app.payments.config import paystack_runtime

    cfg = paystack_runtime(db_session)
    assert cfg.mode == "live"
    assert cfg.secret_key == "sk_live_runtime_test_secret_key"
    assert cfg.public_key == "pk_live_runtime_test_public_key"
