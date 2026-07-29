"""Write-path helpers for analytics tracking tables."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.constants import CONVERSION_STAGES
from app.analytics.dedupe import claim_dedupe_key, claim_windowed, generate_dedupe_key
from app.analytics.dimensions import build_analytics_row_dimensions
from app.analytics.models import (
    AnalyticsEvent,
    ConversionEvent,
    EventClick,
    EventImpression,
    PageView,
)
from app.analytics.schemas import (
    AnalyticsDimensions,
    TrackClickRequest,
    TrackConversionRequest,
    TrackEventRequest,
    TrackImpressionRequest,
    TrackPageViewRequest,
)
from app.analytics.taxonomy import (
    FORBIDDEN_CLIENT_METADATA_KEYS,
    TrackedAction,
    is_server_only_action,
)
from app.analytics.utils import is_likely_bot
from app.core.config import get_settings
from app.events.models import Event
from app.users.models import User
from app.users.service import user_has_permission


def _find_by_request_id(db: Session, request_id: str | None) -> AnalyticsEvent | None:
    if not request_id:
        return None
    return db.scalar(
        select(AnalyticsEvent).where(AnalyticsEvent.request_id == request_id)
    )


def _reject_server_only(action: str | None) -> None:
    if action and is_server_only_action(action):
        raise HTTPException(
            status_code=403,
            detail=(
                f"{action} is a trusted server-side analytics action and "
                "cannot be recorded from the client"
            ),
        )


def _strip_client_revenue_metadata(meta: dict[str, Any]) -> dict[str, Any]:
    return {
        k: v
        for k, v in meta.items()
        if str(k).strip().lower() not in FORBIDDEN_CLIENT_METADATA_KEYS
    }


def _list_context(payload: AnalyticsDimensions) -> str | None:
    meta = payload.metadata if isinstance(payload.metadata, dict) else {}
    props = payload.properties if isinstance(payload.properties, dict) else {}
    raw = meta.get("list_context") or props.get("list_context")
    if raw is None:
        return None
    return str(raw).strip()[:64] or None


def _dims_from_payload(
    payload: AnalyticsDimensions,
    *,
    target_event_id: UUID | None = None,
    extra_metadata: dict[str, Any] | None = None,
    client_ip: str | None = None,
    default_source: str | None = None,
    allow_revenue_metadata: bool = False,
) -> dict[str, Any]:
    meta = {**(payload.metadata or {}), **(payload.properties or {}), **(extra_metadata or {})}
    if not allow_revenue_metadata:
        meta = _strip_client_revenue_metadata(meta)
    return build_analytics_row_dimensions(
        anonymous_id=payload.anonymous_id,
        request_id=payload.request_id,
        occurred_at=payload.occurred_at,
        source=payload.source or default_source,
        medium=payload.medium,
        campaign=payload.campaign,
        term=payload.term,
        content=payload.content,
        utm_source=payload.utm_source,
        utm_medium=payload.utm_medium,
        utm_campaign=payload.utm_campaign,
        utm_term=payload.utm_term,
        utm_content=payload.utm_content,
        referrer=payload.referrer,
        landing_page=payload.landing_page,
        path=payload.path,
        current_path=payload.current_path,
        previous_path=payload.previous_path,
        user_agent=payload.user_agent,
        device_type=payload.device_type,
        browser=payload.browser,
        os=payload.os,
        country=payload.country,
        city=payload.city,
        client_ip=client_ip,
        metadata=meta,
        is_bot=payload.is_bot,
        environment=payload.environment,
        app_version=payload.app_version,
        target_event_id=target_event_id,
    )


def _is_bot_payload(payload: AnalyticsDimensions, dims: dict[str, Any]) -> bool:
    return bool(dims.get("is_bot")) or is_likely_bot(payload.user_agent)


def record_analytics_event(
    db: Session,
    *,
    payload: TrackEventRequest,
    user: User | None = None,
    client_ip: str | None = None,
) -> AnalyticsEvent:
    existing = _find_by_request_id(db, payload.request_id)
    if existing is not None:
        return existing

    action = (payload.tracked_action or payload.event_name or "").strip().lower()
    _reject_server_only(action)
    entity_type = (payload.entity_type or "").strip().lower() or None
    is_blog_entity = entity_type == "blog_post"
    # Never put non-event UUIDs into target_event_id (FK → events.id).
    if is_blog_entity:
        target_id = payload.target_event_id
        entity_id = payload.entity_id
    else:
        target_id = payload.target_event_id or payload.entity_id
        entity_id = target_id or payload.entity_id
        if entity_type is None and target_id is not None:
            entity_type = "event"
    from app.runtime_settings import get_runtime_setting

    settings = get_settings()
    detail_dedupe = int(
        get_runtime_setting("analytics_detail_view_dedupe_seconds", db=db, settings=settings)
        or settings.analytics_detail_view_dedupe_seconds
    )
    impression_dedupe = int(
        get_runtime_setting("analytics_impression_dedupe_seconds", db=db, settings=settings)
        or settings.analytics_impression_dedupe_seconds
    )
    checkout_dedupe = int(
        get_runtime_setting("analytics_checkout_start_dedupe_seconds", db=db, settings=settings)
        or settings.analytics_checkout_start_dedupe_seconds
    )
    user_id = user.id if user else None

    if action == TrackedAction.BLOG_POST_VIEW and entity_id is not None:
        if not claim_windowed(
            db,
            scope="blog_post_view",
            window_seconds=detail_dedupe,
            session_id=payload.session_id,
            anonymous_id=payload.anonymous_id,
            user_id=user_id,
            request_id=payload.request_id,
            extra=str(entity_id),
        ):
            last = db.scalar(
                select(AnalyticsEvent)
                .where(
                    AnalyticsEvent.entity_type == "blog_post",
                    AnalyticsEvent.entity_id == entity_id,
                    AnalyticsEvent.event_name == action,
                )
                .order_by(AnalyticsEvent.created_at.desc())
                .limit(1)
            )
            if last is not None:
                return last

    if action == TrackedAction.BLOG_CARD_IMPRESSION and entity_id is not None:
        list_ctx = _list_context(payload) or "blog_index"
        if not claim_windowed(
            db,
            scope="blog_card_impression",
            window_seconds=impression_dedupe,
            session_id=payload.session_id,
            anonymous_id=payload.anonymous_id,
            user_id=user_id,
            list_context=list_ctx,
            request_id=payload.request_id,
            extra=str(entity_id),
        ):
            last = db.scalar(
                select(AnalyticsEvent)
                .where(
                    AnalyticsEvent.entity_type == "blog_post",
                    AnalyticsEvent.entity_id == entity_id,
                    AnalyticsEvent.event_name == action,
                )
                .order_by(AnalyticsEvent.created_at.desc())
                .limit(1)
            )
            if last is not None:
                return last

    if action == TrackedAction.EVENT_DETAIL_VIEW and target_id is not None:
        if not claim_windowed(
            db,
            scope="detail_view",
            window_seconds=detail_dedupe,
            target_event_id=target_id,
            session_id=payload.session_id,
            anonymous_id=payload.anonymous_id,
            user_id=user_id,
            request_id=payload.request_id,
        ):
            last = db.scalar(
                select(AnalyticsEvent)
                .where(
                    AnalyticsEvent.target_event_id == target_id,
                    AnalyticsEvent.event_name == action,
                    AnalyticsEvent.session_id == payload.session_id,
                )
                .order_by(AnalyticsEvent.created_at.desc())
                .limit(1)
            )
            if last is not None:
                return last

    if action in {
        TrackedAction.EVENT_CARD_IMPRESSION,
        TrackedAction.FEATURED_EVENT_IMPRESSION,
        TrackedAction.PADEYA_PICK_IMPRESSION,
        TrackedAction.FEATURED_PLACEMENT_IMPRESSION,
    } and target_id is not None:
        list_ctx = _list_context(payload)
        source = payload.source or (
            "featured"
            if action
            in {
                TrackedAction.FEATURED_EVENT_IMPRESSION,
                TrackedAction.PADEYA_PICK_IMPRESSION,
                TrackedAction.FEATURED_PLACEMENT_IMPRESSION,
            }
            else "listing"
        )
        if not claim_windowed(
            db,
            scope="impression",
            window_seconds=impression_dedupe,
            target_event_id=target_id,
            session_id=payload.session_id,
            anonymous_id=payload.anonymous_id,
            user_id=user_id,
            list_context=list_ctx or source,
            request_id=payload.request_id,
            extra=source,
        ):
            last = db.scalar(
                select(AnalyticsEvent)
                .where(
                    AnalyticsEvent.target_event_id == target_id,
                    AnalyticsEvent.event_name == action,
                )
                .order_by(AnalyticsEvent.created_at.desc())
                .limit(1)
            )
            if last is not None:
                return last

    if action in {
        TrackedAction.CHECKOUT_PAGE_VIEW,
        TrackedAction.CHECKOUT_START_CLICK,
        TrackedAction.CHECKOUT_STEP_STARTED,
    } and target_id is not None:
        order_raw = None
        if isinstance(payload.metadata, dict):
            order_raw = payload.metadata.get("order_id")
        order_id = None
        if order_raw:
            try:
                order_id = UUID(str(order_raw))
            except (TypeError, ValueError):
                order_id = None
        if not claim_windowed(
            db,
            scope="checkout_start",
            window_seconds=checkout_dedupe,
            target_event_id=target_id,
            session_id=payload.session_id,
            anonymous_id=payload.anonymous_id,
            user_id=user_id,
            order_id=order_id,
            request_id=payload.request_id,
        ):
            last = db.scalar(
                select(AnalyticsEvent)
                .where(
                    AnalyticsEvent.target_event_id == target_id,
                    AnalyticsEvent.event_name == action,
                )
                .order_by(AnalyticsEvent.created_at.desc())
                .limit(1)
            )
            if last is not None:
                return last

    if payload.request_id:
        dedupe = generate_dedupe_key("request_id", request_id=payload.request_id)
        if not claim_dedupe_key(
            db,
            dedupe_key=dedupe,
            scope="request_id",
            target_event_id=target_id,
            session_id=payload.session_id,
            anonymous_id=payload.anonymous_id,
            ttl_hours=None,
        ):
            existing = _find_by_request_id(db, payload.request_id)
            if existing is not None:
                return existing

    extra = {
        "tracked_action": action,
        "target_event_id": str(target_id) if target_id else None,
    }
    if payload.event_listing_id is not None:
        extra["event_listing_id"] = str(payload.event_listing_id)
    ctx = _list_context(payload)
    if ctx:
        extra["list_context"] = ctx
    if is_blog_entity and entity_id is not None:
        extra["blog_post_id"] = str(entity_id)
    if user is not None and (
        user_has_permission(user, "admin.blog.view")
        or user_has_permission(user, "admin.full_access")
        or user_has_permission(user, "analytics.view_platform")
    ):
        extra["traffic_segment"] = "internal_admin"

    dims = _dims_from_payload(
        payload,
        target_event_id=target_id,
        extra_metadata=extra,
        client_ip=client_ip,
    )
    row = AnalyticsEvent(
        event_name=action.strip().lower()[:64],
        entity_type=entity_type or ("event" if target_id else None),
        entity_id=entity_id,
        host_id=payload.host_id,
        user_id=user_id,
        session_id=payload.session_id,
        **dims,
    )
    db.add(row)
    db.flush()
    return row


def record_page_view(
    db: Session,
    *,
    payload: TrackPageViewRequest,
    user: User | None = None,
    client_ip: str | None = None,
) -> PageView:
    target_id = payload.target_event_id or payload.event_id
    action = payload.tracked_action or TrackedAction.EVENT_DETAIL_VIEW
    _reject_server_only(action)
    settings = get_settings()
    user_id = user.id if user else None

    dims_preview = _dims_from_payload(
        payload,
        target_event_id=target_id,
        extra_metadata={"tracked_action": action, "path": payload.path},
        client_ip=client_ip,
        default_source=payload.source,
    )
    is_bot = _is_bot_payload(payload, dims_preview)

    # Total views: always record PageView for humans (repeat visits count).
    row = PageView(
        path=payload.path.strip()[:500],
        host_id=payload.host_id,
        event_id=target_id,
        user_id=user_id,
        session_id=payload.session_id,
        referrer=payload.referrer,
    )
    db.add(row)

    # Unique detail_view on stream: once per session/event within window.
    write_unique_stream = True
    if action == TrackedAction.EVENT_DETAIL_VIEW and target_id is not None:
        write_unique_stream = claim_windowed(
            db,
            scope="detail_view",
            window_seconds=settings.analytics_detail_view_dedupe_seconds,
            target_event_id=target_id,
            session_id=payload.session_id,
            anonymous_id=payload.anonymous_id,
            user_id=user_id,
            request_id=payload.request_id,
        )

    # Bot traffic: keep PageView out of host defaults by flagging stream only.
    if is_bot:
        write_unique_stream = True  # still record bot stream for admin raw

    existing = _find_by_request_id(db, payload.request_id)
    if existing is None and write_unique_stream:
        dims = dict(dims_preview)
        if not dims.get("path"):
            dims["path"] = row.path
        if not dims.get("current_path"):
            dims["current_path"] = row.path
        if not dims.get("referrer"):
            dims["referrer"] = payload.referrer
        if payload.request_id:
            dedupe = generate_dedupe_key("request_id", request_id=payload.request_id)
            if not claim_dedupe_key(
                db,
                dedupe_key=dedupe,
                scope="request_id",
                target_event_id=target_id,
                session_id=payload.session_id,
                anonymous_id=payload.anonymous_id,
                ttl_hours=None,
            ):
                db.flush()
                return row
        db.add(
            AnalyticsEvent(
                event_name=action,
                entity_type="event" if target_id else "page",
                entity_id=target_id,
                host_id=payload.host_id,
                user_id=user_id,
                session_id=payload.session_id,
                **dims,
            )
        )
    db.flush()
    return row


def _resolve_event_host(db: Session, event_id: UUID) -> Event:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


def record_event_impression(
    db: Session,
    *,
    payload: TrackImpressionRequest,
    user: User | None = None,
    client_ip: str | None = None,
) -> EventImpression:
    event_id = payload.target_event_id or payload.event_id
    if event_id is None:
        raise HTTPException(status_code=400, detail="target_event_id is required")
    event = _resolve_event_host(db, event_id)
    action = payload.tracked_action or TrackedAction.EVENT_CARD_IMPRESSION
    _reject_server_only(action)
    settings = get_settings()
    user_id = user.id if user else None
    source = payload.source or (
        "featured"
        if action
        in {
            TrackedAction.FEATURED_EVENT_IMPRESSION,
            TrackedAction.PADEYA_PICK_IMPRESSION,
            TrackedAction.FEATURED_PLACEMENT_IMPRESSION,
        }
        else "listing"
    )
    list_ctx = _list_context(payload) or source

    claimed = claim_windowed(
        db,
        scope="impression",
        window_seconds=settings.analytics_impression_dedupe_seconds,
        target_event_id=event.id,
        session_id=payload.session_id,
        anonymous_id=payload.anonymous_id,
        user_id=user_id,
        list_context=list_ctx,
        request_id=payload.request_id,
        extra=source,
    )

    if not claimed:
        prev = db.scalar(
            select(EventImpression)
            .where(
                EventImpression.event_id == event.id,
                EventImpression.session_id == payload.session_id,
            )
            .order_by(EventImpression.created_at.desc())
            .limit(1)
        )
        if prev is not None:
            return prev

    dims = _dims_from_payload(
        payload,
        target_event_id=event.id,
        extra_metadata={
            "source": source,
            "tracked_action": action,
            "target_event_id": str(event.id),
            "event_listing_id": str(event.id),
            "list_context": list_ctx,
        },
        client_ip=client_ip,
        default_source=source,
    )
    is_bot = _is_bot_payload(payload, dims)

    row = EventImpression(
        event_id=event.id,
        host_id=event.host_id,
        user_id=user_id,
        session_id=payload.session_id,
        source=source,
    )
    db.add(row)
    if not is_bot:
        db.add(
            ConversionEvent(
                event_id=event.id,
                host_id=event.host_id,
                user_id=user_id,
                session_id=payload.session_id,
                stage="impression",
            )
        )

    existing = _find_by_request_id(db, payload.request_id)
    if existing is None:
        db.add(
            AnalyticsEvent(
                event_name=action,
                entity_type="event",
                entity_id=event.id,
                host_id=event.host_id,
                user_id=user_id,
                session_id=payload.session_id,
                **dims,
            )
        )
    db.flush()
    return row


def record_event_click(
    db: Session,
    *,
    payload: TrackClickRequest,
    user: User | None = None,
    client_ip: str | None = None,
) -> EventClick:
    event_id = payload.target_event_id or payload.event_id
    if event_id is None:
        raise HTTPException(status_code=400, detail="target_event_id is required")
    event = _resolve_event_host(db, event_id)
    action = payload.tracked_action or TrackedAction.EVENT_CARD_CLICK
    _reject_server_only(action)
    settings = get_settings()
    user_id = user.id if user else None

    dims = _dims_from_payload(
        payload,
        target_event_id=event.id,
        extra_metadata={
            "click_target": payload.click_target,
            "tracked_action": action,
            "target_event_id": str(event.id),
            "event_listing_id": str(event.id),
        },
        client_ip=client_ip,
        default_source=payload.source,
    )
    is_bot = _is_bot_payload(payload, dims)

    row = EventClick(
        event_id=event.id,
        host_id=event.host_id,
        user_id=user_id,
        session_id=payload.session_id,
        click_target=payload.click_target,
    )
    # Every human click counts.
    if not is_bot:
        db.add(row)
        db.add(
            ConversionEvent(
                event_id=event.id,
                host_id=event.host_id,
                user_id=user_id,
                session_id=payload.session_id,
                stage="click",
            )
        )

    # unique_clicks: claim windowed identity once (metadata flag on first)
    is_unique = claim_windowed(
        db,
        scope="unique_click",
        window_seconds=settings.analytics_unique_click_dedupe_seconds,
        target_event_id=event.id,
        session_id=payload.session_id,
        anonymous_id=payload.anonymous_id,
        user_id=user_id,
        request_id=None,
    )
    if isinstance(dims.get("event_metadata"), dict):
        dims["event_metadata"] = {
            **dims["event_metadata"],
            "unique_click": is_unique,
        }
        dims["properties"] = dims["event_metadata"]

    existing = _find_by_request_id(db, payload.request_id)
    if existing is None:
        # Always write stream click (including bots, flagged)
        db.add(
            AnalyticsEvent(
                event_name=action,
                entity_type="event",
                entity_id=event.id,
                host_id=event.host_id,
                user_id=user_id,
                session_id=payload.session_id,
                **dims,
            )
        )
    db.flush()
    return row


def record_conversion(
    db: Session,
    *,
    payload: TrackConversionRequest,
    user: User | None = None,
    client_ip: str | None = None,
) -> ConversionEvent:
    stage = (payload.stage or "").strip().lower()
    if stage not in CONVERSION_STAGES:
        raise HTTPException(status_code=400, detail="Invalid conversion stage")

    action = (payload.tracked_action or stage).strip().lower()
    stream_name = (
        action
        if action
        in {
            TrackedAction.PAYMENT_SUCCESS,
            TrackedAction.PAYMENT_FAILED,
            TrackedAction.TICKET_ISSUED,
            TrackedAction.CHECKOUT_PAGE_VIEW,
            TrackedAction.CHECKOUT_PAYMENT_STARTED,
            TrackedAction.CHECKOUT_ABANDONED,
            TrackedAction.CHECKOUT_STEP_STARTED,
            TrackedAction.CHECKOUT_START_CLICK,
        }
        else (
            TrackedAction.PAYMENT_SUCCESS
            if stage == "checkout_complete"
            else TrackedAction.PAYMENT_FAILED
            if stage == "payment_failed"
            else TrackedAction.CHECKOUT_PAGE_VIEW
            if stage == "checkout_start"
            else stage
        )
    )
    _reject_server_only(stream_name)
    _reject_server_only(stage)
    if stage in {"checkout_complete", "payment_failed"} or stream_name in {
        TrackedAction.PAYMENT_SUCCESS,
        TrackedAction.PAYMENT_FAILED,
        TrackedAction.TICKET_ISSUED,
    }:
        raise HTTPException(
            status_code=403,
            detail="Trusted conversion stages must be emitted server-side only",
        )

    # Clients cannot fake revenue amounts on conversion track.
    if payload.amount is not None:
        raise HTTPException(
            status_code=403,
            detail="amount cannot be set from the client track endpoint",
        )

    host_id = payload.host_id
    event_id = payload.target_event_id or payload.event_id
    if event_id is not None and host_id is None:
        event = db.get(Event, event_id)
        if event is not None:
            host_id = event.host_id

    settings = get_settings()
    user_id = user.id if user else None

    if stream_name in {
        TrackedAction.CHECKOUT_PAGE_VIEW,
        TrackedAction.CHECKOUT_START_CLICK,
        TrackedAction.CHECKOUT_STEP_STARTED,
    } or stage == "checkout_start":
        if event_id is not None and not claim_windowed(
            db,
            scope="checkout_start",
            window_seconds=settings.analytics_checkout_start_dedupe_seconds,
            target_event_id=event_id,
            session_id=payload.session_id,
            anonymous_id=payload.anonymous_id,
            user_id=user_id,
            order_id=payload.order_id,
            request_id=payload.request_id,
        ):
            # Return existing conversion row shape without inflating
            existing_conv = db.scalar(
                select(ConversionEvent)
                .where(
                    ConversionEvent.event_id == event_id,
                    ConversionEvent.session_id == payload.session_id,
                    ConversionEvent.stage.in_(("checkout_start", stream_name)),
                )
                .order_by(ConversionEvent.created_at.desc())
                .limit(1)
            )
            if existing_conv is not None:
                return existing_conv

    dims = _dims_from_payload(
        payload,
        target_event_id=event_id,
        extra_metadata={
            "tracked_action": stream_name,
            "stage": stage,
            "target_event_id": str(event_id) if event_id else None,
            "order_id": str(payload.order_id) if payload.order_id else None,
        },
        client_ip=client_ip,
        default_source=payload.source,
    )
    is_bot = _is_bot_payload(payload, dims)
    if is_bot:
        dims["is_bot"] = True

    row = ConversionEvent(
        event_id=event_id,
        host_id=host_id,
        user_id=user_id,
        session_id=payload.session_id,
        stage=stage,
        order_id=payload.order_id,
        amount=None,
    )
    db.add(row)

    existing = _find_by_request_id(db, payload.request_id)
    if existing is None:
        db.add(
            AnalyticsEvent(
                event_name=stream_name[:64],
                entity_type="event" if event_id else None,
                entity_id=event_id,
                host_id=host_id,
                user_id=user_id,
                session_id=payload.session_id,
                **dims,
            )
        )
    db.flush()
    return row
