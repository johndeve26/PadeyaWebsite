"""Host API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, require_permission
from app.core.database import get_db
from app.hosts import bank_service, team_service, verification_service, workspace_service
from app.hosts.lifecycle_schemas import (
    HostBankAccountCreate,
    HostBankAccountPublic,
    HostBankAccountUpdate,
    HostDeskEventPublic,
    HostTeamAuditItem,
    HostTeamInvitePreview,
    HostTeamMemberCreate,
    HostTeamMemberInvite,
    HostTeamMemberPublic,
    HostTeamMemberUpdate,
    HostTeamPermissionsUpdate,
    HostVerificationPublic,
    HostVerificationReject,
    HostWorkspacePublic,
)
from app.hosts.schemas import (
    HostOnboardRequest,
    HostProfileUpdate,
    HostPublic,
    HostTaxonomyPublic,
)
from app.hosts.service import get_host_by_user_id, onboard_host, update_host_profile
from app.hosts.recommendations.router import router as host_recommendations_router
from app.users.models import User

router = APIRouter(prefix="/hosts", tags=["hosts"])
router.include_router(host_recommendations_router)


def _client_meta(request: Request) -> tuple[str | None, str | None]:
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    return ip, ua


def _serialize_host(db: Session, host) -> HostPublic:
    from app.taxonomy import service as taxonomy_service

    public = HostPublic.model_validate(host)
    tax = taxonomy_service.get_host_taxonomy(db, host.id)
    niche = None
    if host.profile and host.profile.social_links:
        raw = host.profile.social_links.get("niche_positioning")
        niche = raw if isinstance(raw, str) else None
    public.taxonomy = HostTaxonomyPublic(
        host_type_slugs=tax.get("host_type_slugs") or [],
        category_slugs=tax.get("category_slugs") or [],
        audience_slugs=tax.get("audience_slugs") or [],
        primary_city_slug=tax.get("primary_city_slug"),
        service_area_slugs=tax.get("service_area_slugs") or [],
        niche_positioning=niche,
    )
    return public


@router.get("/health")
async def hosts_module_health() -> dict[str, str]:
    return {"module": "hosts", "status": "ok"}


@router.post("/onboard", response_model=HostPublic, status_code=status.HTTP_201_CREATED)
def onboard(
    payload: HostOnboardRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> HostPublic:
    """Any authenticated user can become a host; service assigns the host role."""
    ip, ua = _client_meta(request)
    host = onboard_host(
        db,
        user=user,
        payload=payload,
        ip_address=ip,
        user_agent=ua,
    )
    return _serialize_host(db, host)


@router.get("/me", response_model=HostPublic)
def read_my_host(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> HostPublic:
    host = get_host_by_user_id(db, user.id)
    if host is None:
        raise HTTPException(status_code=404, detail="Host profile not found")
    return _serialize_host(db, host)


@router.patch("/me", response_model=HostPublic)
def patch_my_host(
    payload: HostProfileUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> HostPublic:
    host = update_host_profile(db, user=user, payload=payload)
    return _serialize_host(db, host)


# --- Workspaces (owner + team + event staff) ---


@router.get("/workspaces", response_model=list[HostWorkspacePublic])
def list_my_workspaces(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[HostWorkspacePublic]:
    rows = workspace_service.list_user_workspaces(db, user=user)
    return [HostWorkspacePublic.model_validate(r) for r in rows]


@router.get(
    "/workspaces/{host_id}/desk-events",
    response_model=list[HostDeskEventPublic],
)
def list_workspace_desk_events(
    host_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[HostDeskEventPublic]:
    workspaces = workspace_service.list_user_workspaces(db, user=user)
    if not any(w["host_id"] == host_id for w in workspaces):
        raise HTTPException(status_code=404, detail="Workspace not found")
    rows = workspace_service.list_desk_events_for_workspace(
        db, user=user, host_id=host_id
    )
    return [HostDeskEventPublic.model_validate(r) for r in rows]


# --- Team members (owner or manage_team; /me = owned host) ---


@router.get("/me/team", response_model=list[HostTeamMemberPublic])
def list_my_team(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    include_archived: bool = Query(default=False),
) -> list[HostTeamMemberPublic]:
    rows = team_service.list_team_members(
        db, user=user, include_archived=include_archived, host_id=None
    )
    return [HostTeamMemberPublic.model_validate(r) for r in rows]


@router.get("/{host_id}/team", response_model=list[HostTeamMemberPublic])
def list_host_team(
    host_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    include_archived: bool = Query(default=False),
) -> list[HostTeamMemberPublic]:
    rows = team_service.list_team_members(
        db, user=user, include_archived=include_archived, host_id=host_id
    )
    return [HostTeamMemberPublic.model_validate(r) for r in rows]


@router.get("/me/team/audit", response_model=list[HostTeamAuditItem])
def list_my_team_audit(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    limit: int = Query(default=50, ge=1, le=100),
) -> list[HostTeamAuditItem]:
    rows = team_service.list_team_audit(db, user=user, limit=limit, host_id=None)
    return [HostTeamAuditItem.model_validate(r) for r in rows]


@router.get("/{host_id}/team/audit", response_model=list[HostTeamAuditItem])
def list_host_team_audit(
    host_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    limit: int = Query(default=50, ge=1, le=100),
) -> list[HostTeamAuditItem]:
    rows = team_service.list_team_audit(
        db, user=user, limit=limit, host_id=host_id
    )
    return [HostTeamAuditItem.model_validate(r) for r in rows]


@router.post(
    "/me/team/invite",
    response_model=HostTeamMemberPublic,
    status_code=status.HTTP_201_CREATED,
)
def invite_my_team_member(
    payload: HostTeamMemberInvite,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> HostTeamMemberPublic:
    row = team_service.invite_team_member(
        db, user=user, payload=payload, host_id=None
    )
    return HostTeamMemberPublic.model_validate(
        team_service.serialize_invite(db, row)
    )


@router.post(
    "/{host_id}/team/invite",
    response_model=HostTeamMemberPublic,
    status_code=status.HTTP_201_CREATED,
)
def invite_host_team_member(
    host_id: UUID,
    payload: HostTeamMemberInvite,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> HostTeamMemberPublic:
    row = team_service.invite_team_member(
        db, user=user, payload=payload, host_id=host_id
    )
    return HostTeamMemberPublic.model_validate(
        team_service.serialize_invite(db, row)
    )


@router.post(
    "/me/team",
    response_model=HostTeamMemberPublic,
    status_code=status.HTTP_201_CREATED,
)
def create_my_team_member(
    payload: HostTeamMemberCreate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> HostTeamMemberPublic:
    """Legacy create — invites by email (pending until accepted)."""
    row = team_service.create_team_member(
        db, user=user, payload=payload, host_id=None
    )
    return HostTeamMemberPublic.model_validate(row)


@router.get("/me/team/{member_id}", response_model=HostTeamMemberPublic)
def get_my_team_member(
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> HostTeamMemberPublic:
    row = team_service.get_team_member_public(
        db, user=user, member_id=member_id, host_id=None
    )
    return HostTeamMemberPublic.model_validate(row)


@router.get("/{host_id}/team/{member_id}", response_model=HostTeamMemberPublic)
def get_host_team_member(
    host_id: UUID,
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> HostTeamMemberPublic:
    row = team_service.get_team_member_public(
        db, user=user, member_id=member_id, host_id=host_id
    )
    return HostTeamMemberPublic.model_validate(row)


@router.patch("/me/team/{member_id}", response_model=HostTeamMemberPublic)
def update_my_team_member(
    member_id: UUID,
    payload: HostTeamMemberUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> HostTeamMemberPublic:
    row = team_service.update_team_member(
        db, user=user, member_id=member_id, payload=payload, host_id=None
    )
    return HostTeamMemberPublic.model_validate(row)


@router.patch("/{host_id}/team/{member_id}", response_model=HostTeamMemberPublic)
def update_host_team_member(
    host_id: UUID,
    member_id: UUID,
    payload: HostTeamMemberUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> HostTeamMemberPublic:
    row = team_service.update_team_member(
        db, user=user, member_id=member_id, payload=payload, host_id=host_id
    )
    return HostTeamMemberPublic.model_validate(row)


@router.patch(
    "/me/team/{member_id}/permissions",
    response_model=HostTeamMemberPublic,
)
def update_my_team_permissions(
    member_id: UUID,
    payload: HostTeamPermissionsUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> HostTeamMemberPublic:
    row = team_service.update_team_permissions(
        db, user=user, member_id=member_id, payload=payload, host_id=None
    )
    return HostTeamMemberPublic.model_validate(row)


@router.patch(
    "/{host_id}/team/{member_id}/permissions",
    response_model=HostTeamMemberPublic,
)
def update_host_team_permissions(
    host_id: UUID,
    member_id: UUID,
    payload: HostTeamPermissionsUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> HostTeamMemberPublic:
    row = team_service.update_team_permissions(
        db, user=user, member_id=member_id, payload=payload, host_id=host_id
    )
    return HostTeamMemberPublic.model_validate(row)


@router.post("/me/team/{member_id}/resend", response_model=HostTeamMemberPublic)
def resend_my_team_invite(
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> HostTeamMemberPublic:
    row = team_service.resend_invite(
        db, user=user, member_id=member_id, host_id=None
    )
    return HostTeamMemberPublic.model_validate(row)


@router.post(
    "/{host_id}/team/{member_id}/resend", response_model=HostTeamMemberPublic
)
def resend_host_team_invite(
    host_id: UUID,
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> HostTeamMemberPublic:
    row = team_service.resend_invite(
        db, user=user, member_id=member_id, host_id=host_id
    )
    return HostTeamMemberPublic.model_validate(row)


@router.post("/me/team/{member_id}/revoke", response_model=HostTeamMemberPublic)
def revoke_my_team_invite(
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> HostTeamMemberPublic:
    row = team_service.revoke_team_invite(
        db, user=user, member_id=member_id, host_id=None
    )
    return HostTeamMemberPublic.model_validate(row)


@router.post(
    "/{host_id}/team/{member_id}/revoke", response_model=HostTeamMemberPublic
)
def revoke_host_team_invite(
    host_id: UUID,
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> HostTeamMemberPublic:
    row = team_service.revoke_team_invite(
        db, user=user, member_id=member_id, host_id=host_id
    )
    return HostTeamMemberPublic.model_validate(row)


@router.post("/me/team/{member_id}/suspend", response_model=HostTeamMemberPublic)
def suspend_my_team_member(
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> HostTeamMemberPublic:
    row = team_service.suspend_team_member(
        db, user=user, member_id=member_id, host_id=None
    )
    return HostTeamMemberPublic.model_validate(row)


@router.post(
    "/{host_id}/team/{member_id}/suspend", response_model=HostTeamMemberPublic
)
def suspend_host_team_member(
    host_id: UUID,
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> HostTeamMemberPublic:
    row = team_service.suspend_team_member(
        db, user=user, member_id=member_id, host_id=host_id
    )
    return HostTeamMemberPublic.model_validate(row)


@router.delete("/me/team/{member_id}", status_code=status.HTTP_405_METHOD_NOT_ALLOWED)
def delete_my_team_member() -> None:
    team_service.delete_team_member_blocked()


@router.post("/me/team/{member_id}/archive", response_model=HostTeamMemberPublic)
def archive_my_team_member(
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> HostTeamMemberPublic:
    row = team_service.archive_team_member(
        db, user=user, member_id=member_id, host_id=None
    )
    return HostTeamMemberPublic.model_validate(row)


@router.post(
    "/{host_id}/team/{member_id}/archive", response_model=HostTeamMemberPublic
)
def archive_host_team_member(
    host_id: UUID,
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> HostTeamMemberPublic:
    row = team_service.archive_team_member(
        db, user=user, member_id=member_id, host_id=host_id
    )
    return HostTeamMemberPublic.model_validate(row)


@router.post("/me/team/{member_id}/restore", response_model=HostTeamMemberPublic)
def restore_my_team_member(
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> HostTeamMemberPublic:
    row = team_service.restore_team_member(
        db, user=user, member_id=member_id, host_id=None
    )
    return HostTeamMemberPublic.model_validate(row)


@router.post(
    "/{host_id}/team/{member_id}/restore", response_model=HostTeamMemberPublic
)
def restore_host_team_member(
    host_id: UUID,
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> HostTeamMemberPublic:
    row = team_service.restore_team_member(
        db, user=user, member_id=member_id, host_id=host_id
    )
    return HostTeamMemberPublic.model_validate(row)


@router.get("/team-invites/{token}", response_model=HostTeamInvitePreview)
def preview_team_invite(
    token: str,
    db: Annotated[Session, Depends(get_db)],
) -> HostTeamInvitePreview:
    return HostTeamInvitePreview.model_validate(
        team_service.preview_team_invite(db, token=token)
    )


@router.post("/team-invites/{token}/accept", response_model=HostTeamMemberPublic)
def accept_team_invite(
    token: str,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> HostTeamMemberPublic:
    row = team_service.accept_team_invite(db, user=user, token=token)
    return HostTeamMemberPublic.model_validate(row)


@router.post("/team-invites/{token}/decline", response_model=HostTeamMemberPublic)
def decline_team_invite(
    token: str,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> HostTeamMemberPublic:
    row = team_service.decline_team_invite(db, user=user, token=token)
    return HostTeamMemberPublic.model_validate(row)


# --- Bank accounts ---


@router.get("/me/bank-accounts", response_model=list[HostBankAccountPublic])
def list_my_bank_accounts(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    include_archived: bool = Query(default=False),
) -> list[HostBankAccountPublic]:
    rows = bank_service.list_bank_accounts(
        db, user=user, include_archived=include_archived
    )
    return [HostBankAccountPublic.model_validate(r) for r in rows]


@router.post(
    "/me/bank-accounts",
    response_model=HostBankAccountPublic,
    status_code=status.HTTP_201_CREATED,
)
def create_my_bank_account(
    payload: HostBankAccountCreate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> HostBankAccountPublic:
    row = bank_service.create_bank_account(db, user=user, payload=payload)
    return HostBankAccountPublic.model_validate(row)


@router.get("/me/bank-accounts/{account_id}", response_model=HostBankAccountPublic)
def get_my_bank_account(
    account_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> HostBankAccountPublic:
    row = bank_service.get_bank_account(db, user=user, account_id=account_id)
    return HostBankAccountPublic.model_validate(row)


@router.patch("/me/bank-accounts/{account_id}", response_model=HostBankAccountPublic)
def update_my_bank_account(
    account_id: UUID,
    payload: HostBankAccountUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> HostBankAccountPublic:
    row = bank_service.update_bank_account(
        db, user=user, account_id=account_id, payload=payload
    )
    return HostBankAccountPublic.model_validate(row)


@router.delete(
    "/me/bank-accounts/{account_id}",
    status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
)
def delete_my_bank_account() -> None:
    bank_service.delete_bank_account_blocked()


@router.post(
    "/me/bank-accounts/{account_id}/archive",
    response_model=HostBankAccountPublic,
)
def archive_my_bank_account(
    account_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> HostBankAccountPublic:
    row = bank_service.archive_bank_account(db, user=user, account_id=account_id)
    return HostBankAccountPublic.model_validate(row)


@router.post(
    "/me/bank-accounts/{account_id}/restore",
    response_model=HostBankAccountPublic,
)
def restore_my_bank_account(
    account_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> HostBankAccountPublic:
    row = bank_service.restore_bank_account(db, user=user, account_id=account_id)
    return HostBankAccountPublic.model_validate(row)


# --- Verification admin ---


@router.get(
    "/admin/verifications",
    response_model=list[HostVerificationPublic],
    dependencies=[Depends(require_permission("hosts.verify"))],
)
def admin_list_verifications(
    db: Annotated[Session, Depends(get_db)],
    status_filter: str | None = Query(default=None, alias="status"),
) -> list[HostVerificationPublic]:
    rows = verification_service.list_verifications(db, status_filter=status_filter)
    return [
        HostVerificationPublic.model_validate(
            verification_service.serialize_verification(db, r)
        )
        for r in rows
    ]


@router.post(
    "/admin/verifications/{verification_id}/approve",
    response_model=HostVerificationPublic,
)
def admin_approve_verification(
    verification_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("hosts.verify"))],
) -> HostVerificationPublic:
    row = verification_service.approve_verification(
        db, admin=admin, verification_id=verification_id
    )
    return HostVerificationPublic.model_validate(
        verification_service.serialize_verification(db, row)
    )


@router.post(
    "/admin/verifications/{verification_id}/reject",
    response_model=HostVerificationPublic,
)
def admin_reject_verification(
    verification_id: UUID,
    payload: HostVerificationReject,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_permission("hosts.verify"))],
) -> HostVerificationPublic:
    row = verification_service.reject_verification(
        db, admin=admin, verification_id=verification_id, notes=payload.notes
    )
    return HostVerificationPublic.model_validate(
        verification_service.serialize_verification(db, row)
    )
