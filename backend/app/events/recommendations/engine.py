"""Rank published events for a fan."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.events.recommendations import constants as C
from app.events.recommendations.affinity import (
    FanEventAffinity,
    event_category_slug,
    event_city_label,
    load_fan_event_affinity,
)
from app.events.recommendations.pool import list_recommendation_candidates
from app.events.recommendations.scoring import EventScoreResult, score_event_for_fan
from app.events.recommendations.settings import EventRecommendationConfig
from app.events.schemas import EventPublic
from app.events.service import serialize_event


@dataclass
class RankDebug:
    candidate_count: int = 0
    excluded: dict[str, int] = field(default_factory=dict)
    top: list[dict] = field(default_factory=list)

    def bump(self, reason: str) -> None:
        self.excluded[reason] = self.excluded.get(reason, 0) + 1


def _apply_diversity(
    items: list[tuple[int, dict, EventScoreResult]],
    *,
    max_per_host: int,
    max_per_category: int,
    max_per_city: int,
) -> list[tuple[int, dict, EventScoreResult]]:
    host_counts: dict[UUID, int] = {}
    cat_counts: dict[str, int] = {}
    city_counts: dict[str, int] = {}
    out: list[tuple[int, dict, EventScoreResult]] = []
    for score, payload, result in items:
        event = payload["_event"]
        host_id = event.host_id
        cat = event_category_slug(event) or ""
        city = event_city_label(event) or ""
        if host_id and host_counts.get(host_id, 0) >= max_per_host:
            continue
        if cat and cat_counts.get(cat, 0) >= max_per_category:
            continue
        if city and city_counts.get(city, 0) >= max_per_city:
            continue
        out.append((score, payload, result))
        if host_id:
            host_counts[host_id] = host_counts.get(host_id, 0) + 1
        if cat:
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
        if city:
            city_counts[city] = city_counts.get(city, 0) + 1
    return out


def rank_event_recommendations(
    db: Session,
    *,
    user_id: UUID,
    affinity: FanEventAffinity,
    config: EventRecommendationConfig,
    limit: int,
    page: int,
    mode: str = C.DEFAULT_MODE,
    city: str | None = None,
    category: str | None = None,
    debug: bool = False,
    exclude_event_ids: set[UUID] | None = None,
) -> tuple[list[dict], int, RankDebug | None]:
    dbg = RankDebug() if debug else None
    if not config.enabled:
        return [], 0, dbg

    pool = list_recommendation_candidates(
        db, limit=config.pool_size, city=city, category=category
    )
    if dbg:
        dbg.candidate_count = len(pool)

    exclude = exclude_event_ids or set()

    scored: list[tuple[int, dict, EventScoreResult]] = []
    for event in pool:
        if event.id in exclude:
            if dbg:
                dbg.bump("excluded_context")
            continue
        result = score_event_for_fan(
            db,
            user_id=user_id,
            event=event,
            affinity=affinity,
            config=config,
            mode=mode,
        )
        if not result.show:
            if dbg:
                bd = result.breakdown
                if bd.get("_exclude_own_host"):
                    dbg.bump("own_host")
                elif bd.get("_exclude_already_purchased"):
                    dbg.bump("already_purchased")
                elif bd.get("_exclude_dismissed"):
                    dbg.bump("active_dismiss")
                elif bd.get("_exclude_category_hidden") or bd.get("_exclude_host_hidden"):
                    dbg.bump("hidden")
                elif result.score < config.min_score:
                    dbg.bump("below_min_score")
                else:
                    dbg.bump("no_safe_reason")
            continue

        public = EventPublic.model_validate(serialize_event(event, access="public"))
        payload = {
            "event": public,
            "score": result.score,
            "reasons": result.reasons,
            "flags": result.flags,
            "breakdown": result.breakdown if debug else None,
            "_event": event,
        }
        scored.append((result.score, payload, result))

    scored.sort(key=lambda t: t[0], reverse=True)
    scored = _apply_diversity(
        scored,
        max_per_host=config.max_per_host,
        max_per_category=config.max_per_category,
        max_per_city=config.max_per_city,
    )

    total = len(scored)
    start = (page - 1) * limit
    page_slice = scored[start : start + limit]

    items: list[dict] = []
    for score, payload, result in page_slice:
        clean = {k: v for k, v in payload.items() if k != "_event"}
        items.append(clean)
        if dbg:
            dbg.top.append(
                {
                    "event_id": str(payload["event"].id),
                    "slug": payload["event"].slug,
                    "score": score,
                    "reasons": result.reasons,
                    "breakdown": result.breakdown,
                    "flags": result.flags,
                }
            )

    return items, total, dbg


def build_affinity(
    db: Session,
    *,
    user_id: UUID,
    own_host_ids: set[UUID],
) -> FanEventAffinity:
    return load_fan_event_affinity(db, user_id=user_id, own_host_ids=own_host_ids)
