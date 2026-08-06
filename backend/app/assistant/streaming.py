"""SSE streaming helpers for assistant chat."""

from __future__ import annotations

import json
from typing import Any, Iterator
from uuid import UUID

from fastapi import Request
from sqlalchemy.orm import Session
from starlette.responses import StreamingResponse

from app.assistant.schemas import AssistantResponse
from app.assistant.service import run_chat_turn
from app.users.models import User

_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


def _sse(event: str, data: dict[str, Any] | list[Any] | str | None) -> str:
    payload = data if isinstance(data, str) else json.dumps(data, default=str)
    return f"event: {event}\ndata: {payload}\n\n"


def iter_chat_sse(
    db: Session,
    *,
    request: Request,
    user: User | None,
    message: str,
    session_id: UUID | None,
    page_context: dict[str, Any] | None,
    anonymous_session_id: str | None,
    timezone: str | None = None,
) -> Iterator[str]:
    """Yield SSE events for one chat turn."""
    try:
        yield _sse("status", {"phase": "starting"})
        response, meta, anon_sid = run_chat_turn(
            db,
            request=request,
            user=user,
            message=message,
            session_id=session_id,
            page_context_raw=page_context,
            anonymous_session_id=anonymous_session_id,
            timezone=timezone,
        )
        yield _sse(
            "session",
            {
                "session_id": str(response.session_id),
                "mode": response.mode,
                "product_name": response.product_name,
                "anonymous_session_id": anon_sid or None,
            },
        )
        yield _sse("status", {"phase": "tools", "intent": response.intent})

        for item in meta:
            ev = item.get("event") or "status"
            data = item.get("data") or {}
            # Never stream private tool args
            if isinstance(data, dict):
                data = {
                    k: v
                    for k, v in data.items()
                    if k
                    not in {
                        "sanitized_arguments",
                        "arguments",
                        "args",
                        "raw_args",
                    }
                }
            yield _sse(ev, data)
            if ev == "card":
                pass

        for card in response.cards:
            yield _sse("card", card.model_dump())
        for action in response.actions:
            yield _sse("action", action.model_dump(mode="json"))

        # Token-ish chunking for progressive UI (not true model streaming)
        yield _sse("status", {"phase": "responding"})
        text = response.text or ""
        chunk_size = 48
        for i in range(0, len(text), chunk_size):
            yield _sse("token", {"text": text[i : i + chunk_size]})

        yield _sse("done", _done_payload(response))
    except Exception as exc:
        from fastapi import HTTPException

        if isinstance(exc, HTTPException):
            yield _sse(
                "error",
                {"status_code": exc.status_code, "detail": exc.detail},
            )
        else:
            yield _sse("error", {"status_code": 500, "detail": "Assistant error"})
        yield _sse("done", {"ok": False})


def _done_payload(response: AssistantResponse) -> dict[str, Any]:
    return {
        "ok": True,
        "session_id": str(response.session_id),
        "message_id": str(response.message_id) if response.message_id else None,
        "mode": response.mode,
        "product_name": response.product_name,
        "text": response.text,
        "citations": [c.model_dump() for c in response.citations],
        "cards": [c.model_dump() for c in response.cards],
        "actions": [a.model_dump(mode="json") for a in response.actions],
        "safety_status": response.safety_status,
        "used_fallback": response.used_fallback,
        "provider": response.provider,
        "model": response.model,
        "intent": response.intent,
        "confirmation_id": (
            str(response.confirmation_id) if response.confirmation_id else None
        ),
        "trace_id": response.trace_id,
    }


def chat_streaming_response(
    db: Session,
    *,
    request: Request,
    user: User | None,
    message: str,
    session_id: UUID | None,
    page_context: dict[str, Any] | None,
    anonymous_session_id: str | None,
    timezone: str | None = None,
) -> StreamingResponse:
    generator = iter_chat_sse(
        db,
        request=request,
        user=user,
        message=message,
        session_id=session_id,
        page_context=page_context,
        anonymous_session_id=anonymous_session_id,
        timezone=timezone,
    )
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )
