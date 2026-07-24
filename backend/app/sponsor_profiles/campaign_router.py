"""Sponsor campaign workspace API."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser
from app.core.database import get_db
from app.sponsor_profiles import campaign_service as svc
from app.sponsor_profiles.recommendations import service as rec_svc
from app.sponsor_profiles.campaign_schemas import (
    CampaignRecommendationFeedbackCreate,
    CampaignRecommendationListPublic,
    CampaignSavedItemLinkCreate,
    CampaignSavedItemPublic,
    SponsorCampaignCreate,
    SponsorCampaignDetail,
    SponsorCampaignListItem,
    SponsorCampaignListPublic,
    SponsorCampaignUpdate,
)

router = APIRouter(prefix="/sponsors/workspaces", tags=["sponsor-campaigns"])


@router.get("/{sponsor_id}/campaigns", response_model=SponsorCampaignListPublic)
def list_campaigns(
    sponsor_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> SponsorCampaignListPublic:
    data = svc.list_campaigns(db, user=user, sponsor_id=sponsor_id)
    return SponsorCampaignListPublic(
        items=[SponsorCampaignListItem.model_validate(i) for i in data["items"]],
        total=data["total"],
    )


@router.post(
    "/{sponsor_id}/campaigns",
    response_model=SponsorCampaignDetail,
    status_code=status.HTTP_201_CREATED,
)
def create_campaign(
    sponsor_id: UUID,
    payload: SponsorCampaignCreate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> SponsorCampaignDetail:
    row = svc.create_campaign(
        db, user=user, sponsor_id=sponsor_id, payload=payload
    )
    return SponsorCampaignDetail.model_validate(row)


@router.get(
    "/{sponsor_id}/campaigns/{campaign_id}",
    response_model=SponsorCampaignDetail,
)
def get_campaign(
    sponsor_id: UUID,
    campaign_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> SponsorCampaignDetail:
    row = svc.get_campaign(
        db, user=user, sponsor_id=sponsor_id, campaign_id=campaign_id
    )
    return SponsorCampaignDetail.model_validate(row)


@router.patch(
    "/{sponsor_id}/campaigns/{campaign_id}",
    response_model=SponsorCampaignDetail,
)
def patch_campaign(
    sponsor_id: UUID,
    campaign_id: UUID,
    payload: SponsorCampaignUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> SponsorCampaignDetail:
    row = svc.update_campaign(
        db,
        user=user,
        sponsor_id=sponsor_id,
        campaign_id=campaign_id,
        payload=payload,
    )
    return SponsorCampaignDetail.model_validate(row)


@router.post(
    "/{sponsor_id}/campaigns/{campaign_id}/archive",
    response_model=SponsorCampaignDetail,
)
def archive_campaign(
    sponsor_id: UUID,
    campaign_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> SponsorCampaignDetail:
    row = svc.archive_campaign(
        db, user=user, sponsor_id=sponsor_id, campaign_id=campaign_id
    )
    return SponsorCampaignDetail.model_validate(row)


@router.post(
    "/{sponsor_id}/campaigns/{campaign_id}/pause",
    response_model=SponsorCampaignDetail,
)
def pause_campaign(
    sponsor_id: UUID,
    campaign_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> SponsorCampaignDetail:
    row = svc.pause_campaign(
        db, user=user, sponsor_id=sponsor_id, campaign_id=campaign_id
    )
    return SponsorCampaignDetail.model_validate(row)


@router.post(
    "/{sponsor_id}/campaigns/{campaign_id}/activate",
    response_model=SponsorCampaignDetail,
)
def activate_campaign(
    sponsor_id: UUID,
    campaign_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> SponsorCampaignDetail:
    row = svc.activate_campaign(
        db, user=user, sponsor_id=sponsor_id, campaign_id=campaign_id
    )
    return SponsorCampaignDetail.model_validate(row)


@router.post(
    "/{sponsor_id}/campaigns/{campaign_id}/saved-items",
    response_model=CampaignSavedItemPublic,
    status_code=status.HTTP_201_CREATED,
)
def add_saved_item(
    sponsor_id: UUID,
    campaign_id: UUID,
    payload: CampaignSavedItemLinkCreate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> CampaignSavedItemPublic:
    row = svc.attach_saved_item(
        db,
        user=user,
        sponsor_id=sponsor_id,
        campaign_id=campaign_id,
        payload=payload,
    )
    return CampaignSavedItemPublic.model_validate(row)


@router.delete(
    "/{sponsor_id}/campaigns/{campaign_id}/saved-items/{saved_item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_saved_item(
    sponsor_id: UUID,
    campaign_id: UUID,
    saved_item_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> None:
    svc.detach_saved_item(
        db,
        user=user,
        sponsor_id=sponsor_id,
        campaign_id=campaign_id,
        saved_item_id=saved_item_id,
    )


@router.get(
    "/{sponsor_id}/campaigns/{campaign_id}/recommendations",
    response_model=CampaignRecommendationListPublic,
)
def list_recommendations(
    sponsor_id: UUID,
    campaign_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> CampaignRecommendationListPublic:
    data = rec_svc.get_recommendations(
        db, user=user, sponsor_id=sponsor_id, campaign_id=campaign_id
    )
    return CampaignRecommendationListPublic.model_validate(data)


@router.post(
    "/{sponsor_id}/campaigns/{campaign_id}/recommendations/{item_id}/feedback",
    status_code=status.HTTP_204_NO_CONTENT,
)
def recommendation_feedback(
    sponsor_id: UUID,
    campaign_id: UUID,
    item_id: UUID,
    payload: CampaignRecommendationFeedbackCreate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> None:
    rec_svc.record_recommendation_feedback(
        db,
        user=user,
        sponsor_id=sponsor_id,
        campaign_id=campaign_id,
        item_type=payload.item_type,
        item_id=item_id,
        action=payload.action,
    )
