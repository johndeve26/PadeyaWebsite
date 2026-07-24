"""Fan Connect API routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, Response
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.fan_connect import service as svc
from app.fan_connect.schemas import (
    AdminBlockListPublic,
    AdminOverviewPublic,
    AdminReportListPublic,
    BlockBody,
    CanConnectPublic,
    ConnectEventListPublic,
    ConnectionListPublic,
    ConnectionPublic,
    CreateRequestBody,
    DeclineCooldownOptionsPublic,
    DeclineRequestBody,
    DismissSuggestionBody,
    FanConnectSettingsPublic,
    FanConnectSettingsUpdate,
    LocationPreferenceBody,
    LocationPreferencePublic,
    ReportBody,
    ReportPublic,
    SuggestionActionPublic,
    SuggestionsPublic,
)
from app.users.models import User

router = APIRouter(prefix="/fan-connect", tags=["fan-connect"])


@router.get("/settings", response_model=FanConnectSettingsPublic)
def get_settings(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("fan_connect.use"))],
) -> FanConnectSettingsPublic:
    return FanConnectSettingsPublic.model_validate(svc.settings_payload(db, user))


@router.patch("/settings", response_model=FanConnectSettingsPublic)
def patch_settings(
    payload: FanConnectSettingsUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("fan_connect.use"))],
) -> FanConnectSettingsPublic:
    svc.update_settings(db, user, payload)
    return FanConnectSettingsPublic.model_validate(svc.settings_payload(db, user))


@router.get("/can-connect/{username}", response_model=CanConnectPublic)
def can_connect(
    username: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("fan_connect.use"))],
) -> CanConnectPublic:
    return CanConnectPublic.model_validate(svc.can_connect(db, user, username))


@router.post("/requests", response_model=ConnectionPublic)
def create_request(
    payload: CreateRequestBody,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("fan_connect.use"))],
) -> ConnectionPublic:
    conn = svc.create_request(
        db,
        user,
        username=payload.username,
        message=payload.message,
        context_event_id=payload.context_event_id,
    )
    return ConnectionPublic.model_validate(svc.serialize_connection(db, conn, user))


@router.get("/requests", response_model=ConnectionListPublic)
def list_requests(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("fan_connect.use"))],
    box: str = Query(default="incoming", pattern="^(incoming|outgoing)$"),
) -> ConnectionListPublic:
    return ConnectionListPublic.model_validate(svc.list_requests(db, user, box=box))


@router.post("/requests/{connection_id}/accept", response_model=ConnectionPublic)
def accept_request(
    connection_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("fan_connect.use"))],
) -> ConnectionPublic:
    conn = svc.accept_request(db, user, connection_id)
    return ConnectionPublic.model_validate(svc.serialize_connection(db, conn, user))


@router.get("/decline-cooldown-options", response_model=DeclineCooldownOptionsPublic)
def decline_cooldown_options(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("fan_connect.use"))],
) -> DeclineCooldownOptionsPublic:
    data = svc.decline_cooldown_options(db)
    return DeclineCooldownOptionsPublic.model_validate(data)


@router.post("/requests/{connection_id}/decline", response_model=ConnectionPublic)
def decline_request(
    connection_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("fan_connect.use"))],
    payload: DeclineRequestBody = Body(default_factory=DeclineRequestBody),
) -> ConnectionPublic:
    conn = svc.decline_request(
        db, user, connection_id, cooldown_days=payload.cooldown_days
    )
    return ConnectionPublic.model_validate(svc.serialize_connection(db, conn, user))


@router.post("/requests/{connection_id}/cancel", response_model=ConnectionPublic)
def cancel_request(
    connection_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("fan_connect.use"))],
) -> ConnectionPublic:
    conn = svc.cancel_request(db, user, connection_id)
    return ConnectionPublic.model_validate(svc.serialize_connection(db, conn, user))


@router.get("/connections", response_model=ConnectionListPublic)
def list_connections(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("fan_connect.use"))],
) -> ConnectionListPublic:
    return ConnectionListPublic.model_validate(svc.list_connections(db, user))


def _remove_connection_response(
    connection_id: UUID,
    db: Session,
    user: User,
) -> ConnectionPublic:
    conn = svc.disconnect(db, user, connection_id)
    return ConnectionPublic.model_validate(svc.serialize_connection(db, conn, user))


@router.post("/connections/{connection_id}/remove", response_model=ConnectionPublic)
def remove_connection(
    connection_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("fan_connect.use"))],
) -> ConnectionPublic:
    """Remove connection — messaging disabled until reconnected."""
    return _remove_connection_response(connection_id, db, user)


@router.post("/connections/{connection_id}/disconnect", response_model=ConnectionPublic)
def disconnect_connection(
    connection_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("fan_connect.use"))],
) -> ConnectionPublic:
    """Alias for remove — soft-end connection."""
    return _remove_connection_response(connection_id, db, user)


@router.post("/block", status_code=204, response_class=Response)
def block(
    payload: BlockBody,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("fan_connect.use"))],
) -> Response:
    svc.block_fan(db, user, username=payload.username, reason=payload.reason)
    return Response(status_code=204)


@router.post("/report", response_model=ReportPublic)
def report(
    payload: ReportBody,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("fan_connect.use"))],
) -> ReportPublic:
    row = svc.report_fan(
        db,
        user,
        username=payload.username,
        reason=payload.reason,
        details=payload.details,
        connection_id=payload.connection_id,
        thread_id=payload.thread_id,
    )
    return ReportPublic.model_validate(
        {"id": row.id, "status": row.status, "reason": row.reason, "created_at": row.created_at}
    )


@router.get("/suggestions", response_model=SuggestionsPublic)
def get_suggestions(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("fan_connect.use"))],
    event_id: UUID | None = None,
    category: str | None = Query(default=None, max_length=120),
    city: str | None = Query(default=None, max_length=120),
    area: str | None = Query(default=None, max_length=120),
    mode: str | None = Query(
        default="mixed",
        description=(
            "mixed | near_me | same_event | connections_of_connections | "
            "same_interests | new_people"
        ),
    ),
    lat: float | None = Query(default=None, ge=-90, le=90),
    lng: float | None = Query(default=None, ge=-180, le=180),
    radius_km: float | None = Query(default=None, ge=1, le=100),
    limit: int = Query(default=12, ge=1, le=50),
    page: int = Query(default=1, ge=1),
    cursor: str | None = Query(
        default=None,
        description="Optional page cursor (page number as string).",
    ),
) -> SuggestionsPublic:
    """lat/lng are one-time matching only — never auto-persisted as GPS."""
    page_num = page
    if cursor:
        try:
            page_num = max(1, int(cursor))
        except ValueError:
            page_num = page
    return SuggestionsPublic.model_validate(
        svc.suggestions(
            db,
            user,
            event_id=event_id,
            category=category,
            city=city,
            area=area,
            mode=mode,
            lat=lat,
            lng=lng,
            radius_km=radius_km,
            limit=limit,
            page=page_num,
        )
    )


@router.post(
    "/suggestions/{user_id}/dismiss",
    response_model=SuggestionActionPublic,
)
def dismiss_suggestion(
    user_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("fan_connect.use"))],
    payload: DismissSuggestionBody | None = None,
) -> SuggestionActionPublic:
    body = payload or DismissSuggestionBody()
    return SuggestionActionPublic.model_validate(
        svc.dismiss_suggestion(db, user, user_id, reason=body.reason)
    )


@router.post(
    "/suggestions/{user_id}/more-like-this",
    response_model=SuggestionActionPublic,
)
def more_like_this(
    user_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("fan_connect.use"))],
) -> SuggestionActionPublic:
    return SuggestionActionPublic.model_validate(
        svc.more_like_this(db, user, user_id)
    )


@router.post("/location/preference", response_model=LocationPreferencePublic)
def save_location_preference(
    payload: LocationPreferenceBody,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("fan_connect.use"))],
) -> LocationPreferencePublic:
    """Save approximate city/area only when user explicitly chooses to save."""
    return LocationPreferencePublic.model_validate(
        svc.save_location_preference(
            db,
            user,
            city=payload.city,
            area=payload.area,
            country=payload.country,
            latitude_approx=payload.latitude_approx,
            longitude_approx=payload.longitude_approx,
            precision=payload.precision,
        )
    )


@router.get("/location/preference", response_model=LocationPreferencePublic | None)
def get_location_preference(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("fan_connect.use"))],
) -> LocationPreferencePublic | None:
    data = svc.get_location_preference(db, user)
    if data is None:
        return None
    return LocationPreferencePublic.model_validate(data)


@router.delete("/location/preference", status_code=204, response_class=Response)
def clear_location_preference(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("fan_connect.use"))],
) -> Response:
    svc.clear_location_preference(db, user)
    return Response(status_code=204)


@router.get("/events", response_model=ConnectEventListPublic)
def list_connect_events(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("fan_connect.use"))],
) -> ConnectEventListPublic:
    return ConnectEventListPublic.model_validate(svc.list_connect_events(db, user))


@router.get(
    "/admin/overview",
    response_model=AdminOverviewPublic,
    dependencies=[Depends(require_permission("admin.full_access"))],
)
def admin_overview(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> AdminOverviewPublic:
    return AdminOverviewPublic.model_validate(svc.admin_overview(db))


@router.get(
    "/admin/blocks",
    response_model=AdminBlockListPublic,
    dependencies=[Depends(require_permission("admin.full_access"))],
)
def admin_blocks(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.full_access"))],
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
) -> AdminBlockListPublic:
    return AdminBlockListPublic.model_validate(
        svc.admin_list_blocks(db, page=page, limit=limit)
    )


@router.get(
    "/admin/reports",
    response_model=AdminReportListPublic,
    dependencies=[Depends(require_permission("admin.full_access"))],
)
def admin_reports(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.full_access"))],
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
) -> AdminReportListPublic:
    """Legacy path — prefer GET /admin/fan-connect/reports."""
    return AdminReportListPublic.model_validate(
        svc.admin_list_reports(db, page=page, limit=limit)
    )
