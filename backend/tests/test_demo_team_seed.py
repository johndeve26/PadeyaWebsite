"""DJ Maze host-team demo seed."""

from __future__ import annotations

import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.demo.constants import (
    DEMO_ACCOUNTS,
    DEMO_PASSWORD,
    DEMO_TEAM_ACCOUNTS,
    DEMO_TEAM_INVITE_TOKEN,
    DEMO_TEAM_MEMBERS,
    EXTRA_HOST_ACCOUNTS,
)
from app.demo.seed import (
    _ensure_categories,
    _ensure_events,
    _ensure_hosts,
    _ensure_user,
)
from app.demo.team_seed import seed_host_team_demo
from app.hosts.models import HostTeamInvite, HostTeamMember
from app.hosts.team_permissions import normalize_permissions_dict, unpack_scope_json
from app.teams.permissions import can_scan_merch_pickup, can_scan_ticket
from app.users.seed import seed_roles_and_permissions
from app.users.service import get_user_by_email


def test_dj_maze_team_demo_seed(db_session: Session):
    seed_roles_and_permissions(db_session)
    users = {}
    for acct in [*DEMO_ACCOUNTS, *EXTRA_HOST_ACCOUNTS, *DEMO_TEAM_ACCOUNTS]:
        users[acct["email"]] = _ensure_user(
            db_session,
            email=acct["email"],
            full_name=acct["full_name"],
            role=acct["role"],
        )
    categories = _ensure_categories(db_session)
    hosts = _ensure_hosts(db_session, users)
    events = _ensure_events(db_session, hosts, categories)
    db_session.commit()

    counts = seed_host_team_demo(
        db_session, users=users, hosts=hosts, events=events
    )
    db_session.commit()
    assert counts["team_members"] == len(DEMO_TEAM_MEMBERS)
    assert counts["team_invites"] == 1

    # Idempotent refresh
    counts2 = seed_host_team_demo(
        db_session, users=users, hosts=hosts, events=events
    )
    db_session.commit()
    assert counts2["team_members"] == len(DEMO_TEAM_MEMBERS)

    host = hosts["djmaze"]
    afrobeats = events["afrobeats-night-live"]

    gate = get_user_by_email(db_session, "gate@demo.padeye.test")
    pickup = get_user_by_email(db_session, "pickup@demo.padeye.test")
    observer = get_user_by_email(db_session, "sponsor-observer@demo.padeye.test")
    assert gate and pickup and observer
    assert gate.full_name == "Gate Scanner"
    assert pickup.full_name == "Pickup Staff"

    gate_m = db_session.scalar(
        select(HostTeamMember).where(
            HostTeamMember.host_id == host.id,
            HostTeamMember.user_id == gate.id,
        )
    )
    assert gate_m is not None
    assert gate_m.role_label == "Gate Scanner"
    g_scope, g_ids = unpack_scope_json(gate_m.scope_json, role=gate_m.role)
    assert g_scope == "selected_events"
    assert afrobeats.id in g_ids
    g_perms = normalize_permissions_dict(gate_m.permissions_json)
    assert g_perms["tickets.scan_qr"] is True
    assert g_perms["tickets.check_in"] is True
    assert can_scan_ticket(db_session, gate.id, host.id, afrobeats.id) is True

    pickup_m = db_session.scalar(
        select(HostTeamMember).where(
            HostTeamMember.host_id == host.id,
            HostTeamMember.user_id == pickup.id,
        )
    )
    assert pickup_m is not None
    assert pickup_m.role_label == "Pickup Staff"
    p_perms = normalize_permissions_dict(pickup_m.permissions_json)
    assert p_perms["merch.scan_pickup_qr"] is True
    assert p_perms["merch.mark_picked_up"] is True
    assert can_scan_merch_pickup(db_session, pickup.id, host.id, afrobeats.id) is True

    observer_m = db_session.scalar(
        select(HostTeamMember).where(
            HostTeamMember.host_id == host.id,
            HostTeamMember.user_id == observer.id,
        )
    )
    assert observer_m is not None
    o_perms = normalize_permissions_dict(observer_m.permissions_json)
    assert o_perms["sponsors.view"] is True
    assert o_perms["analytics.view_sponsors"] is True
    assert o_perms["tickets.scan_qr"] is False
    assert o_perms["finance.view_payouts"] is False

    invite = db_session.scalar(
        select(HostTeamInvite).where(
            HostTeamInvite.host_id == host.id,
            HostTeamInvite.email == "team-invitee@demo.padeye.test",
        )
    )
    assert invite is not None
    assert invite.status == "pending"
    assert invite.token_hash == hashlib.sha256(
        DEMO_TEAM_INVITE_TOKEN.encode("utf-8")
    ).hexdigest()
    assert DEMO_PASSWORD == "DemoPass123!"
