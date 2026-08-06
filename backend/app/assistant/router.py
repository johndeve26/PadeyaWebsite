"""Public / authenticated assistant API routes."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from starlette.responses import Response

from app.assistant import confirmation as confirmation_svc
from app.assistant import sessions as session_svc
from app.assistant.constants import ANONYMOUS_COOKIE_MAX_AGE_SECONDS, ANONYMOUS_COOKIE_NAME
from app.assistant.privacy import sanitize_page_context
from app.assistant.schemas import (
    AssistantStatusPublic,
    ConfirmAction,
    FeedbackCreate,
    ChatStreamRequest,
    SessionDetailPublic,
    SessionPublic,
    MessagePublic,
)
from app.assistant.service import assert_assistant_allowed, public_status
from app.assistant.streaming import chat_streaming_response
from app.auth.dependencies import get_current_user_optional
from app.core.database import get_db
from app.users.models import User

router = APIRouter(prefix="/assistant", tags=["assistant"])


def _anon_sid(request: Request) -> str | None:
    return request.cookies.get(ANONYMOUS_COOKIE_NAME)


def _set_anon_cookie(response: Response, sid: str) -> None:
    response.set_cookie(
        key=ANONYMOUS_COOKIE_NAME,
        value=sid,
        max_age=ANONYMOUS_COOKIE_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
        path="/",
    )


@router.get("/status", response_model=AssistantStatusPublic)
def assistant_status(
    db: Annotated[Session, Depends(get_db)],
) -> AssistantStatusPublic:
    return AssistantStatusPublic(**public_status(db))


@router.post("/chat/stream")
def chat_stream(
    payload: ChatStreamRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> Any:
    assert_assistant_allowed(user=user)
    page_ctx: dict[str, Any] | None
    if payload.page_context is None:
        page_ctx = None
    elif hasattr(payload.page_context, "model_dump"):
        page_ctx = sanitize_page_context(payload.page_context.model_dump())  # type: ignore[union-attr]
    else:
        page_ctx = sanitize_page_context(dict(payload.page_context))  # type: ignore[arg-type]

    anon = _anon_sid(request)
    set_cookie = False
    if user is None and not anon:
        anon = session_svc.new_anonymous_session_id()
        set_cookie = True

    stream = chat_streaming_response(
        db,
        request=request,
        user=user,
        message=payload.message,
        session_id=payload.session_id,
        page_context=page_ctx,
        anonymous_session_id=anon,
        timezone=payload.timezone,
    )
    # Always refresh anonymous cookie when present so follow-ups stay bound.
    if user is None and anon:
        _set_anon_cookie(stream, anon)
        set_cookie = True
    _ = set_cookie
    return stream


@router.get("/sessions", response_model=list[SessionPublic])
def list_sessions(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> list[SessionPublic]:
    assert_assistant_allowed(user=user)
    if user is None:
        return []
    rows = session_svc.list_sessions_for_user(db, user=user)
    out: list[SessionPublic] = []
    for row in rows:
        out.append(
            SessionPublic(
                id=row.id,
                mode=row.mode,
                title=row.title,
                active_role=row.active_role,
                expires_at=row.expires_at,
                created_at=row.created_at,
                updated_at=row.updated_at,
                message_count=session_svc.message_count(db, row.id),
            )
        )
    return out


@router.get("/sessions/{session_id}", response_model=SessionDetailPublic)
def get_session(
    session_id: UUID,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> SessionDetailPublic:
    assert_assistant_allowed(user=user)
    row = session_svc.get_session_for_actor(
        db,
        session_id=session_id,
        user=user,
        anonymous_session_id=_anon_sid(request),
    )
    messages = [
        MessagePublic(
            id=m.id,
            role=m.role,
            content=m.content,
            structured_content_json=m.structured_content_json,
            safety_status=m.safety_status,
            created_at=m.created_at,
        )
        for m in (row.messages or [])
    ]
    return SessionDetailPublic(
        id=row.id,
        mode=row.mode,
        title=row.title,
        active_role=row.active_role,
        expires_at=row.expires_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
        message_count=len(messages),
        messages=messages,
    )


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: UUID,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> dict[str, str]:
    assert_assistant_allowed(user=user)
    session_svc.delete_session(
        db,
        session_id=session_id,
        user=user,
        anonymous_session_id=_anon_sid(request),
    )
    return {"status": "deleted"}


@router.post("/actions/{confirmation_id}/confirm")
def confirm_action(
    confirmation_id: UUID,
    payload: ConfirmAction,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> dict[str, Any]:
    assert_assistant_allowed(user=user)
    if user is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="Authentication required")
    # idempotency_key on payload reserved for future client correlation
    _ = payload.idempotency_key
    return confirmation_svc.confirm_action(
        db, confirmation_id=confirmation_id, user=user
    )


@router.post("/actions/{confirmation_id}/cancel")
def cancel_action(
    confirmation_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> dict[str, Any]:
    assert_assistant_allowed(user=user)
    if user is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="Authentication required")
    return confirmation_svc.cancel_action(
        db, confirmation_id=confirmation_id, user=user
    )


@router.post("/feedback")
def create_feedback(
    payload: FeedbackCreate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> dict[str, Any]:
    assert_assistant_allowed(user=user)
    row = session_svc.record_feedback(
        db,
        session_id=payload.session_id,
        message_id=payload.message_id,
        rating=payload.rating,
        reason=payload.reason,
        comment=payload.comment,
        user=user,
        anonymous_session_id=_anon_sid(request),
    )
    return {"id": str(row.id), "status": "recorded"}
