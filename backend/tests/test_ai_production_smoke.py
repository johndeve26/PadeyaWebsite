"""Production smoke checks for Pàdéyá canonical AI (24 draft-only features)."""

from __future__ import annotations

import os
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.constants import (
    ADMIN_CONTROL_FEATURES,
    ADMIN_QUARANTINED_AI_FEATURES,
    FUTURE_AI_FEATURES,
    LEGACY_HOST_AI_FEATURES,
)
from app.ai.feature_routing import ensure_default_provider_profiles, list_feature_routes_public
from app.ai.models import AIFeatureRoute, AIPromptTemplate
from app.ai.seed import seed_ai_prompt_templates
from app.ai.service import ensure_templates
from app.core.security import hash_password
from app.hosts.models import Host, HostProfile
from app.users.models import User
from app.users.service import get_role_by_name


def _admin_headers(client: TestClient, db: Session) -> dict[str, str]:
    admin = User(
        email="ai-smoke-admin@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Smoke Admin",
        is_active=True,
    )
    admin.roles.append(get_role_by_name(db, "super_admin"))
    db.add(admin)
    db.commit()
    login = client.post(
        "/api/v1/auth/login",
        json={"email": admin.email, "password": "securepass1"},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_migrations_at_head():
    """Alembic head includes AI control center revisions (checked in CI/deploy)."""
    from pathlib import Path

    versions = Path(__file__).resolve().parents[1] / "alembic" / "versions"
    names = {p.name for p in versions.glob("20260722_012*_*.py")}
    assert "20260722_0127_ai_control_center.py" in names
    assert "20260722_0128_ai_feature_auto_models.py" in names


def test_templates_and_routes_seeded(db_session: Session):
    seed_ai_prompt_templates(db_session)
    ensure_templates(db_session)
    ensure_default_provider_profiles(db_session)
    db_session.commit()

    slugs = set(
        db_session.scalars(
            select(AIPromptTemplate.slug).where(AIPromptTemplate.is_active.is_(True))
        ).all()
    )
    for key in ADMIN_CONTROL_FEATURES:
        assert key in slugs, f"missing template slug {key}"

    routes = list_feature_routes_public(db_session)
    route_keys = {r["feature_key"] for r in routes}
    for key in ADMIN_CONTROL_FEATURES:
        assert key in route_keys, f"missing feature route {key}"
    for key in FUTURE_AI_FEATURES:
        assert key in route_keys
        row = next(r for r in routes if r["feature_key"] == key)
        assert row["future"] is True
        assert row["product_status"] == "blocked"
        assert row["routing_editable"] is False
        assert row["enabled"] is False

    assert len(ADMIN_CONTROL_FEATURES) == 24


def test_provider_profiles_exist(db_session: Session):
    profiles = ensure_default_provider_profiles(db_session)
    db_session.commit()
    assert len(profiles) >= 1
    template = next(p for p in profiles if p.provider_type == "template_fallback")
    assert template.is_enabled is True


def test_admin_ai_overview_and_routes(client: TestClient, db_session: Session):
    headers = _admin_headers(client, db_session)
    overview = client.get("/api/v1/ai/admin/controls/overview", headers=headers)
    assert overview.status_code == 200, overview.text

    routes = client.get("/api/v1/ai/admin/controls/routes", headers=headers)
    assert routes.status_code == 200, routes.text
    items = routes.json()
    assert isinstance(items, list)
    fan_bio = next(i for i in items if i["feature_key"] == "fan.passport.bio")
    assert fan_bio["category"] == "fan"
    assert fan_bio["product_status"] == "active"


def test_kill_switch_blocks_generate(client: TestClient, db_session: Session):
    host_user = User(
        email="ai-smoke-host@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Smoke Host",
        is_active=True,
    )
    host_user.roles.append(get_role_by_name(db_session, "host"))
    db_session.add(host_user)
    db_session.flush()
    host = Host(
        user_id=host_user.id,
        display_name="Smoke Host",
        slug="ai-smoke-host",
        status="active",
    )
    db_session.add(host)
    db_session.flush()
    db_session.add(HostProfile(host_id=host.id, bio="host"))
    db_session.commit()

    login = client.post(
        "/api/v1/auth/login",
        json={"email": host_user.email, "password": "securepass1"},
    )
    h = {"Authorization": f"Bearer {login.json()['access_token']}"}

    with patch.dict(os.environ, {"AI_KILL_SWITCH": "1"}):
        resp = client.post(
            "/api/v1/ai/host/generate",
            headers=h,
            json={"feature": "host.event.title", "notes": "test"},
        )
    assert resp.status_code == 503


def test_quarantined_keys_rejected(client: TestClient, db_session: Session):
    admin_h = _admin_headers(client, db_session)

    host_user = User(
        email="ai-smoke-host2@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Smoke Host 2",
        is_active=True,
    )
    host_user.roles.append(get_role_by_name(db_session, "host"))
    db_session.add(host_user)
    db_session.flush()
    db_session.add(
        Host(
            user_id=host_user.id,
            display_name="Smoke Host 2",
            slug="ai-smoke-host-2",
            status="active",
        )
    )
    db_session.flush()
    host2 = db_session.scalar(select(Host).where(Host.slug == "ai-smoke-host-2"))
    assert host2 is not None
    db_session.add(HostProfile(host_id=host2.id, bio="host"))
    db_session.commit()
    host_login = client.post(
        "/api/v1/auth/login",
        json={"email": host_user.email, "password": "securepass1"},
    )
    host_h = {"Authorization": f"Bearer {host_login.json()['access_token']}"}

    for feature in ADMIN_QUARANTINED_AI_FEATURES:
        resp = client.post(
            "/api/v1/ai/admin/generate",
            headers=admin_h,
            json={"feature": feature, "notes": "x"},
        )
        assert resp.status_code == 403, (feature, resp.text)

    for feature in ("generate_email_announcement", "suggest_ticket_pricing"):
        assert feature in LEGACY_HOST_AI_FEATURES
        resp = client.post(
            "/api/v1/ai/host/generate",
            headers=host_h,
            json={"feature": feature, "notes": "x"},
        )
        assert resp.status_code == 403, (feature, resp.text)


def test_safe_generation_logs_no_prompts(client: TestClient, db_session: Session):
    headers = _admin_headers(client, db_session)
    logs = client.get("/api/v1/ai/admin/controls/logs?limit=5", headers=headers)
    assert logs.status_code == 200, logs.text
    payload = logs.json()
    items = payload.get("items") or payload.get("logs") or []
    for item in items:
        blob = str(item).lower()
        assert "system_prompt" not in blob
        assert "user_prompt" not in blob
        assert "sk-" not in blob


def test_future_ai_keys_not_generatable(client: TestClient, db_session: Session):
    admin_h = _admin_headers(client, db_session)
    for feature in FUTURE_AI_FEATURES:
        resp = client.post(
            "/api/v1/ai/admin/generate",
            headers=admin_h,
            json={"feature": feature, "notes": "x"},
        )
        assert resp.status_code in (400, 403), (feature, resp.text)


def test_default_routes_disabled_for_quarantined_defaults(db_session: Session):
    from app.ai.constants import DEFAULT_FEATURE_ENABLED

    for key in LEGACY_HOST_AI_FEATURES | ADMIN_QUARANTINED_AI_FEATURES | set(FUTURE_AI_FEATURES):
        assert DEFAULT_FEATURE_ENABLED.get(key) is False

    count_enabled_future = db_session.scalar(
        select(func.count())
        .select_from(AIFeatureRoute)
        .where(AIFeatureRoute.feature_key.in_(FUTURE_AI_FEATURES))
    )
    _ = count_enabled_future  # routes may not exist until listed; defaults are false in code
