"""Analytics service: access control, dashboards, CSV exports."""

from __future__ import annotations

import csv
import io
from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.analytics.aggregations import (
    build_admin_events,
    build_admin_hosts,
    build_admin_platform_summary,
    build_admin_revenue,
    build_admin_support,
    build_event_analytics,
    build_host_analytics,
    resolve_range,
)
from app.analytics.constants import MAX_EXPORT_ROWS
from app.analytics.event_detail_reports import (
    build_admin_channel_performance,
    build_admin_event_bundle,
    build_admin_event_compare,
    build_admin_event_leaderboard,
    build_event_ambassadors,
    build_event_audience,
    build_event_funnel,
    build_event_overview,
    build_event_promos,
    build_event_sources,
    build_event_tickets,
    build_event_timeseries,
    export_event_analytics_csv_rows,
)
from app.analytics.event_filters import EventAnalyticsFilters
from app.analytics.schemas import (
    TrackBatchItemResult,
    TrackBatchRequest,
    TrackBatchResponse,
    TrackClickRequest,
    TrackConversionRequest,
    TrackEventRequest,
    TrackImpressionRequest,
    TrackPageViewRequest,
)
from app.analytics.tracking import (
    record_analytics_event,
    record_conversion,
    record_event_click,
    record_event_impression,
    record_page_view,
)
from app.core.audit import write_audit_log
from app.core.config import get_settings
from app.events.models import Event
from app.hosts.team_access import require_host_event_permission, require_host_for_permission
from app.users.models import User
from app.users.service import user_has_permission


def _enrich_client_payload(
    payload: TrackEventRequest,
    *,
    user: User | None,
    client_ip: str | None,
    user_agent: str | None,
    referrer: str | None,
) -> TrackEventRequest:
    """Fill server-owned dimensions when the client omitted them."""
    settings = get_settings()
    if not payload.user_agent and user_agent:
        object.__setattr__(payload, "user_agent", user_agent[:500])
    if not payload.referrer and referrer:
        object.__setattr__(payload, "referrer", referrer[:500])
    if not payload.environment:
        object.__setattr__(payload, "environment", settings.app_env[:32])
    if not payload.session_id and payload.anonymous_id:
        # Soft session from anon — client should send session_id; keep optional
        pass
    _ = client_ip  # hashed in dimensions write path
    _ = user  # attached as user_id on write
    return payload


def track_event(
    db: Session,
    *,
    payload: TrackEventRequest,
    user: User | None = None,
    client_ip: str | None = None,
) -> dict:
    row = record_analytics_event(db, payload=payload, user=user, client_ip=client_ip)
    db.commit()
    db.refresh(row)
    return {
        "accepted": True,
        "id": row.id,
        "tracked_action": row.event_name,
    }


def track_public(
    db: Session,
    *,
    payload: TrackEventRequest,
    user: User | None = None,
    client_ip: str | None = None,
    user_agent: str | None = None,
    referrer: str | None = None,
) -> dict:
    """Unified public track — requires known taxonomy actions."""
    object.__setattr__(payload, "require_known_action", True)
    # Re-validate action under known-action rules
    from app.analytics.taxonomy import require_known_tracked_action

    raw = payload.tracked_action or payload.event_name or ""
    try:
        resolved = require_known_tracked_action(raw)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    object.__setattr__(payload, "tracked_action", resolved)
    object.__setattr__(payload, "event_name", resolved)
    object.__setattr__(payload, "analytics_event_name", resolved)

    _enrich_client_payload(
        payload,
        user=user,
        client_ip=client_ip,
        user_agent=user_agent,
        referrer=referrer,
    )
    return track_event(db, payload=payload, user=user, client_ip=client_ip)


def track_batch(
    db: Session,
    *,
    payload: TrackBatchRequest,
    user: User | None = None,
    client_ip: str | None = None,
    user_agent: str | None = None,
    referrer: str | None = None,
) -> TrackBatchResponse:
    results: list[TrackBatchItemResult] = []
    accepted = 0
    rejected = 0
    for index, item in enumerate(payload.events):
        try:
            result = track_public(
                db,
                payload=item,
                user=user,
                client_ip=client_ip,
                user_agent=user_agent,
                referrer=referrer,
            )
            results.append(
                TrackBatchItemResult(
                    accepted=True,
                    id=result["id"],
                    tracked_action=result.get("tracked_action"),
                    index=index,
                )
            )
            accepted += 1
        except HTTPException as exc:
            db.rollback()
            results.append(
                TrackBatchItemResult(
                    accepted=False,
                    error=str(exc.detail),
                    index=index,
                )
            )
            rejected += 1
        except Exception as exc:  # noqa: BLE001 — per-item isolation
            db.rollback()
            results.append(
                TrackBatchItemResult(
                    accepted=False,
                    error=str(exc)[:200],
                    index=index,
                )
            )
            rejected += 1
    return TrackBatchResponse(
        accepted_count=accepted,
        rejected_count=rejected,
        results=results,
    )


def track_page_view(
    db: Session,
    *,
    payload: TrackPageViewRequest,
    user: User | None = None,
    client_ip: str | None = None,
) -> dict:
    row = record_page_view(db, payload=payload, user=user, client_ip=client_ip)
    db.commit()
    db.refresh(row)
    return {
        "accepted": True,
        "id": row.id,
        "tracked_action": payload.tracked_action,
    }


def _can_view_host_analytics(
    user: User, db: Session | None = None, host_id: UUID | None = None
) -> bool:
    if user_has_permission(user, "analytics.view_own") or user_has_permission(
        user, "admin.full_access"
    ):
        return True
    if db is None:
        return False
    try:
        require_host_for_permission(
            db,
            user=user,
            host_id=host_id,
            permission="analytics.view_events",
        )
        return True
    except HTTPException:
        return False


def _can_view_platform_analytics(user: User) -> bool:
    return user_has_permission(user, "analytics.view_platform") or user_has_permission(
        user, "admin.full_access"
    )


def _can_export(user: User, db: Session | None = None) -> bool:
    if user_has_permission(user, "analytics.export") or user_has_permission(
        user, "admin.full_access"
    ):
        return True
    if db is None:
        return False
    try:
        require_host_for_permission(
            db, user=user, host_id=None, permission="analytics.export"
        )
        return True
    except HTTPException:
        return False


def track_impression(
    db: Session,
    *,
    payload: TrackImpressionRequest,
    user: User | None = None,
    client_ip: str | None = None,
) -> dict:
    row = record_event_impression(db, payload=payload, user=user, client_ip=client_ip)
    db.commit()
    db.refresh(row)
    return {
        "accepted": True,
        "id": row.id,
        "tracked_action": payload.tracked_action,
    }


def track_click(
    db: Session,
    *,
    payload: TrackClickRequest,
    user: User | None = None,
    client_ip: str | None = None,
) -> dict:
    row = record_event_click(db, payload=payload, user=user, client_ip=client_ip)
    db.commit()
    db.refresh(row)
    return {
        "accepted": True,
        "id": row.id,
        "tracked_action": payload.tracked_action,
    }


def track_conversion(
    db: Session,
    *,
    payload: TrackConversionRequest,
    user: User | None = None,
    client_ip: str | None = None,
) -> dict:
    row = record_conversion(db, payload=payload, user=user, client_ip=client_ip)
    db.commit()
    db.refresh(row)
    return {
        "accepted": True,
        "id": row.id,
        "tracked_action": payload.tracked_action or payload.stage,
    }


def get_host_analytics(
    db: Session,
    *,
    user: User,
    range_start: datetime | None = None,
    range_end: datetime | None = None,
    include_bots: bool = False,
) -> dict:
    if include_bots and not _can_view_platform_analytics(user):
        raise HTTPException(status_code=403, detail="Bot-inclusive analytics require admin access")
    host, _ = require_host_for_permission(
        db, user=user, host_id=None, permission="analytics.view_events"
    )
    start, end = resolve_range(range_start=range_start, range_end=range_end)
    return build_host_analytics(
        db,
        host_id=host.id,
        range_start=start,
        range_end=end,
        include_bots=include_bots,
    )


def get_host_event_analytics(
    db: Session,
    *,
    user: User,
    event_id: UUID,
    range_start: datetime | None = None,
    range_end: datetime | None = None,
    include_bots: bool = False,
) -> dict:
    if include_bots and not _can_view_platform_analytics(user):
        raise HTTPException(status_code=403, detail="Bot-inclusive analytics require admin access")
    host, event = require_host_event_permission(
        db,
        user=user,
        event_id=event_id,
        permission="analytics.view_events",
    )
    start, end = resolve_range(range_start=range_start, range_end=range_end)
    try:
        return build_event_analytics(
            db,
            host_id=host.id,
            event_id=event_id,
            range_start=start,
            range_end=end,
            include_bots=include_bots,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def get_admin_summary(
    db: Session,
    *,
    user: User,
    range_start: datetime | None = None,
    range_end: datetime | None = None,
) -> dict:
    if not _can_view_platform_analytics(user):
        raise HTTPException(status_code=403, detail="Not allowed to view platform analytics")
    start, end = resolve_range(range_start=range_start, range_end=range_end)
    return build_admin_platform_summary(db, range_start=start, range_end=end)


def get_admin_revenue(
    db: Session,
    *,
    user: User,
    range_start: datetime | None = None,
    range_end: datetime | None = None,
) -> dict:
    if not _can_view_platform_analytics(user):
        raise HTTPException(status_code=403, detail="Not allowed to view platform analytics")
    start, end = resolve_range(range_start=range_start, range_end=range_end)
    return build_admin_revenue(db, range_start=start, range_end=end)


def get_admin_events(
    db: Session,
    *,
    user: User,
    range_start: datetime | None = None,
    range_end: datetime | None = None,
) -> dict:
    if not _can_view_platform_analytics(user):
        raise HTTPException(status_code=403, detail="Not allowed to view platform analytics")
    start, end = resolve_range(range_start=range_start, range_end=range_end)
    return build_admin_events(db, range_start=start, range_end=end)


def get_admin_hosts(
    db: Session,
    *,
    user: User,
    range_start: datetime | None = None,
    range_end: datetime | None = None,
) -> dict:
    if not _can_view_platform_analytics(user):
        raise HTTPException(status_code=403, detail="Not allowed to view platform analytics")
    start, end = resolve_range(range_start=range_start, range_end=range_end)
    return build_admin_hosts(db, range_start=start, range_end=end)


def get_admin_support(db: Session, *, user: User) -> dict:
    if not _can_view_platform_analytics(user):
        raise HTTPException(status_code=403, detail="Not allowed to view platform analytics")
    return build_admin_support(db)


def _can_view_blog_analytics(user: User) -> bool:
    return (
        _can_view_platform_analytics(user)
        or user_has_permission(user, "admin.blog.view")
    )


def get_admin_blog_analytics(
    db: Session,
    *,
    user: User,
    range_start: datetime | None = None,
    range_end: datetime | None = None,
    include_internal: bool = False,
) -> dict:
    if not _can_view_blog_analytics(user):
        raise HTTPException(status_code=403, detail="Not allowed to view blog analytics")
    from app.analytics.blog_reports import build_admin_blog_summary, resolve_blog_range

    start, end = resolve_blog_range(range_start=range_start, range_end=range_end)
    if include_internal and not _can_view_platform_analytics(user):
        include_internal = False
    return build_admin_blog_summary(
        db,
        range_start=start,
        range_end=end,
        include_internal=include_internal,
    )


def get_admin_blog_post_analytics(
    db: Session,
    *,
    user: User,
    post_id: UUID,
    range_start: datetime | None = None,
    range_end: datetime | None = None,
    include_internal: bool = False,
) -> dict:
    if not _can_view_blog_analytics(user):
        raise HTTPException(status_code=403, detail="Not allowed to view blog analytics")
    from app.analytics.blog_reports import (
        build_admin_blog_post_analytics,
        resolve_blog_range,
    )

    start, end = resolve_blog_range(range_start=range_start, range_end=range_end)
    if include_internal and not _can_view_platform_analytics(user):
        include_internal = False
    data = build_admin_blog_post_analytics(
        db,
        post_id=post_id,
        range_start=start,
        range_end=end,
        include_internal=include_internal,
    )
    if data is None:
        raise HTTPException(status_code=404, detail="Blog post not found")
    return data


def _parse_event_filters(
    *,
    user: User,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    source: str | None = None,
    medium: str | None = None,
    campaign: str | None = None,
    ticket_type_id: UUID | None = None,
    device_type: str | None = None,
    city: str | None = None,
    include_bots: bool = False,
) -> EventAnalyticsFilters:
    if include_bots and not _can_view_platform_analytics(user):
        raise HTTPException(
            status_code=403,
            detail="Bot-inclusive analytics require admin access",
        )
    return EventAnalyticsFilters.from_query(
        date_from=date_from,
        date_to=date_to,
        source=source,
        medium=medium,
        campaign=campaign,
        ticket_type_id=ticket_type_id,
        device_type=device_type,
        city=city,
        include_bots=include_bots,
    )


def _require_host_event(db: Session, *, user: User, event_id: UUID) -> Event:
    _, event = require_host_event_permission(
        db,
        user=user,
        event_id=event_id,
        permission="analytics.view_events",
    )
    return event


def get_host_event_overview(
    db: Session,
    *,
    user: User,
    event_id: UUID,
    **filter_kwargs,
) -> dict:
    event = _require_host_event(db, user=user, event_id=event_id)
    filters = _parse_event_filters(user=user, **filter_kwargs)
    try:
        return build_event_overview(
            db, event_id=event.id, host_id=event.host_id, filters=filters
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def get_host_event_funnel(db: Session, *, user: User, event_id: UUID, **filter_kwargs) -> dict:
    event = _require_host_event(db, user=user, event_id=event_id)
    filters = _parse_event_filters(user=user, **filter_kwargs)
    try:
        return build_event_funnel(
            db, event_id=event.id, host_id=event.host_id, filters=filters
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def get_host_event_timeseries(
    db: Session, *, user: User, event_id: UUID, **filter_kwargs
) -> dict:
    event = _require_host_event(db, user=user, event_id=event_id)
    filters = _parse_event_filters(user=user, **filter_kwargs)
    try:
        return build_event_timeseries(
            db, event_id=event.id, host_id=event.host_id, filters=filters
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def get_host_event_sources(db: Session, *, user: User, event_id: UUID, **filter_kwargs) -> dict:
    event = _require_host_event(db, user=user, event_id=event_id)
    filters = _parse_event_filters(user=user, **filter_kwargs)
    try:
        return build_event_sources(
            db, event_id=event.id, host_id=event.host_id, filters=filters
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def get_host_event_tickets(db: Session, *, user: User, event_id: UUID, **filter_kwargs) -> dict:
    event = _require_host_event(db, user=user, event_id=event_id)
    filters = _parse_event_filters(user=user, **filter_kwargs)
    try:
        return build_event_tickets(
            db, event_id=event.id, host_id=event.host_id, filters=filters
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def get_host_event_audience(db: Session, *, user: User, event_id: UUID, **filter_kwargs) -> dict:
    event = _require_host_event(db, user=user, event_id=event_id)
    filters = _parse_event_filters(user=user, **filter_kwargs)
    try:
        return build_event_audience(
            db, event_id=event.id, host_id=event.host_id, filters=filters
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def get_host_event_promos(db: Session, *, user: User, event_id: UUID, **filter_kwargs) -> dict:
    event = _require_host_event(db, user=user, event_id=event_id)
    filters = _parse_event_filters(user=user, **filter_kwargs)
    try:
        return build_event_promos(
            db, event_id=event.id, host_id=event.host_id, filters=filters
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def get_host_event_ambassadors(
    db: Session, *, user: User, event_id: UUID, **filter_kwargs
) -> dict:
    event = _require_host_event(db, user=user, event_id=event_id)
    filters = _parse_event_filters(user=user, **filter_kwargs)
    try:
        return build_event_ambassadors(
            db, event_id=event.id, host_id=event.host_id, filters=filters
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def export_host_event_analytics_csv(
    db: Session,
    *,
    user: User,
    event_id: UUID,
    **filter_kwargs,
) -> str:
    _require_host_event(db, user=user, event_id=event_id)
    if not _can_export(user, db):
        raise HTTPException(status_code=403, detail="Export permission required")
    overview = get_host_event_overview(db, user=user, event_id=event_id, **filter_kwargs)
    funnel = get_host_event_funnel(db, user=user, event_id=event_id, **filter_kwargs)
    write_audit_log(
        db,
        action="analytics.export.host_event",
        actor_user_id=user.id,
        resource_type="event",
        resource_id=str(event_id),
    )
    db.commit()
    headers, rows = export_event_analytics_csv_rows(overview, funnel)
    return _csv_from_rows(headers, rows)


def get_admin_event_analytics(
    db: Session, *, user: User, event_id: UUID, **filter_kwargs
) -> dict:
    if not _can_view_platform_analytics(user):
        raise HTTPException(status_code=403, detail="Not allowed to view platform analytics")
    if db.get(Event, event_id) is None:
        raise HTTPException(status_code=404, detail="Event not found")
    filters = _parse_event_filters(user=user, **filter_kwargs)
    try:
        return build_admin_event_bundle(db, event_id=event_id, filters=filters)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _admin_event_slice(
    db: Session,
    *,
    user: User,
    event_id: UUID,
    builder,
    **filter_kwargs,
) -> dict:
    if not _can_view_platform_analytics(user):
        raise HTTPException(status_code=403, detail="Not allowed to view platform analytics")
    if db.get(Event, event_id) is None:
        raise HTTPException(status_code=404, detail="Event not found")
    filters = _parse_event_filters(user=user, **filter_kwargs)
    try:
        return builder(db, event_id=event_id, filters=filters)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def get_admin_event_funnel(db: Session, *, user: User, event_id: UUID, **filter_kwargs) -> dict:
    return _admin_event_slice(
        db, user=user, event_id=event_id, builder=build_event_funnel, **filter_kwargs
    )


def get_admin_event_timeseries(
    db: Session, *, user: User, event_id: UUID, **filter_kwargs
) -> dict:
    return _admin_event_slice(
        db, user=user, event_id=event_id, builder=build_event_timeseries, **filter_kwargs
    )


def get_admin_event_audience(
    db: Session, *, user: User, event_id: UUID, **filter_kwargs
) -> dict:
    return _admin_event_slice(
        db, user=user, event_id=event_id, builder=build_event_audience, **filter_kwargs
    )


def get_admin_event_promos(db: Session, *, user: User, event_id: UUID, **filter_kwargs) -> dict:
    return _admin_event_slice(
        db, user=user, event_id=event_id, builder=build_event_promos, **filter_kwargs
    )


def get_admin_event_ambassadors(
    db: Session, *, user: User, event_id: UUID, **filter_kwargs
) -> dict:
    return _admin_event_slice(
        db, user=user, event_id=event_id, builder=build_event_ambassadors, **filter_kwargs
    )


def export_admin_event_analytics_csv(
    db: Session,
    *,
    user: User,
    event_id: UUID,
    **filter_kwargs,
) -> str:
    if not _can_export(user) or not _can_view_platform_analytics(user):
        raise HTTPException(status_code=403, detail="Export permission required")
    filters = _parse_event_filters(user=user, **filter_kwargs)
    if db.get(Event, event_id) is None:
        raise HTTPException(status_code=404, detail="Event not found")
    overview = build_event_overview(db, event_id=event_id, filters=filters)
    funnel = build_event_funnel(db, event_id=event_id, filters=filters)
    write_audit_log(
        db,
        action="analytics.export.admin_event",
        actor_user_id=user.id,
        resource_type="event",
        resource_id=str(event_id),
    )
    db.commit()
    headers, rows = export_event_analytics_csv_rows(overview, funnel)
    return _csv_from_rows(headers, rows)


def get_admin_event_leaderboard(
    db: Session,
    *,
    user: User,
    sort_by: str = "revenue",
    limit: int = 50,
    **filter_kwargs,
) -> dict:
    if not _can_view_platform_analytics(user):
        raise HTTPException(status_code=403, detail="Not allowed to view platform analytics")
    filters = _parse_event_filters(user=user, **filter_kwargs)
    return build_admin_event_leaderboard(
        db, filters=filters, sort_by=sort_by, limit=limit
    )


def get_admin_channel_performance(
    db: Session,
    *,
    user: User,
    **filter_kwargs,
) -> dict:
    if not _can_view_platform_analytics(user):
        raise HTTPException(status_code=403, detail="Not allowed to view platform analytics")
    filters = _parse_event_filters(user=user, **filter_kwargs)
    return build_admin_channel_performance(db, filters=filters)


def get_admin_event_compare(
    db: Session,
    *,
    user: User,
    event_ids: list[UUID],
    **filter_kwargs,
) -> dict:
    if not _can_view_platform_analytics(user):
        raise HTTPException(status_code=403, detail="Not allowed to view platform analytics")
    if not event_ids:
        raise HTTPException(status_code=400, detail="Provide at least one event_id")
    filters = _parse_event_filters(user=user, **filter_kwargs)
    try:
        return build_admin_event_compare(db, event_ids=event_ids, filters=filters)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def export_admin_events_analytics_csv(
    db: Session,
    *,
    user: User,
    sort_by: str = "revenue",
    limit: int = 200,
    **filter_kwargs,
) -> str:
    if not _can_export(user) or not _can_view_platform_analytics(user):
        raise HTTPException(status_code=403, detail="Export permission required")
    data = get_admin_event_leaderboard(
        db, user=user, sort_by=sort_by, limit=limit, **filter_kwargs
    )
    write_audit_log(
        db,
        action="analytics.export.admin_events",
        actor_user_id=user.id,
        resource_type="platform",
        resource_id="events_leaderboard",
    )
    db.commit()
    headers = [
        "event_id",
        "host_id",
        "title",
        "host_display_name",
        "impressions",
        "detail_views",
        "checkout_starts",
        "purchases",
        "tickets_sold",
        "revenue",
        "conversion_rate",
    ]
    rows = [
        [
            r["event_id"],
            r["host_id"],
            r["title"],
            r["host_display_name"],
            r["impressions"],
            r["detail_views"],
            r["checkout_starts"],
            r["purchases"],
            r["tickets_sold"],
            r["revenue"],
            r["conversion_rate"],
        ]
        for r in data["events"]
    ]
    return _csv_from_rows(headers, rows)


def _csv_from_rows(headers: list[str], rows: list[list[object]]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    for row in rows[:MAX_EXPORT_ROWS]:
        writer.writerow(row)
    return buf.getvalue()


def export_host_analytics_csv(
    db: Session,
    *,
    user: User,
    range_start: datetime | None = None,
    range_end: datetime | None = None,
) -> str:
    if not _can_export(user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Export permission required",
        )

    data = get_host_analytics(
        db, user=user, range_start=range_start, range_end=range_end
    )
    write_audit_log(
        db,
        action="analytics.export.host",
        actor_user_id=user.id,
        resource_type="host",
        resource_id=str(data["host_id"]),
    )
    db.commit()

    rows: list[list[object]] = [
        ["tickets_sold", data["tickets_sold"]],
        ["revenue", data["revenue"]],
        ["check_ins", data["check_ins"]],
        ["no_shows", data["no_shows"]],
        ["page_views", data["page_views"]],
        ["event_impressions", data["event_impressions"]],
        ["event_clicks", data["event_clicks"]],
        ["checkout_starts", data["checkout_starts"]],
        ["checkout_completes", data["checkout_completes"]],
        ["conversion_rate", data["conversion_rate"]],
        ["repeat_buyers", data["repeat_buyers"]],
        ["unique_buyers", data["unique_buyers"]],
        ["vault_earnings", data["vault_earnings"]],
    ]
    for point in data["sales_over_time"]:
        rows.append([f"sales:{point['date']}", point["value"]])
    return _csv_from_rows(["metric", "value"], rows)


def export_admin_analytics_csv(
    db: Session,
    *,
    user: User,
    range_start: datetime | None = None,
    range_end: datetime | None = None,
) -> str:
    if not _can_export(user) or not _can_view_platform_analytics(user):
        raise HTTPException(status_code=403, detail="Export permission required")

    data = get_admin_summary(
        db, user=user, range_start=range_start, range_end=range_end
    )
    write_audit_log(
        db,
        action="analytics.export.admin",
        actor_user_id=user.id,
        resource_type="platform",
        resource_id="summary",
    )
    db.commit()

    rows = [
        ["total_users", data["total_users"]],
        ["total_hosts", data["total_hosts"]],
        ["total_events", data["total_events"]],
        ["tickets_sold", data["tickets_sold"]],
        ["gross_revenue", data["gross_revenue"]],
        ["platform_fees", data["platform_fees"]],
        ["refund_rate", data["refund_rate"]],
        ["refund_amount", data["refund_amount"]],
        ["payout_totals", data["payout_totals"]],
        ["vault_revenue", data["vault_revenue"]],
        ["failed_payments", data["failed_payments"]],
        ["support_volume", data["support_volume"]],
    ]
    return _csv_from_rows(["metric", "value"], rows)
