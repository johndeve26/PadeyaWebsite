"""Admin production readiness (read-only preflight)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.platform.readiness import ReadinessReport, run_production_readiness
from app.platform.schemas import (
    AIReadinessSummaryPublic,
    ProductionReadinessPublic,
    ReadinessCheckPublic,
)
from app.users.models import User

router = APIRouter(prefix="/admin/platform", tags=["platform-readiness"])


def _serialize_report(report: ReadinessReport) -> ProductionReadinessPublic:
    ai = None
    if report.ai_readiness is not None:
        ar = report.ai_readiness
        ai = AIReadinessSummaryPublic(
            status=ar.status,
            templates_seeded=ar.templates_seeded,
            feature_routes_present=ar.feature_routes_present,
            provider_status=ar.provider_status,
            kill_switch_active=ar.kill_switch_active,
            blocked_keys_status=ar.blocked_keys_status,
            quarantined_keys_status=ar.quarantined_keys_status,
            spend_cap_status=ar.spend_cap_status,
            message=ar.message,
        )
    return ProductionReadinessPublic(
        verdict=report.verdict.value,
        summary=report.summary,
        checks=[
            ReadinessCheckPublic(
                id=c.id,
                category=c.category,
                name=c.name,
                status=c.status,
                message=c.message,
                fix=c.fix,
                details=dict(c.details),
            )
            for c in report.checks
        ],
        ai_readiness=ai,
    )


@router.get("/readiness", response_model=ProductionReadinessPublic)
@router.get("/go-live", response_model=ProductionReadinessPublic, include_in_schema=False)
def admin_production_readiness(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_permission("admin.platform.view_readiness"))],
) -> ProductionReadinessPublic:
    report = run_production_readiness(db=db)
    return _serialize_report(report)
