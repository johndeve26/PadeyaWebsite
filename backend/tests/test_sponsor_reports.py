"""Sponsor workspace reports."""

from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.hosts.models import Host, HostProfile, HostVerification
from app.sponsorships.models import (
    HostSponsorshipSettings,
    Sponsor,
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
        company_name="Report Co",
        display_name="Report Co",
        slug=f"rep-{owner.email.split('@')[0]}",
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


def test_owner_can_view_overview_report(client: TestClient, db_session: Session):
    owner = _user(db_session, "rep-own@example.com")
    sponsor = _sponsor(db_session, owner)
    headers = _login(client, owner.email)
    resp = client.get(
        f"/api/v1/sponsors/workspaces/{sponsor.id}/reports/overview",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["sponsor_id"] == str(sponsor.id)
    assert "inquiries" in body


def test_non_member_cannot_view_report(client: TestClient, db_session: Session):
    owner = _user(db_session, "rep-no@example.com")
    stranger = _user(db_session, "rep-str@example.com")
    sponsor = _sponsor(db_session, owner)
    denied = client.get(
        f"/api/v1/sponsors/workspaces/{sponsor.id}/reports/overview",
        headers=_login(client, stranger.email),
    )
    assert denied.status_code in (403, 404)


def test_report_aggregates_inquiries(client: TestClient, db_session: Session):
    owner = _user(db_session, "rep-inq@example.com")
    host_owner = _user(db_session, "rep-inq-h@example.com")
    host = Host(
        user_id=host_owner.id,
        display_name="H",
        slug="rep-inq-host",
        status="active",
    )
    db_session.add(host)
    db_session.flush()
    db_session.add(HostProfile(host_id=host.id, city="Lagos"))
    db_session.add(HostVerification(host_id=host.id, status="verified"))
    db_session.add(
        HostSponsorshipSettings(host_id=host.id, accepting_sponsors=True)
    )
    sponsor = _sponsor(db_session, owner)
    slot = SponsorshipSlot(
        host_id=host.id,
        slot_type="title",
        title="T",
        description="D",
        price=Decimal("1000"),
        status="published",
        moderation_status="approved",
    )
    db_session.add(slot)
    db_session.flush()
    db_session.add(
        SponsorshipInquiry(
            slot_id=slot.id,
            sponsor_id=sponsor.id,
            company_name="Report Co",
            contact_name="Owner",
            contact_email=owner.email,
            message="Hello world inquiry text",
            status="accepted",
        )
    )
    db_session.add(
        SponsorshipInquiry(
            slot_id=slot.id,
            sponsor_id=sponsor.id,
            company_name="Report Co",
            contact_name="Owner",
            contact_email=owner.email,
            message="Pending one",
            status="new",
        )
    )
    db_session.commit()
    headers = _login(client, owner.email)
    body = client.get(
        f"/api/v1/sponsors/workspaces/{sponsor.id}/reports/overview",
        headers=headers,
    ).json()
    assert body["inquiries"]["total"] == 2
    assert body["inquiries"]["accepted"] == 1
    assert body["inquiries"]["pending"] == 1


def test_report_does_not_expose_fan_pii(client: TestClient, db_session: Session):
    owner = _user(db_session, "rep-pii@example.com")
    sponsor = _sponsor(db_session, owner)
    headers = _login(client, owner.email)
    raw = client.get(
        f"/api/v1/sponsors/workspaces/{sponsor.id}/reports/overview",
        headers=headers,
    ).text
    assert "contact_email" not in raw
    assert "fan@" not in raw.lower()
    assert "attendee" not in raw.lower()
    assert "buyer" not in raw.lower()
