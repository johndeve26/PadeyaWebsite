"""Public admin team invite acceptance API: `/api/v1/admin/team/invites/{token}`."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.admin_team import service as team_service
from app.auth.dependencies import CurrentUser
from app.core.database import get_db

router = APIRouter(prefix="/admin/team/invites", tags=["admin-team-invites"])


def _client_meta(request: Request) -> tuple[str | None, str | None]:
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    return ip, ua


@router.get("/{token}")
def preview_admin_team_invite(
    token: str,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return team_service.preview_admin_invite(db, token=token)


@router.post("/{token}/accept")
def accept_admin_team_invite(
    token: str,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict[str, Any]:
    ip, ua = _client_meta(request)
    return team_service.accept_admin_invite(
        db,
        user=user,
        token=token,
        ip_address=ip,
        user_agent=ua,
    )
