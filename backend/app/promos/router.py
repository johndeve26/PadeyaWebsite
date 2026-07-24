"""Promo codes and ambassador API."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.ambassadors.rate_limit import rate_limit_ambassador_track
from app.auth.dependencies import CurrentUser, get_current_user_optional
from app.users.models import User
from app.core.database import get_db
from app.events.schemas import MessageResponse
from app.promos.campaigns import (
    campaign_leaderboard,
    create_campaign,
    end_campaign,
    get_event_campaign,
    get_host_campaign,
    list_event_open_campaigns,
    list_host_campaigns,
    pause_campaign,
    remove_campaign_ambassador,
    resume_campaign,
    serialize_campaign,
    update_campaign,
)
from app.promos.schemas import (
    AmbassadorCampaignCreate,
    AmbassadorCampaignPublic,
    AmbassadorCampaignUpdate,
    AmbassadorCreate,
    AmbassadorEarningsSummary,
    AmbassadorHostDashboard,
    AmbassadorSelfDashboard,
    AmbassadorEnrollmentList,
    AmbassadorPublic,
    CampaignLeaderboardRow,
    EligibleAmbassadorEventPublic,
    AmbassadorUpdate,
    OpenAmbassadorJoinRequest,
    OpenAmbassadorProgramPublic,
    PromoCodeCreate,
    PromoCodePublic,
    PromoCodeUpdate,
    PromoValidateRequest,
    PromoValidateResponse,
    ReferralClickRequest,
)
from app.promos.service import (
    create_ambassador,
    create_promo,
    delete_ambassador,
    delete_promo,
    get_host_ambassador_detail,
    get_my_ambassador_dashboard,
    get_my_ambassador_earnings_summary,
    get_my_open_event_ambassador,
    get_open_ambassador_program,
    join_open_event_ambassador,
    leave_open_event_ambassador,
    list_eligible_ambassador_events,
    list_host_ambassadors,
    list_host_promos,
    list_my_ambassador_enrollments,
    preview_promo,
    record_referral_click,
    update_ambassador,
    update_promo,
)

router = APIRouter(prefix="/promos", tags=["promos"])


@router.get("/health")
async def promos_module_health() -> dict[str, str]:
    return {"module": "promos", "status": "ok"}


@router.get("/codes", response_model=list[PromoCodePublic])
def host_promos(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[PromoCodePublic]:
    return [PromoCodePublic.model_validate(p) for p in list_host_promos(db, user)]


@router.post("/codes", response_model=PromoCodePublic, status_code=status.HTTP_201_CREATED)
def create_promo_code(
    payload: PromoCodeCreate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> PromoCodePublic:
    return PromoCodePublic.model_validate(create_promo(db, user=user, payload=payload))


@router.patch("/codes/{promo_id}", response_model=PromoCodePublic)
def patch_promo_code(
    promo_id: UUID,
    payload: PromoCodeUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> PromoCodePublic:
    return PromoCodePublic.model_validate(
        update_promo(db, user=user, promo_id=promo_id, payload=payload)
    )


@router.delete("/codes/{promo_id}", response_model=MessageResponse)
def remove_promo_code(
    promo_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> MessageResponse:
    delete_promo(db, user=user, promo_id=promo_id)
    return MessageResponse(message="Promo code deleted")


@router.post("/validate", response_model=PromoValidateResponse)
def validate_promo(
    payload: PromoValidateRequest,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> PromoValidateResponse:
    return PromoValidateResponse.model_validate(
        preview_promo(
            db,
            user=user,
            code=payload.code,
            event_id=payload.event_id,
            items=payload.items,
        )
    )


@router.post(
    "/referrals/click",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_ambassador_track)],
)
def referral_click(
    payload: ReferralClickRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> dict[str, str | bool]:
    from app.ambassadors.fraud import request_client_ip
    from app.ambassadors.referral_tracking import (
        ReferralLandingInput,
        ReferralTrackingService,
    )

    source = payload.source or (
        "merch_page"
        if payload.landing_path and "/merch" in payload.landing_path
        else (
            "checkout"
            if payload.landing_path and "/checkout" in payload.landing_path
            else ("event_page" if payload.event_id else "host_page")
        )
    )
    target_type = (
        "checkout"
        if source == "checkout"
        else (
            "merch"
            if source == "merch_page"
            else ("event" if payload.event_id else "host")
        )
    )
    result = ReferralTrackingService.record_landing(
        db,
        ReferralLandingInput(
            referral_code=payload.referral_code,
            source=source,
            target_type=target_type,
            event_id=payload.event_id,
            landing_path=payload.landing_path,
            anonymous_visitor_id=payload.anonymous_visitor_id,
            user=user,
            ip_address=request_client_ip(request),
            user_agent=request.headers.get("user-agent"),
            prefer_merch=source == "merch_page",
        ),
    )
    return {
        "status": "ok",
        "click_id": str(result["click_id"]),
        "is_duplicate_30s": result.get("is_duplicate_30s", False),
        "is_unique_24h": result.get("is_unique_24h", False),
    }


@router.get(
    "/ambassadors/eligible-events",
    response_model=list[EligibleAmbassadorEventPublic],
)
def eligible_ambassador_events(
    db: Annotated[Session, Depends(get_db)],
) -> list[EligibleAmbassadorEventPublic]:
    return [
        EligibleAmbassadorEventPublic.model_validate(row)
        for row in list_eligible_ambassador_events(db)
    ]


@router.get("/campaigns", response_model=list[AmbassadorCampaignPublic])
def host_campaigns(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[AmbassadorCampaignPublic]:
    return [
        AmbassadorCampaignPublic.model_validate(c) for c in list_host_campaigns(db, user)
    ]


@router.post(
    "/campaigns",
    response_model=AmbassadorCampaignPublic,
    status_code=status.HTTP_201_CREATED,
)
def create_host_campaign(
    payload: AmbassadorCampaignCreate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> AmbassadorCampaignPublic:
    return AmbassadorCampaignPublic.model_validate(
        create_campaign(db, user=user, payload=payload)
    )


@router.get("/campaigns/{campaign_id}", response_model=AmbassadorCampaignPublic)
def host_campaign_detail(
    campaign_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> AmbassadorCampaignPublic:
    return AmbassadorCampaignPublic.model_validate(
        get_host_campaign(db, user=user, campaign_id=campaign_id)
    )


@router.patch("/campaigns/{campaign_id}", response_model=AmbassadorCampaignPublic)
def patch_host_campaign(
    campaign_id: UUID,
    payload: AmbassadorCampaignUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> AmbassadorCampaignPublic:
    return AmbassadorCampaignPublic.model_validate(
        update_campaign(db, user=user, campaign_id=campaign_id, payload=payload)
    )


@router.post("/campaigns/{campaign_id}/pause", response_model=AmbassadorCampaignPublic)
def pause_host_campaign(
    campaign_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> AmbassadorCampaignPublic:
    return AmbassadorCampaignPublic.model_validate(
        pause_campaign(db, user=user, campaign_id=campaign_id)
    )


@router.post("/campaigns/{campaign_id}/resume", response_model=AmbassadorCampaignPublic)
def resume_host_campaign(
    campaign_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> AmbassadorCampaignPublic:
    return AmbassadorCampaignPublic.model_validate(
        resume_campaign(db, user=user, campaign_id=campaign_id)
    )


@router.post("/campaigns/{campaign_id}/end", response_model=AmbassadorCampaignPublic)
def end_host_campaign(
    campaign_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> AmbassadorCampaignPublic:
    return AmbassadorCampaignPublic.model_validate(
        end_campaign(db, user=user, campaign_id=campaign_id)
    )


@router.get(
    "/campaigns/{campaign_id}/leaderboard",
    response_model=list[CampaignLeaderboardRow],
)
def host_campaign_leaderboard(
    campaign_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[CampaignLeaderboardRow]:
    return [
        CampaignLeaderboardRow.model_validate(r)
        for r in campaign_leaderboard(db, user=user, campaign_id=campaign_id)
    ]


@router.post(
    "/campaigns/{campaign_id}/ambassadors/{ambassador_id}/remove",
    response_model=MessageResponse,
)
def remove_host_campaign_ambassador(
    campaign_id: UUID,
    ambassador_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> MessageResponse:
    remove_campaign_ambassador(
        db, user=user, campaign_id=campaign_id, ambassador_id=ambassador_id
    )
    return MessageResponse(message="Ambassador removed from campaign")


@router.get(
    "/events/{event_id}/campaign",
    response_model=AmbassadorCampaignPublic,
)
def host_event_campaign(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> AmbassadorCampaignPublic:
    row = get_event_campaign(db, user=user, event_id=event_id)
    if row is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="No Ambassadors campaign for this event")
    return AmbassadorCampaignPublic.model_validate(row)


@router.get(
    "/events/{event_id}/campaigns",
    response_model=list[AmbassadorCampaignPublic],
)
def host_event_campaigns(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[AmbassadorCampaignPublic]:
    from app.events.service import assert_can_manage_event, get_event_by_id
    from app.hosts.service import require_user_host
    from fastapi import HTTPException

    host = require_user_host(db, user)
    event = get_event_by_id(db, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    assert_can_manage_event(db, user, event, host)
    rows = list_event_open_campaigns(db, event_id=event.id)
    return [
        AmbassadorCampaignPublic.model_validate(serialize_campaign(db, c))
        for c in rows
    ]


@router.get(
    "/events/{event_id}/ambassadors/program",
    response_model=OpenAmbassadorProgramPublic,
)
def open_ambassador_program(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> OpenAmbassadorProgramPublic:
    return OpenAmbassadorProgramPublic.model_validate(
        get_open_ambassador_program(db, event_id=event_id)
    )


@router.post(
    "/events/{event_id}/ambassadors/join",
    response_model=AmbassadorPublic,
    status_code=status.HTTP_201_CREATED,
)
def join_event_ambassador(
    event_id: UUID,
    payload: OpenAmbassadorJoinRequest,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> AmbassadorPublic:
    return AmbassadorPublic.model_validate(
        join_open_event_ambassador(
            db,
            user=user,
            event_id=event_id,
            accept_terms=payload.accept_terms,
            campaign_type=payload.campaign_type,
            campaign_id=payload.campaign_id,
        )
    )


@router.get(
    "/events/{event_id}/ambassadors/me",
    response_model=AmbassadorPublic,
)
def my_event_ambassador(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    campaign_type: str | None = None,
) -> AmbassadorPublic:
    return AmbassadorPublic.model_validate(
        get_my_open_event_ambassador(
            db,
            user=user,
            event_id=event_id,
            campaign_type=campaign_type,
        )
    )


@router.post(
    "/events/{event_id}/ambassadors/leave",
    response_model=MessageResponse,
)
def leave_event_ambassador(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> MessageResponse:
    leave_open_event_ambassador(db, user=user, event_id=event_id)
    return MessageResponse(message="Left Event Ambassadors")


@router.get("/ambassadors", response_model=list[AmbassadorPublic])
def host_ambassadors(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[AmbassadorPublic]:
    return [AmbassadorPublic.model_validate(a) for a in list_host_ambassadors(db, user)]


@router.post(
    "/ambassadors",
    response_model=AmbassadorPublic,
    status_code=status.HTTP_201_CREATED,
)
def create_host_ambassador(
    payload: AmbassadorCreate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> AmbassadorPublic:
    return AmbassadorPublic.model_validate(
        create_ambassador(db, user=user, payload=payload)
    )


@router.get("/ambassadors/{ambassador_id}", response_model=AmbassadorHostDashboard)
def host_ambassador_detail(
    ambassador_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> AmbassadorHostDashboard:
    return AmbassadorHostDashboard.model_validate(
        get_host_ambassador_detail(db, user=user, ambassador_id=ambassador_id)
    )


@router.patch("/ambassadors/{ambassador_id}", response_model=AmbassadorPublic)
def patch_host_ambassador(
    ambassador_id: UUID,
    payload: AmbassadorUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> AmbassadorPublic:
    return AmbassadorPublic.model_validate(
        update_ambassador(db, user=user, ambassador_id=ambassador_id, payload=payload)
    )


@router.delete("/ambassadors/{ambassador_id}", response_model=MessageResponse)
def remove_host_ambassador(
    ambassador_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> MessageResponse:
    delete_ambassador(db, user=user, ambassador_id=ambassador_id)
    return MessageResponse(message="Ambassador deleted")


@router.get("/ambassador/me", response_model=AmbassadorSelfDashboard)
def my_ambassador_dashboard(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> AmbassadorSelfDashboard:
    return AmbassadorSelfDashboard.model_validate(
        get_my_ambassador_dashboard(db, user)
    )


@router.get("/ambassador/enrollments", response_model=AmbassadorEnrollmentList)
def my_ambassador_enrollments(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> AmbassadorEnrollmentList:
    rows = list_my_ambassador_enrollments(db, user)
    return AmbassadorEnrollmentList(
        enrollments=[AmbassadorSelfDashboard.model_validate(r) for r in rows]
    )


@router.get("/ambassador/earnings-summary", response_model=AmbassadorEarningsSummary)
def my_ambassador_earnings_summary(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> AmbassadorEarningsSummary:
    return AmbassadorEarningsSummary.model_validate(
        get_my_ambassador_earnings_summary(db, user)
    )
