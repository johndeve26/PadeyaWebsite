"""Seed default roles and permissions."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.users.constants import (
    DEFAULT_PERMISSIONS,
    DEFAULT_ROLES,
    ROLE_PERMISSIONS,
)
from app.users.models import Permission, Role


def seed_roles_and_permissions(db: Session) -> None:
    permissions_by_code: dict[str, Permission] = {}
    for code, description in DEFAULT_PERMISSIONS:
        permission = db.scalar(select(Permission).where(Permission.code == code))
        if permission is None:
            permission = Permission(code=code, description=description)
            db.add(permission)
            db.flush()
        elif permission.description != description:
            permission.description = description
        permissions_by_code[code] = permission

    for role_name, description in DEFAULT_ROLES.items():
        role = db.scalar(select(Role).where(Role.name == role_name))
        if role is None:
            role = Role(name=role_name, description=description)
            db.add(role)
            db.flush()

        desired_codes = ROLE_PERMISSIONS.get(role_name, [])
        desired = [permissions_by_code[code] for code in desired_codes]
        role.permissions = desired

    db.commit()
