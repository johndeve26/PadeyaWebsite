"""Action confirmation create / confirm / cancel with expiry + user binding."""

from __future__ import annotations

import hashlib
import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.assistant.models import AssistantActionConfirmation
from app.assistant.privacy import sanitize_tool_args_for_log
from app.assistant.tools.executor import execute_tool
from app.users.models import User

_DEFAULT_TTL_MINUTES = 15


def _idem_key(user_id: UUID, tool_name: str, args: dict[str, Any] | None, explicit: str | None) -> str:
    if explicit:
        return explicit.strip()[:128]
    payload = json.dumps(
        {"u": str(user_id), "t": tool_name, "a": sanitize_tool_args_for_log(args)},
        sort_keys=True,
        default=str,
    )
    digest = hashlib.sha256(payload.encode()).hexdigest()[:40]
    return f"asst-{digest}-{secrets.token_hex(4)}"


def create_confirmation(
    db: Session,
    *,
    user: User,
    tool_name: str,
    args: dict[str, Any] | None,
    idempotency_key: str | None = None,
    ttl_minutes: int = _DEFAULT_TTL_MINUTES,
) -> AssistantActionConfirmation:
    key = _idem_key(user.id, tool_name, args, idempotency_key)
    existing = db.scalars(
        select(AssistantActionConfirmation).where(
            AssistantActionConfirmation.idempotency_key == key
        )
    ).first()
    if existing is not None:
        return existing
    row = AssistantActionConfirmation(
        user_id=user.id,
        tool_name=tool_name,
        sanitized_arguments_json=sanitize_tool_args_for_log(args),
        idempotency_key=key,
        status="pending",
        expires_at=datetime.now(UTC) + timedelta(minutes=ttl_minutes),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _get_owned(
    db: Session, *, confirmation_id: UUID, user: User
) -> AssistantActionConfirmation:
    row = db.get(AssistantActionConfirmation, confirmation_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Confirmation not found")
    if row.user_id != user.id:
        raise HTTPException(status_code=403, detail="Confirmation not owned by user")
    return row


def confirm_action(
    db: Session,
    *,
    confirmation_id: UUID,
    user: User,
    page_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row = _get_owned(db, confirmation_id=confirmation_id, user=user)
    now = datetime.now(UTC)
    if row.status != "pending":
        raise HTTPException(status_code=409, detail=f"Confirmation is {row.status}")
    expires = row.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if expires <= now:
        row.status = "expired"
        db.commit()
        raise HTTPException(status_code=410, detail="Confirmation expired")

    result = execute_tool(
        db,
        tool_name=row.tool_name,
        args=row.sanitized_arguments_json or {},
        user=user,
        page_context=page_context,
        confirmed=True,
    )
    row.confirmed_at = now
    row.result_json = {
        k: v
        for k, v in result.items()
        if k not in {"sanitized_arguments"}
    }
    row.status = "confirmed" if result.get("ok") else "failed"
    db.commit()
    db.refresh(row)
    return {
        "confirmation_id": str(row.id),
        "status": row.status,
        "tool_name": row.tool_name,
        "result": row.result_json,
    }


def cancel_action(
    db: Session, *, confirmation_id: UUID, user: User
) -> dict[str, Any]:
    row = _get_owned(db, confirmation_id=confirmation_id, user=user)
    if row.status != "pending":
        raise HTTPException(status_code=409, detail=f"Confirmation is {row.status}")
    row.status = "cancelled"
    db.commit()
    return {"confirmation_id": str(row.id), "status": "cancelled"}
