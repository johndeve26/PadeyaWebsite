"""Sponsor profile workspace backend tests."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.sponsorships.models import Sponsor
from app.users.models import User
from app.users.service import get_role_by_name


def _login(client: TestClient, email: str) -> dict[str, str]:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _buyer(db: Session, email: str = "sp-buyer@example.com") -> User:
    user = User(
        email=email,
        password_hash=hash_password("securepass1"),
        full_name="Buyer",
        is_active=True,
    )
    user.roles.append(get_role_by_name(db, "buyer"))
    db.add(user)
    db.commit()
    return user


def test_create_sponsor_profile(client: TestClient, db_session: Session):
    user = _buyer(db_session, "sp-create@example.com")
    headers = _login(client, user.email)
    created = client.post(
        "/api/v1/sponsors/profiles",
        headers=headers,
        json={
            "display_name": "Acme Lagos",
            "sponsor_type": "brand",
            "industry": "Beverages",
            "categories": ["nightlife"],
            "submit_for_review": True,
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["display_name"] == "Acme Lagos"
    assert body["verification_status"] == "pending"
    assert body["status"] == "under_review"
    assert body["slug"]


def test_sponsor_slug_unique(client: TestClient, db_session: Session):
    user = _buyer(db_session, "sp-slug@example.com")
    headers = _login(client, user.email)
    first = client.post(
        "/api/v1/sponsors/profiles",
        headers=headers,
        json={"display_name": "Same Name Co", "sponsor_type": "business"},
    )
    assert first.status_code == 201, first.text
    slug1 = first.json()["slug"]

    user2 = _buyer(db_session, "sp-slug2@example.com")
    headers2 = _login(client, user2.email)
    second = client.post(
        "/api/v1/sponsors/profiles",
        headers=headers2,
        json={"display_name": "Same Name Co", "sponsor_type": "business"},
    )
    assert second.status_code == 201, second.text
    slug2 = second.json()["slug"]
    assert slug1 != slug2


def test_owner_can_edit_sponsor(client: TestClient, db_session: Session):
    user = _buyer(db_session, "sp-edit@example.com")
    headers = _login(client, user.email)
    created = client.post(
        "/api/v1/sponsors/profiles",
        headers=headers,
        json={"display_name": "Editable Brand", "sponsor_type": "agency"},
    )
    assert created.status_code == 201
    sponsor_id = created.json()["id"]

    patched = client.patch(
        "/api/v1/sponsors/me",
        headers=headers,
        params={"sponsor_id": sponsor_id},
        json={"short_bio": "We sponsor live experiences."},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["short_bio"] == "We sponsor live experiences."


def test_non_owner_cannot_edit_sponsor(client: TestClient, db_session: Session):
    owner = _buyer(db_session, "sp-own@example.com")
    other = _buyer(db_session, "sp-other@example.com")
    headers = _login(client, owner.email)
    created = client.post(
        "/api/v1/sponsors/profiles",
        headers=headers,
        json={"display_name": "Private Brand", "sponsor_type": "brand"},
    )
    sponsor_id = created.json()["id"]

    denied = client.patch(
        "/api/v1/sponsors/me",
        headers=_login(client, other.email),
        params={"sponsor_id": sponsor_id},
        json={"short_bio": "Hacked"},
    )
    assert denied.status_code in (403, 404)


def test_public_directory_hides_unapproved(client: TestClient, db_session: Session):
    user = _buyer(db_session, "sp-pub@example.com")
    headers = _login(client, user.email)
    created = client.post(
        "/api/v1/sponsors/profiles",
        headers=headers,
        json={"display_name": "Hidden Co", "sponsor_type": "brand"},
    )
    slug = created.json()["slug"]

    listing = client.get("/api/v1/sponsors/public/directory")
    assert listing.status_code == 200
    assert not any(row["slug"] == slug for row in listing.json())

    profile = client.get(f"/api/v1/sponsors/public/{slug}")
    assert profile.status_code == 404


def test_public_shows_verified_active(client: TestClient, db_session: Session):
    sponsor = Sponsor(
        owner_user_id=None,
        user_id=None,
        company_name="Public Verified",
        display_name="Public Verified",
        slug="public-verified-co",
        sponsor_type="brand",
        contact_name="PR",
        contact_email="pr@verified.example.com",
        status="active",
        verification_status="verified",
        visibility="public",
        onboarding_status="active",
        short_bio="Verified sponsor",
    )
    db_session.add(sponsor)
    db_session.commit()

    listing = client.get("/api/v1/sponsors/public/directory")
    assert any(row["slug"] == "public-verified-co" for row in listing.json())

    profile = client.get("/api/v1/sponsors/public/public-verified-co")
    assert profile.status_code == 200
    assert profile.json()["verified"] is True
    assert profile.json()["show_contact_cta"] is True


def test_public_directory_includes_partnership_stats(client: TestClient, db_session: Session):
    sponsor = Sponsor(
        owner_user_id=None,
        user_id=None,
        company_name="Directory Stats Co",
        display_name="Directory Stats Co",
        slug="directory-stats-co",
        sponsor_type="brand",
        contact_name="PR",
        contact_email="stats@verified.example.com",
        status="active",
        verification_status="verified",
        visibility="public",
        onboarding_status="active",
        short_bio="Stats on directory cards only.",
        categories=["tech"],
        target_locations=["Lagos"],
        logo_url="/demo/sponsors/acme-events.svg",
    )
    db_session.add(sponsor)
    db_session.commit()

    listing = client.get("/api/v1/sponsors/public/directory")
    assert listing.status_code == 200
    row = next(r for r in listing.json() if r["slug"] == "directory-stats-co")
    assert row["use_logo_fallback"] is True
    assert row.get("logo_url") is None
    assert "public_campaigns_count" in row
    assert "sponsored_events_count" in row
    assert "partnered_hosts_count" in row
    assert "budget_range" not in row
    assert "internal_notes" not in row


def test_admin_verify_and_restrict(client: TestClient, db_session: Session):
    user = _buyer(db_session, "sp-admin@example.com")
    headers = _login(client, user.email)
    created = client.post(
        "/api/v1/sponsors/profiles",
        headers=headers,
        json={
            "display_name": "Review Me",
            "sponsor_type": "ngo",
            "submit_for_review": True,
        },
    )
    sponsor_id = created.json()["id"]

    admin = User(
        email="sp-admin-user@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Admin",
        is_active=True,
    )
    admin.roles.append(get_role_by_name(db_session, "moderation"))
    db_session.add(admin)
    db_session.commit()
    admin_headers = _login(client, admin.email)

    listed = client.get("/api/v1/admin/sponsors", headers=admin_headers)
    assert listed.status_code == 200
    assert any(row["id"] == sponsor_id for row in listed.json())

    approved = client.post(
        f"/api/v1/admin/sponsors/{sponsor_id}/verify",
        headers=admin_headers,
        json={"action": "approve", "notes": "Looks legit"},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["verification_status"] == "verified"

    restricted = client.post(
        f"/api/v1/admin/sponsors/{sponsor_id}/status",
        headers=admin_headers,
        json={"status": "restricted", "notes": "Policy review"},
    )
    assert restricted.status_code == 200
    assert restricted.json()["status"] == "restricted"


def test_sponsor_cannot_read_fan_private_data(client: TestClient, db_session: Session):
    """Sponsor workspace APIs must not expose fan passport private endpoints."""
    user = _buyer(db_session, "sp-fan@example.com")
    headers = _login(client, user.email)
    client.post(
        "/api/v1/sponsors/profiles",
        headers=headers,
        json={"display_name": "Fan Probe", "sponsor_type": "brand"},
    )
    denied = client.get("/api/v1/passport/admin/hidden", headers=headers)
    assert denied.status_code in (403, 404, 405)


def _public_verified_sponsor(db: Session, **overrides) -> Sponsor:
    data: dict = {
        "owner_user_id": None,
        "user_id": None,
        "company_name": "Rich Public Co",
        "display_name": "Rich Public Co",
        "slug": "rich-public-co",
        "sponsor_type": "brand",
        "contact_name": "PR",
        "contact_email": "rich@verified.example.com",
        "status": "active",
        "verification_status": "verified",
        "visibility": "public",
        "onboarding_status": "active",
        "short_bio": "Partners with hosts on Pàdéyá.",
        "description": "Full public description.",
        "industry": "Fintech",
        "categories": ["tech", "business"],
        "target_locations": ["Lagos", "Abuja"],
        "campaign_goals": ["lead_generation"],
        "cover_image_url": "/demo/sponsors/acme-events.svg",
        "internal_notes": "SECRET",
        "budget_range": "₦5M–₦10M",
    }
    data.update(overrides)
    sponsor = Sponsor(**data)
    db.add(sponsor)
    db.commit()
    db.refresh(sponsor)
    return sponsor


def test_public_profile_rich_payload_is_privacy_safe(client: TestClient, db_session: Session):
    user = _buyer(db_session, "sp-rich@example.com")
    sponsor = _public_verified_sponsor(db_session)

    from app.sponsorships.models import SponsorCampaign

    db_session.add(
        SponsorCampaign(
            sponsor_id=sponsor.id,
            created_by_user_id=user.id,
            name="Private draft",
            public_ref="private-draft",
            objective="brand_awareness",
            visibility="private",
            moderation_status="not_required",
            status="draft",
        )
    )
    db_session.add(
        SponsorCampaign(
            sponsor_id=sponsor.id,
            created_by_user_id=user.id,
            name="Pending case study",
            public_ref="pending-case",
            objective="brand_awareness",
            visibility="public_case_study",
            moderation_status="pending",
            status="active",
        )
    )
    db_session.add(
        SponsorCampaign(
            sponsor_id=sponsor.id,
            created_by_user_id=user.id,
            name="Approved case study",
            public_ref="approved-case",
            objective="lead_generation",
            visibility="public_case_study",
            moderation_status="approved",
            status="active",
            target_categories=["tech"],
            description="Public-safe summary only.",
        )
    )
    db_session.commit()

    resp = client.get("/api/v1/sponsors/public/rich-public-co")
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["use_cover_fallback"] is True
    assert body["cover_image_url"] is None
    assert "summary_cards" in body
    assert "public_campaigns" in body
    assert "sponsored_events" in body
    assert "partnered_hosts" in body
    assert len(body["public_campaigns"]) == 1
    assert body["public_campaigns"][0]["name"] == "Approved case study"
    assert "budget" not in str(body).lower()
    assert "internal_notes" not in body
    assert body.get("internal_notes") is None
    assert body.get("budget_range") is None


def test_public_profile_rejects_acme_style_cover(client: TestClient, db_session: Session):
    _public_verified_sponsor(
        db_session,
        slug="korawave-cover-test",
        display_name="KoraWave Cover Test",
        company_name="KoraWave Cover Test",
        cover_image_url="/brand/sponsors/acme-events.svg",
    )
    resp = client.get("/api/v1/sponsors/public/korawave-cover-test")
    assert resp.status_code == 200
    assert resp.json()["use_cover_fallback"] is True
    assert resp.json()["cover_image_url"] is None
