"""Personalized host recommendations for fans."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.hosts.models import Host
from app.hosts.recommendations import constants as C
from app.hosts.recommendations.engine import build_affinity, rank_host_recommendations
from app.hosts.recommendations.models import (
    HostRecommendationCategoryHide,
    HostRecommendationDismissal,
    HostRecommendationFeedback,
    HostRecommendationImpression,
)
from app.hosts.recommendations.settings import load_host_recommendation_config
from app.legacy.models import HostLegacyPage
from app.users.models import User


def _now() -> datetime:
    return datetime.now(UTC)


def _own_host_ids(db: Session, user_id: UUID) -> set[UUID]:
    return set(
        db.scalars(select(Host.id).where(Host.user_id == user_id)).all()
    )


def _host_category_slugs(db: Session, host_id: UUID) -> list[str]:
    page = db.scalar(select(HostLegacyPage).where(HostLegacyPage.host_id == host_id))
    slugs: list[str] = []
    if page and page.primary_category_slug:
        slugs.append(page.primary_category_slug.lower())
    if page and page.host_type_slug:
        slugs.append(page.host_type_slug.lower())
    return slugs


def _record_feedback(
    db: Session,
    *,
    user_id: UUID,
    host_id: UUID,
    action: str,
    context: dict | None = None,
) -> None:
    if action not in C.FEEDBACK_ACTIONS:
        return
    db.add(
        HostRecommendationFeedback(
            user_id=user_id,
            host_id=host_id,
            action=action,
            context=context,
        )
    )


def list_recommendations(
    db: Session,
    user: User,
    *,
    limit: int = C.RECOMMENDATIONS_CAP,
    page: int = 1,
) -> dict:
    config = load_host_recommendation_config(db)
    limit = min(max(1, limit), 50)
    page = max(1, page)

    if not config.enabled:
        return {
            "items": [],
            "page": page,
            "limit": limit,
            "total": 0,
            "next_cursor": None,
            "empty_title": "Recommendations paused",
            "empty_description": "Host recommendations are temporarily unavailable.",
        }

    affinity = build_affinity(db, user_id=user.id, own_host_ids=_own_host_ids(db, user.id))
    items, total, _ = rank_host_recommendations(
        db,
        user_id=user.id,
        affinity=affinity,
        config=config,
        limit=limit,
        page=page,
    )
    next_cursor = str(page + 1) if page * limit < total else None

    empty_title = None
    empty_description = None
    if total == 0:
        empty_title = "No host matches yet"
        empty_description = (
            "Follow hosts, buy tickets, or save your city in Connect settings "
            "and Pàdéyá will surface Legacy hosts that fit your nights."
        )

    return {
        "items": items,
        "page": page,
        "limit": limit,
        "total": total,
        "next_cursor": next_cursor,
        "empty_title": empty_title,
        "empty_description": empty_description,
    }


def debug_recommendations(db: Session, *, target_user_id: UUID) -> dict:
    config = load_host_recommendation_config(db)
    affinity = build_affinity(
        db, user_id=target_user_id, own_host_ids=_own_host_ids(db, target_user_id)
    )
    _, total, dbg = rank_host_recommendations(
        db,
        user_id=target_user_id,
        affinity=affinity,
        config=config,
        limit=20,
        page=1,
        debug=True,
    )
    return {
        "user_id": target_user_id,
        "enabled": config.enabled,
        "config": {
            "min_score": config.min_score,
            "dismiss_days": config.dismiss_days,
            "pool_size": config.pool_size,
            "weights": {
                "interest": config.weight_interest,
                "location": config.weight_location,
                "social": config.weight_social,
                "trust": config.weight_trust,
                "freshness": config.weight_freshness,
            },
            "max_per_category": config.max_per_category,
            "max_per_city": config.max_per_city,
            "impression_penalty_threshold": config.impression_penalty_threshold,
            "cold_start_mode": config.cold_start_mode,
        },
        "candidate_count": dbg.candidate_count if dbg else 0,
        "excluded_by_reason": dbg.excluded if dbg else {},
        "shown_count": total,
        "top": dbg.top if dbg else [],
    }


def _upsert_dismissal(
    db: Session,
    *,
    user_id: UUID,
    host_id: UUID,
    dismiss_days: int,
    reason: str | None = None,
) -> None:
    expires = _now() + timedelta(days=dismiss_days)
    row = db.scalar(
        select(HostRecommendationDismissal).where(
            HostRecommendationDismissal.user_id == user_id,
            HostRecommendationDismissal.host_id == host_id,
        )
    )
    if row is None:
        db.add(
            HostRecommendationDismissal(
                user_id=user_id,
                host_id=host_id,
                reason=reason,
                dismissed_at=_now(),
                expires_at=expires,
            )
        )
    else:
        row.reason = reason or row.reason
        row.dismissed_at = _now()
        row.expires_at = expires


def dismiss_recommendation(
    db: Session,
    user: User,
    host_id: UUID,
    *,
    reason: str | None = None,
) -> dict:
    config = load_host_recommendation_config(db)
    host = db.get(Host, host_id)
    if host is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Host not found")

    _upsert_dismissal(
        db,
        user_id=user.id,
        host_id=host_id,
        dismiss_days=config.dismiss_days,
        reason=reason,
    )
    _record_feedback(
        db,
        user_id=user.id,
        host_id=host_id,
        action=C.FEEDBACK_DISMISS,
        context={"reason": reason} if reason else None,
    )
    db.commit()
    return {"ok": True, "host_id": host_id}


def not_interested(
    db: Session,
    user: User,
    host_id: UUID,
) -> dict:
    """Dismiss host and penalize similar categories/host types."""
    config = load_host_recommendation_config(db)
    host = db.get(Host, host_id)
    if host is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Host not found")

    slugs = _host_category_slugs(db, host_id)
    _upsert_dismissal(
        db,
        user_id=user.id,
        host_id=host_id,
        dismiss_days=config.dismiss_days,
        reason="not_interested",
    )
    _record_feedback(
        db,
        user_id=user.id,
        host_id=host_id,
        action=C.FEEDBACK_DISMISS,
        context={"reason": "not_interested"},
    )
    _record_feedback(
        db,
        user_id=user.id,
        host_id=host_id,
        action=C.FEEDBACK_NOT_INTERESTED,
        context={"category_slugs": slugs} if slugs else None,
    )
    db.commit()
    return {"ok": True, "host_id": host_id}


def hide_category(
    db: Session,
    user: User,
    category_slug: str,
) -> dict:
    config = load_host_recommendation_config(db)
    slug = category_slug.strip().lower()
    if not slug:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="category_slug required")

    expires = _now() + timedelta(days=config.category_hide_days)
    row = db.scalar(
        select(HostRecommendationCategoryHide).where(
            HostRecommendationCategoryHide.user_id == user.id,
            HostRecommendationCategoryHide.category_slug == slug,
        )
    )
    if row is None:
        db.add(
            HostRecommendationCategoryHide(
                user_id=user.id,
                category_slug=slug,
                hidden_at=_now(),
                expires_at=expires,
            )
        )
    else:
        row.hidden_at = _now()
        row.expires_at = expires

    db.commit()
    return {"ok": True, "category_slug": slug}


def more_like_this(db: Session, user: User, host_id: UUID) -> dict:
    host = db.get(Host, host_id)
    if host is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Host not found")

    _record_feedback(
        db,
        user_id=user.id,
        host_id=host_id,
        action=C.FEEDBACK_MORE_LIKE_THIS,
    )
    db.commit()
    return {"ok": True, "host_id": host_id}


def record_click(db: Session, user: User, host_id: UUID) -> dict:
    host = db.get(Host, host_id)
    if host is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Host not found")
    _record_feedback(db, user_id=user.id, host_id=host_id, action=C.FEEDBACK_CLICK)
    db.commit()
    return {"ok": True, "host_id": host_id}


def record_follow_feedback(db: Session, user: User, host_id: UUID) -> dict:
    host = db.get(Host, host_id)
    if host is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Host not found")
    _record_feedback(db, user_id=user.id, host_id=host_id, action=C.FEEDBACK_FOLLOW)
    db.commit()
    return {"ok": True, "host_id": host_id}


def record_impressions(
    db: Session,
    user: User,
    items: list[dict],
) -> dict:
    for row in items[:25]:
        host_id = row.get("host_id")
        if not host_id:
            continue
        if isinstance(host_id, str):
            host_id = UUID(host_id)
        surface = str(row.get("surface") or "unknown")[:32]
        position = row.get("position")
        score = row.get("recommendation_score")
        codes = row.get("reason_codes")
        db.add(
            HostRecommendationImpression(
                user_id=user.id,
                host_id=host_id,
                surface=surface,
                position=int(position) if position is not None else None,
                recommendation_score=int(score) if score is not None else None,
                reason_codes=codes if isinstance(codes, list) else None,
            )
        )
    db.commit()
    return {"ok": True, "recorded": min(len(items), 25)}
