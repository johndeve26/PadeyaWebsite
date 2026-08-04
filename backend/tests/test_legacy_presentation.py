"""Legacy presentation helpers — display score, provisional, next-tier, bands."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from app.legacy.presentation import (
    build_legacy_trust_summary,
    build_next_tier_summary,
    display_score,
    factor_contributions,
    provisional_state,
    public_evidence,
    public_factor_bands,
)
from app.legacy.scoring import ScoreInputs, compute_composite_score


def test_display_score_rounds_whole_number():
    assert display_score(Decimal("72.46")) == 72
    assert display_score(Decimal("72.50")) == 73
    assert display_score(None) == 0
    assert display_score(-1) == 0
    assert display_score(140) == 100


def test_provisional_limited_history():
    thin = provisional_state(completed_events=2, review_count=1)
    assert thin["is_provisional"] is True
    assert "limited_completed_events" in thin["provisional_reasons"]
    assert "limited_verified_reviews" in thin["provisional_reasons"]

    solid = provisional_state(completed_events=3, review_count=5)
    assert solid["is_provisional"] is False
    assert solid["provisional_reasons"] == []


def test_public_evidence_skips_zero_noise_and_no_fake_rating():
    items = public_evidence(
        average_verified_rating=None,
        review_count=0,
        completed_events=0,
        tickets_sold=0,
        verified_checkins=0,
        repeat_buyers_rate=None,
        followers=0,
    )
    assert len(items) == 1
    assert items[0]["key"] == "verified_reviews"
    assert items[0]["display"] == "None yet"

    rich = public_evidence(
        average_verified_rating=Decimal("4.8"),
        review_count=32,
        completed_events=18,
        tickets_sold=3850,
        verified_checkins=1240,
        repeat_buyers_rate=Decimal("14"),
        followers=900,
    )
    keys = [i["key"] for i in rich]
    assert "verified_rating" in keys
    assert "completed_events" in keys
    assert len(rich) <= 6


def test_score_met_gates_remaining_state():
    inputs = ScoreInputs(
        average_verified_rating=Decimal("4.5"),
        review_count=10,
        completed_events=4,
        tickets_sold=200,
        verified_checkins=100,
        refund_dispute_rate=None,
        events_hosted=4,
        followers=100,
        repeat_buyers_rate=None,
    )
    next_tier = SimpleNamespace(
        slug="icon",
        name="Icon",
        min_score=Decimal("70"),
        requirements={
            "min_completed_events": 12,
            "min_tickets_sold": 1500,
            "min_verified_checkins": 800,
            "min_average_rating": 4.4,
            "min_review_count": 30,
        },
    )
    summary = build_next_tier_summary(
        composite_score=Decimal("72.00"),
        current_tier=SimpleNamespace(slug="certified", name="Certified"),
        next_tier=next_tier,
        inputs=inputs,
    )
    assert summary is not None
    assert summary["score_requirement_met"] is True
    assert summary["state"] == "score_met_gates_remaining"
    assert summary["score_remaining"] == 0.0
    assert summary["gates_remaining"] > 0
    assert summary["unmet_requirements"]


def test_top_tier_trust_summary_has_no_next_tier():
    inputs = ScoreInputs(
        average_verified_rating=Decimal("4.8"),
        review_count=80,
        completed_events=30,
        tickets_sold=6000,
        verified_checkins=3000,
        refund_dispute_rate=Decimal("2"),
        events_hosted=30,
        followers=2000,
        repeat_buyers_rate=Decimal("20"),
    )
    trust = build_legacy_trust_summary(
        composite_score=Decimal("90.12"),
        tier=SimpleNamespace(
            slug="legend",
            name="Legend",
            description="Top",
            rank=5,
        ),
        legacy_status="Legend",
        factor_scores={"verified_rating": 96},
        completed_events=30,
        tickets_sold=6000,
        verified_checkins=3000,
        average_verified_rating=Decimal("4.8"),
        review_count=80,
        followers=2000,
        repeat_buyers_rate=Decimal("20"),
        refund_dispute_rate=Decimal("2"),
        next_tier=None,
        inputs=inputs,
        is_top_tier=True,
    )
    assert trust["display_score"] == 90
    assert trust["is_top_tier"] is True
    assert trust["next_tier"] is None
    assert trust["headline"] == "Highest Legacy tier"


def test_refund_unknown_band_is_building_not_placeholder():
    bands = public_factor_bands(
        {"refund_dispute_rate": 80, "verified_rating": 90},
        refund_rate_unknown=True,
    )
    refund = next(b for b in bands if b["key"] == "refund_record")
    assert refund["band"] == "building"
    assert refund["normalized"] is None


def test_factor_contributions_reconcile_to_composite():
    score, factors = compute_composite_score(
        ScoreInputs(
            average_verified_rating=Decimal("5"),
            review_count=10,
            completed_events=10,
            tickets_sold=2500,
            verified_checkins=1500,
            refund_dispute_rate=None,
            events_hosted=10,
            followers=1000,
            repeat_buyers_rate=Decimal("20"),
        )
    )
    rows = factor_contributions(
        {k: float(v) for k, v in factors.items()},
        metrics={
            "completed_events": 10,
            "tickets_sold": 2500,
            "verified_checkins": 1500,
            "average_verified_rating": 5,
            "review_count": 10,
            "followers": 1000,
            "repeat_buyers_rate": 20,
            "refund_dispute_rate": None,
        },
    )
    total = sum(Decimal(str(r["contribution"])) for r in rows)
    assert abs(total - score) <= Decimal("0.05")
