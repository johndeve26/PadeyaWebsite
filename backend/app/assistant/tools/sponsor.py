"""Sponsor-scoped tools — overview, campaigns, deals (aggregates only)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.users.models import User
from app.users.service import user_has_role


def _resolve_sponsor_id(
    db: Session, user: User, args: dict[str, Any] | None
) -> UUID | None:
    from app.sponsor_profiles.service import list_user_sponsor_workspaces

    args = args or {}
    raw = args.get("sponsor_id")
    if raw:
        try:
            return UUID(str(raw))
        except (ValueError, TypeError):
            pass
    slug = str(args.get("sponsor_slug") or "").strip()
    workspaces = list_user_sponsor_workspaces(db, user=user)
    if slug:
        for ws in workspaces:
            if (ws.get("slug") or "").lower() == slug.lower():
                return ws["sponsor_id"]
    return workspaces[0]["sponsor_id"] if workspaces else None


def _safe_deal(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("id") or ""),
        "title": row.get("title") or row.get("name"),
        "status": row.get("status"),
        "package_type": row.get("package_type"),
        "amount": row.get("amount"),
        "currency": row.get("currency"),
        "host_display_name": row.get("host_display_name"),
    }


def get_my_sponsor_overview(
    db: Session, *, user: User | None, args: dict[str, Any] | None = None, **_: Any
) -> dict[str, Any]:
    if user is None:
        return {"ok": False, "error": "auth_required"}
    if not user_has_role(user, "sponsor", "super_admin"):
        return {"ok": False, "error": "forbidden"}

    sponsor_id = _resolve_sponsor_id(db, user, args)
    if sponsor_id is None:
        return {
            "ok": False,
            "error": "not_found",
            "detail": "No sponsor workspace linked to this account.",
        }

    try:
        from app.sponsor_profiles.report_service import overview_report

        report = overview_report(db, user=user, sponsor_id=sponsor_id)
    except Exception as exc:
        return {"ok": False, "error": "lookup_failed", "detail": type(exc).__name__}

    inq = report.get("inquiries") or {}
    deals = report.get("deals") or {}
    pending = int(inq.get("pending") or 0)
    saved = int(report.get("saved_opportunities_count") or 0)
    deal_count = int(deals.get("total_deals") or deals.get("count") or 0)
    opted_in = int(inq.get("accepted") or 0)

    return {
        "ok": True,
        "dashboard_url": "/sponsor",
        "saved_opportunities_count": saved,
        "inquiries_pending": pending,
        "inquiries_total": int(inq.get("total") or 0),
        "deals_total": deal_count,
        "response_rate": report.get("response_rate"),
        "campaigns_by_status": report.get("campaigns_by_status") or {},
        "deals": deals,
        "summary": (
            f"Sponsor overview: {saved} saved opportunities, "
            f"{int(inq.get('total') or 0)} inquiries ({pending} pending), "
            f"{deal_count} deal(s), {opted_in} accepted inquiries."
        ),
    }


def list_my_sponsor_campaigns(
    db: Session, *, user: User | None, args: dict[str, Any] | None = None, **_: Any
) -> dict[str, Any]:
    if user is None:
        return {"ok": False, "error": "auth_required", "results": []}
    if not user_has_role(user, "sponsor", "super_admin"):
        return {"ok": False, "error": "forbidden", "results": []}

    sponsor_id = _resolve_sponsor_id(db, user, args)
    if sponsor_id is None:
        return {"ok": True, "results": [], "count": 0, "summary": "No sponsor workspace found."}

    limit = min(int((args or {}).get("limit") or 10), 25)
    results: list[dict[str, Any]] = []
    try:
        from app.sponsor_profiles.campaign_service import list_campaigns

        payload = list_campaigns(db, user=user, sponsor_id=sponsor_id)
        for row in (payload.get("items") or [])[:limit]:
            if not isinstance(row, dict):
                continue
            results.append(
                {
                    "id": str(row.get("id") or ""),
                    "name": row.get("name"),
                    "status": row.get("status"),
                    "objective": row.get("objective"),
                    "saved_items_count": row.get("saved_items_count"),
                    "inquiries_count": row.get("inquiries_count"),
                }
            )
    except Exception:
        results = []

    return {
        "ok": True,
        "results": results,
        "count": len(results),
        "dashboard_url": "/sponsor",
        "summary": f"You have {len(results)} sponsorship campaign(s).",
    }


def list_my_sponsor_deals(
    db: Session, *, user: User | None, args: dict[str, Any] | None = None, **_: Any
) -> dict[str, Any]:
    if user is None:
        return {"ok": False, "error": "auth_required", "results": []}
    if not user_has_role(user, "sponsor", "super_admin"):
        return {"ok": False, "error": "forbidden", "results": []}

    sponsor_id = _resolve_sponsor_id(db, user, args)
    if sponsor_id is None:
        return {"ok": True, "results": [], "count": 0, "summary": "No sponsor workspace found."}

    limit = min(int((args or {}).get("limit") or 10), 25)
    results: list[dict[str, Any]] = []
    try:
        from app.sponsorships.deals_service import sponsor_list_deals

        for row in sponsor_list_deals(db, user, sponsor_id)[:limit]:
            if isinstance(row, dict):
                results.append(_safe_deal(row))
    except Exception:
        results = []

    by_status: dict[str, int] = {}
    for row in results:
        st = str(row.get("status") or "unknown")
        by_status[st] = by_status.get(st, 0) + 1

    return {
        "ok": True,
        "results": results,
        "count": len(results),
        "deals_by_status": by_status,
        "dashboard_url": "/sponsor",
        "summary": f"You have {len(results)} sponsorship deal(s).",
    }


def list_my_sponsor_workspaces(
    db: Session, *, user: User | None, args: dict[str, Any] | None = None, **_: Any
) -> dict[str, Any]:
    if user is None:
        return {"ok": False, "error": "auth_required", "results": []}
    if not user_has_role(user, "sponsor", "super_admin"):
        return {"ok": False, "error": "forbidden", "results": []}

    results: list[dict[str, Any]] = []
    try:
        from app.sponsor_profiles.service import list_user_sponsor_workspaces

        for ws in list_user_sponsor_workspaces(db, user=user):
            results.append(
                {
                    "sponsor_id": str(ws.get("sponsor_id") or ""),
                    "display_name": ws.get("display_name"),
                    "slug": ws.get("slug"),
                    "role": ws.get("role"),
                    "verification_status": ws.get("verification_status"),
                }
            )
    except Exception:
        results = []

    return {
        "ok": True,
        "results": results,
        "count": len(results),
        "dashboard_url": "/sponsor",
        "summary": f"You have access to {len(results)} sponsor workspace(s).",
    }


def list_my_sponsor_opportunities(
    db: Session, *, user: User | None, args: dict[str, Any] | None = None, **_: Any
) -> dict[str, Any]:
    """Alias: open campaigns in the sponsor workspace."""
    return list_my_sponsor_campaigns(db, user=user, args=args)


def list_my_sponsor_applications(
    db: Session, *, user: User | None, args: dict[str, Any] | None = None, **_: Any
) -> dict[str, Any]:
    """Alias: sponsorship deals / inquiries pipeline."""
    deals = list_my_sponsor_deals(db, user=user, args=args)
    if not deals.get("ok"):
        return deals
    overview = get_my_sponsor_overview(db, user=user, args=args)
    pending = 0
    if overview.get("ok"):
        pending = int(overview.get("inquiries_pending") or 0)
    return {
        **deals,
        "inquiries_pending": pending,
        "summary": (
            f"{deals.get('summary', '')} {pending} pending inquiry(ies)."
            if pending
            else str(deals.get("summary") or "")
        ),
    }
