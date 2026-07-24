"""Build scrubbed aggregate context for admin AI summaries."""

from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.constants import (
    FEATURE_ADMIN_DAILY_OPS,
    FEATURE_ADMIN_REPORTS_SUMMARY,
    FEATURE_ADMIN_REVENUE_SUMMARY,
    FEATURE_ADMIN_SUPPORT_QUEUE,
)
from app.ai.context_scrubber import scrub_context, scrub_value
from app.users.models import User
from app.users.service import user_has_permission

ADMIN_SUMMARY_SAFE_KEYS = frozenset(
    {
        "notes",
        "range_label",
        "support_snapshot",
        "reports_snapshot",
        "revenue_snapshot",
        "operations_snapshot",
        "top_events",
        "top_hosts",
        "category_trends",
        "suggested_review_links",
    }
)

OPEN_STATUSES = frozenset(
    {"open", "pending", "waiting_on_user", "escalated", "in_progress"}
)


def _perm_any(user: User, *codes: str) -> bool:
    return any(user_has_permission(user, c) for c in codes)


def _assert_feature_permission(user: User, feature: str) -> None:
    if not (
        user_has_permission(user, "ai.use_platform")
        or user_has_permission(user, "admin.full_access")
    ):
        raise HTTPException(status_code=403, detail="AI permission required")

    if feature == FEATURE_ADMIN_SUPPORT_QUEUE:
        if not _perm_any(
            user,
            "admin.support.view",
            "admin.support.view_all",
            "admin.full_access",
        ):
            raise HTTPException(status_code=403, detail="Support view permission required")
        return

    if feature == FEATURE_ADMIN_REVENUE_SUMMARY:
        if not _perm_any(user, "analytics.view_platform", "admin.full_access"):
            raise HTTPException(
                status_code=403, detail="Analytics view permission required"
            )
        return

    if feature == FEATURE_ADMIN_REPORTS_SUMMARY:
        if not _perm_any(
            user,
            "reviews.moderate",
            "admin.full_access",
        ):
            raise HTTPException(
                status_code=403, detail="Reports / moderation permission required"
            )
        return

    if feature == FEATURE_ADMIN_DAILY_OPS:
        if not _perm_any(
            user,
            "analytics.view_platform",
            "admin.full_access",
        ):
            raise HTTPException(
                status_code=403, detail="Operations summary permission required"
            )
        return


def _json_blob(data: object, *, max_len: int = 3500) -> str:
    try:
        return scrub_value(json.dumps(data, default=str), max_len=max_len)
    except Exception:
        return "{}"


def _support_queue_snapshot(db: Session) -> dict:
    from app.support.models import SupportCase

    cases = list(
        db.scalars(
            select(SupportCase)
            .where(SupportCase.status.in_(tuple(OPEN_STATUSES)))
            .order_by(SupportCase.updated_at.desc())
            .limit(200)
        ).all()
    )
    open_count = len(cases)
    urgent = sum(1 for c in cases if (c.priority or "").lower() == "urgent")
    high = sum(1 for c in cases if (c.priority or "").lower() == "high")
    by_category = Counter((c.category or "other") for c in cases)
    by_priority = Counter((c.priority or "normal") for c in cases)

    attention: list[dict] = []
    for c in cases:
        if (c.priority or "").lower() not in {"urgent", "high"}:
            continue
        attention.append(
            {
                "case_number": c.case_number,
                "priority": c.priority,
                "category": c.category,
                "status": c.status,
                "subject": scrub_value((c.subject or "")[:120], max_len=120),
            }
        )
        if len(attention) >= 8:
            break

    return {
        "open_tickets": open_count,
        "urgent_count": urgent,
        "high_priority_count": high,
        "by_category": dict(by_category.most_common(12)),
        "by_priority": dict(by_priority),
        "needs_fastest_attention": attention,
        "note": "Counts from open support tickets only. Message bodies excluded.",
    }


def _revenue_snapshot(db: Session, *, range_start: datetime, range_end: datetime) -> dict:
    from app.analytics.aggregations import build_admin_platform_summary, build_admin_revenue

    revenue = build_admin_revenue(db, range_start=range_start, range_end=range_end)
    summary = build_admin_platform_summary(
        db, range_start=range_start, range_end=range_end
    )

    merch_items = 0
    try:
        from app.payments.models import Order, OrderItem

        merch_items = int(
            db.scalar(
                select(func.count())
                .select_from(OrderItem)
                .join(Order, Order.id == OrderItem.order_id)
                .where(
                    Order.status == "paid",
                    Order.paid_at.is_not(None),
                    Order.paid_at >= range_start,
                    Order.paid_at <= range_end,
                    OrderItem.item_kind == "merch",
                )
            )
            or 0
        )
    except Exception:
        merch_items = 0

    return {
        "gross_revenue": str(revenue.get("gross_revenue")),
        "net_after_refunds": str(revenue.get("net_after_refunds")),
        "refund_amount": str(revenue.get("refund_amount")),
        "platform_fees": str(revenue.get("platform_fees")),
        "payout_totals": str(revenue.get("payout_totals")),
        "tickets_sold": summary.get("tickets_sold"),
        "merch_items_sold": merch_items,
        "failed_payments": summary.get("failed_payments"),
        "top_events": (summary.get("top_events") or [])[:5],
        "top_hosts": [
            {
                "display_name": h.get("display_name"),
                "username": h.get("username"),
                "revenue": h.get("revenue"),
            }
            for h in (summary.get("top_hosts") or [])[:5]
        ],
        "category_trends": (summary.get("category_trends") or [])[:8],
        "sales_points": len(revenue.get("sales_over_time") or []),
        "note": "Aggregate commerce totals only. No buyer PII or payment payloads.",
    }


def _reports_snapshot(db: Session) -> dict:
    from app.reviews.models import ReviewReport, VerifiedReview

    review_rows: list[dict] = []
    reports = list(
        db.scalars(
            select(ReviewReport)
            .where(ReviewReport.status == "open")
            .order_by(ReviewReport.created_at.desc())
            .limit(40)
        ).all()
    )
    reason_counts: Counter[str] = Counter()
    for r in reports:
        reason = scrub_value((r.reason or "unspecified")[:80], max_len=80)
        reason_counts[reason or "unspecified"] += 1
        review = db.get(VerifiedReview, r.review_id)
        review_rows.append(
            {
                "report_id": str(r.id)[-8:],
                "reason": reason,
                "rating": review.rating if review else None,
                "review_title": scrub_value(
                    (review.title or "")[:80], max_len=80
                )
                if review
                else "",
                "status": r.status,
            }
        )

    message_open = 0
    message_themes: list[dict] = []
    try:
        from app.messaging.models import MessageReport

        message_open = int(
            db.scalar(
                select(func.count())
                .select_from(MessageReport)
                .where(MessageReport.status.in_(("open", "pending", "under_review")))
            )
            or 0
        )
        msg_reports = list(
            db.scalars(
                select(MessageReport)
                .where(MessageReport.status.in_(("open", "pending", "under_review")))
                .order_by(MessageReport.created_at.desc())
                .limit(20)
            ).all()
        )
        theme_counts: Counter[str] = Counter()
        for mr in msg_reports:
            theme = scrub_value(
                (getattr(mr, "reason", None) or "abuse")[:60],
                max_len=60,
            )
            theme_counts[theme or "abuse"] += 1
            message_themes.append(
                {
                    "report_id": str(mr.id)[-8:],
                    "theme": theme,
                    "status": mr.status,
                }
            )
        message_themes = [
            {"theme": k, "count": v} for k, v in theme_counts.most_common(8)
        ]
    except Exception:
        message_open = 0
        message_themes = []

    return {
        "open_review_reports": len(reports),
        "review_reason_themes": dict(reason_counts.most_common(10)),
        "review_samples": review_rows[:12],
        "open_message_reports": message_open,
        "message_report_themes": message_themes,
        "note": (
            "Advisory only. AI must not hide, approve, reject, suspend, or warn. "
            "IDs are truncated display labels."
        ),
    }


def _operations_snapshot(
    db: Session, *, range_start: datetime, range_end: datetime
) -> dict:
    from app.analytics.aggregations import build_admin_platform_summary
    from app.events.models import Event
    from app.hosts.models import Host
    from app.users.models import User as UserModel

    summary = build_admin_platform_summary(
        db, range_start=range_start, range_end=range_end
    )
    new_users = int(
        db.scalar(
            select(func.count())
            .select_from(UserModel)
            .where(
                UserModel.created_at >= range_start,
                UserModel.created_at <= range_end,
            )
        )
        or 0
    )
    new_hosts = int(
        db.scalar(
            select(func.count())
            .select_from(Host)
            .where(Host.created_at >= range_start, Host.created_at <= range_end)
        )
        or 0
    )
    new_events = int(
        db.scalar(
            select(func.count())
            .select_from(Event)
            .where(Event.created_at >= range_start, Event.created_at <= range_end)
        )
        or 0
    )

    support = _support_queue_snapshot(db)
    reports = _reports_snapshot(db)

    return {
        "new_users": new_users,
        "new_hosts": new_hosts,
        "new_events": new_events,
        "tickets_sold": summary.get("tickets_sold"),
        "gross_revenue": str(summary.get("gross_revenue")),
        "refund_amount": str(summary.get("refund_amount")),
        "failed_payments": summary.get("failed_payments"),
        "support_open_tickets": support.get("open_tickets"),
        "support_urgent": support.get("urgent_count"),
        "open_review_reports": reports.get("open_review_reports"),
        "open_message_reports": reports.get("open_message_reports"),
        "top_events": (summary.get("top_events") or [])[:5],
        "note": "On-demand aggregate snapshot. Not a scheduled job.",
    }


def build_admin_summary_context(
    db: Session,
    *,
    user: User,
    feature: str,
    notes: str = "",
) -> tuple[dict[str, str], list[str]]:
    """Permission-gated aggregate context for admin AI summaries."""
    _assert_feature_permission(user, feature)

    from app.analytics.aggregations import resolve_range

    start, end = resolve_range()
    # Daily ops prefers a rolling 24h window when available
    if feature == FEATURE_ADMIN_DAILY_OPS:
        end = datetime.now(UTC)
        start = end - timedelta(hours=24)

    range_label = f"{start.isoformat()} → {end.isoformat()}"
    raw: dict[str, str] = {
        "notes": scrub_value(notes or "", max_len=500),
        "range_label": range_label,
        "support_snapshot": "",
        "reports_snapshot": "",
        "revenue_snapshot": "",
        "operations_snapshot": "",
        "top_events": "",
        "top_hosts": "",
        "category_trends": "",
        "suggested_review_links": "",
    }

    if feature == FEATURE_ADMIN_SUPPORT_QUEUE:
        snap = _support_queue_snapshot(db)
        raw["support_snapshot"] = _json_blob(snap)
        raw["suggested_review_links"] = (
            "/admin/support · /admin/support/settings · /support/refunds"
        )
    elif feature == FEATURE_ADMIN_REVENUE_SUMMARY:
        snap = _revenue_snapshot(db, range_start=start, range_end=end)
        raw["revenue_snapshot"] = _json_blob(snap)
        raw["top_events"] = _json_blob(snap.get("top_events") or [], max_len=1500)
        raw["top_hosts"] = _json_blob(snap.get("top_hosts") or [], max_len=1500)
        raw["category_trends"] = _json_blob(
            snap.get("category_trends") or [], max_len=1200
        )
        raw["suggested_review_links"] = (
            "/admin/analytics · /admin/analytics/revenue · /admin/refunds · /admin/payouts"
        )
    elif feature == FEATURE_ADMIN_REPORTS_SUMMARY:
        snap = _reports_snapshot(db)
        raw["reports_snapshot"] = _json_blob(snap)
        raw["suggested_review_links"] = (
            "/admin/reviews · /admin/message-reports · /admin/fan-connect/reports"
        )
    elif feature == FEATURE_ADMIN_DAILY_OPS:
        snap = _operations_snapshot(db, range_start=start, range_end=end)
        raw["operations_snapshot"] = _json_blob(snap)
        raw["support_snapshot"] = _json_blob(
            {
                "open_tickets": snap.get("support_open_tickets"),
                "urgent": snap.get("support_urgent"),
            },
            max_len=800,
        )
        raw["reports_snapshot"] = _json_blob(
            {
                "open_review_reports": snap.get("open_review_reports"),
                "open_message_reports": snap.get("open_message_reports"),
            },
            max_len=800,
        )
        raw["suggested_review_links"] = (
            "/admin · /admin/support · /admin/analytics · /admin/reviews · "
            "/admin/refunds · /admin/events/review"
        )

    scrubbed, redactions = scrub_context(raw, allowlist=ADMIN_SUMMARY_SAFE_KEYS)
    return scrubbed, redactions
