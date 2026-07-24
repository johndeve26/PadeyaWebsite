"""User + admin appeal APIs."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.appeals import service as appeals_service
from app.appeals.suspension_notify import AUDIT_APPEAL_SUBMITTED  # noqa: F401
from app.auth.dependencies import get_current_user, require_permission
from app.core.database import get_db
from app.users.admin_user_audit import client_request_meta
from app.users.models import User

router = APIRouter(tags=["appeals"])

_REVIEW = require_permission("admin.appeals.review", "admin.users.suspend")


class AppealCreateBody(BaseModel):
    message: str = Field(min_length=10, max_length=4000)


class AppealReviewBody(BaseModel):
    admin_reply: str | None = Field(default=None, max_length=1000)


@router.get("/me/suspension")
def my_suspension(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Public-safe active suspension for the signed-in user."""
    row = appeals_service.get_active_suspension(db, user.id)
    if row is None:
        return {"suspension": None, "pending_appeal": None}
    from sqlalchemy import select

    from app.appeals.models import APPEAL_STATUS_PENDING, AccountAppeal

    pending = db.scalar(
        select(AccountAppeal).where(
            AccountAppeal.suspension_id == row.id,
            AccountAppeal.status == APPEAL_STATUS_PENDING,
        )
    )
    return {
        "suspension": appeals_service.serialize_suspension_public(row),
        "pending_appeal": (
            appeals_service.serialize_appeal(pending) if pending else None
        ),
    }


@router.post("/appeals")
def create_appeal(
    payload: AppealCreateBody,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> dict:
    ip, ua = client_request_meta(request)
    appeal = appeals_service.submit_appeal(
        db,
        user=user,
        message=payload.message,
        ip_address=ip,
        user_agent=ua,
    )
    return appeals_service.serialize_appeal(appeal)


@router.get("/admin/appeals")
def admin_list_appeals(
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(_REVIEW)],
    status: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(40, ge=1, le=100),
) -> dict:
    return appeals_service.list_appeals_admin(
        db, status=status, page=page, limit=limit
    )


@router.get("/admin/appeals/{appeal_id}")
def admin_get_appeal(
    appeal_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(_REVIEW)],
) -> dict:
    return appeals_service.get_appeal_admin(db, appeal_id)


@router.post("/admin/appeals/{appeal_id}/approve")
def admin_approve_appeal(
    appeal_id: UUID,
    payload: AppealReviewBody,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(_REVIEW)],
) -> dict:
    ip, ua = client_request_meta(request)
    return appeals_service.approve_appeal(
        db,
        admin=admin,
        appeal_id=appeal_id,
        admin_reply=payload.admin_reply,
        ip_address=ip,
        user_agent=ua,
    )


@router.post("/admin/appeals/{appeal_id}/reject")
def admin_reject_appeal(
    appeal_id: UUID,
    payload: AppealReviewBody,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(_REVIEW)],
) -> dict:
    ip, ua = client_request_meta(request)
    return appeals_service.reject_appeal(
        db,
        admin=admin,
        appeal_id=appeal_id,
        admin_reply=payload.admin_reply,
        ip_address=ip,
        user_agent=ua,
    )
