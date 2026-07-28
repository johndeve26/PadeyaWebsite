"""Platform maintenance middleware, schedules, bypass, notify, audit."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.maintenance.models import (
    MaintenanceAuditLog,
    MaintenanceNotification,
    MaintenanceSchedule,
    MaintenanceSection,
    MaintenanceSettings,
)
from app.maintenance.service import (
    apply_due_schedules,
    ensure_section_rows,
    get_or_create_settings,
)
from app.users.models import Permission, Role, User
from app.users.service import get_role_by_name

from tests.helpers.auth import register_json

ADMIN = "/api/v1/admin/platform/maintenance"


def _register(client: TestClient, email: str) -> dict[str, str]:
    res = client.post(
        "/api/v1/auth/register",
        json=register_json(email=email, password="Password123!", full_name="Maint User"),
    )
    assert res.status_code == 201, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def _grant_perms(db: Session, user: User, *codes: str) -> None:
    role = Role(name=f"tmp-m-{uuid4().hex[:8]}", description="test")
    for code in codes:
        perm = db.scalar(select(Permission).where(Permission.code == code))
        assert perm is not None, f"missing permission {code}"
        role.permissions.append(perm)
    db.add(role)
    user.roles.append(role)
    db.commit()


def _admin_headers(client: TestClient, db: Session, assign_role, email: str) -> dict[str, str]:
    headers = _register(client, email)
    assign_role(email, "super_admin")
    return headers


def _set_mode(db: Session, mode: str, **kwargs) -> MaintenanceSettings:
    from app.maintenance.decision_cache import invalidate_maintenance_decision_cache

    settings = get_or_create_settings(db)
    settings.mode = mode
    for k, v in kwargs.items():
        setattr(settings, k, v)
    db.commit()
    invalidate_maintenance_decision_cache()
    return settings


def test_full_site_maintenance_blocks_users(
    client: TestClient, db_session: Session, assign_role
):
    _set_mode(db_session, "active", message="Down for maintenance")
    fan = _register(client, "fan-block@example.com")
    res = client.get("/api/v1/events", headers=fan)
    assert res.status_code == 503, res.text
    body = res.json()
    assert body["maintenance"] is True
    assert body["section"] == "platform"
    assert "maintenance" in body["detail"].lower() or "Down" in body["detail"]


def test_admin_can_access_admin_panel_during_maintenance(
    client: TestClient, db_session: Session, assign_role
):
    _set_mode(db_session, "active")
    headers = _admin_headers(
        client, db_session, assign_role, "admin-maint@example.com"
    )
    res = client.get(ADMIN, headers=headers)
    assert res.status_code == 200, res.text
    assert res.json()["settings"]["mode"] == "active"


def test_read_only_blocks_writes_allows_reads(
    client: TestClient, db_session: Session, assign_role
):
    _set_mode(db_session, "read_only")
    fan = _register(client, "fan-ro@example.com")
    get_res = client.get("/api/v1/events", headers=fan)
    assert get_res.status_code != 423
    assert get_res.status_code != 503

    post_res = client.post(
        "/api/v1/reviews",
        headers=fan,
        json={"event_id": str(uuid4()), "rating": 5, "body": "hi"},
    )
    assert post_res.status_code == 423, post_res.text
    assert post_res.json()["maintenance"] is True


def test_section_maintenance_blocks_only_affected_section(
    client: TestClient, db_session: Session, assign_role
):
    _set_mode(db_session, "section_only")
    ensure_section_rows(db_session)
    messaging = db_session.scalar(
        select(MaintenanceSection).where(
            MaintenanceSection.section_key == "messaging"
        )
    )
    assert messaging is not None
    messaging.enabled = True
    messaging.mode = "maintenance"
    messaging.message = "Messaging offline"
    db_session.commit()

    fan = _register(client, "fan-sec@example.com")
    events = client.get("/api/v1/events", headers=fan)
    assert events.status_code not in {503, 423}, events.text

    msg = client.get("/api/v1/messages", headers=fan)
    assert msg.status_code == 503, msg.text
    assert msg.json()["section"] == "messaging"


def test_checkout_maintenance_blocks_checkout_only(
    client: TestClient, db_session: Session, assign_role
):
    _set_mode(db_session, "off")
    ensure_section_rows(db_session)
    checkout = db_session.scalar(
        select(MaintenanceSection).where(
            MaintenanceSection.section_key == "checkout"
        )
    )
    assert checkout is not None
    checkout.enabled = True
    checkout.mode = "maintenance"
    checkout.message = "Checkout offline"
    db_session.commit()

    fan = _register(client, "fan-co@example.com")
    events = client.get("/api/v1/events", headers=fan)
    assert events.status_code not in {503, 423}

    pay = client.post(
        "/api/v1/orders",
        headers=fan,
        json={},
    )
    assert pay.status_code == 503, pay.text
    assert pay.json()["section"] == "checkout"


def test_scheduled_maintenance_activates_and_disables(
    client: TestClient, db_session: Session, assign_role
):
    now = datetime.now(UTC)
    sched = MaintenanceSchedule(
        title="Window",
        message="Scheduled down",
        target_mode="active",
        starts_at=now - timedelta(minutes=1),
        ends_at=now + timedelta(hours=1),
        auto_enable=True,
        auto_disable=True,
        status="pending",
    )
    db_session.add(sched)
    _set_mode(db_session, "off")

    # Trigger middleware schedule apply
    client.get("/api/v1/events")
    db_session.expire_all()
    settings = get_or_create_settings(db_session)
    assert settings.mode == "active"
    db_session.refresh(sched)
    assert sched.status == "active"

    sched.ends_at = now - timedelta(seconds=1)
    db_session.commit()
    client.get("/api/v1/events")
    db_session.expire_all()
    settings = get_or_create_settings(db_session)
    assert settings.mode == "off"
    db_session.refresh(sched)
    assert sched.status == "completed"


def test_bypass_works_for_permitted_admin(
    client: TestClient, db_session: Session, assign_role
):
    _set_mode(db_session, "active")
    headers = _admin_headers(
        client, db_session, assign_role, "bypass-ok@example.com"
    )
    created = client.post(f"{ADMIN}/bypass?hours=2", headers=headers)
    assert created.status_code == 200, created.text
    token = created.json()["token"]
    assert token

    # Product path with bypass (admin panel already allowed; use events)
    res = client.get(
        "/api/v1/events",
        headers={**headers, "X-Maintenance-Bypass": token},
    )
    assert res.status_code != 503, res.text

    audits = db_session.scalars(
        select(MaintenanceAuditLog).where(
            MaintenanceAuditLog.action == "bypass_used"
        )
    ).all()
    assert len(audits) >= 1


def test_bypass_denied_for_normal_user(
    client: TestClient, db_session: Session, assign_role
):
    _set_mode(db_session, "active")
    admin_h = _admin_headers(
        client, db_session, assign_role, "bypass-admin@example.com"
    )
    token = client.post(f"{ADMIN}/bypass", headers=admin_h).json()["token"]

    fan = _register(client, "bypass-fan@example.com")
    res = client.get(
        "/api/v1/events",
        headers={**fan, "X-Maintenance-Bypass": token},
    )
    assert res.status_code == 503, res.text


def test_notification_job_creates_delivery_records(
    client: TestClient, db_session: Session, assign_role
):
    headers = _admin_headers(
        client, db_session, assign_role, "notify-admin@example.com"
    )
    _register(client, "notify-fan@example.com")
    res = client.post(
        f"{ADMIN}/notifications",
        headers=headers,
        json={
            "title": "Upcoming maintenance",
            "body": "We will be offline soon.",
            "channels": ["in_app"],
            "audience": "all_users",
            "send_now": True,
        },
    )
    assert res.status_code == 200, res.text
    assert res.json()["delivery_count"] >= 1
    row = db_session.scalar(select(MaintenanceNotification).limit(1))
    assert row is not None
    assert row.status == "sent"
    assert row.delivery_count >= 1


def test_audit_logs_are_created(
    client: TestClient, db_session: Session, assign_role
):
    headers = _admin_headers(
        client, db_session, assign_role, "audit-admin@example.com"
    )
    res = client.patch(
        ADMIN,
        headers=headers,
        json={"mode": "read_only", "title": "RO"},
    )
    assert res.status_code == 200, res.text
    logs = db_session.scalars(select(MaintenanceAuditLog)).all()
    actions = {a.action for a in logs}
    assert "read_only_mode_enabled" in actions


def test_public_status_and_health_allowed_during_maintenance(
    client: TestClient, db_session: Session
):
    _set_mode(db_session, "active")
    status = client.get("/api/v1/maintenance/status")
    assert status.status_code == 200
    assert status.json()["mode"] == "active"
    health = client.get("/health")
    assert health.status_code == 200
    ready = client.get("/ready")
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"
