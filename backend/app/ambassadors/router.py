"""Public / user Ambassadors routes — /api/v1/ambassadors/..."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.ambassadors import service as svc
from app.ambassadors.rate_limit import rate_limit_ambassador_track
from app.ambassadors.schemas import (
    AmbassadorJoinRequest,
    AmbassadorLinkPublic,
    CampaignPublic,
    EarningsSummaryPublic,
    EligibleEventPublic,
    ParticipantPublic,
    ProfilePublic,
    TrackCheckoutStartedRequest,
    TrackClickRequest,
    TrackResultPublic,
)
from app.auth.dependencies import CurrentUser, get_current_user_optional
from app.core.database import get_db
from app.users.models import User

router = APIRouter(prefix="/ambassadors", tags=["ambassadors"])


@router.get("/eligible-events", response_model=list[EligibleEventPublic])
def eligible_events(
    db: Annotated[Session, Depends(get_db)],
) -> list[EligibleEventPublic]:
    return [
        EligibleEventPublic.model_validate(r) for r in svc.list_eligible_events(db)
    ]


@router.post("/join", response_model=ParticipantPublic)
def join(
    payload: AmbassadorJoinRequest,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> ParticipantPublic:
    return ParticipantPublic.model_validate(
        svc.join_campaign(
            db,
            user=user,
            accept_terms=payload.accept_terms,
            campaign_id=payload.campaign_id,
            event_id=payload.event_id,
        )
    )


@router.get("/me", response_model=ProfilePublic)
def me(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> ProfilePublic:
    return ProfilePublic.model_validate(svc.get_my_profile(db, user))


@router.get("/me/campaigns", response_model=list[ParticipantPublic])
def my_campaigns(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[ParticipantPublic]:
    return [
        ParticipantPublic.model_validate(r) for r in svc.list_my_campaigns(db, user)
    ]


@router.get("/me/links", response_model=list[AmbassadorLinkPublic])
def my_links(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[AmbassadorLinkPublic]:
    return [
        AmbassadorLinkPublic.model_validate(r) for r in svc.list_my_links(db, user)
    ]


@router.get("/me/earnings", response_model=EarningsSummaryPublic)
def my_earnings(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> EarningsSummaryPublic:
    return EarningsSummaryPublic.model_validate(svc.my_earnings(db, user))


@router.get("/campaigns/{campaign_id}", response_model=CampaignPublic)
def get_campaign(
    campaign_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> CampaignPublic:
    return CampaignPublic.model_validate(svc.get_public_campaign(db, campaign_id))


@router.post(
    "/track-click",
    response_model=TrackResultPublic,
    dependencies=[Depends(rate_limit_ambassador_track)],
)
def track_click(
    payload: TrackClickRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> TrackResultPublic:
    from app.ambassadors.fraud import request_client_ip

    return TrackResultPublic.model_validate(
        svc.track_click(
            db,
            payload=payload,
            user=user,
            ip_address=request_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    )


@router.post("/track-checkout-started", response_model=TrackResultPublic)
def track_checkout_started(
    payload: TrackCheckoutStartedRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> TrackResultPublic:
    return TrackResultPublic.model_validate(
        svc.track_checkout_started(db, payload=payload, user=user)
    )
