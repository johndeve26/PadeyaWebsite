"""Admin team management APIs."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.admin_team.schemas import (
    AdminRoleCreate,
    AdminRoleUpdate,
    AdminTeamForceLogout,
    AdminTeamInviteCreate,
    AdminTeamMemberDisable,
    AdminTeamMemberUpdate,
)
from app.admin_team import service as team_service
from app.auth.dependencies import get_current_user, get_db, require_permission
from app.users.models import User

router = APIRouter(prefix="/admin/team", tags=["admin-team"])


def _client_meta(request: Request) -> tuple[str | None, str | None]:
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    return ip, ua


@router.get("")
def admin_list_team(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("admin.team.view", "admin.full_access"))
    ],
    status_filter: Annotated[str | None, Query(alias="status")] = None,
) -> dict[str, Any]:
    team_service.assert_admin_access_allowed(db, user)
    team_service.ensure_system_admin_roles(db)
    db.commit()
    return {
        "members": team_service.list_members(db, status=status_filter),
        "pending_invites": team_service.list_pending_invites(db),
    }


@router.post("/invite", status_code=status.HTTP_201_CREATED)
def admin_invite_team_member(
    payload: AdminTeamInviteCreate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("admin.team.invite", "admin.full_access"))
    ],
) -> dict[str, Any]:
    team_service.assert_admin_access_allowed(db, user)
    ip, ua = _client_meta(request)
    result = team_service.invite_member(
        db,
        actor=user,
        email=str(payload.email),
        admin_role_id=payload.admin_role_id,
        system_key=payload.system_key,
        ip_address=ip,
        user_agent=ua,
    )
    db.commit()
    return result


@router.get("/roles")
def admin_list_roles(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("admin.team.view", "admin.full_access"))
    ],
) -> dict[str, Any]:
    team_service.assert_admin_access_allowed(db, user)
    team_service.ensure_system_admin_roles(db)
    db.commit()
    return {
        "roles": team_service.list_roles(db),
        "permission_catalog": team_service.list_permission_catalog(),
    }


@router.post("/roles", status_code=status.HTTP_201_CREATED)
def admin_create_role(
    payload: AdminRoleCreate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User,
        Depends(require_permission("admin.team.manage_roles", "admin.full_access")),
    ],
) -> dict[str, Any]:
    team_service.assert_admin_access_allowed(db, user)
    ip, ua = _client_meta(request)
    result = team_service.create_custom_role(
        db,
        actor=user,
        name=payload.name,
        description=payload.description,
        permission_codes=payload.permission_codes,
        ip_address=ip,
        user_agent=ua,
    )
    db.commit()
    return result


@router.patch("/roles/{role_id}")
def admin_update_role(
    role_id: UUID,
    payload: AdminRoleUpdate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User,
        Depends(require_permission("admin.team.manage_roles", "admin.full_access")),
    ],
) -> dict[str, Any]:
    team_service.assert_admin_access_allowed(db, user)
    ip, ua = _client_meta(request)
    data = payload.model_dump(exclude_unset=True)
    result = team_service.update_custom_role(
        db,
        actor=user,
        role_id=role_id,
        name=data.get("name"),
        description=data.get("description"),
        permission_codes=data.get("permission_codes"),
        ip_address=ip,
        user_agent=ua,
    )
    db.commit()
    return result


@router.post("/roles/{role_id}/archive")
def admin_archive_role(
    role_id: UUID,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User,
        Depends(require_permission("admin.team.manage_roles", "admin.full_access")),
    ],
) -> dict[str, Any]:
    team_service.assert_admin_access_allowed(db, user)
    ip, ua = _client_meta(request)
    result = team_service.archive_custom_role(
        db,
        actor=user,
        role_id=role_id,
        ip_address=ip,
        user_agent=ua,
    )
    db.commit()
    return result


@router.get("/members/{member_id}")
def admin_get_member(
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("admin.team.view", "admin.full_access"))
    ],
) -> dict[str, Any]:
    from app.users.service import user_has_permission

    team_service.assert_admin_access_allowed(db, user)
    member = team_service.get_member(db, member_id)
    audit: list[dict[str, Any]] = []
    if user_has_permission(user, "admin.team.view_audit") or user_has_permission(
        user, "admin.full_access"
    ):
        audit = team_service.list_member_audit(db, member_id=member_id, limit=50)
    return {"member": member, "audit": audit}


@router.patch("/members/{member_id}")
def admin_update_member(
    member_id: UUID,
    payload: AdminTeamMemberUpdate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User,
        Depends(
            require_permission("admin.team.manage_members", "admin.full_access")
        ),
    ],
) -> dict[str, Any]:
    team_service.assert_admin_access_allowed(db, user)
    ip, ua = _client_meta(request)
    result = team_service.update_member(
        db,
        actor=user,
        member_id=member_id,
        admin_role_id=payload.admin_role_id,
        system_key=payload.system_key,
        permission_codes=payload.permission_codes,
        ip_address=ip,
        user_agent=ua,
    )
    db.commit()
    return result


@router.post("/members/{member_id}/disable")
def admin_disable_member(
    member_id: UUID,
    payload: AdminTeamMemberDisable,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User,
        Depends(
            require_permission("admin.team.manage_members", "admin.full_access")
        ),
    ],
) -> dict[str, Any]:
    team_service.assert_admin_access_allowed(db, user)
    ip, ua = _client_meta(request)
    result = team_service.disable_member(
        db,
        actor=user,
        member_id=member_id,
        reason=payload.reason,
        remove=payload.remove,
        ip_address=ip,
        user_agent=ua,
    )
    db.commit()
    return result


@router.post("/members/{member_id}/force-logout")
def admin_force_logout_member(
    member_id: UUID,
    payload: AdminTeamForceLogout,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User,
        Depends(
            require_permission(
                "admin.team.force_logout",
                "admin.users.force_logout",
                "admin.full_access",
            )
        ),
    ],
) -> dict[str, Any]:
    team_service.assert_admin_access_allowed(db, user)
    ip, ua = _client_meta(request)
    result = team_service.force_logout_member(
        db,
        actor=user,
        member_id=member_id,
        reason=payload.reason,
        ip_address=ip,
        user_agent=ua,
    )
    db.commit()
    return result
