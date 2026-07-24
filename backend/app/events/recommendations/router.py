"""Fan event recommendation routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser
from app.core.database import get_db
from app.events.recommendations import constants as C
from app.events.recommendations import service as rec_svc
from app.events.recommendations.schemas import (
    EventRecommendationFeedbackBody,
    EventRecommendationFeedbackPublic,
    EventRecommendationImpressionsBody,
    EventRecommendationImpressionsPublic,
    EventRecommendationsPublic,
)

router = APIRouter(prefix="/recommendations", tags=["event-recommendations"])


@router.get("", response_model=EventRecommendationsPublic)
def list_event_recommendations(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=50)] = 12,
    cursor: Annotated[str | None, Query()] = None,
    city: Annotated[str | None, Query()] = None,
    area: Annotated[str | None, Query()] = None,
    category: Annotated[str | None, Query()] = None,
    date_range: Annotated[str | None, Query()] = None,
    mode: Annotated[str, Query()] = C.DEFAULT_MODE,
    exclude_event_id: Annotated[UUID | None, Query()] = None,
    context_event_id: Annotated[UUID | None, Query()] = None,
    host_id: Annotated[UUID | None, Query()] = None,
) -> EventRecommendationsPublic:
    payload = rec_svc.list_recommendations(
        db,
        user,
        limit=limit,
        cursor=cursor,
        city=city,
        area=area,
        category=category,
        date_range=date_range,
        mode=mode,
        exclude_event_id=exclude_event_id,
        context_event_id=context_event_id,
        host_id=host_id,
    )
    return EventRecommendationsPublic.model_validate(payload)


@router.post("/impressions", response_model=EventRecommendationImpressionsPublic)
def record_event_recommendation_impressions(
    body: EventRecommendationImpressionsBody,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> EventRecommendationImpressionsPublic:
    payload = rec_svc.record_impressions(
        db,
        user,
        [item.model_dump() for item in body.items],
    )
    return EventRecommendationImpressionsPublic.model_validate(payload)


@router.post("/{event_id}/feedback", response_model=EventRecommendationFeedbackPublic)
def event_recommendation_feedback(
    event_id: UUID,
    body: EventRecommendationFeedbackBody,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> EventRecommendationFeedbackPublic:
    rec_svc.submit_feedback(
        db,
        user,
        event_id,
        action=body.action,
        category_slug=body.category_slug,
    )
    return EventRecommendationFeedbackPublic(ok=True, event_id=event_id)
