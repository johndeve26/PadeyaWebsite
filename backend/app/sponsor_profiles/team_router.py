"""Sponsor team management API."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser
from app.core.database import get_db
from app.sponsor_profiles.team_schemas import (
    SponsorTeamAuditItem,
    SponsorTeamInviteCreate,
    SponsorTeamInviteCreateResponse,
    SponsorTeamInvitePreview,
    SponsorTeamInvitePublic,
    SponsorTeamListPublic,
    SponsorTeamMemberPublic,
    SponsorTeamMemberUpdate,
)
from app.sponsor_profiles import team_service as svc

router = APIRouter(prefix="/sponsors/workspaces", tags=["sponsor-team"])


@router.get("/{sponsor_id}/team", response_model=SponsorTeamListPublic)
def get_sponsor_team(
    sponsor_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> SponsorTeamListPublic:
    data = svc.list_sponsor_team(db, user=user, sponsor_id=sponsor_id)
    return SponsorTeamListPublic(
        members=[SponsorTeamMemberPublic.model_validate(m) for m in data["members"]],
        invites=[SponsorTeamInvitePublic.model_validate(i) for i in data["invites"]],
    )


@router.post(
    "/{sponsor_id}/team/invites",
    response_model=SponsorTeamInviteCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_invite(
    sponsor_id: UUID,
    payload: SponsorTeamInviteCreate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> SponsorTeamInviteCreateResponse:
    invite, accept_path = svc.create_team_invite(
        db, user=user, sponsor_id=sponsor_id, payload=payload
    )
    return SponsorTeamInviteCreateResponse(
        invite=SponsorTeamInvitePublic.model_validate(invite),
        accept_path=accept_path,
    )


@router.post(
    "/{sponsor_id}/team/invites/{invite_id}/resend",
    response_model=SponsorTeamInvitePublic,
)
def resend_invite(
    sponsor_id: UUID,
    invite_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> SponsorTeamInvitePublic:
    row = svc.resend_team_invite(
        db, user=user, sponsor_id=sponsor_id, invite_id=invite_id
    )
    return SponsorTeamInvitePublic.model_validate(row)


@router.delete(
    "/{sponsor_id}/team/invites/{invite_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def cancel_invite(
    sponsor_id: UUID,
    invite_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> None:
    svc.cancel_team_invite(db, user=user, sponsor_id=sponsor_id, invite_id=invite_id)


@router.patch(
    "/{sponsor_id}/team/members/{member_id}",
    response_model=SponsorTeamMemberPublic,
)
def patch_member(
    sponsor_id: UUID,
    member_id: UUID,
    payload: SponsorTeamMemberUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> SponsorTeamMemberPublic:
    row = svc.update_team_member(
        db,
        user=user,
        sponsor_id=sponsor_id,
        member_id=member_id,
        payload=payload,
    )
    return SponsorTeamMemberPublic.model_validate(row)


@router.delete(
    "/{sponsor_id}/team/members/{member_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_member(
    sponsor_id: UUID,
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> None:
    svc.remove_team_member(db, user=user, sponsor_id=sponsor_id, member_id=member_id)


@router.get("/{sponsor_id}/team/audit", response_model=list[SponsorTeamAuditItem])
def team_audit(
    sponsor_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[SponsorTeamAuditItem]:
    rows = svc.list_team_audit(db, user=user, sponsor_id=sponsor_id)
    return [SponsorTeamAuditItem.model_validate(r) for r in rows]


invite_router = APIRouter(prefix="/sponsors/team/invites", tags=["sponsor-team-invites"])


@invite_router.get("/{token}", response_model=SponsorTeamInvitePreview)
def preview_invite(
    token: str,
    db: Annotated[Session, Depends(get_db)],
) -> SponsorTeamInvitePreview:
    return SponsorTeamInvitePreview.model_validate(
        svc.preview_team_invite(db, token=token)
    )


@invite_router.post("/{token}/accept", response_model=SponsorTeamMemberPublic)
def accept_invite(
    token: str,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> SponsorTeamMemberPublic:
    row = svc.accept_team_invite(db, user=user, token=token)
    return SponsorTeamMemberPublic.model_validate(row)
