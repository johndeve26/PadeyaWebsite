"""Unified /analytics/track and /track/batch endpoints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analytics.models import AnalyticsEvent
from app.analytics.taxonomy import TrackedAction
from app.analytics.trusted import track_server_event
from app.core.security import hash_password
from app.events.models import Event, TicketType
from app.hosts.models import Host, HostProfile
from app.users.models import User
from app.users.service import get_role_by_name


def _seed(db: Session) -> Event:
    user = User(
        email="track-ep@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Track EP Host",
        is_active=True,
    )
    user.roles.append(get_role_by_name(db, "host"))
    db.add(user)
    db.flush()
    host = Host(
        user_id=user.id,
        display_name="Track EP",
        slug="track-ep",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, bio="x"))
    start = datetime.now(UTC) + timedelta(days=2)
    event = Event(
        title="Track Endpoint Night",
        slug="track-endpoint-night",
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


def test_unified_track_enriches_and_accepts(client: TestClient, db_session: Session):
    event = _seed(db_session)
    res = client.post(
        "/api/v1/analytics/track",
        json={
            "event_name": TrackedAction.EVENT_DETAIL_VIEW,
            "target_event_id": str(event.id),
            "session_id": "sess-unified",
            "anonymous_id": "anon-unified",
            "path": f"/events/{event.slug}",
            "utm_source": "newsletter",
        },
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X)"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["accepted"] is True
    assert body["tracked_action"] == TrackedAction.EVENT_DETAIL_VIEW
    row = db_session.get(AnalyticsEvent, UUID(body["id"]))
    assert row is not None
    assert row.utm_source == "newsletter"
    assert row.path == f"/events/{event.slug}"
    assert row.environment is not None
    assert row.device_type in {"desktop", "mobile", "tablet", "unknown"}


def test_unified_track_rejects_trusted(client: TestClient, db_session: Session):
    event = _seed(db_session)
    res = client.post(
        "/api/v1/analytics/track",
        json={
            "event_name": TrackedAction.PAYMENT_SUCCESS,
            "target_event_id": str(event.id),
            "session_id": "sess-bad",
        },
    )
    assert res.status_code == 403


def test_unified_track_rejects_oversized_metadata(
    client: TestClient, db_session: Session
):
    event = _seed(db_session)
    meta = {f"k{i}": "v" for i in range(80)}
    res = client.post(
        "/api/v1/analytics/track",
        json={
            "event_name": TrackedAction.EVENT_SHARE_CLICK,
            "target_event_id": str(event.id),
            "session_id": "sess-meta",
            "metadata": meta,
        },
    )
    assert res.status_code == 422


def test_track_batch(client: TestClient, db_session: Session):
    event = _seed(db_session)
    res = client.post(
        "/api/v1/analytics/track/batch",
        json={
            "events": [
                {
                    "event_name": TrackedAction.EVENT_CARD_IMPRESSION,
                    "target_event_id": str(event.id),
                    "session_id": "batch-1",
                    "anonymous_id": "anon-b",
                    "metadata": {"list_context": "home"},
                },
                {
                    "event_name": TrackedAction.EVENT_CARD_CLICK,
                    "target_event_id": str(event.id),
                    "session_id": "batch-1",
                    "anonymous_id": "anon-b",
                },
                {
                    "event_name": TrackedAction.PAYMENT_SUCCESS,
                    "target_event_id": str(event.id),
                    "session_id": "batch-1",
                },
            ]
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["accepted_count"] == 2
    assert body["rejected_count"] == 1


def test_vault_client_actions_accepted(client: TestClient, db_session: Session):
    event = _seed(db_session)
    vault_item_id = "22222222-2222-2222-2222-222222222222"
    for action in (
        TrackedAction.VAULT_PAGE_VIEW,
        TrackedAction.VAULT_ITEM_IMPRESSION,
        TrackedAction.VAULT_ITEM_CLICK,
        TrackedAction.VAULT_ITEM_VIEW,
        TrackedAction.VAULT_UNLOCK_CLICK,
        TrackedAction.VAULT_UNLOCK_SUCCESS,
        TrackedAction.VAULT_UNLOCK_FAILED,
        TrackedAction.VAULT_FOLLOW_UNLOCK,
        TrackedAction.VAULT_TICKET_UNLOCK,
        TrackedAction.VAULT_MEDIA_OPEN,
        TrackedAction.VAULT_DOWNLOAD_CLICK,
    ):
        res = client.post(
            "/api/v1/analytics/track",
            json={
                "event_name": action,
                "host_id": str(event.host_id),
                "session_id": f"sess-vault-{action}",
                "anonymous_id": "anon-vault",
                "metadata": {
                    "vault_item_id": vault_item_id,
                    "access_type": "one_time_unlock",
                    "related_event_id": str(event.id),
                    "locked_state": "locked",
                    "source_page": "vault_item",
                },
            },
        )
        assert res.status_code == 200, f"{action}: {res.text}"
        assert res.json()["accepted"] is True
        assert res.json()["tracked_action"] == action

    rejected = client.post(
        "/api/v1/analytics/track",
        json={
            "event_name": TrackedAction.VAULT_PURCHASE,
            "host_id": str(event.host_id),
            "session_id": "sess-vault-purchase-bad",
        },
    )
    assert rejected.status_code == 403


def test_track_server_event_writes_stream(db_session: Session):
    event = _seed(db_session)
    row = track_server_event(
        db_session,
        event_name=TrackedAction.VAULT_PURCHASE,
        host_id=event.host_id,
        user_id=None,
        value=Decimal("2500.00"),
        currency="NGN",
        metadata={"vault_purchase_id": "11111111-1111-1111-1111-111111111111"},
        request_id="trusted:vault_purchase:test-1",
    )
    db_session.commit()
    assert row is not None
    assert row.event_name == TrackedAction.VAULT_PURCHASE
    assert row.event_metadata and row.event_metadata.get("conversion_value") == "2500.00"
    # Idempotent
    again = track_server_event(
        db_session,
        event_name=TrackedAction.VAULT_PURCHASE,
        host_id=event.host_id,
        value=Decimal("2500.00"),
        request_id="trusted:vault_purchase:test-1",
    )
    assert again is None
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(AnalyticsEvent)
            .where(AnalyticsEvent.event_name == TrackedAction.VAULT_PURCHASE)
        )
        == 1
    )
