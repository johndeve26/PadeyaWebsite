"""Checklist coverage for push subscriptions, outbox, privacy, admin, worker."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.encryption import decrypt_secret, encrypt_secret
from app.email.prefs import get_or_create_preferences
from app.notifications.models import PushProviderSettings, PushSubscription
from app.notifications.push import mark_subscription_failure
from app.notifications.settings_service import update_push_settings
from app.push.models import PushEvent
from app.push.provider import PushPayload, WebPushProvider
from app.push.service import drain_push_outbox, enqueue_push
from app.users.models import User


def _enable_push(
    db: Session,
    *,
    provider: str = "log",
    actor_user_id=None,
) -> PushProviderSettings:
    return update_push_settings(
        db,
        updates={
            "push_enabled": True,
            "provider": provider,
            "generate_vapid_keys": True,
            "vapid_subject": "mailto:support@padeya.com",
        },
        actor_user_id=actor_user_id,
        commit=True,
    )


def test_non_auth_user_cannot_register_push(client: TestClient):
    res = client.post(
        "/api/v1/push/subscriptions",
        json={
            "endpoint": "https://push.example.com/anon",
            "p256dh": "p256dh",
            "auth": "auth",
        },
    )
    assert res.status_code in {401, 403}


def test_user_can_register_and_unregister_push_subscription(
    client: TestClient, db_session: Session, assign_role
):
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "checklist-sub@example.com",
            "password": "Password123!",
            "full_name": "Checklist Sub",
        },
    )
    assert reg.status_code == 201
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    assign_role("checklist-sub@example.com", "super_admin")
    _enable_push(db_session)

    created = client.post(
        "/api/v1/push/subscriptions",
        headers=headers,
        json={
            "endpoint": "https://push.example.com/checklist-sub",
            "p256dh": "p256dh-checklist",
            "auth": "auth-checklist",
            "device_label": "pytest",
        },
    )
    assert created.status_code == 200, created.text
    sub_id = created.json()["id"]
    assert created.json()["is_active"] is True

    listed = client.get("/api/v1/push/subscriptions", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1

    removed = client.delete(
        f"/api/v1/push/subscriptions/{sub_id}",
        headers=headers,
    )
    assert removed.status_code == 200
    assert removed.json()["revoked"] is True

    active = client.get("/api/v1/push/subscriptions", headers=headers)
    assert all(item["id"] != sub_id for item in active.json()["items"])


def test_push_enqueued_for_ticket_confirmed_after_payment(
    client: TestClient, db_session: Session, assign_role
):
    from app.email.models import EmailEvent
    from app.payments.paystack import sign_body_for_tests
    from tests.test_email_system import _seed_event

    event, ticket_type = _seed_event(db_session)
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "push-ticket-buyer@example.com",
            "password": "securepass1",
            "full_name": "Push Ticket Buyer",
        },
    )
    assert reg.status_code == 201
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    user = db_session.scalar(
        select(User).where(User.email == "push-ticket-buyer@example.com")
    )
    assert user is not None

    assign_role("push-ticket-buyer@example.com", "super_admin")
    _enable_push(db_session, actor_user_id=user.id)
    prefs = get_or_create_preferences(db_session, user.id)
    prefs.push_enabled = True
    prefs.push_ticket_updates = True
    db_session.commit()

    order = client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "event_id": str(event.id),
            "items": [{"ticket_type_id": str(ticket_type.id), "quantity": 1}],
        },
    ).json()

    # Before payment verification — no ticket push / confirm email yet
    before_push = db_session.scalar(
        select(PushEvent).where(
            PushEvent.recipient_user_id == user.id,
            PushEvent.template.in_(("ticket_confirmed", "ticket.confirmed")),
        )
    )
    assert before_push is None
    before_email = db_session.scalar(
        select(EmailEvent).where(EmailEvent.template == "ticket_confirmed")
    )
    assert before_email is None

    with patch(
        "app.payments.service.initialize_transaction",
        return_value={
            "authorization_url": "https://checkout.paystack.com/test",
            "access_code": "ACCESS",
            "reference": order["reference"],
        },
    ):
        client.post(f"/api/v1/payments/checkout/{order['id']}", headers=headers)

    payload = {
        "event": "charge.success",
        "data": {
            "reference": order["reference"],
            "status": "success",
            "amount": 500000,
            "currency": "NGN",
            "id": 999101,
        },
    }
    body = json.dumps(payload).encode()
    sig = sign_body_for_tests(body)
    wh = client.post(
        "/api/v1/payments/webhooks/paystack",
        content=body,
        headers={"x-paystack-signature": sig, "content-type": "application/json"},
    )
    assert wh.status_code == 200, wh.text

    push_row = db_session.scalar(
        select(PushEvent)
        .where(
            PushEvent.recipient_user_id == user.id,
            PushEvent.template.in_(("ticket_confirmed", "ticket.confirmed")),
        )
        .order_by(PushEvent.created_at.desc())
    )
    assert push_row is not None
    assert push_row.status in {"pending", "sent", "skipped"}

    email_row = db_session.scalar(
        select(EmailEvent).where(EmailEvent.template == "ticket_confirmed")
    )
    assert email_row is not None


def test_marketing_push_respects_opt_in(db_session: Session, client: TestClient):
    from app.notifications.prefs import push_preference_allows

    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "mkt-push@example.com",
            "password": "Password123!",
            "full_name": "Mkt Push",
        },
    )
    assert reg.status_code == 201
    user = db_session.scalar(select(User).where(User.email == "mkt-push@example.com"))
    assert user is not None
    prefs = get_or_create_preferences(db_session, user.id)
    prefs.push_enabled = True
    prefs.push_marketing = False
    db_session.commit()

    ok, reason = push_preference_allows(
        db_session, user_id=user.id, kind="merch.post_event_drop"
    )
    assert ok is False
    assert reason == "pref_push_marketing_off"

    prefs.push_marketing = True
    db_session.commit()
    ok, _ = push_preference_allows(
        db_session, user_id=user.id, kind="merch.post_event_drop"
    )
    assert ok is True


def test_disabled_push_preference_skips_send(db_session: Session, client: TestClient):
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "pref-off@example.com",
            "password": "Password123!",
            "full_name": "Pref Off",
        },
    )
    assert reg.status_code == 201
    user = db_session.scalar(select(User).where(User.email == "pref-off@example.com"))
    assert user is not None
    _enable_push(db_session)
    prefs = get_or_create_preferences(db_session, user.id)
    prefs.push_enabled = False
    db_session.commit()

    event = enqueue_push(
        db_session,
        template="ticket_confirmed",
        recipient_user_id=user.id,
        context={"event_title": "Lagos Night"},
        dedupe_key=f"checklist:pref-off:{uuid4()}",
    )
    db_session.commit()
    assert event is not None
    assert event.status == "skipped"
    assert event.error_message == "push_enabled_off"


def test_web_push_provider_sends_with_active_subscription(
    db_session: Session, client: TestClient, assign_role
):
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "webpush-user@example.com",
            "password": "Password123!",
            "full_name": "WebPush User",
        },
    )
    assert reg.status_code == 201
    user = db_session.scalar(
        select(User).where(User.email == "webpush-user@example.com")
    )
    assert user is not None
    assign_role("webpush-user@example.com", "super_admin")
    _enable_push(db_session, provider="web_push", actor_user_id=user.id)

    sub = PushSubscription(
        user_id=user.id,
        endpoint="https://fcm.googleapis.com/fcm/send/checklist",
        p256dh_encrypted=encrypt_secret("p256dh-web"),
        auth_encrypted=encrypt_secret("auth-web"),
        is_active=True,
    )
    db_session.add(sub)
    db_session.commit()

    captured: list[dict] = []

    def fake_webpush(**kwargs):
        captured.append(kwargs)
        return MagicMock()

    with patch("pywebpush.webpush", fake_webpush):
        provider = WebPushProvider()
        result = provider.send(
            db_session,
            user_id=user.id,
            subscriptions=[sub],
            payload=PushPayload(
                title="Pàdéyá test notification",
                body="Push notifications are working.",
                url="/dashboard/notifications",
                kind="admin_push_test",
            ),
        )
    db_session.commit()
    assert result.ok is True
    assert result.delivered == 1
    assert len(captured) == 1
    assert "vapid_public_key" not in captured[0]
    assert "vapid_private_key" in captured[0]
    assert captured[0].get("vapid_claims", {}).get("sub")
    wire = json.loads(captured[0]["data"])
    assert set(wire.keys()) <= {
        "title",
        "body",
        "action_url",
        "notification_id",
        "tag",
        "timestamp",
        "icon",
        "badge",
    }
    assert "pickup_code" not in wire
    assert "email" not in wire


def test_expired_subscription_is_deactivated(db_session: Session, client: TestClient):
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "expire-sub@example.com",
            "password": "Password123!",
            "full_name": "Expire Sub",
        },
    )
    assert reg.status_code == 201
    user = db_session.scalar(select(User).where(User.email == "expire-sub@example.com"))
    assert user is not None
    sub = PushSubscription(
        user_id=user.id,
        endpoint="https://push.example.com/expired",
        p256dh_encrypted=encrypt_secret("p256dh"),
        auth_encrypted=encrypt_secret("auth"),
        is_active=True,
    )
    db_session.add(sub)
    db_session.commit()

    mark_subscription_failure(sub, status_code=410)
    db_session.commit()
    db_session.refresh(sub)
    assert sub.is_active is False
    assert sub.revoked_at is not None


def test_push_payload_excludes_private_fields():
    from app.push.privacy import sanitize_push_context
    from app.push.provider import PushPayload

    dirty = sanitize_push_context(
        {
            "event_title": "Night",
            "pickup_code": "SECRET99",
            "shipping_address": "12 Hidden",
            "email": "x@y.com",
            "message_body": "private",
            "action_url": "/dashboard/tickets",
        }
    )
    assert "pickup_code" not in dirty
    assert "shipping_address" not in dirty
    assert "email" not in dirty
    assert "message_body" not in dirty

    data = json.loads(
        PushPayload(
            title="Ticket confirmed",
            body="Ready on Pàdéyá.",
            url="/dashboard/tickets",
            kind="ticket_confirmed",
        ).to_json()
    )
    assert "pickup_code" not in data
    assert "body_full" not in data


def test_admin_can_send_test_push_non_admin_cannot(
    client: TestClient, db_session: Session, assign_role
):
    buyer = client.post(
        "/api/v1/auth/register",
        json={
            "email": "no-admin-push@example.com",
            "password": "Password123!",
            "full_name": "No Admin",
        },
    )
    assert buyer.status_code == 201
    buyer_h = {"Authorization": f"Bearer {buyer.json()['access_token']}"}
    assert client.get("/api/v1/admin/push/settings", headers=buyer_h).status_code == 403
    assert (
        client.post("/api/v1/admin/push/settings/test", headers=buyer_h, json={}).status_code
        == 403
    )

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "email": "yes-admin-push@example.com",
            "password": "Password123!",
            "full_name": "Yes Admin",
        },
    )
    assert admin.status_code == 201
    assign_role("yes-admin-push@example.com", "super_admin")
    admin_h = {"Authorization": f"Bearer {admin.json()['access_token']}"}
    user = db_session.scalar(
        select(User).where(User.email == "yes-admin-push@example.com")
    )
    assert user is not None
    _enable_push(db_session, provider="log", actor_user_id=user.id)
    db_session.add(
        PushSubscription(
            user_id=user.id,
            endpoint="https://push.example.com/admin-test-device",
            p256dh_encrypted=encrypt_secret("p256dh"),
            auth_encrypted=encrypt_secret("auth"),
            is_active=True,
        )
    )
    db_session.commit()

    test = client.post("/api/v1/admin/push/settings/test", headers=admin_h, json={})
    assert test.status_code == 200, test.text
    assert test.json()["title"] == "Pàdéyá test notification"
    assert test.json()["ok"] is True


def test_vapid_private_key_encrypted(
    client: TestClient, db_session: Session, assign_role
):
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "vapid-check@example.com",
            "password": "Password123!",
            "full_name": "Vapid Check",
        },
    )
    assert reg.status_code == 201
    assign_role("vapid-check@example.com", "super_admin")
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    saved = client.patch(
        "/api/v1/admin/push/settings",
        headers=headers,
        json={"generate_vapid_keys": True, "push_enabled": True},
    )
    assert saved.status_code == 200
    assert "vapid_private_key" not in saved.json()
    assert "vapid_private_key_encrypted" not in saved.json()
    row = db_session.scalar(select(PushProviderSettings).where(PushProviderSettings.is_active))
    assert row is not None
    assert row.vapid_private_key_encrypted
    plain = decrypt_secret(row.vapid_private_key_encrypted)
    assert plain
    assert plain not in saved.text


def test_worker_processes_pending_events(db_session: Session, client: TestClient):
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "worker-drain@example.com",
            "password": "Password123!",
            "full_name": "Worker Drain",
        },
    )
    assert reg.status_code == 201
    user = db_session.scalar(
        select(User).where(User.email == "worker-drain@example.com")
    )
    assert user is not None
    _enable_push(db_session, provider="log")
    prefs = get_or_create_preferences(db_session, user.id)
    prefs.push_enabled = True
    prefs.push_ticket_updates = True
    db_session.add(
        PushSubscription(
            user_id=user.id,
            endpoint="https://push.example.com/worker-drain",
            p256dh_encrypted=encrypt_secret("p256dh"),
            auth_encrypted=encrypt_secret("auth"),
            is_active=True,
        )
    )
    db_session.commit()

    event = enqueue_push(
        db_session,
        template="ticket_confirmed",
        recipient_user_id=user.id,
        context={"event_title": "Worker Night"},
        dedupe_key=f"checklist:worker:{uuid4()}",
    )
    db_session.commit()
    assert event is not None
    assert event.status == "pending"

    stats = drain_push_outbox(db_session, limit=20, commit=True)
    assert stats.attempted >= 1
    db_session.refresh(event)
    assert event.status == "sent"
