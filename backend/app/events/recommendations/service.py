"""Personalized event recommendations for fans."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.events.models import Event
from app.events.recommendations import constants as C
from app.events.recommendations.affinity import event_category_slug
from app.events.recommendations.engine import build_affinity, rank_event_recommendations
from app.events.recommendations.models import (
    EventRecommendationCategoryHide,
    EventRecommendationDismissal,
    EventRecommendationFeedback,
    EventRecommendationHostHide,
    EventRecommendationImpression,
)
from app.events.recommendations.settings import load_event_recommendation_config
from app.hosts.models import Host
from app.users.models import User


def _now() -> datetime:
    return datetime.now(UTC)


def _own_host_ids(db: Session, user_id: UUID) -> set[UUID]:
    return set(db.scalars(select(Host.id).where(Host.user_id == user_id)).all())


def _record_feedback(
    db: Session,
    *,
    user_id: UUID,
    event_id: UUID,
    action: str,
    context: dict | None = None,
) -> None:
    if action not in C.FEEDBACK_ACTIONS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid feedback action")
    db.add(
        EventRecommendationFeedback(
            user_id=user_id,
            event_id=event_id,
            action=action,
            context=context,
        )
    )


def _event_context(db: Session, event_id: UUID) -> dict:
    event = db.get(Event, event_id)
    if event is None:
        return {}
    slugs = []
    cat = event_category_slug(event)
    if cat:
        slugs.append(cat)
    city = event.city.strip().lower() if event.city else None
    ctx: dict = {"category_slugs": slugs}
    if event.host_id:
        ctx["host_id"] = str(event.host_id)
    if city:
        ctx["city"] = city
    return ctx


def list_recommendations(
    db: Session,
    user: User,
    *,
    limit: int = C.RECOMMENDATIONS_CAP,
    cursor: str | None = None,
    city: str | None = None,
    area: str | None = None,
    category: str | None = None,
    date_range: str | None = None,
    mode: str = C.DEFAULT_MODE,
    exclude_event_id: UUID | None = None,
    context_event_id: UUID | None = None,
    host_id: UUID | None = None,
) -> dict:
    config = load_event_recommendation_config(db)
    limit = min(max(1, limit), 50)
    page = 1
    if cursor:
        try:
            page = max(1, int(cursor))
        except ValueError:
            page = 1

    mode = mode if mode in C.MODES else C.DEFAULT_MODE
    if not config.enabled:
        return {
            "events": [],
            "next_cursor": None,
            "mode": mode,
            "generated_at": _now(),
            "empty_title": "Recommendations paused",
            "empty_description": "Event recommendations are temporarily unavailable.",
        }

    affinity = build_affinity(db, user_id=user.id, own_host_ids=_own_host_ids(db, user.id))
    _ = area, date_range, host_id

    exclude_ids: set[UUID] = set()
    if exclude_event_id:
        exclude_ids.add(exclude_event_id)
    if context_event_id:
        exclude_ids.add(context_event_id)
        ctx_row = db.get(Event, context_event_id)
        if ctx_row is not None:
            from app.events.service import get_event_by_id

            ctx_row = get_event_by_id(db, context_event_id) or ctx_row
            if not category:
                cat_slug = event_category_slug(ctx_row)
                if cat_slug:
                    category = cat_slug
            if not city and ctx_row.city:
                city = ctx_row.city.strip().lower().replace(" ", "-")

    items, total, _ = rank_event_recommendations(
        db,
        user_id=user.id,
        affinity=affinity,
        config=config,
        limit=limit,
        page=page,
        mode=mode,
        city=city,
        category=category,
        exclude_event_ids=exclude_ids,
    )
    next_cursor = str(page + 1) if page * limit < total else None

    empty_title = None
    empty_description = None
    if total == 0:
        empty_title = "No event matches yet"
        empty_description = (
            "Buy tickets, follow hosts, or set your city in Connect settings "
            "and Pàdéyá will surface nights that fit you."
        )

    return {
        "events": items,
        "next_cursor": next_cursor,
        "mode": mode,
        "generated_at": _now(),
        "empty_title": empty_title,
        "empty_description": empty_description,
    }


def debug_recommendations(db: Session, *, target_user_id: UUID) -> dict:
    config = load_event_recommendation_config(db)
    affinity = build_affinity(
        db, user_id=target_user_id, own_host_ids=_own_host_ids(db, target_user_id)
    )
    _, total, dbg = rank_event_recommendations(
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
                "host": config.weight_host,
                "location": config.weight_location,
                "social": config.weight_social,
                "trust": config.weight_trust,
                "freshness": config.weight_freshness,
            },
            "max_per_host": config.max_per_host,
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
    event_id: UUID,
    dismiss_days: int,
    reason: str | None = None,
) -> None:
    expires = _now() + timedelta(days=dismiss_days)
    row = db.scalar(
        select(EventRecommendationDismissal).where(
            EventRecommendationDismissal.user_id == user_id,
            EventRecommendationDismissal.event_id == event_id,
        )
    )
    if row is None:
        db.add(
            EventRecommendationDismissal(
                user_id=user_id,
                event_id=event_id,
                reason=reason,
                dismissed_at=_now(),
                expires_at=expires,
            )
        )
    else:
        row.reason = reason or row.reason
        row.dismissed_at = _now()
        row.expires_at = expires


def submit_feedback(
    db: Session,
    user: User,
    event_id: UUID,
    *,
    action: str,
    category_slug: str | None = None,
) -> dict:
    config = load_event_recommendation_config(db)
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Event not found")

    ctx = _event_context(db, event_id)

    if action == C.FEEDBACK_DISMISS:
        _upsert_dismissal(
            db,
            user_id=user.id,
            event_id=event_id,
            dismiss_days=config.dismiss_days,
            reason="dismissed",
        )
    elif action == C.FEEDBACK_NOT_INTERESTED:
        _upsert_dismissal(
            db,
            user_id=user.id,
            event_id=event_id,
            dismiss_days=config.dismiss_days,
            reason="not_interested",
        )
    elif action == C.FEEDBACK_HIDE_CATEGORY:
        slug = (category_slug or (ctx.get("category_slugs") or [None])[0] or "").strip().lower()
        if not slug:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="category_slug required")
        expires = _now() + timedelta(days=config.category_hide_days)
        row = db.scalar(
            select(EventRecommendationCategoryHide).where(
                EventRecommendationCategoryHide.user_id == user.id,
                EventRecommendationCategoryHide.category_slug == slug,
            )
        )
        if row is None:
            db.add(
                EventRecommendationCategoryHide(
                    user_id=user.id,
                    category_slug=slug,
                    hidden_at=_now(),
                    expires_at=expires,
                )
            )
        else:
            row.hidden_at = _now()
            row.expires_at = expires
    elif action == C.FEEDBACK_HIDE_HOST:
        if not event.host_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Event has no host")
        expires = _now() + timedelta(days=config.host_hide_days)
        row = db.scalar(
            select(EventRecommendationHostHide).where(
                EventRecommendationHostHide.user_id == user.id,
                EventRecommendationHostHide.host_id == event.host_id,
            )
        )
        if row is None:
            db.add(
                EventRecommendationHostHide(
                    user_id=user.id,
                    host_id=event.host_id,
                    hidden_at=_now(),
                    expires_at=expires,
                )
            )
        else:
            row.hidden_at = _now()
            row.expires_at = expires

    _record_feedback(db, user_id=user.id, event_id=event_id, action=action, context=ctx)
    db.commit()
    return {"ok": True, "event_id": event_id}


def record_impressions(
    db: Session,
    user: User,
    items: list[dict],
) -> dict:
    for row in items[:25]:
        event_id = row.get("event_id")
        if not event_id:
            continue
        if isinstance(event_id, str):
            event_id = UUID(event_id)
        surface = str(row.get("surface") or "unknown")[:32]
        position = row.get("position")
        score = row.get("recommendation_score")
        codes = row.get("reason_codes")
        db.add(
            EventRecommendationImpression(
                user_id=user.id,
                event_id=event_id,
                surface=surface,
                position=int(position) if position is not None else None,
                recommendation_score=int(score) if score is not None else None,
                reason_codes=codes if isinstance(codes, list) else None,
            )
        )
    db.commit()
    return {"ok": True, "recorded": min(len(items), 25)}
