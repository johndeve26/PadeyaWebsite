"""Admin event buyers / attendees list and export routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser
from app.core.database import get_db
from app.tickets.admin_export import (
    export_admin_event_buyers,
    list_admin_event_buyer_exports,
    list_admin_event_buyers,
)

router = APIRouter(prefix="/admin/events", tags=["admin-events-buyers"])


def _client_meta(request: Request) -> tuple[str | None, str | None]:
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    return ip, ua


def _filter_kwargs(
    *,
    q: str | None,
    ticket_status: str | None,
    purchase_status: str | None,
    payment_status: str | None,
    refund_status: str | None,
    checked_in: str | None,
    ticket_type: str | None,
    purchased_from: str | None,
    purchased_to: str | None,
    promo_code: str | None,
    ambassador_code: str | None,
) -> dict:
    return {
        "q": q,
        "ticket_status": ticket_status,
        "purchase_status": purchase_status,
        "payment_status": payment_status,
        "refund_status": refund_status,
        "checked_in": checked_in,
        "ticket_type": ticket_type,
        "purchased_from": purchased_from,
        "purchased_to": purchased_to,
        "promo_code": promo_code,
        "ambassador_code": ambassador_code,
    }


@router.get("/{event_id}/buyers")
def admin_event_buyers(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    q: str | None = Query(default=None, max_length=120),
    ticket_status: str | None = Query(default=None, max_length=32),
    purchase_status: str | None = Query(default=None, max_length=32),
    payment_status: str | None = Query(default=None, max_length=32),
    refund_status: str | None = Query(default=None, max_length=32),
    checked_in: str | None = Query(default=None, max_length=8),
    ticket_type: str | None = Query(default=None, max_length=160),
    purchased_from: str | None = Query(default=None, max_length=40),
    purchased_to: str | None = Query(default=None, max_length=40),
    promo_code: str | None = Query(default=None, max_length=64),
    ambassador_code: str | None = Query(default=None, max_length=64),
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict:
    return list_admin_event_buyers(
        db,
        user=user,
        event_id=event_id,
        limit=limit,
        offset=offset,
        **_filter_kwargs(
            q=q,
            ticket_status=ticket_status,
            purchase_status=purchase_status,
            payment_status=payment_status,
            refund_status=refund_status,
            checked_in=checked_in,
            ticket_type=ticket_type,
            purchased_from=purchased_from,
            purchased_to=purchased_to,
            promo_code=promo_code,
            ambassador_code=ambassador_code,
        ),
    )


@router.get("/{event_id}/buyers/export")
def admin_event_buyers_export(
    event_id: UUID,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    format: str = Query(default="csv", max_length=16),
    mode: str = Query(default="operations", max_length=32),
    reason: str | None = Query(default=None, max_length=500),
    include_private_contact: str | None = Query(default=None, max_length=8),
    q: str | None = Query(default=None, max_length=120),
    ticket_status: str | None = Query(default=None, max_length=32),
    purchase_status: str | None = Query(default=None, max_length=32),
    payment_status: str | None = Query(default=None, max_length=32),
    refund_status: str | None = Query(default=None, max_length=32),
    checked_in: str | None = Query(default=None, max_length=8),
    ticket_type: str | None = Query(default=None, max_length=160),
    purchased_from: str | None = Query(default=None, max_length=40),
    purchased_to: str | None = Query(default=None, max_length=40),
    promo_code: str | None = Query(default=None, max_length=64),
    ambassador_code: str | None = Query(default=None, max_length=64),
) -> Response:
    ip, ua = _client_meta(request)
    body, filename, media_type, _meta = export_admin_event_buyers(
        db,
        user=user,
        event_id=event_id,
        format=format,
        mode=mode,
        reason=reason,
        include_private_contact=include_private_contact,
        ip_address=ip,
        user_agent=ua,
        **_filter_kwargs(
            q=q,
            ticket_status=ticket_status,
            purchase_status=purchase_status,
            payment_status=payment_status,
            refund_status=refund_status,
            checked_in=checked_in,
            ticket_type=ticket_type,
            purchased_from=purchased_from,
            purchased_to=purchased_to,
            promo_code=promo_code,
            ambassador_code=ambassador_code,
        ),
    )
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    if isinstance(body, (str, bytes)):
        return Response(content=body, media_type=media_type, headers=headers)
    return StreamingResponse(body, media_type=media_type, headers=headers)


@router.get("/{event_id}/buyers/exports")
def admin_event_buyer_export_history(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    limit: int = Query(default=50, ge=1, le=100),
) -> list[dict]:
    return list_admin_event_buyer_exports(
        db, user=user, event_id=event_id, limit=limit
    )
