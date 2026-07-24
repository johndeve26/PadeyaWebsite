"""Seed default roles and permissions."""

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.users.constants import (
    DEFAULT_PERMISSIONS,
    DEFAULT_ROLES,
    ROLE_PERMISSIONS,
)
from app.users.models import Permission, Role, RolePermission


def seed_roles_and_permissions(db: Session) -> None:
    permission_codes = [code for code, _ in DEFAULT_PERMISSIONS]
    existing_permissions = {
        row.code: row
        for row in db.scalars(
            select(Permission).where(Permission.code.in_(permission_codes))
        ).all()
    }

    for code, description in DEFAULT_PERMISSIONS:
        permission = existing_permissions.get(code)
        if permission is None:
            permission = Permission(code=code, description=description)
            db.add(permission)
            existing_permissions[code] = permission
        elif permission.description != description:
            permission.description = description

    if any(p.id is None for p in existing_permissions.values()):
        db.flush()

    role_names = list(DEFAULT_ROLES.keys())
    existing_roles = {
        row.name: row
        for row in db.scalars(
            select(Role)
            .where(Role.name.in_(role_names))
            .options(selectinload(Role.permissions))
        ).all()
    }

    for role_name, description in DEFAULT_ROLES.items():
        role = existing_roles.get(role_name)
        if role is None:
            role = Role(name=role_name, description=description)
            db.add(role)
            existing_roles[role_name] = role

    if any(r.id is None for r in existing_roles.values()):
        db.flush()

    role_ids = [role.id for role in existing_roles.values()]
    current_links: dict = {role_id: set() for role_id in role_ids}
    if role_ids:
        for role_id, permission_id in db.execute(
            select(RolePermission.role_id, RolePermission.permission_id).where(
                RolePermission.role_id.in_(role_ids)
            )
        ).all():
            current_links.setdefault(role_id, set()).add(permission_id)

    for role_name in DEFAULT_ROLES:
        role = existing_roles[role_name]
        desired_codes = ROLE_PERMISSIONS.get(role_name, [])
        desired_ids = {
            existing_permissions[code].id
            for code in desired_codes
            if code in existing_permissions
        }
        have_ids = current_links.get(role.id, set())
        to_remove = have_ids - desired_ids
        to_add = desired_ids - have_ids
        if to_remove:
            db.execute(
                delete(RolePermission).where(
                    RolePermission.role_id == role.id,
                    RolePermission.permission_id.in_(to_remove),
                )
            )
        for permission_id in to_add:
            db.add(RolePermission(role_id=role.id, permission_id=permission_id))

    db.commit()
