"""Admin sponsor campaign moderation API."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.sponsor_profiles import campaign_service as svc
from app.sponsor_profiles.campaign_schemas import (
    AdminCampaignDetail,
    AdminCampaignListItem,
    AdminCampaignRejectRequest,
)
from app.sponsor_profiles.recommendations.service import admin_debug_recommendations
from app.users.models import User

router = APIRouter(prefix="/admin/sponsor-campaigns", tags=["admin-sponsor-campaigns"])


@router.get("", response_model=list[AdminCampaignListItem])
def admin_list(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.sponsor_campaigns.view"))],
) -> list[AdminCampaignListItem]:
    rows = svc.admin_list_campaigns(db)
    return [AdminCampaignListItem.model_validate(r) for r in rows]


@router.get("/{campaign_id}", response_model=AdminCampaignDetail)
def admin_detail(
    campaign_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.sponsor_campaigns.view"))],
) -> AdminCampaignDetail:
    row = svc.admin_get_campaign(db, campaign_id)
    return AdminCampaignDetail.model_validate(row)


@router.get("/{campaign_id}/recommendations/debug")
def admin_recommendations_debug(
    campaign_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.sponsor_campaigns.view"))],
) -> dict:
    return admin_debug_recommendations(db, campaign_id=campaign_id)


@router.post("/{campaign_id}/approve", response_model=AdminCampaignDetail)
def admin_approve(
    campaign_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(require_permission("admin.sponsor_campaigns.moderate"))],
) -> AdminCampaignDetail:
    row = svc.admin_approve_campaign(db, actor=actor, campaign_id=campaign_id)
    return AdminCampaignDetail.model_validate(row)


@router.post("/{campaign_id}/reject", response_model=AdminCampaignDetail)
def admin_reject(
    campaign_id: UUID,
    payload: AdminCampaignRejectRequest,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(require_permission("admin.sponsor_campaigns.moderate"))],
) -> AdminCampaignDetail:
    row = svc.admin_reject_campaign(
        db,
        actor=actor,
        campaign_id=campaign_id,
        rejection_reason=payload.rejection_reason,
    )
    return AdminCampaignDetail.model_validate(row)
