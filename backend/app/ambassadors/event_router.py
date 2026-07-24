"""Event-scoped Ambassadors routes — /api/v1/events/{slug}/ambassador*"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.ambassadors import service as svc
from app.ambassadors.schemas import (
    AmbassadorJoinRequest,
    EventAmbassadorLinkPublic,
    EventAmbassadorStatusPublic,
    ParticipantPublic,
)
from app.auth.dependencies import CurrentUser, get_current_user_optional
from app.core.database import get_db
from app.users.models import User

router = APIRouter(prefix="/events", tags=["ambassadors-events"])


@router.get(
    "/{slug}/ambassador-status",
    response_model=EventAmbassadorStatusPublic,
)
def ambassador_status(
    slug: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> EventAmbassadorStatusPublic:
    return EventAmbassadorStatusPublic.model_validate(
        svc.event_ambassador_status(db, slug=slug, user=user)
    )


@router.post(
    "/{slug}/ambassador/join",
    response_model=ParticipantPublic,
)
def ambassador_join(
    slug: str,
    payload: AmbassadorJoinRequest,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> ParticipantPublic:
    return ParticipantPublic.model_validate(
        svc.join_event_by_slug(
            db,
            user=user,
            slug=slug,
            accept_terms=payload.accept_terms,
        )
    )


@router.get(
    "/{slug}/ambassador/link",
    response_model=EventAmbassadorLinkPublic,
)
def ambassador_link(
    slug: str,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> EventAmbassadorLinkPublic:
    return EventAmbassadorLinkPublic.model_validate(
        svc.event_ambassador_link(db, user=user, slug=slug)
    )
