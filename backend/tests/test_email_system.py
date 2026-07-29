"""Transactional email system — templates, outbox, prefs, privacy."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.email.models import EmailEvent
from app.email.prefs import get_or_create_preferences, update_preferences
from app.email.config import assert_email_runtime_safe, production_email_ready
from app.email.queue import drain_email_outbox, process_pending_emails
from app.email.renderer import render_host_announcement, render_template
from app.email.service import enqueue_template, send_template
from app.email.templates import TEMPLATES, assert_brand_safe
from app.email.tokens import make_prefs_token, parse_prefs_token
from app.core.config import get_settings
from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostProfile
from app.payments.paystack import sign_body_for_tests
from app.users.models import User
from app.users.seed import seed_roles_and_permissions
from app.users.service import get_role_by_name


def test_all_templates_render_with_plain_and_html():
    for name in TEMPLATES:
        subject, text, html = render_template(
            name,
            {
                "full_name": "Ada",
                "buyer_name": "Ada",
                "event_title": "Lagos Night",
                "ticket_codes": "T-ABC123",
                "item_summary": "1× Cap",
                "product_name": "Cap",
                "requester_name": "Tolu",
                "acceptor_name": "Amaka",
                "brand_name": "Acme",
                "host_name": "DJ Maze",
                "report_kind": "review",
                "refund_status": "approved",
                "shipping_status": "shipped",
                "payout_status": "paid",
                "inquiry_status": "accepted",
                "detail": "Webhook failed",
                "case_ref": "CASE-1",
                "ticket_count": 2,
                "item_count": 1,
                "subject_label": "Lagos Night",
                "update_summary": "Doors open later",
                "starts_at_label": "tomorrow",
                "pickup_code_short": "PICK1234",
                "tracking_number": "TRK1",
            },
        )
        assert subject
        assert "Pàdéyá" in text or "Pàdéyá" in subject
        assert "<html" in html.lower()
        assert text.strip()
        assert_brand_safe(text)
        for bad in ("Padeya", "Padéyá", "Pàdéyé"):
            assert bad not in text
            assert bad not in subject


def test_host_announcement_renders_branded_html():
    subject, text, html = render_host_announcement(
        title="Weekend show",
        body="Hello fans,\n\nSee you on the dance floor.",
        host_name="DJ Maze",
        host_slug="dj-maze",
    )
    assert subject == "Weekend show"
    assert "DJ Maze" in text
    assert "Pàdéyá" in text
    assert "/brand/padeya-logo-dark-v3.png" in html
    assert "From DJ Maze" in html
    assert "View DJ Maze on Pàdéyá" in html
    assert "/hosts/dj-maze" in html
    assert "Unsubscribe from marketing" in html
    assert html.count("<p style=") >= 2


def test_host_announcement_splits_single_newline_paragraphs():
    """Bodies without blank lines (AI apply path) must not collapse to one <p>."""
    from app.email.renderer import split_host_announcement_body

    body = (
        "Hi Tolu,\n"
        "We're excited to invite you to Mainland After Dark.\n"
        "Looking forward to seeing you there!\n"
        "Best,\n"
        "DJ Maze"
    )
    parts = split_host_announcement_body(body)
    assert len(parts) == 5
    assert parts[0] == "Hi Tolu,"
    assert parts[-1] == "DJ Maze"

    _, _, html = render_host_announcement(
        title="Mainland After Dark",
        body=body,
        host_name="DJ Maze",
        host_slug="dj-maze",
    )
    assert ">Hi Tolu,<" in html
    assert ">Best,<" in html
    assert ">DJ Maze<" in html
    assert html.count("<p style=") >= 5


def test_host_announcement_personalizes_name_tokens():
    from app.email.renderer import (
        apply_announcement_merge_tokens,
        recipient_greeting_name,
    )

    assert recipient_greeting_name("Tolu Afro") == "Tolu"
    assert recipient_greeting_name("Tolu A.") == "Tolu"
    assert recipient_greeting_name("") == "there"
    assert (
        apply_announcement_merge_tokens(
            "Hi {{name}}, see you", recipient_name="Ada Lovelace"
        )
        == "Hi Ada, see you"
    )

    subject, text, html = render_host_announcement(
        title="{{name}} — this weekend",
        body="Hi {{first_name}},\n\nDoors at 8.",
        host_name="DJ Maze",
        host_slug="dj-maze",
        recipient_name="Chidi Okeke",
    )
    assert subject == "Chidi — this weekend"
    assert "Hi Chidi," in text
    assert "{{name}}" not in text
    assert "{{first_name}}" not in html
    assert "Hi Chidi," in html


def test_host_announcement_allows_ascii_brand_in_host_copy():
    _, _, html = render_host_announcement(
        title="Show",
        body="Welcome to Padeya night — see you there.",
        host_name="DJ Maze",
        host_slug="dj-maze",
    )
    assert "Padeya night" in html


def test_forbidden_brand_spellings():
    with pytest.raises(ValueError):
        assert_brand_safe("Welcome to Padeya")


def test_verify_email_allows_forbidden_spelling_in_full_name():
    """User display names must not trip brand policing (blocks change-email)."""
    subject, text, html = render_template(
        "verify_email",
        {
            "full_name": "Admin Padeya",
            "verification_code": "123456",
            "expiry_hours": "24",
            "cta_path": "/verify?token=abc",
        },
    )
    assert subject
    assert "Admin Padeya" in text
    assert "Pàdéyá" in text
    assert "Admin Padeya" in html
    assert_brand_safe(text, scrub=["Admin Padeya"])


def test_enqueue_and_dev_deliver(db_session: Session):
    seed_roles_and_permissions(db_session)
    role = get_role_by_name(db_session, "attendee")
    user = User(
        email="buyer@example.com",
        password_hash="x",
        full_name="Buyer",
        roles=[role] if role else [],
    )
    db_session.add(user)
    db_session.flush()

    event = send_template(
        db_session,
        template="welcome",
        to=user.email,
        recipient_user_id=user.id,
        context={"full_name": "Buyer"},
        dedupe_key=f"user:{user.id}:welcome",
        deliver_now=True,
    )
    db_session.commit()
    assert event is not None
    assert event.status == "sent"
    assert event.provider == "log"


def test_marketing_pref_skips_cart_reminder(db_session: Session):
    seed_roles_and_permissions(db_session)
    role = get_role_by_name(db_session, "attendee")
    user = User(
        email="fan@example.com",
        password_hash="x",
        full_name="Fan",
        roles=[role] if role else [],
    )
    db_session.add(user)
    db_session.flush()
    prefs = get_or_create_preferences(db_session, user.id)
    assert prefs.email_marketing is True
    update_preferences(db_session, user_id=user.id, updates={"email_marketing": False})
    db_session.commit()

    event = enqueue_template(
        db_session,
        template="merch_cart_reminder",
        to=user.email,
        recipient_user_id=user.id,
        dedupe_key="cart:test:1",
    )
    db_session.commit()
    assert event is not None
    assert event.status == "skipped"


def test_security_still_sends_when_marketing_off(db_session: Session):
    seed_roles_and_permissions(db_session)
    role = get_role_by_name(db_session, "attendee")
    user = User(
        email="sec@example.com",
        password_hash="x",
        full_name="Sec",
        roles=[role] if role else [],
    )
    db_session.add(user)
    db_session.flush()
    update_preferences(db_session, user_id=user.id, updates={"email_marketing": False})

    event = send_template(
        db_session,
        template="security_alert",
        to=user.email,
        recipient_user_id=user.id,
        context={"detail": "Password changed on Pàdéyá."},
        deliver_now=True,
    )
    db_session.commit()
    assert event is not None
    assert event.status == "sent"


def test_dedupe_webhook_style(db_session: Session):
    a = enqueue_template(
        db_session,
        template="ticket_confirmed",
        to="a@example.com",
        dedupe_key="order:abc:ticket_confirmed",
        context={"buyer_name": "A", "event_title": "Show", "ticket_codes": "T1"},
    )
    b = enqueue_template(
        db_session,
        template="ticket_confirmed",
        to="a@example.com",
        dedupe_key="order:abc:ticket_confirmed",
        context={"buyer_name": "A", "event_title": "Show", "ticket_codes": "T1"},
    )
    db_session.commit()
    assert a is not None and b is not None
    assert a.id == b.id
    count = len(
        list(
            db_session.scalars(
                select(EmailEvent).where(
                    EmailEvent.dedupe_key == "order:abc:ticket_confirmed"
                )
            )
        )
    )
    assert count == 1


def test_ticket_email_has_no_order_reference():
    _, text, _ = render_template(
        "ticket_confirmed",
        {
            "buyer_name": "Ada",
            "event_title": "Night",
            "ticket_codes": "T-PUBLIC",
        },
    )
    assert "T-PUBLIC" in text
    assert "order_" not in text.lower()
    assert "paystack" not in text.lower()


def test_prefs_api_and_unsubscribe(client: TestClient, db_session: Session):
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "prefs@example.com",
            "password": "Password123!",
            "full_name": "Prefs User",
        "gender": "prefer_not_to_say"},
    )
    assert reg.status_code == 201, reg.text
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    got = client.get("/api/v1/email/preferences", headers=headers)
    assert got.status_code == 200
    assert got.json()["email_security"] is True
    assert got.json()["email_marketing"] is True
    assert got.json()["email_messages"] is True

    patched = client.patch(
        "/api/v1/email/preferences",
        headers=headers,
        json={"email_messages": True, "email_security": False},
    )
    assert patched.status_code == 200
    assert patched.json()["email_messages"] is True
    assert patched.json()["email_security"] is True

    user = db_session.scalar(select(User).where(User.email == "prefs@example.com"))
    assert user is not None
    unsub_token = make_prefs_token(user.id, purpose="unsubscribe")
    unsub = client.post(
        "/api/v1/email/unsubscribe",
        json={"token": unsub_token, "marketing_only": True},
    )
    assert unsub.status_code == 200
    assert unsub.json()["email_marketing"] is False


def test_admin_email_list(client: TestClient, db_session: Session, assign_role):
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "admin-mail@example.com",
            "password": "Password123!",
            "full_name": "Admin Mail",
        "gender": "prefer_not_to_say"},
    )
    assert reg.status_code == 201, reg.text
    assign_role("admin-mail@example.com", "super_admin")
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    send_template(
        db_session,
        template="welcome",
        to="admin-mail@example.com",
        context={"full_name": "Admin"},
        deliver_now=True,
    )
    db_session.commit()

    listed = client.get("/api/v1/admin/emails", headers=headers)
    assert listed.status_code == 200, listed.text
    assert listed.json()["total"] >= 1


def test_admin_email_notification_settings_route(client: TestClient, assign_role):
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "admin-notif-mail@example.com",
            "password": "Password123!",
            "full_name": "Admin Notif",
        "gender": "prefer_not_to_say"},
    )
    assert reg.status_code == 201, reg.text
    assign_role("admin-notif-mail@example.com", "super_admin")
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    settings = client.get("/api/v1/admin/emails/notification-settings", headers=headers)
    assert settings.status_code == 200, settings.text
    body = settings.json()
    assert "master_enabled" in body
    assert "digest_enabled" in body

    templates = client.get("/api/v1/admin/emails/templates", headers=headers)
    assert templates.status_code == 200, templates.text


def _seed_event(db_session: Session) -> tuple[Event, TicketType]:
    host_user = User(
        email=f"email-host-{uuid4().hex[:8]}@example.com",
        password_hash="x",
        full_name="Event Host",
        is_active=True,
    )
    role = get_role_by_name(db_session, "host")
    assert role is not None
    host_user.roles.append(role)
    db_session.add(host_user)
    db_session.flush()
    host = Host(
        user_id=host_user.id,
        display_name="Event Host",
        slug=f"email-host-{uuid4().hex[:8]}",
        status="active",
    )
    db_session.add(host)
    db_session.flush()
    db_session.add(HostProfile(host_id=host.id, city="Lagos"))
    category = db_session.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=14)
    event = Event(
        title="Email Paid Night",
        slug=f"email-paid-{uuid4().hex[:8]}",
        description="A published event for email checkout tests with enough detail.",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=5),
        venue_name="Arena",
        city="Lagos",
        state="Lagos",
        status="published",
        featured=False,
        published_at=datetime.now(UTC),
    )
    db_session.add(event)
    db_session.flush()
    ticket_type = TicketType(
        event_id=event.id,
        name="Regular",
        type="regular",
        description="GA",
        price=Decimal("5000.00"),
        quantity=10,
        quantity_sold=0,
        quantity_reserved=0,
        min_per_order=1,
        max_per_order=5,
        visibility="public",
        status="active",
    )
    db_session.add(ticket_type)
    db_session.commit()
    db_session.refresh(event)
    db_session.refresh(ticket_type)
    return event, ticket_type


def test_webhook_enqueues_ticket_email_without_reference_leak(
    client: TestClient, db_session: Session
):
    event, ticket_type = _seed_event(db_session)
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "email-buyer@example.com",
            "password": "securepass1",
            "full_name": "Buyer User",
        "gender": "prefer_not_to_say"},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "email-buyer@example.com", "password": "securepass1"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    order = client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "event_id": str(event.id),
            "items": [{"ticket_type_id": str(ticket_type.id), "quantity": 1}],
        },
    ).json()

    with patch(
        "app.payments.service.initialize_transaction",
        return_value={
            "authorization_url": "https://checkout.paystack.com/test",
            "access_code": "ACCESS",
            "reference": order["reference"],
        },
    ):
        client.post(f"/api/v1/payments/checkout/{order['id']}", headers=headers)

    payload = {
        "event": "charge.success",
        "data": {
            "reference": order["reference"],
            "status": "success",
            "amount": 500000,
            "currency": "NGN",
            "id": 999001,
        },
    }
    body = json.dumps(payload).encode()
    sig = sign_body_for_tests(body)
    wh = client.post(
        "/api/v1/payments/webhooks/paystack",
        content=body,
        headers={"x-paystack-signature": sig, "content-type": "application/json"},
    )
    assert wh.status_code == 200, wh.text

    rows = list(
        db_session.scalars(
            select(EmailEvent).where(EmailEvent.template == "ticket_confirmed")
        )
    )
    assert len(rows) == 1
    assert rows[0].status == "pending"
    ctx = rows[0].context_json or {}
    assert order["reference"] not in json.dumps(ctx)
    assert "ticket_codes" in ctx

    # Duplicate webhook must not duplicate email
    wh2 = client.post(
        "/api/v1/payments/webhooks/paystack",
        content=body,
        headers={"x-paystack-signature": sig, "content-type": "application/json"},
    )
    assert wh2.status_code == 200
    rows2 = list(
        db_session.scalars(
            select(EmailEvent).where(EmailEvent.template == "ticket_confirmed")
        )
    )
    assert len(rows2) == 1

    processed = process_pending_emails(db_session, limit=20)
    assert processed >= 1
    db_session.refresh(rows2[0])
    assert rows2[0].status == "sent"


def test_prefs_token_roundtrip():
    uid = uuid4()
    token = make_prefs_token(uid, purpose="preferences")
    assert parse_prefs_token(token, purpose="preferences") == uid


def test_drain_stats_safe_and_counts(db_session: Session):
    enqueue_template(
        db_session,
        template="welcome",
        to="drain@example.com",
        context={"full_name": "Drain"},
        dedupe_key="drain:welcome:1",
    )
    db_session.commit()
    stats = drain_email_outbox(db_session, limit=10, commit=True)
    assert stats.attempted >= 1
    assert stats.sent >= 1
    assert stats.provider_mode  # e.g. dev_log
    assert "password" not in stats.provider_mode.lower()


def test_production_smtp_ready_fails_loudly(monkeypatch, db_session: Session):
    settings = get_settings()
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "email_enabled", True)
    monkeypatch.setattr(settings, "email_dev_mode", False)
    monkeypatch.setattr(settings, "email_provider", "smtp")
    monkeypatch.setattr(settings, "smtp_host", "")
    monkeypatch.setattr(settings, "smtp_from_email", "noreply@padeya.com")
    ok, err = production_email_ready(settings, db=db_session)
    assert ok is False
    assert err and "SMTP host" in err
    with pytest.raises(RuntimeError, match="SMTP host"):
        assert_email_runtime_safe(settings, db=db_session)


def test_admin_email_provider_settings_masked(
    client: TestClient, db_session: Session, assign_role
):
    from app.core.encryption import decrypt_secret
    from app.email.models import EmailProviderSettings
    from app.email.config import email_runtime

    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "smtp-admin@example.com",
            "password": "Password123!",
            "full_name": "SMTP Admin",
        "gender": "prefer_not_to_say"},
    )
    assert reg.status_code == 201, reg.text
    assign_role("smtp-admin@example.com", "super_admin")
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    got = client.get("/api/v1/admin/email/settings", headers=headers)
    assert got.status_code == 200, got.text
    body = got.json()
    assert "smtp_password" not in body
    assert body["smtp_password_configured"] is False
    assert body["smtp_from_name"] == "Pàdéyá" or "Pàdéyá" in (body.get("smtp_from_name") or "")

    patched = client.patch(
        "/api/v1/admin/email/settings",
        headers=headers,
        json={
            "email_enabled": True,
            "provider": "smtp",
            "dev_mode": True,
            "smtp_from_email": "noreply@padeya.com",
            "smtp_from_name": "Pàdéyá",
            "smtp_reply_to": "support@padeya.com",
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "smtp_username": "mailer@padeya.com",
            "smtp_password": "super-secret-smtp",
            "smtp_use_tls": True,
            "smtp_use_ssl": False,
        },
    )
    assert patched.status_code == 200, patched.text
    data = patched.json()
    assert data["is_active"] is True
    assert data["smtp_password_configured"] is True
    assert data["smtp_password_last4"] == "smtp"
    assert data["smtp_host"] == "smtp.example.com"
    assert "super-secret-smtp" not in patched.text
    assert "smtp_password" not in data
    assert data["smtp_username_masked"]

    # Blank password keeps existing
    keep = client.patch(
        "/api/v1/admin/email/settings",
        headers=headers,
        json={"smtp_password": "", "smtp_host": "smtp2.example.com"},
    )
    assert keep.status_code == 200
    assert keep.json()["smtp_host"] == "smtp2.example.com"
    assert keep.json()["smtp_password_configured"] is True

    row = db_session.scalar(select(EmailProviderSettings))
    assert row is not None
    assert row.smtp_password_encrypted
    assert decrypt_secret(row.smtp_password_encrypted) == "super-secret-smtp"
    assert "super-secret-smtp" not in (row.smtp_password_encrypted or "")

    # TLS+SSL conflict rejected
    bad = client.patch(
        "/api/v1/admin/email/settings",
        headers=headers,
        json={"smtp_use_tls": True, "smtp_use_ssl": True},
    )
    assert bad.status_code == 400

    # Non-admin forbidden
    reg2 = client.post(
        "/api/v1/auth/register",
        json={
            "email": "smtp-user@example.com",
            "password": "Password123!",
            "full_name": "SMTP User",
        "gender": "prefer_not_to_say"},
    )
    assert reg2.status_code == 201
    forbidden = client.get(
        "/api/v1/admin/email/settings",
        headers={"Authorization": f"Bearer {reg2.json()['access_token']}"},
    )
    assert forbidden.status_code == 403

    cfg = email_runtime(db=db_session)
    assert cfg.smtp_host == "smtp2.example.com"
    assert cfg.smtp_password == "super-secret-smtp"
    assert cfg.provider == "smtp"
    assert cfg.from_name == "Pàdéyá"

    disabled = client.post("/api/v1/admin/email/settings/disable", headers=headers)
    assert disabled.status_code == 200
    assert disabled.json()["email_enabled"] is False
    cfg2 = email_runtime(db=db_session)
    assert cfg2.enabled is False
