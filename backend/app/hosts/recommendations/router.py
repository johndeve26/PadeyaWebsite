"""Host recommendation routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser
from app.core.database import get_db
from app.hosts.recommendations import service as rec_svc
from app.hosts.recommendations.schemas import (
    DismissHostRecommendationBody,
    HideHostCategoryBody,
    HostRecommendationActionPublic,
    HostRecommendationImpressionsBody,
    HostRecommendationImpressionsPublic,
    HostRecommendationsPublic,
)

router = APIRouter(prefix="/recommendations", tags=["host-recommendations"])


@router.get("", response_model=HostRecommendationsPublic)
def list_host_recommendations(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=50)] = 12,
    page: Annotated[int, Query(ge=1)] = 1,
) -> HostRecommendationsPublic:
    payload = rec_svc.list_recommendations(db, user, limit=limit, page=page)
    return HostRecommendationsPublic.model_validate(payload)


@router.post("/impressions", response_model=HostRecommendationImpressionsPublic)
def record_host_recommendation_impressions(
    body: HostRecommendationImpressionsBody,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> HostRecommendationImpressionsPublic:
    payload = rec_svc.record_impressions(
        db,
        user,
        [item.model_dump() for item in body.items],
    )
    return HostRecommendationImpressionsPublic.model_validate(payload)


@router.post("/hide-category", response_model=HostRecommendationActionPublic)
def hide_host_category(
    body: HideHostCategoryBody,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> HostRecommendationActionPublic:
    rec_svc.hide_category(db, user, body.category_slug)
    return HostRecommendationActionPublic(ok=True, category_slug=body.category_slug)


@router.post("/{host_id}/dismiss", response_model=HostRecommendationActionPublic)
def dismiss_host_recommendation(
    host_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    body: DismissHostRecommendationBody | None = None,
) -> HostRecommendationActionPublic:
    reason = body.reason if body else None
    rec_svc.dismiss_recommendation(db, user, host_id, reason=reason)
    return HostRecommendationActionPublic(ok=True, host_id=host_id)


@router.post("/{host_id}/not-interested", response_model=HostRecommendationActionPublic)
def not_interested_host(
    host_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> HostRecommendationActionPublic:
    rec_svc.not_interested(db, user, host_id)
    return HostRecommendationActionPublic(ok=True, host_id=host_id)


@router.post("/{host_id}/more-like-this", response_model=HostRecommendationActionPublic)
def more_like_host(
    host_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> HostRecommendationActionPublic:
    rec_svc.more_like_this(db, user, host_id)
    return HostRecommendationActionPublic(ok=True, host_id=host_id)


@router.post("/{host_id}/click", response_model=HostRecommendationActionPublic)
def click_host_recommendation(
    host_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> HostRecommendationActionPublic:
    rec_svc.record_click(db, user, host_id)
    return HostRecommendationActionPublic(ok=True, host_id=host_id)


@router.post("/{host_id}/follow", response_model=HostRecommendationActionPublic)
def follow_host_recommendation_feedback(
    host_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> HostRecommendationActionPublic:
    rec_svc.record_follow_feedback(db, user, host_id)
    return HostRecommendationActionPublic(ok=True, host_id=host_id)
