"""Shared filters for per-event analytics reports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy.sql import ColumnElement

from app.analytics.aggregations import resolve_range
from app.analytics.models import AnalyticsEvent


@dataclass(frozen=True)
class EventAnalyticsFilters:
    date_from: datetime
    date_to: datetime
    source: str | None = None
    medium: str | None = None
    campaign: str | None = None
    ticket_type_id: UUID | None = None
    device_type: str | None = None
    city: str | None = None
    include_bots: bool = False

    @classmethod
    def from_query(
        cls,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        range_start: datetime | None = None,
        range_end: datetime | None = None,
        source: str | None = None,
        medium: str | None = None,
        campaign: str | None = None,
        ticket_type_id: UUID | None = None,
        device_type: str | None = None,
        city: str | None = None,
        include_bots: bool = False,
    ) -> "EventAnalyticsFilters":
        start, end = resolve_range(
            range_start=date_from or range_start,
            range_end=date_to or range_end,
        )
        return cls(
            date_from=start,
            date_to=end,
            source=(source or "").strip() or None,
            medium=(medium or "").strip() or None,
            campaign=(campaign or "").strip() or None,
            ticket_type_id=ticket_type_id,
            device_type=(device_type or "").strip().lower() or None,
            city=(city or "").strip() or None,
            include_bots=include_bots,
        )


def stream_time_column() -> ColumnElement:
    """Prefer occurred_at, fall back to received_at."""
    from sqlalchemy import func

    return func.coalesce(AnalyticsEvent.occurred_at, AnalyticsEvent.received_at)


def apply_stream_filters(
    clauses: list,
    filters: EventAnalyticsFilters,
    *,
    event_id: UUID,
    host_id: UUID | None = None,
) -> list:
    """Append common AnalyticsEvent filters for a single product event."""
    ts = stream_time_column()
    clauses.extend(
        [
            AnalyticsEvent.target_event_id == event_id,
            ts >= filters.date_from,
            ts <= filters.date_to,
        ]
    )
    if host_id is not None:
        clauses.append(AnalyticsEvent.host_id == host_id)
    if not filters.include_bots:
        clauses.append(AnalyticsEvent.is_bot.is_(False))
    if filters.source:
        clauses.append(
            (AnalyticsEvent.utm_source == filters.source)
            | (AnalyticsEvent.source == filters.source)
        )
    if filters.medium:
        clauses.append(
            (AnalyticsEvent.utm_medium == filters.medium)
            | (AnalyticsEvent.medium == filters.medium)
        )
    if filters.campaign:
        clauses.append(
            (AnalyticsEvent.utm_campaign == filters.campaign)
            | (AnalyticsEvent.campaign == filters.campaign)
        )
    if filters.device_type:
        clauses.append(AnalyticsEvent.device_type == filters.device_type)
    if filters.city:
        clauses.append(AnalyticsEvent.city == filters.city)
    return clauses


def metadata_ticket_type_matches(meta: dict | None, ticket_type_id: UUID | None) -> bool:
    if ticket_type_id is None:
        return True
    if not meta:
        return False
    raw = meta.get("ticket_type_id")
    if raw is None:
        return False
    return str(raw) == str(ticket_type_id)


def classify_traffic_source(
    *,
    source: str | None,
    medium: str | None,
    campaign: str | None = None,
) -> str:
    """Bucket attribution into report-friendly source categories."""
    src = (source or "").strip().lower()
    med = (medium or "").strip().lower()
    camp = (campaign or "").strip().lower()

    if "ambassador" in src or "ambassador" in med or "ambassador" in camp:
        return "ambassador"
    if med in {"cpc", "ppc", "paid", "paid_social", "display", "cpm"} or src in {
        "googleads",
        "facebookads",
        "meta_ads",
    }:
        return "paid"
    if med in {"email", "newsletter"} or src in {"email", "newsletter"}:
        return "email"
    if "whatsapp" in src or "whatsapp" in med or src in {"wa", "wa.me"}:
        return "whatsapp"
    if med in {"social", "social-network", "social_media"} or src in {
        "facebook",
        "instagram",
        "twitter",
        "x",
        "tiktok",
        "linkedin",
        "youtube",
        "snapchat",
    }:
        return "social"
    if med in {"organic", "seo"} or src in {"google", "bing", "yahoo", "duckduckgo"}:
        return "search"
    if med == "referral" or (src and med == "referral"):
        return "referral"
    if not src and not med:
        return "direct"
    if src in {"(direct)", "direct"} or med in {"(none)", "none"}:
        return "direct"
    if src or med:
        return "referral"
    return "unknown"
