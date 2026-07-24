"""Check-in and scanner API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser
from app.checkins.offline_service import sync_offline_scans
from app.checkins.schemas import (
    CheckInPublic,
    CheckInRequest,
    CheckInStats,
    DeskAttendeePublic,
    ManualOverrideRequest,
    OfflineScanResultItem,
    OfflineSyncRequest,
    OfflineSyncResponse,
    ScanResultResponse,
    ScannerSessionPublic,
    StaffAssignRequest,
    StaffAssignmentPublic,
    StartSessionRequest,
    TicketScanInfo,
    ValidateQrRequest,
)
from app.checkins.service import (
    assign_event_staff,
    check_in_ticket,
    end_scanner_session,
    event_checkin_stats,
    list_checkins,
    list_event_staff,
    override_check_in,
    search_attendees,
    serialize_checkin,
    serialize_desk_attendee,
    serialize_session,
    serialize_staff,
    start_scanner_session,
    unassign_event_staff,
    validate_qr,
)
from app.core.database import get_db
from app.events.schemas import MessageResponse

router = APIRouter(prefix="/checkins", tags=["checkins"])


@router.get("/health")
async def checkins_module_health() -> dict[str, str]:
    return {"module": "checkins", "status": "ok"}


@router.post(
    "/sessions",
    response_model=ScannerSessionPublic,
    status_code=status.HTTP_201_CREATED,
)
def start_session(
    payload: StartSessionRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> ScannerSessionPublic:
    ip = request.client.host if request.client else None
    session = start_scanner_session(db, user=user, payload=payload, ip_address=ip)
    return ScannerSessionPublic.model_validate(serialize_session(db, session))


@router.post("/sessions/{session_id}/end", response_model=ScannerSessionPublic)
def end_session(
    session_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> ScannerSessionPublic:
    session = end_scanner_session(db, user=user, session_id=session_id)
    return ScannerSessionPublic.model_validate(serialize_session(db, session))


@router.post("/validate", response_model=ScanResultResponse)
def validate_qr_endpoint(
    payload: ValidateQrRequest,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> ScanResultResponse:
    result = validate_qr(db, user=user, payload=payload)
    ticket = result.get("ticket")
    return ScanResultResponse(
        outcome=result["outcome"],
        message=result["message"],
        ticket=TicketScanInfo(**ticket) if ticket else None,
        check_in_id=result.get("check_in_id"),
        checked_in_at=result.get("checked_in_at"),
        scanner_name=result.get("scanner_name"),
    )


@router.post("/scan", response_model=ScanResultResponse)
def scan_and_check_in(
    payload: CheckInRequest,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> ScanResultResponse:
    result = check_in_ticket(db, user=user, payload=payload)
    ticket = result.get("ticket")
    return ScanResultResponse(
        outcome=result["outcome"],
        message=result["message"],
        ticket=TicketScanInfo(**ticket) if ticket else None,
        check_in_id=result.get("check_in_id"),
        checked_in_at=result.get("checked_in_at"),
        scanner_name=result.get("scanner_name"),
    )


@router.post("/override", response_model=ScanResultResponse)
def override_endpoint(
    payload: ManualOverrideRequest,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> ScanResultResponse:
    result = override_check_in(db, user=user, payload=payload)
    ticket = result.get("ticket")
    return ScanResultResponse(
        outcome=result["outcome"],
        message=result["message"],
        ticket=TicketScanInfo(**ticket) if ticket else None,
        check_in_id=result.get("check_in_id"),
        checked_in_at=result.get("checked_in_at"),
        scanner_name=result.get("scanner_name"),
    )


@router.get("/events/{event_id}/search", response_model=list[DeskAttendeePublic])
def search(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    q: str = Query(min_length=2, max_length=120),
) -> list[DeskAttendeePublic]:
    tickets = search_attendees(db, user=user, event_id=event_id, query=q)
    return [
        DeskAttendeePublic.model_validate(serialize_desk_attendee(t)) for t in tickets
    ]


@router.get("/events/{event_id}", response_model=list[CheckInPublic])
def list_event_checkins(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[CheckInPublic]:
    entries = list_checkins(db, user=user, event_id=event_id)
    return [CheckInPublic.model_validate(serialize_checkin(db, e)) for e in entries]


@router.get("/events/{event_id}/stats", response_model=CheckInStats)
def stats(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> CheckInStats:
    return CheckInStats.model_validate(event_checkin_stats(db, user=user, event_id=event_id))


@router.get("/events/{event_id}/staff", response_model=list[StaffAssignmentPublic])
def get_staff(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[StaffAssignmentPublic]:
    rows = list_event_staff(db, user=user, event_id=event_id)
    return [StaffAssignmentPublic.model_validate(serialize_staff(db, r)) for r in rows]


@router.post(
    "/events/{event_id}/staff",
    response_model=StaffAssignmentPublic,
    status_code=status.HTTP_201_CREATED,
)
def post_staff(
    event_id: UUID,
    payload: StaffAssignRequest,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> StaffAssignmentPublic:
    row = assign_event_staff(db, user=user, event_id=event_id, email=payload.email)
    return StaffAssignmentPublic.model_validate(serialize_staff(db, row))


@router.delete(
    "/events/{event_id}/staff/{assignment_id}",
    response_model=MessageResponse,
)
def delete_staff(
    event_id: UUID,
    assignment_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> MessageResponse:
    unassign_event_staff(
        db, user=user, event_id=event_id, assignment_id=assignment_id
    )
    return MessageResponse(message="Staff unassigned")


@router.post("/offline/sync", response_model=OfflineSyncResponse)
def offline_sync(
    payload: OfflineSyncRequest,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> OfflineSyncResponse:
    result = sync_offline_scans(
        db,
        user=user,
        event_id=payload.event_id,
        client_batch_id=payload.client_batch_id,
        device_label=payload.device_label,
        scans=[s.model_dump() for s in payload.scans],
    )
    items = []
    for row in result["results"]:
        ticket = row.get("ticket")
        items.append(
            OfflineScanResultItem(
                client_scan_id=row["client_scan_id"],
                sync_status=row["sync_status"],
                conflict_reason=row.get("conflict_reason"),
                ticket=TicketScanInfo(**ticket) if ticket else None,
                check_in_id=row.get("check_in_id"),
            )
        )
    return OfflineSyncResponse(
        batch_id=result["batch_id"],
        client_batch_id=result["client_batch_id"],
        status=result["status"],
        accepted_count=result["accepted_count"],
        conflict_count=result["conflict_count"],
        invalid_count=result["invalid_count"],
        results=items,
    )
