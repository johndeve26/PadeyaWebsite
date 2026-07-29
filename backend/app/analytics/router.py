"""Analytics API routes — tracking, host/admin dashboards, CSV export."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user_optional, require_permission
from app.core.database import get_db
from app.analytics.rate_limit import rate_limit_analytics_track
from app.analytics.schemas import (
    AdminEventsSummary,
    AdminHostsSummary,
    AdminPlatformSummary,
    AdminRevenueSummary,
    AdminSupportSummary,
    AdminBlogAnalyticsSummary,
    AdminBlogPostAnalytics,
    EventAnalyticsSummary,
    HostAnalyticsSummary,
    TrackAccepted,
    TrackBatchRequest,
    TrackBatchResponse,
    TrackClickRequest,
    TrackConversionRequest,
    TrackEventRequest,
    TrackImpressionRequest,
    TrackPageViewRequest,
)
from app.analytics.service import (
    export_admin_analytics_csv,
    export_host_analytics_csv,
    get_admin_blog_analytics,
    get_admin_blog_post_analytics,
    get_admin_events,
    get_admin_hosts,
    get_admin_revenue,
    get_admin_summary,
    get_admin_support,
    get_host_analytics,
    get_host_event_analytics,
    track_batch,
    track_click,
    track_conversion,
    track_event,
    track_impression,
    track_page_view,
    track_public,
)
from app.users.models import User

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


def _with_request_ua(payload: TrackEventRequest | TrackPageViewRequest | TrackImpressionRequest | TrackClickRequest | TrackConversionRequest, request: Request):
    if not payload.user_agent:
        ua = request.headers.get("user-agent")
        if ua:
            object.__setattr__(payload, "user_agent", ua[:500])
    return payload


@router.get("/health")
async def analytics_module_health() -> dict[str, str]:
    return {"module": "analytics", "status": "ok"}


# --- Public / optional-auth tracking ---


@router.post(
    "/track",
    response_model=TrackAccepted,
    dependencies=[Depends(rate_limit_analytics_track)],
)
def api_track(
    payload: TrackEventRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> TrackAccepted:
    """Unified client track endpoint. Validates taxonomy; rejects trusted actions."""
    _with_request_ua(payload, request)
    return TrackAccepted.model_validate(
        track_public(
            db,
            payload=payload,
            user=user,
            client_ip=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
            referrer=request.headers.get("referer") or request.headers.get("referrer"),
        )
    )


@router.post(
    "/track/batch",
    response_model=TrackBatchResponse,
    dependencies=[Depends(rate_limit_analytics_track)],
)
def api_track_batch(
    payload: TrackBatchRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> TrackBatchResponse:
    """Batch client track — same enrichment/security as ``/track``."""
    return track_batch(
        db,
        payload=payload,
        user=user,
        client_ip=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
        referrer=request.headers.get("referer") or request.headers.get("referrer"),
    )


@router.post("/track/event", response_model=TrackAccepted)
def api_track_event(
    payload: TrackEventRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> TrackAccepted:
    _with_request_ua(payload, request)
    return TrackAccepted.model_validate(
        track_event(db, payload=payload, user=user, client_ip=_client_ip(request))
    )


@router.post("/track/page-view", response_model=TrackAccepted)
def api_track_page_view(
    payload: TrackPageViewRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> TrackAccepted:
    _with_request_ua(payload, request)
    return TrackAccepted.model_validate(
        track_page_view(db, payload=payload, user=user, client_ip=_client_ip(request))
    )


@router.post("/track/impression", response_model=TrackAccepted)
def api_track_impression(
    payload: TrackImpressionRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> TrackAccepted:
    _with_request_ua(payload, request)
    return TrackAccepted.model_validate(
        track_impression(db, payload=payload, user=user, client_ip=_client_ip(request))
    )


@router.post("/track/click", response_model=TrackAccepted)
def api_track_click(
    payload: TrackClickRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> TrackAccepted:
    _with_request_ua(payload, request)
    return TrackAccepted.model_validate(
        track_click(db, payload=payload, user=user, client_ip=_client_ip(request))
    )


@router.post("/track/conversion", response_model=TrackAccepted)
def api_track_conversion(
    payload: TrackConversionRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> TrackAccepted:
    _with_request_ua(payload, request)
    return TrackAccepted.model_validate(
        track_conversion(db, payload=payload, user=user, client_ip=_client_ip(request))
    )


# --- Host analytics ---


@router.get("/host/summary", response_model=HostAnalyticsSummary)
def api_host_summary(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    range_start: datetime | None = None,
    range_end: datetime | None = None,
    include_bots: bool = False,
) -> HostAnalyticsSummary:
    return HostAnalyticsSummary.model_validate(
        get_host_analytics(
            db,
            user=user,
            range_start=range_start,
            range_end=range_end,
            include_bots=include_bots,
        )
    )


@router.get("/host/events/{event_id}", response_model=EventAnalyticsSummary)
def api_host_event(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    range_start: datetime | None = None,
    range_end: datetime | None = None,
    include_bots: bool = False,
) -> EventAnalyticsSummary:
    return EventAnalyticsSummary.model_validate(
        get_host_event_analytics(
            db,
            user=user,
            event_id=event_id,
            range_start=range_start,
            range_end=range_end,
            include_bots=include_bots,
        )
    )


@router.get("/host/export.csv")
def api_host_export(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    range_start: datetime | None = None,
    range_end: datetime | None = None,
) -> Response:
    csv_text = export_host_analytics_csv(
        db, user=user, range_start=range_start, range_end=range_end
    )
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=host-analytics.csv"},
    )


# --- Admin analytics ---


@router.get("/admin/summary", response_model=AdminPlatformSummary)
def api_admin_summary(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User,
        Depends(require_permission("analytics.view_platform", "admin.full_access")),
    ],
    range_start: datetime | None = None,
    range_end: datetime | None = None,
) -> AdminPlatformSummary:
    return AdminPlatformSummary.model_validate(
        get_admin_summary(db, user=user, range_start=range_start, range_end=range_end)
    )


@router.get("/admin/revenue", response_model=AdminRevenueSummary)
def api_admin_revenue(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User,
        Depends(require_permission("analytics.view_platform", "admin.full_access")),
    ],
    range_start: datetime | None = None,
    range_end: datetime | None = None,
) -> AdminRevenueSummary:
    return AdminRevenueSummary.model_validate(
        get_admin_revenue(db, user=user, range_start=range_start, range_end=range_end)
    )


@router.get("/admin/events", response_model=AdminEventsSummary)
def api_admin_events(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User,
        Depends(require_permission("analytics.view_platform", "admin.full_access")),
    ],
    range_start: datetime | None = None,
    range_end: datetime | None = None,
) -> AdminEventsSummary:
    return AdminEventsSummary.model_validate(
        get_admin_events(db, user=user, range_start=range_start, range_end=range_end)
    )


@router.get("/admin/hosts", response_model=AdminHostsSummary)
def api_admin_hosts(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User,
        Depends(require_permission("analytics.view_platform", "admin.full_access")),
    ],
    range_start: datetime | None = None,
    range_end: datetime | None = None,
) -> AdminHostsSummary:
    return AdminHostsSummary.model_validate(
        get_admin_hosts(db, user=user, range_start=range_start, range_end=range_end)
    )


@router.get("/admin/support", response_model=AdminSupportSummary)
def api_admin_support(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User,
        Depends(require_permission("analytics.view_platform", "admin.full_access")),
    ],
) -> AdminSupportSummary:
    return AdminSupportSummary.model_validate(get_admin_support(db, user=user))


@router.get("/admin/blog", response_model=AdminBlogAnalyticsSummary)
def api_admin_blog_analytics(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User,
        Depends(
            require_permission(
                "analytics.view_platform",
                "admin.blog.view",
                "admin.full_access",
            )
        ),
    ],
    range_start: datetime | None = None,
    range_end: datetime | None = None,
    include_internal: bool = False,
) -> AdminBlogAnalyticsSummary:
    return AdminBlogAnalyticsSummary.model_validate(
        get_admin_blog_analytics(
            db,
            user=user,
            range_start=range_start,
            range_end=range_end,
            include_internal=include_internal,
        )
    )


@router.get("/admin/blog/posts/{post_id}", response_model=AdminBlogPostAnalytics)
def api_admin_blog_post_analytics(
    post_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User,
        Depends(
            require_permission(
                "analytics.view_platform",
                "admin.blog.view",
                "admin.full_access",
            )
        ),
    ],
    range_start: datetime | None = None,
    range_end: datetime | None = None,
    include_internal: bool = False,
) -> AdminBlogPostAnalytics:
    return AdminBlogPostAnalytics.model_validate(
        get_admin_blog_post_analytics(
            db,
            user=user,
            post_id=post_id,
            range_start=range_start,
            range_end=range_end,
            include_internal=include_internal,
        )
    )


@router.get("/admin/export.csv")
def api_admin_export(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User,
        Depends(require_permission("analytics.export", "admin.full_access")),
    ],
    range_start: datetime | None = None,
    range_end: datetime | None = None,
) -> Response:
    csv_text = export_admin_analytics_csv(
        db, user=user, range_start=range_start, range_end=range_end
    )
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=platform-analytics.csv"},
    )
