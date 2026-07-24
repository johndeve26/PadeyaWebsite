"""FastAPI WebSocket messaging endpoint.

WS /api/v1/messages/ws?token=<access_jwt>

Auth: validate JWT on connect; close 4401 if missing/invalid/expired/inactive.
REST remains send authority — no send_message over the socket.
Thread actions re-check server-side permission gates (never trust the client).
"""

from __future__ import annotations

import json
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core import database as database_module
from app.core.security import decode_access_token
from app.messaging import ws_events
from app.messaging.ws_hub import messaging_hub
from app.messaging.ws_permissions import (
    thread_participant_ids,
    user_may_emit_thread_action,
)
from app.users.service import get_user_by_id

router = APIRouter(tags=["messaging-ws"])


def _user_from_token(db, token: str | None):
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        user_id = UUID(str(payload["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
    user = get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        return None
    return user


def _parse_thread_id(data: dict) -> UUID | None:
    try:
        return UUID(str(data.get("thread_id")))
    except (TypeError, ValueError):
        return None


@router.websocket("/messages/ws")
async def messages_ws(
    websocket: WebSocket,
    token: Annotated[str | None, Query()] = None,
) -> None:
    # Short-lived session for auth only — do not hold DB for the socket lifetime.
    db = database_module.SessionLocal()
    try:
        user = _user_from_token(db, token)
        if user is None:
            await websocket.accept()
            await websocket.close(code=4401)
            return
        user_id = user.id
    finally:
        db.close()

    # Personal user channel subscription (implicit on connect).
    await messaging_hub.connect(user_id, websocket)
    try:
        await websocket.send_json(
            {"type": "connected", "user_channel": str(user_id)}
        )
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                data = {}
            if not isinstance(data, dict):
                continue
            msg_type = str(data.get("type") or "")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            if msg_type in {"typing.start", "typing.stop", "typing", "typing_stop"}:
                thread_id = _parse_thread_id(data)
                if thread_id is None:
                    continue
                session = database_module.SessionLocal()
                try:
                    from app.messaging.service import safe_typing_display_name

                    u = get_user_by_id(session, user_id)
                    if u is None:
                        continue
                    # Participant + can-reply gate — never trust client thread_id alone.
                    thread = user_may_emit_thread_action(
                        session, u, thread_id, require_can_reply=True
                    )
                    if thread is None:
                        continue
                    is_typing = msg_type in {"typing.start", "typing"}
                    # Ephemeral only — not written to the database.
                    ws_events.publish_typing(
                        thread_id=thread_id,
                        from_user_id=user_id,
                        participant_ids=thread_participant_ids(thread),
                        is_typing=is_typing,
                        display_name=safe_typing_display_name(session, u, thread),
                    )
                finally:
                    session.close()
                continue

            if msg_type == "message.read":
                # Only thread_id is accepted from the client. reader_id / read_at
                # from the payload are ignored — receipt always belongs to the
                # authenticated socket user for their own thread.
                thread_id = _parse_thread_id(data)
                if thread_id is None:
                    continue
                session = database_module.SessionLocal()
                try:
                    from app.messaging import service as messaging_svc

                    u = get_user_by_id(session, user_id)
                    if u is None:
                        continue
                    # Participant + not blocked/closed/disconnected (same family as REST)
                    if (
                        user_may_emit_thread_action(
                            session, u, thread_id, require_can_reply=False
                        )
                        is None
                    ):
                        continue
                    messaging_svc.mark_read(session, u, thread_id)
                except Exception:
                    pass
                finally:
                    session.close()
                continue

            if msg_type == "thread.subscribe":
                thread_id = _parse_thread_id(data)
                if thread_id is None:
                    continue
                session = database_module.SessionLocal()
                try:
                    u = get_user_by_id(session, user_id)
                    if u is None:
                        continue
                    # Admins who are not parties are denied here.
                    thread = user_may_emit_thread_action(
                        session, u, thread_id, require_can_reply=False
                    )
                    if thread is None:
                        await websocket.send_json(
                            {
                                "type": "thread.subscribe_denied",
                                "thread_id": str(thread_id),
                            }
                        )
                        continue
                    messaging_hub.subscribe_thread(websocket, thread_id)
                    await websocket.send_json(
                        {
                            "type": "thread.subscribed",
                            "thread_id": str(thread_id),
                        }
                    )
                finally:
                    session.close()
                continue

            if msg_type == "thread.unsubscribe":
                thread_id = _parse_thread_id(data)
                if thread_id is None:
                    continue
                messaging_hub.unsubscribe_thread(websocket, thread_id)
                await websocket.send_json(
                    {
                        "type": "thread.unsubscribed",
                        "thread_id": str(thread_id),
                    }
                )
                continue

            # Ignore send_message and any other client types — REST is authority.
    except WebSocketDisconnect:
        pass
    finally:
        await messaging_hub.disconnect(user_id, websocket)
