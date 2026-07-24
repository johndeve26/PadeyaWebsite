"""Central host-team permission checker.

``host_profile_id`` is the host workspace id (``hosts.id``).

Allow an action when any of:
1. User is the host owner
2. Active ``host_team_members`` row with the required permission and host-wide scope
3. Valid ``event_staff_assignments`` for that event/action
4. Active team member with the required permission scoped to that event
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.checkins.models import EventStaffAssignment
from app.events.models import Event
from app.hosts.models import Host, HostTeamMember
from app.hosts.team_permissions import (
    SCOPE_HOST_WIDE,
    get_active_team_membership,
    membership_covers_event,
    membership_scope,
    normalize_permissions_dict,
    team_permission_allows,
)
from app.users.service import get_user_by_id, user_has_permission, user_has_role

# Map namespaced team permissions → event staff assignment types.
_STAFF_PERMISSION_TYPES: dict[str, frozenset[str]] = {
    "tickets.scan_qr": frozenset({"ticket_scanner", "event_ops"}),
    "tickets.check_in": frozenset({"ticket_scanner", "event_ops"}),
    "tickets.view": frozenset({"ticket_scanner", "event_ops", "merch_pickup"}),
    "merch.scan_pickup_qr": frozenset({"merch_pickup", "event_ops"}),
    "merch.mark_picked_up": frozenset({"merch_pickup", "event_ops"}),
    "merch.fulfill_orders": frozenset({"merch_pickup", "event_ops"}),
    "merch.view": frozenset({"merch_pickup", "event_ops"}),
    "events.view": frozenset({"ticket_scanner", "merch_pickup", "event_ops"}),
    "events.edit": frozenset({"event_ops"}),
    "events.publish": frozenset({"event_ops"}),
}


def _is_platform_admin(db: Session, user_id: uuid.UUID) -> bool:
    user = get_user_by_id(db, user_id)
    if user is None:
        return False
    return user_has_role(user, "super_admin") or user_has_permission(
        user, "admin.full_access"
    )


def is_host_owner(
    db: Session, user_id: uuid.UUID, host_profile_id: uuid.UUID
) -> bool:
    """True when ``user_id`` owns the host workspace (``hosts.id``)."""
    host = db.get(Host, host_profile_id)
    return host is not None and host.user_id == user_id and host.status == "active"


def get_team_membership(
    db: Session, user_id: uuid.UUID, host_profile_id: uuid.UUID
) -> HostTeamMember | None:
    """Active, non-removed team membership for this host workspace."""
    return get_active_team_membership(
        db, user_id=user_id, host_id=host_profile_id
    )


def team_membership_blocks_desk(
    db: Session, user_id: uuid.UUID, host_profile_id: uuid.UUID
) -> bool:
    """True when a suspended/removed team row must revoke desk access immediately.

    Pure event-staff (no team membership) is unaffected. Once invited onto the
    host team, inactive membership status always wins over leftover staff rows.
    """
    row = db.scalar(
        select(HostTeamMember).where(
            HostTeamMember.host_id == host_profile_id,
            HostTeamMember.user_id == user_id,
        )
    )
    if row is None:
        return False
    if row.status == "active" and row.removed_at is None:
        return False
    return True


def has_host_permission(
    db: Session,
    user_id: uuid.UUID,
    host_profile_id: uuid.UUID,
    permission: str,
) -> bool:
    """Host-scoped permission (no event). Owner or active team toggle."""
    if _is_platform_admin(db, user_id):
        return True
    if is_host_owner(db, user_id, host_profile_id):
        return True
    return team_permission_allows(
        db,
        user_id=user_id,
        host_id=host_profile_id,
        permission=permission,
    )


def host_team_or_owner_allows(
    db: Session,
    user_id: uuid.UUID,
    host_profile_id: uuid.UUID,
    *permissions: str,
) -> bool:
    """Owner or active team toggle — never platform-admin shortcut.

    Use for participation surfaces (e.g. messaging) where super_admin must
    not become an implicit host-side party.
    """
    if is_host_owner(db, user_id, host_profile_id):
        return True
    return any(
        team_permission_allows(
            db,
            user_id=user_id,
            host_id=host_profile_id,
            permission=perm,
        )
        for perm in permissions
    )


def _active_staff_row(
    db: Session, *, user_id: uuid.UUID, event_id: uuid.UUID
) -> EventStaffAssignment | None:
    now = datetime.now(UTC)
    return db.scalar(
        select(EventStaffAssignment).where(
            EventStaffAssignment.event_id == event_id,
            EventStaffAssignment.user_id == user_id,
            EventStaffAssignment.status == "active",
            or_(
                EventStaffAssignment.expires_at.is_(None),
                EventStaffAssignment.expires_at > now,
            ),
        )
    )


def has_event_staff_assignment(
    db: Session,
    user_id: uuid.UUID,
    event_id: uuid.UUID,
    permission: str | None = None,
) -> bool:
    """Valid per-event desk assignment, optionally matching ``permission``."""
    row = _active_staff_row(db, user_id=user_id, event_id=event_id)
    if row is None:
        return False
    if not permission:
        return True

    # Explicit JSON overrides on the assignment win when present.
    if row.permissions_json:
        perms = normalize_permissions_dict(row.permissions_json)
        if permission in perms:
            return bool(perms[permission])

    allowed_types = _STAFF_PERMISSION_TYPES.get(permission)
    if allowed_types is None:
        # Unknown permission key — any active desk assignment is not enough.
        return False
    assignment_type = (row.assignment_type or "ticket_scanner").strip().lower()
    return assignment_type in allowed_types


def has_event_permission(
    db: Session,
    user_id: uuid.UUID,
    host_profile_id: uuid.UUID,
    event_id: uuid.UUID,
    permission: str,
) -> bool:
    """Event-scoped permission using the hybrid host-team rule."""
    if _is_platform_admin(db, user_id):
        return True

    event = db.get(Event, event_id)
    if event is None or event.host_id != host_profile_id:
        return False

    if is_host_owner(db, user_id, host_profile_id):
        return True

    # (3) Per-event staff assignment for this action
    if has_event_staff_assignment(
        db, user_id=user_id, event_id=event_id, permission=permission
    ):
        return True

    membership = get_team_membership(db, user_id, host_profile_id)
    if membership is None:
        return False
    if not team_permission_allows(
        db,
        user_id=user_id,
        host_id=host_profile_id,
        permission=permission,
    ):
        return False

    scope, _ = membership_scope(membership)
    # (2) Host-wide team permission
    if scope == SCOPE_HOST_WIDE:
        return True
    # (4) Permission scoped to this event (ids and/or staff link)
    return membership_covers_event(db, membership, event_id)


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _inactive_staff_row(
    db: Session, *, user_id: uuid.UUID, event_id: uuid.UUID
) -> EventStaffAssignment | None:
    """Any staff row for event (including inactive/expired) — for denial reasons."""
    return db.scalar(
        select(EventStaffAssignment)
        .where(
            EventStaffAssignment.event_id == event_id,
            EventStaffAssignment.user_id == user_id,
        )
        .order_by(EventStaffAssignment.created_at.desc())
    )


def _team_has_desk_permission(
    db: Session,
    *,
    user_id: uuid.UUID,
    host_profile_id: uuid.UUID,
    permissions: tuple[str, ...],
) -> bool:
    return any(
        team_permission_allows(
            db, user_id=user_id, host_id=host_profile_id, permission=p
        )
        for p in permissions
    )


def can_scan_ticket(
    db: Session,
    user_id: uuid.UUID,
    host_profile_id: uuid.UUID,
    event_id: uuid.UUID,
) -> bool:
    """Ticket scanner allow rule.

    Allow: host owner; active team with tickets.scan_qr / tickets.check_in
    (host-wide or scoped to this event); valid event_staff_assignment for event.
    """
    if _is_platform_admin(db, user_id):
        return True
    event = db.get(Event, event_id)
    if event is None or event.host_id != host_profile_id:
        return False
    if is_host_owner(db, user_id, host_profile_id):
        return True
    if team_membership_blocks_desk(db, user_id, host_profile_id):
        return False
    # Valid per-event staff assignment (active + not expired).
    if has_event_staff_assignment(
        db, user_id=user_id, event_id=event_id, permission=None
    ):
        return True

    membership = get_team_membership(db, user_id, host_profile_id)
    if membership is None:
        return False
    if not _team_has_desk_permission(
        db,
        user_id=user_id,
        host_profile_id=host_profile_id,
        permissions=("tickets.scan_qr", "tickets.check_in"),
    ):
        return False
    scope, _ = membership_scope(membership)
    if scope == SCOPE_HOST_WIDE:
        return True
    # Scoped: event must be in scope_json (not via unrelated staff on another event).
    _, scoped_ids = membership_scope(membership)
    return event_id in scoped_ids


def ticket_scan_denial_reason(
    db: Session,
    user_id: uuid.UUID,
    host_profile_id: uuid.UUID,
    event_id: uuid.UUID,
) -> str | None:
    """Human-readable denial reason, or None when allowed."""
    if can_scan_ticket(db, user_id, host_profile_id, event_id):
        return None
    event = db.get(Event, event_id)
    if event is None:
        return "Event not found"
    if event.host_id != host_profile_id:
        return "Event does not belong to this host"
    if is_host_owner(db, user_id, host_profile_id):
        return None

    any_membership = db.scalar(
        select(HostTeamMember).where(
            HostTeamMember.host_id == host_profile_id,
            HostTeamMember.user_id == user_id,
        )
    )
    if any_membership is not None:
        if any_membership.status == "suspended":
            return "Team membership is suspended"
        if any_membership.status == "removed" or any_membership.removed_at is not None:
            return "Team membership has been removed"
        if any_membership.status != "active":
            return f"Team membership is {any_membership.status}"
        if not _team_has_desk_permission(
            db,
            user_id=user_id,
            host_profile_id=host_profile_id,
            permissions=("tickets.scan_qr", "tickets.check_in"),
        ):
            return "Team member lacks tickets.scan_qr / tickets.check_in"
        scope, scoped_ids = membership_scope(any_membership)
        if scope != SCOPE_HOST_WIDE and event_id not in scoped_ids:
            return "Scanner is not scoped to this event"

    staff = _inactive_staff_row(db, user_id=user_id, event_id=event_id)
    if staff is not None:
        now = datetime.now(UTC)
        if staff.status != "active":
            return f"Event staff assignment is {staff.status}"
        expires = _as_utc(staff.expires_at)
        if expires is not None and expires <= now:
            return "Event staff assignment has expired"

    # Staff on a different event under this host?
    other_staff = db.scalar(
        select(EventStaffAssignment.id)
        .join(Event, Event.id == EventStaffAssignment.event_id)
        .where(
            EventStaffAssignment.user_id == user_id,
            Event.host_id == host_profile_id,
            EventStaffAssignment.event_id != event_id,
            EventStaffAssignment.status == "active",
        )
    )
    if other_staff is not None:
        return "Scanner assigned to a different event"

    other_host_team = db.scalar(
        select(HostTeamMember.id).where(
            HostTeamMember.user_id == user_id,
            HostTeamMember.host_id != host_profile_id,
            HostTeamMember.status == "active",
            HostTeamMember.removed_at.is_(None),
        )
    )
    if other_host_team is not None and any_membership is None:
        return "User belongs to a different host team"

    return "Not authorized to scan tickets for this event"


def can_scan_merch_pickup(
    db: Session,
    user_id: uuid.UUID,
    host_profile_id: uuid.UUID,
    event_id: uuid.UUID,
) -> bool:
    """Merch pickup scanner allow rule.

    Allow: host owner; active team with merch.scan_pickup_qr / merch.mark_picked_up
    (host-wide or scoped); valid merch_pickup (or event_ops) staff assignment.
    Does not grant catalog edit. ``merch.fulfill_orders`` alone is not enough to scan.
    """
    if _is_platform_admin(db, user_id):
        return True
    event = db.get(Event, event_id)
    if event is None or event.host_id != host_profile_id:
        return False
    if is_host_owner(db, user_id, host_profile_id):
        return True
    if team_membership_blocks_desk(db, user_id, host_profile_id):
        return False

    if has_event_staff_assignment(
        db, user_id=user_id, event_id=event_id, permission="merch.scan_pickup_qr"
    ):
        return True

    membership = get_team_membership(db, user_id, host_profile_id)
    if membership is None:
        return False
    if not _team_has_desk_permission(
        db,
        user_id=user_id,
        host_profile_id=host_profile_id,
        permissions=("merch.scan_pickup_qr", "merch.mark_picked_up"),
    ):
        return False
    scope, scoped_ids = membership_scope(membership)
    if scope == SCOPE_HOST_WIDE:
        return True
    return event_id in scoped_ids


def merch_scan_denial_reason(
    db: Session,
    user_id: uuid.UUID,
    host_profile_id: uuid.UUID,
    event_id: uuid.UUID,
) -> str | None:
    if can_scan_merch_pickup(db, user_id, host_profile_id, event_id):
        return None
    event = db.get(Event, event_id)
    if event is None:
        return "Event not found"
    if event.host_id != host_profile_id:
        return "Event does not belong to this host"

    any_membership = db.scalar(
        select(HostTeamMember).where(
            HostTeamMember.host_id == host_profile_id,
            HostTeamMember.user_id == user_id,
        )
    )
    if any_membership is not None:
        if any_membership.status == "suspended":
            return "Team membership is suspended"
        if any_membership.status == "removed" or any_membership.removed_at is not None:
            return "Team membership has been removed"
        if any_membership.status != "active":
            return f"Team membership is {any_membership.status}"
        if not _team_has_desk_permission(
            db,
            user_id=user_id,
            host_profile_id=host_profile_id,
            permissions=("merch.scan_pickup_qr", "merch.mark_picked_up"),
        ):
            return "Team member lacks merch.scan_pickup_qr / merch.mark_picked_up"
        scope, scoped_ids = membership_scope(any_membership)
        if scope != SCOPE_HOST_WIDE and event_id not in scoped_ids:
            return "Merch scanner is not scoped to this event"

    staff = _inactive_staff_row(db, user_id=user_id, event_id=event_id)
    if staff is not None:
        now = datetime.now(UTC)
        if staff.status != "active":
            return f"Event staff assignment is {staff.status}"
        expires = _as_utc(staff.expires_at)
        if expires is not None and expires <= now:
            return "Event staff assignment has expired"
        at = (staff.assignment_type or "").strip().lower()
        if at not in {"merch_pickup", "event_ops"} and "merch" not in (
            staff.role_label or ""
        ).lower():
            return "Event staff assignment is not merch pickup for this event"

    return "Not authorized to scan merch pickup for this event"


def require_host_permission(
    db: Session,
    user_id: uuid.UUID,
    host_profile_id: uuid.UUID,
    permission: str | tuple[str, ...] | list[str],
) -> Host:
    """Raise 403 unless the user may perform a host-scoped action. Returns host."""
    host = db.get(Host, host_profile_id)
    if host is None or host.status != "active":
        raise HTTPException(status_code=404, detail="Host not found")

    permissions = (permission,) if isinstance(permission, str) else tuple(permission)
    if any(
        has_host_permission(db, user_id, host_profile_id, p) for p in permissions
    ):
        return host

    from app.teams.team_audit import write_permission_denied_audit

    write_permission_denied_audit(
        db,
        host_id=host.id,
        actor_user_id=user_id,
        permission=permissions[0],
    )
    try:
        db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Missing permission: {permissions[0]}",
    )


def require_event_permission(
    db: Session,
    user_id: uuid.UUID,
    host_profile_id: uuid.UUID,
    event_id: uuid.UUID,
    permission: str | tuple[str, ...] | list[str],
) -> Event:
    """Raise 403 unless the user may perform an event-scoped action. Returns event."""
    event = db.get(Event, event_id)
    if event is None or event.host_id != host_profile_id:
        raise HTTPException(status_code=404, detail="Event not found")

    permissions = (permission,) if isinstance(permission, str) else tuple(permission)
    if any(
        has_event_permission(db, user_id, host_profile_id, event_id, p)
        for p in permissions
    ):
        return event

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Missing permission: {permissions[0]}",
    )
