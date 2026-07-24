"""Admin team management service — invites, roles, members, audit."""

from __future__ import annotations

import hashlib
import re
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.admin_team.models import (
    AdminAuditLog,
    AdminInvite,
    AdminRole,
    AdminRolePermission,
    AdminTeamMember,
)
from app.core.audit import write_audit_log
from app.users.admin_actions_service import revoke_all_sessions
from app.users.constants import (
    ADMIN_TEAM_HIGH_LEVEL_PERMISSIONS,
    ADMIN_TEAM_HIGH_LEVEL_SYSTEM_KEYS,
    ADMIN_TEAM_PERMISSION_GROUPS,
    ADMIN_TEAM_SYSTEM_ROLE_LINKS,
    ADMIN_TEAM_SYSTEM_ROLE_META,
    DEFAULT_PERMISSIONS,
    ROLE_PERMISSIONS,
)
from app.users.models import Permission, Role, User
from app.users.service import (
    get_role_by_name,
    get_user_by_email,
    get_user_by_id,
    user_has_permission,
    user_permission_codes,
    user_role_names,
)

INVITE_TTL_DAYS = 7
MEMBER_STATUS_ACTIVE = "active"
MEMBER_STATUS_DISABLED = "disabled"
MEMBER_STATUS_REMOVED = "removed"

ACTION_INVITE = "admin_team.invite"
ACTION_ROLE_CREATE = "admin_team.role_create"
ACTION_ROLE_UPDATE = "admin_team.role_update"
ACTION_MEMBER_UPDATE = "admin_team.member_update"
ACTION_MEMBER_DISABLE = "admin_team.member_disable"
ACTION_MEMBER_REMOVE = "admin_team.member_remove"
ACTION_FORCE_LOGOUT = "admin_team.force_logout"
ACTION_LOGIN = "admin_team.login"


def _now() -> datetime:
    return datetime.now(UTC)


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


def _is_super(user: User) -> bool:
    return user_has_permission(user, "admin.full_access") or "super_admin" in set(
        user_role_names(user)
    )


def _permission_catalog() -> dict[str, str]:
    return {code: desc for code, desc in DEFAULT_PERMISSIONS}


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")
    return slug[:48] or "custom"


def write_admin_team_audit(
    db: Session,
    *,
    action: str,
    actor_user_id: uuid.UUID | None,
    target_user_id: uuid.UUID | None = None,
    target_member_id: uuid.UUID | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AdminAuditLog:
    safe = dict(details or {})
    for key in list(safe.keys()):
        lowered = key.lower()
        if any(
            s in lowered
            for s in ("password", "hash", "token", "secret", "credential")
        ):
            safe.pop(key, None)
    row = AdminAuditLog(
        action=action,
        actor_user_id=actor_user_id,
        target_user_id=target_user_id,
        target_member_id=target_member_id,
        entity_type=entity_type,
        entity_id=entity_id,
        details=safe or None,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(row)
    write_audit_log(
        db,
        action=action,
        actor_user_id=actor_user_id,
        resource_type=entity_type or "admin_team",
        resource_id=entity_id,
        details=safe or None,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return row


def ensure_system_admin_roles(db: Session) -> None:
    """Seed preset admin_roles linked to RBAC Role rows."""
    for system_key, role_name in ADMIN_TEAM_SYSTEM_ROLE_LINKS.items():
        existing = db.scalar(
            select(AdminRole).where(AdminRole.system_key == system_key)
        )
        linked = get_role_by_name(db, role_name)
        label, description = ADMIN_TEAM_SYSTEM_ROLE_META[system_key]
        is_high = system_key in ADMIN_TEAM_HIGH_LEVEL_SYSTEM_KEYS
        if existing is None:
            row = AdminRole(
                name=label,
                description=description,
                system_key=system_key,
                is_system=True,
                is_high_level=is_high,
                linked_role_id=linked.id if linked else None,
            )
            db.add(row)
            db.flush()
            codes = ROLE_PERMISSIONS.get(role_name, [])
            if role_name == "super_admin":
                codes = ["admin.full_access"]
            for code in codes:
                db.add(
                    AdminRolePermission(admin_role_id=row.id, permission_code=code)
                )
        else:
            existing.name = label
            existing.description = description
            existing.is_system = True
            existing.is_high_level = is_high
            if linked is not None:
                existing.linked_role_id = linked.id


def get_active_team_member(db: Session, user_id: uuid.UUID) -> AdminTeamMember | None:
    return db.scalar(
        select(AdminTeamMember)
        .where(
            AdminTeamMember.user_id == user_id,
            AdminTeamMember.status == MEMBER_STATUS_ACTIVE,
        )
        .options(selectinload(AdminTeamMember.admin_role))
    )


def assert_admin_access_allowed(db: Session, user: User) -> None:
    """Block disabled/removed team members even if stale roles remain."""
    member = db.scalar(
        select(AdminTeamMember).where(AdminTeamMember.user_id == user.id)
    )
    if member is None:
        return
    if member.status in {MEMBER_STATUS_DISABLED, MEMBER_STATUS_REMOVED}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin team access is disabled",
        )


def record_admin_login_if_applicable(
    db: Session,
    *,
    user: User,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    member = get_active_team_member(db, user.id)
    roles = set(user_role_names(user))
    platform = roles & {
        "super_admin",
        "admin",
        "support_agent",
        "finance_admin",
        "moderation",
        "operations",
        "marketing",
    }
    if member is None and not platform:
        return
    write_admin_team_audit(
        db,
        action=ACTION_LOGIN,
        actor_user_id=user.id,
        target_user_id=user.id,
        target_member_id=member.id if member else None,
        entity_type="admin_team_member",
        entity_id=str(member.id) if member else str(user.id),
        details={"roles": sorted(roles)},
        ip_address=ip_address,
        user_agent=user_agent,
    )


def _serialize_role(role: AdminRole) -> dict[str, Any]:
    codes = sorted({p.permission_code for p in role.permissions})
    return {
        "id": str(role.id),
        "name": role.name,
        "description": role.description,
        "system_key": role.system_key,
        "is_system": role.is_system,
        "is_high_level": role.is_high_level,
        "linked_role_id": str(role.linked_role_id) if role.linked_role_id else None,
        "permission_codes": codes,
        "archived_at": role.archived_at.isoformat() if role.archived_at else None,
        "created_at": role.created_at.isoformat() if role.created_at else None,
    }


def _serialize_user_safe(user: User | None) -> dict[str, Any] | None:
    if user is None:
        return None
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
    }


def _serialize_member(db: Session, member: AdminTeamMember) -> dict[str, Any]:
    user = get_user_by_id(db, member.user_id)
    role = member.admin_role
    return {
        "id": str(member.id),
        "user_id": str(member.user_id),
        "status": member.status,
        "user": _serialize_user_safe(user),
        "role": _serialize_role(role) if role else None,
        "invited_by_user_id": (
            str(member.invited_by_user_id) if member.invited_by_user_id else None
        ),
        "disabled_at": member.disabled_at.isoformat() if member.disabled_at else None,
        "removed_at": member.removed_at.isoformat() if member.removed_at else None,
        "created_at": member.created_at.isoformat() if member.created_at else None,
        "updated_at": member.updated_at.isoformat() if member.updated_at else None,
        "permissions": (
            sorted(user_permission_codes(user)) if user is not None else []
        ),
    }


def list_permission_catalog() -> list[dict[str, Any]]:
    catalog = _permission_catalog()
    groups: list[dict[str, Any]] = []
    for label, codes in ADMIN_TEAM_PERMISSION_GROUPS:
        groups.append(
            {
                "group": label,
                "permissions": [
                    {
                        "code": code,
                        "description": catalog.get(code, code),
                        "high_level": code in ADMIN_TEAM_HIGH_LEVEL_PERMISSIONS,
                    }
                    for code in codes
                    if code in catalog or True
                ],
            }
        )
    return groups


def list_roles(db: Session, *, include_archived: bool = False) -> list[dict[str, Any]]:
    ensure_system_admin_roles(db)
    q = select(AdminRole).options(selectinload(AdminRole.permissions))
    if not include_archived:
        q = q.where(AdminRole.archived_at.is_(None))
    rows = list(db.scalars(q.order_by(AdminRole.is_system.desc(), AdminRole.name)))
    return [_serialize_role(r) for r in rows]


def get_role_or_404(db: Session, role_id: uuid.UUID) -> AdminRole:
    role = db.scalar(
        select(AdminRole)
        .where(AdminRole.id == role_id)
        .options(selectinload(AdminRole.permissions))
    )
    if role is None or role.archived_at is not None:
        raise HTTPException(status_code=404, detail="Admin role not found")
    return role


def _resolve_role(
    db: Session,
    *,
    admin_role_id: uuid.UUID | None,
    system_key: str | None,
) -> AdminRole:
    ensure_system_admin_roles(db)
    if admin_role_id is not None:
        return get_role_or_404(db, admin_role_id)
    key = (system_key or "").strip().lower()
    if not key:
        raise HTTPException(
            status_code=400, detail="admin_role_id or system_key is required"
        )
    role = db.scalar(
        select(AdminRole)
        .where(AdminRole.system_key == key, AdminRole.archived_at.is_(None))
        .options(selectinload(AdminRole.permissions))
    )
    if role is None:
        raise HTTPException(status_code=404, detail="Admin role not found")
    return role


def _assert_can_assign_role(actor: User, role: AdminRole) -> None:
    if role.is_high_level or (
        role.system_key and role.system_key in ADMIN_TEAM_HIGH_LEVEL_SYSTEM_KEYS
    ):
        if not _is_super(actor):
            raise HTTPException(
                status_code=403,
                detail="Only super_admin can assign high-level admin roles",
            )


def _assert_can_edit_role(actor: User, role: AdminRole) -> None:
    if role.is_system:
        raise HTTPException(
            status_code=403, detail="System roles cannot be edited"
        )
    if role.is_high_level and not _is_super(actor):
        raise HTTPException(
            status_code=403,
            detail="Only super_admin can edit high-level admin roles",
        )


def _assert_permission_codes_allowed(actor: User, codes: list[str]) -> list[str]:
    catalog = _permission_catalog()
    cleaned: list[str] = []
    seen: set[str] = set()
    for raw in codes:
        code = (raw or "").strip()
        if not code or code in seen:
            continue
        if code not in catalog:
            raise HTTPException(
                status_code=400, detail=f"Unknown permission: {code}"
            )
        if code in ADMIN_TEAM_HIGH_LEVEL_PERMISSIONS and not _is_super(actor):
            raise HTTPException(
                status_code=403,
                detail=f"Only super_admin can grant {code}",
            )
        seen.add(code)
        cleaned.append(code)
    return cleaned


def _sync_linked_custom_role(
    db: Session,
    *,
    admin_role: AdminRole,
    permission_codes: list[str],
) -> Role:
    """Create/update the underlying RBAC Role for a custom admin role."""
    role_name = f"admin_custom_{_slugify(admin_role.name)}_{str(admin_role.id)[:8]}"
    linked: Role | None = None
    if admin_role.linked_role_id:
        linked = db.scalar(select(Role).where(Role.id == admin_role.linked_role_id))
    if linked is None:
        linked = db.scalar(select(Role).where(Role.name == role_name))
    if linked is None:
        linked = Role(
            name=role_name,
            description=admin_role.description or admin_role.name,
        )
        db.add(linked)
        db.flush()
        admin_role.linked_role_id = linked.id
    else:
        admin_role.linked_role_id = linked.id
        linked.description = admin_role.description or admin_role.name

    perms = list(
        db.scalars(select(Permission).where(Permission.code.in_(permission_codes)))
    )
    by_code = {p.code: p for p in perms}
    missing = [c for c in permission_codes if c not in by_code]
    if missing:
        raise HTTPException(
            status_code=400, detail=f"Permissions not seeded: {', '.join(missing)}"
        )
    linked.permissions = [by_code[c] for c in permission_codes]
    return linked


def _replace_admin_role_permissions(
    db: Session, admin_role: AdminRole, codes: list[str]
) -> None:
    admin_role.permissions.clear()
    db.flush()
    for code in codes:
        db.add(
            AdminRolePermission(admin_role_id=admin_role.id, permission_code=code)
        )
    db.flush()


def _assign_linked_role(db: Session, user: User, admin_role: AdminRole) -> None:
    if admin_role.linked_role_id is None:
        return
    linked = db.scalar(select(Role).where(Role.id == admin_role.linked_role_id))
    if linked is None:
        return
    # Drop other platform/custom admin roles first (keep buyer/host).
    keep_names = {"buyer", "host", "host_staff"}
    platform = set(ADMIN_TEAM_SYSTEM_ROLE_LINKS.values())
    remaining: list[Role] = []
    for role in list(user.roles):
        if role.name in keep_names:
            remaining.append(role)
            continue
        if role.name in platform or role.name.startswith("admin_custom_"):
            continue
        if role.name == "admin_staff":
            continue
        remaining.append(role)
    if linked not in remaining:
        remaining.append(linked)
    staff = get_role_by_name(db, "admin_staff")
    if staff is not None and staff not in remaining:
        remaining.append(staff)
    user.roles = remaining


def _strip_admin_roles(db: Session, user: User) -> None:
    keep_names = {"buyer", "host", "host_staff"}
    platform = set(ADMIN_TEAM_SYSTEM_ROLE_LINKS.values())
    user.roles = [
        r
        for r in list(user.roles)
        if r.name in keep_names
        or (
            r.name not in platform
            and r.name != "admin_staff"
            and not r.name.startswith("admin_custom_")
        )
    ]


def create_custom_role(
    db: Session,
    *,
    actor: User,
    name: str,
    description: str | None,
    permission_codes: list[str],
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    if not user_has_permission(actor, "admin.team.manage_roles"):
        raise HTTPException(status_code=403, detail="Insufficient permission")
    codes = _assert_permission_codes_allowed(actor, permission_codes)
    cleaned_name = name.strip()
    if len(cleaned_name) < 2:
        raise HTTPException(status_code=400, detail="Role name is required")
    row = AdminRole(
        name=cleaned_name,
        description=(description or "").strip() or None,
        system_key=None,
        is_system=False,
        is_high_level=False,
        created_by_user_id=actor.id,
    )
    db.add(row)
    db.flush()
    _replace_admin_role_permissions(db, row, codes)
    _sync_linked_custom_role(db, admin_role=row, permission_codes=codes)
    db.refresh(row)
    write_admin_team_audit(
        db,
        action=ACTION_ROLE_CREATE,
        actor_user_id=actor.id,
        entity_type="admin_role",
        entity_id=str(row.id),
        details={
            "name": row.name,
            "permission_codes": codes,
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return _serialize_role(row)


def update_custom_role(
    db: Session,
    *,
    actor: User,
    role_id: uuid.UUID,
    name: str | None = None,
    description: str | None = None,
    permission_codes: list[str] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    if not user_has_permission(actor, "admin.team.manage_roles"):
        raise HTTPException(status_code=403, detail="Insufficient permission")
    role = get_role_or_404(db, role_id)
    _assert_can_edit_role(actor, role)
    before = _serialize_role(role)
    if name is not None:
        role.name = name.strip()
    if description is not None:
        role.description = description.strip() or None
    codes = (
        _assert_permission_codes_allowed(actor, permission_codes)
        if permission_codes is not None
        else [p.permission_code for p in role.permissions]
    )
    if permission_codes is not None:
        _replace_admin_role_permissions(db, role, codes)
    _sync_linked_custom_role(db, admin_role=role, permission_codes=codes)
    # Re-sync active members on this role
    members = list(
        db.scalars(
            select(AdminTeamMember).where(
                AdminTeamMember.admin_role_id == role.id,
                AdminTeamMember.status == MEMBER_STATUS_ACTIVE,
            )
        )
    )
    for member in members:
        user = get_user_by_id(db, member.user_id)
        if user is not None:
            _assign_linked_role(db, user, role)
    db.refresh(role)
    write_admin_team_audit(
        db,
        action=ACTION_ROLE_UPDATE,
        actor_user_id=actor.id,
        entity_type="admin_role",
        entity_id=str(role.id),
        details={"before": before, "after": _serialize_role(role)},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return _serialize_role(role)


def list_members(
    db: Session, *, status: str | None = None
) -> list[dict[str, Any]]:
    ensure_system_admin_roles(db)
    q = select(AdminTeamMember).options(selectinload(AdminTeamMember.admin_role))
    if status:
        q = q.where(AdminTeamMember.status == status)
    else:
        q = q.where(AdminTeamMember.status != MEMBER_STATUS_REMOVED)
    rows = list(db.scalars(q.order_by(AdminTeamMember.created_at.desc())))
    return [_serialize_member(db, m) for m in rows]


def get_member(db: Session, member_id: uuid.UUID) -> dict[str, Any]:
    member = db.scalar(
        select(AdminTeamMember)
        .where(AdminTeamMember.id == member_id)
        .options(selectinload(AdminTeamMember.admin_role))
    )
    if member is None:
        raise HTTPException(status_code=404, detail="Team member not found")
    return _serialize_member(db, member)


def _assert_can_modify_member(actor: User, target: User, member: AdminTeamMember) -> None:
    target_roles = set(user_role_names(target))
    if "super_admin" in target_roles and not _is_super(actor):
        raise HTTPException(
            status_code=403,
            detail="Normal admin cannot modify a super_admin",
        )
    role = member.admin_role
    if role and role.is_high_level and not _is_super(actor):
        raise HTTPException(
            status_code=403,
            detail="Only super_admin can modify high-level team members",
        )


def invite_member(
    db: Session,
    *,
    actor: User,
    email: str,
    admin_role_id: uuid.UUID | None = None,
    system_key: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    if not user_has_permission(actor, "admin.team.invite"):
        raise HTTPException(status_code=403, detail="Insufficient permission")
    role = _resolve_role(db, admin_role_id=admin_role_id, system_key=system_key)
    _assert_can_assign_role(actor, role)

    normalized = email.lower().strip()
    existing_user = get_user_by_email(db, normalized)
    if existing_user is not None:
        existing_member = db.scalar(
            select(AdminTeamMember).where(
                AdminTeamMember.user_id == existing_user.id
            )
        )
        if (
            existing_member is not None
            and existing_member.status == MEMBER_STATUS_ACTIVE
        ):
            raise HTTPException(
                status_code=409, detail="User is already an active team member"
            )
        member = _activate_or_create_member(
            db,
            user=existing_user,
            admin_role=role,
            invited_by=actor.id,
            existing=existing_member,
        )
        write_admin_team_audit(
            db,
            action=ACTION_INVITE,
            actor_user_id=actor.id,
            target_user_id=existing_user.id,
            target_member_id=member.id,
            entity_type="admin_team_member",
            entity_id=str(member.id),
            details={
                "email_hint": _email_hint(normalized),
                "role_id": str(role.id),
                "role_name": role.name,
                "system_key": role.system_key,
                "provisioned": True,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return {
            "invite_id": None,
            "status": "provisioned",
            "email_hint": _email_hint(normalized),
            "member": _serialize_member(db, member),
            "expires_at": None,
        }

    # Pending invite for unknown email
    pending = db.scalar(
        select(AdminInvite).where(
            AdminInvite.email == normalized,
            AdminInvite.status == "pending",
        )
    )
    raw, token_hash = _new_invite_token()
    expires = _now() + timedelta(days=INVITE_TTL_DAYS)
    if pending is not None:
        pending.admin_role_id = role.id
        pending.token_hash = token_hash
        pending.expires_at = expires
        pending.invited_by_user_id = actor.id
        invite = pending
    else:
        invite = AdminInvite(
            email=normalized,
            admin_role_id=role.id,
            token_hash=token_hash,
            status="pending",
            invited_by_user_id=actor.id,
            expires_at=expires,
        )
        db.add(invite)
        db.flush()

    write_admin_team_audit(
        db,
        action=ACTION_INVITE,
        actor_user_id=actor.id,
        entity_type="admin_invite",
        entity_id=str(invite.id),
        details={
            "email_hint": _email_hint(normalized),
            "role_id": str(role.id),
            "role_name": role.name,
            "system_key": role.system_key,
            "provisioned": False,
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )
    # Token returned once for ops/testing — never stored in audit.
    return {
        "invite_id": str(invite.id),
        "status": "pending",
        "email_hint": _email_hint(normalized),
        "member": None,
        "expires_at": invite.expires_at.isoformat(),
        "invite_token": raw,
    }


def _activate_or_create_member(
    db: Session,
    *,
    user: User,
    admin_role: AdminRole,
    invited_by: uuid.UUID | None,
    existing: AdminTeamMember | None,
) -> AdminTeamMember:
    if existing is None:
        member = AdminTeamMember(
            user_id=user.id,
            admin_role_id=admin_role.id,
            status=MEMBER_STATUS_ACTIVE,
            invited_by_user_id=invited_by,
        )
        db.add(member)
        db.flush()
    else:
        member = existing
        member.admin_role_id = admin_role.id
        member.status = MEMBER_STATUS_ACTIVE
        member.disabled_at = None
        member.disabled_by_user_id = None
        member.removed_at = None
        member.removed_by_user_id = None
        member.invited_by_user_id = invited_by or member.invited_by_user_id
        db.flush()
        db.refresh(member, attribute_names=["admin_role"])
    _assign_linked_role(db, user, admin_role)
    return member


def update_member(
    db: Session,
    *,
    actor: User,
    member_id: uuid.UUID,
    admin_role_id: uuid.UUID | None = None,
    system_key: str | None = None,
    permission_codes: list[str] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    if not user_has_permission(actor, "admin.team.manage_members"):
        raise HTTPException(status_code=403, detail="Insufficient permission")
    member = db.scalar(
        select(AdminTeamMember)
        .where(AdminTeamMember.id == member_id)
        .options(selectinload(AdminTeamMember.admin_role))
    )
    if member is None:
        raise HTTPException(status_code=404, detail="Team member not found")
    target = get_user_by_id(db, member.user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    _assert_can_modify_member(actor, target, member)
    before = _serialize_member(db, member)

    if admin_role_id is not None or system_key is not None:
        role = _resolve_role(
            db, admin_role_id=admin_role_id, system_key=system_key
        )
        _assert_can_assign_role(actor, role)
        member.admin_role_id = role.id
        db.flush()
        db.refresh(member, attribute_names=["admin_role"])
        _assign_linked_role(db, target, role)

    if permission_codes is not None:
        role = member.admin_role
        if role is None or role.is_system:
            raise HTTPException(
                status_code=400,
                detail="Permission overrides require a custom role; assign a custom role first",
            )
        _assert_can_edit_role(actor, role)
        codes = _assert_permission_codes_allowed(actor, permission_codes)
        _replace_admin_role_permissions(db, role, codes)
        _sync_linked_custom_role(db, admin_role=role, permission_codes=codes)
        _assign_linked_role(db, target, role)

    if member.status != MEMBER_STATUS_ACTIVE:
        member.status = MEMBER_STATUS_ACTIVE
        member.disabled_at = None
        member.disabled_by_user_id = None

    write_admin_team_audit(
        db,
        action=ACTION_MEMBER_UPDATE,
        actor_user_id=actor.id,
        target_user_id=target.id,
        target_member_id=member.id,
        entity_type="admin_team_member",
        entity_id=str(member.id),
        details={"before": before, "after": _serialize_member(db, member)},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return _serialize_member(db, member)


def disable_member(
    db: Session,
    *,
    actor: User,
    member_id: uuid.UUID,
    reason: str | None = None,
    remove: bool = False,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    if not user_has_permission(actor, "admin.team.manage_members"):
        raise HTTPException(status_code=403, detail="Insufficient permission")
    member = db.scalar(
        select(AdminTeamMember)
        .where(AdminTeamMember.id == member_id)
        .options(selectinload(AdminTeamMember.admin_role))
    )
    if member is None:
        raise HTTPException(status_code=404, detail="Team member not found")
    target = get_user_by_id(db, member.user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    _assert_can_modify_member(actor, target, member)
    if target.id == actor.id:
        raise HTTPException(
            status_code=400, detail="Cannot disable your own admin access"
        )

    now = _now()
    if remove:
        member.status = MEMBER_STATUS_REMOVED
        member.removed_at = now
        member.removed_by_user_id = actor.id
        action = ACTION_MEMBER_REMOVE
    else:
        member.status = MEMBER_STATUS_DISABLED
        member.disabled_at = now
        member.disabled_by_user_id = actor.id
        action = ACTION_MEMBER_DISABLE

    _strip_admin_roles(db, target)
    revoke_all_sessions(
        db,
        admin=actor,
        user_id=target.id,
        reason=reason or ("removed" if remove else "disabled"),
        commit=False,
        skip_permission_check=True,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    write_admin_team_audit(
        db,
        action=action,
        actor_user_id=actor.id,
        target_user_id=target.id,
        target_member_id=member.id,
        entity_type="admin_team_member",
        entity_id=str(member.id),
        details={"reason": (reason or "").strip() or None, "remove": remove},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return _serialize_member(db, member)


def force_logout_member(
    db: Session,
    *,
    actor: User,
    member_id: uuid.UUID,
    reason: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    if not (
        user_has_permission(actor, "admin.team.force_logout")
        or user_has_permission(actor, "admin.users.force_logout")
    ):
        raise HTTPException(status_code=403, detail="Insufficient permission")
    member = db.scalar(
        select(AdminTeamMember).where(AdminTeamMember.id == member_id)
    )
    if member is None:
        raise HTTPException(status_code=404, detail="Team member not found")
    target = get_user_by_id(db, member.user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    _assert_can_modify_member(actor, target, member)
    result = revoke_all_sessions(
        db,
        admin=actor,
        user_id=target.id,
        reason=reason,
        commit=False,
        skip_permission_check=True,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    write_admin_team_audit(
        db,
        action=ACTION_FORCE_LOGOUT,
        actor_user_id=actor.id,
        target_user_id=target.id,
        target_member_id=member.id,
        entity_type="admin_team_member",
        entity_id=str(member.id),
        details={
            "reason": (reason or "").strip() or None,
            "revoked_count": result.get("revoked_count"),
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return result


def list_member_audit(
    db: Session,
    *,
    member_id: uuid.UUID | None = None,
    target_user_id: uuid.UUID | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    q = select(AdminAuditLog).order_by(AdminAuditLog.created_at.desc()).limit(
        min(max(limit, 1), 200)
    )
    if member_id is not None:
        q = q.where(AdminAuditLog.target_member_id == member_id)
    if target_user_id is not None:
        q = q.where(AdminAuditLog.target_user_id == target_user_id)
    rows = list(db.scalars(q))
    out: list[dict[str, Any]] = []
    for row in rows:
        out.append(
            {
                "id": str(row.id),
                "action": row.action,
                "actor_user_id": str(row.actor_user_id) if row.actor_user_id else None,
                "target_user_id": (
                    str(row.target_user_id) if row.target_user_id else None
                ),
                "target_member_id": (
                    str(row.target_member_id) if row.target_member_id else None
                ),
                "entity_type": row.entity_type,
                "entity_id": row.entity_id,
                "details": row.details,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
        )
    return out


def list_pending_invites(db: Session) -> list[dict[str, Any]]:
    rows = list(
        db.scalars(
            select(AdminInvite)
            .where(AdminInvite.status == "pending")
            .options(selectinload(AdminInvite.admin_role))
            .order_by(AdminInvite.created_at.desc())
        )
    )
    return [
        {
            "id": str(r.id),
            "email_hint": _email_hint(r.email),
            "status": r.status,
            "role": _serialize_role(r.admin_role) if r.admin_role else None,
            "expires_at": r.expires_at.isoformat() if r.expires_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
