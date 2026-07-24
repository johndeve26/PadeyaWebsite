"""In-app + push notification system."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.encryption import decrypt_secret
from app.messaging.models import InAppNotification
from app.notifications.models import PushProviderSettings, PushSubscription
from app.notifications.service import notify_user, unread_count
from app.notifications.settings_service import generate_vapid_keypair, update_push_settings


def test_notify_user_creates_in_app(
    db_session: Session, client: TestClient, assign_role, monkeypatch
):
    captured: list = []

    def _capture(user_ids, payload):
        captured.append((list(user_ids), payload))

    monkeypatch.setattr(
        "app.messaging.ws_events.publish_to_users",
        _capture,
    )

    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "notif-user@example.com",
            "password": "Password123!",
            "full_name": "Notif User",
        },
    )
    assert reg.status_code == 201
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    from app.users.models import User

    user = db_session.scalar(select(User).where(User.email == "notif-user@example.com"))
    assert user is not None

    row = notify_user(
        db_session,
        user_id=user.id,
        kind="merch.confirmed",
        title="Merch ready",
        body="Your merch is ready for pickup on Pàdéyá.",
        link_path="/dashboard/orders",
        send_push=False,
        dedupe_key="test:merch:1",
    )
    db_session.commit()
    assert row is not None
    assert unread_count(db_session, user_id=user.id) >= 1
    assert any(p.get("type") == "notification.created" for _, p in captured)
    assert captured[-1][1]["notification"]["id"] == str(row.id)

    # Dedupe — no second row / no second emit
    before = len(captured)
    again = notify_user(
        db_session,
        user_id=user.id,
        kind="merch.confirmed",
        title="Merch ready",
        body="Your merch is ready for pickup on Pàdéyá.",
        link_path="/dashboard/orders",
        send_push=False,
        dedupe_key="test:merch:1",
    )
    assert again is None
    assert len(captured) == before

    listed = client.get("/api/v1/notifications", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1

    read = client.post(
        f"/api/v1/notifications/{row.id}/read",
        headers=headers,
    )
    assert read.status_code == 200
    assert read.json()["read_at"] is not None


def test_non_admin_cannot_access_push_settings(client: TestClient):
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "push-buyer@example.com",
            "password": "Password123!",
            "full_name": "Push Buyer",
        },
    )
    assert reg.status_code == 201
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    res = client.get("/api/v1/admin/push/settings", headers=headers)
    assert res.status_code == 403


def test_admin_vapid_settings_encrypted(
    client: TestClient, db_session: Session, assign_role
):
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "push-admin@example.com",
            "password": "Password123!",
            "full_name": "Push Admin",
        },
    )
    assert reg.status_code == 201
    assign_role("push-admin@example.com", "super_admin")
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    gen = client.patch(
        "/api/v1/admin/push/settings",
        headers=headers,
        json={
            "generate_vapid_keys": True,
            "push_enabled": True,
            "vapid_subject": "mailto:support@padeya.com",
        },
    )
    assert gen.status_code == 200, gen.text
    data = gen.json()
    assert data["push_enabled"] is True
    assert data["vapid_public_key"]
    assert data["vapid_private_configured"] is True
    assert "BEGIN PRIVATE" not in (data.get("vapid_public_key") or "")
    assert "vapid_private_key" not in data

    row = db_session.scalar(select(PushProviderSettings))
    assert row is not None
    assert row.vapid_private_key_encrypted
    plain = decrypt_secret(row.vapid_private_key_encrypted)
    assert "PRIVATE KEY" in plain or len(plain) > 20
    assert plain not in gen.text


def test_push_subscribe_requires_enabled_settings(
    client: TestClient, db_session: Session, assign_role
):
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "sub-user@example.com",
            "password": "Password123!",
            "full_name": "Sub User",
        },
    )
    assert reg.status_code == 201
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    blocked = client.post(
        "/api/v1/push/subscriptions",
        headers=headers,
        json={
            "endpoint": "https://push.example.com/sub/1",
            "p256dh": "abc",
            "auth": "def",
        },
    )
    assert blocked.status_code == 503

    assign_role("sub-user@example.com", "super_admin")
    admin_headers = headers
    client.patch(
        "/api/v1/admin/push/settings",
        headers=admin_headers,
        json={"generate_vapid_keys": True, "push_enabled": True},
    )

    # Re-register as normal user for subscribe (same user is now admin — fine)
    ok = client.post(
        "/api/v1/push/subscriptions",
        headers=headers,
        json={
            "endpoint": "https://push.example.com/sub/2",
            "p256dh": "p256dh-test-key-value",
            "auth": "auth-test-key-value",
        },
    )
    assert ok.status_code == 200, ok.text
    sub = db_session.scalar(select(PushSubscription))
    assert sub is not None
    assert "p256dh-test-key-value" not in sub.p256dh_encrypted
    assert decrypt_secret(sub.p256dh_encrypted) == "p256dh-test-key-value"


def test_generate_vapid_keypair_roundtrip():
    public, private = generate_vapid_keypair()
    assert public
    assert "PRIVATE" in private


def test_admin_provider_log_and_deliveries(
    client: TestClient, db_session: Session, assign_role
):
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "push-log-admin@example.com",
            "password": "Password123!",
            "full_name": "Push Log Admin",
        },
    )
    assert reg.status_code == 201
    assign_role("push-log-admin@example.com", "super_admin")
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    saved = client.patch(
        "/api/v1/admin/push/settings",
        headers=headers,
        json={
            "push_enabled": True,
            "provider": "log",
            "vapid_subject": "mailto:support@padeya.com",
        },
    )
    assert saved.status_code == 200, saved.text
    body = saved.json()
    assert body["provider"] == "log"
    assert body["push_enabled"] is True
    assert "vapid_private_key" not in body
    assert "vapid_private_key_encrypted" not in body

    # Active device required even in log mode
    no_device = client.post(
        "/api/v1/admin/push/settings/test",
        headers=headers,
        json={},
    )
    assert no_device.status_code == 400
    assert "no active push devices" in no_device.json()["detail"].lower()

    from app.core.encryption import encrypt_secret
    from app.notifications.models import PushSubscription
    from app.users.models import User

    admin_user = db_session.scalar(
        select(User).where(User.email == "push-log-admin@example.com")
    )
    assert admin_user is not None
    db_session.add(
        PushSubscription(
            user_id=admin_user.id,
            endpoint="https://push.example/admin-log-test",
            p256dh_encrypted=encrypt_secret("p256dh-test"),
            auth_encrypted=encrypt_secret("auth-test"),
            is_active=True,
            platform="test",
            device_label="pytest",
        )
    )
    db_session.commit()

    lookup = client.get(
        "/api/v1/admin/push/subscriptions/lookup",
        headers=headers,
        params={"email": "push-log-admin@example.com"},
    )
    assert lookup.status_code == 200
    assert lookup.json()["has_active_device"] is True
    assert lookup.json()["active_subscription_count"] >= 1

    test = client.post(
        "/api/v1/admin/push/settings/test",
        headers=headers,
        json={},
    )
    assert test.status_code == 200, test.text
    assert test.json()["provider"] == "log"
    assert test.json()["title"] == "Pàdéyá test notification"
    assert test.json()["body"] == "Push notifications are working."
    assert test.json()["action_url"] == "/dashboard/notifications"

    deliveries = client.get("/api/v1/admin/push/deliveries", headers=headers)
    assert deliveries.status_code == 200, deliveries.text
    payload = deliveries.json()
    assert payload["total"] >= 1
    assert payload["summary"].get("logged", 0) >= 1
    assert any(row["status"] == "logged" for row in payload["items"])
    # Never leak secrets in delivery errors
    for row in payload["items"]:
        err = row.get("error_message") or ""
        assert "PRIVATE KEY" not in err
        assert "BEGIN" not in err


def test_admin_can_disable_push_globally(
    client: TestClient, db_session: Session, assign_role
):
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "push-off-admin@example.com",
            "password": "Password123!",
            "full_name": "Push Off Admin",
        },
    )
    assert reg.status_code == 201
    assign_role("push-off-admin@example.com", "super_admin")
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    client.patch(
        "/api/v1/admin/push/settings",
        headers=headers,
        json={"push_enabled": True, "provider": "log"},
    )
    disabled = client.post(
        "/api/v1/admin/push/settings/disable",
        headers=headers,
    )
    assert disabled.status_code == 200
    assert disabled.json()["push_enabled"] is False


def test_multi_device_subscriptions_and_remove(
    client: TestClient, db_session: Session, assign_role
):
    from app.notifications.push import (
        FAILURE_DEACTIVATE_THRESHOLD,
        mark_subscription_failure,
    )

    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "multi-device@example.com",
            "password": "Password123!",
            "full_name": "Multi Device",
        },
    )
    assert reg.status_code == 201
    assign_role("multi-device@example.com", "super_admin")
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    client.patch(
        "/api/v1/admin/push/settings",
        headers=headers,
        json={"generate_vapid_keys": True, "push_enabled": True, "provider": "log"},
    )

    a = client.post(
        "/api/v1/push/subscriptions",
        headers=headers,
        json={
            "endpoint": "https://push.example.com/device-a",
            "p256dh": "p256dh-a",
            "auth": "auth-a",
            "platform": "macos",
            "device_label": "Mac browser",
        },
    )
    b = client.post(
        "/api/v1/push/subscriptions",
        headers=headers,
        json={
            "endpoint": "https://push.example.com/device-b",
            "p256dh": "p256dh-b",
            "auth": "auth-b",
            "platform": "android",
            "device_label": "Android browser",
        },
    )
    assert a.status_code == 200, a.text
    assert b.status_code == 200, b.text
    assert a.json()["is_active"] is True
    assert "p256dh" not in a.json()
    assert "auth" not in a.json()
    assert "endpoint" not in a.json()
    assert a.json().get("endpoint_hint")

    listed = client.get("/api/v1/push/subscriptions", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["total"] == 2

    remove = client.delete(
        f"/api/v1/push/subscriptions/{a.json()['id']}",
        headers=headers,
    )
    assert remove.status_code == 200
    assert remove.json()["revoked"] is True

    active = client.get("/api/v1/push/subscriptions", headers=headers)
    assert active.json()["total"] == 1
    assert active.json()["items"][0]["id"] == b.json()["id"]

    from uuid import UUID

    sub_b = db_session.get(PushSubscription, UUID(b.json()["id"]))
    assert sub_b is not None
    for _ in range(FAILURE_DEACTIVATE_THRESHOLD):
        mark_subscription_failure(sub_b)
    db_session.commit()
    db_session.refresh(sub_b)
    assert sub_b.is_active is False
    assert sub_b.revoked_at is not None
    assert sub_b.failure_count >= FAILURE_DEACTIVATE_THRESHOLD


def test_push_outbox_enqueue_dedupe_and_skip(
    client: TestClient, db_session: Session, assign_role
):
    from app.push.models import PushEvent
    from app.push.service import drain_push_outbox, enqueue_push
    from app.users.models import User

    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "push-outbox@example.com",
            "password": "Password123!",
            "full_name": "Outbox User",
        },
    )
    assert reg.status_code == 201
    user = db_session.scalar(
        select(User).where(User.email == "push-outbox@example.com")
    )
    assert user is not None

    # Push globally off → skipped
    skipped = enqueue_push(
        db_session,
        template="ticket.confirmed",
        recipient_user_id=user.id,
        context={"event_title": "Lagos Night", "title": "Your ticket is ready."},
        dedupe_key="push:order:test-1",
    )
    db_session.commit()
    assert skipped is not None
    assert skipped.status == "skipped"
    assert skipped.error_message == "push_disabled"

    assign_role("push-outbox@example.com", "super_admin")
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    client.patch(
        "/api/v1/admin/push/settings",
        headers=headers,
        json={"push_enabled": True, "provider": "log"},
    )

    # User master switch off → skipped
    from app.email.prefs import get_or_create_preferences

    prefs = get_or_create_preferences(db_session, user.id)
    prefs.push_enabled = False
    db_session.commit()

    no_opt = enqueue_push(
        db_session,
        template="ticket.confirmed",
        recipient_user_id=user.id,
        context={"event_title": "Lagos Night"},
        dedupe_key="push:order:test-2",
    )
    db_session.commit()
    assert no_opt is not None
    assert no_opt.status == "skipped"
    assert no_opt.error_message == "push_enabled_off"

    # Turn master back on for purchase-style send
    prefs.push_enabled = True
    db_session.commit()

    pending = enqueue_push(
        db_session,
        template="ticket.confirmed",
        recipient_user_id=user.id,
        context={"event_title": "Lagos Night", "title": "Your ticket is ready."},
        dedupe_key="push:order:test-3",
        force=False,
    )
    db_session.commit()
    assert pending is not None
    assert pending.status == "pending"

    again = enqueue_push(
        db_session,
        template="ticket.confirmed",
        recipient_user_id=user.id,
        context={"event_title": "Lagos Night"},
        dedupe_key="push:order:test-3",
    )
    assert again is not None
    assert again.id == pending.id

    stats = drain_push_outbox(db_session, limit=20, commit=True)
    assert stats.attempted >= 1
    db_session.refresh(pending)
    assert pending.status == "sent"

    events = client.get("/api/v1/admin/push/events", headers=headers)
    assert events.status_code == 200
    assert events.json()["total"] >= 1
    assert any(e["dedupe_key"] == "push:order:test-3" for e in events.json()["items"])
    # Ensure table exists for ORM
    assert db_session.scalar(select(func.count()).select_from(PushEvent)) >= 1




def test_push_preference_rules(db_session: Session, client: TestClient, monkeypatch):
    from app.email.prefs import get_or_create_preferences, update_preferences
    from app.notifications.prefs import push_preference_allows, push_pref_key_for_kind
    from app.push.models import PushEvent
    from app.users.models import User

    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "push-prefs@example.com",
            "password": "Password123!",
            "full_name": "Push Prefs",
        },
    )
    assert reg.status_code == 201
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    user = db_session.scalar(select(User).where(User.email == "push-prefs@example.com"))
    assert user is not None

    assert push_pref_key_for_kind("review.new") == "push_reviews"
    assert push_pref_key_for_kind("security.login") == "push_security"
    assert push_pref_key_for_kind("merch.post_event_drop") == "push_marketing"

    # Master off blocks everything including security
    prefs = get_or_create_preferences(db_session, user.id)
    prefs.push_enabled = False
    db_session.commit()
    ok, reason = push_preference_allows(
        db_session, user_id=user.id, kind="security.password_reset"
    )
    assert ok is False
    assert reason == "push_enabled_off"

    prefs.push_enabled = True
    prefs.push_marketing = False
    prefs.unsubscribed_marketing_at = None
    db_session.commit()

    # Security allowed even when marketing off
    ok, reason = push_preference_allows(
        db_session, user_id=user.id, kind="security.password_reset"
    )
    assert ok is True
    assert reason is None

    # Marketing category off is respected
    ok, reason = push_preference_allows(
        db_session, user_id=user.id, kind="marketing.promo"
    )
    assert ok is False
    assert reason == "pref_push_marketing_off"

    prefs.push_marketing = True
    db_session.commit()
    ok, _ = push_preference_allows(
        db_session, user_id=user.id, kind="marketing.promo"
    )
    assert ok is True

    # Ticket category opt-out respected
    prefs.push_ticket_updates = False
    db_session.commit()
    ok, reason = push_preference_allows(
        db_session, user_id=user.id, kind="ticket.confirmed"
    )
    assert ok is False
    assert reason == "pref_push_ticket_updates_off"

    # Reviews category
    prefs.push_reviews = False
    db_session.commit()
    ok, reason = push_preference_allows(
        db_session, user_id=user.id, kind="review.new"
    )
    assert ok is False
    assert reason == "pref_push_reviews_off"

    # Cannot disable push_security via API
    patched = client.patch(
        "/api/v1/push/preferences",
        headers=headers,
        json={"push_security": False, "push_enabled": True, "push_reviews": True},
    )
    assert patched.status_code == 200
    body = patched.json()
    assert body["push_security"] is True
    assert body["push_reviews"] is True
    assert body["push_enabled"] is True

    # Message rate limit (resolved via runtime settings, not raw Settings)
    monkeypatch.setattr(
        "app.runtime_settings.get_runtime_setting",
        lambda key, *, db=None, settings=None: (
            2 if key == "push_message_rate_limit_per_hour" else 12
        ),
    )
    prefs = get_or_create_preferences(db_session, user.id)
    prefs.push_enabled = True
    prefs.push_messages = True
    db_session.commit()

    for i in range(2):
        db_session.add(
            PushEvent(
                recipient_user_id=user.id,
                template="message.host_reply",
                title="New message",
                body="You have a new message on Pàdéyá.",
                status="sent",
            )
        )
    db_session.commit()

    ok, reason = push_preference_allows(
        db_session, user_id=user.id, kind="message.fan_reply"
    )
    assert ok is False
    assert reason == "message_push_rate_limited"

    # update_preferences keeps push_security true
    update_preferences(
        db_session, user_id=user.id, updates={"push_security": False}
    )
    db_session.commit()
    prefs = get_or_create_preferences(db_session, user.id)
    assert prefs.push_security is True
