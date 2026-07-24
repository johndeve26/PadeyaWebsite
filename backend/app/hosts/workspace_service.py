"""List host workspaces a user can access (owned + team + event staff)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.checkins.models import EventStaffAssignment
from app.events.models import Event
from app.hosts.models import Host, HostTeamMember
from app.hosts.service import get_host_by_user_id
from app.hosts.team_permissions import (
    PERMISSION_KEYS,
    membership_scope,
    normalize_permissions_dict,
    permissions_for_role,
)
from app.users.models import User


def _owner_permissions() -> dict[str, bool]:
    return {key: True for key in PERMISSION_KEYS}


def list_user_workspaces(db: Session, *, user: User) -> list[dict[str, Any]]:
    """Return workspaces: owned host, active team memberships, event-staff hosts."""
    by_host: dict[uuid.UUID, dict[str, Any]] = {}

    owned = get_host_by_user_id(db, user.id)
    if owned is not None:
        by_host[owned.id] = {
            "host_id": owned.id,
            "display_name": owned.display_name,
            "slug": owned.slug,
            "kind": "owner",
            "role": "owner",
            "role_label": "Owner",
            "permissions": _owner_permissions(),
            "scope": "host_wide",
            "scoped_event_ids": [],
            "membership_id": None,
            "is_owner": True,
        }

    memberships = list(
        db.scalars(
            select(HostTeamMember).where(
                HostTeamMember.user_id == user.id,
                HostTeamMember.status == "active",
                HostTeamMember.removed_at.is_(None),
            )
        )
    )
    for row in memberships:
        if row.host_id in by_host and by_host[row.host_id]["kind"] == "owner":
            continue
        host = db.get(Host, row.host_id)
        if host is None or host.status != "active":
            continue
        perms = normalize_permissions_dict(
            row.permissions_json or permissions_for_role(row.role)
        )
        scope, scoped_ids = membership_scope(row)
        by_host[row.host_id] = {
            "host_id": host.id,
            "display_name": host.display_name,
            "slug": host.slug,
            "kind": "team_member",
            "role": row.role,
            "role_label": row.role_label,
            "permissions": perms,
            "scope": scope,
            "scoped_event_ids": [str(eid) for eid in scoped_ids],
            "membership_id": row.id,
            "is_owner": False,
        }

    staff_host_ids = db.scalars(
        select(Event.host_id)
        .join(EventStaffAssignment, EventStaffAssignment.event_id == Event.id)
        .where(
            EventStaffAssignment.user_id == user.id,
            EventStaffAssignment.status == "active",
        )
        .distinct()
    ).all()
    for host_id in staff_host_ids:
        if host_id in by_host:
            continue
        host = db.get(Host, host_id)
        if host is None or host.status != "active":
            continue
        by_host[host_id] = {
            "host_id": host.id,
            "display_name": host.display_name,
            "slug": host.slug,
            "kind": "event_staff",
            "role": "scanner",
            "role_label": "Event staff",
            "permissions": normalize_permissions_dict(
                {
                    "events.view": True,
                    "tickets.view": True,
                    "merch.view": True,
                }
            ),
            "scope": "selected_events",
            "scoped_event_ids": [],
            "membership_id": None,
            "is_owner": False,
        }

    return sorted(by_host.values(), key=lambda w: (not w["is_owner"], w["display_name"].lower()))


def list_desk_events_for_workspace(
    db: Session, *, user: User, host_id: uuid.UUID
) -> list[dict[str, Any]]:
    """Events under a host that the user may scan (hybrid)."""
    from app.checkins.permissions import can_scan_event

    host = db.get(Host, host_id)
    if host is None:
        return []

    events = list(
        db.scalars(
            select(Event)
            .where(Event.host_id == host_id)
            .order_by(Event.start_datetime.desc())
            .limit(100)
        )
    )
    from app.events.privacy import public_location_label
    from app.teams.permissions import is_host_owner

    out: list[dict[str, Any]] = []
    owner = is_host_owner(db, user.id, host_id)
    for event in events:
        if not can_scan_event(db, user, event.id):
            continue
        # Safe public label for all desk users; street/coords never on desk list.
        # Owners may see venue_name when operationally useful at the door.
        safe_label = public_location_label(event)
        venue_name = None
        visibility = getattr(event, "location_visibility", None) or "full_public"
        if owner or visibility in {"full_public", "area_only", "online_only"}:
            venue_name = event.venue_name
        out.append(
            {
                "id": event.id,
                "title": event.title,
                "slug": event.slug,
                "status": event.status,
                "start_datetime": event.start_datetime,
                "location_label": safe_label,
                "venue_name": venue_name,
                "staff_check_in_path": f"/staff/check-in/{event.id}",
                "host_check_in_path": f"/host/events/{event.id}/check-in",
            }
        )
    return out
