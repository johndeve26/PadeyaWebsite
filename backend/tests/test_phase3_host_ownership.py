"""Phase 3 — host resource ownership / cross-tenant IDOR."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.helpers.phase3_personas import (
    add_team_member,
    login_existing,
    register_persona,
    seed_host_with_event,
)


def _hosts(client: TestClient, db: Session):
    _, host_a, event_a, _ = seed_host_with_event(
        db, email="p3-host-a@example.com", slug_suffix="ha", title="Host A Night"
    )
    _, host_b, event_b, _ = seed_host_with_event(
        db, email="p3-host-b@example.com", slug_suffix="hb", title="Host B Night"
    )
    headers_a = login_existing(client, "p3-host-a@example.com")
    headers_b = login_existing(client, "p3-host-b@example.com")
    fan = register_persona(client, email="p3-host-fan@example.com", full_name="Host Fan")
    return host_a, event_a, headers_a, host_b, event_b, headers_b, fan


def test_host_a_can_read_own_event_management(client: TestClient, db_session: Session):
    _, event_a, headers_a, *_ = _hosts(client, db_session)
    resp = client.get(f"/api/v1/events/by-id/{event_a.id}", headers=headers_a)
    assert resp.status_code == 200, resp.text


def test_host_b_cannot_mutate_host_a_event(client: TestClient, db_session: Session):
    _, event_a, headers_a, _, _, headers_b, _ = _hosts(client, db_session)
    # Cross-host edit must reject/conceal.
    patch = client.patch(
        f"/api/v1/events/by-id/{event_a.id}",
        headers=headers_b,
        json={"title": "Hijacked Title"},
    )
    assert patch.status_code in {403, 404}, patch.text

    cancel = client.post(
        f"/api/v1/events/by-id/{event_a.id}/cancel",
        headers=headers_b,
        json={"reason": "not mine"},
    )
    assert cancel.status_code in {403, 404}, cancel.text


def test_host_b_analytics_of_host_a_is_404(client: TestClient, db_session: Session):
    """Phase 2 anti-enumeration policy: foreign host analytics → 404."""
    _, event_a, _, _, _, headers_b, fan = _hosts(client, db_session)
    for headers in (headers_b, fan.headers):
        resp = client.get(
            f"/api/v1/host/events/{event_a.id}/analytics/overview",
            headers=headers,
        )
        assert resp.status_code == 404, resp.text
        export = client.get(
            f"/api/v1/host/events/{event_a.id}/analytics/export",
            headers=headers,
        )
        assert export.status_code == 404, export.text


def test_anonymous_and_fan_cannot_manage_host_event(client: TestClient, db_session: Session):
    _, event_a, _, *_rest = _hosts(client, db_session)
    fan = register_persona(client, email="p3-host-fan2@example.com", full_name="Fan2")
    for headers in (None, fan.headers):
        kw = {"headers": headers} if headers else {}
        assert (
            client.patch(
                f"/api/v1/events/by-id/{event_a.id}",
                json={"title": "Nope"},
                **kw,
            ).status_code
            in {401, 403, 404}
        )


def test_team_member_without_event_edit_cannot_patch(
    client: TestClient, db_session: Session
):
    host_a, event_a, headers_a, *_ = _hosts(client, db_session)
    denied = add_team_member(
        db_session,
        host_id=host_a.id,
        email="p3-team-viewonly@example.com",
        client=client,
        permission_overrides={"events.view": True, "events.edit": False},
    )
    from app.teams.workspace_pref import set_active_workspace
    from app.users.models import User

    user = db_session.query(User).filter_by(email="p3-team-viewonly@example.com").one()
    set_active_workspace(db_session, user=user, host_id=host_a.id)
    db_session.commit()

    # Owner can still read.
    assert (
        client.get(f"/api/v1/events/by-id/{event_a.id}", headers=headers_a).status_code
        == 200
    )
    denied_patch = client.patch(
        f"/api/v1/events/by-id/{event_a.id}",
        headers=denied,
        json={"title": "Should Fail"},
    )
    assert denied_patch.status_code in {403, 404}, denied_patch.text


def test_team_member_with_event_edit_can_patch(client: TestClient, db_session: Session):
    host_a, event_a, _, *_ = _hosts(client, db_session)
    allowed = add_team_member(
        db_session,
        host_id=host_a.id,
        email="p3-team-edit@example.com",
        client=client,
        permission_overrides={"events.view": True, "events.edit": True},
    )
    from app.teams.workspace_pref import set_active_workspace
    from app.users.models import User

    user = db_session.query(User).filter_by(email="p3-team-edit@example.com").one()
    set_active_workspace(db_session, user=user, host_id=host_a.id)
    db_session.commit()

    ok = client.patch(
        f"/api/v1/events/by-id/{event_a.id}",
        headers=allowed,
        json={"title": "Team Edited Title"},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["title"] == "Team Edited Title"


def test_host_b_team_cannot_edit_host_a_event(client: TestClient, db_session: Session):
    host_a, event_a, _, host_b, _, _, _ = _hosts(client, db_session)
    foreign_team = add_team_member(
        db_session,
        host_id=host_b.id,
        email="p3-team-foreign@example.com",
        client=client,
        permission_overrides={"events.view": True, "events.edit": True},
    )
    from app.teams.workspace_pref import set_active_workspace
    from app.users.models import User

    user = db_session.query(User).filter_by(email="p3-team-foreign@example.com").one()
    set_active_workspace(db_session, user=user, host_id=host_b.id)
    db_session.commit()

    resp = client.patch(
        f"/api/v1/events/by-id/{event_a.id}",
        headers=foreign_team,
        json={"title": "Cross Host"},
    )
    assert resp.status_code in {403, 404}, resp.text
