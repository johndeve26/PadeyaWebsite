"""AI Copilot: provider abstraction, prompts, usage logs, permissions, fallback."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.ai.models import AIUsageLog
from app.ai.prompts import extract_placeholders, render_prompt
from app.ai.providers import (
    OpenAICompatibleProvider,
    TemplateFallbackProvider,
    UnavailableProvider,
    get_ai_provider,
)
from app.core.config import Settings
from app.core.security import hash_password
from app.events.models import Event, TicketType
from app.hosts.models import Host, HostProfile
from app.users.models import User
from app.users.service import get_role_by_name


def _login(client: TestClient, email: str) -> dict[str, str]:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _seed_host(
    db: Session, *, email: str = "ai-host@example.com", slug: str = "ai-host"
) -> tuple[Host, User]:
    host_user = User(
        email=email,
        password_hash=hash_password("securepass1"),
        full_name="AI Host",
        is_active=True,
    )
    host_user.roles.append(get_role_by_name(db, "host"))
    db.add(host_user)
    db.flush()
    host = Host(
        user_id=host_user.id,
        display_name="AI Host",
        slug=slug,
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, bio="AI host"))
    db.commit()
    return host, host_user


def _seed_event(db: Session, host: Host) -> Event:
    start = datetime.now(UTC) + timedelta(days=5)
    event = Event(
        title="Neon Nights",
        slug="neon-nights-ai",
        description="A night of music and culture in Lagos with enough text.",
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=5),
        city="Lagos",
        venue_name="The Yard",
        status="published",
        featured=False,
        published_at=datetime.now(UTC),
        capacity=300,
    )
    db.add(event)
    db.flush()
    db.add(
        TicketType(
            event_id=event.id,
            name="GA",
            type="regular",
            price=Decimal("5000.00"),
            quantity=200,
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


def test_ai_provider_abstraction():
    template = TemplateFallbackProvider()
    out = template.complete(
        system_prompt="sys",
        user_prompt="Task: Generate titles\nCity: Lagos\nEvent: Test",
    )
    assert out.used_fallback is True
    assert "Draft" in out.text or "Lagos" in out.text
    assert out.provider == "template"

    unavailable = UnavailableProvider("down")
    fb = unavailable.complete(system_prompt="s", user_prompt="Task: hello")
    assert fb.used_fallback is True
    assert fb.error_message == "down"

    settings = Settings(
        ai_enabled=True,
        ai_provider="openai",
        ai_api_key="",
        ai_model="gpt-test",
    )
    openai = OpenAICompatibleProvider(settings)
    missing_key = openai.complete(system_prompt="s", user_prompt="Task: pricing")
    assert missing_key.used_fallback is True
    assert "AI_API_KEY" in (missing_key.error_message or "")


def test_prompt_rendering():
    template = "Hello {name} in {city}. Extra {missing}."
    assert extract_placeholders(template) == ["name", "city", "missing"]
    rendered = render_prompt(template, {"name": "Ada", "city": "Lagos"})
    assert rendered == "Hello Ada in Lagos. Extra ."


def test_usage_logging(client: TestClient, db_session: Session):
    host, host_user = _seed_host(db_session)
    event = _seed_event(db_session, host)
    headers = _login(client, host_user.email)

    before = db_session.query(AIUsageLog).count()
    resp = client.post(
        "/api/v1/ai/host/generate",
        headers=headers,
        json={
            "feature": "host.event.title",
            "event_id": str(event.id),
            "notes": "Afrobeats rooftop",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["requires_human_confirmation"] is True
    assert body["can_auto_publish"] is False
    assert body["can_auto_send"] is False
    assert body["can_modify_finance"] is False
    assert body["suggestion"]
    assert body.get("redaction_applied") is not None
    assert db_session.query(AIUsageLog).count() == before + 1
    log = db_session.query(AIUsageLog).order_by(AIUsageLog.created_at.desc()).first()
    assert log is not None
    assert log.feature_key == "host.event.title"
    assert log.host_id == host.id
    assert log.success is True
    meta = log.meta or {}
    assert meta.get("validation_result") == "passed"
    assert "latency_ms" in meta
    assert meta.get("estimated_cost_micros") is not None


def test_permission_checks(client: TestClient, db_session: Session):
    host, host_user = _seed_host(db_session, email="ai-h2@example.com", slug="ai-h2")
    _seed_event(db_session, host)

    buyer = User(
        email="ai-buyer@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Buyer",
        is_active=True,
    )
    buyer.roles.append(get_role_by_name(db_session, "buyer"))
    db_session.add(buyer)
    db_session.commit()

    denied = client.post(
        "/api/v1/ai/host/generate",
        headers=_login(client, buyer.email),
        json={"feature": "host.event.title"},
    )
    assert denied.status_code == 403

    legacy_denied = client.post(
        "/api/v1/ai/host/generate",
        headers=_login(client, host_user.email),
        json={"feature": "generate_instagram_captions", "notes": "party"},
    )
    assert legacy_denied.status_code == 403
    assert "Legacy host AI" in legacy_denied.json()["detail"]

    host_ok = client.post(
        "/api/v1/ai/host/generate",
        headers=_login(client, host_user.email),
        json={"feature": "host.event.description", "notes": "party vibe"},
    )
    assert host_ok.status_code == 200, host_ok.text

    host_admin_denied = client.post(
        "/api/v1/ai/admin/generate",
        headers=_login(client, host_user.email),
        json={"feature": "explain_revenue_trends"},
    )
    assert host_admin_denied.status_code == 403

    admin = User(
        email="ai-admin@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Admin",
        is_active=True,
    )
    admin.roles.append(get_role_by_name(db_session, "super_admin"))
    db_session.add(admin)
    db_session.commit()

    admin_quarantined = client.post(
        "/api/v1/ai/admin/generate",
        headers=_login(client, admin.email),
        json={"feature": "fraud_risk_summary"},
    )
    assert admin_quarantined.status_code == 403
    assert "not available" in admin_quarantined.json()["detail"].lower()

    recommend_blocked = client.post(
        "/api/v1/ai/admin/generate",
        headers=_login(client, admin.email),
        json={"feature": "recommend_featured_events"},
    )
    assert recommend_blocked.status_code == 403
    support = client.post(
        "/api/v1/ai/admin/support/summary",
        headers=_login(client, admin.email),
    )
    assert support.status_code == 200, support.text


def test_env_api_key_syncs_network_provider_and_route(client: TestClient, db_session: Session):
    from app.ai.constants import FEATURE_HOST_ANNOUNCEMENTS_DRAFT
    from app.ai.feature_routing import (
        get_or_create_feature_route,
        sync_env_network_provider,
    )
    from app.ai.models import AIProviderProfile
    from app.core.config import get_settings

    host, host_user = _seed_host(
        db_session, email="ai-route@example.com", slug="ai-route"
    )
    _ = host

    template = AIProviderProfile(
        provider_type="template_fallback",
        display_name="Template only",
        default_model="template-v1",
        available_models=["template-v1"],
        is_enabled=True,
        priority=1000,
        timeout_seconds=5,
        max_tokens_default=800,
    )
    db_session.add(template)
    db_session.commit()

    with patch.object(get_settings(), "ai_api_key", "sk-test-sync-key-12345"):
        net = sync_env_network_provider(db_session)
        assert net is not None
        assert net.use_env_api_key is True
        route = get_or_create_feature_route(db_session, FEATURE_HOST_ANNOUNCEMENTS_DRAFT)
        primary = db_session.get(AIProviderProfile, route.primary_provider_id)
        assert primary is not None
        assert primary.provider_type != "template_fallback"


def test_team_member_announcement_ai_uses_active_workspace(
    client: TestClient, db_session: Session
):
    from datetime import UTC, datetime

    from app.hosts.models import HostTeamMember
    from app.hosts.team_permissions import pack_scope_json, permissions_for_role
    from app.teams.workspace_pref import set_active_workspace

    host, host_user = _seed_host(
        db_session, email="ai-team-host@example.com", slug="ai-team-host"
    )
    _ = host_user

    client.post(
        "/api/v1/auth/register",
        json={
            "email": "ai-team-member@example.com",
            "password": "securepass1",
            "full_name": "Team Marketer",
        },
    )
    member = db_session.query(User).filter_by(email="ai-team-member@example.com").one()
    perms = permissions_for_role("viewer")
    perms.update({"events.create": True, "events.view": True})
    db_session.add(
        HostTeamMember(
            host_id=host.id,
            user_id=member.id,
            role="viewer",
            role_label="Viewer",
            status="active",
            permissions_json=perms,
            scope_json=pack_scope_json("host_wide"),
            joined_at=datetime.now(UTC),
        )
    )
    db_session.commit()

    set_active_workspace(db_session, user=member, host_id=host.id)
    headers = _login(client, "ai-team-member@example.com")

    resp = client.post(
        "/api/v1/ai/host/generate",
        headers=headers,
        json={
            "feature": "host.announcements.draft",
            "notes": "Weekend show in Ibadan — hype the crowd.",
            "extra": {
                "channel": "email",
                "audience_label": "Followers",
            },
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["suggestion"] or body.get("announcement_email_body")
    log = db_session.query(AIUsageLog).order_by(AIUsageLog.created_at.desc()).first()
    assert log is not None
    assert log.host_id == host.id


def test_announcement_ai_with_related_event(client: TestClient, db_session: Session):
    host, host_user = _seed_host(
        db_session, email="ai-ann-event@example.com", slug="ai-ann-event"
    )
    event = _seed_event(db_session, host)
    headers = _login(client, host_user.email)

    resp = client.post(
        "/api/v1/ai/host/generate",
        headers=headers,
        json={
            "feature": "host.announcements.draft",
            "event_id": str(event.id),
            "notes": "Thank them for coming",
            "extra": {"channel": "both", "audience_label": "Followers"},
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("announcement_email_body") or body.get("suggestion")


def test_fallback_when_provider_unavailable(client: TestClient, db_session: Session):
    from app.ai.providers import AICompletion

    host, host_user = _seed_host(db_session, email="ai-fb@example.com", slug="ai-fb")
    headers = _login(client, host_user.email)

    def _fail_attempt(*_args, **_kwargs):
        return AICompletion(
            text="",
            provider="openai",
            model_name="gpt-test",
            used_fallback=False,
            error_message="simulated outage",
        )

    with patch("app.ai.feature_routing._attempt", side_effect=_fail_attempt):
        resp = client.post(
            "/api/v1/ai/host/generate",
            headers=headers,
            json={"feature": "host.merch.title", "notes": "tee drop"},
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["used_fallback"] is True
    assert body.get("fallback_reason")
    assert body["suggestion"]
    log = db_session.query(AIUsageLog).order_by(AIUsageLog.created_at.desc()).first()
    assert log is not None
    assert log.used_fallback is True


def test_get_ai_provider_respects_disabled_flag():
    settings = Settings(ai_enabled=False, ai_provider="openai", ai_api_key="sk-test")
    provider = get_ai_provider(settings)
    assert isinstance(provider, UnavailableProvider)
    out = provider.complete(system_prompt="s", user_prompt="Task: x")
    assert out.used_fallback is True
