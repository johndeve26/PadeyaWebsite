"""Taxonomy naming + normalization for analytics tracked_action values."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.models import AnalyticsEvent, ConversionEvent
from app.analytics.taxonomy import (
    TrackedAction,
    normalize_tracked_action,
    require_known_tracked_action,
)
from app.analytics.trusted import emit_payment_success
from app.core.security import hash_password
from app.events.models import Event, TicketType
from app.hosts.models import Host, HostProfile
from app.users.models import User
from app.users.service import get_role_by_name


def _seed(db: Session) -> Event:
    user = User(
        email="tax-host@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Tax Host",
        is_active=True,
    )
    user.roles.append(get_role_by_name(db, "host"))
    db.add(user)
    db.flush()
    host = Host(
        user_id=user.id,
        display_name="Tax Host",
        slug="tax-host",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, bio="x"))
    start = datetime.now(UTC) + timedelta(days=2)
    event = Event(
        title="Taxonomy Night",
        slug="taxonomy-night",
        description="Enough characters for event description body.",
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=3),
        city="Lagos",
        status="published",
        featured=False,
        published_at=datetime.now(UTC),
    )
    db.add(event)
    db.flush()
    db.add(
        TicketType(
            event_id=event.id,
            name="GA",
            type="regular",
            price=Decimal("1000.00"),
            quantity=50,
            quantity_sold=0,
            quantity_reserved=0,
            min_per_order=1,
            max_per_order=4,
            visibility="public",
            status="active",
        )
    )
    db.commit()
    db.refresh(event)
    return event


def test_vault_actions_are_known():
    for name in (
        "vault_page_view",
        "vault_item_impression",
        "vault_item_click",
        "vault_item_view",
        "vault_unlock_click",
        "vault_unlock_success",
        "vault_unlock_failed",
        "vault_follow_unlock",
        "vault_ticket_unlock",
        "vault_media_open",
        "vault_download_click",
        "vault_purchase",
    ):
        assert require_known_tracked_action(name) == name


def test_normalize_legacy_aliases():
    assert (
        normalize_tracked_action("event_impression")
        == TrackedAction.EVENT_CARD_IMPRESSION
    )
    assert normalize_tracked_action("checkout_complete") == TrackedAction.PAYMENT_SUCCESS
    assert (
        normalize_tracked_action("page_view", path="/events/taxonomy-night")
        == TrackedAction.EVENT_DETAIL_VIEW
    )
    assert (
        normalize_tracked_action("page_view", path="/events")
        == TrackedAction.EVENT_LIST_VIEW
    )
    assert require_known_tracked_action("ticket_type_selected") == (
        TrackedAction.TICKET_TYPE_SELECTED
    )


def test_track_action_taxonomy_fields(client: TestClient, db_session: Session):
    event = _seed(db_session)
    res = client.post(
        "/api/v1/analytics/track/event",
        json={
            "tracked_action": "event_share_click",
            "analytics_event_name": "event_share_click",
            "target_event_id": str(event.id),
            "event_listing_id": str(event.id),
            "require_known_action": True,
            "properties": {"method": "clipboard"},
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["accepted"] is True
    assert body["tracked_action"] == TrackedAction.EVENT_SHARE_CLICK

    row = db_session.query(AnalyticsEvent).order_by(AnalyticsEvent.created_at.desc()).first()
    assert row is not None
    assert row.event_name == TrackedAction.EVENT_SHARE_CLICK
    assert row.entity_id == event.id
    assert row.properties["target_event_id"] == str(event.id)
    assert row.properties["tracked_action"] == TrackedAction.EVENT_SHARE_CLICK


def test_impression_accepts_target_event_id(client: TestClient, db_session: Session):
    event = _seed(db_session)
    res = client.post(
        "/api/v1/analytics/track/impression",
        json={
            "target_event_id": str(event.id),
            "tracked_action": "featured_event_impression",
            "source": "home_featured",
        },
    )
    assert res.status_code == 200, res.text
    assert res.json()["tracked_action"] == TrackedAction.FEATURED_EVENT_IMPRESSION


def test_trusted_payment_success_emits_conversion_stage(db_session: Session):
    event = _seed(db_session)
    order_id = uuid4()
    emit_payment_success(
        db_session,
        order_id=order_id,
        event_id=event.id,
        host_id=event.host_id,
        buyer_user_id=None,
        amount=Decimal("1000.00"),
        ticket_count=1,
    )
    db_session.commit()
    row = db_session.scalar(
        select(ConversionEvent).where(
            ConversionEvent.event_id == event.id,
            ConversionEvent.stage == "checkout_complete",
        )
    )
    assert row is not None
    assert row.stage == "checkout_complete"
    stream = db_session.scalar(
        select(AnalyticsEvent).where(
            AnalyticsEvent.event_name == TrackedAction.PAYMENT_SUCCESS
        )
    )
    assert stream is not None
    assert stream.event_metadata and stream.event_metadata.get("order_id") == str(
        order_id
    )
