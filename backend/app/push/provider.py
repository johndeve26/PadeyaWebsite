"""Push providers — Web Push (pywebpush) and log (safe default)."""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.encryption import decrypt_secret
from app.notifications.models import PushDeliveryEvent, PushSubscription
from app.notifications.push import mark_subscription_failure, mark_subscription_success
from app.notifications.settings_service import get_active_push_settings
from app.push.privacy import sanitize_delivery_error

logger = logging.getLogger("padeya.push.provider")


@dataclass
class PushPayload:
    """Safe browser payload — never include chat bodies, attachments, venues, or payments."""

    title: str
    body: str
    url: str
    kind: str
    notification_id: str | None = None
    icon: str | None = None
    badge: str | None = None
    tag: str | None = None
    timestamp_ms: int | None = None

    def to_json(self) -> str:
        # Whitelist only — never attach context blobs (codes, venues, chat, etc.).
        from app.push.privacy import safe_action_url, scrub_push_copy

        action_url = safe_action_url(self.url)
        tag = (self.tag or self.notification_id or self.kind or "padeya-notification")[
            :80
        ]
        data = {
            "title": scrub_push_copy(self.title or "Pàdéyá", limit=120) or "Pàdéyá",
            "body": scrub_push_copy(
                self.body or "You have a new notification on Pàdéyá.", limit=240
            )
            or "You have a new notification on Pàdéyá.",
            "action_url": action_url,
            "notification_id": (
                str(self.notification_id)[:80] if self.notification_id else None
            ),
            "tag": tag,
            "timestamp": int(
                self.timestamp_ms
                if self.timestamp_ms is not None
                else datetime.now(UTC).timestamp() * 1000
            ),
            "icon": self.icon or "/icons/icon-192.png",
            "badge": self.badge or "/icons/icon-192.png",
        }
        return json.dumps(data)


@dataclass
class ProviderSendResult:
    ok: bool
    status: str  # sent | logged | failed | revoked | skipped
    delivered: int = 0
    error: str | None = None


class BasePushProvider(ABC):
    name: str

    @abstractmethod
    def send(
        self,
        db: Session,
        *,
        user_id,
        subscriptions: list[PushSubscription],
        payload: PushPayload,
        push_event_id=None,
    ) -> ProviderSendResult:
        raise NotImplementedError


class LogPushProvider(BasePushProvider):
    """Record delivery without calling browser endpoints."""

    name = "log"

    def send(
        self,
        db: Session,
        *,
        user_id,
        subscriptions: list[PushSubscription],
        payload: PushPayload,
        push_event_id=None,
    ) -> ProviderSendResult:
        del push_event_id
        event = PushDeliveryEvent(
            user_id=user_id,
            subscription_id=subscriptions[0].id if subscriptions else None,
            notification_id=None,
            kind=payload.kind[:64],
            status="logged",
            sent_at=datetime.now(UTC),
        )
        db.add(event)
        if subscriptions:
            mark_subscription_success(subscriptions[0])
        db.flush()
        logger.info(
            "push logged user=%s kind=%s delivered=%s",
            user_id,
            payload.kind,
            1,
        )
        return ProviderSendResult(ok=True, status="logged", delivered=1)


class WebPushProvider(BasePushProvider):
    """Real browser delivery via pywebpush + VAPID."""

    name = "web_push"

    def send(
        self,
        db: Session,
        *,
        user_id,
        subscriptions: list[PushSubscription],
        payload: PushPayload,
        push_event_id=None,
    ) -> ProviderSendResult:
        del push_event_id
        settings = get_active_push_settings(db)
        if settings is None or not settings.vapid_public_key:
            return ProviderSendResult(
                ok=False, status="failed", error="vapid_missing"
            )
        if not settings.vapid_private_key_encrypted:
            return ProviderSendResult(
                ok=False, status="failed", error="vapid_private_missing"
            )
        if not subscriptions:
            return ProviderSendResult(
                ok=False, status="skipped", error="no_active_subscriptions"
            )

        try:
            private_key = decrypt_secret(settings.vapid_private_key_encrypted)
        except Exception:  # noqa: BLE001
            logger.error("Cannot decrypt VAPID private key")
            return ProviderSendResult(
                ok=False, status="failed", error="vapid_decrypt_failed"
            )

        try:
            from pywebpush import WebPushException, webpush
        except ImportError:
            return ProviderSendResult(
                ok=False, status="failed", error="pywebpush_missing"
            )

        subject = (settings.vapid_subject or "mailto:support@padeya.com").strip()
        data = payload.to_json()
        delivered = 0
        last_error: str | None = None

        for sub in subscriptions:
            delivery = PushDeliveryEvent(
                user_id=user_id,
                subscription_id=sub.id,
                notification_id=None,
                kind=payload.kind[:64],
                status="pending",
            )
            db.add(delivery)
            db.flush()
            try:
                p256dh = decrypt_secret(sub.p256dh_encrypted)
                auth = decrypt_secret(sub.auth_encrypted)
                webpush(
                    subscription_info={
                        "endpoint": sub.endpoint,
                        "keys": {"p256dh": p256dh, "auth": auth},
                    },
                    data=data,
                    vapid_private_key=private_key,
                    vapid_claims={"sub": subject},
                )
                delivery.status = "sent"
                delivery.sent_at = datetime.now(UTC)
                mark_subscription_success(sub)
                delivered += 1
            except WebPushException as exc:  # type: ignore[misc]
                status_code = getattr(
                    getattr(exc, "response", None), "status_code", None
                )
                safe = sanitize_delivery_error(str(exc)) or "webpush_failed"
                delivery.status = "failed"
                delivery.error_message = safe
                mark_subscription_failure(sub, status_code=status_code)
                if sub.revoked_at is not None:
                    delivery.status = "revoked"
                last_error = safe
                logger.warning(
                    "webpush failed sub=%s status=%s", sub.id, status_code
                )
            except Exception as exc:  # noqa: BLE001
                safe = sanitize_delivery_error(str(exc)) or "provider_error"
                delivery.status = "failed"
                delivery.error_message = safe
                mark_subscription_failure(sub)
                last_error = safe

        db.flush()
        if delivered:
            return ProviderSendResult(ok=True, status="sent", delivered=delivered)
        return ProviderSendResult(
            ok=False,
            status="failed",
            delivered=0,
            error=last_error or "all_subscriptions_failed",
        )


def get_push_provider(db: Session) -> BasePushProvider:
    settings = get_active_push_settings(db)
    mode = (settings.provider if settings else "log") or "log"
    mode = mode.strip().lower()
    if mode == "web_push":
        return WebPushProvider()
    return LogPushProvider()
