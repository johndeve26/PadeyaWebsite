"""Payments and orders API routes."""

from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user_optional, require_permission
from app.core.database import get_db
from app.payments.fee_quote_schemas import (
    BuyerFeeQuoteLine,
    BuyerFeeQuoteRequest,
    BuyerFeeQuoteResponse,
)
from app.payments.schemas import (
    CheckoutBuyerEmailCheck,
    CheckoutBuyerEmailCheckPublic,
    CheckoutInitializeRequest,
    CheckoutResponse,
    OrderClaimPublic,
    OrderClaimRequest,
    OrderClaimStart,
    OrderClaimStartPublic,
    OrderCreate,
    OrderPdfDownloadRequest,
    OrderPublic,
    OrderReferenceSummaryPublic,
    PaymentPublic,
    PaystackConfigPublic,
)
from app.payments.service import (
    archive_order,
    confirm_checkout_payment,
    create_order,
    get_order_by_id,
    get_order_by_reference,
    initialize_checkout,
    list_all_orders,
    list_all_payments,
    list_buyer_orders,
    require_buyer_order,
    serialize_order,
)
from app.payments.webhook import process_paystack_webhook
from app.users.models import User

router = APIRouter(tags=["payments"])


@router.get("/payments/health")
async def payments_module_health() -> dict[str, str]:
    return {"module": "payments", "status": "ok"}


@router.get("/payments/paystack/config", response_model=PaystackConfigPublic)
def paystack_public_config(
    db: Annotated[Session, Depends(get_db)],
) -> PaystackConfigPublic:
    """Active Paystack mode + public key for checkout (no secrets)."""
    from app.payments.config import paystack_runtime

    cfg = paystack_runtime(db)
    mode: str = cfg.mode if cfg.mode == "live" else "test"
    return PaystackConfigPublic(
        mode=mode,
        public_key=cfg.public_key or None,
        base_url=cfg.base_url,
    )


@router.post("/payments/fee-quote", response_model=BuyerFeeQuoteResponse)
def quote_buyer_fees(
    payload: BuyerFeeQuoteRequest,
    db: Annotated[Session, Depends(get_db)],
) -> BuyerFeeQuoteResponse:
    """Buyer-facing fee quote for checkout preview. Never returns host commission terms."""
    from app.finance.fees.checkout_fees import (
        buyer_facing_fee_breakdown,
        calculate_checkout_fees,
    )
    from app.hosts.models import Host

    host = db.get(Host, payload.host_id)
    if host is None:
        raise HTTPException(status_code=404, detail="Host not found")

    result = calculate_checkout_fees(
        db,
        host_id=payload.host_id,
        ticket_subtotal=payload.ticket_subtotal,
        merch_subtotal=payload.merch_subtotal,
        ticket_discount=payload.ticket_discount,
        merch_discount=payload.merch_discount,
        shipping_amount=payload.shipping_amount,
        currency=payload.currency.upper(),
    )
    discount_total = (
        payload.ticket_discount + payload.merch_discount
    ).quantize(Decimal("0.01"))
    return BuyerFeeQuoteResponse(
        subtotal=(payload.ticket_subtotal + payload.merch_subtotal).quantize(
            Decimal("0.01")
        ),
        discount_total=discount_total,
        shipping_amount=result.shipping_amount,
        buyer_fee_total=result.buyer_fee_total,
        processing_fee_total=result.processing_fee_total,
        final_total=result.final_total,
        fee_breakdown=[
            BuyerFeeQuoteLine(**row) for row in buyer_facing_fee_breakdown(result)
        ],
    )


@router.post(
    "/checkout/buyer-email/check",
    response_model=CheckoutBuyerEmailCheckPublic,
)
def check_checkout_buyer_email(
    payload: CheckoutBuyerEmailCheck,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> CheckoutBuyerEmailCheckPublic:
    """Logged-out checkout: detect existing accounts before payment."""
    if user is not None:
        return CheckoutBuyerEmailCheckPublic(status="ok")

    from app.events.models import Event
    from app.payments.attendees import validate_email
    from app.payments.guest import (
        assert_guest_email_allowed_for_checkout,
        resolve_matched_account,
    )

    email = validate_email(payload.email)
    if resolve_matched_account(db, email) is not None:
        return CheckoutBuyerEmailCheckPublic(status="existing_account")

    event = db.get(Event, payload.event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    assert_guest_email_allowed_for_checkout(
        db,
        email=email,
        host_id=event.host_id,
        has_tickets=payload.has_tickets,
        has_merch=payload.has_merch,
    )
    return CheckoutBuyerEmailCheckPublic(status="ok")


@router.get(
    "/orders/reference/{reference}/summary",
    response_model=OrderReferenceSummaryPublic,
)
def order_summary_by_reference(
    reference: str,
    email: str,
    db: Annotated[Session, Depends(get_db)],
) -> OrderReferenceSummaryPublic:
    """Checkout success polling — minimal status without auth."""
    from app.payments.order_pdf import email_may_access_order
    from app.payments.service import normalize_order_reference

    order = get_order_by_reference(db, reference)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if not email_may_access_order(db, order, email):
        raise HTTPException(status_code=403, detail="Email does not match this order.")
    ref = normalize_order_reference(order.reference) or order.reference
    return OrderReferenceSummaryPublic(
        reference=ref,
        status=order.status,
        pdf_available=order.status == "paid",
    )


@router.post("/orders/reference/{reference}/pdf")
def download_order_pdf_by_reference(
    reference: str,
    payload: OrderPdfDownloadRequest,
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    """Download ticket/receipt PDF(s) using buyer email (checkout success, no login)."""
    from app.payments.order_pdf import package_order_pdf_download

    order = get_order_by_reference(db, reference)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    body, filename, media_type = package_order_pdf_download(
        db, order=order, email=payload.email
    )
    return Response(
        content=body,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/orders/{order_id}/pdf")
def download_order_pdf_authenticated(
    order_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> Response:
    """Signed-in buyer download for dashboard / success when logged in."""
    from app.payments.order_pdf import package_order_pdf_download

    order = require_buyer_order(db, user, order_id)
    body, filename, media_type = package_order_pdf_download(
        db, order=order, email=user.email
    )
    return Response(
        content=body,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/orders", response_model=OrderPublic, status_code=status.HTTP_201_CREATED)
def create_order_endpoint(
    payload: OrderCreate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> OrderPublic:
    client_ip = request.client.host if request.client else None
    order = create_order(db, user=user, payload=payload, client_ip=client_ip)
    return OrderPublic.model_validate(serialize_order(db, order))


@router.get("/orders/mine", response_model=list[OrderPublic])
def my_orders(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[OrderPublic]:
    return [OrderPublic.model_validate(serialize_order(db, o)) for o in list_buyer_orders(db, user)]


@router.get("/orders/{order_id}", response_model=OrderPublic)
def get_order(
    order_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> OrderPublic:
    order = require_buyer_order(db, user, order_id)
    return OrderPublic.model_validate(serialize_order(db, order))


@router.post("/orders/{order_id}/resend-ticket-emails", response_model=dict[str, str])
def resend_ticket_emails_endpoint(
    order_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict[str, str]:
    from app.tickets.service import resend_order_ticket_emails

    return resend_order_ticket_emails(db, user=user, order_id=order_id)


@router.post("/orders/{order_id}/archive", response_model=OrderPublic)
def archive_buyer_order(
    order_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> OrderPublic:
    order = archive_order(db, user=user, order_id=order_id)
    return OrderPublic.model_validate(serialize_order(db, order))


@router.post("/payments/checkout/{order_id}", response_model=CheckoutResponse)
def checkout(
    order_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)],
    body: CheckoutInitializeRequest | None = None,
) -> CheckoutResponse:
    payment_email = body.payment_email if body else None
    result = initialize_checkout(
        db,
        user=user,
        order_id=order_id,
        payment_email=payment_email,
    )
    return CheckoutResponse(**result)


@router.post("/payments/checkout/{order_id}/confirm", response_model=OrderPublic)
def confirm_checkout(
    order_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> OrderPublic:
    """Verify Paystack and issue tickets when the popup succeeds before the webhook arrives."""
    order = confirm_checkout_payment(db, user=user, order_id=order_id)
    return OrderPublic.model_validate(serialize_order(db, order))


@router.post("/orders/claim", response_model=OrderClaimPublic)
def claim_guest_order(
    payload: OrderClaimRequest,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> OrderClaimPublic:
    """Claim a paid guest order after email-verified magic link (token) + login."""
    from app.payments.guest import claim_order_for_user, find_order_by_claim_token

    order = find_order_by_claim_token(db, payload.token)
    if order is None:
        raise HTTPException(status_code=400, detail="Invalid or expired claim link")
    claim_order_for_user(db, order=order, user=user, raw_token=payload.token)
    db.commit()
    event_title = None
    from app.events.models import Event

    event = db.get(Event, order.event_id)
    if event:
        event_title = event.title
    ticket_count = len(order.tickets) if getattr(order, "tickets", None) else 0
    return OrderClaimPublic(
        order_id=order.id,
        reference=order.reference,
        status=order.status,
        claimed=True,
        buyer_email=order.buyer_email,
        event_title=event_title,
        ticket_count=ticket_count,
        message="Tickets are now in your Pàdéyá account.",
    )


@router.post("/orders/claim/start", response_model=OrderClaimStartPublic)
def start_guest_order_claim(
    payload: OrderClaimStart,
    db: Annotated[Session, Depends(get_db)],
) -> OrderClaimStartPublic:
    """Re-issue a claim magic link to the guest buyer email."""
    from app.payments.guest import request_guest_claim_link

    result = request_guest_claim_link(
        db,
        order_reference=payload.order_reference,
        email=payload.email,
    )
    return OrderClaimStartPublic(**result)


@router.post("/payments/webhooks/paystack")
async def paystack_webhook(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, str]:
    body = await request.body()
    signature = request.headers.get("x-paystack-signature")
    return process_paystack_webhook(db, body=body, signature=signature)


@router.get("/admin/orders", response_model=list[OrderPublic])
def admin_orders(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("payments.view", "admin.full_access"))],
) -> list[OrderPublic]:
    _ = user
    return [OrderPublic.model_validate(serialize_order(db, o)) for o in list_all_orders(db)]


@router.get("/admin/payments", response_model=list[PaymentPublic])
def admin_payments(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("payments.view", "admin.full_access"))],
) -> list[PaymentPublic]:
    _ = user
    return [PaymentPublic.model_validate(p) for p in list_all_payments(db)]


@router.get("/admin/orders/{order_id}", response_model=OrderPublic)
def admin_order_detail(
    order_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("payments.view", "admin.full_access"))],
) -> OrderPublic:
    _ = user
    order = get_order_by_id(db, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return OrderPublic.model_validate(serialize_order(db, order))
