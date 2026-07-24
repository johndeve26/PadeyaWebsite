"""Open Event Ambassadors demo seed (Afrobeats Night Ambassador Drive)."""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app.core.config import get_settings
from app.demo.constants import (
    DEMO_EMAIL_DOMAIN,
    DEMO_EVENT_SLUG_PREFIX,
    OPEN_AMBASSADOR_CAMPAIGN_NAME,
)
from app.demo.seed import seed_demo_data
from app.events.models import Event
from app.promos.ambassador_domain import AmbassadorConversion, AmbassadorParticipant
from app.promos.models import Ambassador, AmbassadorCampaign, AmbassadorSale, PromoClick
from app.users.service import get_user_by_email


@pytest.fixture()
def demo_settings(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("FRONTEND_URL", "http://localhost:3000")
    get_settings.cache_clear()
    yield get_settings()
    get_settings.cache_clear()


def test_demo_open_ambassadors_campaign_and_ledger(demo_settings, db_session) -> None:
    first = seed_demo_data(db_session, reset=True)
    assert first["status"] == "seeded"
    assert first.get("open_ambassador_campaigns", 0) >= 1
    assert first.get("open_ambassador_participants", 0) >= 3

    event = db_session.scalar(
        select(Event).where(
            Event.slug == f"{DEMO_EVENT_SLUG_PREFIX}afrobeats-night-live"
        )
    )
    assert event is not None
    assert event.open_ambassadors_enabled is True

    campaign = db_session.scalar(
        select(AmbassadorCampaign).where(
            AmbassadorCampaign.event_id == event.id,
            AmbassadorCampaign.name == OPEN_AMBASSADOR_CAMPAIGN_NAME,
        )
    )
    assert campaign is not None
    assert campaign.status == "public_open"
    assert campaign.applies_to == "tickets_and_merch"
    assert campaign.leaderboard_reward_enabled is True

    codes = {"toluafro", "amaka20", "chidilive"}
    for code in codes:
        amb = db_session.scalar(
            select(Ambassador).where(
                Ambassador.campaign_id == campaign.id,
                Ambassador.referral_code == code,
                Ambassador.program_kind == "open_event",
            )
        )
        assert amb is not None, code
        assert amb.status == "active"
        part = db_session.scalar(
            select(AmbassadorParticipant).where(
                AmbassadorParticipant.campaign_id == campaign.id,
                AmbassadorParticipant.ambassador_code == code,
            )
        )
        assert part is not None, code
        clicks = (
            db_session.scalar(
                select(func.count())
                .select_from(PromoClick)
                .where(PromoClick.ambassador_id == amb.id)
            )
            or 0
        )
        assert clicks >= 5, code

    sales = list(
        db_session.scalars(
            select(AmbassadorSale).where(
                AmbassadorSale.ambassador_id.in_(
                    select(Ambassador.id).where(
                        Ambassador.campaign_id == campaign.id
                    )
                )
            )
        ).all()
    )
    statuses = {s.status for s in sales}
    assert "attributed" in statuses
    assert "approved" in statuses
    assert "reversed" in statuses
    assert any((s.tickets_sold or 0) > 0 for s in sales)
    assert any((s.merch_units_sold or 0) > 0 for s in sales) or any(
        c.conversion_type == "merch"
        for c in db_session.scalars(
            select(AmbassadorConversion).where(
                AmbassadorConversion.campaign_id == campaign.id
            )
        ).all()
    )

    domain_statuses = {
        c.status
        for c in db_session.scalars(
            select(AmbassadorConversion).where(
                AmbassadorConversion.campaign_id == campaign.id
            )
        ).all()
    }
    assert "pending" in domain_statuses or "payable" in domain_statuses
    assert "reversed" in domain_statuses

    tolu = get_user_by_email(db_session, f"fan1@{DEMO_EMAIL_DOMAIN}")
    assert tolu is not None
    assert tolu.full_name == "Tolu Nightlife Explorer"

    # Idempotent refresh must not duplicate participants.
    second = seed_demo_data(db_session, reset=False)
    assert second["status"] == "already_seeded"
    participants = (
        db_session.scalar(
            select(func.count())
            .select_from(AmbassadorParticipant)
            .where(AmbassadorParticipant.campaign_id == campaign.id)
        )
        or 0
    )
    assert participants == 3
