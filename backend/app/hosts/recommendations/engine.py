"""Rank discoverable hosts for a fan — diversity + optional debug."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy.orm import Session

from app.hosts.recommendations.affinity import (
    FanHostAffinity,
    host_category_slugs,
    host_city_label,
    load_fan_host_affinity,
)
from app.hosts.recommendations.constants import COLD_START_OFF
from app.hosts.recommendations import constants as C
from app.hosts.recommendations.scoring import HostScoreResult, score_host_for_fan
from app.hosts.recommendations.settings import HostRecommendationConfig
from app.legacy.discover import list_discover_hosts
from app.legacy.schemas import HostDiscoveryPublic


@dataclass
class RankDebug:
    candidate_count: int = 0
    excluded: dict[str, int] = field(default_factory=dict)
    top: list[dict] = field(default_factory=list)

    def bump(self, reason: str) -> None:
        self.excluded[reason] = self.excluded.get(reason, 0) + 1


def _apply_diversity(
    items: list[tuple[int, dict, HostScoreResult]],
    *,
    max_per_category: int,
    max_per_city: int,
) -> list[tuple[int, dict, HostScoreResult]]:
    if max_per_category <= 0 and max_per_city <= 0:
        return items
    cat_counts: dict[str, int] = {}
    city_counts: dict[str, int] = {}
    out: list[tuple[int, dict, HostScoreResult]] = []
    for score, payload, result in items:
        card = payload.get("_card") or {}
        cats = host_category_slugs(card)
        city = host_city_label(card) or ""
        blocked = False
        for slug in cats:
            if cat_counts.get(slug, 0) >= max_per_category:
                blocked = True
                break
        if city and city_counts.get(city, 0) >= max_per_city:
            blocked = True
        if blocked:
            continue
        out.append((score, payload, result))
        for slug in cats:
            cat_counts[slug] = cat_counts.get(slug, 0) + 1
        if city:
            city_counts[city] = city_counts.get(city, 0) + 1
    return out


def rank_host_recommendations(
    db: Session,
    *,
    user_id: UUID,
    affinity: FanHostAffinity,
    config: HostRecommendationConfig,
    limit: int,
    page: int,
    debug: bool = False,
) -> tuple[list[dict], int, RankDebug | None]:
    dbg = RankDebug() if debug else None
    if not config.enabled:
        return [], 0, dbg

    pool = list_discover_hosts(db, limit=config.pool_size)
    if dbg:
        dbg.candidate_count = len(pool)

    scored: list[tuple[int, dict, HostScoreResult]] = []
    for row in pool:
        host_id = row["host_id"]
        if not isinstance(host_id, UUID):
            host_id = UUID(str(host_id))

        result = score_host_for_fan(
            db,
            user_id=user_id,
            card=row,
            affinity=affinity,
            config=config,
        )

        if not result.show:
            if dbg:
                if host_id in affinity.own_host_ids:
                    dbg.bump("own_host")
                elif host_id in affinity.followed_host_ids:
                    dbg.bump("already_followed")
                elif result.breakdown.get("_exclude_dismissed"):
                    dbg.bump("active_dismiss")
                elif result.breakdown.get("_exclude_category_hidden"):
                    dbg.bump("category_hidden")
                elif result.score < config.min_score:
                    dbg.bump("below_min_score")
                else:
                    dbg.bump("no_safe_reason")
            continue

        host_public = HostDiscoveryPublic.model_validate(row)
        payload = {
            "host": host_public,
            "score": result.score,
            "reasons": result.reasons,
            "recommendation_label": result.recommendation_label,
            "relationship": result.relationship,
            "breakdown": result.breakdown if debug else None,
            "_card": row,
        }
        scored.append((result.score, payload, result))

    scored.sort(key=lambda t: t[0], reverse=True)
    scored = _apply_diversity(
        scored,
        max_per_category=config.max_per_category,
        max_per_city=config.max_per_city,
    )

    total = len(scored)
    start = (page - 1) * limit
    page_slice = scored[start : start + limit]

    items: list[dict] = []
    for score, payload, result in page_slice:
        clean = {k: v for k, v in payload.items() if k != "_card"}
        items.append(clean)
        if dbg:
            dbg.top.append(
                {
                    "host_id": str(payload["host"].host_id),
                    "username": payload["host"].username,
                    "score": score,
                    "reasons": result.reasons,
                    "breakdown": result.breakdown,
                }
            )

    return items, total, dbg


def build_affinity(
    db: Session,
    *,
    user_id: UUID,
    own_host_ids: set[UUID],
) -> FanHostAffinity:
    from sqlalchemy import select

    from app.hosts.recommendations.models import HostRecommendationFeedback

    more_like_ids = set(
        db.scalars(
            select(HostRecommendationFeedback.host_id).where(
                HostRecommendationFeedback.user_id == user_id,
                HostRecommendationFeedback.action == C.FEEDBACK_MORE_LIKE_THIS,
            ).limit(30)
        ).all()
    )
    return load_fan_host_affinity(
        db,
        user_id=user_id,
        own_host_ids=own_host_ids,
        more_like_host_ids=more_like_ids,
    )
