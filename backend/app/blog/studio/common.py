"""Shared helpers for Blog AI Studio generation."""

from __future__ import annotations

import logging
import re
import time
import uuid
from typing import Any, Callable, TypeVar

from fastapi import HTTPException
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.ai.blog_context import assert_blog_ai_permission
from app.ai.feature_routing import complete_for_feature
from app.blog.studio import operations as ops
from app.blog.studio import rate_limit as rl
from app.blog.studio.json_parse import parse_model, repair_user_prompt
from app.blog.studio.schemas import BlogContentBrief
from app.blog.studio.voice import build_system_prompt
from app.users.models import User

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def _brief(payload_brief: BlogContentBrief | None) -> BlogContentBrief:
    return payload_brief or BlogContentBrief()


def _tone(brief: BlogContentBrief) -> tuple[str | None, str | None]:
    return brief.tone, brief.custom_tone


def _complete(
    db: Session,
    *,
    feature_key: str,
    system_prompt: str,
    user_prompt: str,
    force_template: bool = False,
):
    return complete_for_feature(
        db,
        feature_key=feature_key,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        force_template_only=force_template,
    )


def _parse_with_repair(
    db: Session,
    *,
    feature_key: str,
    system_prompt: str,
    user_prompt: str,
    model: type[T],
    force_template: bool,
    fallback: Callable[[], T],
) -> tuple[T, str | None, Any]:
    routed = _complete(
        db,
        feature_key=feature_key,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        force_template=force_template,
    )
    text = routed.result.text or ""
    try:
        return parse_model(text, model), routed.result.provider, routed
    except (ValueError, ValidationError):
        pass
    routed2 = _complete(
        db,
        feature_key=feature_key,
        system_prompt=system_prompt,
        user_prompt=repair_user_prompt(user_prompt),
        force_template=True,
    )
    try:
        return parse_model(routed2.result.text or "", model), routed2.result.provider, routed2
    except (ValueError, ValidationError):
        logger.info("blog_studio_parse_fallback feature=%s", feature_key)
        return fallback(), "template", routed2


def _begin(user: User, client_request_id: str | None) -> Any | None:
    assert_blog_ai_permission(user)
    cached = rl.get_idempotent(str(user.id), client_request_id)
    if cached is not None:
        return cached
    rl.check_studio_rate_limit(str(user.id))
    rl.acquire_generation_slot(str(user.id))
    return None


def _finish(
    db: Session,
    *,
    user: User,
    operation: str,
    feature_key: str,
    started: float,
    client_request_id: str | None,
    post_id: uuid.UUID | None,
    success: bool,
    provider: str | None = None,
    model_name: str | None = None,
    tokens_in: int | None = None,
    tokens_out: int | None = None,
    error_code: str | None = None,
    payload: Any = None,
) -> None:
    try:
        ops.log_operation(
            db,
            operation=operation,
            actor=user,
            post_id=post_id,
            feature_key=feature_key,
            provider=provider,
            model_name=model_name,
            success=success,
            duration_ms=int((time.monotonic() - started) * 1000),
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            error_code=error_code,
            client_request_id=client_request_id,
            commit=True,
        )
        if success and payload is not None:
            rl.store_idempotent(str(user.id), client_request_id, payload)
    finally:
        rl.release_generation_slot(str(user.id))


def _slug_guess(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
    return slug[:200] or "post"
