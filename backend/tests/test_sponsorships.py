"""Sponsorship marketplace: slots, inquiries, moderation, visibility."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.hosts.models import Host, HostProfile, HostTeamMember, HostVerification
from app.sponsorships.models import (
    HostSponsorshipSettings,
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


def _seed_host(
    db: Session,
    *,
    email: str = "sp-host@example.com",
    slug: str = "sp-host",
    verified: bool = True,
    accepting_sponsors: bool = True,
) -> tuple[Host, User]:
    host_user = User(
        email=email,
        password_hash=hash_password("securepass1"),
        full_name="Sponsor Host",
        is_active=True,
    )
    host_user.roles.append(get_role_by_name(db, "host"))
    db.add(host_user)
    db.flush()
    host = Host(
        user_id=host_user.id,
        display_name="Sponsor Host",
        slug=slug,
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, bio="Verified host for sponsors", city="Lagos"))
    db.add(
        HostVerification(
            host_id=host.id,
            status="verified" if verified else "pending",
            reviewed_at=datetime.now(UTC) if verified else None,
        )
    )
    db.add(
        HostSponsorshipSettings(
            host_id=host.id,
            accepting_sponsors=accepting_sponsors,
        )
    )
    db.commit()
    return host, host_user


def test_create_sponsorship_slot(client: TestClient, db_session: Session):
    host, host_user = _seed_host(db_session)
    headers = _login(client, host_user.email)

    created = client.post(
        "/api/v1/sponsorships/host/slots",
        headers=headers,
        json={
            "slot_type": "logo_event_page",
            "title": "Event page logo",
            "description": "Logo placement on the public event page for one night.",
            "price": "250000.00",
            "status": "published",
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["status"] == "published"
    assert body["host_verified"] is True
    assert body["slot_type"] == "logo_event_page"
    assert db_session.query(SponsorshipSlot).count() == 1


def test_host_permission(client: TestClient, db_session: Session):
    host, host_user = _seed_host(db_session, email="sp-h2@example.com", slug="sp-h2")
    buyer = User(
        email="sp-buyer@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Buyer",
        is_active=True,
    )
    buyer.roles.append(get_role_by_name(db_session, "buyer"))
    db_session.add(buyer)
    db_session.commit()

    denied = client.post(
        "/api/v1/sponsorships/host/slots",
        headers=_login(client, buyer.email),
        json={
            "slot_type": "booth_at_event",
            "title": "Booth",
            "description": "On-site booth for product sampling and brand activation.",
            "price": "100000",
        },
    )
    assert denied.status_code in (403, 404)

    ok = client.post(
        "/api/v1/sponsorships/host/slots",
        headers=_login(client, host_user.email),
        json={
            "slot_type": "booth_at_event",
            "title": "Booth",
            "description": "On-site booth for product sampling and brand activation.",
            "price": "100000",
            "status": "draft",
        },
    )
    assert ok.status_code == 201, ok.text
    assert host.id


def test_inquiry_submission(client: TestClient, db_session: Session):
    host, host_user = _seed_host(db_session, email="sp-inq@example.com", slug="sp-inq")
    headers = _login(client, host_user.email)
    created = client.post(
        "/api/v1/sponsorships/host/slots",
        headers=headers,
        json={
            "slot_type": "banner_legacy_page",
            "title": "Legacy banner",
            "description": "Banner placement on the host Legacy Page for 30 days.",
            "price": "180000",
            "status": "published",
        },
    )
    assert created.status_code == 201, created.text
    slot_id = created.json()["id"]

    inquiry = client.post(
        f"/api/v1/sponsorships/public/slots/{slot_id}/inquire",
        json={
            "company_name": "Acme Brands",
            "contact_name": "Ada Brand",
            "contact_email": "ada@acme.example.com",
            "message": "We want to sponsor your next three nightlife events in Lagos.",
            "proposed_budget": "200000",
        },
    )
    assert inquiry.status_code == 201, inquiry.text
    assert inquiry.json()["status"] == "new"
    assert db_session.query(SponsorshipInquiry).count() == 1

    host_list = client.get(
        "/api/v1/sponsorships/host/inquiries", headers=headers
    )
    assert host_list.status_code == 200
    assert len(host_list.json()) == 1
    assert host_list.json()[0]["company_name"] == "Acme Brands"

    updated = client.patch(
        f"/api/v1/sponsorships/host/inquiries/{inquiry.json()['id']}",
        headers=headers,
        json={"status": "reviewing", "host_note": "Looks promising"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "reviewing"


def test_admin_moderation(client: TestClient, db_session: Session):
    host, host_user = _seed_host(db_session, email="sp-mod@example.com", slug="sp-mod")
    headers = _login(client, host_user.email)
    created = client.post(
        "/api/v1/sponsorships/host/slots",
        headers=headers,
        json={
            "slot_type": "sponsored_vault_content",
            "title": "Vault sponsorship",
            "description": "Sponsored drop in The Vault with brand integration.",
            "price": "300000",
            "status": "published",
        },
    )
    assert created.status_code == 201, created.text
    slot_id = created.json()["id"]

    public = client.get("/api/v1/sponsorships/public/slots")
    assert public.status_code == 200
    assert any(s["id"] == slot_id for s in public.json())

    admin = User(
        email="sp-admin@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Admin",
        is_active=True,
    )
    admin.roles.append(get_role_by_name(db_session, "super_admin"))
    db_session.add(admin)
    db_session.commit()

    hide = client.post(
        f"/api/v1/sponsorships/admin/slots/{slot_id}/moderate",
        headers=_login(client, admin.email),
        json={"action": "remove", "note": "Inappropriate packaging"},
    )
    assert hide.status_code == 200, hide.text
    assert hide.json()["moderation_status"] == "removed"
    assert hide.json()["status"] == "disabled"

    gone = client.get("/api/v1/sponsorships/public/slots")
    assert all(s["id"] != slot_id for s in gone.json())


def test_public_visibility_rules(client: TestClient, db_session: Session):
    unverified, uv_user = _seed_host(
        db_session, email="sp-uv@example.com", slug="sp-uv", verified=False
    )
    headers = _login(client, uv_user.email)

    # Unverified host cannot publish
    blocked = client.post(
        "/api/v1/sponsorships/host/slots",
        headers=headers,
        json={
            "slot_type": "logo_ticket_email",
            "title": "Email logo",
            "description": "Logo in ticket confirmation emails for this event.",
            "price": "90000",
            "status": "published",
        },
    )
    assert blocked.status_code == 400

    draft = client.post(
        "/api/v1/sponsorships/host/slots",
        headers=headers,
        json={
            "slot_type": "logo_ticket_email",
            "title": "Email logo",
            "description": "Logo in ticket confirmation emails for this event.",
            "price": "90000",
            "status": "draft",
        },
    )
    assert draft.status_code == 201, draft.text

    # Draft never public
    public = client.get("/api/v1/sponsorships/public/slots")
    assert all(s["id"] != draft.json()["id"] for s in public.json())

    # Verified host appears in /sponsors/hosts listing API
    verified, _ = _seed_host(
        db_session, email="sp-vh@example.com", slug="sp-vh", verified=True
    )
    hosts = client.get("/api/v1/sponsorships/public/hosts")
    assert hosts.status_code == 200
    ids = {h["host_id"] for h in hosts.json()}
    assert str(verified.id) in ids
    assert str(unverified.id) not in ids


def test_public_slots_include_eligible_host(client: TestClient, db_session: Session):
    host, host_user = _seed_host(
        db_session, email="sp-elig@example.com", slug="sp-elig", accepting_sponsors=True
    )
    headers = _login(client, host_user.email)
    created = client.post(
        "/api/v1/sponsorships/host/slots",
        headers=headers,
        json={
            "slot_type": "logo_event_page",
            "title": "Eligible slot",
            "description": "Public marketplace listing for verified accepting host.",
            "price": "50000",
            "status": "published",
        },
    )
    assert created.status_code == 201, created.text
    slot_id = created.json()["id"]
    public = client.get("/api/v1/sponsorships/public/slots")
    assert any(s["id"] == slot_id for s in public.json())


def test_public_slots_exclude_not_accepting_sponsors(
    client: TestClient, db_session: Session
):
    host, host_user = _seed_host(
        db_session,
        email="sp-noacc@example.com",
        slug="sp-noacc",
        accepting_sponsors=False,
    )
    headers = _login(client, host_user.email)
    created = client.post(
        "/api/v1/sponsorships/host/slots",
        headers=headers,
        json={
            "slot_type": "booth_at_event",
            "title": "Hidden slot",
            "description": "Host paused sponsor intake.",
            "price": "80000",
            "status": "published",
        },
    )
    assert created.status_code == 201, created.text
    slot_id = created.json()["id"]
    public = client.get("/api/v1/sponsorships/public/slots")
    assert all(s["id"] != slot_id for s in public.json())
    hosts = client.get("/api/v1/sponsorships/public/hosts")
    assert all(h["host_id"] != str(host.id) for h in hosts.json())


def test_public_slots_exclude_draft_and_removed(client: TestClient, db_session: Session):
    host, host_user = _seed_host(db_session, email="sp-hide@example.com", slug="sp-hide")
    headers = _login(client, host_user.email)
    draft = client.post(
        "/api/v1/sponsorships/host/slots",
        headers=headers,
        json={
            "slot_type": "banner_legacy_page",
            "title": "Draft only",
            "description": "Not published.",
            "price": "10000",
            "status": "draft",
        },
    )
    assert draft.status_code == 201
    pub = client.post(
        "/api/v1/sponsorships/host/slots",
        headers=headers,
        json={
            "slot_type": "banner_legacy_page",
            "title": "To remove",
            "description": "Will be moderated off public list.",
            "price": "20000",
            "status": "published",
        },
    )
    assert pub.status_code == 201
    slot_id = pub.json()["id"]
    assert any(s["id"] == slot_id for s in client.get("/api/v1/sponsorships/public/slots").json())

    admin = User(
        email="sp-mod2@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Admin",
        is_active=True,
    )
    admin.roles.append(get_role_by_name(db_session, "super_admin"))
    db_session.add(admin)
    db_session.commit()
    client.post(
        f"/api/v1/sponsorships/admin/slots/{slot_id}/moderate",
        headers=_login(client, admin.email),
        json={"action": "remove", "note": "Policy"},
    )
    public = client.get("/api/v1/sponsorships/public/slots")
    ids = {s["id"] for s in public.json()}
    assert slot_id not in ids
    assert draft.json()["id"] not in ids


def test_host_team_sponsor_viewer_can_read_host_sponsorships(
    client: TestClient, db_session: Session
):
    """Team members with sponsors.view must pass router + service (not host role only)."""
    host, _owner = _seed_host(
        db_session, email="sp-view-host@example.com", slug="sp-view-host"
    )
    viewer = User(
        email="sp-viewer@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Sponsor Viewer",
        is_active=True,
    )
    viewer.roles.append(get_role_by_name(db_session, "host_staff"))
    db_session.add(viewer)
    db_session.flush()
    db_session.add(
        HostTeamMember(
            host_id=host.id,
            user_id=viewer.id,
            role="viewer",
            role_label="Sponsor Observer",
            status="active",
            permissions_json={
                "_replace": True,
                "sponsors.view": True,
                "analytics.view_sponsors": True,
            },
        )
    )
    db_session.commit()

    from app.teams.workspace_pref import set_active_workspace

    set_active_workspace(db_session, user=viewer, host_id=host.id)
    db_session.commit()

    headers = _login(client, viewer.email)
    settings = client.get("/api/v1/sponsorships/host/settings", headers=headers)
    assert settings.status_code == 200, settings.text
    slots = client.get("/api/v1/sponsorships/host/slots", headers=headers)
    assert slots.status_code == 200, slots.text
    inquiries = client.get("/api/v1/sponsorships/host/inquiries", headers=headers)
    assert inquiries.status_code == 200, inquiries.text

    denied = client.post(
        "/api/v1/sponsorships/host/slots",
        headers=headers,
        json={
            "slot_type": "logo_event_page",
            "title": "Blocked",
            "description": "Should fail without manage_slots.",
            "price": "1000",
        },
    )
    assert denied.status_code == 403
