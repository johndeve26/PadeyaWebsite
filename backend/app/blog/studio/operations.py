"""Safe metadata logging for Blog AI Studio operations."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.blog.models import BlogAiOperation
from app.users.models import User

# Never persist these substrings in error_code / logs via this module
_SECRET_MARKERS = ("api_key", "apikey", "authorization", "bearer ", "sk-", "secret")


def _safe_error_code(raw: str | None) -> str | None:
    if not raw:
        return None
    lowered = raw.lower()
    if any(m in lowered for m in _SECRET_MARKERS):
        return "provider_error"
    return raw[:64]


def log_operation(
    db: Session,
    *,
    operation: str,
    actor: User | None,
    post_id: uuid.UUID | None = None,
    feature_key: str | None = None,
    provider: str | None = None,
    model_name: str | None = None,
    success: bool = False,
    duration_ms: int | None = None,
    tokens_in: int | None = None,
    tokens_out: int | None = None,
    error_code: str | None = None,
    client_request_id: str | None = None,
    commit: bool = True,
) -> BlogAiOperation:
    row = BlogAiOperation(
        post_id=post_id,
        actor_user_id=actor.id if actor else None,
        operation=operation[:64],
        feature_key=(feature_key or "")[:120] or None,
        provider=(provider or "")[:64] or None,
        model_name=(model_name or "")[:120] or None,
        success=success,
        duration_ms=duration_ms,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        error_code=_safe_error_code(error_code),
        client_request_id=(client_request_id or "")[:120] or None,
    )
    db.add(row)
    if commit:
        db.commit()
        db.refresh(row)
    else:
        db.flush()
    return row


def list_operations(
    db: Session, *, post_id: uuid.UUID, limit: int = 50
) -> list[BlogAiOperation]:
    return list(
        db.scalars(
            select(BlogAiOperation)
            .where(BlogAiOperation.post_id == post_id)
            .order_by(BlogAiOperation.created_at.desc())
            .limit(limit)
        ).all()
    )


def serialize_operation(row: BlogAiOperation) -> dict[str, Any]:
    return {
        "id": row.id,
        "post_id": row.post_id,
        "actor_user_id": row.actor_user_id,
        "operation": row.operation,
        "feature_key": row.feature_key,
        "provider": row.provider,
        "model_name": row.model_name,
        "success": row.success,
        "duration_ms": row.duration_ms,
        "tokens_in": row.tokens_in,
        "tokens_out": row.tokens_out,
        "error_code": row.error_code,
        "client_request_id": row.client_request_id,
        "created_at": row.created_at,
    }
