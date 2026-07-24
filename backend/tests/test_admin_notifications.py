"""Admin notification system — settings, campaigns, orchestrator."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.admin_notifications.models import NotificationDelivery, NotificationSetting
from app.admin_notifications.orchestrator import dispatch_typed, send_notification
from app.admin_notifications.settings_service import (
    ensure_default_settings,
    get_or_create_setting,
    update_setting,
)
from app.users.models import User
from app.users.seed import seed_roles_and_permissions
from app.users.service import get_role_by_name


def _admin_headers(client: TestClient, db_session: Session, assign_role) -> dict:
    email = f"notif-admin-{uuid4().hex[:8]}@example.com"
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Password123!",
            "full_name": "Notif Admin",
        },
    )
    assert reg.status_code == 201, reg.text
    assign_role(email, "super_admin")
    return {"Authorization": f"Bearer {reg.json()['access_token']}"}, email


def test_admin_can_toggle_notification_type(
    client: TestClient, db_session: Session, assign_role
):
    headers, _ = _admin_headers(client, db_session, assign_role)
    listed = client.get("/api/v1/admin/notifications/settings", headers=headers)
    assert listed.status_code == 200, listed.text
    assert any(r["type_key"] == "vault.item_published" for r in listed.json())

    patched = client.put(
        "/api/v1/admin/notifications/settings/vault.item_published",
        headers=headers,
        json={"enabled": False, "channels": {"push": False}},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["enabled"] is False
    assert patched.json()["channels"]["push"] is False


def test_disabled_notification_does_not_send(db_session: Session, client: TestClient):
    seed_roles_and_permissions(db_session)
    role = get_role_by_name(db_session, "attendee")
    user = User(
        email=f"skip-{uuid4().hex[:8]}@example.com",
        password_hash="x",
        full_name="Skip",
        roles=[role] if role else [],
    )
    db_session.add(user)
    db_session.flush()
    ensure_default_settings(db_session)
    setting = get_or_create_setting(db_session, "merch.listing_published")
    setting.enabled = False
    db_session.commit()

    result = dispatch_typed(
        db_session,
        type_key="merch.listing_published",
        recipient_user_id=user.id,
        title="Should not send",
        body="Nope",
        dedupe_key=f"test-disabled:{user.id}",
    )
    assert result.get("error") == "type_disabled" or result.get("sent", 0) == 0


def test_custom_campaign_sends_to_selected_users(
    client: TestClient, db_session: Session, assign_role
):
    headers, _ = _admin_headers(client, db_session, assign_role)
    target_email = f"target-{uuid4().hex[:8]}@example.com"
    target = client.post(
        "/api/v1/auth/register",
        json={
            "email": target_email,
            "password": "Password123!",
            "full_name": "Target User",
        },
    )
    assert target.status_code == 201, target.text
    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {target.json()['access_token']}"},
    )
    assert me.status_code == 200, me.text
    target_id = me.json()["id"]

    created = client.post(
        "/api/v1/admin/notifications/campaigns",
        headers=headers,
        json={
            "title": "Hello fans",
            "body": "Custom admin notice",
            "channels": {"in_app": True, "push": False, "email": False},
            "audience_mode": "selected_users",
            "user_ids": [target_id],
            "cta_url": "/dashboard/notifications",
        },
    )
    assert created.status_code == 201, created.text
    campaign_id = created.json()["id"]

    sent = client.post(
        f"/api/v1/admin/notifications/campaigns/{campaign_id}/send",
        headers=headers,
    )
    assert sent.status_code == 200, sent.text
    assert sent.json()["campaign"]["status"] == "sent"

    deliveries = client.get(
        f"/api/v1/admin/notifications/campaigns/{campaign_id}/deliveries",
        headers=headers,
    )
    assert deliveries.status_code == 200
    assert len(deliveries.json()) >= 1


def test_critical_suspension_still_sends_when_prefs_off(
    db_session: Session, client: TestClient
):
    seed_roles_and_permissions(db_session)
    role = get_role_by_name(db_session, "attendee")
    user = User(
        email=f"crit-{uuid4().hex[:8]}@example.com",
        password_hash="x",
        full_name="Crit",
        roles=[role] if role else [],
    )
    db_session.add(user)
    db_session.flush()
    ensure_default_settings(db_session)
    from app.email.prefs import get_or_create_preferences

    prefs = get_or_create_preferences(db_session, user.id)
    prefs.email_marketing = False
    prefs.push_marketing = False
    db_session.commit()

    result = send_notification(
        db_session,
        type_key="account.suspended",
        recipient_user_ids=[user.id],
        title="Account suspended",
        body="Your account was suspended.",
        dedupe_key=f"suspend:{user.id}:{uuid4().hex[:6]}",
    )
    assert result["ok"] is True
    assert result["sent"] >= 1


def test_duplicate_notifications_deduped(db_session: Session):
    seed_roles_and_permissions(db_session)
    role = get_role_by_name(db_session, "attendee")
    user = User(
        email=f"dupe-{uuid4().hex[:8]}@example.com",
        password_hash="x",
        full_name="Dupe",
        roles=[role] if role else [],
    )
    db_session.add(user)
    db_session.flush()
    ensure_default_settings(db_session)
    key = f"dupe-key:{user.id}"
    first = send_notification(
        db_session,
        type_key="support.ticket_updated",
        recipient_user_ids=[user.id],
        title="Update",
        body="Support update",
        dedupe_key=key,
    )
    second = send_notification(
        db_session,
        type_key="support.ticket_updated",
        recipient_user_ids=[user.id],
        title="Update",
        body="Support update",
        dedupe_key=key,
    )
    assert first["sent"] >= 1
    # Second pass should skip duplicate in-app/push/email
    assert second["sent"] == 0 or second["skipped"] >= 1


def test_unauthorized_cannot_send_notifications(client: TestClient):
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"fan-{uuid4().hex[:8]}@example.com",
            "password": "Password123!",
            "full_name": "Fan",
        },
    )
    assert reg.status_code == 201
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    res = client.get("/api/v1/admin/notifications/settings", headers=headers)
    assert res.status_code == 403

    create = client.post(
        "/api/v1/admin/notifications/campaigns",
        headers=headers,
        json={"title": "Nope", "body": "Nope", "user_ids": []},
    )
    assert create.status_code == 403


def test_marketing_respects_user_prefs(db_session: Session):
    seed_roles_and_permissions(db_session)
    role = get_role_by_name(db_session, "attendee")
    user = User(
        email=f"mkt-{uuid4().hex[:8]}@example.com",
        password_hash="x",
        full_name="Mkt",
        roles=[role] if role else [],
    )
    db_session.add(user)
    db_session.flush()
    ensure_default_settings(db_session)
    from app.email.prefs import get_or_create_preferences, update_preferences

    update_preferences(
        db_session, user_id=user.id, updates={"email_marketing": False, "push_enabled": True}
    )
    setting = get_or_create_setting(db_session, "vault.item_published")
    setting.enabled = True
    setting.channel_in_app = True
    setting.channel_push = False
    setting.channel_email = True
    setting.respect_user_prefs = True
    setting.classification = "marketing"
    setting.audience = "context_recipients"
    db_session.commit()

    result = send_notification(
        db_session,
        type_key="vault.item_published",
        recipient_user_ids=[user.id],
        title="New vault",
        body="Drop live",
        dedupe_key=f"mkt:{user.id}",
    )
    # in-app still ok; email should skip marketing pref
    emails = db_session.query(NotificationDelivery).filter_by(
        recipient_user_id=user.id, channel="email", type_key="vault.item_published"
    ).all()
    assert not any(d.status == "sent" for d in emails)
    assert result["ok"] is True


def test_delivery_and_audit_recorded(
    client: TestClient, db_session: Session, assign_role
):
    headers, _ = _admin_headers(client, db_session, assign_role)
    ensure_default_settings(db_session)
    db_session.commit()
    before = db_session.query(NotificationSetting).count()
    assert before >= 1

    patched = client.put(
        "/api/v1/admin/notifications/settings/message.new",
        headers=headers,
        json={"cooldown_seconds": 60},
    )
    assert patched.status_code == 200

    from app.admin_notifications.models import NotificationAuditLog

    audits = (
        db_session.query(NotificationAuditLog)
        .filter_by(action="notification.setting_changed")
        .all()
    )
    assert len(audits) >= 1
