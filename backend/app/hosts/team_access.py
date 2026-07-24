"""Resolve which host a user may administer for team / sensitive ops.

Product rule: host owner OR active team member with the required permission
may perform host operations. Owner-only keys stay in OWNER_ONLY_PERMISSION_KEYS
(e.g. finance.manage_payout_settings) unless the owner explicitly grants them.
"""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.hosts.models import Host
from app.hosts.service import get_host_by_id, get_host_by_user_id
from app.teams.permissions import (
    has_event_permission,
    has_host_permission,
    is_host_owner as _is_owner_by_ids,
)
from app.teams.team_audit import write_permission_denied_audit
from app.users.models import User
from app.users.service import user_has_permission, user_has_role


def is_host_owner(host: Host, user: User) -> bool:
    return host.user_id == user.id


def _deny(
    db: Session, *, host_id: uuid.UUID, user_id: uuid.UUID, permission: str
) -> None:
    write_permission_denied_audit(
        db,
        host_id=host_id,
        actor_user_id=user_id,
        permission=permission,
    )
    try:
        db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Missing permission: {permission}",
    )


def require_host_for_permission(
    db: Session,
    *,
    user: User,
    host_id: uuid.UUID | None,
    permission: str | tuple[str, ...],
) -> tuple[Host, bool]:
    """Return (host, actor_is_owner).

    - ``host_id`` None → owned host if present; else active workspace (team).
    - Owner always allowed.
    - Active team member allowed when any listed permission is granted
      (host-wide membership permission).
    """
    from app.users.restrictions import assert_no_restriction

    permissions = (permission,) if isinstance(permission, str) else tuple(permission)

    # Map host permission codes → selective restriction keys (fail closed).
    _host_restriction_map = {
        "events.create": "cannot_create_events",
        "events.publish": "cannot_publish_events",
        "events.manage_own": "cannot_manage_events",
        "events.update_own": "cannot_manage_events",
        "events.read_own": None,  # view not blocked by manage restriction alone
        "tickets.manage": "cannot_manage_tickets",
        "tickets.scan": "cannot_scan_tickets",
        "ticket_types.update": "cannot_manage_tickets",
        "ticket_types.deactivate": "cannot_manage_tickets",
        "merch.create": "cannot_manage_merch",
        "merch.manage_own": "cannot_manage_merch",
        "merch.fulfill": "cannot_fulfill_merch",
        "merch.view_fulfillment": "cannot_fulfill_merch",
        "team.invite": "cannot_invite_host_team",
        "team.manage": "cannot_invite_host_team",
        "sponsorships.manage": "cannot_manage_sponsorships",
        "ambassadors.manage": "cannot_manage_host_ambassadors",
        "finance.view": "cannot_view_host_finance",
        "finance.manage_payout_settings": "cannot_view_host_finance",
        "payouts.request": "cannot_view_host_finance",
    }
    for perm in permissions:
        key = _host_restriction_map.get(perm)
        if key:
            assert_no_restriction(db, user.id, key)
        # Broad manage / create verbs
        if "merch" in perm and "fulfill" not in perm:
            assert_no_restriction(db, user.id, "cannot_manage_merch")
        if perm.startswith("events.") and perm not in {
            "events.read_own",
            "events.create",
            "events.publish",
        }:
            assert_no_restriction(db, user.id, "cannot_manage_events")

    if host_id is None:
        from app.teams.workspace_pref import get_active_workspace_id

        active = get_active_workspace_id(db, user_id=user.id)
        owned = get_host_by_user_id(db, user.id)
        if active is not None:
            host_id = active
        elif owned is not None:
            return owned, True
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Host profile not found. Complete onboarding first.",
            )

    host = get_host_by_id(db, host_id)
    if host is None or host.status != "active":
        raise HTTPException(status_code=404, detail="Host not found")

    if is_host_owner(host, user) or _is_owner_by_ids(db, user.id, host.id):
        return host, True

    if any(
        has_host_permission(db, user.id, host.id, perm) for perm in permissions
    ):
        return host, False

    _deny(db, host_id=host.id, user_id=user.id, permission=permissions[0])
    raise AssertionError("unreachable")  # pragma: no cover


def require_host_event_permission(
    db: Session,
    *,
    user: User,
    event_id: uuid.UUID,
    permission: str | tuple[str, ...],
    host_id: uuid.UUID | None = None,
) -> tuple[Host, object]:
    """Return (host, event) when actor may perform ``permission`` on the event.

    Owner of the event's host, platform admin, or active team member with
    host-wide / event-scoped permission.
    """
    from app.events.models import Event

    permissions = (permission,) if isinstance(permission, str) else tuple(permission)
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    host = get_host_by_id(db, event.host_id)
    if host is None or host.status != "active":
        raise HTTPException(status_code=404, detail="Host not found")

    if user_has_role(user, "super_admin") or user_has_permission(
        user, "admin.full_access"
    ):
        return host, event

    if host_id is not None and host_id != event.host_id:
        raise HTTPException(
            status_code=403, detail="You can only manage events for this host"
        )

    if is_host_owner(host, user) or _is_owner_by_ids(db, user.id, host.id):
        return host, event

    if any(
        has_event_permission(db, user.id, host.id, event.id, perm)
        for perm in permissions
    ):
        return host, event

    # Unrelated actors: hide event existence. Team members with wrong
    # permission get an explicit 403.
    from app.teams.permissions import get_team_membership

    if get_team_membership(db, user.id, host.id) is None:
        raise HTTPException(status_code=404, detail="Event not found")

    _deny(db, host_id=host.id, user_id=user.id, permission=permissions[0])
    raise AssertionError("unreachable")  # pragma: no cover
