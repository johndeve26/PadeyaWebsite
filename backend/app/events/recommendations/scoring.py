"""Score a published event for a fan."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.events.models import Event
from app.events.recommendations import constants as C
from app.events.recommendations.affinity import (
    FanEventAffinity,
    event_category_slug,
    event_city_label,
)
from app.events.recommendations.models import (
    EventRecommendationDismissal,
    EventRecommendationFeedback,
    EventRecommendationImpression,
)
from app.events.recommendations.settings import EventRecommendationConfig


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _w(value: int, weight: float, cap: int) -> int:
    return min(cap, int(round(value * max(0.0, weight))))


def _label(code: str) -> str:
    return C.REASON_LABELS.get(code, code.replace("_", " ").title())


@dataclass
class EventScoreResult:
    score: int
    reasons: list[dict] = field(default_factory=list)
    show: bool = False
    breakdown: dict[str, int] = field(default_factory=dict)
    flags: dict[str, bool] = field(default_factory=dict)


def _mode_weights(mode: str, config: EventRecommendationConfig) -> dict[str, float]:
    wi, wh, wl, ws, wt, wf = (
        config.weight_interest,
        config.weight_host,
        config.weight_location,
        config.weight_social,
        config.weight_trust,
        config.weight_freshness,
    )
    if mode == "near_you":
        wl *= 1.6
    elif mode == "similar_to_attended":
        wi *= 1.5
    elif mode == "followed_hosts":
        wh *= 1.6
    elif mode == "friends_going":
        ws *= 1.6
    elif mode == "trending":
        wt *= 1.3
        wf *= 1.2
    return {
        "interest": wi,
        "host": wh,
        "location": wl,
        "social": ws,
        "trust": wt,
        "freshness": wf,
    }


def _dismissal_state(
    db: Session, user_id: UUID, event_id: UUID, *, dismiss_days: int
) -> dict:
    row = db.scalar(
        select(EventRecommendationDismissal).where(
            EventRecommendationDismissal.user_id == user_id,
            EventRecommendationDismissal.event_id == event_id,
        )
    )
    if row is None:
        return {"exclude": False, "penalty": False}
    expires = _aware(row.expires_at)
    if expires is not None and expires > _now():
        return {"exclude": True, "penalty": False}
    return {"exclude": False, "penalty": True}


def _impression_engagement(db: Session, user_id: UUID, event_id: UUID) -> dict:
    impressions = int(
        db.scalar(
            select(func.count())
            .select_from(EventRecommendationImpression)
            .where(
                EventRecommendationImpression.user_id == user_id,
                EventRecommendationImpression.event_id == event_id,
            )
        )
        or 0
    )
    engaged = int(
        db.scalar(
            select(func.count())
            .select_from(EventRecommendationFeedback)
            .where(
                EventRecommendationFeedback.user_id == user_id,
                EventRecommendationFeedback.event_id == event_id,
                EventRecommendationFeedback.action.in_(
                    (
                        C.FEEDBACK_CLICKED,
                        C.FEEDBACK_SAVED,
                        C.FEEDBACK_PURCHASED,
                        C.FEEDBACK_MORE_LIKE_THIS,
                    )
                ),
            )
        )
        or 0
    )
    return {"impressions": impressions, "engaged": engaged}


def _is_weekend_soon(event: Event) -> bool:
    start = _aware(event.start_datetime)
    if start is None:
        return False
    now = _now()
    if start < now:
        return False
    return start <= now + timedelta(days=C.WEEKEND_DAYS)


def score_event_for_fan(
    db: Session,
    *,
    user_id: UUID,
    event: Event,
    affinity: FanEventAffinity,
    config: EventRecommendationConfig,
    mode: str = C.DEFAULT_MODE,
) -> EventScoreResult:
    weights = _mode_weights(mode, config)
    event_id = event.id
    host_id = event.host_id
    flags: dict[str, bool] = {
        "from_followed_host": False,
        "similar_to_attended": False,
        "near_you": False,
        "connected_fans_signal": False,
        "category_match": False,
    }

    if host_id and host_id in affinity.own_host_ids:
        return EventScoreResult(score=0, show=False, breakdown={"_exclude_own_host": 1})

    if event_id in affinity.upcoming_ticket_event_ids:
        return EventScoreResult(
            score=0, show=False, breakdown={"_exclude_already_purchased": 1}
        )

    cat = event_category_slug(event)
    if cat and cat in affinity.hidden_category_slugs:
        return EventScoreResult(score=0, show=False, breakdown={"_exclude_category_hidden": 1})

    if host_id and host_id in affinity.hidden_host_ids:
        return EventScoreResult(score=0, show=False, breakdown={"_exclude_host_hidden": 1})

    dismiss = _dismissal_state(db, user_id, event_id, dismiss_days=config.dismiss_days)
    if dismiss["exclude"]:
        return EventScoreResult(score=0, show=False, breakdown={"_exclude_dismissed": 1})

    breakdown: dict[str, int] = {}
    score = 0
    reasons: list[dict] = []
    interest_used = 0
    host_used = 0
    loc_used = 0
    social_used = 0
    trust_used = 0
    fresh_used = 0

    if cat:
        if (
            cat in affinity.attended_category_slugs
            or cat in affinity.ticketed_category_slugs
            or cat in affinity.favorite_categories
        ):
            pts = _w(C.PTS_CATEGORY_MATCH, weights["interest"], C.CAP_INTEREST - interest_used)
            interest_used += pts
            score += pts
            flags["category_match"] = True
            reasons.append({"code": C.REASON_CATEGORY, "label": _label(C.REASON_CATEGORY)})
        if cat in affinity.attended_category_slugs:
            pts = _w(
                C.PTS_SIMILAR_ATTENDED,
                weights["interest"],
                C.CAP_INTEREST - interest_used,
            )
            interest_used += pts
            score += pts
            flags["similar_to_attended"] = True
            reasons.append(
                {"code": C.REASON_SIMILAR_ATTENDED, "label": _label(C.REASON_SIMILAR_ATTENDED)}
            )
        if cat in affinity.penalized_category_slugs:
            score -= C.SCORE_PENALTY_CATEGORY
            breakdown["not_interested_category"] = -C.SCORE_PENALTY_CATEGORY

    if host_id:
        if host_id in affinity.followed_host_ids:
            pts = _w(C.PTS_FOLLOWED_HOST, weights["host"], C.CAP_HOST - host_used)
            host_used += pts
            score += pts
            flags["from_followed_host"] = True
            reasons.append(
                {"code": C.REASON_FOLLOWED_HOST, "label": _label(C.REASON_FOLLOWED_HOST)}
            )
        if host_id in affinity.attended_host_ids:
            pts = _w(C.PTS_ATTENDED_HOST, weights["host"], C.CAP_HOST - host_used)
            host_used += pts
            score += pts
        if host_id in affinity.penalized_host_ids:
            score -= C.SCORE_PENALTY_HOST
            breakdown["hide_host"] = -C.SCORE_PENALTY_HOST

    city = event_city_label(event)
    if city:
        if city in affinity.favorite_cities or (
            affinity.location_city and city == affinity.location_city
        ):
            pts = _w(C.PTS_CITY_MATCH, weights["location"], C.CAP_LOCATION - loc_used)
            loc_used += pts
            score += pts
            flags["near_you"] = True
            reasons.append({"code": C.REASON_CITY, "label": _label(C.REASON_CITY)})
        if city in affinity.more_like_city_labels:
            pts = _w(C.PTS_AREA_MATCH, weights["location"], C.CAP_LOCATION - loc_used)
            loc_used += pts
            score += pts
            flags["near_you"] = True

    net_ev = int(affinity.network_event_counts.get(event_id) or 0)
    if net_ev > 0:
        pts = _w(
            min(net_ev * C.PTS_NETWORK_ATTENDING, C.CAP_SOCIAL),
            weights["social"],
            C.CAP_SOCIAL - social_used,
        )
        social_used += pts
        score += pts
        flags["connected_fans_signal"] = True
        reasons.append({"code": C.REASON_NETWORK, "label": _label(C.REASON_NETWORK)})

    if host_id:
        net_host = int(affinity.network_host_follow_counts.get(host_id) or 0)
        if net_host > 0:
            pts = _w(
                min(net_host * C.PTS_NETWORK_HOST_FOLLOWS, C.CAP_SOCIAL - social_used),
                weights["social"],
                C.CAP_SOCIAL - social_used,
            )
            social_used += pts
            score += pts
            flags["connected_fans_signal"] = True
            if not any(r["code"] == C.REASON_NETWORK for r in reasons):
                reasons.append({"code": C.REASON_NETWORK, "label": _label(C.REASON_NETWORK)})

    if host_id and host_id in affinity.verified_host_ids:
        pts = _w(C.PTS_VERIFIED_HOST, weights["trust"], C.CAP_TRUST - trust_used)
        trust_used += pts
        score += pts
        reasons.append({"code": C.REASON_VERIFIED, "label": _label(C.REASON_VERIFIED)})

    if event.featured:
        pts = _w(C.PTS_FEATURED, weights["trust"], C.CAP_TRUST - trust_used)
        trust_used += pts
        score += pts
        reasons.append({"code": C.REASON_FEATURED, "label": _label(C.REASON_FEATURED)})

    if event_id in affinity.pick_event_ids:
        pts = _w(C.PTS_PADEYA_PICK, weights["trust"], C.CAP_TRUST - trust_used)
        trust_used += pts
        score += pts
        reasons.append({"code": C.REASON_PICK, "label": _label(C.REASON_PICK)})

    start = _aware(event.start_datetime)
    if start and start <= _now() + timedelta(days=C.UPCOMING_SOON_DAYS):
        pts = _w(C.PTS_UPCOMING_SOON, weights["freshness"], C.CAP_FRESHNESS - fresh_used)
        fresh_used += pts
        score += pts
        reasons.append({"code": C.REASON_UPCOMING, "label": _label(C.REASON_UPCOMING)})

    if _is_weekend_soon(event):
        pts = _w(C.PTS_UPCOMING_SOON // 2, weights["freshness"], C.CAP_FRESHNESS - fresh_used)
        fresh_used += pts
        score += pts
        reasons.append({"code": C.REASON_WEEKEND, "label": _label(C.REASON_WEEKEND)})

    pub = _aware(getattr(event, "published_at", None))
    if pub and pub >= _now() - timedelta(days=14):
        pts = _w(C.PTS_RECENTLY_PUBLISHED, weights["freshness"], C.CAP_FRESHNESS - fresh_used)
        fresh_used += pts
        score += pts

    if affinity.more_like_category_slugs and cat and cat in affinity.more_like_category_slugs:
        score += C.SCORE_BOOST_MORE_LIKE
        breakdown["more_like"] = C.SCORE_BOOST_MORE_LIKE

    stats = _impression_engagement(db, user_id, event_id)
    if (
        stats["impressions"] >= config.impression_penalty_threshold
        and stats["engaged"] == 0
    ):
        score -= C.SCORE_PENALTY_IGNORED
        breakdown["ignored"] = -C.SCORE_PENALTY_IGNORED

    if dismiss["penalty"]:
        score -= C.SCORE_PENALTY_DISMISSED
        breakdown["dismissed"] = -C.SCORE_PENALTY_DISMISSED

    if not reasons and config.cold_start_mode != C.COLD_START_OFF:
        if city and affinity.location_city and city == affinity.location_city:
            pts = _w(12, weights["freshness"], C.CAP_FRESHNESS)
            score += pts
            reasons.append(
                {"code": C.REASON_POPULAR_CITY, "label": _label(C.REASON_POPULAR_CITY)}
            )
        elif event.featured or event_id in affinity.pick_event_ids:
            code = C.REASON_PICK if event_id in affinity.pick_event_ids else C.REASON_FEATURED
            pts = _w(10, weights["trust"], C.CAP_TRUST)
            score += pts
            reasons.append({"code": code, "label": _label(code)})

    clamped = max(0, min(C.SCORE_MAX, score))
    show = clamped >= config.min_score and bool(reasons)
    deduped: list[dict] = []
    seen: set[str] = set()
    for r in reasons:
        if r["code"] in seen:
            continue
        seen.add(r["code"])
        deduped.append(r)

    return EventScoreResult(
        score=clamped,
        reasons=deduped[:4],
        show=show,
        breakdown=breakdown,
        flags=flags,
    )
