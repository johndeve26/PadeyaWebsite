"""Public Legacy API verification across host trust states."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.hosts.models import Host, HostProfile
from app.legacy.models import HostLegacyScore, HostLegacyScoreHistory, LegacyTier
from app.legacy.presentation import display_score
from app.legacy.seed import seed_legacy_tiers
from app.legacy.service import refresh_host_legacy_score
from app.users.models import User
from app.users.service import get_role_by_name
from tests.test_legacy_tiers import _seed_host_with_metrics


def _host_user(db: Session, email: str, slug: str) -> Host:
    user = User(
        email=email,
        password_hash=hash_password("securepass1"),
        full_name=slug,
        is_active=True,
    )
    role = get_role_by_name(db, "host")
    assert role is not None
    user.roles.append(role)
    db.add(user)
    db.flush()
    host = Host(user_id=user.id, display_name=slug, slug=slug, status="active")
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id))
    db.flush()
    return host


def _public_legacy(client: TestClient, slug: str) -> dict:
    res = client.get(f"/api/v1/u/{slug}/legacy")
    assert res.status_code == 200, res.text
    return res.json()


def test_no_history_host_legacy_trust(client: TestClient, db_session: Session):
    seed_legacy_tiers(db_session)
    host = _host_user(db_session, "legacy-empty@example.com", "legacy-empty")
    refresh_host_legacy_score(db_session, host.id, reason="seed")
    db_session.commit()

    body = _public_legacy(client, host.slug)
    trust = body["legacy_trust"]
    assert trust["display_score"] == round(float(trust["score"]))
    assert trust["headline"] == "No verified hosting history yet"
    assert trust["is_provisional"] is True


def test_provisional_host_legacy_trust(client: TestClient, db_session: Session):
    seed_legacy_tiers(db_session)
    host = _seed_host_with_metrics(
        db_session, completed_events=2, tickets=10, checkins=5, reviews=1
    )
    refresh_host_legacy_score(db_session, host.id, reason="seed")
    db_session.commit()

    trust = _public_legacy(client, host.slug)["legacy_trust"]
    assert trust["is_provisional"] is True
    assert trust["display_score"] >= 0
    assert any(
        item["key"] == "verified_reviews" for item in trust["evidence"]
    )


def test_established_host_display_score_and_evidence(
    client: TestClient, db_session: Session
):
    seed_legacy_tiers(db_session)
    host = _seed_host_with_metrics(
        db_session, completed_events=4, tickets=200, checkins=100, reviews=8
    )
    score = refresh_host_legacy_score(db_session, host.id, reason="seed")
    db_session.commit()

    trust = _public_legacy(client, host.slug)["legacy_trust"]
    assert trust["display_score"] == display_score(score.composite_score)
    assert trust["is_provisional"] is False
    keys = {item["key"] for item in trust["evidence"]}
    assert "completed_events" in keys
    assert "verified_rating" in keys
    # Verified star rating remains on stats, separate from Legacy score card.
    assert body_stats_rating_present(_public_legacy(client, host.slug))


def body_stats_rating_present(body: dict) -> bool:
    return body["stats"]["average_verified_rating"] is not None or body["stats"]["review_count"] == 0


def test_score_met_gate_blocked_next_tier_state(client: TestClient, db_session: Session):
    seed_legacy_tiers(db_session)
    host = _host_user(db_session, "legacy-gated@example.com", "legacy-gated")
    score_row = HostLegacyScore(
        host_id=host.id,
        events_hosted=1,
        completed_events=1,
        tickets_sold=30,
        verified_checkins=15,
        review_count=2,
        followers=10,
        composite_score=Decimal("72.00"),
        legacy_status="Rising",
    )
    db_session.add(score_row)
    db_session.flush()
    rising = db_session.scalar(select(LegacyTier).where(LegacyTier.slug == "rising"))
    certified = db_session.scalar(
        select(LegacyTier).where(LegacyTier.slug == "certified")
    )
    assert rising and certified
    score_row.tier_id = rising.id
    db_session.commit()

    trust = _public_legacy(client, host.slug)["legacy_trust"]
    nxt = trust.get("next_tier")
    assert nxt is not None
    if float(trust["score"]) >= float(certified.min_score):
        assert nxt["score_requirement_met"] is True
        assert nxt["state"] == "score_met_gates_remaining"
        assert nxt["score_remaining"] == 0


def test_top_tier_host_has_no_next_tier(client: TestClient, db_session: Session):
    seed_legacy_tiers(db_session)
    host = _host_user(db_session, "legacy-legend@example.com", "legacy-legend")
    legend = db_session.scalar(select(LegacyTier).where(LegacyTier.slug == "legend"))
    assert legend
    db_session.add(
        HostLegacyScore(
            host_id=host.id,
            tier_id=legend.id,
            events_hosted=30,
            completed_events=30,
            tickets_sold=6000,
            verified_checkins=3000,
            review_count=80,
            followers=500,
            composite_score=Decimal("90.00"),
            legacy_status="Legend",
        )
    )
    db_session.commit()

    trust = _public_legacy(client, host.slug)["legacy_trust"]
    assert trust["is_top_tier"] is True
    assert trust.get("next_tier") is None


def test_public_legacy_get_does_not_rescore(client: TestClient, db_session: Session):
    host = _seed_host_with_metrics(db_session)
    refresh_host_legacy_score(db_session, host.id, reason="seed", force_history=True)
    db_session.commit()
    before = len(
        db_session.scalars(
            select(HostLegacyScoreHistory).where(
                HostLegacyScoreHistory.host_id == host.id
            )
        ).all()
    )

    with patch("app.legacy.service.refresh_host_legacy_score") as mock_refresh:
        res = client.get(f"/api/v1/u/{host.slug}/legacy")
        assert res.status_code == 200
        mock_refresh.assert_not_called()

    after = len(
        db_session.scalars(
            select(HostLegacyScoreHistory).where(
                HostLegacyScoreHistory.host_id == host.id
            )
        ).all()
    )
    assert after == before
