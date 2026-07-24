"""Sponsor workspace reports API."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser
from app.core.database import get_db
from app.sponsor_profiles import report_service as svc
from app.sponsor_profiles.report_schemas import (
    CampaignReportPublic,
    SponsorOverviewReportPublic,
)

router = APIRouter(prefix="/sponsors/workspaces", tags=["sponsor-reports"])


@router.get("/{sponsor_id}/reports/overview", response_model=SponsorOverviewReportPublic)
def sponsor_overview_report(
    sponsor_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> SponsorOverviewReportPublic:
    data = svc.overview_report(db, user=user, sponsor_id=sponsor_id)
    return SponsorOverviewReportPublic.model_validate(data)


@router.get(
    "/{sponsor_id}/campaigns/{campaign_id}/reports",
    response_model=CampaignReportPublic,
)
def sponsor_campaign_report(
    sponsor_id: UUID,
    campaign_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> CampaignReportPublic:
    data = svc.campaign_report(
        db, user=user, sponsor_id=sponsor_id, campaign_id=campaign_id
    )
    return CampaignReportPublic.model_validate(data)
