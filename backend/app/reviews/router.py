"""Verified reviews API."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, require_permission
from app.core.database import get_db
from app.reviews.schemas import (
    ReviewCreate,
    ReviewEligibility,
    ReviewModerateRequest,
    ReviewPublic,
    ReviewReplyCreate,
    ReviewReportCreate,
    ReviewReportPublic,
    ReviewUpdate,
)
from app.reviews.service import (
    check_eligibility,
    list_host_reviews,
    list_my_reviews,
    list_reported_reviews,
    moderate_review,
    reply_to_review,
    report_review,
    serialize_review,
    submit_review,
    update_review,
    withdraw_review,
)
from app.users.models import User

router = APIRouter(prefix="/reviews", tags=["reviews"])


def _client_meta(request: Request) -> tuple[str | None, str | None]:
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    return ip, ua


@router.get("/health")
async def reviews_module_health() -> dict[str, str]:
    return {"module": "reviews", "status": "ok"}


@router.get("/eligibility", response_model=ReviewEligibility)
def review_eligibility(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    ticket_id: UUID | None = Query(default=None),
    event_id: UUID | None = Query(default=None),
) -> ReviewEligibility:
    return ReviewEligibility.model_validate(
        check_eligibility(db, user=user, ticket_id=ticket_id, event_id=event_id)
    )


@router.post("", response_model=ReviewPublic, status_code=status.HTTP_201_CREATED)
def create_review(
    payload: ReviewCreate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> ReviewPublic:
    ip, ua = _client_meta(request)
    review = submit_review(
        db, user=user, payload=payload, ip_address=ip, user_agent=ua
    )
    return ReviewPublic.model_validate(serialize_review(db, review, include_moderation=True))


@router.get("/me", response_model=list[ReviewPublic])
def my_reviews(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[ReviewPublic]:
    return [ReviewPublic.model_validate(r) for r in list_my_reviews(db, user)]


@router.get("/host/me", response_model=list[ReviewPublic])
def host_reviews(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[ReviewPublic]:
    return [ReviewPublic.model_validate(r) for r in list_host_reviews(db, user)]


@router.patch("/{review_id}", response_model=ReviewPublic)
def patch_review(
    review_id: UUID,
    payload: ReviewUpdate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> ReviewPublic:
    ip, ua = _client_meta(request)
    review = update_review(
        db,
        user=user,
        review_id=review_id,
        payload=payload,
        ip_address=ip,
        user_agent=ua,
    )
    return ReviewPublic.model_validate(
        serialize_review(db, review, include_moderation=True)
    )


@router.post("/{review_id}/reply", response_model=ReviewPublic)
def create_reply(
    review_id: UUID,
    payload: ReviewReplyCreate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> ReviewPublic:
    ip, ua = _client_meta(request)
    review = reply_to_review(
        db,
        user=user,
        review_id=review_id,
        payload=payload,
        ip_address=ip,
        user_agent=ua,
    )
    return ReviewPublic.model_validate(serialize_review(db, review, include_moderation=True))


@router.post("/{review_id}/report", response_model=ReviewReportPublic, status_code=status.HTTP_201_CREATED)
def create_report(
    review_id: UUID,
    payload: ReviewReportCreate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> ReviewReportPublic:
    ip, ua = _client_meta(request)
    report = report_review(
        db,
        user=user,
        review_id=review_id,
        payload=payload,
        ip_address=ip,
        user_agent=ua,
    )
    return ReviewReportPublic.model_validate(
        {
            "id": report.id,
            "review_id": report.review_id,
            "reporter_user_id": report.reporter_user_id,
            "reason": report.reason,
            "status": report.status,
            "created_at": report.created_at,
            "review": None,
        }
    )


@router.delete("/{review_id}", response_model=ReviewPublic)
def delete_review(
    review_id: UUID,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> ReviewPublic:
    """Buyers withdraw (soft). Hosts cannot delete — 403."""
    ip, ua = _client_meta(request)
    review = withdraw_review(
        db, user=user, review_id=review_id, ip_address=ip, user_agent=ua
    )
    return ReviewPublic.model_validate(
        serialize_review(db, review, include_moderation=True)
    )


@router.get(
    "/admin/reported",
    response_model=list[ReviewReportPublic],
    dependencies=[Depends(require_permission("reviews.moderate", "admin.full_access"))],
)
def admin_reported(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("reviews.moderate", "admin.full_access"))],
) -> list[ReviewReportPublic]:
    return [ReviewReportPublic.model_validate(r) for r in list_reported_reviews(db)]


@router.post(
    "/{review_id}/moderate",
    response_model=ReviewPublic,
    dependencies=[Depends(require_permission("reviews.moderate", "admin.full_access"))],
)
def admin_moderate(
    review_id: UUID,
    payload: ReviewModerateRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("reviews.moderate", "admin.full_access"))],
) -> ReviewPublic:
    ip, ua = _client_meta(request)
    review = moderate_review(
        db,
        user=user,
        review_id=review_id,
        payload=payload,
        ip_address=ip,
        user_agent=ua,
    )
    return ReviewPublic.model_validate(serialize_review(db, review, include_moderation=True))
