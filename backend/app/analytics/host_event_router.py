"""Host per-event analytics routes.

Paths:
  GET /api/v1/host/events/{event_id}/analytics/...
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.analytics.event_detail_schemas import (
    EventAnalyticsAmbassadors,
    EventAnalyticsAudience,
    EventAnalyticsFunnel,
    EventAnalyticsOverview,
    EventAnalyticsPromos,
    EventAnalyticsSources,
    EventAnalyticsTickets,
    EventAnalyticsTimeseries,
)
from app.analytics.service import (
    export_host_event_analytics_csv,
    get_host_event_ambassadors,
    get_host_event_audience,
    get_host_event_funnel,
    get_host_event_overview,
    get_host_event_promos,
    get_host_event_sources,
    get_host_event_tickets,
    get_host_event_timeseries,
)
from app.auth.dependencies import CurrentUser
from app.core.database import get_db

router = APIRouter(prefix="/host/events", tags=["host-analytics"])


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
    "/{event_id}/analytics/overview",
    response_model=EventAnalyticsOverview,
)
def api_host_event_overview(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    filters: Annotated[dict, Depends(_filter_params)],
) -> EventAnalyticsOverview:
    return EventAnalyticsOverview.model_validate(
        get_host_event_overview(db, user=user, event_id=event_id, **filters)
    )


@router.get(
    "/{event_id}/analytics/funnel",
    response_model=EventAnalyticsFunnel,
)
def api_host_event_funnel(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    filters: Annotated[dict, Depends(_filter_params)],
) -> EventAnalyticsFunnel:
    return EventAnalyticsFunnel.model_validate(
        get_host_event_funnel(db, user=user, event_id=event_id, **filters)
    )


@router.get(
    "/{event_id}/analytics/timeseries",
    response_model=EventAnalyticsTimeseries,
)
def api_host_event_timeseries(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    filters: Annotated[dict, Depends(_filter_params)],
) -> EventAnalyticsTimeseries:
    return EventAnalyticsTimeseries.model_validate(
        get_host_event_timeseries(db, user=user, event_id=event_id, **filters)
    )


@router.get(
    "/{event_id}/analytics/sources",
    response_model=EventAnalyticsSources,
)
def api_host_event_sources(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    filters: Annotated[dict, Depends(_filter_params)],
) -> EventAnalyticsSources:
    return EventAnalyticsSources.model_validate(
        get_host_event_sources(db, user=user, event_id=event_id, **filters)
    )


@router.get(
    "/{event_id}/analytics/tickets",
    response_model=EventAnalyticsTickets,
)
def api_host_event_tickets(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    filters: Annotated[dict, Depends(_filter_params)],
) -> EventAnalyticsTickets:
    return EventAnalyticsTickets.model_validate(
        get_host_event_tickets(db, user=user, event_id=event_id, **filters)
    )


@router.get(
    "/{event_id}/analytics/audience",
    response_model=EventAnalyticsAudience,
)
def api_host_event_audience(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    filters: Annotated[dict, Depends(_filter_params)],
) -> EventAnalyticsAudience:
    return EventAnalyticsAudience.model_validate(
        get_host_event_audience(db, user=user, event_id=event_id, **filters)
    )


@router.get(
    "/{event_id}/analytics/promos",
    response_model=EventAnalyticsPromos,
)
def api_host_event_promos(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    filters: Annotated[dict, Depends(_filter_params)],
) -> EventAnalyticsPromos:
    return EventAnalyticsPromos.model_validate(
        get_host_event_promos(db, user=user, event_id=event_id, **filters)
    )


@router.get(
    "/{event_id}/analytics/ambassadors",
    response_model=EventAnalyticsAmbassadors,
)
def api_host_event_ambassadors(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    filters: Annotated[dict, Depends(_filter_params)],
) -> EventAnalyticsAmbassadors:
    return EventAnalyticsAmbassadors.model_validate(
        get_host_event_ambassadors(db, user=user, event_id=event_id, **filters)
    )


@router.get("/{event_id}/analytics/export")
def api_host_event_export(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    filters: Annotated[dict, Depends(_filter_params)],
) -> Response:
    csv_text = export_host_event_analytics_csv(
        db, user=user, event_id=event_id, **filters
    )
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="event-{event_id}-analytics.csv"'
        },
    )
