"""Public pricing API for the marketing /pricing page."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.pricing.schemas import PublicPricingResponse
from app.pricing.service import build_public_pricing

router = APIRouter(prefix="/pricing", tags=["pricing"])


@router.get("/public", response_model=PublicPricingResponse)
def get_public_pricing(
    db: Annotated[Session, Depends(get_db)],
) -> PublicPricingResponse:
    """Public-safe fee schedule for fans and hosts.

    Never returns host overrides, admin notes, internal commercial reason
    fields, or other hosts' custom rates.
    """
    return build_public_pricing(db)
