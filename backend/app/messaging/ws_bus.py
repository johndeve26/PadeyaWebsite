"""Cross-worker messaging fan-out via Redis pub/sub.

Channels:
  - user:{user_id}:messages
  - thread:{thread_id}:messages

When Redis is unavailable (typical local single-worker), falls back to an
in-memory bus on this process only. Documented in docs/MESSAGING.md.
"""

from __future__ import annotations

import json
import logging
import threading
from collections.abc import Callable
from typing import Any
from uuid import UUID

from app.messaging.ws_sanitize import sanitize_event_payload

logger = logging.getLogger(__name__)

UserHandler = Callable[[list[UUID], dict[str, Any]], None]
ThreadHandler = Callable[[UUID, list[UUID], dict[str, Any], bool], None]


def user_channel(user_id: UUID | str) -> str:
    return f"user:{user_id}:messages"


def thread_channel(thread_id: UUID | str) -> str:
    return f"thread:{thread_id}:messages"


class MessagingEventBus:
    """Publish sanitized events; deliver to local handlers (via Redis or memory)."""

    def __init__(self) -> None:
        self._mode: str = "memory"  # memory | redis
        self._on_users: UserHandler | None = None
        self._on_thread: ThreadHandler | None = None
        self._pubsub: Any | None = None
        self._publish_client: Any | None = None
        self._listener: threading.Thread | None = None
        self._stop = threading.Event()
        self._lock = threading.RLock()
        self._user_refs: dict[str, int] = {}
        self._thread_refs: dict[str, int] = {}

    @property
    def mode(self) -> str:
        return self._mode

    def start(
        self,
        *,
        on_users: UserHandler,
        on_thread: ThreadHandler,
    ) -> str:
        """Start bus. Returns active mode: ``redis`` or ``memory``."""
        self._on_users = on_users
        self._on_thread = on_thread
        self._stop.clear()

        from app.core.config import get_settings

        # Keep pytest deterministic — never depend on a shared Redis during tests.
        if get_settings().app_env == "test":
            self._mode = "memory"
            logger.info("messaging ws bus: in-memory (APP_ENV=test)")
            return self._mode

        client = self._try_redis()
        if client is None:
            self._mode = "memory"
            logger.info(
                "messaging ws bus: in-memory fallback (single-worker only; "
                "set REDIS_URL and run Redis for multi-worker fan-out)"
            )
            return self._mode

        self._publish_client = client
        try:
            self._pubsub = client.pubsub(ignore_subscribe_messages=True)
            # Keep subscription alive with a noop pattern; real channels added on demand.
            self._pubsub.psubscribe("__padeya_messaging_keepalive__")
        except Exception:
            logger.warning(
                "messaging ws bus: Redis pubsub setup failed; using in-memory fallback",
                exc_info=True,
            )
            self._mode = "memory"
            self._publish_client = None
            self._pubsub = None
            return self._mode

        self._mode = "redis"
        self._listener = threading.Thread(
            target=self._listen_loop,
            name="messaging-ws-redis",
            daemon=True,
        )
        self._listener.start()
        logger.info("messaging ws bus: Redis pub/sub enabled")
        return self._mode

    def stop(self) -> None:
        self._stop.set()
        pubsub = self._pubsub
        if pubsub is not None:
            try:
                pubsub.close()
            except Exception:
                pass
        self._pubsub = None
        self._publish_client = None
        if self._listener and self._listener.is_alive():
            self._listener.join(timeout=2.0)
        self._listener = None
        with self._lock:
            self._user_refs.clear()
            self._thread_refs.clear()

    def _try_redis(self) -> Any | None:
        from app.core.redis import get_redis

        # Fresh ping each start (avoid stale None from boot before Redis is up)
        import app.core.redis as redis_mod

        redis_mod._redis_client = None
        return get_redis()

    def ensure_user_channel(self, user_id: UUID) -> None:
        channel = user_channel(user_id)
        with self._lock:
            self._user_refs[channel] = self._user_refs.get(channel, 0) + 1
            if self._user_refs[channel] == 1:
                self._subscribe(channel)

    def drop_user_channel(self, user_id: UUID) -> None:
        channel = user_channel(user_id)
        with self._lock:
            n = self._user_refs.get(channel, 0) - 1
            if n <= 0:
                self._user_refs.pop(channel, None)
                self._unsubscribe(channel)
            else:
                self._user_refs[channel] = n

    def ensure_thread_channel(self, thread_id: UUID) -> None:
        channel = thread_channel(thread_id)
        with self._lock:
            self._thread_refs[channel] = self._thread_refs.get(channel, 0) + 1
            if self._thread_refs[channel] == 1:
                self._subscribe(channel)

    def drop_thread_channel(self, thread_id: UUID) -> None:
        channel = thread_channel(thread_id)
        with self._lock:
            n = self._thread_refs.get(channel, 0) - 1
            if n <= 0:
                self._thread_refs.pop(channel, None)
                self._unsubscribe(channel)
            else:
                self._thread_refs[channel] = n

    def publish_users(self, user_ids: list[UUID], payload: dict[str, Any]) -> None:
        clean = sanitize_event_payload(payload)
        if not isinstance(clean, dict):
            return
        if self._mode == "memory" or self._publish_client is None:
            if self._on_users:
                self._on_users(list(user_ids), clean)
            return
        for uid in user_ids:
            envelope = {
                "v": 1,
                "kind": "user",
                "user_id": str(uid),
                "payload": clean,
            }
            try:
                self._publish_client.publish(
                    user_channel(uid), json.dumps(envelope, default=str)
                )
            except Exception:
                logger.debug("redis publish user failed; local deliver", exc_info=True)
                if self._on_users:
                    self._on_users([uid], clean)

    def publish_thread(
        self,
        thread_id: UUID,
        *,
        allowed_user_ids: list[UUID],
        payload: dict[str, Any],
        fallback_to_users: bool = True,
    ) -> None:
        clean = sanitize_event_payload(payload)
        if not isinstance(clean, dict):
            return
        if self._mode == "memory" or self._publish_client is None:
            if self._on_thread:
                self._on_thread(
                    thread_id, list(allowed_user_ids), clean, fallback_to_users
                )
            return
        envelope = {
            "v": 1,
            "kind": "thread",
            "thread_id": str(thread_id),
            "allowed_user_ids": [str(uid) for uid in allowed_user_ids],
            "fallback_to_users": fallback_to_users,
            "payload": clean,
        }
        try:
            self._publish_client.publish(
                thread_channel(thread_id), json.dumps(envelope, default=str)
            )
        except Exception:
            logger.debug("redis publish thread failed; local deliver", exc_info=True)
            if self._on_thread:
                self._on_thread(
                    thread_id, list(allowed_user_ids), clean, fallback_to_users
                )

    def _subscribe(self, channel: str) -> None:
        if self._mode != "redis" or self._pubsub is None:
            return
        try:
            self._pubsub.subscribe(channel)
        except Exception:
            logger.debug("redis subscribe failed: %s", channel, exc_info=True)

    def _unsubscribe(self, channel: str) -> None:
        if self._mode != "redis" or self._pubsub is None:
            return
        try:
            self._pubsub.unsubscribe(channel)
        except Exception:
            logger.debug("redis unsubscribe failed: %s", channel, exc_info=True)

    def _listen_loop(self) -> None:
        pubsub = self._pubsub
        if pubsub is None:
            return
        try:
            while not self._stop.is_set():
                message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if not message:
                    continue
                if message.get("type") != "message":
                    continue
                data = message.get("data")
                if not data:
                    continue
                try:
                    envelope = json.loads(data)
                except json.JSONDecodeError:
                    continue
                self._dispatch_envelope(envelope)
        except Exception:
            if not self._stop.is_set():
                logger.warning("messaging ws redis listener stopped", exc_info=True)

    def _dispatch_envelope(self, envelope: dict[str, Any]) -> None:
        kind = envelope.get("kind")
        payload = envelope.get("payload")
        if not isinstance(payload, dict):
            return
        payload = sanitize_event_payload(payload)
        if not isinstance(payload, dict):
            return
        if kind == "user":
            try:
                uid = UUID(str(envelope.get("user_id")))
            except (TypeError, ValueError):
                return
            if self._on_users:
                self._on_users([uid], payload)
            return
        if kind == "thread":
            try:
                tid = UUID(str(envelope.get("thread_id")))
            except (TypeError, ValueError):
                return
            allowed: list[UUID] = []
            for raw in envelope.get("allowed_user_ids") or []:
                try:
                    allowed.append(UUID(str(raw)))
                except (TypeError, ValueError):
                    continue
            if self._on_thread:
                self._on_thread(
                    tid,
                    allowed,
                    payload,
                    bool(envelope.get("fallback_to_users", True)),
                )


messaging_bus = MessagingEventBus()
