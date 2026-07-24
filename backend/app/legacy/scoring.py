"""Pure Legacy composite score and tier selection."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from app.legacy.constants import SCORE_CAPS, SCORE_WEIGHTS


def _q(value: Decimal | float | int) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _clamp(value: Decimal, low: Decimal = Decimal("0"), high: Decimal = Decimal("100")) -> Decimal:
    return max(low, min(high, value))


@dataclass(frozen=True)
class ScoreInputs:
    average_verified_rating: Decimal | None
    review_count: int
    completed_events: int
    tickets_sold: int
    verified_checkins: int
    refund_dispute_rate: Decimal | None  # 0–100 percent; lower is better
    events_hosted: int
    followers: int
    repeat_buyers_rate: Decimal | None  # 0–100 percent


def factor_scores(inputs: ScoreInputs) -> dict[str, Decimal]:
    """Normalize each factor to 0–100 before weighting."""
    if inputs.average_verified_rating is not None and inputs.review_count > 0:
        rating = _clamp(_q(Decimal(inputs.average_verified_rating) / Decimal("5") * 100))
    else:
        rating = Decimal("0")

    events_cap = Decimal(SCORE_CAPS["completed_events"])
    completed = _clamp(_q(Decimal(inputs.completed_events) / events_cap * 100))

    tickets_cap = Decimal(SCORE_CAPS["tickets_sold"])
    tickets = _clamp(_q(Decimal(inputs.tickets_sold) / tickets_cap * 100))

    checkins_cap = Decimal(SCORE_CAPS["verified_checkins"])
    checkins = _clamp(_q(Decimal(inputs.verified_checkins) / checkins_cap * 100))

    # Neutral placeholder when refunds are not tracked yet
    if inputs.refund_dispute_rate is None:
        refund = Decimal("80.00")
    else:
        rate = _clamp(Decimal(inputs.refund_dispute_rate), Decimal("0"), Decimal("100"))
        refund = _clamp(_q(Decimal("100") - rate))

    if inputs.events_hosted <= 0:
        consistency = Decimal("0")
    else:
        attendance = Decimal(inputs.verified_checkins) / max(Decimal(inputs.tickets_sold), Decimal("1"))
        completion = Decimal(inputs.completed_events) / Decimal(inputs.events_hosted)
        consistency = _clamp(_q(((attendance * Decimal("0.5")) + (completion * Decimal("0.5"))) * 100))

    followers_cap = Decimal(SCORE_CAPS["followers"])
    follower_part = _clamp(Decimal(inputs.followers) / followers_cap * 100)
    if inputs.repeat_buyers_rate is None:
        repeat_part = Decimal("0")
    else:
        repeat_part = _clamp(Decimal(inputs.repeat_buyers_rate))
    repeat_followers = _clamp(_q((follower_part * Decimal("0.5")) + (repeat_part * Decimal("0.5"))))

    return {
        "verified_rating": rating,
        "completed_events": completed,
        "tickets_sold": tickets,
        "verified_checkins": checkins,
        "refund_dispute_rate": refund,
        "consistency": consistency,
        "repeat_buyers_followers": repeat_followers,
    }


def composite_score_from_factors(factors: dict[str, Decimal]) -> Decimal:
    total = Decimal("0")
    for key, weight in SCORE_WEIGHTS.items():
        total += factors.get(key, Decimal("0")) * weight
    return _q(total)


def compute_composite_score(inputs: ScoreInputs) -> tuple[Decimal, dict[str, Decimal]]:
    factors = factor_scores(inputs)
    return composite_score_from_factors(factors), factors


def meets_tier_requirements(requirements: dict[str, Any] | None, inputs: ScoreInputs) -> bool:
    if not requirements:
        return True
    if inputs.completed_events < int(requirements.get("min_completed_events") or 0):
        return False
    if inputs.tickets_sold < int(requirements.get("min_tickets_sold") or 0):
        return False
    if inputs.verified_checkins < int(requirements.get("min_verified_checkins") or 0):
        return False
    min_reviews = int(requirements.get("min_review_count") or 0)
    if inputs.review_count < min_reviews:
        return False
    min_rating = requirements.get("min_average_rating")
    if min_rating is not None:
        if inputs.average_verified_rating is None:
            return False
        if Decimal(inputs.average_verified_rating) < Decimal(str(min_rating)):
            return False
    return True


def select_tier(
    tiers: list[Any],
    *,
    score: Decimal,
    inputs: ScoreInputs,
) -> Any | None:
    """
    Pick the highest-rank active tier where score >= min_score
    and hard requirements are met.
    """
    eligible = [
        t
        for t in tiers
        if getattr(t, "is_active", True)
        and Decimal(t.min_score) <= score
        and meets_tier_requirements(getattr(t, "requirements", None), inputs)
    ]
    if not eligible:
        # Fall back to lowest-rank tier (New Host)
        active = [t for t in tiers if getattr(t, "is_active", True)]
        return min(active, key=lambda t: t.rank) if active else None
    return max(eligible, key=lambda t: t.rank)


def requirement_checklist(
    requirements: dict[str, Any] | None,
    inputs: ScoreInputs,
) -> list[dict[str, Any]]:
    reqs = requirements or {}
    items: list[dict[str, Any]] = []

    def add(key: str, label: str, current: Decimal | int | None, needed: Decimal | int | None) -> None:
        if needed is None:
            return
        met = current is not None and Decimal(str(current)) >= Decimal(str(needed))
        items.append(
            {
                "key": key,
                "label": label,
                "current": float(current) if current is not None else 0,
                "required": float(needed),
                "met": met,
            }
        )

    add(
        "completed_events",
        "Completed events",
        inputs.completed_events,
        reqs.get("min_completed_events"),
    )
    add("tickets_sold", "Tickets sold", inputs.tickets_sold, reqs.get("min_tickets_sold"))
    add(
        "verified_checkins",
        "Verified check-ins",
        inputs.verified_checkins,
        reqs.get("min_verified_checkins"),
    )
    add("review_count", "Verified reviews", inputs.review_count, reqs.get("min_review_count"))
    add(
        "average_rating",
        "Average verified rating",
        inputs.average_verified_rating,
        reqs.get("min_average_rating"),
    )
    return items
