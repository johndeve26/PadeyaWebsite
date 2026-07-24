"""Sponsor saved items."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.hosts.models import Host, HostProfile, HostVerification
from app.sponsorships.models import Sponsor, SponsorSavedItem, SponsorTeamMember
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


def _verified_host(db: Session, owner: User) -> Host:
    host = Host(
        user_id=owner.id,
        display_name="Saved Host",
        slug=f"sv-{owner.email.split('@')[0]}",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, city="Lagos"))
    db.add(HostVerification(host_id=host.id, status="verified"))
    db.commit()
    return host


def _sponsor(db: Session, owner: User) -> Sponsor:
    sp = Sponsor(
        owner_user_id=owner.id,
        user_id=owner.id,
        company_name="Save Co",
        display_name="Save Co",
        slug=f"save-{owner.email.split('@')[0]}",
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


def test_member_can_save_host(client: TestClient, db_session: Session):
    owner = _user(db_session, "sv-own@example.com")
    host_owner = _user(db_session, "sv-host@example.com")
    host = _verified_host(db_session, host_owner)
    sponsor = _sponsor(db_session, owner)
    headers = _login(client, owner.email)

    created = client.post(
        f"/api/v1/sponsors/workspaces/{sponsor.id}/saved",
        headers=headers,
        json={"item_type": "host", "item_id": str(host.id), "note": "Watch list"},
    )
    assert created.status_code == 201, created.text
    assert created.json()["available"] is True
    assert created.json()["title"] == "Saved Host"


def test_duplicate_save_idempotent(client: TestClient, db_session: Session):
    owner = _user(db_session, "sv-dup@example.com")
    host_owner = _user(db_session, "sv-dup-h@example.com")
    host = _verified_host(db_session, host_owner)
    sponsor = _sponsor(db_session, owner)
    headers = _login(client, owner.email)
    body = {"item_type": "host", "item_id": str(host.id)}

    first = client.post(
        f"/api/v1/sponsors/workspaces/{sponsor.id}/saved",
        headers=headers,
        json=body,
    )
    second = client.post(
        f"/api/v1/sponsors/workspaces/{sponsor.id}/saved",
        headers=headers,
        json=body,
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert db_session.query(SponsorSavedItem).count() == 1


def test_unauthorized_cannot_save(client: TestClient, db_session: Session):
    owner = _user(db_session, "sv-o@example.com")
    stranger = _user(db_session, "sv-str@example.com")
    host_owner = _user(db_session, "sv-h2@example.com")
    host = _verified_host(db_session, host_owner)
    sponsor = _sponsor(db_session, owner)

    denied = client.post(
        f"/api/v1/sponsors/workspaces/{sponsor.id}/saved",
        headers=_login(client, stranger.email),
        json={"item_type": "host", "item_id": str(host.id)},
    )
    assert denied.status_code in (403, 404)


def test_viewer_cannot_edit_note(client: TestClient, db_session: Session):
    owner = _user(db_session, "sv-vo@example.com")
    viewer = _user(db_session, "sv-vw@example.com")
    host_owner = _user(db_session, "sv-vh@example.com")
    host = _verified_host(db_session, host_owner)
    sponsor = _sponsor(db_session, owner)
    db_session.add(
        SponsorTeamMember(
            sponsor_id=sponsor.id,
            user_id=viewer.id,
            role="viewer",
            status="active",
        )
    )
    saved = SponsorSavedItem(
        sponsor_id=sponsor.id,
        saved_by_user_id=owner.id,
        item_type="host",
        item_id=host.id,
        note="original",
    )
    db_session.add(saved)
    db_session.commit()

    denied = client.patch(
        f"/api/v1/sponsors/workspaces/{sponsor.id}/saved/{saved.id}",
        headers=_login(client, viewer.email),
        json={"note": "nope"},
    )
    assert denied.status_code == 403

    ok = client.get(
        f"/api/v1/sponsors/workspaces/{sponsor.id}/saved",
        headers=_login(client, viewer.email),
    )
    assert ok.status_code == 200


def test_unavailable_host_hidden_safe(client: TestClient, db_session: Session):
    owner = _user(db_session, "sv-hide@example.com")
    host_owner = _user(db_session, "sv-hide-h@example.com")
    host = _verified_host(db_session, host_owner)
    sponsor = _sponsor(db_session, owner)
    saved = SponsorSavedItem(
        sponsor_id=sponsor.id,
        saved_by_user_id=owner.id,
        item_type="host",
        item_id=host.id,
    )
    db_session.add(saved)
    host.status = "archived"
    db_session.commit()

    listing = client.get(
        f"/api/v1/sponsors/workspaces/{sponsor.id}/saved",
        headers=_login(client, owner.email),
    )
    item = listing.json()["items"][0]
    assert item["available"] is False
    assert item["title"] is None
