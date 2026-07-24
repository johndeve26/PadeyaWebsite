"""Host CRM and audience API."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser
from app.core.database import get_db
from app.crm.schemas import (
    AnnouncementCreate,
    AnnouncementDispatchResult,
    AnnouncementPublic,
    AnnouncementUpdate,
    AudienceMemberPublic,
    AudienceSegmentCreate,
    AudienceSegmentPublic,
    AudienceStatsPublic,
    FollowRequest,
    FollowingHostPublic,
    MarketingOptInUpdate,
)
from app.crm.service import (
    archive_announcement,
    cancel_announcement,
    create_announcement,
    create_segment,
    delete_segment,
    dispatch_announcement_email,
    follow_host,
    get_announcement,
    host_audience_dashboard,
    list_announcements,
    list_audience_members,
    list_host_followers,
    list_my_following,
    list_segments,
    unfollow_host,
    update_announcement,
    update_marketing_opt_in,
)
from app.events.schemas import MessageResponse

router = APIRouter(prefix="/crm", tags=["crm"])


@router.get("/health")
async def crm_module_health() -> dict[str, str]:
    return {"module": "crm", "status": "ok"}


@router.post("/follow", response_model=FollowingHostPublic, status_code=status.HTTP_201_CREATED)
def follow(
    payload: FollowRequest,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> FollowingHostPublic:
    return FollowingHostPublic.model_validate(follow_host(db, user=user, payload=payload))


@router.delete("/follow/{host_id}", status_code=status.HTTP_204_NO_CONTENT)
def unfollow(
    host_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> None:
    unfollow_host(db, user=user, host_id=host_id)


@router.get("/me/following", response_model=list[FollowingHostPublic])
def my_following(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[FollowingHostPublic]:
    return [FollowingHostPublic.model_validate(r) for r in list_my_following(db, user)]


@router.patch("/me/following/{host_id}", response_model=FollowingHostPublic)
def patch_marketing_opt_in(
    host_id: UUID,
    payload: MarketingOptInUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> FollowingHostPublic:
    return FollowingHostPublic.model_validate(
        update_marketing_opt_in(
            db,
            user=user,
            host_id=host_id,
            marketing_opt_in=payload.marketing_opt_in,
        )
    )


@router.get("/host/audience", response_model=AudienceStatsPublic)
def audience_dashboard(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> AudienceStatsPublic:
    return AudienceStatsPublic.model_validate(host_audience_dashboard(db, user))


@router.get("/host/followers", response_model=list[AudienceMemberPublic])
def host_followers(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[AudienceMemberPublic]:
    return [AudienceMemberPublic.model_validate(m) for m in list_host_followers(db, user)]


@router.get("/host/audience/members", response_model=list[AudienceMemberPublic])
def audience_members(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    segment_key: str | None = Query(default=None),
    segment_id: UUID | None = Query(default=None),
    event_id: UUID | None = Query(default=None),
    ticket_type_id: UUID | None = Query(default=None),
    check_in_status: str | None = Query(default=None),
) -> list[AudienceMemberPublic]:
    return [
        AudienceMemberPublic.model_validate(m)
        for m in list_audience_members(
            db,
            user,
            segment_key=segment_key,
            segment_id=segment_id,
            event_id=event_id,
            ticket_type_id=ticket_type_id,
            check_in_status=check_in_status,
        )
    ]


@router.get("/host/segments", response_model=list[AudienceSegmentPublic])
def host_segments(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[AudienceSegmentPublic]:
    return [AudienceSegmentPublic.model_validate(s) for s in list_segments(db, user)]


@router.post(
    "/host/segments",
    response_model=AudienceSegmentPublic,
    status_code=status.HTTP_201_CREATED,
)
def create_host_segment(
    payload: AudienceSegmentCreate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> AudienceSegmentPublic:
    return AudienceSegmentPublic.model_validate(
        create_segment(db, user=user, payload=payload)
    )


@router.delete(
    "/host/segments/{segment_id}",
    response_model=MessageResponse,
)
def delete_host_segment(
    segment_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> MessageResponse:
    delete_segment(db, user=user, segment_id=segment_id)
    return MessageResponse(message="Segment deleted")


@router.get("/host/announcements", response_model=list[AnnouncementPublic])
def host_announcements(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[AnnouncementPublic]:
    return [AnnouncementPublic.model_validate(a) for a in list_announcements(db, user)]


@router.post(
    "/host/announcements",
    response_model=AnnouncementPublic,
    status_code=status.HTTP_201_CREATED,
)
def create_host_announcement(
    payload: AnnouncementCreate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> AnnouncementPublic:
    return AnnouncementPublic.model_validate(
        create_announcement(db, user=user, payload=payload)
    )


@router.get("/host/announcements/{announcement_id}", response_model=AnnouncementPublic)
def get_host_announcement(
    announcement_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> AnnouncementPublic:
    return AnnouncementPublic.model_validate(
        get_announcement(db, user=user, announcement_id=announcement_id)
    )


@router.patch(
    "/host/announcements/{announcement_id}",
    response_model=AnnouncementPublic,
)
def patch_host_announcement(
    announcement_id: UUID,
    payload: AnnouncementUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> AnnouncementPublic:
    return AnnouncementPublic.model_validate(
        update_announcement(
            db, user=user, announcement_id=announcement_id, payload=payload
        )
    )


@router.post(
    "/host/announcements/{announcement_id}/dispatch-email",
    response_model=AnnouncementDispatchResult,
)
def dispatch_email(
    announcement_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> AnnouncementDispatchResult:
    return AnnouncementDispatchResult.model_validate(
        dispatch_announcement_email(db, user=user, announcement_id=announcement_id)
    )


@router.post(
    "/host/announcements/{announcement_id}/cancel",
    response_model=AnnouncementPublic,
)
def cancel_host_announcement(
    announcement_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> AnnouncementPublic:
    return AnnouncementPublic.model_validate(
        cancel_announcement(db, user=user, announcement_id=announcement_id)
    )


@router.post(
    "/host/announcements/{announcement_id}/archive",
    response_model=AnnouncementPublic,
)
def archive_host_announcement(
    announcement_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> AnnouncementPublic:
    return AnnouncementPublic.model_validate(
        archive_announcement(db, user=user, announcement_id=announcement_id)
    )
