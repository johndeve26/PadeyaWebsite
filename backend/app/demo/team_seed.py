"""DJ Maze host-team demo memberships, pending invite, and audit samples."""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.checkins.models import EventStaffAssignment
from app.demo.constants import (
    DEMO_EMAIL_DOMAIN,
    DEMO_EVENT_SLUG_PREFIX,
    DEMO_TEAM_ACCOUNTS,
    DEMO_TEAM_INVITE_TOKEN,
    DEMO_TEAM_MEMBERS,
)
from app.events.models import Event
from app.hosts.models import Host, HostTeamAuditLog, HostTeamInvite, HostTeamMember
from app.hosts.team_permissions import (
    SCOPE_SELECTED_EVENTS,
    empty_permissions,
    merge_permissions,
    normalize_permissions_dict,
    pack_scope_json,
)
from app.teams.team_audit import write_team_audit
from app.teams.workspace_pref import UserActiveWorkspace
from app.users.models import User
from app.users.service import get_role_by_name, get_user_by_email

INVITEE_EMAIL = f"team-invitee@{DEMO_EMAIL_DOMAIN}"


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _assignment_type_for_role(role: str) -> str:
    if role == "merch_staff":
        return "merch_pickup"
    if role in {
        "event_manager",
        "ambassador_manager",
        "finance_manager",
        "viewer",
        "admin",
        "support_staff",
        "sponsor_manager",
    }:
        return "event_ops"
    return "ticket_scanner"


def _permissions_for_spec(spec: dict[str, Any]) -> dict[str, bool]:
    overrides = spec.get("permission_overrides")
    if isinstance(overrides, dict) and overrides.get("_replace"):
        perms = empty_permissions()
        for key, value in overrides.items():
            if key == "_replace":
                continue
            if key in perms:
                perms[key] = bool(value)
        return perms
    return merge_permissions(spec["role"], overrides)


def _resolve_event_ids(
    events: dict[str, Event], event_keys: list[str]
) -> list[uuid.UUID]:
    ids: list[uuid.UUID] = []
    for key in event_keys:
        event = events.get(key)
        if event is None:
            slug = f"{DEMO_EVENT_SLUG_PREFIX}{key}"
            for ev in events.values():
                if ev.slug == slug:
                    event = ev
                    break
        if event is not None:
            ids.append(event.id)
    return ids


def _ensure_membership(
    db: Session,
    *,
    host: Host,
    user: User,
    owner: User,
    spec: dict[str, Any],
    event_ids: list[uuid.UUID],
) -> HostTeamMember:
    row = db.scalar(
        select(HostTeamMember).where(
            HostTeamMember.host_id == host.id,
            HostTeamMember.user_id == user.id,
        )
    )
    perms = _permissions_for_spec(spec)
    scope = pack_scope_json(spec["scope"], event_ids)
    now = datetime.now(UTC)
    if row is None:
        row = HostTeamMember(
            host_id=host.id,
            user_id=user.id,
            role=spec["role"],
            role_label=spec["role_label"],
            status="active",
            permissions_json=perms,
            scope_json=scope,
            invited_by_user_id=owner.id,
            joined_at=now,
        )
        db.add(row)
        db.flush()
        write_team_audit(
            db,
            host_id=host.id,
            action="hosts.team_member_added",
            actor_user_id=owner.id,
            target_user_id=user.id,
            entity_type="host_team_member",
            entity_id=str(row.id),
            metadata={
                "role": row.role,
                "role_label": row.role_label,
                "demo": True,
            },
        )
    else:
        row.role = spec["role"]
        row.role_label = spec["role_label"]
        row.status = "active"
        row.removed_at = None
        row.suspended_at = None
        row.permissions_json = perms
        row.scope_json = scope
        if row.joined_at is None:
            row.joined_at = now
        row.invited_by_user_id = owner.id
        db.flush()
    return row


def _sync_event_staff(
    db: Session,
    *,
    row: HostTeamMember,
    owner: User,
    event_ids: list[uuid.UUID],
) -> None:
    scope_type = (row.scope_json or {}).get("type")
    if scope_type != SCOPE_SELECTED_EVENTS or not event_ids:
        return
    if row.role not in {"scanner", "merch_staff", "event_manager", "viewer"}:
        return
    assignment_type = _assignment_type_for_role(row.role)
    perms = normalize_permissions_dict(row.permissions_json)
    for event_id in event_ids:
        existing = db.scalar(
            select(EventStaffAssignment).where(
                EventStaffAssignment.event_id == event_id,
                EventStaffAssignment.user_id == row.user_id,
            )
        )
        if existing is not None:
            existing.team_member_id = row.id
            existing.assignment_type = assignment_type
            existing.role_label = row.role_label
            existing.permissions_json = perms
            existing.status = "active"
            existing.expires_at = None
            continue
        db.add(
            EventStaffAssignment(
                event_id=event_id,
                user_id=row.user_id,
                team_member_id=row.id,
                assigned_by_user_id=owner.id,
                assignment_type=assignment_type,
                role_label=row.role_label,
                permissions_json=perms,
                status="active",
            )
        )


def _ensure_pending_invite(
    db: Session,
    *,
    host: Host,
    owner: User,
    afrobeats_id: uuid.UUID | None,
) -> HostTeamInvite:
    token_hash = _hash_token(DEMO_TEAM_INVITE_TOKEN)
    perms = merge_permissions(
        "scanner",
        {"tickets.scan_qr": True, "tickets.check_in": True},
    )
    scope = pack_scope_json(
        "selected_events",
        [afrobeats_id] if afrobeats_id is not None else [],
    )
    invitee = get_user_by_email(db, INVITEE_EMAIL)
    row = db.scalar(
        select(HostTeamInvite).where(
            HostTeamInvite.host_id == host.id,
            HostTeamInvite.email == INVITEE_EMAIL,
        )
    )
    expires = datetime.now(UTC) + timedelta(days=14)
    if row is None:
        row = HostTeamInvite(
            host_id=host.id,
            email=INVITEE_EMAIL,
            role="scanner",
            role_label="Scanner Staff",
            status="pending",
            permissions_json=perms,
            scope_json=scope,
            token_hash=token_hash,
            expires_at=expires,
            invited_by_user_id=owner.id,
            invited_user_id=invitee.id if invitee else None,
        )
        db.add(row)
        db.flush()
        write_team_audit(
            db,
            host_id=host.id,
            action="hosts.team_invite",
            actor_user_id=owner.id,
            target_user_id=invitee.id if invitee else None,
            entity_type="host_team_invite",
            entity_id=str(row.id),
            metadata={
                "invited_email": INVITEE_EMAIL,
                "role": "scanner",
                "role_label": "Scanner Staff",
                "demo": True,
            },
        )
    else:
        row.status = "pending"
        row.role = "scanner"
        row.role_label = "Scanner Staff"
        row.permissions_json = perms
        row.scope_json = scope
        row.token_hash = token_hash
        row.expires_at = expires
        row.revoked_at = None
        row.accepted_at = None
        row.invited_by_user_id = owner.id
        row.invited_user_id = invitee.id if invitee else None
        db.flush()
    return row


def _set_active_workspace(db: Session, *, user: User, host_id: uuid.UUID) -> None:
    row = db.get(UserActiveWorkspace, user.id)
    if row is None:
        db.add(UserActiveWorkspace(user_id=user.id, host_id=host_id))
    else:
        row.host_id = host_id


def _ensure_sample_audits(db: Session, *, host: Host, owner: User) -> None:
    """Guarantee a few readable audit rows even on refresh."""
    existing = db.scalar(
        select(HostTeamAuditLog.id).where(
            HostTeamAuditLog.host_id == host.id,
            HostTeamAuditLog.action == "hosts.team_invite",
        )
    )
    if existing is not None:
        return
    write_team_audit(
        db,
        host_id=host.id,
        action="hosts.team_invite",
        actor_user_id=owner.id,
        entity_type="host_team_invite",
        entity_id="demo",
        metadata={"demo": True, "role": "scanner", "note": "seed bootstrap"},
    )


def seed_host_team_demo(
    db: Session,
    *,
    users: dict[str, User],
    hosts: dict[str, Host],
    events: dict[str, Event],
) -> dict[str, int]:
    """Idempotent DJ Maze team: admin, gate, pickup, viewer + pending invite."""
    from app.demo.seed import _ensure_user

    host = hosts.get("djmaze")
    if host is None:
        return {"team_members": 0, "team_invites": 0}

    owner = users.get(f"host@{DEMO_EMAIL_DOMAIN}") or get_user_by_email(
        db, f"host@{DEMO_EMAIL_DOMAIN}"
    )
    if owner is None:
        owner = db.get(User, host.user_id)
    if owner is None:
        return {"team_members": 0, "team_invites": 0}

    for acct in DEMO_TEAM_ACCOUNTS:
        users[acct["email"]] = _ensure_user(
            db,
            email=acct["email"],
            full_name=acct["full_name"],
            role=acct["role"],
        )

    staff_role = get_role_by_name(db, "host_staff")
    members_created = 0
    for spec in DEMO_TEAM_MEMBERS:
        user = users.get(spec["email"]) or get_user_by_email(db, spec["email"])
        if user is None:
            continue
        if staff_role and staff_role not in user.roles:
            user.roles.append(staff_role)
        event_ids = _resolve_event_ids(events, list(spec.get("event_keys") or []))
        row = _ensure_membership(
            db,
            host=host,
            user=user,
            owner=owner,
            spec=spec,
            event_ids=event_ids,
        )
        _sync_event_staff(db, row=row, owner=owner, event_ids=event_ids)
        _set_active_workspace(db, user=user, host_id=host.id)
        members_created += 1

    afrobeats = events.get("afrobeats-night-live")
    afrobeats_id = afrobeats.id if afrobeats is not None else None
    _ensure_pending_invite(
        db, host=host, owner=owner, afrobeats_id=afrobeats_id
    )
    _ensure_sample_audits(db, host=host, owner=owner)
    _set_active_workspace(db, user=owner, host_id=host.id)
    db.flush()
    return {
        "team_members": members_created,
        "team_invites": 1,
    }
