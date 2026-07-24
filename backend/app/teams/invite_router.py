"""Public invite acceptance API: `/api/v1/team/invites/{token}`."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser
from app.core.database import get_db
from app.hosts import team_service
from app.hosts.lifecycle_schemas import HostTeamInvitePreview, HostTeamMemberPublic

router = APIRouter(prefix="/team/invites", tags=["team-invites"])


@router.get("/{token}", response_model=HostTeamInvitePreview)
def preview_team_invite(
    token: str,
    db: Annotated[Session, Depends(get_db)],
) -> HostTeamInvitePreview:
    return HostTeamInvitePreview.model_validate(
        team_service.preview_team_invite(db, token=token)
    )


@router.post("/{token}/accept", response_model=HostTeamMemberPublic)
def accept_team_invite(
    token: str,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> HostTeamMemberPublic:
    row = team_service.accept_team_invite(db, user=user, token=token)
    return HostTeamMemberPublic.model_validate(row)
