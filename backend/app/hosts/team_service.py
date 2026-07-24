"""Host org team invites, members, permissions, and lifecycle."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.checkins.models import EventStaffAssignment
from app.hosts.lifecycle_schemas import (
    HostTeamMemberCreate,
    HostTeamMemberInvite,
    HostTeamMemberUpdate,
    HostTeamPermissionsUpdate,
)
from app.hosts.models import Host, HostTeamInvite, HostTeamMember
from app.hosts.team_access import require_host_for_permission
from app.hosts.team_invite_resolve import resolve_invitee
from app.passport.models import FanPassport
from app.passport.privacy import is_publicly_reachable
from app.teams import notify as team_notify
from app.teams.team_audit import (
    finance_keys_granted,
    list_host_audit_feed,
    write_team_audit,
)
from app.hosts.team_permissions import (
    SCOPE_SELECTED_EVENTS,
    apply_permission_update,
    default_role_label,
    membership_scope,
    normalize_permissions_dict,
    normalize_role,
    normalize_scope,
    pack_scope_json,
    parse_scoped_event_ids,
    permissions_for_role,
    scoped_event_ids_as_str,
    unpack_scope_json,
)
from app.users.models import User
from app.users.service import get_role_by_name, get_user_by_email, get_user_by_id

INVITE_TTL_DAYS = 7


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _new_invite_token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(32)
    return raw, _hash_token(raw)


def _email_hint(email: str) -> str:
    local, _, domain = email.partition("@")
    if not domain:
        return "***"
    keep = local[:1] if local else "*"
    return f"{keep}***@{domain}"


def _permission_overrides(raw: Any) -> dict[str, Any] | None:
    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw
    if hasattr(raw, "model_dump"):
        return raw.model_dump(exclude_unset=True)
    return dict(raw)


def _assignment_type_for_role(role: str) -> str:
    if role == "merch_staff":
        return "merch_pickup"
    if role in {"event_manager", "viewer", "admin", "support_staff", "sponsor_manager"}:
        return "event_ops"
    return "ticket_scanner"


def _write_team_audit(
    db: Session,
    *,
    host_id: uuid.UUID,
    action: str,
    actor_user_id: uuid.UUID | None,
    target_user_id: uuid.UUID | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    write_team_audit(
        db,
        host_id=host_id,
        action=action,
        actor_user_id=actor_user_id,
        target_user_id=target_user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata=metadata,
    )


def _public_invitee_surface(
    db: Session,
    *,
    user_id: uuid.UUID | None,
    invite_method: str,
    invited_username: str | None,
    fallback_email: str | None = None,
) -> dict[str, Any]:
    """Host-safe invitee fields — never leak private email for username invites."""
    kind = (invite_method or "email").strip().lower()
    username = (invited_username or "").strip().lstrip("@").lower() or None
    display_name: str | None = None
    avatar_url: str | None = None

    if user_id is not None:
        user = get_user_by_id(db, user_id)
        passport = db.scalar(
            select(FanPassport).where(FanPassport.user_id == user_id)
        )
        if passport is not None:
            if not username and passport.username:
                username = passport.username
            display_name = passport.display_name or None
            if passport.avatar_url and is_publicly_reachable(passport.visibility):
                avatar_url = passport.avatar_url
        if user is not None and not display_name:
            display_name = user.full_name or None

    if kind == "username":
        return {
            "invite_method": "username",
            "invited_username": f"@{username}" if username else None,
            "invited_email": None,
            "display_name": display_name or (f"@{username}" if username else None),
            "avatar_url": avatar_url,
        }

    email = (fallback_email or "").strip().lower() or None
    if not display_name and user_id is not None:
        user = get_user_by_id(db, user_id)
        if user is not None:
            display_name = user.full_name or email
    return {
        "invite_method": "email",
        "invited_username": None,
        "invited_email": email,
        "display_name": display_name or email,
        "avatar_url": avatar_url,
    }


def _serialize_member(db: Session, row: HostTeamMember) -> dict[str, Any]:
    kind = getattr(row, "invite_method", None) or "email"
    username = getattr(row, "invited_username", None)
    user = get_user_by_id(db, row.user_id)
    surface = _public_invitee_surface(
        db,
        user_id=row.user_id,
        invite_method=kind,
        invited_username=username,
        fallback_email=user.email if user is not None else None,
    )
    scope, scoped_ids = membership_scope(row)
    return {
        "id": row.id,
        "host_id": row.host_id,
        "user_id": row.user_id,
        "role": row.role,
        "role_label": row.role_label,
        "status": row.status,
        "permissions": normalize_permissions_dict(row.permissions_json),
        "scope": scope,
        "scoped_event_ids": scoped_ids,
        "invite_expires_at": None,
        "invited_at": None,
        "accepted_at": row.joined_at,
        "suspended_at": row.suspended_at,
        "archived_at": row.removed_at,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        **surface,
    }


def serialize_invite(db: Session, row: HostTeamInvite) -> dict[str, Any]:
    kind = getattr(row, "invite_method", None) or "email"
    username = getattr(row, "invited_username", None)
    surface = _public_invitee_surface(
        db,
        user_id=row.invited_user_id,
        invite_method=kind,
        invited_username=username,
        fallback_email=row.email,
    )
    scope, scoped_ids = unpack_scope_json(row.scope_json, role=row.role)
    api_status = row.status
    if api_status == "revoked":
        api_status = "declined"
    return {
        "id": row.id,
        "host_id": row.host_id,
        "user_id": row.invited_user_id,
        "role": row.role,
        "role_label": row.role_label,
        "status": api_status,
        "permissions": normalize_permissions_dict(row.permissions_json),
        "scope": scope,
        "scoped_event_ids": scoped_ids,
        "invite_expires_at": row.expires_at,
        "invited_at": row.created_at,
        "accepted_at": row.accepted_at,
        "suspended_at": None,
        "archived_at": row.revoked_at,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        **surface,
    }


def _validate_scoped_events(
    db: Session, *, host_id: uuid.UUID, event_ids: list[uuid.UUID]
) -> list[uuid.UUID]:
    from app.events.models import Event

    if not event_ids:
        return []
    valid = set(
        db.scalars(
            select(Event.id).where(
                Event.host_id == host_id, Event.id.in_(event_ids)
            )
        ).all()
    )
    missing = [eid for eid in event_ids if eid not in valid]
    if missing:
        raise HTTPException(
            status_code=400,
            detail="One or more scoped events do not belong to this host",
        )
    return event_ids


def _apply_scope(
    db: Session,
    *,
    host_id: uuid.UUID,
    role: str,
    scope: str | None,
    scoped_event_ids: list[uuid.UUID] | None,
) -> dict[str, Any]:
    resolved = normalize_scope(scope, role=role)
    ids = parse_scoped_event_ids(scoped_event_ids or [])
    if resolved == SCOPE_SELECTED_EVENTS:
        ids = _validate_scoped_events(db, host_id=host_id, event_ids=ids)
    else:
        ids = []
    return pack_scope_json(resolved, ids)


def _sync_event_staff_for_scope(
    db: Session,
    *,
    row: HostTeamMember,
    actor_user_id: uuid.UUID | None,
) -> None:
    """Upsert event_staff_assignments for selected-event desk roles."""
    scope, ids = membership_scope(row)
    if scope != SCOPE_SELECTED_EVENTS:
        return
    if row.role not in {"scanner", "merch_staff", "event_manager", "viewer"}:
        return
    if not ids:
        return
    label = row.role_label or row.role
    assignment_type = _assignment_type_for_role(row.role)
    for event_id in ids:
        existing = db.scalar(
            select(EventStaffAssignment).where(
                EventStaffAssignment.event_id == event_id,
                EventStaffAssignment.user_id == row.user_id,
            )
        )
        if existing is not None:
            existing.team_member_id = row.id
            existing.assignment_type = assignment_type
            existing.role_label = label
            existing.permissions_json = normalize_permissions_dict(row.permissions_json)
            existing.status = "active"
            continue
        db.add(
            EventStaffAssignment(
                event_id=event_id,
                user_id=row.user_id,
                team_member_id=row.id,
                assigned_by_user_id=actor_user_id,
                assignment_type=assignment_type,
                role_label=label,
                permissions_json=normalize_permissions_dict(row.permissions_json),
                status="active",
            )
        )


def list_team_members(
    db: Session,
    *,
    user: User,
    include_archived: bool = False,
    host_id: uuid.UUID | None = None,
    include: Literal["all", "members", "invites"] = "all",
) -> list[dict[str, Any]]:
    host, _ = require_host_for_permission(
        db, user=user, host_id=host_id, permission="team.view"
    )
    rows: list[dict[str, Any]] = []

    if include in ("all", "members"):
        member_q = select(HostTeamMember).where(HostTeamMember.host_id == host.id)
        if not include_archived:
            member_q = member_q.where(
                HostTeamMember.status != "removed",
                HostTeamMember.removed_at.is_(None),
            )
        members = list(db.scalars(member_q.order_by(HostTeamMember.created_at.desc())))
        rows.extend(_serialize_member(db, m) for m in members)

    if include in ("all", "invites"):
        invite_q = select(HostTeamInvite).where(HostTeamInvite.host_id == host.id)
        if not include_archived:
            invite_q = invite_q.where(
                HostTeamInvite.status.in_(("pending", "expired")),
            )
        invites = list(db.scalars(invite_q.order_by(HostTeamInvite.created_at.desc())))
        rows.extend(serialize_invite(db, i) for i in invites)

    rows.sort(key=lambda r: r["created_at"] or datetime.min.replace(tzinfo=UTC), reverse=True)
    return rows


def _resolve_team_entity(
    db: Session, *, host_id: uuid.UUID, entity_id: uuid.UUID
) -> tuple[Literal["member", "invite"], HostTeamMember | HostTeamInvite]:
    member = db.get(HostTeamMember, entity_id)
    if member is not None and member.host_id == host_id:
        return "member", member
    invite = db.get(HostTeamInvite, entity_id)
    if invite is not None and invite.host_id == host_id:
        return "invite", invite
    raise HTTPException(status_code=404, detail="Team member not found")


def get_team_member(
    db: Session,
    *,
    user: User,
    member_id: uuid.UUID,
    host_id: uuid.UUID | None = None,
    permission: str | tuple[str, ...] = "team.view",
) -> HostTeamMember | HostTeamInvite:
    host, _ = require_host_for_permission(
        db, user=user, host_id=host_id, permission=permission
    )
    _, row = _resolve_team_entity(db, host_id=host.id, entity_id=member_id)
    return row


def get_team_member_public(
    db: Session,
    *,
    user: User,
    member_id: uuid.UUID,
    host_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    host, _ = require_host_for_permission(
        db, user=user, host_id=host_id, permission="team.view"
    )
    kind, row = _resolve_team_entity(db, host_id=host.id, entity_id=member_id)
    if kind == "invite":
        return serialize_invite(db, row)  # type: ignore[arg-type]
    return _serialize_member(db, row)  # type: ignore[arg-type]


def _grant_host_staff(db: Session, target: User) -> None:
    staff_role = get_role_by_name(db, "host_staff")
    if staff_role and staff_role not in target.roles:
        target.roles.append(staff_role)


def _deactivate_event_staff_for_member(db: Session, row: HostTeamMember) -> None:
    """Revoke desk/event staff for this host immediately on suspend/remove."""
    from app.events.models import Event

    host_event_ids = select(Event.id).where(Event.host_id == row.host_id)
    assignments = list(
        db.scalars(
            select(EventStaffAssignment).where(
                EventStaffAssignment.status == "active",
                or_(
                    EventStaffAssignment.team_member_id == row.id,
                    and_(
                        EventStaffAssignment.user_id == row.user_id,
                        EventStaffAssignment.event_id.in_(host_event_ids),
                    ),
                ),
            )
        )
    )
    for assignment in assignments:
        assignment.status = "inactive"


def _maybe_revoke_host_staff(db: Session, target: User) -> None:
    other_team = db.scalar(
        select(HostTeamMember.id).where(
            HostTeamMember.user_id == target.id,
            HostTeamMember.status == "active",
            HostTeamMember.removed_at.is_(None),
        )
    )
    if other_team is not None:
        return
    other_event = db.scalar(
        select(EventStaffAssignment.id).where(
            EventStaffAssignment.user_id == target.id,
            EventStaffAssignment.status == "active",
        )
    )
    if other_event is not None:
        return
    staff_role = get_role_by_name(db, "host_staff")
    if staff_role and staff_role in target.roles:
        target.roles.remove(staff_role)


def _enqueue_invite_email(
    db: Session,
    *,
    host: Host,
    row: HostTeamInvite,
    raw_token: str,
) -> None:
    team_notify.enqueue_team_invite_email(
        db, host=host, invite=row, raw_token=raw_token
    )


def _notify_host_invite_accepted(
    db: Session,
    *,
    host: Host,
    invite: HostTeamInvite,
    member_user: User,
) -> None:
    team_notify.notify_host_invite_accepted(
        db, host=host, invite=invite, member_user=member_user
    )


def _expire_invite_if_needed(db: Session, row: HostTeamInvite) -> HostTeamInvite:
    if row.status != "pending":
        return row
    expires = _as_utc(row.expires_at)
    if expires is not None and expires < datetime.now(UTC):
        row.status = "expired"
        db.flush()
    return row


def invite_team_member(
    db: Session,
    *,
    user: User,
    payload: HostTeamMemberInvite,
    host_id: uuid.UUID | None = None,
) -> HostTeamInvite:
    host, actor_is_owner = require_host_for_permission(
        db, user=user, host_id=host_id, permission="team.invite"
    )
    identifier = payload.invite_identifier or payload.email
    if not identifier:
        raise HTTPException(status_code=400, detail="invite_identifier is required")
    resolved = resolve_invitee(db, str(identifier))
    email = resolved.email
    existing_user = resolved.user
    invite_method = resolved.kind
    invited_username = resolved.username

    if existing_user is not None and existing_user.id == user.id:
        raise HTTPException(status_code=400, detail="Cannot invite yourself")
    if email == (user.email or "").strip().lower():
        raise HTTPException(status_code=400, detail="Cannot invite yourself")
    owner = get_user_by_id(db, host.user_id)
    if owner is not None and (
        (existing_user is not None and existing_user.id == owner.id)
        or email == (owner.email or "").strip().lower()
    ):
        raise HTTPException(
            status_code=400,
            detail="The host owner already has full access and cannot be invited as a team member",
        )

    role = normalize_role(payload.role)
    role_label = (payload.role_label or default_role_label(role)).strip()
    overrides = _permission_overrides(
        payload.permissions_json
        if payload.permissions_json is not None
        else payload.permissions
    )
    perms = apply_permission_update(
        role=role,
        current=None,
        overrides=overrides,
        actor_is_owner=actor_is_owner,
    )
    scope_json = _apply_scope(
        db,
        host_id=host.id,
        role=role,
        scope=payload.scope,
        scoped_event_ids=payload.selected_event_ids or payload.scoped_event_ids,
    )

    if existing_user is not None:
        active = db.scalar(
            select(HostTeamMember).where(
                HostTeamMember.host_id == host.id,
                HostTeamMember.user_id == existing_user.id,
                HostTeamMember.status == "active",
                HostTeamMember.removed_at.is_(None),
            )
        )
        if active is not None:
            raise HTTPException(status_code=409, detail="User already on team")

    # Prevent duplicate pending (replace expired/revoked) for same email or user.
    existing_invite = db.scalar(
        select(HostTeamInvite).where(
            HostTeamInvite.host_id == host.id,
            func.lower(HostTeamInvite.email) == email,
            HostTeamInvite.status.in_(("pending", "expired", "revoked")),
        )
    )
    if existing_invite is None and existing_user is not None:
        existing_invite = db.scalar(
            select(HostTeamInvite).where(
                HostTeamInvite.host_id == host.id,
                HostTeamInvite.invited_user_id == existing_user.id,
                HostTeamInvite.status.in_(("pending", "expired", "revoked")),
            )
        )

    raw_token, token_hash = _new_invite_token()
    now = datetime.now(UTC)
    expires = now + timedelta(days=INVITE_TTL_DAYS)

    if existing_invite is not None:
        row = existing_invite
        row.status = "pending"
        row.role = role
        row.role_label = role_label
        row.permissions_json = perms
        row.scope_json = scope_json
        row.email = email
        row.invite_method = invite_method
        row.invited_username = invited_username
        row.invited_user_id = existing_user.id if existing_user else None
        row.token_hash = token_hash
        row.expires_at = expires
        row.accepted_at = None
        row.revoked_at = None
        row.invited_by_user_id = user.id
        action = "hosts.team_resend"
    else:
        row = HostTeamInvite(
            host_id=host.id,
            email=email,
            invite_method=invite_method,
            invited_username=invited_username,
            role=role,
            role_label=role_label,
            status="pending",
            permissions_json=perms,
            scope_json=scope_json,
            token_hash=token_hash,
            expires_at=expires,
            invited_by_user_id=user.id,
            invited_user_id=existing_user.id if existing_user else None,
        )
        db.add(row)
        action = "hosts.team_invite"

    db.flush()
    _enqueue_invite_email(db, host=host, row=row, raw_token=raw_token)
    # Host-facing audit: never store private account email for username invites.
    audit_meta: dict[str, Any] = {
        "invite_method": invite_method,
        "role": role,
        "role_label": role_label,
        "scope": scope_json.get("type"),
        "scoped_event_count": len(scope_json.get("event_ids") or []),
    }
    if invite_method == "username" and invited_username:
        audit_meta["invited_username"] = invited_username
    else:
        audit_meta["invited_email"] = email
    _write_team_audit(
        db,
        host_id=host.id,
        action=action,
        actor_user_id=user.id,
        target_user_id=row.invited_user_id,
        entity_type="host_team_invite",
        entity_id=str(row.id),
        metadata=audit_meta,
    )
    db.commit()
    db.refresh(row)
    return row


def serialize_invite_created(db: Session, row: HostTeamInvite) -> dict[str, Any]:
    """Compact create response — no private email for username invites."""
    method = (getattr(row, "invite_method", None) or "email").strip().lower()
    api_status = "declined" if row.status == "revoked" else row.status
    base: dict[str, Any] = {
        "invite_id": row.id,
        "invite_method": method,
        "status": api_status,
        "masked_email": None,
        "display_name": None,
        "username": None,
        "avatar_url": None,
    }
    if method == "username":
        surface = _public_invitee_surface(
            db,
            user_id=row.invited_user_id,
            invite_method="username",
            invited_username=row.invited_username,
            fallback_email=None,
        )
        base["display_name"] = surface.get("display_name")
        base["username"] = surface.get("invited_username")
        base["avatar_url"] = surface.get("avatar_url")
        return base

    base["masked_email"] = _email_hint(row.email or "")
    return base


def create_team_member(
    db: Session,
    *,
    user: User,
    payload: HostTeamMemberCreate,
    host_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Backward-compatible create → invite flow."""
    email = payload.invited_email
    if not email and payload.user_id is not None:
        target = get_user_by_id(db, payload.user_id)
        if target is None:
            raise HTTPException(status_code=404, detail="User not found")
        email = target.email
    if not email:
        raise HTTPException(status_code=400, detail="Provide invited_email or user_id")
    role = normalize_role(payload.role or payload.role_label)
    row = invite_team_member(
        db,
        user=user,
        host_id=host_id,
        payload=HostTeamMemberInvite(
            invite_identifier=email,
            role=role,
            role_label=payload.role_label or default_role_label(role),
            permissions_json=payload.permissions,
            scope=payload.scope,
            selected_event_ids=payload.scoped_event_ids,
        ),
    )
    return serialize_invite(db, row)


def _require_member(
    db: Session, *, host_id: uuid.UUID, member_id: uuid.UUID
) -> HostTeamMember:
    kind, row = _resolve_team_entity(db, host_id=host_id, entity_id=member_id)
    if kind != "member":
        raise HTTPException(
            status_code=400,
            detail="This action applies to accepted team members only",
        )
    return row  # type: ignore[return-value]


def _require_invite(
    db: Session, *, host_id: uuid.UUID, member_id: uuid.UUID
) -> HostTeamInvite:
    kind, row = _resolve_team_entity(db, host_id=host_id, entity_id=member_id)
    if kind != "invite":
        raise HTTPException(status_code=400, detail="Only pending invites can be resent")
    return row  # type: ignore[return-value]


def update_team_member(
    db: Session,
    *,
    user: User,
    member_id: uuid.UUID,
    payload: HostTeamMemberUpdate,
    host_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    host, actor_is_owner = require_host_for_permission(
        db, user=user, host_id=host_id, permission="team.edit_permissions"
    )
    kind, entity = _resolve_team_entity(db, host_id=host.id, entity_id=member_id)
    data = payload.model_dump(exclude_unset=True)

    if kind == "invite":
        row: HostTeamInvite = entity  # type: ignore[assignment]
        if row.status not in {"pending", "expired"}:
            raise HTTPException(status_code=400, detail="Invite is no longer editable")
        if "role" in data and data["role"] is not None:
            row.role = normalize_role(data["role"])
            row.role_label = data.get("role_label") or default_role_label(row.role)
            if "permissions" not in data:
                row.permissions_json = apply_permission_update(
                    role=row.role,
                    current=row.permissions_json,
                    overrides=permissions_for_role(row.role),
                    actor_is_owner=actor_is_owner,
                )
        if "role_label" in data and data["role_label"] is not None:
            row.role_label = data["role_label"]
        if "permissions" in data and data["permissions"] is not None:
            row.permissions_json = apply_permission_update(
                role=row.role,
                current=row.permissions_json,
                overrides=_permission_overrides(data["permissions"]),
                actor_is_owner=actor_is_owner,
            )
        if "scope" in data or "scoped_event_ids" in data:
            scope, current_ids = unpack_scope_json(row.scope_json, role=row.role)
            row.scope_json = _apply_scope(
                db,
                host_id=host.id,
                role=row.role,
                scope=data.get("scope", scope),
                scoped_event_ids=(
                    data["scoped_event_ids"]
                    if "scoped_event_ids" in data
                    else current_ids
                ),
            )
        _write_team_audit(
            db,
            host_id=host.id,
            action="hosts.team_update",
            actor_user_id=user.id,
            target_user_id=row.invited_user_id,
            entity_type="host_team_invite",
            entity_id=str(row.id),
            metadata={k: data[k] for k in data if k != "permissions"},
        )
        db.commit()
        db.refresh(row)
        return serialize_invite(db, row)

    row_m: HostTeamMember = entity  # type: ignore[assignment]
    if row_m.removed_at is not None or row_m.status == "removed":
        raise HTTPException(status_code=400, detail="Restore member before updating")
    before_perms = normalize_permissions_dict(row_m.permissions_json)
    before_scope, before_ids = membership_scope(row_m)
    if "role" in data and data["role"] is not None:
        row_m.role = normalize_role(data["role"])
        row_m.role_label = data.get("role_label") or default_role_label(row_m.role)
        if "permissions" not in data:
            row_m.permissions_json = apply_permission_update(
                role=row_m.role,
                current=row_m.permissions_json,
                overrides=permissions_for_role(row_m.role),
                actor_is_owner=actor_is_owner,
            )
    if "role_label" in data and data["role_label"] is not None:
        row_m.role_label = data["role_label"]
    if "permissions" in data and data["permissions"] is not None:
        row_m.permissions_json = apply_permission_update(
            role=row_m.role,
            current=row_m.permissions_json,
            overrides=_permission_overrides(data["permissions"]),
            actor_is_owner=actor_is_owner,
        )
    if "scope" in data or "scoped_event_ids" in data:
        scope, current_ids = membership_scope(row_m)
        row_m.scope_json = _apply_scope(
            db,
            host_id=host.id,
            role=row_m.role,
            scope=data.get("scope", scope),
            scoped_event_ids=(
                data["scoped_event_ids"]
                if "scoped_event_ids" in data
                else current_ids
            ),
        )
    status_changed_to_suspended = False
    if "status" in data and data["status"] is not None:
        if data["status"] not in {"active", "suspended", "inactive"}:
            raise HTTPException(status_code=400, detail="Invalid status")
        if data["status"] == "inactive":
            data["status"] = "suspended"
        if data["status"] == "suspended":
            _assert_not_host_owner_membership(db, row_m)
            row_m.status = "suspended"
            row_m.suspended_at = datetime.now(UTC)
            status_changed_to_suspended = True
        elif data["status"] == "active":
            row_m.status = "active"
            row_m.suspended_at = None
    if status_changed_to_suspended:
        _deactivate_event_staff_for_member(db, row_m)
        target = get_user_by_id(db, row_m.user_id)
        if target is not None:
            _maybe_revoke_host_staff(db, target)
    else:
        _sync_event_staff_for_scope(db, row=row_m, actor_user_id=user.id)
    after_perms = normalize_permissions_dict(row_m.permissions_json)
    after_scope, after_ids = membership_scope(row_m)
    _write_team_audit(
        db,
        host_id=host.id,
        action="hosts.team_update",
        actor_user_id=user.id,
        target_user_id=row_m.user_id,
        entity_type="host_team_member",
        entity_id=str(row_m.id),
        metadata={
            k: data[k]
            for k in data
            if k not in {"permissions", "scoped_event_ids"}
        },
    )
    if any(k in data for k in ("role", "role_label", "permissions")):
        _write_team_audit(
            db,
            host_id=host.id,
            action="hosts.team_permissions_update",
            actor_user_id=user.id,
            target_user_id=row_m.user_id,
            entity_type="host_team_member",
            entity_id=str(row_m.id),
            metadata={
                "role": row_m.role,
                "role_label": row_m.role_label,
                "scope": after_scope,
            },
        )
        for key in finance_keys_granted(before_perms, after_perms):
            _write_team_audit(
                db,
                host_id=host.id,
                action="hosts.team_finance_permission_grant",
                actor_user_id=user.id,
                target_user_id=row_m.user_id,
                entity_type="host_team_member",
                entity_id=str(row_m.id),
                metadata={"permission": key, "role": row_m.role},
            )
    if ("scope" in data or "scoped_event_ids" in data) and (
        before_scope != after_scope or set(before_ids) != set(after_ids)
    ):
        _write_team_audit(
            db,
            host_id=host.id,
            action="hosts.team_scope_update",
            actor_user_id=user.id,
            target_user_id=row_m.user_id,
            entity_type="host_team_member",
            entity_id=str(row_m.id),
            metadata={
                "scope": after_scope,
                "scoped_event_count": len(after_ids),
                "previous_scope": before_scope,
            },
        )
    if any(
        k in data
        for k in ("role", "role_label", "permissions", "scope", "scoped_event_ids")
    ):
        team_notify.notify_member_permissions_updated(
            db, host=host, member=row_m
        )
    if data.get("status") == "suspended":
        team_notify.notify_member_suspended(db, host=host, member=row_m)
    db.commit()
    db.refresh(row_m)
    return _serialize_member(db, row_m)


def update_team_permissions(
    db: Session,
    *,
    user: User,
    member_id: uuid.UUID,
    payload: HostTeamPermissionsUpdate,
    host_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    host, actor_is_owner = require_host_for_permission(
        db, user=user, host_id=host_id, permission="team.edit_permissions"
    )
    kind, entity = _resolve_team_entity(db, host_id=host.id, entity_id=member_id)

    if kind == "invite":
        row: HostTeamInvite = entity  # type: ignore[assignment]
        before_perms = normalize_permissions_dict(row.permissions_json)
        before_scope, before_ids = unpack_scope_json(row.scope_json, role=row.role)
        if payload.role is not None:
            row.role = normalize_role(payload.role)
        row.role_label = (
            payload.role_label
            if payload.role_label is not None
            else default_role_label(row.role)
        )
        row.permissions_json = apply_permission_update(
            role=row.role,
            current=row.permissions_json,
            overrides=_permission_overrides(payload.permissions),
            actor_is_owner=actor_is_owner,
        )
        if payload.scope is not None or payload.scoped_event_ids is not None:
            scope, current_ids = unpack_scope_json(row.scope_json, role=row.role)
            row.scope_json = _apply_scope(
                db,
                host_id=host.id,
                role=row.role,
                scope=payload.scope if payload.scope is not None else scope,
                scoped_event_ids=(
                    payload.scoped_event_ids
                    if payload.scoped_event_ids is not None
                    else current_ids
                ),
            )
        scope_out, ids_out = unpack_scope_json(row.scope_json, role=row.role)
        after_perms = normalize_permissions_dict(row.permissions_json)
        _write_team_audit(
            db,
            host_id=host.id,
            action="hosts.team_permissions_update",
            actor_user_id=user.id,
            target_user_id=row.invited_user_id,
            entity_type="host_team_invite",
            entity_id=str(row.id),
            metadata={
                "role": row.role,
                "role_label": row.role_label,
                "scope": scope_out,
                "scoped_event_count": len(ids_out),
                "invited_email": row.email,
            },
        )
        if before_scope != scope_out or set(before_ids) != set(ids_out):
            _write_team_audit(
                db,
                host_id=host.id,
                action="hosts.team_scope_update",
                actor_user_id=user.id,
                target_user_id=row.invited_user_id,
                entity_type="host_team_invite",
                entity_id=str(row.id),
                metadata={
                    "scope": scope_out,
                    "scoped_event_count": len(ids_out),
                    "previous_scope": before_scope,
                },
            )
        for key in finance_keys_granted(before_perms, after_perms):
            _write_team_audit(
                db,
                host_id=host.id,
                action="hosts.team_finance_permission_grant",
                actor_user_id=user.id,
                target_user_id=row.invited_user_id,
                entity_type="host_team_invite",
                entity_id=str(row.id),
                metadata={"permission": key, "role": row.role},
            )
        db.commit()
        db.refresh(row)
        return serialize_invite(db, row)

    row_m: HostTeamMember = entity  # type: ignore[assignment]
    if row_m.removed_at is not None or row_m.status == "removed":
        raise HTTPException(status_code=400, detail="Restore member before updating")
    before_perms = normalize_permissions_dict(row_m.permissions_json)
    before_scope, before_ids = membership_scope(row_m)
    if payload.role is not None:
        row_m.role = normalize_role(payload.role)
    row_m.role_label = (
        payload.role_label
        if payload.role_label is not None
        else default_role_label(row_m.role)
    )
    row_m.permissions_json = apply_permission_update(
        role=row_m.role,
        current=row_m.permissions_json,
        overrides=_permission_overrides(payload.permissions),
        actor_is_owner=actor_is_owner,
    )
    if payload.scope is not None or payload.scoped_event_ids is not None:
        scope, current_ids = membership_scope(row_m)
        row_m.scope_json = _apply_scope(
            db,
            host_id=host.id,
            role=row_m.role,
            scope=payload.scope if payload.scope is not None else scope,
            scoped_event_ids=(
                payload.scoped_event_ids
                if payload.scoped_event_ids is not None
                else current_ids
            ),
        )
    scope_out, ids_out = membership_scope(row_m)
    after_perms = normalize_permissions_dict(row_m.permissions_json)
    _sync_event_staff_for_scope(db, row=row_m, actor_user_id=user.id)
    _write_team_audit(
        db,
        host_id=host.id,
        action="hosts.team_permissions_update",
        actor_user_id=user.id,
        target_user_id=row_m.user_id,
        entity_type="host_team_member",
        entity_id=str(row_m.id),
        metadata={
            "role": row_m.role,
            "role_label": row_m.role_label,
            "scope": scope_out,
            "scoped_event_count": len(ids_out),
        },
    )
    if before_scope != scope_out or set(before_ids) != set(ids_out):
        _write_team_audit(
            db,
            host_id=host.id,
            action="hosts.team_scope_update",
            actor_user_id=user.id,
            target_user_id=row_m.user_id,
            entity_type="host_team_member",
            entity_id=str(row_m.id),
            metadata={
                "scope": scope_out,
                "scoped_event_count": len(ids_out),
                "previous_scope": before_scope,
            },
        )
    for key in finance_keys_granted(before_perms, after_perms):
        _write_team_audit(
            db,
            host_id=host.id,
            action="hosts.team_finance_permission_grant",
            actor_user_id=user.id,
            target_user_id=row_m.user_id,
            entity_type="host_team_member",
            entity_id=str(row_m.id),
            metadata={"permission": key, "role": row_m.role},
        )
    team_notify.notify_member_permissions_updated(db, host=host, member=row_m)
    db.commit()
    db.refresh(row_m)
    return _serialize_member(db, row_m)


def resend_invite(
    db: Session,
    *,
    user: User,
    member_id: uuid.UUID,
    host_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    host, _ = require_host_for_permission(
        db, user=user, host_id=host_id, permission="team.invite"
    )
    row = _require_invite(db, host_id=host.id, member_id=member_id)
    if row.status not in {"pending", "expired", "revoked"}:
        raise HTTPException(status_code=400, detail="Only pending invites can be resent")
    raw_token, token_hash = _new_invite_token()
    now = datetime.now(UTC)
    row.status = "pending"
    row.token_hash = token_hash
    row.expires_at = now + timedelta(days=INVITE_TTL_DAYS)
    row.revoked_at = None
    row.invited_by_user_id = user.id
    db.flush()
    _enqueue_invite_email(db, host=host, row=row, raw_token=raw_token)
    _write_team_audit(
        db,
        host_id=host.id,
        action="hosts.team_resend",
        actor_user_id=user.id,
        target_user_id=row.invited_user_id,
        entity_type="host_team_invite",
        entity_id=str(row.id),
        metadata={"invited_email": row.email},
    )
    db.commit()
    db.refresh(row)
    return serialize_invite(db, row)


def _assert_not_host_owner_membership(db: Session, row: HostTeamMember) -> None:
    host = db.get(Host, row.host_id)
    if host is not None and row.user_id == host.user_id:
        raise HTTPException(
            status_code=400,
            detail="The host owner cannot be suspended or removed from the team",
        )


def suspend_team_member(
    db: Session,
    *,
    user: User,
    member_id: uuid.UUID,
    host_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    host, _ = require_host_for_permission(
        db, user=user, host_id=host_id, permission="team.remove_members"
    )
    row = _require_member(db, host_id=host.id, member_id=member_id)
    _assert_not_host_owner_membership(db, row)
    row.status = "suspended"
    row.suspended_at = datetime.now(UTC)
    _deactivate_event_staff_for_member(db, row)
    target = get_user_by_id(db, row.user_id)
    if target is not None:
        _maybe_revoke_host_staff(db, target)
    _write_team_audit(
        db,
        host_id=row.host_id,
        action="hosts.team_suspend",
        actor_user_id=user.id,
        target_user_id=row.user_id,
        entity_type="host_team_member",
        entity_id=str(row.id),
    )
    team_notify.notify_member_suspended(db, host=host, member=row)
    db.commit()
    db.refresh(row)
    return _serialize_member(db, row)


def archive_team_member(
    db: Session,
    *,
    user: User,
    member_id: uuid.UUID,
    host_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    host, _ = require_host_for_permission(
        db, user=user, host_id=host_id, permission="team.remove_members"
    )
    kind, entity = _resolve_team_entity(db, host_id=host.id, entity_id=member_id)
    if kind == "invite":
        return revoke_team_invite(
            db, user=user, member_id=member_id, host_id=host.id
        )

    row_m: HostTeamMember = entity  # type: ignore[assignment]
    _assert_not_host_owner_membership(db, row_m)
    if row_m.removed_at is not None or row_m.status == "removed":
        return _serialize_member(db, row_m)
    row_m.status = "removed"
    row_m.removed_at = datetime.now(UTC)
    _deactivate_event_staff_for_member(db, row_m)
    target = get_user_by_id(db, row_m.user_id)
    if target is not None:
        _maybe_revoke_host_staff(db, target)
    _write_team_audit(
        db,
        host_id=row_m.host_id,
        action="hosts.team_remove",
        actor_user_id=user.id,
        target_user_id=row_m.user_id,
        entity_type="host_team_member",
        entity_id=str(row_m.id),
        metadata={"role": row_m.role, "role_label": row_m.role_label},
    )
    team_notify.notify_member_removed(db, host=host, member=row_m)
    db.commit()
    db.refresh(row_m)
    return _serialize_member(db, row_m)


def restore_team_member(
    db: Session,
    *,
    user: User,
    member_id: uuid.UUID,
    host_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    host, _ = require_host_for_permission(
        db, user=user, host_id=host_id, permission="team.remove_members"
    )
    kind, entity = _resolve_team_entity(db, host_id=host.id, entity_id=member_id)
    if kind == "invite":
        raise HTTPException(
            status_code=400,
            detail="Pending invites cannot be restored — resend the invite instead",
        )
    row: HostTeamMember = entity  # type: ignore[assignment]
    row.status = "active"
    row.removed_at = None
    row.suspended_at = None
    target = get_user_by_id(db, row.user_id)
    if target is not None:
        _grant_host_staff(db, target)
    _write_team_audit(
        db,
        host_id=row.host_id,
        action="hosts.team_restore",
        actor_user_id=user.id,
        target_user_id=row.user_id,
        entity_type="host_team_member",
        entity_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    return _serialize_member(db, row)


def delete_team_member_blocked() -> None:
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail="Hard delete blocked; use POST .../archive",
    )


def _find_invite_by_token(db: Session, token: str) -> HostTeamInvite:
    token_hash = _hash_token(token.strip())
    row = db.scalar(
        select(HostTeamInvite).where(HostTeamInvite.token_hash == token_hash)
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Invite not found")
    return row


def preview_team_invite(db: Session, *, token: str) -> dict[str, Any]:
    row = _find_invite_by_token(db, token)
    host = db.get(Host, row.host_id)
    if host is None:
        raise HTTPException(status_code=404, detail="Invite not found")
    row = _expire_invite_if_needed(db, row)
    if row.status == "expired":
        db.commit()
    status_value = row.status
    kind = getattr(row, "invite_method", None) or "email"
    username = getattr(row, "invited_username", None)
    if kind == "username" and username:
        invitee_hint = f"@{username.lstrip('@')}"
    else:
        invitee_hint = _email_hint(row.email or "") or "***"
    return {
        "host_display_name": host.display_name,
        "role": row.role,
        "role_label": row.role_label,
        "invite_method": kind,
        "invited_email_hint": invitee_hint,
        "expires_at": row.expires_at,
        "status": "declined" if status_value == "revoked" else status_value,
        "already_accepted": status_value == "accepted",
    }


def accept_team_invite(db: Session, *, user: User, token: str) -> dict[str, Any]:
    invite = _find_invite_by_token(db, token)
    invite = _expire_invite_if_needed(db, invite)

    if invite.status == "accepted":
        existing = db.scalar(
            select(HostTeamMember).where(
                HostTeamMember.host_id == invite.host_id,
                HostTeamMember.user_id == user.id,
                HostTeamMember.status == "active",
                HostTeamMember.removed_at.is_(None),
            )
        )
        if existing is not None:
            return _serialize_member(db, existing)
        raise HTTPException(status_code=400, detail="Invite was already accepted")

    if invite.status == "expired":
        db.commit()
        raise HTTPException(status_code=400, detail="Invite has expired")
    if invite.status == "revoked":
        raise HTTPException(status_code=400, detail="Invite has been revoked")
    if invite.status != "pending":
        raise HTTPException(status_code=400, detail="Invite is no longer available")

    from app.auth.verified_email import assert_verified_email

    assert_verified_email(user)

    method = (getattr(invite, "invite_method", None) or "email").strip().lower()
    if method == "username":
        # Only the invited Pàdéyá account may accept.
        if (
            invite.invited_user_id is None
            or user.id != invite.invited_user_id
        ):
            raise HTTPException(
                status_code=403,
                detail="This invite was sent to another Pàdéyá account.",
            )
    else:
        # Email invite: register/login first; signed-in email must match.
        if (invite.email or "").strip().lower() != (user.email or "").strip().lower():
            raise HTTPException(
                status_code=403,
                detail="Sign in with the invited email address to accept this Pàdéyá team invite",
            )
    conflict = db.scalar(
        select(HostTeamMember).where(
            HostTeamMember.host_id == invite.host_id,
            HostTeamMember.user_id == user.id,
            HostTeamMember.status == "active",
            HostTeamMember.removed_at.is_(None),
        )
    )
    if conflict is not None:
        raise HTTPException(status_code=409, detail="You are already on this host team")

    now = datetime.now(UTC)
    scope_json = invite.scope_json or pack_scope_json(
        normalize_scope(None, role=invite.role)
    )
    host = db.get(Host, invite.host_id)
    if host is None:
        raise HTTPException(status_code=404, detail="Invite not found")

    member = HostTeamMember(
        host_id=invite.host_id,
        user_id=user.id,
        role=invite.role,
        role_label=invite.role_label,
        status="active",
        permissions_json=invite.permissions_json,
        scope_json=scope_json,
        invited_by_user_id=invite.invited_by_user_id,
        invite_method=getattr(invite, "invite_method", None) or "email",
        invited_username=getattr(invite, "invited_username", None),
        joined_at=now,
    )
    db.add(member)

    invite.status = "accepted"
    invite.accepted_at = now
    invite.invited_user_id = user.id
    # Token hash remains for preview (“already accepted”); status blocks reuse.

    _grant_host_staff(db, user)
    db.flush()
    _sync_event_staff_for_scope(db, row=member, actor_user_id=user.id)
    _write_team_audit(
        db,
        host_id=invite.host_id,
        action="hosts.team_accept",
        actor_user_id=user.id,
        target_user_id=user.id,
        entity_type="host_team_member",
        entity_id=str(member.id),
        metadata={
            "invite_id": str(invite.id),
            "role": member.role,
        },
    )
    _write_team_audit(
        db,
        host_id=invite.host_id,
        action="hosts.team_member_added",
        actor_user_id=user.id,
        target_user_id=user.id,
        entity_type="host_team_member",
        entity_id=str(member.id),
        metadata={
            "invite_id": str(invite.id),
            "role": member.role,
            "role_label": member.role_label,
        },
    )
    _notify_host_invite_accepted(db, host=host, invite=invite, member_user=user)
    db.commit()
    db.refresh(member)
    return _serialize_member(db, member)


def decline_team_invite(db: Session, *, user: User, token: str) -> dict[str, Any]:
    row = _find_invite_by_token(db, token)
    row = _expire_invite_if_needed(db, row)
    if row.status != "pending":
        raise HTTPException(status_code=400, detail="Invite is no longer available")
    if (row.email or "").strip().lower() != (user.email or "").strip().lower():
        raise HTTPException(
            status_code=403,
            detail="Sign in with the invited email address to decline this invite",
        )
    row.status = "revoked"
    row.revoked_at = datetime.now(UTC)
    row.token_hash = ""
    _write_team_audit(
        db,
        host_id=row.host_id,
        action="hosts.team_decline",
        actor_user_id=user.id,
        target_user_id=user.id,
        entity_type="host_team_invite",
        entity_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    return serialize_invite(db, row)


def revoke_team_invite(
    db: Session,
    *,
    user: User,
    member_id: uuid.UUID,
    host_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Host revokes a pending invite (cannot be accepted afterward)."""
    host, _ = require_host_for_permission(
        db, user=user, host_id=host_id, permission="team.remove_members"
    )
    row = _require_invite(db, host_id=host.id, member_id=member_id)
    row = _expire_invite_if_needed(db, row)
    if row.status in {"revoked", "accepted"}:
        return serialize_invite(db, row)
    if row.status not in {"pending", "expired"}:
        raise HTTPException(status_code=400, detail="Invite cannot be revoked")
    row.status = "revoked"
    row.revoked_at = datetime.now(UTC)
    row.token_hash = ""
    _write_team_audit(
        db,
        host_id=host.id,
        action="hosts.team_revoke",
        actor_user_id=user.id,
        target_user_id=row.invited_user_id,
        entity_type="host_team_invite",
        entity_id=str(row.id),
        metadata={"invited_email": row.email},
    )
    team_notify.notify_invite_revoked(db, host=host, invite=row)
    db.commit()
    db.refresh(row)
    return serialize_invite(db, row)


def list_team_audit(
    db: Session,
    *,
    user: User,
    limit: int = 50,
    host_id: uuid.UUID | None = None,
) -> list[dict[str, Any]]:
    host, _ = require_host_for_permission(
        db, user=user, host_id=host_id, permission="team.view"
    )
    return list_host_audit_feed(db, host_id=host.id, limit=limit)
