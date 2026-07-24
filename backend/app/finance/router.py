"""Finance API: refunds, balances, ledger, payouts, earnings, platform revenue."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, require_permission, require_role
from app.core.audit import write_audit_log
from app.core.database import get_db
from app.finance.earnings_schemas import HostEarningsReport
from app.finance.earnings_service import (
    earnings_report_csv,
    get_admin_earnings,
    get_host_earnings_for_user,
    list_admin_host_earnings_overview,
)
from app.finance.platform_revenue import (
    assert_platform_finance_access,
    assert_platform_finance_export,
    build_platform_revenue_report,
    platform_revenue_csv,
)
from app.finance.schemas import (
    HostBalancePublic,
    LedgerEntryPublic,
    PayoutMarkPaid,
    PayoutRequestCreate,
    PayoutRequestPublic,
    PayoutReview,
    PlatformRevenueReportPublic,
    RefundEscalate,
    RefundPolicyInfo,
    RefundRequestCreate,
    RefundRequestPublic,
    RefundReview,
    SettlementReportPublic,
)
from app.finance.service import (
    cancel_refund_request,
    create_payout_request,
    create_refund_request,
    escalate_refund_request,
    get_host_balance,
    list_host_ledger,
    list_host_payouts,
    list_ledger_entries,
    list_my_refund_requests,
    list_payouts_for_admin,
    list_refund_requests_for_staff,
    mark_payout_paid,
    review_payout_request,
    review_refund_request,
    settlement_report,
)
from app.users.models import User

router = APIRouter(prefix="/finance", tags=["finance"])


@router.get("/health")
async def finance_module_health() -> dict[str, str]:
    return {"module": "finance", "status": "ok"}


@router.get("/refund-policies", response_model=RefundPolicyInfo)
def refund_policies() -> RefundPolicyInfo:
    return RefundPolicyInfo()


# --- Buyer refunds ---


@router.post(
    "/refunds/requests",
    response_model=RefundRequestPublic,
    status_code=status.HTTP_201_CREATED,
)
def create_refund(
    payload: RefundRequestCreate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> RefundRequestPublic:
    return RefundRequestPublic.model_validate(
        create_refund_request(db, user=user, payload=payload)
    )


@router.get("/refunds/mine", response_model=list[RefundRequestPublic])
def my_refunds(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[RefundRequestPublic]:
    return [
        RefundRequestPublic.model_validate(r) for r in list_my_refund_requests(db, user)
    ]


@router.post(
    "/refunds/requests/{request_id}/cancel",
    response_model=RefundRequestPublic,
)
def cancel_refund(
    request_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> RefundRequestPublic:
    return RefundRequestPublic.model_validate(
        cancel_refund_request(db, user=user, request_id=request_id)
    )


# --- Support / admin refund review ---


@router.get("/refunds/requests", response_model=list[RefundRequestPublic])
def staff_refunds(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("refunds.review", "admin.full_access"))
    ],
    status_filter: str | None = Query(default=None, alias="status"),
) -> list[RefundRequestPublic]:
    return [
        RefundRequestPublic.model_validate(r)
        for r in list_refund_requests_for_staff(db, user, status_filter=status_filter)
    ]


@router.post(
    "/refunds/requests/{request_id}/escalate",
    response_model=RefundRequestPublic,
)
def escalate_refund(
    request_id: UUID,
    payload: RefundEscalate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("refunds.review", "admin.full_access"))
    ],
) -> RefundRequestPublic:
    return RefundRequestPublic.model_validate(
        escalate_refund_request(db, user=user, request_id=request_id, payload=payload)
    )


@router.post(
    "/refunds/requests/{request_id}/review",
    response_model=RefundRequestPublic,
)
def review_refund(
    request_id: UUID,
    payload: RefundReview,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> RefundRequestPublic:
    return RefundRequestPublic.model_validate(
        review_refund_request(db, user=user, request_id=request_id, payload=payload)
    )


# --- Host balance & payouts ---


@router.get("/host/balance", response_model=HostBalancePublic)
def host_balance(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> HostBalancePublic:
    return HostBalancePublic.model_validate(get_host_balance(db, user))


@router.get("/host/ledger", response_model=list[LedgerEntryPublic])
def host_ledger(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    limit: int = Query(default=100, ge=1, le=200),
) -> list[LedgerEntryPublic]:
    return [
        LedgerEntryPublic.model_validate(e)
        for e in list_host_ledger(db, user, limit=limit)
    ]


@router.post(
    "/host/payouts",
    response_model=PayoutRequestPublic,
    status_code=status.HTTP_201_CREATED,
)
def host_create_payout(
    payload: PayoutRequestCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("payouts.request", "admin.full_access"))
    ],
) -> PayoutRequestPublic:
    return PayoutRequestPublic.model_validate(
        create_payout_request(db, user=user, payload=payload)
    )


@router.get("/host/payouts", response_model=list[PayoutRequestPublic])
def host_list_payouts(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[PayoutRequestPublic]:
    return [PayoutRequestPublic.model_validate(p) for p in list_host_payouts(db, user)]


@router.get("/host/earnings", response_model=HostEarningsReport)
def host_earnings(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    event_id: UUID | None = None,
) -> HostEarningsReport:
    return get_host_earnings_for_user(db, user, event_id=event_id)


@router.get("/host/earnings/export.csv")
def host_earnings_export(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    event_id: UUID | None = None,
) -> Response:
    report = get_host_earnings_for_user(db, user, event_id=event_id)
    csv_body = earnings_report_csv(report)
    filename = "padeya-host-earnings.csv"
    if event_id is not None:
        filename = f"padeya-host-earnings-{event_id}.csv"
    return Response(
        content=csv_body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/host/events/{event_id}/earnings",
    response_model=HostEarningsReport,
)
def host_event_earnings(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> HostEarningsReport:
    return get_host_earnings_for_user(db, user, event_id=event_id)


# --- Admin finance ---


@router.get("/admin/payouts", response_model=list[PayoutRequestPublic])
def admin_payouts(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    status_filter: str | None = Query(default=None, alias="status"),
) -> list[PayoutRequestPublic]:
    return [
        PayoutRequestPublic.model_validate(p)
        for p in list_payouts_for_admin(db, user, status_filter=status_filter)
    ]


@router.post("/admin/payouts/{payout_id}/review", response_model=PayoutRequestPublic)
def admin_review_payout(
    payout_id: UUID,
    payload: PayoutReview,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> PayoutRequestPublic:
    return PayoutRequestPublic.model_validate(
        review_payout_request(db, user=user, payout_id=payout_id, payload=payload)
    )


@router.post(
    "/admin/payouts/{payout_id}/mark-paid",
    response_model=PayoutRequestPublic,
)
def admin_mark_payout_paid(
    payout_id: UUID,
    payload: PayoutMarkPaid,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_role("super_admin"))],
) -> PayoutRequestPublic:
    return PayoutRequestPublic.model_validate(
        mark_payout_paid(db, user=user, payout_id=payout_id, payload=payload)
    )


@router.get("/admin/ledger", response_model=list[LedgerEntryPublic])
def admin_ledger(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    host_id: UUID | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[LedgerEntryPublic]:
    return [
        LedgerEntryPublic.model_validate(e)
        for e in list_ledger_entries(db, user, host_id=host_id, limit=limit)
    ]


@router.get("/admin/settlement", response_model=SettlementReportPublic)
def admin_settlement(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    host_id: UUID | None = None,
) -> SettlementReportPublic:
    return SettlementReportPublic.model_validate(
        settlement_report(db, user, host_id=host_id)
    )


@router.get("/admin/earnings", response_model=HostEarningsReport)
def admin_earnings(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    host_id: UUID | None = None,
    event_id: UUID | None = None,
) -> HostEarningsReport:
    return get_admin_earnings(db, user, host_id=host_id, event_id=event_id)


@router.get("/admin/earnings/hosts")
def admin_earnings_hosts(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[dict]:
    return list_admin_host_earnings_overview(db, user)


@router.get("/admin/earnings/export.csv")
def admin_earnings_export(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    host_id: UUID | None = None,
    event_id: UUID | None = None,
) -> Response:
    from app.finance.platform_revenue import assert_platform_finance_export

    assert_platform_finance_export(user)
    report = get_admin_earnings(db, user, host_id=host_id, event_id=event_id)
    write_audit_log(
        db,
        action="finance.host_earnings_export",
        actor_user_id=user.id,
        resource_type="host_earnings",
        resource_id=str(host_id or event_id or "export"),
        details={
            "host_id": str(host_id) if host_id else None,
            "event_id": str(event_id) if event_id else None,
            "row_count": len(report.rows),
        },
    )
    db.commit()
    csv_body = earnings_report_csv(report)
    return Response(
        content=csv_body,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="padeya-admin-earnings.csv"'
        },
    )


@router.get(
    "/admin/hosts/{host_id}/earnings",
    response_model=HostEarningsReport,
)
def admin_host_earnings(
    host_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> HostEarningsReport:
    return get_admin_earnings(db, user, host_id=host_id)


@router.get(
    "/admin/events/{event_id}/earnings",
    response_model=HostEarningsReport,
)
def admin_event_earnings(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> HostEarningsReport:
    return get_admin_earnings(db, user, event_id=event_id)


@router.get(
    "/admin/platform-revenue",
    response_model=PlatformRevenueReportPublic,
)
def admin_platform_revenue(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    host_id: UUID | None = None,
    event_id: UUID | None = None,
    revenue_type: str | None = Query(default=None),
) -> PlatformRevenueReportPublic:
    assert_platform_finance_access(user)
    report = build_platform_revenue_report(
        db,
        date_from=date_from,
        date_to=date_to,
        host_id=host_id,
        event_id=event_id,
        revenue_type=revenue_type,
    )
    return PlatformRevenueReportPublic.model_validate(report)


@router.get("/admin/platform-revenue/export.csv")
def admin_platform_revenue_export(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    host_id: UUID | None = None,
    event_id: UUID | None = None,
    revenue_type: str | None = Query(default=None),
) -> Response:
    assert_platform_finance_export(user)
    report = build_platform_revenue_report(
        db,
        date_from=date_from,
        date_to=date_to,
        host_id=host_id,
        event_id=event_id,
        revenue_type=revenue_type,
    )
    write_audit_log(
        db,
        action="finance.platform_revenue_export",
        actor_user_id=user.id,
        resource_type="platform_ledger",
        resource_id="export",
        details={
            "host_id": str(host_id) if host_id else None,
            "event_id": str(event_id) if event_id else None,
            "revenue_type": revenue_type,
            "entry_count": report["summary"].get("entry_count"),
        },
    )
    db.commit()
    return Response(
        content=platform_revenue_csv(report),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="padeya-platform-revenue.csv"'
        },
    )


@router.get("/admin/platform-ledger")
def admin_platform_ledger(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    host_id: UUID | None = None,
    event_id: UUID | None = None,
    entry_type: str | None = None,
    limit: int = Query(default=200, ge=1, le=500),
) -> dict:
    """List platform ledger entries (read-only; no mutate endpoints)."""
    assert_platform_finance_access(user)
    report = build_platform_revenue_report(
        db,
        date_from=date_from,
        date_to=date_to,
        host_id=host_id,
        event_id=event_id,
        revenue_type=None,
    )
    entries = report["entries"]
    if entry_type:
        entries = [e for e in entries if e.get("entry_type") == entry_type]
    return {
        "summary": report["summary"],
        "entries": entries[:limit],
        "mutable": False,
    }
