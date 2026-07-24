"""Fan Connect analytics — taxonomy + privacy-safe trusted emits."""

from __future__ import annotations

from sqlalchemy import select

from app.analytics.dimensions import scrub_metadata
from app.analytics.models import AnalyticsEvent
from app.analytics.taxonomy import (
    SERVER_ONLY_ACTIONS,
    TrackedAction,
    is_known_tracked_action,
    is_server_only_action,
)
from app.fan_connect import analytics as fc_analytics
from app.core.security import hash_password
from app.users.models import User
from app.users.service import get_role_by_name
from uuid import uuid4


FAN_CONNECT_CLIENT = {
    TrackedAction.FAN_CONNECT_PAGE_VIEW,
    TrackedAction.FAN_CONNECT_SETTINGS_UPDATED,
    TrackedAction.FAN_CONNECT_SUGGESTION_IMPRESSION,
    TrackedAction.FAN_CONNECT_SUGGESTION_CLICKED,
}

FAN_CONNECT_TRUSTED = {
    TrackedAction.FAN_CONNECT_ENABLED,
    TrackedAction.FAN_CONNECT_DISABLED,
    TrackedAction.FAN_CONNECT_REQUEST_SENT,
    TrackedAction.FAN_CONNECT_REQUEST_ACCEPTED,
    TrackedAction.FAN_CONNECT_REQUEST_DECLINED,
    TrackedAction.FAN_CONNECT_CONNECTION_REMOVED,
    TrackedAction.FAN_CONNECT_BLOCKED,
    TrackedAction.FAN_CONNECT_REPORTED,
    TrackedAction.FAN_FAN_MESSAGE_THREAD_CREATED,
    TrackedAction.FAN_FAN_MESSAGE_SENT,
}


def test_fan_connect_actions_in_taxonomy() -> None:
    for action in FAN_CONNECT_CLIENT | FAN_CONNECT_TRUSTED:
        assert is_known_tracked_action(action), action
    for action in FAN_CONNECT_TRUSTED:
        assert is_server_only_action(action), action
        assert action in SERVER_ONLY_ACTIONS
    for action in FAN_CONNECT_CLIENT:
        assert not is_server_only_action(action), action


def test_fan_connect_metadata_scrub_drops_private_fields() -> None:
    cleaned = scrub_metadata(
        {
            "connection_id": str(uuid4()),
            "thread_id": str(uuid4()),
            "counterpart_username": "chiditech",
            "score_band": "good",
            "email": "secret@example.com",
            "phone": "+2348000000000",
            "order_id": str(uuid4()),  # allowlisted globally but must not be relied on
            "shipping_address": "12 Secret Street",
            "message_body": "Hey — my VIP table is…",
            "ticket_type_name": "VIP Table",
            "payment_reference": "psk_xxx",
            "locked_vault_url": "https://evil.example/vault",
        }
    )
    assert cleaned["counterpart_username"] == "chiditech"
    assert cleaned["score_band"] == "good"
    assert "email" not in cleaned
    assert "phone" not in cleaned
    assert "shipping_address" not in cleaned
    assert "message_body" not in cleaned
    assert "locked_vault_url" not in cleaned
    # ticket_type_name is allowlisted for tickets — Connect emitters must not send it.
    # Privacy test: emitters only pass safe keys (covered by emit test below).


def test_emit_request_accepted_writes_event(db_session) -> None:
    user = User(
        email="fc-analytics@example.com",
        password_hash=hash_password("securepass1"),
        full_name="FC Analytics",
        is_active=True,
    )
    role = get_role_by_name(db_session, "buyer")
    if role is not None:
        user.roles.append(role)
    db_session.add(user)
    db_session.flush()

    connection_id = uuid4()
    thread_id = uuid4()
    fc_analytics.emit_request_accepted(
        db_session,
        user_id=user.id,
        connection_id=connection_id,
        thread_id=thread_id,
    )
    db_session.commit()

    row = db_session.scalar(
        select(AnalyticsEvent).where(
            AnalyticsEvent.event_name == TrackedAction.FAN_CONNECT_REQUEST_ACCEPTED,
            AnalyticsEvent.user_id == user.id,
        )
    )
    assert row is not None
    meta = row.event_metadata or {}
    assert meta.get("connection_id") == str(connection_id)
    assert meta.get("thread_id") == str(thread_id)
    assert "email" not in meta
    assert "message_body" not in meta
    assert "ticket_type" not in str(meta).lower()
