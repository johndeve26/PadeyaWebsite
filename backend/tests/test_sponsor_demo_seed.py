"""Tests for rich sponsor demo seed (local only)."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from sqlalchemy import func, select

from app.core.config import get_settings
from app.demo.constants import DEMO_PASSWORD
from app.demo.guards import DemoEnvironmentError
from app.demo.seed import seed_demo_data
from app.demo.sponsor_demo_guards import SponsorDemoSeedError, assert_sponsor_demo_seed_allowed
from app.demo.constants import DEMO_EVENT_SLUG_PREFIX
from app.demo.sponsor_demo_seed import (
    PUBLIC_DIRECTORY_SLUGS,
    SPONSOR_SPECS,
    public_directory_slugs,
    public_profile_safe,
    seed_rich_sponsor_demo,
)
from app.events.models import Event
from app.sponsor_profiles.public_profile_service import build_public_sponsor_profile
from app.sponsor_profiles.report_service import overview_report
from app.users.models import User
from app.sponsorships.models import (
    Sponsor,
    SponsorCampaign,
    SponsorSavedItem,
    SponsorTeamMember,
    SponsorshipDeal,
    SponsorshipDeliverable,
    SponsorshipInquiry,
    SponsorshipInvoice,
    SponsorshipPaymentEvent,
    SponsorshipPlacement,
)
from app.sponsor_profiles.recommendations.models import CampaignRecommendationFeedback
from app.sponsor_profiles.service import list_public_sponsors


@pytest.fixture()
def sponsor_demo_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("FRONTEND_URL", "http://localhost:3000")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_production_blocks_sponsor_demo_seed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DEMO_MODE", "true")
    get_settings.cache_clear()
    with pytest.raises(DemoEnvironmentError):
        assert_sponsor_demo_seed_allowed()
    get_settings.cache_clear()


def test_requires_demo_mode_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.delenv("SPONSOR_DEMO_SEED_ENABLED", raising=False)
    get_settings.cache_clear()
    with pytest.raises(SponsorDemoSeedError):
        assert_sponsor_demo_seed_allowed()
    get_settings.cache_clear()


def test_rich_sponsor_seed_end_to_end(db_session, sponsor_demo_env, client) -> None:
    seed_demo_data(db_session, reset=False)
    with patch("app.notifications.service.notify_user") as notify:
        result = seed_rich_sponsor_demo(db_session, force=True)
    notify.assert_not_called()

    assert result["sponsors"] == 6
    assert result["skipped"] is False

    slugs = {s.slug for s in db_session.scalars(select(Sponsor)).all()}
    for spec in SPONSOR_SPECS:
        assert spec.slug in slugs

    assert (
        db_session.scalar(
            select(func.count()).select_from(SponsorTeamMember).join(
                Sponsor, SponsorTeamMember.sponsor_id == Sponsor.id
            ).where(Sponsor.slug == "neonpalm-drinks")
        )
        >= 3
    )

    neon = db_session.scalar(select(Sponsor).where(Sponsor.slug == "neonpalm-drinks"))
    assert neon is not None
    saved = db_session.scalar(
        select(func.count())
        .select_from(SponsorSavedItem)
        .where(SponsorSavedItem.sponsor_id == neon.id)
    )
    assert saved and saved >= 3

    campaigns = db_session.scalar(
        select(func.count())
        .select_from(SponsorCampaign)
        .join(Sponsor, SponsorCampaign.sponsor_id == Sponsor.id)
        .where(Sponsor.slug.in_([s.slug for s in SPONSOR_SPECS]))
    )
    assert campaigns and campaigns >= 6

    deals = db_session.scalar(
        select(func.count())
        .select_from(SponsorshipDeal)
        .join(Sponsor, SponsorshipDeal.sponsor_id == Sponsor.id)
        .where(Sponsor.slug.in_([s.slug for s in SPONSOR_SPECS]))
    )
    assert deals and deals >= 4

    deliverables = db_session.scalar(select(func.count()).select_from(SponsorshipDeliverable))
    assert deliverables and deliverables >= 6

    payments = db_session.scalar(
        select(func.count()).select_from(SponsorshipPaymentEvent)
    )
    assert payments and payments >= 2
    for ref in db_session.scalars(
        select(SponsorshipPaymentEvent.provider_reference)
    ):
        assert "demo" in str(ref).lower()

    public = public_directory_slugs(db_session)
    for slug in PUBLIC_DIRECTORY_SLUGS:
        assert slug in public
    assert "campuswave" not in public
    assert "jollof-republic" not in public

    campus = db_session.scalar(select(Sponsor).where(Sponsor.slug == "campuswave"))
    assert campus is not None
    assert campus.status == "under_review"

    feedback = db_session.scalar(
        select(func.count()).select_from(CampaignRecommendationFeedback)
    )
    assert feedback and feedback >= 2

    jollof = db_session.scalar(select(Sponsor).where(Sponsor.slug == "jollof-republic"))
    assert jollof is not None
    inq = db_session.scalar(
        select(SponsorshipInquiry).where(SponsorshipInquiry.sponsor_id == jollof.id)
    )
    assert inq is not None
    assert inq.status == "reviewing"

    nova = db_session.scalar(select(Sponsor).where(Sponsor.slug == "novaskin-beauty"))
    assert nova is not None
    owner = db_session.get(User, nova.owner_user_id)
    assert owner is not None
    report = overview_report(db_session, sponsor_id=nova.id, user=owner)
    assert report["inquiries"]["total"] >= 0
    assert "deals" in report

    payload = public_profile_safe(neon)
    assert "internal_notes" not in payload
    assert payload.get("budget_range") is None

    listed = list_public_sponsors(db_session)
    listed_slugs = {s.slug for s in listed if s.slug}
    assert PUBLIC_DIRECTORY_SLUGS.issubset(listed_slugs)

    for spec in SPONSOR_SPECS:
        ev_count = db_session.scalar(
            select(func.count())
            .select_from(Event)
            .where(Event.slug.like(f"{DEMO_EVENT_SLUG_PREFIX}spn-{spec.slug}-%"))
        )
        assert ev_count is not None and ev_count >= 5, spec.slug
        host_count = db_session.scalar(
            select(func.count(func.distinct(Event.host_id)))
            .select_from(Event)
            .where(Event.slug.like(f"{DEMO_EVENT_SLUG_PREFIX}spn-{spec.slug}-%"))
        )
        assert host_count is not None and host_count >= 2, spec.slug
        camp_count = db_session.scalar(
            select(func.count())
            .select_from(SponsorCampaign)
            .join(Sponsor, SponsorCampaign.sponsor_id == Sponsor.id)
            .where(Sponsor.slug == spec.slug)
        )
        assert camp_count is not None and camp_count >= 1, spec.slug

    def _public_sections(slug: str) -> tuple[int, int, int]:
        row = db_session.scalar(select(Sponsor).where(Sponsor.slug == slug))
        assert row is not None
        data = build_public_sponsor_profile(db_session, row)
        assert "internal_notes" not in data
        assert data.get("budget_range") is None
        assert "invoice" not in str(data).lower()
        return (
            len(data["public_campaigns"]),
            len(data["sponsored_events"]),
            len(data["partnered_hosts"]),
        )

    kora_c, kora_e, kora_h = _public_sections("korawave-pay")
    assert kora_c >= 1
    assert kora_e >= 5
    assert kora_h >= 2
    kora_titles = {
        row["event_title"]
        for row in build_public_sponsor_profile(
            db_session,
            db_session.scalar(select(Sponsor).where(Sponsor.slug == "korawave-pay")),
        )["sponsored_events"]
    }
    for expected in (
        "Creator Economy Mixer Lagos",
        "Startup Founders Night",
        "Tech Talent Social",
        "Business Builders Brunch",
        "Digital Payments Meetup",
    ):
        assert expected in kora_titles

    _neon_c, neon_e, _neon_h = _public_sections("neonpalm-drinks")
    assert neon_e >= 5
    dir = client.get("/api/v1/sponsors/public/directory")
    assert dir.status_code == 200
    neon_row = next(r for r in dir.json() if r["slug"] == "neonpalm-drinks")
    assert neon_row["sponsored_events_count"] >= 5
    assert neon_row["use_logo_fallback"] is True

    nova_c, nova_e, nova_h = _public_sections("novaskin-beauty")
    assert nova_e >= 5
    assert nova_h >= 2

    pulse_c, pulse_e, pulse_h = _public_sections("pulseframe-media")
    assert pulse_e >= 5
    assert pulse_h >= 2

    kora = db_session.scalar(select(Sponsor).where(Sponsor.slug == "korawave-pay"))
    assert kora is not None
    profile = build_public_sponsor_profile(db_session, kora)
    assert profile["public_campaigns"]
    camp = profile["public_campaigns"][0]
    assert camp["objective_label"]
    assert camp["target_categories"]
    assert camp["target_locations"]
    assert "linked_sponsored_events_count" in camp
    assert profile["partnered_hosts"]
    assert profile["partnered_hosts"][0].get("sponsored_events_together", 0) >= 1
    related = profile["related_sponsors"]
    assert len(related) >= 2
    for r in related:
        assert r.get("slug")
        assert "categories" in r

    jollof = db_session.scalar(select(Sponsor).where(Sponsor.slug == "jollof-republic"))
    assert jollof is not None
    with pytest.raises(ValueError):
        build_public_sponsor_profile(db_session, jollof)
    campus = db_session.scalar(select(Sponsor).where(Sponsor.slug == "campuswave"))
    assert campus is not None
    with pytest.raises(ValueError):
        build_public_sponsor_profile(db_session, campus)


def test_no_paystack_on_seed(db_session, sponsor_demo_env) -> None:
    seed_demo_data(db_session, reset=False)
    with patch(
        "app.payments.paystack.initialize_transaction",
    ) as init_txn, patch("app.notifications.service.notify_user") as notify:
        seed_rich_sponsor_demo(db_session, force=True)
    init_txn.assert_not_called()
    notify.assert_not_called()

    unpaid = db_session.scalar(
        select(SponsorshipInvoice).join(
            SponsorshipDeal, SponsorshipInvoice.deal_id == SponsorshipDeal.id
        ).join(Sponsor, SponsorshipDeal.sponsor_id == Sponsor.id).where(
            Sponsor.slug == "korawave-pay",
            SponsorshipDeal.title == "KoraWave Invoice Pending",
        )
    )
    assert unpaid is not None
    assert unpaid.status == "issued"
