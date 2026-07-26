"""Browser Web Push delivery via pywebpush."""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.encryption import decrypt_secret
from app.messaging.models import InAppNotification
from app.notifications.models import PushDeliveryEvent, PushSubscription
from app.notifications.prefs import push_preference_allows
from app.notifications.settings_service import get_active_push_settings

logger = logging.getLogger("padeya.notifications.push")

# Soft failures accumulate; hard expiry (404/410) deactivates immediately.
FAILURE_DEACTIVATE_THRESHOLD = 5


def _safe_error(exc: Exception) -> str:
    text = str(exc)[:400]
    for secret_label in ("auth", "p256dh", "private"):
        if secret_label in text.lower() and len(text) > 80:
            return text[:80] + "…"
    return text


def infer_platform(user_agent: str | None) -> str | None:
    ua = (user_agent or "").lower()
    if not ua:
        return None
    if "iphone" in ua or "ipad" in ua or "ios" in ua:
        return "ios"
    if "android" in ua:
        return "android"
    if "mac os" in ua or "macintosh" in ua:
        return "macos"
    if "windows" in ua:
        return "windows"
    if "linux" in ua:
        return "linux"
    if "mobile" in ua:
        return "mobile"
    return "web"


def default_device_label(user_agent: str | None, platform: str | None) -> str:
    if platform:
        return f"{platform.capitalize()} browser"
    ua = user_agent or ""
    m = re.search(r"(Chrome|Firefox|Safari|Edge|Opera)/[\d.]+", ua, re.I)
    if m:
        return f"{m.group(1)} browser"
    return "Browser"


def _active_subscriptions(db: Session, *, user_id: UUID) -> list[PushSubscription]:
    return list(
        db.scalars(
            select(PushSubscription).where(
                PushSubscription.user_id == user_id,
                PushSubscription.is_active.is_(True),
                PushSubscription.revoked_at.is_(None),
            )
        )
    )


def deactivate_subscription(
    sub: PushSubscription,
    *,
    reason: str = "deactivated",
) -> None:
    now = datetime.now(UTC)
    sub.is_active = False
    if sub.revoked_at is None:
        sub.revoked_at = now
    logger.info(
        "push subscription deactivated id=%s reason=%s failures=%s",
        sub.id,
        reason,
        sub.failure_count,
    )


def mark_subscription_success(sub: PushSubscription) -> None:
    now = datetime.now(UTC)
    sub.last_success_at = now
    sub.failure_count = 0
    sub.is_active = True
    sub.revoked_at = None


def mark_subscription_failure(
    sub: PushSubscription,
    *,
    status_code: int | None = None,
    deactivate_now: bool = False,
) -> None:
    now = datetime.now(UTC)
    sub.last_failure_at = now
    sub.failure_count = int(sub.failure_count or 0) + 1
    expired = status_code in {404, 410}
    if deactivate_now or expired or sub.failure_count >= FAILURE_DEACTIVATE_THRESHOLD:
        reason = "expired" if expired else "repeated_failures"
        deactivate_subscription(sub, reason=reason)


def deliver_push_for_notification(
    db: Session,
    *,
    notification: InAppNotification,
    force: bool = False,
) -> int:
    """Send push to all active subscriptions for the notification user.

    Returns count of successful deliveries. Never raises to callers.
    """
    if not force:
        allowed, reason = push_preference_allows(
            db,
            user_id=notification.user_id,
            kind=notification.kind,
            force=force,
        )
        if not allowed:
            logger.debug(
                "push skipped user=%s kind=%s reason=%s",
                notification.user_id,
                notification.kind,
                reason,
            )
            return 0

    settings = get_active_push_settings(db)
    if settings is None or not settings.push_enabled:
        return 0

    provider = (settings.provider or "log").strip().lower()
    subs = _active_subscriptions(db, user_id=notification.user_id)

    # Safe whitelist — prefer app.push.provider.PushPayload for new sends.
    action = notification.link_path or "/dashboard/notifications"
    payload_dict = {
        "title": (notification.title or "Pàdéyá")[:120],
        "body": (notification.body or "You have a new notification on Pàdéyá.")[:240],
        "action_url": action[:300],
        "notification_id": str(notification.id),
        "tag": str(notification.id),
        "timestamp": int(datetime.now(UTC).timestamp() * 1000),
    }

    # Log mode: record delivery attempts without calling push endpoints.
    if provider == "log":
        event = PushDeliveryEvent(
            user_id=notification.user_id,
            subscription_id=subs[0].id if subs else None,
            notification_id=notification.id,
            kind=notification.kind,
            status="logged",
            sent_at=datetime.now(UTC),
        )
        db.add(event)
        if subs:
            mark_subscription_success(subs[0])
        db.flush()
        logger.info(
            "push logged (provider=log) user=%s kind=%s notification=%s",
            notification.user_id,
            notification.kind,
            notification.id,
        )
        return 1

    if not settings.vapid_public_key or not settings.vapid_private_key_encrypted:
        return 0
    if not subs:
        return 0

    try:
        private_key_plain = decrypt_secret(settings.vapid_private_key_encrypted)
    except Exception:  # noqa: BLE001
        logger.error("Cannot decrypt VAPID private key — push skipped for this send")
        return 0

    subject = (settings.vapid_subject or "mailto:support@padeya.com").strip()

    try:
        from pywebpush import WebPushException, webpush

        from app.push.vapid import load_vapid_private

        vapid_key = load_vapid_private(private_key_plain)
    except ImportError:
        logger.error("pywebpush not installed")
        return 0
    except Exception:  # noqa: BLE001
        logger.error("Cannot load VAPID private key — push skipped for this send")
        return 0

    payload = json.dumps(payload_dict)
    sent = 0
    for sub in subs:
        event = PushDeliveryEvent(
            user_id=notification.user_id,
            subscription_id=sub.id,
            notification_id=notification.id,
            kind=notification.kind,
            status="pending",
        )
        db.add(event)
        db.flush()
        try:
            p256dh = decrypt_secret(sub.p256dh_encrypted)
            auth = decrypt_secret(sub.auth_encrypted)
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": p256dh, "auth": auth},
                },
                data=payload,
                vapid_private_key=vapid_key,
                vapid_claims={"sub": subject},
            )
            event.status = "sent"
            event.sent_at = datetime.now(UTC)
            mark_subscription_success(sub)
            sent += 1
        except WebPushException as exc:  # type: ignore[misc]
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            safe = _safe_error(exc)
            event.status = "failed"
            event.error_message = safe
            mark_subscription_failure(sub, status_code=status_code)
            if sub.revoked_at is not None:
                event.status = "revoked"
            logger.warning(
                "webpush failed sub=%s status=%s error=%s",
                sub.id,
                status_code,
                safe,
            )
        except Exception as exc:  # noqa: BLE001
            event.status = "failed"
            event.error_message = _safe_error(exc)
            mark_subscription_failure(sub)
            logger.warning("webpush error sub=%s error=%s", sub.id, event.error_message)
    db.flush()
    return sent


def upsert_subscription(
    db: Session,
    *,
    user_id: UUID,
    endpoint: str,
    p256dh: str,
    auth: str,
    user_agent: str | None = None,
    device_label: str | None = None,
    platform: str | None = None,
) -> PushSubscription:
    from app.core.encryption import encrypt_secret

    endpoint_norm = (endpoint or "").strip()
    if not endpoint_norm.startswith("https://"):
        raise ValueError("Invalid push endpoint")
    if not p256dh.strip() or not auth.strip():
        raise ValueError("Push subscription keys are required")

    platform_norm = (platform or "").strip().lower()[:64] or infer_platform(user_agent)
    label = (device_label or "").strip()[:120] or default_device_label(
        user_agent, platform_norm
    )

    row = db.scalar(
        select(PushSubscription).where(PushSubscription.endpoint == endpoint_norm)
    )
    created = row is None
    if row is None:
        row = PushSubscription(
            user_id=user_id,
            endpoint=endpoint_norm,
            p256dh_encrypted=encrypt_secret(p256dh.strip()),
            auth_encrypted=encrypt_secret(auth.strip()),
            user_agent=(user_agent or "")[:400] or None,
            device_label=label,
            platform=platform_norm,
            is_active=True,
            failure_count=0,
        )
        db.add(row)
    else:
        row.user_id = user_id
        row.p256dh_encrypted = encrypt_secret(p256dh.strip())
        row.auth_encrypted = encrypt_secret(auth.strip())
        row.user_agent = (user_agent or "")[:400] or None
        row.device_label = label
        row.platform = platform_norm
        row.is_active = True
        row.revoked_at = None
        row.failure_count = 0
    db.flush()
    if created:
        logger.info(
            "push_subscription_created id=%s user=%s platform=%s",
            row.id,
            user_id,
            platform_norm,
        )
    else:
        logger.info(
            "push_subscription_saved id=%s user=%s platform=%s",
            row.id,
            user_id,
            platform_norm,
        )
    return row


def revoke_subscription(
    db: Session,
    *,
    user_id: UUID,
    endpoint: str | None = None,
    subscription_id: UUID | None = None,
) -> bool:
    stmt = select(PushSubscription).where(PushSubscription.user_id == user_id)
    if subscription_id is not None:
        stmt = stmt.where(PushSubscription.id == subscription_id)
    elif endpoint:
        stmt = stmt.where(PushSubscription.endpoint == endpoint.strip())
    else:
        return False
    row = db.scalar(stmt)
    if row is None:
        return False
    deactivate_subscription(row, reason="user_removed")
    db.flush()
    return True


def list_user_subscriptions(
    db: Session,
    *,
    user_id: UUID,
    include_inactive: bool = False,
) -> list[PushSubscription]:
    stmt = select(PushSubscription).where(PushSubscription.user_id == user_id)
    if not include_inactive:
        stmt = stmt.where(
            PushSubscription.is_active.is_(True),
            PushSubscription.revoked_at.is_(None),
        )
    return list(
        db.scalars(stmt.order_by(PushSubscription.created_at.desc()))
    )


def serialize_subscription_public(row: PushSubscription) -> dict:
    """Never include p256dh/auth keys or endpoint secrets beyond a short hint."""
    endpoint = row.endpoint or ""
    hint = endpoint[-24:] if len(endpoint) > 24 else endpoint
    return {
        "id": row.id,
        "device_label": row.device_label,
        "platform": row.platform,
        "user_agent": row.user_agent,
        "endpoint_hint": f"…{hint}" if hint else None,
        "is_active": bool(row.is_active),
        "revoked_at": row.revoked_at,
        "last_success_at": row.last_success_at,
        "last_failure_at": row.last_failure_at,
        "failure_count": int(row.failure_count or 0),
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }
