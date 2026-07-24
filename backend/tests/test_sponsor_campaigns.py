"""Sponsor campaigns."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.hosts.models import Host, HostProfile, HostVerification
from app.sponsorships.models import (
    CampaignSavedItem,
    Sponsor,
    SponsorCampaign,
    SponsorSavedItem,
    SponsorTeamMember,
    SponsorshipInquiry,
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


def _user(db: Session, email: str, *, role: str = "buyer") -> User:
    u = User(
        email=email,
        password_hash=hash_password("securepass1"),
        full_name="User",
        is_active=True,
    )
    u.roles.append(get_role_by_name(db, role))
    db.add(u)
    db.commit()
    return u


def _sponsor(db: Session, owner: User) -> Sponsor:
    sp = Sponsor(
        owner_user_id=owner.id,
        user_id=owner.id,
        company_name="Camp Co",
        display_name="Camp Co",
        slug=f"camp-{owner.email.split('@')[0]}",
        sponsor_type="brand",
        contact_name="Owner",
        contact_email=owner.email,
        status="active",
        verification_status="verified",
        visibility="private",
        onboarding_status="active",
    )
    db.add(sp)
    db.commit()
    return sp


def _verified_host(db: Session, owner: User) -> Host:
    host = Host(
        user_id=owner.id,
        display_name="Camp Host",
        slug=f"ch-{owner.email.split('@')[0]}",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, city="Lagos"))
    db.add(HostVerification(host_id=host.id, status="verified"))
    db.commit()
    return host


def _published_slot(db: Session, host: Host) -> SponsorshipSlot:
    slot = SponsorshipSlot(
        host_id=host.id,
        slot_type="title",
        title="Title slot",
        description="Desc",
        price=1000,
        status="published",
        moderation_status="approved",
    )
    db.add(slot)
    db.commit()
    return slot


def test_owner_can_create_campaign(client: TestClient, db_session: Session):
    owner = _user(db_session, "camp-own@example.com")
    sponsor = _sponsor(db_session, owner)
    headers = _login(client, owner.email)

    created = client.post(
        f"/api/v1/sponsors/workspaces/{sponsor.id}/campaigns",
        headers=headers,
        json={"name": "Summer push", "objective": "brand_awareness"},
    )
    assert created.status_code == 201, created.text
    assert created.json()["status"] == "draft"
    assert created.json()["visibility"] == "private"


def test_campaign_manager_can_create(client: TestClient, db_session: Session):
    owner = _user(db_session, "camp-mo@example.com")
    mgr = _user(db_session, "camp-mgr@example.com")
    sponsor = _sponsor(db_session, owner)
    db_session.add(
        SponsorTeamMember(
            sponsor_id=sponsor.id,
            user_id=mgr.id,
            role="campaign_manager",
            status="active",
        )
    )
    db_session.commit()

    created = client.post(
        f"/api/v1/sponsors/workspaces/{sponsor.id}/campaigns",
        headers=_login(client, mgr.email),
        json={"name": "Mgr camp", "objective": "lead_generation"},
    )
    assert created.status_code == 201


def test_viewer_cannot_create(client: TestClient, db_session: Session):
    owner = _user(db_session, "camp-vo@example.com")
    viewer = _user(db_session, "camp-vw@example.com")
    sponsor = _sponsor(db_session, owner)
    db_session.add(
        SponsorTeamMember(
            sponsor_id=sponsor.id,
            user_id=viewer.id,
            role="viewer",
            status="active",
        )
    )
    db_session.commit()

    denied = client.post(
        f"/api/v1/sponsors/workspaces/{sponsor.id}/campaigns",
        headers=_login(client, viewer.email),
        json={"name": "Nope", "objective": "other"},
    )
    assert denied.status_code == 403


def test_non_member_cannot_access(client: TestClient, db_session: Session):
    owner = _user(db_session, "camp-no@example.com")
    stranger = _user(db_session, "camp-str@example.com")
    sponsor = _sponsor(db_session, owner)

    denied = client.get(
        f"/api/v1/sponsors/workspaces/{sponsor.id}/campaigns",
        headers=_login(client, stranger.email),
    )
    assert denied.status_code in (403, 404)


def test_attach_saved_item_idempotent(client: TestClient, db_session: Session):
    owner = _user(db_session, "camp-sv@example.com")
    host_owner = _user(db_session, "camp-h@example.com")
    host = _verified_host(db_session, host_owner)
    sponsor = _sponsor(db_session, owner)
    saved = SponsorSavedItem(
        sponsor_id=sponsor.id,
        saved_by_user_id=owner.id,
        item_type="host",
        item_id=host.id,
    )
    db_session.add(saved)
    db_session.commit()
    headers = _login(client, owner.email)

    camp = client.post(
        f"/api/v1/sponsors/workspaces/{sponsor.id}/campaigns",
        headers=headers,
        json={"name": "With saved", "objective": "event_activation"},
    ).json()
    cid = camp["id"]
    body = {"sponsor_saved_item_id": str(saved.id)}
    first = client.post(
        f"/api/v1/sponsors/workspaces/{sponsor.id}/campaigns/{cid}/saved-items",
        headers=headers,
        json=body,
    )
    second = client.post(
        f"/api/v1/sponsors/workspaces/{sponsor.id}/campaigns/{cid}/saved-items",
        headers=headers,
        json=body,
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert db_session.query(CampaignSavedItem).count() == 1


def test_inquiry_links_to_campaign(client: TestClient, db_session: Session):
    owner = _user(db_session, "camp-inq@example.com")
    host_owner = _user(db_session, "camp-ih@example.com")
    host = _verified_host(db_session, host_owner)
    slot = _published_slot(db_session, host)
    sponsor = _sponsor(db_session, owner)
    headers = _login(client, owner.email)
    camp = client.post(
        f"/api/v1/sponsors/workspaces/{sponsor.id}/campaigns",
        headers=headers,
        json={"name": "Inq camp", "objective": "product_launch"},
    ).json()

    inq = client.post(
        f"/api/v1/sponsorships/public/slots/{slot.id}/inquire",
        headers=headers,
        json={
            "company_name": sponsor.company_name,
            "contact_name": "Owner",
            "contact_email": owner.email,
            "message": "We want to sponsor this slot please",
            "campaign_id": camp["id"],
            "sponsor_id": str(sponsor.id),
        },
    )
    assert inq.status_code in (200, 201), inq.text
    row = db_session.get(SponsorshipInquiry, uuid.UUID(inq.json()["id"]))
    assert row is not None
    assert str(row.campaign_id) == camp["id"]


def test_archived_campaign_read_only(client: TestClient, db_session: Session):
    owner = _user(db_session, "camp-ar@example.com")
    sponsor = _sponsor(db_session, owner)
    headers = _login(client, owner.email)
    camp = client.post(
        f"/api/v1/sponsors/workspaces/{sponsor.id}/campaigns",
        headers=headers,
        json={"name": "Archive me", "objective": "other"},
    ).json()
    cid = camp["id"]
    client.post(
        f"/api/v1/sponsors/workspaces/{sponsor.id}/campaigns/{cid}/archive",
        headers=headers,
    )
    denied = client.patch(
        f"/api/v1/sponsors/workspaces/{sponsor.id}/campaigns/{cid}",
        headers=headers,
        json={"name": "New name"},
    )
    assert denied.status_code == 403


def test_admin_moderates_public_case_study(client: TestClient, db_session: Session):
    owner = _user(db_session, "camp-ad@example.com")
    admin = _user(db_session, "camp-admin@example.com", role="moderation")
    sponsor = _sponsor(db_session, owner)
    headers = _login(client, owner.email)
    camp = client.post(
        f"/api/v1/sponsors/workspaces/{sponsor.id}/campaigns",
        headers=headers,
        json={
            "name": "Public story",
            "objective": "brand_awareness",
            "visibility": "public_case_study",
        },
    ).json()
    cid = camp["id"]
    activated = client.post(
        f"/api/v1/sponsors/workspaces/{sponsor.id}/campaigns/{cid}/activate",
        headers=headers,
    )
    assert activated.json()["status"] == "under_review"

    approve = client.post(
        f"/api/v1/admin/sponsor-campaigns/{cid}/approve",
        headers=_login(client, admin.email),
    )
    assert approve.status_code == 200, approve.text
    assert approve.json()["moderation_status"] == "approved"
    assert approve.json()["status"] == "active"


def test_private_campaign_not_in_public_api(client: TestClient, db_session: Session):
    owner = _user(db_session, "camp-pv@example.com")
    sponsor = _sponsor(db_session, owner)
    sponsor.visibility = "public"
    db_session.commit()
    headers = _login(client, owner.email)
    camp = client.post(
        f"/api/v1/sponsors/workspaces/{sponsor.id}/campaigns",
        headers=headers,
        json={"name": "Secret", "objective": "other", "visibility": "private"},
    ).json()

    public = client.get(f"/api/v1/sponsors/public/{sponsor.slug}")
    if public.status_code == 200:
        assert "Secret" not in str(public.json())
    assert camp["name"] == "Secret"
