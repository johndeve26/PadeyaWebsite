"""Team members may perform host ops only with the matching permission."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostProfile, HostTeamMember
from app.hosts.team_permissions import pack_scope_json, permissions_for_role
from app.users.models import User
from app.users.service import get_role_by_name


def _login(client: TestClient, email: str) -> dict[str, str]:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


from tests.helpers.auth import register_json


def _register(client: TestClient, email: str, name: str) -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json=register_json(email=email, full_name=name),
    )
    return _login(client, email)


def _seed_host(db: Session, *, suffix: str) -> tuple[Host, Event]:
    host_user = User(
        email=f"ops-host-{suffix}@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Ops Host",
        is_active=True,
    )
    role = get_role_by_name(db, "host")
    assert role is not None
    host_user.roles.append(role)
    db.add(host_user)
    db.flush()
    host = Host(
        user_id=host_user.id,
        display_name=f"Ops Host {suffix}",
        slug=f"ops-host-{suffix}",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, city="Lagos"))
    category = db.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=12)
    event = Event(
        title=f"Ops Night {suffix}",
        slug=f"ops-night-{suffix}",
        description="Team ops permission event.",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=3),
        city="Lagos",
        status="published",
        featured=False,
        published_at=datetime.now(UTC),
    )
    db.add(event)
    db.flush()
    db.add(
        TicketType(
            event_id=event.id,
            name="GA",
            type="regular",
            price=Decimal("3000.00"),
            quantity=50,
            quantity_sold=0,
            quantity_reserved=0,
            min_per_order=1,
            max_per_order=4,
            visibility="public",
            status="active",
        )
    )
    db.commit()
    return host, event


def _add_member(
    db: Session,
    *,
    host_id,
    email: str,
    client: TestClient,
    permission_overrides: dict[str, bool],
) -> dict[str, str]:
    headers = _register(client, email, "Ops Team")
    member = db.query(User).filter_by(email=email).one()
    perms = permissions_for_role("viewer")
    perms.update(permission_overrides)
    db.add(
        HostTeamMember(
            host_id=host_id,
            user_id=member.id,
            role="viewer",
            role_label="Viewer",
            status="active",
            permissions_json=perms,
            scope_json=pack_scope_json("host_wide"),
            joined_at=datetime.now(UTC),
        )
    )
    db.commit()
    return headers


def _event_payload() -> dict:
    start = datetime.now(UTC) + timedelta(days=20)
    return {
        "title": f"Team Create {uuid4().hex[:6]}",
        "description": "Created by a team member with events.create.",
        "start_datetime": start.isoformat(),
        "end_datetime": (start + timedelta(hours=2)).isoformat(),
        "venue_name": "Hall",
        "city": "Lagos",
        "state": "Lagos",
        "venue": {
            "name": "Hall",
            "city": "Lagos",
            "state": "Lagos",
            "country": "Nigeria",
        },
    }


def test_team_events_create_permission_gate(
    client: TestClient, db_session: Session
):
    from app.teams.workspace_pref import set_active_workspace

    host, _event = _seed_host(db_session, suffix="ev")
    denied_h = _add_member(
        db_session,
        host_id=host.id,
        email="ops-ev-deny@example.com",
        client=client,
        permission_overrides={"events.view": True},
    )
    deny_user = db_session.query(User).filter_by(email="ops-ev-deny@example.com").one()
    set_active_workspace(db_session, user=deny_user, host_id=host.id)
    denied = client.post(
        "/api/v1/events",
        headers=denied_h,
        json=_event_payload(),
    )
    assert denied.status_code == 403

    allowed_h = _add_member(
        db_session,
        host_id=host.id,
        email="ops-ev-ok@example.com",
        client=client,
        permission_overrides={"events.create": True, "events.view": True},
    )
    member = db_session.query(User).filter_by(email="ops-ev-ok@example.com").one()
    set_active_workspace(db_session, user=member, host_id=host.id)

    ok = client.post(
        "/api/v1/events",
        headers=allowed_h,
        json=_event_payload(),
    )
    assert ok.status_code == 201, ok.text


def test_team_merch_create_and_edit_permission_gates(
    client: TestClient, db_session: Session
):
    host, event = _seed_host(db_session, suffix="me")
    create_h = _add_member(
        db_session,
        host_id=host.id,
        email="ops-me-create@example.com",
        client=client,
        permission_overrides={
            "merch.create": True,
            "merch.view": True,
            "events.view": True,
        },
    )
    from app.teams.workspace_pref import set_active_workspace

    creator = db_session.query(User).filter_by(email="ops-me-create@example.com").one()
    set_active_workspace(db_session, user=creator, host_id=host.id)

    created = client.post(
        f"/api/v1/merch/events/{event.id}/products",
        headers=create_h,
        json={
            "name": "Ops Tee",
            "description": "Team merch",
            "base_price": "5000.00",
            "status": "draft",
            "variants": [
                {"label": "M", "inventory_count": 3, "status": "active"}
            ],
        },
    )
    assert created.status_code == 200, created.text
    product_id = created.json()["id"]

    # Same creator has merch.create but not merch.edit — edit must be denied.
    denied = client.patch(
        f"/api/v1/merch/products/{product_id}",
        headers=create_h,
        json={"name": "Nope"},
    )
    assert denied.status_code == 403


def test_team_ambassadors_create_campaign_permission_gate(
    client: TestClient, db_session: Session
):
    host, event = _seed_host(db_session, suffix="ac")
    denied_h = _add_member(
        db_session,
        host_id=host.id,
        email="ops-ac-deny@example.com",
        client=client,
        permission_overrides={"ambassadors.view": True},
    )
    payload = {
        "event_id": str(event.id),
        "name": "Denied Campaign",
        "commission_percent": "5.00",
        "visibility": "public_open",
    }
    denied = client.post(
        f"/api/v1/host/ambassadors/campaigns?host_id={host.id}",
        headers=denied_h,
        json=payload,
    )
    assert denied.status_code == 403

    allowed_h = _add_member(
        db_session,
        host_id=host.id,
        email="ops-ac-ok@example.com",
        client=client,
        permission_overrides={
            "ambassadors.view": True,
            "ambassadors.create_campaigns": True,
        },
    )
    ok = client.post(
        f"/api/v1/host/ambassadors/campaigns?host_id={host.id}",
        headers=allowed_h,
        json={
            "event_id": str(event.id),
            "name": "Allowed Campaign",
            "commission_percent": "5.00",
            "visibility": "public_open",
        },
    )
    assert ok.status_code == 201, ok.text
