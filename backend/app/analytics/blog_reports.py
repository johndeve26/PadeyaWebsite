"""Backend-authoritative blog analytics aggregations."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analytics.models import AnalyticsEvent
from app.analytics.taxonomy import TrackedAction
from app.analytics.utils import visitor_identity
from app.blog.models import BlogAiOperation, BlogComment, BlogPost
from app.blog.studio.operations import serialize_operation

BLOG_ENGAGEMENT_ACTIONS = frozenset(
    {
        TrackedAction.BLOG_INDEX_VIEW,
        TrackedAction.BLOG_POST_VIEW,
        TrackedAction.BLOG_CARD_IMPRESSION,
        TrackedAction.BLOG_CARD_CLICK,
        TrackedAction.BLOG_SCROLL_MILESTONE,
        TrackedAction.BLOG_SHARE_CLICK,
        TrackedAction.BLOG_RELATED_CLICK,
        TrackedAction.BLOG_CTA_CLICK,
        TrackedAction.BLOG_FILTER_USED,
        TrackedAction.BLOG_CATEGORY_PAGE_VIEW,
        TrackedAction.BLOG_TAG_PAGE_VIEW,
        TrackedAction.BLOG_AUTHOR_PAGE_VIEW,
    }
)


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def resolve_blog_range(
    *,
    range_start: datetime | None = None,
    range_end: datetime | None = None,
    days: int = 30,
) -> tuple[datetime, datetime]:
    end = _as_utc(range_end) or datetime.now(UTC)
    start = _as_utc(range_start) or (end - timedelta(days=max(1, min(days, 366))))
    return start, end


def _is_public_row(row: AnalyticsEvent) -> bool:
    if row.is_bot:
        return False
    meta = row.event_metadata if isinstance(row.event_metadata, dict) else {}
    segment = str(meta.get("traffic_segment") or "").lower()
    return segment not in {"internal_admin"}


def _count_action(
    rows: list[AnalyticsEvent],
    action: str,
    *,
    public_only: bool = True,
) -> int:
    n = 0
    for r in rows:
        if r.event_name != action:
            continue
        if public_only and not _is_public_row(r):
            continue
        n += 1
    return n


def _unique_visitors(rows: list[AnalyticsEvent], *, public_only: bool = True) -> int:
    seen: set[str] = set()
    for r in rows:
        if public_only and not _is_public_row(r):
            continue
        ident = visitor_identity(
            user_id=r.user_id, anonymous_id=r.anonymous_id, session_id=r.session_id
        )
        if ident:
            seen.add(ident)
    return len(seen)


def _load_stream(
    db: Session,
    *,
    range_start: datetime,
    range_end: datetime,
    post_id: UUID | None = None,
    actions: frozenset[str] | None = None,
) -> list[AnalyticsEvent]:
    stmt = select(AnalyticsEvent).where(
        (
            (
                AnalyticsEvent.occurred_at.is_not(None)
                & (AnalyticsEvent.occurred_at >= range_start)
                & (AnalyticsEvent.occurred_at <= range_end)
            )
            | (
                AnalyticsEvent.occurred_at.is_(None)
                & (AnalyticsEvent.created_at >= range_start)
                & (AnalyticsEvent.created_at <= range_end)
            )
        )
    )
    if post_id is not None:
        stmt = stmt.where(
            AnalyticsEvent.entity_type == "blog_post",
            AnalyticsEvent.entity_id == post_id,
        )
    elif actions:
        stmt = stmt.where(AnalyticsEvent.event_name.in_(tuple(actions)))
    else:
        blog_actions = tuple(BLOG_ENGAGEMENT_ACTIONS) + (
            TrackedAction.BLOG_POST_PUBLISHED,
            TrackedAction.BLOG_POST_UNPUBLISHED,
            TrackedAction.BLOG_POST_ARCHIVED,
            TrackedAction.BLOG_AI_OPERATION,
            TrackedAction.BLOG_COMMENT_CREATED,
        )
        stmt = stmt.where(
            (AnalyticsEvent.entity_type == "blog_post")
            | (AnalyticsEvent.event_name.in_(blog_actions))
        )
    return list(db.scalars(stmt.order_by(AnalyticsEvent.created_at.asc())).all())


def build_admin_blog_summary(
    db: Session,
    *,
    range_start: datetime,
    range_end: datetime,
    include_internal: bool = False,
) -> dict:
    rows = _load_stream(db, range_start=range_start, range_end=range_end)
    public = include_internal

    def c(action: str) -> int:
        return _count_action(rows, action, public_only=not public)

    index_views = c(TrackedAction.BLOG_INDEX_VIEW)
    impressions = c(TrackedAction.BLOG_CARD_IMPRESSION)
    card_clicks = c(TrackedAction.BLOG_CARD_CLICK)
    post_views = c(TrackedAction.BLOG_POST_VIEW)
    scroll_50 = 0
    scroll_100 = 0
    for r in rows:
        if r.event_name != TrackedAction.BLOG_SCROLL_MILESTONE:
            continue
        if not public and not _is_public_row(r):
            continue
        meta = r.event_metadata if isinstance(r.event_metadata, dict) else {}
        milestone = int(meta.get("read_milestone") or meta.get("scroll_pct") or 0)
        if milestone >= 100:
            scroll_100 += 1
        elif milestone >= 50:
            scroll_50 += 1
    shares = c(TrackedAction.BLOG_SHARE_CLICK)
    related = c(TrackedAction.BLOG_RELATED_CLICK)
    ctas = c(TrackedAction.BLOG_CTA_CLICK)
    filters = c(TrackedAction.BLOG_FILTER_USED)
    comments = c(TrackedAction.BLOG_COMMENT_CREATED)
    publishes = c(TrackedAction.BLOG_POST_PUBLISHED)
    bot_rows = sum(1 for r in rows if r.is_bot)
    internal_rows = sum(
        1
        for r in rows
        if isinstance(r.event_metadata, dict)
        and str(r.event_metadata.get("traffic_segment") or "") == "internal_admin"
    )

    # Top posts by public post views
    by_post: dict[UUID, dict] = {}
    for r in rows:
        if r.entity_type != "blog_post" or r.entity_id is None:
            continue
        if not public and not _is_public_row(r):
            continue
        bucket = by_post.setdefault(
            r.entity_id,
            {
                "post_id": str(r.entity_id),
                "views": 0,
                "shares": 0,
                "cta_clicks": 0,
                "scroll_50": 0,
                "comments": 0,
            },
        )
        if r.event_name == TrackedAction.BLOG_POST_VIEW:
            bucket["views"] += 1
        elif r.event_name == TrackedAction.BLOG_SHARE_CLICK:
            bucket["shares"] += 1
        elif r.event_name == TrackedAction.BLOG_CTA_CLICK:
            bucket["cta_clicks"] += 1
        elif r.event_name == TrackedAction.BLOG_COMMENT_CREATED:
            bucket["comments"] += 1
        elif r.event_name == TrackedAction.BLOG_SCROLL_MILESTONE:
            meta = r.event_metadata if isinstance(r.event_metadata, dict) else {}
            if int(meta.get("read_milestone") or meta.get("scroll_pct") or 0) >= 50:
                bucket["scroll_50"] += 1

    post_ids = list(by_post.keys())
    titles: dict[UUID, tuple[str, str | None]] = {}
    if post_ids:
        for p in db.scalars(select(BlogPost).where(BlogPost.id.in_(post_ids))).all():
            titles[p.id] = (p.title, p.slug)
    top_posts = sorted(by_post.values(), key=lambda x: x["views"], reverse=True)[:15]
    for item in top_posts:
        pid = UUID(item["post_id"])
        title, slug = titles.get(pid, ("Unknown", None))
        item["title"] = title
        item["slug"] = slug

    # Publishing cadence — group in Python for SQLite/Postgres portability
    published_posts = list(
        db.scalars(
            select(BlogPost).where(
                BlogPost.published_at.is_not(None),
                BlogPost.published_at >= range_start,
                BlogPost.published_at <= range_end,
                BlogPost.status == "published",
            )
        ).all()
    )
    cadence_map: dict[str, int] = {}
    for p in published_posts:
        when = _as_utc(p.published_at)
        if when is None:
            continue
        day = when.date().isoformat()
        cadence_map[day] = cadence_map.get(day, 0) + 1
    cadence = [
        {"date": d, "published": cadence_map[d]} for d in sorted(cadence_map.keys())
    ]

    draft_ages: list[float] = []
    for r in rows:
        if r.event_name != TrackedAction.BLOG_POST_PUBLISHED:
            continue
        meta = r.event_metadata if isinstance(r.event_metadata, dict) else {}
        age = meta.get("draft_age_hours")
        if isinstance(age, (int, float)):
            draft_ages.append(float(age))

    ai_ops = list(
        db.scalars(
            select(BlogAiOperation).where(
                BlogAiOperation.created_at >= range_start,
                BlogAiOperation.created_at <= range_end,
            )
        ).all()
    )
    ai_success = sum(1 for o in ai_ops if o.success)
    ai_by_op: dict[str, int] = {}
    for o in ai_ops:
        ai_by_op[o.operation] = ai_by_op.get(o.operation, 0) + 1

    def rate(num: int, den: int) -> float:
        if den <= 0:
            return 0.0
        return round(100.0 * num / den, 2)

    engagement_rows = [
        r
        for r in rows
        if r.event_name in BLOG_ENGAGEMENT_ACTIONS
        and (public or _is_public_row(r))
    ]

    return {
        "range_start": range_start.isoformat(),
        "range_end": range_end.isoformat(),
        "include_internal": include_internal,
        "totals": {
            "index_views": index_views,
            "card_impressions": impressions,
            "card_clicks": card_clicks,
            "post_views": post_views,
            "unique_visitors": _unique_visitors(
                [r for r in rows if r.event_name == TrackedAction.BLOG_POST_VIEW],
                public_only=not public,
            ),
            "scroll_50": scroll_50,
            "scroll_100": scroll_100,
            "shares": shares,
            "related_clicks": related,
            "cta_clicks": ctas,
            "filter_uses": filters,
            "comments": comments,
            "publishes": publishes,
            "bot_events": bot_rows,
            "internal_admin_events": internal_rows,
        },
        "funnel": {
            "index_views": index_views,
            "card_impressions": impressions,
            "card_clicks": card_clicks,
            "post_views": post_views,
            "scroll_50": scroll_50,
            "engaged": shares + ctas + related + comments,
            "click_through_rate": rate(card_clicks, impressions),
            "view_from_click_rate": rate(post_views, card_clicks),
            "read_50_rate": rate(scroll_50, post_views),
            "share_rate": rate(shares, post_views),
            "cta_rate": rate(ctas, post_views),
        },
        "top_posts": top_posts,
        "publishing": {
            "posts_published": publishes
            or sum(int(x["published"]) for x in cadence),
            "cadence": cadence,
            "avg_draft_age_hours": (
                round(sum(draft_ages) / len(draft_ages), 2) if draft_ages else None
            ),
            "draft_age_samples": len(draft_ages),
        },
        "ai_studio": {
            "operations": len(ai_ops),
            "successes": ai_success,
            "success_rate": rate(ai_success, len(ai_ops)),
            "by_operation": [
                {"operation": k, "count": v}
                for k, v in sorted(ai_by_op.items(), key=lambda x: -x[1])
            ],
        },
        "timeseries": _daily_counts(engagement_rows, public_only=not public),
    }


def _daily_counts(
    rows: list[AnalyticsEvent], *, public_only: bool
) -> list[dict]:
    buckets: dict[str, dict[str, int]] = {}
    for r in rows:
        if public_only and not _is_public_row(r):
            continue
        when = _as_utc(r.occurred_at or r.created_at)
        if when is None:
            continue
        day = when.date().isoformat()
        bucket = buckets.setdefault(
            day,
            {
                "date": day,
                "post_views": 0,
                "shares": 0,
                "cta_clicks": 0,
                "card_clicks": 0,
            },
        )
        if r.event_name == TrackedAction.BLOG_POST_VIEW:
            bucket["post_views"] += 1
        elif r.event_name == TrackedAction.BLOG_SHARE_CLICK:
            bucket["shares"] += 1
        elif r.event_name == TrackedAction.BLOG_CTA_CLICK:
            bucket["cta_clicks"] += 1
        elif r.event_name == TrackedAction.BLOG_CARD_CLICK:
            bucket["card_clicks"] += 1
    return [buckets[k] for k in sorted(buckets.keys())]


def build_admin_blog_post_analytics(
    db: Session,
    *,
    post_id: UUID,
    range_start: datetime,
    range_end: datetime,
    include_internal: bool = False,
) -> dict | None:
    post = db.get(BlogPost, post_id)
    if post is None or post.archived_at is not None:
        return None
    rows = _load_stream(
        db, range_start=range_start, range_end=range_end, post_id=post_id
    )
    public = include_internal

    def c(action: str) -> int:
        return _count_action(rows, action, public_only=not public)

    post_views = c(TrackedAction.BLOG_POST_VIEW)
    scroll_milestones: dict[str, int] = {"25": 0, "50": 0, "75": 0, "100": 0}
    for r in rows:
        if r.event_name != TrackedAction.BLOG_SCROLL_MILESTONE:
            continue
        if not public and not _is_public_row(r):
            continue
        meta = r.event_metadata if isinstance(r.event_metadata, dict) else {}
        m = int(meta.get("read_milestone") or meta.get("scroll_pct") or 0)
        key = str(m) if str(m) in scroll_milestones else None
        if key:
            scroll_milestones[key] += 1
        elif m >= 100:
            scroll_milestones["100"] += 1
        elif m >= 75:
            scroll_milestones["75"] += 1
        elif m >= 50:
            scroll_milestones["50"] += 1
        elif m >= 25:
            scroll_milestones["25"] += 1

    sources: dict[str, int] = {}
    devices: dict[str, int] = {}
    for r in rows:
        if r.event_name != TrackedAction.BLOG_POST_VIEW:
            continue
        if not public and not _is_public_row(r):
            continue
        src = (r.utm_source or r.source or "direct")[:80]
        sources[src] = sources.get(src, 0) + 1
        device = (r.device_type or "unknown")[:32]
        devices[device] = devices.get(device, 0) + 1

    share_channels: dict[str, int] = {}
    for r in rows:
        if r.event_name != TrackedAction.BLOG_SHARE_CLICK:
            continue
        if not public and not _is_public_row(r):
            continue
        meta = r.event_metadata if isinstance(r.event_metadata, dict) else {}
        ch = str(meta.get("share_channel") or "unknown")[:40]
        share_channels[ch] = share_channels.get(ch, 0) + 1

    cta_breakdown: dict[str, int] = {}
    for r in rows:
        if r.event_name != TrackedAction.BLOG_CTA_CLICK:
            continue
        if not public and not _is_public_row(r):
            continue
        meta = r.event_metadata if isinstance(r.event_metadata, dict) else {}
        cta = str(meta.get("cta_id") or meta.get("cta_path") or "unknown")[:80]
        cta_breakdown[cta] = cta_breakdown.get(cta, 0) + 1

    comment_count = db.scalar(
        select(func.count())
        .select_from(BlogComment)
        .where(
            BlogComment.post_id == post_id,
            BlogComment.status == "published",
            BlogComment.archived_at.is_(None),
            BlogComment.created_at >= range_start,
            BlogComment.created_at <= range_end,
        )
    )

    ai_ops = list(
        db.scalars(
            select(BlogAiOperation)
            .where(
                BlogAiOperation.post_id == post_id,
                BlogAiOperation.created_at >= range_start,
                BlogAiOperation.created_at <= range_end,
            )
            .order_by(BlogAiOperation.created_at.desc())
            .limit(40)
        ).all()
    )

    draft_age = None
    for r in rows:
        if r.event_name != TrackedAction.BLOG_POST_PUBLISHED:
            continue
        meta = r.event_metadata if isinstance(r.event_metadata, dict) else {}
        age = meta.get("draft_age_hours")
        if isinstance(age, (int, float)):
            draft_age = float(age)
            break
    if draft_age is None and post.published_at and post.created_at:
        created = _as_utc(post.created_at)
        published = _as_utc(post.published_at)
        if created and published and published >= created:
            draft_age = round((published - created).total_seconds() / 3600.0, 2)

    def rate(num: int, den: int) -> float:
        if den <= 0:
            return 0.0
        return round(100.0 * num / den, 2)

    shares = c(TrackedAction.BLOG_SHARE_CLICK)
    ctas = c(TrackedAction.BLOG_CTA_CLICK)
    related = c(TrackedAction.BLOG_RELATED_CLICK)

    return {
        "post": {
            "id": str(post.id),
            "title": post.title,
            "slug": post.slug,
            "status": post.status,
            "published_at": post.published_at.isoformat() if post.published_at else None,
            "created_at": post.created_at.isoformat() if post.created_at else None,
        },
        "range_start": range_start.isoformat(),
        "range_end": range_end.isoformat(),
        "include_internal": include_internal,
        "totals": {
            "post_views": post_views,
            "unique_visitors": _unique_visitors(
                [r for r in rows if r.event_name == TrackedAction.BLOG_POST_VIEW],
                public_only=not public,
            ),
            "scroll_milestones": scroll_milestones,
            "shares": shares,
            "related_clicks": related,
            "cta_clicks": ctas,
            "comments": int(comment_count or 0),
            "bot_events": sum(1 for r in rows if r.is_bot),
            "internal_admin_events": sum(
                1
                for r in rows
                if isinstance(r.event_metadata, dict)
                and str(r.event_metadata.get("traffic_segment") or "")
                == "internal_admin"
            ),
        },
        "rates": {
            "read_50_rate": rate(scroll_milestones["50"] + scroll_milestones["75"] + scroll_milestones["100"], post_views),
            "read_100_rate": rate(scroll_milestones["100"], post_views),
            "share_rate": rate(shares, post_views),
            "cta_rate": rate(ctas, post_views),
        },
        "sources": [
            {"source": k, "views": v}
            for k, v in sorted(sources.items(), key=lambda x: -x[1])[:12]
        ],
        "devices": [
            {"device": k, "views": v}
            for k, v in sorted(devices.items(), key=lambda x: -x[1])
        ],
        "share_channels": [
            {"channel": k, "count": v}
            for k, v in sorted(share_channels.items(), key=lambda x: -x[1])
        ],
        "cta_breakdown": [
            {"cta": k, "count": v}
            for k, v in sorted(cta_breakdown.items(), key=lambda x: -x[1])
        ],
        "publishing": {
            "draft_age_hours": draft_age,
            "status": post.status,
        },
        "ai_studio": {
            "operations": len(ai_ops),
            "successes": sum(1 for o in ai_ops if o.success),
            "recent": [serialize_operation(o) for o in ai_ops[:10]],
        },
        "timeseries": _daily_counts(rows, public_only=not public),
    }
