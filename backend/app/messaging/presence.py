"""Cross-worker WebSocket presence for notification channel selection.

Local hub connections are authoritative for this process. Redis refcounts
cover multi-worker deployments when Redis is available.
"""

from __future__ import annotations

import logging
from uuid import UUID

logger = logging.getLogger(__name__)

_PRESENCE_TTL_SECONDS = 600


def _presence_key(user_id: UUID) -> str:
    return f"padeya:ws:presence:{user_id}"


def mark_user_online(user_id: UUID) -> None:
    try:
        from app.core.redis import get_redis

        client = get_redis()
        if client is None:
            return
        key = _presence_key(user_id)
        client.incr(key)
        client.expire(key, _PRESENCE_TTL_SECONDS)
    except Exception:  # noqa: BLE001
        logger.debug("presence mark online failed", exc_info=True)


def mark_user_offline(user_id: UUID) -> None:
    """Decrement presence when the last local socket for the user closes."""
    try:
        from app.core.redis import get_redis

        client = get_redis()
        if client is None:
            return
        key = _presence_key(user_id)
        remaining = client.decr(key)
        if remaining is None or int(remaining) <= 0:
            client.delete(key)
        else:
            client.expire(key, _PRESENCE_TTL_SECONDS)
    except Exception:  # noqa: BLE001
        logger.debug("presence mark offline failed", exc_info=True)


def is_user_present(user_id: UUID) -> bool:
    """True when the user has an active messaging WebSocket somewhere."""
    try:
        from app.messaging.ws_hub import messaging_hub

        if messaging_hub.is_online(user_id):
            return True
    except Exception:  # noqa: BLE001
        pass

    try:
        from app.core.redis import get_redis

        client = get_redis()
        if client is None:
            return False
        raw = client.get(_presence_key(user_id))
        return bool(raw) and int(raw) > 0
    except Exception:  # noqa: BLE001
        return False


def is_user_active_on_thread(user_id: UUID, thread_id: UUID) -> bool:
    """Local-process check: user has the thread subscribed on an open socket."""
    try:
        from app.messaging.ws_hub import messaging_hub

        return messaging_hub.user_subscribed_to_thread(user_id, thread_id)
    except Exception:  # noqa: BLE001
        return False
