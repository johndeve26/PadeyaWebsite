"""Ambassador-scoped tools — referral stats, campaigns, links (aggregates only)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.users.models import User


def _money(value: object | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return str(value.quantize(Decimal("0.01")))
    return str(value)


def get_my_referral_summary(
    db: Session, *, user: User | None, args: dict[str, Any] | None = None, **_: Any
) -> dict[str, Any]:
    if user is None:
        return {"ok": False, "error": "auth_required"}

    referral: dict[str, Any] = {}
    earnings: dict[str, Any] = {}
    campaigns: list[dict[str, Any]] = []
    try:
        from app.ambassadors.service import list_my_campaigns, my_earnings
        from app.promos.reporting import get_ambassador_referral_summary

        referral = get_ambassador_referral_summary(db, user=user)
        earnings = my_earnings(db, user)
        campaigns = list_my_campaigns(db, user)
    except Exception:
        pass

    clicks = int(referral.get("clicks") or 0)
    converted = int(referral.get("converted_orders") or 0)
    active_campaigns = len(campaigns)
    confirmed = int(earnings.get("confirmed_conversions") or 0)
    paid = _money(earnings.get("paid_amount"))
    pending = _money(earnings.get("pending_amount"))

    parts = [
        f"{clicks} referral clicks",
        f"{converted} converted orders",
        f"{confirmed} confirmed conversions",
        f"{active_campaigns} active campaign(s)",
    ]
    if paid and paid != "0.00":
        parts.append(f"{paid} NGN paid")
    elif pending and pending != "0.00":
        parts.append(f"{pending} NGN pending")

    return {
        "ok": True,
        "dashboard_url": "/ambassador",
        "clicks": clicks,
        "conversion_rate": referral.get("conversion_rate"),
        "converted_orders": converted,
        "confirmed_conversions": confirmed,
        "active_campaigns": active_campaigns,
        "paid_amount": paid,
        "pending_amount": pending,
        "primary_referral_link": referral.get("primary_referral_link_path"),
        "summary": "Ambassador stats: " + ", ".join(parts) + ".",
    }


def get_my_ambassador_earnings(
    db: Session, *, user: User | None, args: dict[str, Any] | None = None, **_: Any
) -> dict[str, Any]:
    if user is None:
        return {"ok": False, "error": "auth_required"}

    domain: dict[str, Any] = {}
    promos: dict[str, Any] = {}
    try:
        from app.ambassadors.service import my_earnings
        from app.promos.service import get_my_ambassador_earnings_summary

        domain = my_earnings(db, user)
        promos = get_my_ambassador_earnings_summary(db, user)
    except Exception:
        domain = {}
        promos = {}

    tickets = int(promos.get("tickets_sold") or 0)
    revenue = _money(promos.get("revenue_generated"))
    payable = _money(domain.get("payable_amount") or promos.get("payable_earnings"))
    paid = _money(domain.get("paid_amount") or promos.get("paid_earnings"))

    summary = (
        f"Ambassador earnings: {tickets} tickets sold via your links"
        + (f", {revenue} NGN referred gross" if revenue and revenue != "0.00" else "")
        + (f", {payable or paid or '0.00'} NGN payable/paid." if payable or paid else ".")
    )

    return {
        "ok": True,
        "dashboard_url": "/ambassador",
        "tickets_sold": tickets,
        "revenue_generated": revenue,
        "payable_amount": payable,
        "paid_amount": paid,
        "confirmed_conversions": int(domain.get("confirmed_conversions") or 0),
        "summary": summary,
    }


def list_my_ambassador_campaigns(
    db: Session, *, user: User | None, args: dict[str, Any] | None = None, **_: Any
) -> dict[str, Any]:
    if user is None:
        return {"ok": False, "error": "auth_required", "results": []}

    limit = min(int((args or {}).get("limit") or 10), 25)
    results: list[dict[str, Any]] = []
    try:
        from app.ambassadors.service import list_my_campaigns

        for row in list_my_campaigns(db, user)[:limit]:
            if not isinstance(row, dict):
                continue
            results.append(
                {
                    "campaign_id": str(row.get("campaign_id") or ""),
                    "campaign_name": row.get("campaign_name") or row.get("name"),
                    "event_title": row.get("event_title"),
                    "event_slug": row.get("event_slug"),
                    "status": row.get("status"),
                    "ambassador_code": row.get("ambassador_code"),
                }
            )
    except Exception:
        results = []

    return {
        "ok": True,
        "results": results,
        "count": len(results),
        "dashboard_url": "/ambassador",
        "summary": f"You are in {len(results)} ambassador campaign(s).",
    }


def list_my_referral_links(
    db: Session, *, user: User | None, args: dict[str, Any] | None = None, **_: Any
) -> dict[str, Any]:
    if user is None:
        return {"ok": False, "error": "auth_required", "results": []}

    limit = min(int((args or {}).get("limit") or 10), 25)
    results: list[dict[str, Any]] = []
    try:
        from app.ambassadors.service import list_my_links

        for row in list_my_links(db, user)[:limit]:
            results.append(
                {
                    "ambassador_code": row.get("ambassador_code"),
                    "event_slug": row.get("event_slug"),
                    "share_url_path": row.get("share_url_path") or row.get("event_path"),
                }
            )
    except Exception:
        results = []

    return {
        "ok": True,
        "results": results,
        "count": len(results),
        "dashboard_url": "/ambassador",
        "summary": f"You have {len(results)} active referral link(s).",
    }
