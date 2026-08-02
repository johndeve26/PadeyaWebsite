"""Test fixtures using an isolated SQLite database (or Phase 4.5 Postgres)."""

from __future__ import annotations

import os

# Configure test DB before app imports bind the engine.
# Phase 4.5: PHASE45_POSTGRES=1 + TEST_DATABASE_URL → isolated PostgreSQL.
_PHASE45 = os.environ.get("PHASE45_POSTGRES", "").strip() == "1"
if _PHASE45:
    _pg = (os.environ.get("TEST_DATABASE_URL") or "").strip()
    if not _pg:
        raise RuntimeError("PHASE45_POSTGRES=1 requires TEST_DATABASE_URL")
    from tests.helpers.postgres_safety import assert_safe_postgres_url

    assert_safe_postgres_url(_pg, app_env=os.environ.get("APP_ENV", "test"))
    os.environ["DATABASE_URL"] = _pg
else:
    os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["APP_ENV"] = "test"
os.environ["DEMO_MODE"] = "false"
os.environ["FRONTEND_URL"] = "http://localhost:3000"
os.environ["EMAIL_PROVIDER"] = "log"
os.environ["EMAIL_ENABLED"] = "true"
os.environ["EMAIL_DEV_MODE"] = "true"
os.environ["EMAIL_QUEUE_ENABLED"] = "true"
os.environ["PUSH_QUEUE_ENABLED"] = "true"
os.environ["EMAIL_SETTINGS_ENCRYPTION_KEY"] = "test-email-settings-encryption-key"
os.environ["MEDIA_PUBLIC_BASE_URL"] = "http://testserver"
os.environ["MEDIA_ROOT"] = "media_uploads_test"
os.environ["MEDIA_STORAGE_PROVIDER"] = "local"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.audit import AuditLog  # noqa: F401
from app.core.database import Base, get_db
from app.auth import models as auth_models  # noqa: F401
from app.users import models as user_models  # noqa: F401
from app.admin import impersonation_models as admin_impersonation_models  # noqa: F401
from app.hosts import models as host_models  # noqa: F401
from app.events import models as event_models  # noqa: F401
from app.payments import models as payment_models  # noqa: F401
from app.tickets import models as ticket_models  # noqa: F401
from app.checkins import models as checkin_models  # noqa: F401
from app.reviews import models as review_models  # noqa: F401
from app.legacy import models as legacy_models  # noqa: F401
from app.promos import models as promo_models  # noqa: F401
from app.crm import models as crm_models  # noqa: F401
from app.finance import models as finance_models  # noqa: F401
from app.finance.fees import models as finance_fee_models  # noqa: F401
from app.vault import models as vault_models  # noqa: F401
from app.passport import models as passport_models  # noqa: F401
from app.messaging import models as messaging_models  # noqa: F401
from app.fan_connect import models as fan_connect_models  # noqa: F401
from app.memories import models as memories_models  # noqa: F401
from app.analytics import models as analytics_models  # noqa: F401
from app.ai import models as ai_models  # noqa: F401
from app.sponsorships import models as sponsorships_models  # noqa: F401
from app.tickets import advanced_models as ticket_advanced_models  # noqa: F401
from app.demo import models as demo_models  # noqa: F401
from app.support import models as support_models  # noqa: F401
from app.cms import models as cms_models  # noqa: F401
from app.taxonomy import models as taxonomy_models  # noqa: F401
from app.merch import models as merch_models  # noqa: F401
from app.email import models as email_models  # noqa: F401
from app.notifications import models as notifications_models  # noqa: F401
from app.teams import scan_audit as teams_scan_audit  # noqa: F401
from app.teams import workspace_pref as teams_workspace_pref  # noqa: F401
from app.runtime_settings import models as runtime_settings_models  # noqa: F401
from app.maintenance import models as maintenance_models  # noqa: F401
from app.blog import models as blog_models  # noqa: F401
from app.knowledge_base import models as knowledge_base_models  # noqa: F401
from app.main import app
from app.core.config import get_settings
from app.events.seed import seed_event_categories
from app.legacy.seed import seed_legacy_tiers
from app.passport.seed import seed_fan_badges
from app.ai.seed import seed_ai_prompt_templates
from app.taxonomy.service import seed_taxonomy_vocab
from app.users.models import User
from app.users.seed import seed_roles_and_permissions
from app.users.service import get_role_by_name

get_settings.cache_clear()


def _seed_paystack_test_settings(session: Session) -> None:
    """Payment/webhook tests expect test Paystack keys — admin runtime_settings only."""
    from app.runtime_settings.service import runtime_settings_service as svc

    svc.upsert(session, category="payments", key="paystack_mode", value="test", commit=False)
    svc.upsert(
        session,
        category="payments",
        key="paystack_secret_key",
        value="sk_test_padeya",
        commit=False,
    )
    svc.upsert(
        session,
        category="payments",
        key="paystack_public_key",
        value="pk_test_padeya",
        commit=False,
    )
    svc.upsert(
        session,
        category="payments",
        key="paystack_webhook_secret",
        value="sk_test_padeya",
        commit=False,
    )
    session.commit()


@pytest.fixture()
def db_engine():
    if _PHASE45:
        from sqlalchemy.pool import NullPool

        engine = create_engine(
            os.environ["DATABASE_URL"],
            poolclass=NullPool,
            future=True,
        )
        # Schema comes from Alembic on the isolated Phase 4.5 DB — do not drop.
        try:
            yield engine
        finally:
            engine.dispose()
        return

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record):  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()
    seed_roles_and_permissions(session)
    seed_event_categories(session)
    seed_taxonomy_vocab(session)
    seed_legacy_tiers(session)
    seed_fan_badges(session)
    seed_ai_prompt_templates(session)
    _seed_paystack_test_settings(session)
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session: Session, db_engine):
    import app.core.database as database

    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=db_engine
    )
    previous_session_local = database.SessionLocal
    database.SessionLocal = TestingSessionLocal

    if _PHASE45:
        # Per-request sessions so concurrent workers do not share one Session.
        # Webhook/payment routes manage commit/rollback themselves — do not
        # auto-commit/rollback here (that can undo or mask transactional intent).
        def _override_get_db():
            session = TestingSessionLocal()
            try:
                yield session
            finally:
                session.close()
    else:
        def _override_get_db():
            try:
                yield db_session
            finally:
                pass

    app.dependency_overrides[get_db] = _override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        database.SessionLocal = previous_session_local


@pytest.fixture()
def assign_role(db_session: Session):
    def _assign(email: str, role_name: str) -> User:
        user = db_session.query(User).filter(User.email == email.lower()).one()
        role = get_role_by_name(db_session, role_name)
        assert role is not None
        if role not in user.roles:
            user.roles.append(role)
            db_session.commit()
            db_session.refresh(user)
        return user

    return _assign


@pytest.fixture(autouse=True)
def auto_verify_registered_users_in_tests(db_session: Session, request: pytest.FixtureRequest):
    """Most suites assume registered users can run gated flows; email verification tests opt out."""
    if request.node.fspath.basename == "test_email_verification.py":
        yield
        return

    from app.auth import router as auth_router
    from app.auth import service as auth_service

    original = auth_service.register_user

    def register_user_verified_for_tests(*args, **kwargs):
        user, tokens = original(*args, **kwargs)
        row = db_session.get(User, user.id)
        if row is not None and not row.is_verified:
            row.is_verified = True
            db_session.commit()
        return user, tokens

    auth_service.register_user = register_user_verified_for_tests
    auth_router.register_user = register_user_verified_for_tests
    try:
        yield
    finally:
        auth_service.register_user = original
        auth_router.register_user = original
