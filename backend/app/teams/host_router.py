"""Host-facing team management API: `/api/v1/host/team*`."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser
from app.core.database import get_db
from app.hosts import team_service
from app.hosts.lifecycle_schemas import (
    HostTeamAuditItem,
    HostTeamInviteCreateResponse,
    HostTeamInviteLookupResponse,
    HostTeamMemberInvite,
    HostTeamMemberPublic,
    HostTeamMemberUpdate,
)
from app.hosts.team_access import require_host_for_permission
from app.hosts.team_invite_resolve import preview_invite_identifier
from app.hosts.team_permissions import (
    OWNER_ONLY_PERMISSION_KEYS,
    PERMISSION_GROUPS,
    PERMISSION_KEYS,
    ROLE_DEFAULT_SCOPES,
    ROLE_LABELS,
    TEAM_ROLES,
    permissions_for_role,
)
from app.teams.deps import ResolvedHostId
from app.teams.schemas import (
    TeamPermissionGroupCatalog,
    TeamPermissionsCatalog,
    TeamRoleCatalogItem,
)

router = APIRouter(prefix="/host/team", tags=["host-team"])


@router.get("", response_model=list[HostTeamMemberPublic])
def list_host_team_members(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    resolved_host_id: ResolvedHostId,
    include_archived: bool = Query(default=False),
) -> list[HostTeamMemberPublic]:
    rows = team_service.list_team_members(
        db,
        user=user,
        include_archived=include_archived,
        host_id=resolved_host_id,
        include="members",
    )
    return [HostTeamMemberPublic.model_validate(r) for r in rows]


@router.get("/invites/lookup", response_model=HostTeamInviteLookupResponse)
def lookup_host_team_invitee(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    resolved_host_id: ResolvedHostId,
    identifier: str = Query(min_length=1, max_length=320),
) -> HostTeamInviteLookupResponse:
    """Privacy-safe preview while typing an email or Pàdéyá username."""
    require_host_for_permission(
        db, user=user, host_id=resolved_host_id, permission="team.invite"
    )
    return HostTeamInviteLookupResponse.model_validate(
        preview_invite_identifier(db, identifier)
    )


@router.post(
    "/invites",
    response_model=HostTeamInviteCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_host_team_invite(
    payload: HostTeamMemberInvite,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    resolved_host_id: ResolvedHostId,
) -> HostTeamInviteCreateResponse:
    row = team_service.invite_team_member(
        db, user=user, payload=payload, host_id=resolved_host_id
    )
    return HostTeamInviteCreateResponse.model_validate(
        team_service.serialize_invite_created(db, row)
    )


@router.get("/invites", response_model=list[HostTeamMemberPublic])
def list_host_team_invites(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    resolved_host_id: ResolvedHostId,
    include_archived: bool = Query(default=False),
) -> list[HostTeamMemberPublic]:
    rows = team_service.list_team_members(
        db,
        user=user,
        include_archived=include_archived,
        host_id=resolved_host_id,
        include="invites",
    )
    return [HostTeamMemberPublic.model_validate(r) for r in rows]


@router.post(
    "/invites/{invite_id}/revoke",
    response_model=HostTeamMemberPublic,
)
def revoke_host_team_invite(
    invite_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    resolved_host_id: ResolvedHostId,
) -> HostTeamMemberPublic:
    row = team_service.revoke_team_invite(
        db, user=user, member_id=invite_id, host_id=resolved_host_id
    )
    return HostTeamMemberPublic.model_validate(row)


@router.patch(
    "/members/{member_id}",
    response_model=HostTeamMemberPublic,
)
def patch_host_team_member(
    member_id: UUID,
    payload: HostTeamMemberUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    resolved_host_id: ResolvedHostId,
) -> HostTeamMemberPublic:
    row = team_service.update_team_member(
        db,
        user=user,
        member_id=member_id,
        payload=payload,
        host_id=resolved_host_id,
    )
    return HostTeamMemberPublic.model_validate(row)


@router.post(
    "/members/{member_id}/suspend",
    response_model=HostTeamMemberPublic,
)
def suspend_host_team_member(
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    resolved_host_id: ResolvedHostId,
) -> HostTeamMemberPublic:
    row = team_service.suspend_team_member(
        db, user=user, member_id=member_id, host_id=resolved_host_id
    )
    return HostTeamMemberPublic.model_validate(row)


@router.post(
    "/members/{member_id}/remove",
    response_model=HostTeamMemberPublic,
)
def remove_host_team_member(
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    resolved_host_id: ResolvedHostId,
) -> HostTeamMemberPublic:
    row = team_service.archive_team_member(
        db, user=user, member_id=member_id, host_id=resolved_host_id
    )
    return HostTeamMemberPublic.model_validate(row)


@router.get("/audit-log", response_model=list[HostTeamAuditItem])
def list_host_team_audit_log(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    resolved_host_id: ResolvedHostId,
    limit: int = Query(default=50, ge=1, le=100),
) -> list[HostTeamAuditItem]:
    rows = team_service.list_team_audit(
        db, user=user, limit=limit, host_id=resolved_host_id
    )
    return [HostTeamAuditItem.model_validate(r) for r in rows]


@router.get("/permissions", response_model=TeamPermissionsCatalog)
def list_host_team_permissions_catalog(
    _: CurrentUser,
) -> TeamPermissionsCatalog:
    return TeamPermissionsCatalog(
        groups=[
            TeamPermissionGroupCatalog(group=group, keys=list(keys))
            for group, keys in PERMISSION_GROUPS.items()
        ],
        keys=list(PERMISSION_KEYS),
        owner_only_keys=sorted(OWNER_ONLY_PERMISSION_KEYS),
    )


@router.get("/roles", response_model=list[TeamRoleCatalogItem])
def list_host_team_roles_catalog(
    _: CurrentUser,
) -> list[TeamRoleCatalogItem]:
    return [
        TeamRoleCatalogItem(
            role=role,
            label=ROLE_LABELS[role],
            default_scope=ROLE_DEFAULT_SCOPES[role],
            default_permissions=permissions_for_role(role),
        )
        for role in TEAM_ROLES
    ]
