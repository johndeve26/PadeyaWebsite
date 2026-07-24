"""Rules-based sponsor campaign recommendations."""

from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.hosts.models import Host, HostProfile, HostVerification
from app.legacy.models import HostLegacyPage, HostLegacyScore
from app.sponsor_profiles.recommendations import constants as C
from app.sponsor_profiles.recommendations.models import CampaignRecommendationDismissal
from app.sponsor_profiles.recommendations.scoring import score_opportunity, CandidateContext
from app.sponsorships.models import (
    HostSponsorshipSettings,
    Sponsor,
    SponsorCampaign,
    SponsorshipSlot,
)
from app.users.models import User
from app.users.service import get_role_by_name


def _login(client: TestClient, email: str) -> dict[str, str]:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _user(db: Session, email: str) -> User:
    u = User(
        email=email,
        password_hash=hash_password("securepass1"),
        full_name="User",
        is_active=True,
    )
    u.roles.append(get_role_by_name(db, "buyer"))
    db.add(u)
    db.commit()
    return u


def _sponsor(db: Session, owner: User) -> Sponsor:
    sp = Sponsor(
        owner_user_id=owner.id,
        user_id=owner.id,
        company_name="Rec Co",
        display_name="Rec Co",
        slug=f"rec-{owner.email.split('@')[0]}",
        sponsor_type="brand",
        contact_name="Owner",
        contact_email=owner.email,
        status="active",
        verification_status="verified",
        visibility="private",
        onboarding_status="active",
        industry="music",
    )
    db.add(sp)
    db.commit()
    return sp


def _marketplace_host(db: Session, owner: User, *, city: str = "Lagos") -> Host:
    host = Host(
        user_id=owner.id,
        display_name="Rec Host",
        slug=f"rh-{owner.email.split('@')[0]}",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, city=city))
    db.add(HostVerification(host_id=host.id, status="verified"))
    db.add(
        HostSponsorshipSettings(
            host_id=host.id,
            accepting_sponsors=True,
        )
    )
    db.add(
        HostLegacyPage(
            host_id=host.id,
            primary_category_slug="music",
            host_type_slug="dj",
        )
    )
    db.add(
        HostLegacyScore(
            host_id=host.id,
            verified_checkins=50,
            review_count=10,
            average_verified_rating=4.5,
        )
    )
    db.commit()
    return host


def _slot(db: Session, host: Host, *, price: Decimal = Decimal("50000")) -> SponsorshipSlot:
    slot = SponsorshipSlot(
        host_id=host.id,
        slot_type="title",
        title="Title",
        description="Desc",
        price=price,
        status="published",
        moderation_status="approved",
    )
    db.add(slot)
    db.commit()
    return slot


def _campaign(db: Session, sponsor: Sponsor, owner: User) -> SponsorCampaign:
    c = SponsorCampaign(
        sponsor_id=sponsor.id,
        created_by_user_id=owner.id,
        name="Rec camp",
        public_ref="rec-camp",
        objective="event_activation",
        target_categories=["music"],
        target_locations=["Lagos"],
        budget_min=Decimal("40000"),
        budget_max=Decimal("80000"),
        status="active",
    )
    db.add(c)
    db.commit()
    return c


def _ctx(host: Host, slot: SponsorshipSlot) -> CandidateContext:
    return CandidateContext(
        host_id=host.id,
        host=host,
        profile=HostProfile(host_id=host.id, city="Lagos"),
        legacy_page=HostLegacyPage(host_id=host.id, primary_category_slug="music"),
        legacy_score=HostLegacyScore(host_id=host.id, verified_checkins=40, review_count=8),
        tier=None,
        slot=slot,
        event=None,
        event_category=None,
        host_categories={"music"},
        host_city="lagos",
        slot_price=slot.price,
        upcoming_event=False,
        audience_estimate=500,
    )


def test_category_fit_increases_score(db_session: Session):
    owner = _user(db_session, "rec-cat@example.com")
    sponsor = _sponsor(db_session, owner)
    host = _marketplace_host(db_session, owner)
    slot = _slot(db_session, host)
    campaign = _campaign(db_session, sponsor, owner)
    campaign.target_categories = ["music"]
    result = score_opportunity(
        db_session,
        campaign=campaign,
        sponsor=sponsor,
        item_type="sponsorship_slot",
        item_id=slot.id,
        ctx=_ctx(host, slot),
        verified=True,
        saved_tokens=set(),
    )
    assert result.score >= C.SCORE_MIN_SHOW
    assert any(r["code"] == C.REASON_CATEGORY for r in result.reasons)


def test_location_and_budget_fit(db_session: Session):
    owner = _user(db_session, "rec-loc@example.com")
    sponsor = _sponsor(db_session, owner)
    host = _marketplace_host(db_session, owner, city="Lagos")
    slot = _slot(db_session, host, price=Decimal("60000"))
    campaign = _campaign(db_session, sponsor, owner)
    result = score_opportunity(
        db_session,
        campaign=campaign,
        sponsor=sponsor,
        item_type="sponsorship_slot",
        item_id=slot.id,
        ctx=_ctx(host, slot),
        verified=True,
        saved_tokens=set(),
    )
    codes = {r["code"] for r in result.reasons}
    assert C.REASON_LOCATION in codes
    assert C.REASON_BUDGET in codes


def test_verified_host_reason(db_session: Session):
    owner = _user(db_session, "rec-v@example.com")
    sponsor = _sponsor(db_session, owner)
    host = _marketplace_host(db_session, owner)
    slot = _slot(db_session, host)
    campaign = _campaign(db_session, sponsor, owner)
    result = score_opportunity(
        db_session,
        campaign=campaign,
        sponsor=sponsor,
        item_type="host",
        item_id=host.id,
        ctx=_ctx(host, slot),
        verified=True,
        saved_tokens=set(),
    )
    assert any(r["code"] == C.REASON_VERIFIED for r in result.reasons)


def test_inactive_host_excluded_from_api(client: TestClient, db_session: Session):
    owner = _user(db_session, "rec-in@example.com")
    host_owner = _user(db_session, "rec-in-h@example.com")
    sponsor = _sponsor(db_session, owner)
    host = _marketplace_host(db_session, host_owner)
    host.status = "archived"
    _slot(db_session, host)
    campaign = _campaign(db_session, sponsor, owner)
    headers = _login(client, owner.email)
    resp = client.get(
        f"/api/v1/sponsors/workspaces/{sponsor.id}/campaigns/{campaign.id}/recommendations",
        headers=headers,
    )
    assert resp.status_code == 200
    ids = {(i["item_type"], i["item_id"]) for i in resp.json()["items"]}
    assert ("host", str(host.id)) not in ids


def test_unpublished_slot_excluded(client: TestClient, db_session: Session):
    owner = _user(db_session, "rec-un@example.com")
    host_owner = _user(db_session, "rec-un-h@example.com")
    sponsor = _sponsor(db_session, owner)
    host = _marketplace_host(db_session, host_owner)
    slot = _slot(db_session, host)
    slot.status = "draft"
    db_session.commit()
    campaign = _campaign(db_session, sponsor, owner)
    headers = _login(client, owner.email)
    resp = client.get(
        f"/api/v1/sponsors/workspaces/{sponsor.id}/campaigns/{campaign.id}/recommendations",
        headers=headers,
    )
    assert resp.status_code == 200
    assert all(i["item_id"] != str(slot.id) for i in resp.json()["items"])


def test_dismiss_suppresses(client: TestClient, db_session: Session):
    owner = _user(db_session, "rec-dis@example.com")
    host_owner = _user(db_session, "rec-dis-h@example.com")
    sponsor = _sponsor(db_session, owner)
    host = _marketplace_host(db_session, host_owner)
    slot = _slot(db_session, host)
    campaign = _campaign(db_session, sponsor, owner)
    headers = _login(client, owner.email)
    base = client.get(
        f"/api/v1/sponsors/workspaces/{sponsor.id}/campaigns/{campaign.id}/recommendations",
        headers=headers,
    ).json()
    assert any(i["item_id"] == str(slot.id) for i in base["items"])
    client.post(
        f"/api/v1/sponsors/workspaces/{sponsor.id}/campaigns/{campaign.id}/recommendations/{slot.id}/feedback",
        headers=headers,
        json={"item_type": "sponsorship_slot", "action": "dismissed"},
    )
    after = client.get(
        f"/api/v1/sponsors/workspaces/{sponsor.id}/campaigns/{campaign.id}/recommendations",
        headers=headers,
    ).json()
    assert all(i["item_id"] != str(slot.id) for i in after["items"])


def test_safe_reason_labels_only(client: TestClient, db_session: Session):
    owner = _user(db_session, "rec-safe@example.com")
    host_owner = _user(db_session, "rec-safe-h@example.com")
    sponsor = _sponsor(db_session, owner)
    host = _marketplace_host(db_session, host_owner)
    _slot(db_session, host)
    campaign = _campaign(db_session, sponsor, owner)
    headers = _login(client, owner.email)
    resp = client.get(
        f"/api/v1/sponsors/workspaces/{sponsor.id}/campaigns/{campaign.id}/recommendations",
        headers=headers,
    )
    for item in resp.json()["items"]:
        for reason in item["reasons"]:
            assert reason["label"] in set(C.REASON_LABELS.values())
            assert "@" not in reason["label"]
            assert "buyer" not in reason["label"].lower()


def test_recommendations_api_works(client: TestClient, db_session: Session):
    owner = _user(db_session, "rec-api@example.com")
    host_owner = _user(db_session, "rec-api-h@example.com")
    sponsor = _sponsor(db_session, owner)
    host = _marketplace_host(db_session, host_owner)
    _slot(db_session, host)
    campaign = _campaign(db_session, sponsor, owner)
    headers = _login(client, owner.email)
    resp = client.get(
        f"/api/v1/sponsors/workspaces/{sponsor.id}/campaigns/{campaign.id}/recommendations",
        headers=headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()["items"]) >= 1
