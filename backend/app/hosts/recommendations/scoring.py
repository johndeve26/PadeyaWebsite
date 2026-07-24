"""Score a discoverable host for a fan using public-safe affinity signals."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.events.geo import haversine_km, parse_coord
from app.events.maps import city_centroid
from app.hosts.recommendations import constants as C
from app.hosts.recommendations.affinity import (
    FanHostAffinity,
    host_category_slugs,
    host_city_label,
    host_has_upcoming_soon,
)
from app.hosts.recommendations.models import (
    HostRecommendationDismissal,
    HostRecommendationFeedback,
    HostRecommendationImpression,
)
from app.hosts.recommendations.settings import HostRecommendationConfig


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _w(value: int, weight: float) -> int:
    return int(round(value * max(0.0, weight)))


def _label(code: str, fallback: str | None = None) -> str:
    return C.REASON_LABELS.get(code, fallback or code.replace("_", " ").title())


@dataclass
class HostScoreResult:
    score: int
    reasons: list[dict] = field(default_factory=list)
    recommendation_label: str | None = None
    show: bool = False
    breakdown: dict[str, int] = field(default_factory=dict)
    relationship: str = "none"


def recommendation_label(score: int) -> str | None:
    if score >= C.SCORE_LABEL_STRONG:
        return C.LABEL_STRONG
    if score >= C.SCORE_LABEL_GOOD:
        return C.LABEL_GOOD
    if score >= C.SCORE_MIN_SHOW:
        return C.LABEL_SIMILAR
    return None


def _dismissal_state(
    db: Session, user_id: UUID, host_id: UUID, *, dismiss_days: int
) -> dict:
    row = db.scalar(
        select(HostRecommendationDismissal).where(
            HostRecommendationDismissal.user_id == user_id,
            HostRecommendationDismissal.host_id == host_id,
        )
    )
    if row is None:
        return {"exclude": False, "penalty": False}
    expires = _aware(row.expires_at)
    if expires is not None and expires > _now():
        return {"exclude": True, "penalty": False}
    return {"exclude": False, "penalty": True}


def _impression_engagement(db: Session, user_id: UUID, host_id: UUID) -> dict:
    impressions = int(
        db.scalar(
            select(func.count())
            .select_from(HostRecommendationImpression)
            .where(
                HostRecommendationImpression.user_id == user_id,
                HostRecommendationImpression.host_id == host_id,
            )
        )
        or 0
    )
    engaged = int(
        db.scalar(
            select(func.count())
            .select_from(HostRecommendationFeedback)
            .where(
                HostRecommendationFeedback.user_id == user_id,
                HostRecommendationFeedback.host_id == host_id,
                HostRecommendationFeedback.action.in_(
                    (
                        C.FEEDBACK_CLICK,
                        C.FEEDBACK_MORE_LIKE_THIS,
                        C.FEEDBACK_FOLLOW,
                    )
                ),
            )
        )
        or 0
    )
    return {"impressions": impressions, "engaged": engaged}


def _feedback_boost(
    db: Session,
    user_id: UUID,
    affinity: FanHostAffinity,
    card: dict,
    config: HostRecommendationConfig,
) -> dict:
    out = {"boost_more_like": False, "boost_click": False, "ignored": False}
    host_cats = host_category_slugs(card)
    city = host_city_label(card)

    if affinity.more_like_category_slugs and host_cats & affinity.more_like_category_slugs:
        out["boost_more_like"] = True
    if city and city in affinity.more_like_city_labels:
        out["boost_more_like"] = True

    host_id = card["host_id"]
    if isinstance(host_id, str):
        host_id = UUID(host_id)
    stats = _impression_engagement(db, user_id, host_id)
    if (
        stats["impressions"] >= config.impression_penalty_threshold
        and stats["engaged"] == 0
    ):
        out["ignored"] = True
    return out


def _distance_km(affinity: FanHostAffinity, card: dict) -> float | None:
    if affinity.location_lat is None or affinity.location_lng is None:
        return None
    city = host_city_label(card)
    if not city:
        return None
    centroid = city_centroid(city, affinity.location_area)
    if not centroid:
        return None
    plat = parse_coord(centroid[0])
    plng = parse_coord(centroid[1])
    if plat is None or plng is None:
        return None
    return haversine_km(affinity.location_lat, affinity.location_lng, plat, plng)


def score_host_for_fan(
    db: Session,
    *,
    user_id: UUID,
    card: dict,
    affinity: FanHostAffinity,
    config: HostRecommendationConfig | None = None,
) -> HostScoreResult:
    cfg = config or HostRecommendationConfig()
    host_id = card["host_id"]
    if isinstance(host_id, str):
        host_id = UUID(host_id)

    if host_id in affinity.own_host_ids:
        return HostScoreResult(score=0, show=False, breakdown={"_exclude_own": 1})

    if host_id in affinity.followed_host_ids:
        return HostScoreResult(score=0, show=False, breakdown={"_exclude_followed": 1})

    host_cats = host_category_slugs(card)
    if host_cats & affinity.hidden_category_slugs:
        return HostScoreResult(
            score=0,
            show=False,
            breakdown={"_exclude_category_hidden": 1},
        )

    dismiss = _dismissal_state(
        db, user_id, host_id, dismiss_days=cfg.dismiss_days
    )
    if dismiss["exclude"]:
        return HostScoreResult(
            score=0,
            show=False,
            breakdown={"_exclude_dismissed": 1},
        )

    breakdown: dict[str, int] = {}
    score = 0
    reasons: list[dict] = []
    relationship = "none"
    wi, wl, ws, wt, wf = (
        cfg.weight_interest,
        cfg.weight_location,
        cfg.weight_social,
        cfg.weight_trust,
        cfg.weight_freshness,
    )

    if host_id in affinity.attended_host_ids:
        pts = _w(C.SCORE_ATTENDED_HOST, wi)
        breakdown["attended"] = pts
        score += pts
        relationship = "attended"
        reasons.append({"code": C.REASON_ATTENDED, "label": _label(C.REASON_ATTENDED)})

    if host_id in affinity.ticketed_host_ids and host_id not in affinity.attended_host_ids:
        pts = _w(C.SCORE_TICKETED_HOST, wi)
        breakdown["ticketed"] = pts
        score += pts
        if relationship == "none":
            relationship = "ticketed"
        if not any(r["code"] == C.REASON_ATTENDED for r in reasons):
            reasons.append({"code": C.REASON_TICKETED, "label": _label(C.REASON_TICKETED)})

    similar_followed = host_cats & affinity.followed_category_slugs
    if similar_followed:
        raw = min(len(similar_followed) * C.SCORE_SIMILAR_TO_FOLLOWED, C.SCORE_SIMILAR_TO_FOLLOWED_MAX)
        pts = _w(raw, wi)
        breakdown["similar_followed"] = pts
        score += pts
        reasons.append(
            {"code": C.REASON_SIMILAR_FOLLOWED, "label": _label(C.REASON_SIMILAR_FOLLOWED)}
        )

    network_n = int(affinity.network_host_follow_counts.get(host_id) or 0)
    if network_n > 0:
        raw = min(network_n * C.SCORE_NETWORK_FOLLOWS, C.SCORE_NETWORK_FOLLOWS_MAX)
        pts = _w(raw, ws)
        breakdown["network_follows"] = pts
        score += pts
        reasons.append(
            {
                "code": C.REASON_NETWORK_FOLLOWS,
                "label": _label(C.REASON_NETWORK_FOLLOWS),
            }
        )

    passport_cats = host_cats & affinity.favorite_categories
    more_like_cats = host_cats & affinity.more_like_category_slugs
    if passport_cats or more_like_cats:
        pts = _w(C.SCORE_CATEGORY_MATCH, wi)
        breakdown["category"] = pts
        score += pts
        reasons.append({"code": C.REASON_CATEGORY, "label": _label(C.REASON_CATEGORY)})

    if host_cats & affinity.penalized_category_slugs:
        breakdown["not_interested_category"] = -C.SCORE_PENALTY_CATEGORY
        score -= C.SCORE_PENALTY_CATEGORY

    host_city = host_city_label(card)
    city_match = False
    if host_city:
        if host_city in affinity.favorite_cities or host_city in affinity.followed_city_labels:
            city_match = True
        if affinity.location_city and host_city == affinity.location_city:
            city_match = True
        if host_city in affinity.more_like_city_labels:
            city_match = True
    if city_match:
        pts = _w(C.SCORE_CITY_MATCH, wl)
        breakdown["city"] = pts
        score += pts
        reasons.append({"code": C.REASON_CITY, "label": _label(C.REASON_CITY)})

    dist = _distance_km(affinity, card)
    if dist is not None:
        if dist <= 10:
            pts = _w(C.SCORE_NEARBY_WITHIN_10KM, wl)
            breakdown["nearby"] = pts
            score += pts
            if not any(r["code"] in (C.REASON_CITY, C.REASON_NEARBY) for r in reasons):
                reasons.append({"code": C.REASON_NEARBY, "label": _label(C.REASON_NEARBY)})
        elif dist <= 25:
            pts = _w(C.SCORE_NEARBY_WITHIN_25KM, wl)
            breakdown["nearby"] = pts
            score += pts

    if card.get("verified"):
        pts = _w(C.SCORE_VERIFIED, wt)
        breakdown["verified"] = pts
        score += pts
        reasons.append({"code": C.REASON_VERIFIED, "label": _label(C.REASON_VERIFIED)})

    upcoming_n = int(card.get("upcoming_events_count") or 0)
    if upcoming_n > 0:
        pts = _w(C.SCORE_UPCOMING_EVENT, wt)
        breakdown["upcoming"] = pts
        score += pts
        if not any(r["code"] == C.REASON_UPCOMING for r in reasons):
            reasons.append({"code": C.REASON_UPCOMING, "label": _label(C.REASON_UPCOMING)})

    if host_has_upcoming_soon(card, within_days=C.UPCOMING_SOON_DAYS):
        pts = _w(C.SCORE_UPCOMING_SOON, wf)
        breakdown["upcoming_soon"] = pts
        score += pts
        reasons.append(
            {"code": C.REASON_UPCOMING_SOON, "label": _label(C.REASON_UPCOMING_SOON)}
        )

    checkins = int(card.get("verified_checkins_count") or 0)
    if checkins > 0:
        raw = min(
            max(1, checkins // 50) * (C.SCORE_TRUST_CHECKINS // 2),
            C.SCORE_TRUST_CHECKINS_CAP,
        )
        pts = _w(raw, wt)
        breakdown["trust_checkins"] = pts
        score += pts

    rating = card.get("average_rating")
    reviews = int(card.get("review_count") or 0)
    if rating is not None and reviews >= 3:
        pts = _w(C.SCORE_TRUST_RATING, wt)
        breakdown["trust_rating"] = pts
        score += pts
        if not any(r["code"] == C.REASON_TRUST for r in reasons):
            reasons.append({"code": C.REASON_TRUST, "label": _label(C.REASON_TRUST)})

    feedback = _feedback_boost(db, user_id, affinity, card, cfg)
    if feedback["boost_more_like"]:
        breakdown["more_like"] = C.SCORE_BOOST_MORE_LIKE
        score += C.SCORE_BOOST_MORE_LIKE
        if not any(r["code"] == C.REASON_CATEGORY for r in reasons):
            reasons.append(
                {
                    "code": C.REASON_CATEGORY,
                    "label": "More like hosts you liked",
                }
            )
    if feedback["ignored"]:
        breakdown["ignored"] = -C.SCORE_PENALTY_IGNORED
        score -= C.SCORE_PENALTY_IGNORED
    if dismiss["penalty"]:
        breakdown["dismissed"] = -C.SCORE_PENALTY_DISMISSED
        score -= C.SCORE_PENALTY_DISMISSED

    if (
        not reasons
        and upcoming_n > 0
        and cfg.cold_start_mode != C.COLD_START_OFF
    ):
        pts = _w(C.SCORE_COLD_START_BASELINE, wf)
        breakdown["discovery_baseline"] = pts
        score += pts
        reasons.append({"code": C.REASON_UPCOMING, "label": _label(C.REASON_UPCOMING)})

    clamped = max(0, min(C.SCORE_MAX, score))
    label = recommendation_label(clamped)
    min_show = cfg.min_score
    show = clamped >= min_show and bool(reasons)
    return HostScoreResult(
        score=clamped,
        reasons=reasons[:4],
        recommendation_label=label if show else None,
        show=show,
        breakdown=breakdown,
        relationship=relationship,
    )
