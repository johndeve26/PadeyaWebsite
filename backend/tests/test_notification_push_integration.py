"""Integration-style checks: notify_user → push outbox per product domain."""

from __future__ import annotations

import re
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.email.prefs import get_or_create_preferences
from app.notifications.models import PushSubscription
from app.notifications.service import notify_user
from app.notifications.settings_service import update_push_settings
from app.push.models import PushEvent
from app.push.templates import resolve_template_name
from app.users.models import User
from app.core.security import hash_password

SENSITIVE = re.compile(
    r"(paystack|sk_live|qr_|ticket_id|order_id|reference|@|\+234|\b\d{16}\b)",
    re.I,
)


def _enable_push(db: Session) -> None:
    update_push_settings(
        db,
        updates={
            "push_enabled": True,
            "provider": "log",
            "generate_vapid_keys": True,
            "vapid_subject": "mailto:support@padeya.com",
        },
        actor_user_id=None,
        commit=True,
    )


def _user(db: Session, email: str) -> User:
    user = User(
        email=email,
        password_hash=hash_password("Password123!"),
        full_name="Push Int",
        is_active=True,
    )
    db.add(user)
    db.flush()
    prefs = get_or_create_preferences(db, user.id)
    prefs.push_enabled = True
    prefs.push_ticket_updates = True
    prefs.push_merch_updates = True
    prefs.push_messages = True
    prefs.push_fan_connect = True
    prefs.push_host_activity = True
    prefs.push_sponsor_updates = True
    prefs.push_security = True
    db.flush()
    return user


@pytest.mark.parametrize(
    "kind,title,link",
    [
        ("ticket.confirmed", "Ticket ready", "/dashboard/tickets"),
        ("merch.ready_for_pickup", "Merch ready", "/dashboard/merchandise"),
        ("support.ticket_updated", "Support", "/dashboard/support"),
        ("message.new", "Message", "/dashboard/messages"),
        ("fan_connect.request", "Connect", "/connect/requests"),
        ("host.ticket_sale", "Sale", "/host/sales"),
        ("sponsor.inquiry_host", "Sponsor", "/host/sponsorships"),
        ("account.suspended", "Account", "/dashboard/settings"),
    ],
)
def test_notify_user_enqueues_safe_push(
    db_session: Session,
    kind: str,
    title: str,
    link: str,
):
    _enable_push(db_session)
    user = _user(db_session, f"push-int-{kind.replace('.', '-')}@example.com")
    db_session.commit()

    dedupe = f"int:{kind}:{uuid4()}"
    row = notify_user(
        db_session,
        user_id=user.id,
        kind=kind,
        title=title,
        body="Sensitive body with paystack ref ABC123 should not appear in push",
        link_path=link,
        dedupe_key=dedupe,
        push_context={"event_title": "Public Event Name"},
    )
    db_session.commit()
    assert row is not None

    push_row = db_session.scalar(
        select(PushEvent).where(PushEvent.dedupe_key == f"push:{dedupe}")
    )
    assert push_row is not None
    assert push_row.status in {"pending", "sent", "skipped"}
    if push_row.status == "skipped":
        pytest.skip(f"push skipped: {push_row.error_message}")

    expected_tmpl = resolve_template_name(kind)
    assert push_row.template == expected_tmpl
    assert expected_tmpl != "generic"
    assert not SENSITIVE.search(push_row.title or "")
    assert not SENSITIVE.search(push_row.body or "")
    assert "paystack" not in (push_row.body or "").lower()


def test_admin_type_push_off_skips_push(db_session: Session):
    from app.admin_notifications.settings_service import update_setting

    _enable_push(db_session)
    user = _user(db_session, "push-int-admin-off@example.com")
    db_session.commit()

    update_setting(
        db_session,
        type_key="ticket.purchase_confirmed",
        updates={"channels": {"push": False}},
        actor_user_id=user.id,
        actor_is_super_admin=True,
    )
    db_session.commit()

    dedupe = f"int:admin-off:{uuid4()}"
    notify_user(
        db_session,
        user_id=user.id,
        kind="ticket.confirmed",
        title="Ticket",
        body="Body",
        link_path="/dashboard/tickets",
        dedupe_key=dedupe,
    )
    db_session.commit()

    push_row = db_session.scalar(
        select(PushEvent).where(PushEvent.dedupe_key == f"push:{dedupe}")
    )
    assert push_row is None


def test_push_dedupe_idempotent(db_session: Session):
    _enable_push(db_session)
    user = _user(db_session, "push-int-dedupe@example.com")
    db_session.commit()
    dedupe = f"int:dedupe:{uuid4()}"

    notify_user(
        db_session,
        user_id=user.id,
        kind="fan_connect.accepted",
        title="Connected",
        body="Body",
        dedupe_key=dedupe,
    )
    notify_user(
        db_session,
        user_id=user.id,
        kind="fan_connect.accepted",
        title="Connected",
        body="Body",
        dedupe_key=dedupe,
    )
    db_session.commit()

    rows = list(
        db_session.scalars(
            select(PushEvent).where(PushEvent.dedupe_key == f"push:{dedupe}")
        )
    )
    assert len(rows) == 1


def test_invalid_subscription_does_not_fail_in_app(db_session: Session):
    from app.core.encryption import encrypt_secret
    from app.notifications.push import FAILURE_DEACTIVATE_THRESHOLD, mark_subscription_failure

    _enable_push(db_session)
    user = _user(db_session, "push-int-sub-fail@example.com")
    sub = PushSubscription(
        user_id=user.id,
        endpoint=f"https://push.example.com/{uuid4()}",
        p256dh_encrypted=encrypt_secret("p"),
        auth_encrypted=encrypt_secret("a"),
        is_active=True,
    )
    db_session.add(sub)
    db_session.commit()

    dedupe = f"int:sub:{uuid4()}"
    row = notify_user(
        db_session,
        user_id=user.id,
        kind="support.ticket_updated",
        title="Support",
        body="Reply",
        dedupe_key=dedupe,
    )
    db_session.commit()
    assert row is not None

    for _ in range(FAILURE_DEACTIVATE_THRESHOLD):
        mark_subscription_failure(sub)
    db_session.commit()
    db_session.refresh(sub)
    assert sub.is_active is False
