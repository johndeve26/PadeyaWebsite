"""Platform admin team overview: `/api/v1/admin/teams*`."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.teams import admin_service
from app.teams.schemas import AdminTeamAuditItem, AdminTeamSummary
from app.users.models import User

router = APIRouter(prefix="/admin/teams", tags=["admin-teams"])


@router.get("", response_model=list[AdminTeamSummary])
def list_admin_teams(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.full_access"))],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[AdminTeamSummary]:
    rows = admin_service.list_admin_teams(db, limit=limit, offset=offset)
    return [AdminTeamSummary.model_validate(r) for r in rows]


@router.get("/audit", response_model=list[AdminTeamAuditItem])
def list_admin_teams_audit(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.full_access"))],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    host_id: UUID | None = Query(default=None),
) -> list[AdminTeamAuditItem]:
    rows = admin_service.list_admin_team_audit(
        db, limit=limit, offset=offset, host_id=host_id
    )
    return [AdminTeamAuditItem.model_validate(r) for r in rows]
