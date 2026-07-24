"""Per-feature enable checks (env + DB routes/configs)."""

from __future__ import annotations

import os

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.ai.constants import DEFAULT_FEATURE_ENABLED, FEATURE_CANONICAL
from app.core.config import get_settings


def canonicalize_feature(feature: str) -> str:
    key = feature.strip()
    return FEATURE_CANONICAL.get(key, key)


def _disabled_from_env() -> set[str]:
    raw = os.environ.get("AI_DISABLED_FEATURES", "") or ""
    return {part.strip() for part in raw.split(",") if part.strip()}


def is_feature_enabled(feature: str, db: Session | None = None) -> bool:
    canonical = canonicalize_feature(feature)
    disabled = _disabled_from_env()
    if canonical in disabled or feature.strip() in disabled:
        return False

    if db is not None:
        from app.ai.feature_routing import route_enabled

        return route_enabled(db, canonical)

    if canonical in DEFAULT_FEATURE_ENABLED:
        return bool(DEFAULT_FEATURE_ENABLED[canonical])
    return False


def assert_feature_enabled(feature: str, db: Session | None = None) -> str:
    canonical = canonicalize_feature(feature)
    if not is_feature_enabled(canonical, db=db) and not is_feature_enabled(
        feature, db=db
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This AI feature is disabled.",
        )
    return canonical


def assert_ai_globally_available() -> None:
    if (os.environ.get("AI_KILL_SWITCH") or "").strip() in {"1", "true", "TRUE", "yes"}:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI is unavailable right now. You can keep editing manually.",
        )
    _ = get_settings()


def feature_requires_human_review(feature: str, db: Session | None = None) -> bool:
    from app.ai.constants import HIGH_RISK_HUMAN_REVIEW_LOCKED
    from app.ai.models import AIFeatureRoute
    from sqlalchemy import select

    canonical = canonicalize_feature(feature)
    if canonical in HIGH_RISK_HUMAN_REVIEW_LOCKED:
        return True
    if db is None:
        return True
    row = db.scalar(
        select(AIFeatureRoute).where(AIFeatureRoute.feature_key == canonical)
    )
    if row is None:
        return True
    return bool(row.requires_human_review)
