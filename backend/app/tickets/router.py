"""Buyer tickets API routes + Phase 17 advanced ticketing."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser
from app.core.database import get_db
from app.tickets.schemas import (
    TableReservationAssign,
    TableReservationCreate,
    TableReservationPublic,
    TicketCancelRequest,
    TicketDeviceBindRequest,
    TicketPublic,
    TicketQrModeRequest,
    TicketTransferClaimContextPublic,
    TicketTransferClaimRequest,
    TicketTransferActivityPublic,
    TicketTransferPublic,
    TicketTransferRequest,
)
from app.tickets import service as ticket_service
from app.tickets import tables_service
from app.tickets.admin_export import export_admin_event_buyers_csv

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.get("/health")
async def tickets_module_health() -> dict[str, str]:
    return {"module": "tickets", "status": "ok"}


@router.get("/claim/context", response_model=TicketTransferClaimContextPublic)
def transfer_claim_context(
    db: Annotated[Session, Depends(get_db)],
    token: str = Query(min_length=10, max_length=200),
) -> TicketTransferClaimContextPublic:
    """Public read for valid claim tokens — prefill register/login (token is the secret)."""
    payload = ticket_service.get_transfer_claim_context(db, raw_token=token)
    return TicketTransferClaimContextPublic.model_validate(payload)


@router.post("/claim", response_model=TicketPublic)
def claim_transferred_ticket(
    payload: TicketTransferClaimRequest,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> TicketPublic:
    ticket = ticket_service.claim_ticket_transfer(
        db,
        user=user,
        raw_token=payload.token,
    )
    return TicketPublic.model_validate(
        ticket_service.serialize_ticket(db, ticket, include_qr=True)
    )


@router.get("/transfers/mine", response_model=list[TicketTransferActivityPublic])
def my_ticket_transfers(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    limit: int = Query(default=50, ge=1, le=100),
) -> list[TicketTransferActivityPublic]:
    rows = ticket_service.list_my_ticket_transfers(db, user=user, limit=limit)
    return [TicketTransferActivityPublic.model_validate(r) for r in rows]


@router.post("/transfers/{transfer_id}/revoke", response_model=TicketTransferActivityPublic)
def revoke_ticket_transfer(
    transfer_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> TicketTransferActivityPublic:
    row = ticket_service.revoke_pending_ticket_transfer(
        db, user=user, transfer_id=transfer_id
    )
    payload = ticket_service._serialize_transfer_activity(db, user, row)
    return TicketTransferActivityPublic.model_validate(payload)


@router.post("/transfers/{transfer_id}/decline", response_model=TicketTransferActivityPublic)
def decline_ticket_transfer(
    transfer_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> TicketTransferActivityPublic:
    row = ticket_service.decline_pending_ticket_transfer(
        db, user=user, transfer_id=transfer_id
    )
    payload = ticket_service._serialize_transfer_activity(db, user, row)
    return TicketTransferActivityPublic.model_validate(payload)


@router.post("/transfers/{transfer_id}/claim", response_model=TicketPublic)
def claim_ticket_transfer_by_id(
    transfer_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> TicketPublic:
    ticket = ticket_service.claim_pending_ticket_transfer_for_user(
        db, user=user, transfer_id=transfer_id
    )
    return TicketPublic.model_validate(
        ticket_service.serialize_ticket(db, ticket, include_qr=True)
    )


@router.post("/transfers/{transfer_id}/resend-invite", response_model=TicketTransferActivityPublic)
def resend_ticket_transfer_invite(
    transfer_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> TicketTransferActivityPublic:
    try:
        row, claim_path = ticket_service.resend_pending_ticket_transfer_invite(
            db, user=user, transfer_id=transfer_id
        )
    except HTTPException:
        raise
    except Exception as exc:
        mapped = ticket_service.transfer_setup_http_error(exc)
        if mapped is not None:
            raise mapped from exc
        raise
    payload = ticket_service._serialize_transfer_activity(db, user, row)
    payload["claim_path"] = claim_path
    return TicketTransferActivityPublic.model_validate(payload)


@router.post(
    "/transfers/{transfer_id}/claim-link",
    response_model=TicketTransferActivityPublic,
)
def refresh_ticket_transfer_claim_link(
    transfer_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> TicketTransferActivityPublic:
    try:
        row, claim_path = ticket_service.refresh_pending_transfer_claim_link(
            db, user=user, transfer_id=transfer_id
        )
    except HTTPException:
        raise
    except Exception as exc:
        mapped = ticket_service.transfer_setup_http_error(exc)
        if mapped is not None:
            raise mapped from exc
        raise
    payload = ticket_service._serialize_transfer_activity(db, user, row)
    payload["claim_path"] = claim_path
    return TicketTransferActivityPublic.model_validate(payload)


@router.get("/mine", response_model=list[TicketPublic])
def my_tickets(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[TicketPublic]:
    tickets = ticket_service.list_buyer_tickets(db, user)
    return [TicketPublic.model_validate(ticket_service.serialize_ticket(db, t)) for t in tickets]


@router.get("/admin/list", response_model=list[TicketPublic])
def admin_tickets(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    limit: int = Query(default=100, ge=1, le=200),
) -> list[TicketPublic]:
    tickets = ticket_service.admin_list_tickets(db, user=user, limit=limit)
    return [TicketPublic.model_validate(ticket_service.serialize_ticket(db, t)) for t in tickets]


@router.get("/admin/transfers", response_model=list[TicketTransferPublic])
def admin_transfers(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    limit: int = Query(default=100, ge=1, le=200),
) -> list[TicketTransferPublic]:
    rows = ticket_service.admin_list_transfers(db, user=user, limit=limit)
    return [TicketTransferPublic.model_validate(r) for r in rows]


@router.get("/admin/events/{event_id}/buyers/export.csv")
def admin_event_buyers_export(
    event_id: UUID,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> Response:
    """Platform admin CSV of ticket holders for one event (no QR / payment refs / venue)."""
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    csv_text, filename = export_admin_event_buyers_csv(
        db,
        user=user,
        event_id=event_id,
        ip_address=ip,
        user_agent=ua,
    )
    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/events/{event_id}/transfers", response_model=list[TicketTransferPublic])
def event_transfers(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[TicketTransferPublic]:
    rows = ticket_service.list_ticket_transfers_for_event(db, user=user, event_id=event_id)
    return [TicketTransferPublic.model_validate(r) for r in rows]


@router.get("/events/{event_id}/tables", response_model=list[TableReservationPublic])
def list_tables(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[TableReservationPublic]:
    rows = tables_service.list_table_reservations(db, user=user, event_id=event_id)
    return [TableReservationPublic.model_validate(r) for r in rows]


@router.post("/events/{event_id}/tables", response_model=TableReservationPublic)
def create_table(
    event_id: UUID,
    payload: TableReservationCreate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> TableReservationPublic:
    row = tables_service.create_table_reservation(
        db,
        user=user,
        event_id=event_id,
        table_label=payload.table_label,
        capacity=payload.capacity,
        seat_label=payload.seat_label,
        assignment_note=payload.assignment_note,
    )
    return TableReservationPublic.model_validate(row)


@router.patch("/tables/{reservation_id}/assign", response_model=TableReservationPublic)
def assign_table(
    reservation_id: UUID,
    payload: TableReservationAssign,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> TableReservationPublic:
    row = tables_service.assign_table_seat(
        db,
        user=user,
        reservation_id=reservation_id,
        ticket_id=payload.ticket_id,
        seat_label=payload.seat_label,
    )
    return TableReservationPublic.model_validate(row)


@router.post("/tables/{reservation_id}/cancel", response_model=TableReservationPublic)
def cancel_table(
    reservation_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> TableReservationPublic:
    row = tables_service.cancel_table_reservation(
        db, user=user, reservation_id=reservation_id
    )
    return TableReservationPublic.model_validate(row)


@router.get("/{ticket_id}", response_model=TicketPublic)
def ticket_detail(
    ticket_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> TicketPublic:
    ticket = ticket_service.get_buyer_ticket(db, user, ticket_id)
    return TicketPublic.model_validate(
        ticket_service.serialize_ticket(db, ticket, include_qr=True)
    )


@router.get("/{ticket_id}/pdf")
def ticket_pdf(
    ticket_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> Response:
    """Downloadable PDF pass (static QR). Owner-only."""
    pdf_bytes, filename = ticket_service.build_buyer_ticket_pdf(
        db, user=user, ticket_id=ticket_id
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/{ticket_id}/transfers", response_model=list[TicketTransferPublic])
def ticket_transfers(
    ticket_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[TicketTransferPublic]:
    try:
        rows = ticket_service.list_ticket_transfers_for_ticket(
            db, user=user, ticket_id=ticket_id
        )
    except HTTPException:
        raise
    except Exception as exc:
        mapped = ticket_service.transfer_setup_http_error(exc)
        if mapped is not None:
            raise mapped from exc
        raise
    return [TicketTransferPublic.model_validate(r) for r in rows]


@router.post("/{ticket_id}/transfer", response_model=TicketTransferPublic)
def transfer_ticket(
    ticket_id: UUID,
    payload: TicketTransferRequest,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> TicketTransferPublic:
    try:
        row, claim_path = ticket_service.transfer_ticket(
            db,
            user=user,
            ticket_id=ticket_id,
            to_email=str(payload.to_email),
            to_name=payload.to_name,
            note=payload.note,
        )
    except HTTPException:
        raise
    except Exception as exc:
        mapped = ticket_service.transfer_setup_http_error(exc)
        if mapped is not None:
            raise mapped from exc
        raise
    public = TicketTransferPublic.model_validate(row)
    if claim_path:
        public = public.model_copy(update={"claim_path": claim_path})
    return public


@router.post("/{ticket_id}/cancel", response_model=TicketPublic)
def cancel_ticket(
    ticket_id: UUID,
    payload: TicketCancelRequest,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> TicketPublic:
    ticket = ticket_service.cancel_ticket(
        db,
        user=user,
        ticket_id=ticket_id,
        password=payload.password,
        reason=payload.reason,
    )
    return TicketPublic.model_validate(ticket_service.serialize_ticket(db, ticket))


@router.post("/{ticket_id}/qr-mode", response_model=TicketPublic)
def set_qr_mode(
    ticket_id: UUID,
    payload: TicketQrModeRequest,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> TicketPublic:
    ticket = ticket_service.set_ticket_qr_mode(
        db, user=user, ticket_id=ticket_id, qr_mode=payload.qr_mode
    )
    return TicketPublic.model_validate(
        ticket_service.serialize_ticket(db, ticket, include_qr=True)
    )


@router.post("/{ticket_id}/qr-regenerate", response_model=TicketPublic)
def regenerate_qr(
    ticket_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> TicketPublic:
    ticket = ticket_service.regenerate_ticket_qr(db, user=user, ticket_id=ticket_id)
    return TicketPublic.model_validate(
        ticket_service.serialize_ticket(db, ticket, include_qr=True)
    )


@router.post("/{ticket_id}/bind-device", response_model=TicketPublic)
def bind_device(
    ticket_id: UUID,
    payload: TicketDeviceBindRequest,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> TicketPublic:
    ticket = ticket_service.bind_ticket_device(
        db,
        user=user,
        ticket_id=ticket_id,
        device_fingerprint=payload.device_fingerprint,
    )
    return TicketPublic.model_validate(ticket_service.serialize_ticket(db, ticket))
