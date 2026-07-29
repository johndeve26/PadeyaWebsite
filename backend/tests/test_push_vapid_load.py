"""VAPID private key loading — PEM vs raw (pywebpush compatibility)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.core.encryption import encrypt_secret
from app.notifications.models import PushSubscription
from app.notifications.settings_service import generate_vapid_keypair, update_push_settings
from app.push.provider import PushPayload, WebPushProvider
from app.push.vapid import is_pem_private_key, load_vapid_private
from app.users.models import User
from py_vapid import Vapid
from sqlalchemy import select
from sqlalchemy.orm import Session


def test_load_vapid_accepts_pem_and_raw():
    vapid = Vapid()
    vapid.generate_keys()
    pem = vapid.private_pem()
    if isinstance(pem, bytes):
        pem = pem.decode("utf-8")
    assert is_pem_private_key(pem)
    assert load_vapid_private(pem) is not None

    public, raw = generate_vapid_keypair()
    assert public
    assert not is_pem_private_key(raw)
    assert load_vapid_private(raw) is not None


def test_web_push_provider_accepts_stored_pem_private_key(
    db_session: Session, client, assign_role
):
    """Production historically stored PEM — must not hit deserialize errors."""
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "pem-vapid@example.com",
            "password": "Password123!",
            "full_name": "PEM Vapid",
        "gender": "prefer_not_to_say"},
    )
    assert reg.status_code == 201
    user = db_session.scalar(select(User).where(User.email == "pem-vapid@example.com"))
    assert user is not None
    assign_role("pem-vapid@example.com", "super_admin")

    vapid = Vapid()
    vapid.generate_keys()
    pem = vapid.private_pem()
    if isinstance(pem, bytes):
        pem = pem.decode("utf-8")
    from cryptography.hazmat.primitives import serialization
    import base64

    public = vapid.public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )
    public_b64 = base64.urlsafe_b64encode(public).decode("ascii").rstrip("=")

    update_push_settings(
        db_session,
        updates={
            "push_enabled": True,
            "provider": "web_push",
            "vapid_public_key": public_b64,
            "vapid_private_key": pem,
            "vapid_subject": "mailto:support@padeya.com",
        },
        actor_user_id=user.id,
        commit=True,
    )

    sub = PushSubscription(
        user_id=user.id,
        endpoint="https://fcm.googleapis.com/fcm/send/pem-test",
        p256dh_encrypted=encrypt_secret("p256dh-pem"),
        auth_encrypted=encrypt_secret("auth-pem"),
        is_active=True,
    )
    db_session.add(sub)
    db_session.commit()

    captured: list[dict] = []

    def fake_webpush(**kwargs):
        captured.append(kwargs)
        # Ensure we passed a Vapid instance (not a PEM string that from_string breaks).
        assert not isinstance(kwargs.get("vapid_private_key"), str)
        return MagicMock()

    with patch("pywebpush.webpush", fake_webpush):
        result = WebPushProvider().send(
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
    assert result.ok is True
    assert result.delivered == 1
    assert result.error != "vapid_key_invalid"
    assert len(captured) == 1
