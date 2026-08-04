"""Public/host Legacy presentation helpers — display only; no formula changes."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from app.legacy.constants import SCORE_CAPS, SCORE_WEIGHTS
from app.legacy.scoring import ScoreInputs, requirement_checklist

# Limited-history provisional policy (backend-authoritative).
PROVISIONAL_MIN_COMPLETED_EVENTS = 3
PROVISIONAL_MIN_VERIFIED_REVIEWS = 5

# Public factor band thresholds on normalized 0–100 values.
_BAND_CUTOFFS: tuple[tuple[Decimal, str], ...] = (
    (Decimal("85"), "excellent"),
    (Decimal("70"), "strong"),
    (Decimal("50"), "good"),
    (Decimal("25"), "growing"),
    (Decimal("0"), "building"),
)

_PUBLIC_FACTOR_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("guest_satisfaction", ("verified_rating",)),
    ("event_experience", ("completed_events", "tickets_sold")),
    ("verified_attendance", ("verified_checkins",)),
    ("consistency", ("consistency",)),
    ("refund_record", ("refund_dispute_rate",)),
    ("community_loyalty", ("repeat_buyers_followers",)),
)

_FACTOR_LABELS: dict[str, str] = {
    "verified_rating": "Verified rating",
    "completed_events": "Completed events",
    "tickets_sold": "Tickets sold",
    "verified_checkins": "Verified check-ins",
    "refund_dispute_rate": "Refund and dispute record",
    "consistency": "Consistency",
    "repeat_buyers_followers": "Followers and repeat buyers",
}

_FACTOR_WHAT_COUNTS: dict[str, str] = {
    "verified_rating": "Verified guest reviews",
    "completed_events": "Eligible completed events",
    "tickets_sold": "Verified tickets sold",
    "verified_checkins": "Verified door check-ins",
    "refund_dispute_rate": "Verified refund/dispute rate",
    "consistency": "Completion and check-in rates",
    "repeat_buyers_followers": "Followers and repeat buyers",
}

_GATE_REMAINING_COPY: dict[str, str] = {
    "completed_events": "Complete {n} more eligible events",
    "tickets_sold": "Sell {n} more verified tickets",
    "verified_checkins": "Reach {n} more verified check-ins",
    "review_count": "Receive {n} more verified reviews",
    "average_rating": "Maintain at least a {required} verified rating",
}


def display_score(composite: Decimal | float | int | None) -> int:
    """Public whole-number score out of 100."""
    if composite is None:
        return 0
    value = Decimal(str(composite)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(max(Decimal("0"), min(Decimal("100"), value)))


def _as_decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def factor_band(normalized: Decimal | float | int | None) -> str:
    value = _as_decimal(normalized)
    for cutoff, label in _BAND_CUTOFFS:
        if value >= cutoff:
            return label
    return "building"


def provisional_state(
    *,
    completed_events: int,
    review_count: int,
) -> dict[str, Any]:
    reasons: list[str] = []
    if int(completed_events) < PROVISIONAL_MIN_COMPLETED_EVENTS:
        reasons.append("limited_completed_events")
    if int(review_count) < PROVISIONAL_MIN_VERIFIED_REVIEWS:
        reasons.append("limited_verified_reviews")
    return {
        "is_provisional": bool(reasons),
        "provisional_reasons": reasons,
    }


def public_evidence(
    *,
    average_verified_rating: Decimal | float | None,
    review_count: int,
    completed_events: int,
    tickets_sold: int,
    verified_checkins: int,
    repeat_buyers_rate: Decimal | float | None,
    followers: int | None = None,
) -> list[dict[str, Any]]:
    """Concise public evidence rows — skip empty noise."""
    items: list[dict[str, Any]] = []

    if average_verified_rating is not None and int(review_count) > 0:
        items.append(
            {
                "key": "verified_rating",
                "label": "Verified rating",
                "value": float(_as_decimal(average_verified_rating).quantize(Decimal("0.1"))),
                "display": f"{_as_decimal(average_verified_rating).quantize(Decimal('0.1'))}",
                "suffix": None,
            }
        )
        items.append(
            {
                "key": "verified_reviews",
                "label": "Verified reviews",
                "value": int(review_count),
                "display": str(int(review_count)),
                "suffix": None,
            }
        )
    elif int(review_count) == 0:
        items.append(
            {
                "key": "verified_reviews",
                "label": "Verified reviews",
                "value": 0,
                "display": "None yet",
                "suffix": None,
            }
        )

    if int(completed_events) > 0:
        items.append(
            {
                "key": "completed_events",
                "label": "Completed events",
                "value": int(completed_events),
                "display": str(int(completed_events)),
                "suffix": None,
            }
        )

    if int(tickets_sold) > 0:
        items.append(
            {
                "key": "tickets_sold",
                "label": "Tickets sold",
                "value": int(tickets_sold),
                "display": _compact_int(int(tickets_sold)),
                "suffix": None,
            }
        )

    if int(verified_checkins) > 0:
        items.append(
            {
                "key": "verified_checkins",
                "label": "Verified check-ins",
                "value": int(verified_checkins),
                "display": _compact_int(int(verified_checkins)),
                "suffix": None,
            }
        )

    if repeat_buyers_rate is not None and _as_decimal(repeat_buyers_rate) > 0:
        rate = _as_decimal(repeat_buyers_rate).quantize(Decimal("1"))
        items.append(
            {
                "key": "repeat_buyers",
                "label": "Repeat buyers",
                "value": float(rate),
                "display": f"{int(rate)}%",
                "suffix": "%",
            }
        )

    # Followers only when useful and not dominating a thin evidence set.
    if followers is not None and int(followers) > 0 and len(items) < 6:
        if int(completed_events) > 0 or int(verified_checkins) > 0:
            items.append(
                {
                    "key": "followers",
                    "label": "Followers",
                    "value": int(followers),
                    "display": _compact_int(int(followers)),
                    "suffix": None,
                }
            )

    return items[:6]


def _compact_int(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}".rstrip("0").rstrip(".") + "M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}".rstrip("0").rstrip(".") + "K"
    return str(n)


def public_factor_bands(
    factor_scores: dict[str, Any] | None,
    *,
    refund_rate_unknown: bool,
) -> list[dict[str, Any]]:
    scores = factor_scores or {}
    bands: list[dict[str, Any]] = []
    for group_key, source_keys in _PUBLIC_FACTOR_GROUPS:
        if group_key == "refund_record" and refund_rate_unknown:
            bands.append(
                {
                    "key": group_key,
                    "label": "Refund and dispute record",
                    "band": "building",
                    "normalized": None,
                }
            )
            continue
        values = [_as_decimal(scores.get(k)) for k in source_keys]
        if not values:
            continue
        avg = sum(values) / Decimal(len(values))
        bands.append(
            {
                "key": group_key,
                "label": {
                    "guest_satisfaction": "Guest satisfaction",
                    "event_experience": "Event experience",
                    "verified_attendance": "Verified attendance",
                    "consistency": "Consistency",
                    "refund_record": "Refund and dispute record",
                    "community_loyalty": "Community loyalty",
                }[group_key],
                "band": factor_band(avg),
                "normalized": float(avg.quantize(Decimal("0.01"))),
            }
        )
    return bands


def factor_contributions(
    factor_scores: dict[str, Any] | None,
    *,
    metrics: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Host/admin factor table with weights and weighted contribution."""
    scores = factor_scores or {}
    metrics = metrics or {}
    rows: list[dict[str, Any]] = []
    total = Decimal("0")
    for key, weight in SCORE_WEIGHTS.items():
        normalized = _as_decimal(scores.get(key)).quantize(Decimal("0.01"))
        contribution = (normalized * weight).quantize(Decimal("0.01"))
        total += contribution
        cap = SCORE_CAPS.get(key)
        raw_note = _raw_progress_note(key, metrics, cap)
        rows.append(
            {
                "key": key,
                "label": _FACTOR_LABELS.get(key, key),
                "normalized": float(normalized),
                "weight": float(weight),
                "weight_percent": int(weight * 100),
                "contribution": float(contribution),
                "what_counts": _FACTOR_WHAT_COUNTS.get(key, ""),
                "raw_progress": raw_note,
            }
        )
    return rows


def _raw_progress_note(
    key: str, metrics: dict[str, Any], cap: int | None
) -> str | None:
    if key == "completed_events" and cap:
        return f"{int(metrics.get('completed_events') or 0)} of {cap}-event cap"
    if key == "tickets_sold" and cap:
        return f"{int(metrics.get('tickets_sold') or 0)} of {cap:,} cap"
    if key == "verified_checkins" and cap:
        return f"{int(metrics.get('verified_checkins') or 0)} of {cap:,} cap"
    if key == "verified_rating":
        rating = metrics.get("average_verified_rating")
        reviews = int(metrics.get("review_count") or 0)
        if rating is None or reviews <= 0:
            return "No verified reviews yet"
        return f"{_as_decimal(rating).quantize(Decimal('0.1'))} from {reviews} reviews"
    if key == "repeat_buyers_followers":
        followers = int(metrics.get("followers") or 0)
        repeat = metrics.get("repeat_buyers_rate")
        if repeat is None:
            return f"{followers} followers · repeat buyers building"
        return f"{followers} followers · {int(_as_decimal(repeat))}% repeat buyers"
    if key == "refund_dispute_rate":
        rate = metrics.get("refund_dispute_rate")
        if rate is None:
            return "Default placeholder while rate is unknown"
        return f"Verified rate { _as_decimal(rate).quantize(Decimal('0.1')) }%"
    return None


def unmet_requirement_copy(item: dict[str, Any]) -> str:
    key = item["key"]
    current = Decimal(str(item.get("current") or 0))
    required = Decimal(str(item.get("required") or 0))
    remaining = max(Decimal("0"), required - current)
    template = _GATE_REMAINING_COPY.get(key)
    if key == "average_rating":
        return template.format(required=float(required)) if template else item.get("label", key)
    if template:
        n = int(remaining.to_integral_value(rounding=ROUND_HALF_UP))
        return template.format(n=n)
    return item.get("label", key)


def prioritize_unmet(remaining: list[dict[str, Any]], *, limit: int = 3) -> list[dict[str, Any]]:
    def closeness(item: dict[str, Any]) -> float:
        required = float(item.get("required") or 0)
        current = float(item.get("current") or 0)
        if required <= 0:
            return 1.0
        return min(1.0, current / required)

    ordered = sorted(remaining, key=closeness, reverse=True)
    out: list[dict[str, Any]] = []
    for item in ordered[:limit]:
        out.append(
            {
                **item,
                "message": unmet_requirement_copy(item),
            }
        )
    return out


def build_next_tier_summary(
    *,
    composite_score: Decimal,
    current_tier: Any | None,
    next_tier: Any | None,
    inputs: ScoreInputs,
) -> dict[str, Any] | None:
    if next_tier is None:
        return None

    checklist = requirement_checklist(getattr(next_tier, "requirements", None), inputs)
    met = [c for c in checklist if c["met"]]
    remaining = [c for c in checklist if not c["met"]]
    min_score = _as_decimal(next_tier.min_score)
    score_remaining = max(Decimal("0"), (min_score - composite_score)).quantize(Decimal("0.01"))
    score_requirement_met = composite_score >= min_score
    prioritized = prioritize_unmet(remaining, limit=3)
    additional = max(0, len(remaining) - len(prioritized))

    state = "in_progress"
    if score_requirement_met and remaining:
        state = "score_met_gates_remaining"
    elif score_requirement_met and not remaining:
        state = "ready"
    elif not remaining and not score_requirement_met:
        state = "score_remaining"

    return {
        "key": getattr(next_tier, "slug", None),
        "name": getattr(next_tier, "name", None),
        "min_score": float(min_score),
        "score_remaining": float(score_remaining),
        "score_requirement_met": score_requirement_met,
        "gates_met": len(met),
        "gates_total": len(checklist),
        "gates_remaining": len(remaining),
        "state": state,
        "unmet_requirements": prioritized,
        "additional_requirements_count": additional,
        "current_tier_key": getattr(current_tier, "slug", None) if current_tier else None,
        "current_tier_name": getattr(current_tier, "name", None) if current_tier else None,
    }


def build_legacy_trust_summary(
    *,
    composite_score: Decimal | None,
    tier: Any | None,
    legacy_status: str,
    factor_scores: dict[str, Any] | None,
    completed_events: int,
    tickets_sold: int,
    verified_checkins: int,
    average_verified_rating: Decimal | float | None,
    review_count: int,
    followers: int,
    repeat_buyers_rate: Decimal | float | None,
    refund_dispute_rate: Decimal | float | None,
    next_tier: Any | None,
    inputs: ScoreInputs,
    last_recalculated_at: Any | None = None,
    is_top_tier: bool = False,
) -> dict[str, Any]:
    score = _as_decimal(composite_score)
    provisional = provisional_state(
        completed_events=completed_events,
        review_count=review_count,
    )
    next_summary = None
    if is_top_tier or next_tier is None:
        next_summary = None
    else:
        next_summary = build_next_tier_summary(
            composite_score=score,
            current_tier=tier,
            next_tier=next_tier,
            inputs=inputs,
        )

    headline = _public_headline(
        is_provisional=provisional["is_provisional"],
        completed_events=completed_events,
        review_count=review_count,
        is_top_tier=is_top_tier,
    )

    return {
        "score": float(score.quantize(Decimal("0.01"))),
        "display_score": display_score(score),
        "tier": {
            "key": getattr(tier, "slug", None) if tier else None,
            "name": getattr(tier, "name", None) if tier else legacy_status,
            "description": getattr(tier, "description", None) if tier else None,
            "rank": getattr(tier, "rank", None) if tier else None,
        },
        "legacy_status": legacy_status,
        "is_provisional": provisional["is_provisional"],
        "provisional_reasons": provisional["provisional_reasons"],
        "is_top_tier": is_top_tier,
        "headline": headline,
        "evidence": public_evidence(
            average_verified_rating=average_verified_rating,
            review_count=review_count,
            completed_events=completed_events,
            tickets_sold=tickets_sold,
            verified_checkins=verified_checkins,
            repeat_buyers_rate=repeat_buyers_rate,
            followers=followers,
        ),
        "next_tier": next_summary,
        "factor_bands": public_factor_bands(
            factor_scores,
            refund_rate_unknown=refund_dispute_rate is None,
        ),
        "last_recalculated_at": last_recalculated_at,
        "how_it_works_path": "/legacy",
    }


def _public_headline(
    *,
    is_provisional: bool,
    completed_events: int,
    review_count: int,
    is_top_tier: bool,
) -> str:
    if completed_events <= 0 and review_count <= 0:
        return "No verified hosting history yet"
    if is_provisional:
        return "Building verified history"
    if is_top_tier:
        return "Highest Legacy tier"
    return "Trusted and consistently verified"


def score_inputs_from_metrics(metrics: dict[str, Any]) -> ScoreInputs:
    return ScoreInputs(
        average_verified_rating=(
            _as_decimal(metrics["average_verified_rating"])
            if metrics.get("average_verified_rating") is not None
            else None
        ),
        review_count=int(metrics.get("review_count") or 0),
        completed_events=int(metrics.get("completed_events") or 0),
        tickets_sold=int(metrics.get("tickets_sold") or 0),
        verified_checkins=int(metrics.get("verified_checkins") or 0),
        refund_dispute_rate=(
            _as_decimal(metrics["refund_dispute_rate"])
            if metrics.get("refund_dispute_rate") is not None
            else None
        ),
        events_hosted=int(metrics.get("events_hosted") or 0),
        followers=int(metrics.get("followers") or 0),
        repeat_buyers_rate=(
            _as_decimal(metrics["repeat_buyers_rate"])
            if metrics.get("repeat_buyers_rate") is not None
            else None
        ),
    )
