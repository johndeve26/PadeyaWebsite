"""Trigger channel integration — presence gate + refund/admin helpers."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.email.models import EmailEvent
from app.messaging.models import InAppNotification
from app.messaging.notifications import notify_new_chat_message
from app.notifications.triggers import notify_admins_report, notify_buyer_ticket_refund
from app.push.models import PushEvent
from app.users.models import User
from app.users.service import get_role_by_name


def test_message_push_skipped_when_present(
    db_session: Session, monkeypatch
):
    from app.hosts.models import Host, HostProfile
    from app.messaging.models import MessageThread

    fan = User(
        email=f"away-fan-{uuid4().hex[:8]}@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Away Fan",
        is_active=True,
    )
    host_user = User(
        email=f"away-host-{uuid4().hex[:8]}@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Away Host",
        is_active=True,
    )
    host_user.roles.append(get_role_by_name(db_session, "host"))
    db_session.add_all([fan, host_user])
    db_session.flush()
    host = Host(
        user_id=host_user.id,
        display_name="Away Host",
        slug="away-host-" + uuid4().hex[:6],
        status="active",
    )
    db_session.add(host)
    db_session.flush()
    db_session.add(HostProfile(host_id=host.id, bio="Host", city="Lagos"))
    thread = MessageThread(
        thread_type="fan_host",
        fan_user_id=fan.id,
        host_id=host.id,
        host_user_id=host_user.id,
        status="active",
        initiated_by_user_id=fan.id,
    )
    db_session.add(thread)
    db_session.commit()

    from app.email.prefs import get_or_create_preferences

    prefs = get_or_create_preferences(db_session, fan.id)
    prefs.push_enabled = True
    prefs.push_messages = True
    db_session.commit()

    monkeypatch.setattr(
        "app.messaging.notifications._recipient_away",
        lambda **kwargs: False,
    )
    notify_new_chat_message(
        db_session,
        recipient_user_id=fan.id,
        thread_id=thread.id,
        kind="host_reply",
        link_path=f"/dashboard/messages/{thread.id}",
    )
    db_session.commit()

    assert (
        db_session.scalar(
            select(InAppNotification).where(InAppNotification.user_id == fan.id)
        )
        is not None
    )
    push_count = db_session.scalar(
        select(PushEvent).where(PushEvent.recipient_user_id == fan.id)
    )
    assert push_count is None


def test_message_push_enqueued_when_away(db_session: Session, monkeypatch):
    from app.hosts.models import Host, HostProfile
    from app.messaging.models import MessageThread
    from app.notifications.models import PushProviderSettings

    fan = User(
        email=f"push-fan-{uuid4().hex[:8]}@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Push Fan",
        is_active=True,
    )
    host_user = User(
        email=f"push-host-{uuid4().hex[:8]}@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Push Host",
        is_active=True,
    )
    host_user.roles.append(get_role_by_name(db_session, "host"))
    db_session.add_all([fan, host_user])
    db_session.flush()
    host = Host(
        user_id=host_user.id,
        display_name="Push Host",
        slug="push-host-" + uuid4().hex[:6],
        status="active",
    )
    db_session.add(host)
    db_session.flush()
    db_session.add(HostProfile(host_id=host.id, bio="Host", city="Lagos"))
    thread = MessageThread(
        thread_type="fan_host",
        fan_user_id=fan.id,
        host_id=host.id,
        host_user_id=host_user.id,
        status="active",
        initiated_by_user_id=fan.id,
    )
    db_session.add(thread)
    db_session.add(
        PushProviderSettings(
            is_active=True,
            push_enabled=True,
            provider="log",
        )
    )
    db_session.commit()

    from app.email.prefs import get_or_create_preferences

    prefs = get_or_create_preferences(db_session, fan.id)
    prefs.push_enabled = True
    prefs.push_messages = True
    db_session.commit()

    monkeypatch.setattr(
        "app.messaging.notifications._recipient_away",
        lambda **kwargs: True,
    )
    notify_new_chat_message(
        db_session,
        recipient_user_id=fan.id,
        thread_id=thread.id,
        kind="host_reply",
        link_path=f"/dashboard/messages/{thread.id}",
    )
    db_session.commit()

    event = db_session.scalar(
        select(PushEvent).where(PushEvent.recipient_user_id == fan.id)
    )
    assert event is not None
    assert event.template == "new_message"
    assert event.status in {"pending", "sent", "skipped"}


def test_notify_admins_report_emails_and_in_app(
    db_session: Session, assign_role, client: TestClient
):
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "admin-report@example.com",
            "password": "Password123!",
            "full_name": "Admin Report",
        },
    )
    assert reg.status_code == 201
    assign_role("admin-report@example.com", "super_admin")
    admin = db_session.scalar(
        select(User).where(User.email == "admin-report@example.com")
    )
    assert admin is not None

    from app.email.admin_template_service import ensure_admin_template_rows
    from app.email.models import EmailAdminTemplate

    ensure_admin_template_rows(db_session)
    tpl = db_session.scalar(
        select(EmailAdminTemplate).where(EmailAdminTemplate.key == "admin_message_report")
    )
    assert tpl is not None
    tpl.is_enabled = True
    tpl.delivery_mode = "instant"
    tpl.recipient_mode = "group"
    tpl.recipient_group = "super_admin"
    db_session.commit()

    report_id = uuid4()
    n = notify_admins_report(
        db_session,
        report_kind="message",
        report_id=report_id,
        title="New message report on Pàdéyá",
        body="A conversation was reported and needs moderation.",
        link_path="/admin/messaging",
    )
    db_session.commit()
    assert n >= 1

    note = db_session.scalar(
        select(InAppNotification).where(
            InAppNotification.user_id == admin.id,
            InAppNotification.kind == "admin.report",
        )
    )
    assert note is not None
    email = db_session.scalar(
        select(EmailEvent).where(
            EmailEvent.template == "admin_message_report",
            EmailEvent.recipient_user_id == admin.id,
        )
    )
    assert email is not None


def test_notify_buyer_ticket_refund_creates_in_app(db_session: Session):
    user = User(
        email=f"refund-buyer-{uuid4().hex[:8]}@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Refund Buyer",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    notify_buyer_ticket_refund(
        db_session,
        buyer_user_id=user.id,
        event_title="Lagos Night",
        refund_status="approved",
        dedupe_key=f"refund_test:{user.id}",
    )
    db_session.commit()
    note = db_session.scalar(
        select(InAppNotification).where(InAppNotification.user_id == user.id)
    )
    assert note is not None
    assert note.kind == "ticket.refund_update"
    assert "Lagos Night" in note.body
