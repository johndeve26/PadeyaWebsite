"""Sponsor-scoped tools — opportunities and own applications."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.users.models import User
from app.users.service import user_has_role


def list_my_sponsor_opportunities(
    db: Session, *, user: User | None, args: dict[str, Any] | None = None, **_: Any
) -> dict[str, Any]:
    if user is None:
        return {"ok": False, "error": "auth_required", "results": []}
    if not user_has_role(user, "sponsor", "super_admin"):
        return {"ok": False, "error": "forbidden", "results": []}
    limit = min(int((args or {}).get("limit") or 10), 25)
    results: list[dict[str, Any]] = []
    try:
        from app.sponsor_profiles.campaign_service import list_campaigns

        campaigns = list_campaigns(db, limit=limit)  # type: ignore[call-arg]
        for row in campaigns or []:
            if isinstance(row, dict):
                results.append(
                    {
                        "id": str(row.get("id") or ""),
                        "title": row.get("title") or row.get("name"),
                        "status": row.get("status"),
                    }
                )
            else:
                results.append(
                    {
                        "id": str(getattr(row, "id", "")),
                        "title": getattr(row, "title", None)
                        or getattr(row, "name", None),
                        "status": getattr(row, "status", None),
                    }
                )
    except Exception:
        results = []
    return {
        "ok": True,
        "results": results[:limit],
        "count": len(results[:limit]),
        "dashboard_url": "/sponsor",
    }


def list_my_sponsor_applications(
    db: Session, *, user: User | None, args: dict[str, Any] | None = None, **_: Any
) -> dict[str, Any]:
    if user is None:
        return {"ok": False, "error": "auth_required", "results": []}
    if not user_has_role(user, "sponsor", "super_admin"):
        return {"ok": False, "error": "forbidden", "results": []}
    limit = min(int((args or {}).get("limit") or 10), 25)
    results: list[dict[str, Any]] = []
    try:
        # Prefer deals/applications tied to this user's sponsor profile
        from app.sponsor_profiles import models as sp_models

        Profile = getattr(sp_models, "SponsorProfile", None)
        if Profile is not None:
            profile = db.scalars(
                select(Profile).where(Profile.owner_user_id == user.id).limit(1)
            ).first()
            if profile is None and hasattr(Profile, "user_id"):
                profile = db.scalars(
                    select(Profile).where(Profile.user_id == user.id).limit(1)
                ).first()
            if profile is not None:
                results.append(
                    {
                        "profile_id": str(profile.id),
                        "status": getattr(profile, "status", None),
                        "note": "Open the sponsor dashboard for application details.",
                    }
                )
    except Exception:
        results = []
    return {
        "ok": True,
        "results": results[:limit],
        "count": len(results[:limit]),
        "dashboard_url": "/sponsor",
    }
