"""Sponsor team invites and membership."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.sponsorships.models import Sponsor, SponsorTeamInvite, SponsorTeamMember
from app.users.models import User
from app.users.service import get_role_by_name


def _login(client: TestClient, email: str) -> dict[str, str]:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _buyer(db: Session, email: str, name: str = "User") -> User:
    user = User(
        email=email,
        password_hash=hash_password("securepass1"),
        full_name=name,
        is_active=True,
    )
    user.roles.append(get_role_by_name(db, "buyer"))
    db.add(user)
    db.commit()
    return user


def _sponsor_profile(db: Session, owner: User, name: str = "Acme Sponsor") -> Sponsor:
    sponsor = Sponsor(
        owner_user_id=owner.id,
        user_id=owner.id,
        company_name=name,
        display_name=name,
        slug=f"team-{owner.email.split('@')[0]}",
        sponsor_type="brand",
        contact_name=owner.full_name or name,
        contact_email=owner.email,
        status="active",
        verification_status="verified",
        visibility="private",
        onboarding_status="active",
    )
    db.add(sponsor)
    db.commit()
    return sponsor


def test_owner_can_invite_member(client: TestClient, db_session: Session):
    owner = _buyer(db_session, "st-owner@example.com", "Owner")
    sponsor = _sponsor_profile(db_session, owner)
    headers = _login(client, owner.email)

    created = client.post(
        f"/api/v1/sponsors/workspaces/{sponsor.id}/team/invites",
        headers=headers,
        json={"email": "newmember@example.com", "role": "viewer"},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["invite"]["email"] == "newmember@example.com"
    assert body["invite"]["status"] == "pending"

    listing = client.get(
        f"/api/v1/sponsors/workspaces/{sponsor.id}/team",
        headers=headers,
    )
    assert listing.status_code == 200
    assert len(listing.json()["invites"]) == 1


def test_non_admin_cannot_invite(client: TestClient, db_session: Session):
    owner = _buyer(db_session, "st-own2@example.com")
    mgr = _buyer(db_session, "st-mgr@example.com", "Manager")
    sponsor = _sponsor_profile(db_session, owner, "Brand Two")
    db_session.add(
        SponsorTeamMember(
            sponsor_id=sponsor.id,
            user_id=mgr.id,
            role="campaign_manager",
            status="active",
        )
    )
    db_session.commit()

    denied = client.post(
        f"/api/v1/sponsors/workspaces/{sponsor.id}/team/invites",
        headers=_login(client, mgr.email),
        json={"email": "x@example.com", "role": "viewer"},
    )
    assert denied.status_code == 403


def test_role_change_works(client: TestClient, db_session: Session):
    owner = _buyer(db_session, "st-role@example.com")
    member = _buyer(db_session, "st-member@example.com", "Member")
    sponsor = _sponsor_profile(db_session, owner, "Role Co")
    row = SponsorTeamMember(
        sponsor_id=sponsor.id,
        user_id=member.id,
        role="viewer",
        status="active",
    )
    db_session.add(row)
    db_session.commit()

    patched = client.patch(
        f"/api/v1/sponsors/workspaces/{sponsor.id}/team/members/{row.id}",
        headers=_login(client, owner.email),
        json={"role": "admin"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["role"] == "admin"


def test_cannot_remove_owner(client: TestClient, db_session: Session):
    owner = _buyer(db_session, "st-rem@example.com")
    sponsor = _sponsor_profile(db_session, owner, "Remove Co")
    row = SponsorTeamMember(
        sponsor_id=sponsor.id,
        user_id=owner.id,
        role="admin",
        status="active",
    )
    db_session.add(row)
    db_session.commit()

    denied = client.delete(
        f"/api/v1/sponsors/workspaces/{sponsor.id}/team/members/{row.id}",
        headers=_login(client, owner.email),
    )
    assert denied.status_code == 400


def test_removed_member_loses_workspace(client: TestClient, db_session: Session):
    owner = _buyer(db_session, "st-out@example.com")
    member = _buyer(db_session, "st-out-m@example.com")
    sponsor = _sponsor_profile(db_session, owner, "Out Co")
    row = SponsorTeamMember(
        sponsor_id=sponsor.id,
        user_id=member.id,
        role="viewer",
        status="active",
    )
    db_session.add(row)
    db_session.commit()

    removed = client.delete(
        f"/api/v1/sponsors/workspaces/{sponsor.id}/team/members/{row.id}",
        headers=_login(client, owner.email),
    )
    assert removed.status_code == 204

    workspaces = client.get(
        "/api/v1/sponsors/workspaces",
        headers=_login(client, member.email),
    )
    assert workspaces.status_code == 200
    assert not any(w["sponsor_id"] == str(sponsor.id) for w in workspaces.json())


def test_accept_invite_grants_workspace(client: TestClient, db_session: Session):
    owner = _buyer(db_session, "st-acc@example.com")
    invitee = _buyer(db_session, "st-invitee@example.com")
    sponsor = _sponsor_profile(db_session, owner, "Accept Co")
    raw = "test-token-accept-sponsor-team"
    from app.sponsor_profiles.team_service import _hash_token

    inv = SponsorTeamInvite(
        sponsor_id=sponsor.id,
        email=invitee.email,
        role="viewer",
        token_hash=_hash_token(raw),
        status="pending",
        invited_by_user_id=owner.id,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    db_session.add(inv)
    db_session.commit()

    accepted = client.post(
        f"/api/v1/sponsors/team/invites/{raw}/accept",
        headers=_login(client, invitee.email),
    )
    assert accepted.status_code == 200, accepted.text

    workspaces = client.get(
        "/api/v1/sponsors/workspaces",
        headers=_login(client, invitee.email),
    )
    assert any(w["sponsor_id"] == str(sponsor.id) for w in workspaces.json())
