"""Unified referral reporting APIs — shared aggregation only."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, require_permission
from app.core.database import get_db
from app.hosts.service import require_user_host
from app.promos import reporting
from app.users.models import User

router = APIRouter(tags=["referrals"])


@router.get("/referrals/me/summary")
def my_referral_summary(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    scope: str | None = Query(default=None),
    product_type: str | None = Query(default=None),
) -> dict:
    return reporting.get_ambassador_referral_summary(
        db, user=user, scope=scope, product_type=product_type
    )


@router.get("/referrals/me/programs")
def my_referral_programs(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    scope: str | None = Query(default=None),
) -> list[dict]:
    return reporting.get_ambassador_program_breakdown(db, user=user, scope=scope)


@router.get("/referrals/me/earnings")
def my_referral_earnings(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    scope: str | None = Query(default=None),
    product_type: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    return reporting.get_ambassador_earnings(
        db,
        user=user,
        scope=scope,
        product_type=product_type,
        limit=limit,
        offset=offset,
    )


@router.get("/host/referrals/summary")
def host_referral_summary(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    host = require_user_host(db, user)
    return reporting.get_host_referral_summary(db, host_id=host.id)


@router.get("/host/referrals/platform-attributed-sales")
def host_platform_attributed_sales(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    host = require_user_host(db, user)
    return reporting.get_host_platform_attributed_sales(
        db, host_id=host.id, limit=limit, offset=offset
    )


@router.get("/admin/referrals/summary")
def admin_referral_summary(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[
        User,
        Depends(
            require_permission(
                "admin.referrals.view",
                "admin.referrals.finance",
                "admin.full_access",
            )
        ),
    ],
    scope: str | None = Query(default=None),
    payer: str | None = Query(default=None),
) -> dict:
    return reporting.get_admin_referral_summary(db, scope=scope, payer=payer)


@router.get("/admin/referrals/commissions")
def admin_referral_commissions(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[
        User,
        Depends(
            require_permission(
                "admin.referrals.view",
                "admin.referrals.finance",
                "admin.full_access",
            )
        ),
    ],
    payer: str | None = Query(default=None),
    program_id: UUID | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    return reporting.get_admin_referral_commissions(
        db, payer=payer, program_id=program_id, limit=limit, offset=offset
    )


@router.get("/admin/referrals/liabilities")
def admin_referral_liabilities(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[
        User,
        Depends(
            require_permission("admin.referrals.finance", "admin.full_access")
        ),
    ],
    payer: str = Query(default="platform"),
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    return reporting.get_admin_referral_liabilities(
        db, payer=payer, status=status_filter, limit=limit, offset=offset
    )
