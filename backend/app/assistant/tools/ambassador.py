"""Ambassador-scoped tools — own referral data only."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.users.models import User
from app.users.service import user_has_role


def get_my_referral_summary(
    db: Session, *, user: User | None, **_: Any
) -> dict[str, Any]:
    if user is None:
        return {"ok": False, "error": "auth_required"}
    if not user_has_role(user, "ambassador", "super_admin"):
        return {"ok": False, "error": "forbidden"}
    summary: dict[str, Any] = {
        "role": "ambassador",
        "dashboard_url": "/ambassador",
    }
    try:
        # Best-effort: look for ambassador profile / stats without inventing numbers
        from sqlalchemy import func, select

        AmbModel = None
        try:
            from app.ambassadors import models as amb_models

            AmbModel = getattr(amb_models, "AmbassadorProfile", None) or getattr(
                amb_models, "Ambassador", None
            )
        except Exception:
            AmbModel = None
        if AmbModel is not None:
            row = db.scalars(
                select(AmbModel).where(AmbModel.user_id == user.id).limit(1)
            ).first()
            if row is not None:
                summary["profile_id"] = str(getattr(row, "id", ""))
                summary["status"] = getattr(row, "status", None)
        # Conversion count if model exists
        try:
            from app.promos.models import ReferralConversion

            count = db.scalar(
                select(func.count())
                .select_from(ReferralConversion)
                .where(ReferralConversion.ambassador_user_id == user.id)
            )
            if count is not None:
                summary["conversion_count"] = int(count)
        except Exception:
            pass
    except Exception:
        pass
    return {"ok": True, "summary": summary}
