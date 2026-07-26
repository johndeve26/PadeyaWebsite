"""Current-user APIs: workspaces + impersonation status under `/api/v1/me`."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.admin.impersonation_service import build_impersonation_public
from app.admin.schemas import ImpersonationStatusResponse, SessionIdentityResponse
from app.auth.dependencies import CurrentUser, RequestIdentity
from app.auth.impersonation_context import get_impersonation_context
from app.core.database import get_db
from app.hosts import workspace_service
from app.teams.schemas import (
    ActiveWorkspacePublic,
    ActiveWorkspaceSet,
    TeamWorkspacePublic,
)
from app.teams.workspace_pref import get_active_workspace_id, set_active_workspace
from app.users.service import get_user_by_id

router = APIRouter(prefix="/me", tags=["me"])


@router.get("/session", response_model=SessionIdentityResponse)
def get_my_session_identity(
    user: CurrentUser,
    identity: RequestIdentity,
) -> SessionIdentityResponse:
    """Return current_user_id plus actor_admin_id / impersonation_id when set.

    ``current_user_id`` is always the effective user (the target while
    impersonating). Admin permissions are never inherited.
    """
    return SessionIdentityResponse(
        current_user_id=identity.current_user_id or user.id,
        actor_admin_id=identity.actor_admin_id,
        impersonation_id=identity.impersonation_id,
        is_impersonating=identity.is_impersonating,
    )


@router.get("/team-workspaces", response_model=list[TeamWorkspacePublic])
def list_my_team_workspaces(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[TeamWorkspacePublic]:
    active_id = get_active_workspace_id(db, user_id=user.id)
    rows = workspace_service.list_user_workspaces(db, user=user)
    return [
        TeamWorkspacePublic.model_validate(
            {**row, "is_active": active_id is not None and row["host_id"] == active_id}
        )
        for row in rows
    ]


@router.post("/active-workspace", response_model=ActiveWorkspacePublic)
def set_my_active_workspace(
    payload: ActiveWorkspaceSet,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> ActiveWorkspacePublic:
    row = set_active_workspace(db, user=user, host_id=payload.host_id)
    return ActiveWorkspacePublic.model_validate(row)


@router.get("/impersonation", response_model=ImpersonationStatusResponse)
def get_my_impersonation(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> ImpersonationStatusResponse:
    """Return the active impersonation session, if any."""
    ctx = get_impersonation_context()
    if ctx is None:
        return ImpersonationStatusResponse(is_impersonating=False)

    impersonator = get_user_by_id(db, ctx.actor_admin_id)
    expires_at = getattr(user, "_impersonation_expires_at", None)
    data = build_impersonation_public(
        ctx=ctx,
        impersonator=impersonator,
        expires_at=expires_at,
        target=user,
    )
    return ImpersonationStatusResponse(
        is_impersonating=True,
        impersonation_id=data["impersonation_id"],
        current_user_id=user.id,
        actual_user_id=data["actual_user_id"],
        actor_admin_id=data["actor_admin_id"],
        target_user_id=data["target_user_id"],
        reason=data.get("reason"),
        support_ticket_id=data.get("support_ticket_id"),
        started_at=data.get("started_at"),
        expires_at=data.get("expires_at"),
        impersonator_email=data.get("impersonator_email"),
        impersonator_full_name=data.get("impersonator_full_name"),
        target_email=user.email,
        target_full_name=user.full_name,
        scopes=list(data.get("scopes") or []),
        pack=data.get("pack"),
    )
