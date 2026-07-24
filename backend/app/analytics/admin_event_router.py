"""Admin per-event analytics routes.

Paths:
  GET /api/v1/admin/events/{event_id}/analytics
  GET /api/v1/admin/analytics/events/leaderboard
  GET /api/v1/admin/analytics/events/compare
  GET /api/v1/admin/analytics/events/export
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.analytics.event_detail_schemas import (
    AdminChannelPerformance,
    AdminEventAnalyticsBundle,
    AdminEventCompare,
    AdminEventLeaderboard,
    EventAnalyticsAmbassadors,
    EventAnalyticsAudience,
    EventAnalyticsFunnel,
    EventAnalyticsPromos,
    EventAnalyticsTimeseries,
)
from app.analytics.service import (
    export_admin_event_analytics_csv,
    export_admin_events_analytics_csv,
    get_admin_channel_performance,
    get_admin_event_ambassadors,
    get_admin_event_analytics,
    get_admin_event_audience,
    get_admin_event_compare,
    get_admin_event_funnel,
    get_admin_event_leaderboard,
    get_admin_event_promos,
    get_admin_event_timeseries,
)
from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.users.models import User

router = APIRouter(prefix="/admin", tags=["admin-analytics"])


def _filter_params(
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    source: str | None = Query(default=None),
    medium: str | None = Query(default=None),
    campaign: str | None = Query(default=None),
    ticket_type_id: UUID | None = Query(default=None),
    device_type: str | None = Query(default=None),
    city: str | None = Query(default=None),
    include_bots: bool = Query(default=False),
) -> dict:
    return {
        "date_from": date_from,
        "date_to": date_to,
        "source": source,
        "medium": medium,
        "campaign": campaign,
        "ticket_type_id": ticket_type_id,
        "device_type": device_type,
        "city": city,
        "include_bots": include_bots,
    }


@router.get(
    "/events/{event_id}/analytics",
    response_model=AdminEventAnalyticsBundle,
)
def api_admin_event_analytics(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("analytics.view_platform", "admin.full_access"))
    ],
    filters: Annotated[dict, Depends(_filter_params)],
) -> AdminEventAnalyticsBundle:
    return AdminEventAnalyticsBundle.model_validate(
        get_admin_event_analytics(db, user=user, event_id=event_id, **filters)
    )


@router.get(
    "/events/{event_id}/analytics/funnel",
    response_model=EventAnalyticsFunnel,
)
def api_admin_event_funnel(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("analytics.view_platform", "admin.full_access"))
    ],
    filters: Annotated[dict, Depends(_filter_params)],
) -> EventAnalyticsFunnel:
    return EventAnalyticsFunnel.model_validate(
        get_admin_event_funnel(db, user=user, event_id=event_id, **filters)
    )


@router.get(
    "/events/{event_id}/analytics/timeseries",
    response_model=EventAnalyticsTimeseries,
)
def api_admin_event_timeseries(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("analytics.view_platform", "admin.full_access"))
    ],
    filters: Annotated[dict, Depends(_filter_params)],
) -> EventAnalyticsTimeseries:
    return EventAnalyticsTimeseries.model_validate(
        get_admin_event_timeseries(db, user=user, event_id=event_id, **filters)
    )


@router.get(
    "/events/{event_id}/analytics/audience",
    response_model=EventAnalyticsAudience,
)
def api_admin_event_audience(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("analytics.view_platform", "admin.full_access"))
    ],
    filters: Annotated[dict, Depends(_filter_params)],
) -> EventAnalyticsAudience:
    return EventAnalyticsAudience.model_validate(
        get_admin_event_audience(db, user=user, event_id=event_id, **filters)
    )


@router.get(
    "/events/{event_id}/analytics/promos",
    response_model=EventAnalyticsPromos,
)
def api_admin_event_promos(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("analytics.view_platform", "admin.full_access"))
    ],
    filters: Annotated[dict, Depends(_filter_params)],
) -> EventAnalyticsPromos:
    return EventAnalyticsPromos.model_validate(
        get_admin_event_promos(db, user=user, event_id=event_id, **filters)
    )


@router.get(
    "/events/{event_id}/analytics/ambassadors",
    response_model=EventAnalyticsAmbassadors,
)
def api_admin_event_ambassadors(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("analytics.view_platform", "admin.full_access"))
    ],
    filters: Annotated[dict, Depends(_filter_params)],
) -> EventAnalyticsAmbassadors:
    return EventAnalyticsAmbassadors.model_validate(
        get_admin_event_ambassadors(db, user=user, event_id=event_id, **filters)
    )


@router.get("/events/{event_id}/analytics/export")
def api_admin_event_export(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("analytics.export", "admin.full_access"))
    ],
    filters: Annotated[dict, Depends(_filter_params)],
) -> Response:
    csv_text = export_admin_event_analytics_csv(
        db, user=user, event_id=event_id, **filters
    )
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="admin-event-{event_id}-analytics.csv"'
        },
    )


@router.get(
    "/analytics/events/leaderboard",
    response_model=AdminEventLeaderboard,
)
def api_admin_event_leaderboard(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("analytics.view_platform", "admin.full_access"))
    ],
    filters: Annotated[dict, Depends(_filter_params)],
    sort_by: str = Query(default="revenue"),
    limit: int = Query(default=50, ge=1, le=200),
) -> AdminEventLeaderboard:
    return AdminEventLeaderboard.model_validate(
        get_admin_event_leaderboard(
            db, user=user, sort_by=sort_by, limit=limit, **filters
        )
    )


@router.get(
    "/analytics/events/channels",
    response_model=AdminChannelPerformance,
)
def api_admin_event_channels(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("analytics.view_platform", "admin.full_access"))
    ],
    filters: Annotated[dict, Depends(_filter_params)],
) -> AdminChannelPerformance:
    return AdminChannelPerformance.model_validate(
        get_admin_channel_performance(db, user=user, **filters)
    )


@router.get(
    "/analytics/events/compare",
    response_model=AdminEventCompare,
)
def api_admin_event_compare(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("analytics.view_platform", "admin.full_access"))
    ],
    filters: Annotated[dict, Depends(_filter_params)],
    event_ids: list[UUID] = Query(default=[]),
) -> AdminEventCompare:
    return AdminEventCompare.model_validate(
        get_admin_event_compare(db, user=user, event_ids=event_ids, **filters)
    )


@router.get("/analytics/events/export")
def api_admin_events_export(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("analytics.export", "admin.full_access"))
    ],
    filters: Annotated[dict, Depends(_filter_params)],
    sort_by: str = Query(default="revenue"),
    limit: int = Query(default=200, ge=1, le=500),
) -> Response:
    csv_text = export_admin_events_analytics_csv(
        db, user=user, sort_by=sort_by, limit=limit, **filters
    )
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="admin-events-analytics.csv"'
        },
    )
