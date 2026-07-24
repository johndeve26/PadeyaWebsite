"""Admin host recommendation debug."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.hosts.recommendations import service as rec_svc
from app.hosts.recommendations.schemas import HostRecommendationDebugPublic
from app.users.models import User

router = APIRouter(
    prefix="/admin/recommendations/hosts",
    tags=["admin-host-recommendations"],
    dependencies=[Depends(require_permission("admin.full_access"))],
)


@router.get("/debug", response_model=HostRecommendationDebugPublic)
def debug_host_recommendations(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.full_access"))],
    user_id: Annotated[UUID, Query(description="Fan user id to inspect")],
) -> HostRecommendationDebugPublic:
    payload = rec_svc.debug_recommendations(db, target_user_id=user_id)
    return HostRecommendationDebugPublic.model_validate(payload)
