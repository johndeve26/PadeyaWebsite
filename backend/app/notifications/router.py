"""In-app notification routes (popup / inbox). Push routes live in app.push."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser
from app.core.database import get_db
from app.notifications.schemas import (
    InAppNotificationPublic,
    NotificationListResponse,
    PopupMarkRequest,
)
from app.notifications.service import (
    archive_notification,
    list_user_notifications,
    mark_all_read,
    mark_popup_shown,
    mark_read,
    popup_candidates,
    serialize_notification,
    unread_count,
)

router = APIRouter(tags=["notifications"])


@router.get("/notifications", response_model=NotificationListResponse)
def list_notifications(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    category: Annotated[str | None, Query()] = None,
    unread_only: bool = Query(default=False),
) -> NotificationListResponse:
    rows, total = list_user_notifications(
        db,
        user_id=user.id,
        limit=limit,
        offset=offset,
        category=category,
        unread_only=unread_only,
    )
    return NotificationListResponse(
        items=[InAppNotificationPublic.model_validate(serialize_notification(r)) for r in rows],
        total=total,
        unread_count=unread_count(
            db, user_id=user.id, category=category or "all"
        ),
    )


@router.get("/notifications/unread-count")
def get_unread_count(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict[str, int]:
    return {"unread_count": unread_count(db, user_id=user.id)}


@router.get("/notifications/popup", response_model=NotificationListResponse)
def get_popup_notifications(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    limit: int = Query(default=5, ge=1, le=10),
) -> NotificationListResponse:
    rows = popup_candidates(db, user_id=user.id, limit=limit)
    return NotificationListResponse(
        items=[InAppNotificationPublic.model_validate(serialize_notification(r)) for r in rows],
        total=len(rows),
        unread_count=unread_count(db, user_id=user.id, category="all"),
    )


@router.post("/notifications/popup/ack")
def ack_popup_notifications(
    payload: PopupMarkRequest,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict[str, int]:
    n = mark_popup_shown(db, user_id=user.id, notification_ids=payload.notification_ids)
    db.commit()
    return {"marked": n}


@router.post("/notifications/{notification_id}/read", response_model=InAppNotificationPublic)
def read_notification(
    notification_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> InAppNotificationPublic:
    try:
        row = mark_read(db, user_id=user.id, notification_id=notification_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.commit()
    return InAppNotificationPublic.model_validate(serialize_notification(row))


@router.post("/notifications/read-all")
def read_all_notifications(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict[str, int]:
    n = mark_all_read(db, user_id=user.id)
    db.commit()
    return {"marked": n}


@router.post(
    "/notifications/{notification_id}/archive",
    response_model=InAppNotificationPublic,
)
def archive_one(
    notification_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> InAppNotificationPublic:
    try:
        row = archive_notification(db, user_id=user.id, notification_id=notification_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.commit()
    return InAppNotificationPublic.model_validate(serialize_notification(row))
