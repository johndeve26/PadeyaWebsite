"""Authorization helpers for event scanning.

Desk scan enforcement delegates to ``app.teams.permissions`` (central checker).
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.events.models import Event
from app.users.models import User
from app.users.service import user_has_permission, user_has_role


def get_event_or_none(db: Session, event_id: uuid.UUID) -> Event | None:
    return db.get(Event, event_id)


def is_event_staff(db: Session, *, user_id: uuid.UUID, event_id: uuid.UUID) -> bool:
    from app.teams.permissions import has_event_staff_assignment

    return has_event_staff_assignment(
        db, user_id=user_id, event_id=event_id, permission=None
    )


def can_scan_event(db: Session, user: User, event_id: uuid.UUID) -> bool:
    """Hybrid: host owner, scoped team desk perms, or event_staff_assignments."""
    if user_has_role(user, "super_admin") or user_has_permission(user, "admin.full_access"):
        return True

    event = get_event_or_none(db, event_id)
    if event is None:
        return False

    from app.teams.permissions import can_scan_ticket

    return can_scan_ticket(
        db,
        user_id=user.id,
        host_profile_id=event.host_id,
        event_id=event_id,
    )


def can_manage_event_staff(db: Session, user: User, event_id: uuid.UUID) -> bool:
    if user_has_role(user, "super_admin") or user_has_permission(user, "admin.full_access"):
        return True
    event = get_event_or_none(db, event_id)
    if event is None:
        return False

    from app.teams.permissions import has_event_permission

    return has_event_permission(
        db,
        user_id=user.id,
        host_profile_id=event.host_id,
        event_id=event_id,
        permission="events.edit",
    ) or has_event_permission(
        db,
        user_id=user.id,
        host_profile_id=event.host_id,
        event_id=event_id,
        permission="events.publish",
    )


def can_override_checkin(user: User) -> bool:
    return user_has_role(user, "super_admin") or user_has_permission(user, "admin.full_access")
