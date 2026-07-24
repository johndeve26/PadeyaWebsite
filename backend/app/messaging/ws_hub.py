"""Local WebSocket connection registry + fan-out entrypoints.

Local sockets live in-process. Cross-worker delivery goes through
``messaging_bus`` (Redis pub/sub, or in-memory fallback for single-worker).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from collections import defaultdict
from typing import Any
from uuid import UUID

from fastapi import WebSocket

from app.messaging.ws_bus import messaging_bus

logger = logging.getLogger(__name__)

_main_loop: asyncio.AbstractEventLoop | None = None
_DEDUPE_TTL_SEC = 2.0


def set_main_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _main_loop
    _main_loop = loop


class MessagingHub:
    def __init__(self) -> None:
        self._connections: dict[UUID, set[WebSocket]] = defaultdict(set)
        self._thread_subs: dict[WebSocket, set[UUID]] = defaultdict(set)
        self._thread_members: dict[UUID, set[WebSocket]] = defaultdict(set)
        self._ws_user: dict[WebSocket, UUID] = {}
        # Suppress duplicate delivers when the same event arrives via user + thread channels.
        self._recent_fps: dict[str, float] = {}

    async def connect(self, user_id: UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        first = user_id not in self._connections or not self._connections[user_id]
        self._connections[user_id].add(websocket)
        self._ws_user[websocket] = user_id
        messaging_bus.ensure_user_channel(user_id)
        if first:
            from app.messaging.presence import mark_user_online

            mark_user_online(user_id)

    async def disconnect(self, user_id: UUID, websocket: WebSocket) -> None:
        for tid in list(self._thread_subs.get(websocket, set())):
            self.unsubscribe_thread(websocket, tid)
        self._thread_subs.pop(websocket, None)
        self._ws_user.pop(websocket, None)
        conns = self._connections.get(user_id)
        if not conns:
            return
        conns.discard(websocket)
        if not conns:
            self._connections.pop(user_id, None)
            messaging_bus.drop_user_channel(user_id)
            from app.messaging.presence import mark_user_offline

            mark_user_offline(user_id)

    def subscribe_thread(self, websocket: WebSocket, thread_id: UUID) -> None:
        was_empty = not self._thread_members.get(thread_id)
        self._thread_subs[websocket].add(thread_id)
        self._thread_members[thread_id].add(websocket)
        if was_empty:
            messaging_bus.ensure_thread_channel(thread_id)

    def unsubscribe_thread(self, websocket: WebSocket, thread_id: UUID) -> None:
        subs = self._thread_subs.get(websocket)
        if subs:
            subs.discard(thread_id)
        members = self._thread_members.get(thread_id)
        if members:
            members.discard(websocket)
            if not members:
                self._thread_members.pop(thread_id, None)
                messaging_bus.drop_thread_channel(thread_id)

    def is_online(self, user_id: UUID) -> bool:
        """Local-process presence only (multi-worker presence is not tracked)."""
        return bool(self._connections.get(user_id))

    def user_subscribed_to_thread(self, user_id: UUID, thread_id: UUID) -> bool:
        for ws in self._connections.get(user_id, set()):
            if thread_id in self._thread_subs.get(ws, set()):
                return True
        return False

    def _fingerprint(self, payload: dict[str, Any]) -> str:
        raw = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]

    def _is_duplicate(self, payload: dict[str, Any]) -> bool:
        fp = self._fingerprint(payload)
        now = time.monotonic()
        # Opportunistic purge
        if len(self._recent_fps) > 500:
            cutoff = now - _DEDUPE_TTL_SEC
            self._recent_fps = {
                k: ts for k, ts in self._recent_fps.items() if ts >= cutoff
            }
        prev = self._recent_fps.get(fp)
        if prev is not None and now - prev < _DEDUPE_TTL_SEC:
            return True
        self._recent_fps[fp] = now
        return False

    def _permitted_recipients(
        self, user_ids: list[UUID], payload: dict[str, Any]
    ) -> list[UUID]:
        """Re-check receive gates at delivery (multi-worker / stale publish defense)."""
        from app.core import database as database_module
        from app.messaging.ws_permissions import (
            PERSONAL_EVENTS,
            filter_event_recipients,
        )

        event_type = str(payload.get("type") or "")
        if event_type in PERSONAL_EVENTS:
            return list(user_ids)
        raw_tid = payload.get("thread_id")
        if raw_tid is None:
            return list(user_ids)
        try:
            thread_id = UUID(str(raw_tid))
        except (TypeError, ValueError):
            return []
        db = database_module.SessionLocal()
        try:
            return filter_event_recipients(
                db,
                list(user_ids),
                thread_id=thread_id,
                event_type=event_type,
            )
        finally:
            db.close()

    async def send_to_users(self, user_ids: list[UUID], payload: dict[str, Any]) -> None:
        permitted = self._permitted_recipients(list(user_ids), payload)
        for uid in permitted:
            dead: list[WebSocket] = []
            for ws in list(self._connections.get(uid, set())):
                try:
                    await ws.send_json(payload)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                await self.disconnect(uid, ws)

    async def send_to_thread_subscribers(
        self,
        thread_id: UUID,
        *,
        allowed_user_ids: list[UUID],
        payload: dict[str, Any],
        fallback_to_users: bool = True,
    ) -> None:
        permitted = set(self._permitted_recipients(list(allowed_user_ids), payload))
        targets = list(self._thread_members.get(thread_id, set()))
        sent_users: set[UUID] = set()
        dead: list[tuple[UUID, WebSocket]] = []

        for ws in targets:
            uid = self._ws_user.get(ws)
            if uid is None or uid not in permitted:
                continue
            try:
                await ws.send_json(payload)
                sent_users.add(uid)
            except Exception:
                dead.append((uid, ws))

        for uid, ws in dead:
            await self.disconnect(uid, ws)

        if fallback_to_users:
            remaining = [uid for uid in permitted if uid not in sent_users]
            if remaining:
                await self.send_to_users(remaining, payload)

    def publish(self, user_ids: list[UUID], payload: dict[str, Any]) -> None:
        """Fan-out via bus (Redis or in-memory) — never mutates original payload."""
        if not user_ids:
            return
        messaging_bus.publish_users(list(user_ids), payload)
        # Mirror onto thread channel when present (multi-worker thread subscribers).
        thread_raw = payload.get("thread_id")
        if thread_raw:
            try:
                tid = UUID(str(thread_raw))
            except (TypeError, ValueError):
                return
            messaging_bus.publish_thread(
                tid,
                allowed_user_ids=list(user_ids),
                payload=payload,
                fallback_to_users=False,
            )

    def publish_thread(
        self,
        thread_id: UUID,
        *,
        allowed_user_ids: list[UUID],
        payload: dict[str, Any],
        fallback_to_users: bool = True,
    ) -> None:
        if not allowed_user_ids:
            return
        messaging_bus.publish_thread(
            thread_id,
            allowed_user_ids=list(allowed_user_ids),
            payload=payload,
            fallback_to_users=fallback_to_users,
        )

    def deliver_local_users(self, user_ids: list[UUID], payload: dict[str, Any]) -> None:
        """Bus callback: deliver only to sockets on this worker."""
        if self._is_duplicate(payload):
            return
        self._schedule(self.send_to_users(list(user_ids), payload))

    def deliver_local_thread(
        self,
        thread_id: UUID,
        allowed_user_ids: list[UUID],
        payload: dict[str, Any],
        fallback_to_users: bool,
    ) -> None:
        if self._is_duplicate(payload):
            return
        self._schedule(
            self.send_to_thread_subscribers(
                thread_id,
                allowed_user_ids=list(allowed_user_ids),
                payload=payload,
                fallback_to_users=fallback_to_users,
            )
        )

    def _schedule(self, coro) -> None:  # type: ignore[no-untyped-def]
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(coro)
            return
        except RuntimeError:
            pass
        loop = _main_loop
        if loop is None or not loop.is_running():
            return
        try:
            asyncio.run_coroutine_threadsafe(coro, loop)
        except Exception:
            logger.debug("messaging ws local deliver skipped", exc_info=True)


messaging_hub = MessagingHub()


def start_messaging_bus() -> str:
    """Wire bus → local hub delivery. Returns mode ``redis`` or ``memory``."""
    return messaging_bus.start(
        on_users=messaging_hub.deliver_local_users,
        on_thread=messaging_hub.deliver_local_thread,
    )


def stop_messaging_bus() -> None:
    messaging_bus.stop()
