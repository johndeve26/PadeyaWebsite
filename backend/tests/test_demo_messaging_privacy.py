"""Demo seed + messaging privacy contract tests.

Seeds once per module (expensive), then verifies inbox QA, privacy scrubbing,
and serializer safety for message views.
"""

from __future__ import annotations

import os
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure demo ops allowed before settings cache is used.
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DEMO_MODE", "true")

from app.core.config import get_settings
from app.core.database import Base, get_db
from app.demo.constants import DEMO_EMAIL_DOMAIN, DEMO_PASSWORD
from app.demo.messaging_privacy import (
    DEMO_MESSAGE_BANNED_SUBSTRINGS,
    assert_safe_demo_copy,
)
from app.demo.seed import seed_demo_data
from app.events.models import Event
from app.hosts.models import Host
from app.main import app
from app.messaging.models import Message, MessageReport, MessageThread
from app.messaging.service import (
    get_thread_detail,
    list_threads_for_fan,
    list_threads_for_host,
)
from app.passport.directory_service import list_directory_passports
from app.passport.models import FanPassport
from app.users.models import User
from app.users.seed import seed_roles_and_permissions
from app.users.service import get_user_by_email
from app.events.seed import seed_event_categories
from app.legacy.seed import seed_legacy_tiers
from app.passport.seed import seed_fan_badges
from app.ai.seed import seed_ai_prompt_templates
from app.taxonomy.service import seed_taxonomy_vocab
from app.vault.models import VaultItem

# Import model packages so metadata registers (same set as conftest).
from app.core.audit import AuditLog  # noqa: F401
from app.auth import models as auth_models  # noqa: F401
from app.users import models as user_models  # noqa: F401
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
from app.vault import models as vault_models  # noqa: F401
from app.passport import models as passport_models  # noqa: F401
from app.messaging import models as messaging_models  # noqa: F401
from app.memories import models as memories_models  # noqa: F401
from app.analytics import models as analytics_models  # noqa: F401
from app.ai import models as ai_models  # noqa: F401
from app.sponsorships import models as sponsorships_models  # noqa: F401
from app.tickets import advanced_models as ticket_advanced_models  # noqa: F401
from app.demo import models as demo_models  # noqa: F401
from app.support import models as support_models  # noqa: F401
from app.cms import models as cms_models  # noqa: F401
from app.taxonomy import models as taxonomy_models  # noqa: F401


@pytest.fixture(scope="module")
def demo_engine():
    get_settings.cache_clear()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _fk(dbapi_connection, _record):  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
        get_settings.cache_clear()


@pytest.fixture(scope="module")
def demo_db(demo_engine) -> Session:
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=demo_engine)
    session = SessionLocal()
    seed_roles_and_permissions(session)
    seed_event_categories(session)
    seed_taxonomy_vocab(session)
    seed_legacy_tiers(session)
    seed_fan_badges(session)
    seed_ai_prompt_templates(session)
    result = seed_demo_data(session, reset=True)
    assert result["status"] == "seeded"
    assert result.get("message_threads", 0) >= 1 or (
        session.scalar(select(func.count()).select_from(MessageThread)) or 0
    ) >= 1
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="module")
def demo_client(demo_db: Session):
    def _override():
        try:
            yield demo_db
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.pop(get_db, None)


def _login(client: TestClient, email: str) -> dict[str, str]:
    res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": DEMO_PASSWORD},
    )
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def _blob(obj: object) -> str:
    return str(obj).lower()


# --- Unit: privacy guard (no seed) -------------------------------------------------


@pytest.mark.parametrize(
    "bad",
    [
        "Ping me on WhatsApp",
        "Call me at +2348012345678",
        "email me at fan@gmail.com",
        "Send money via bank transfer",
        "Pay here https://paystack.com/pay/x",
        "LOCKED DEMO BODY for slide deck",
    ],
)
def test_assert_safe_demo_copy_rejects_contact_patterns(bad: str) -> None:
    with pytest.raises(AssertionError):
        assert_safe_demo_copy(bad)


def test_assert_safe_demo_copy_allows_safe_placeholders() -> None:
    assert_safe_demo_copy("Open your Pàdéyá ticket and use your QR code at check-in.")
    assert_safe_demo_copy("Refresh your Vault page. Check your dashboard.")


# --- Seed contract -----------------------------------------------------------------


def test_demo_seed_creates_message_threads(demo_db: Session) -> None:
    n = demo_db.scalar(select(func.count()).select_from(MessageThread)) or 0
    m = demo_db.scalar(select(func.count()).select_from(Message)) or 0
    assert n >= 10
    assert m >= 20


def test_demo_seed_idempotent(demo_db: Session) -> None:
    before_threads = demo_db.scalar(select(func.count()).select_from(MessageThread)) or 0
    before_messages = demo_db.scalar(select(func.count()).select_from(Message)) or 0
    again = seed_demo_data(demo_db, reset=False)
    assert again["status"] == "already_seeded"
    after_threads = demo_db.scalar(select(func.count()).select_from(MessageThread)) or 0
    after_messages = demo_db.scalar(select(func.count()).select_from(Message)) or 0
    assert after_threads == before_threads
    assert after_messages == before_messages


def test_private_fans_not_exposed_in_directory(demo_db: Session) -> None:
    private = demo_db.scalars(
        select(FanPassport).where(FanPassport.visibility == "private")
    ).all()
    assert any(p.username == "miralagos" for p in private)
    assert any(p.username == "adafirsttimer" for p in private)
    cards = list_directory_passports(demo_db, page=1, limit=48)
    usernames = {c["username"] for c in cards["items"]}
    assert "miralagos" not in usernames
    assert "adafirsttimer" not in usernames
    assert "bayocampus" not in usernames  # unlisted
    assert "toluwave" in usernames


def test_message_bodies_do_not_expose_contact_info_patterns(demo_db: Session) -> None:
    bodies = " ".join(demo_db.scalars(select(Message.body)).all()).lower()
    for banned in DEMO_MESSAGE_BANNED_SUBSTRINGS:
        assert banned not in bodies, banned


def test_fan_inbox_has_expected_demo_threads(demo_db: Session) -> None:
    tolu = get_user_by_email(demo_db, f"fan1@{DEMO_EMAIL_DOMAIN}")
    amaka = get_user_by_email(demo_db, f"fan2@{DEMO_EMAIL_DOMAIN}")
    chidi = get_user_by_email(demo_db, f"fan3@{DEMO_EMAIL_DOMAIN}")
    assert tolu and amaka and chidi
    tolu_inbox = list_threads_for_fan(
        demo_db, tolu, filter_key="all", q=None, page=1, limit=50
    )
    amaka_inbox = list_threads_for_fan(
        demo_db, amaka, filter_key="all", q=None, page=1, limit=50
    )
    chidi_inbox = list_threads_for_fan(
        demo_db, chidi, filter_key="all", q=None, page=1, limit=50
    )
    # "all" excludes archived; Tolu still has active + blocked
    assert tolu_inbox["total"] >= 3
    assert amaka_inbox["total"] >= 2
    assert chidi_inbox["total"] >= 2
    assert any(t["counterpart"]["display_name"] for t in tolu_inbox["items"])


def test_host_inbox_has_expected_demo_threads(demo_db: Session) -> None:
    maze = demo_db.scalar(select(Host).where(Host.slug == "djmaze"))
    comedy = demo_db.scalar(select(Host).where(Host.slug == "lagoscomedyhub"))
    tech = demo_db.scalar(select(Host).where(Host.slug == "techconnectafrica"))
    praise = demo_db.scalar(select(Host).where(Host.slug == "praiseexperience"))
    mainland = demo_db.scalar(select(Host).where(Host.slug == "mainlandvibes"))
    assert maze and comedy and tech and praise and mainland
    maze_owner = demo_db.get(User, maze.user_id)
    comedy_owner = demo_db.get(User, comedy.user_id)
    tech_owner = demo_db.get(User, tech.user_id)
    praise_owner = demo_db.get(User, praise.user_id)
    mainland_owner = demo_db.get(User, mainland.user_id)
    assert maze_owner and comedy_owner and tech_owner and praise_owner and mainland_owner

    maze_inbox = list_threads_for_host(
        demo_db, maze_owner, filter_key="all", q=None, page=1, limit=50
    )
    comedy_inbox = list_threads_for_host(
        demo_db, comedy_owner, filter_key="all", q=None, page=1, limit=50
    )
    tech_inbox = list_threads_for_host(
        demo_db, tech_owner, filter_key="all", q=None, page=1, limit=50
    )
    praise_requests = list_threads_for_host(
        demo_db, praise_owner, filter_key="requests", q=None, page=1, limit=50
    )
    mainland_inbox = list_threads_for_host(
        demo_db, mainland_owner, filter_key="all", q=None, page=1, limit=50
    )

    # "all" excludes host-archived (Maze has 1 archived → 3 visible)
    assert maze_inbox["total"] == 3
    assert comedy_inbox["total"] == 3
    assert tech_inbox["total"] == 3
    assert praise_requests["total"] >= 1
    assert mainland_inbox["total"] >= 2


def test_reported_message_appears_in_admin_report_list(
    demo_client: TestClient, demo_db: Session
) -> None:
    admin_h = _login(demo_client, f"admin@{DEMO_EMAIL_DOMAIN}")
    listed = demo_client.get("/api/v1/admin/message-reports", headers=admin_h)
    assert listed.status_code == 200, listed.text
    body = listed.json()
    assert body["total"] >= 2
    statuses = {item["status"] for item in body["items"]}
    assert "reviewing" in statuses or "open" in statuses
    # DB also has Bayo's reviewing report
    bayo = get_user_by_email(demo_db, f"fan8@{DEMO_EMAIL_DOMAIN}")
    assert bayo is not None
    report = demo_db.scalar(
        select(MessageReport).where(MessageReport.reporter_user_id == bayo.id)
    )
    assert report is not None
    assert report.status == "reviewing"
    detail = demo_client.get(
        f"/api/v1/admin/message-reports/{report.id}", headers=admin_h
    )
    assert detail.status_code == 200
    blob = _blob(detail.json())
    assert "whatsapp" not in blob
    assert "@demo." not in blob
    assert "locked demo body" not in blob


def test_blocked_thread_disables_sending(
    demo_client: TestClient, demo_db: Session
) -> None:
    tolu = get_user_by_email(demo_db, f"fan1@{DEMO_EMAIL_DOMAIN}")
    comedy = demo_db.scalar(select(Host).where(Host.slug == "lagoscomedyhub"))
    assert tolu and comedy
    blocked = demo_db.scalar(
        select(MessageThread).where(
            MessageThread.fan_user_id == tolu.id,
            MessageThread.host_id == comedy.id,
            MessageThread.status == "blocked",
        )
    )
    assert blocked is not None
    detail = get_thread_detail(demo_db, tolu, blocked.id)
    assert detail["blocked"] is True
    assert detail["can_reply"] is False

    headers = _login(demo_client, f"fan1@{DEMO_EMAIL_DOMAIN}")
    send = demo_client.post(
        f"/api/v1/messages/{blocked.id}/send",
        headers=headers,
        json={"body": "Should not send"},
    )
    assert send.status_code in {400, 403, 409}


def test_message_request_appears_in_request_state(
    demo_client: TestClient, demo_db: Session
) -> None:
    ada = get_user_by_email(demo_db, f"fan7@{DEMO_EMAIL_DOMAIN}")
    praise = demo_db.scalar(select(Host).where(Host.slug == "praiseexperience"))
    assert ada and praise
    thread = demo_db.scalar(
        select(MessageThread).where(
            MessageThread.fan_user_id == ada.id,
            MessageThread.host_id == praise.id,
        )
    )
    assert thread is not None
    assert thread.status == "request"
    praise_owner = demo_db.get(User, praise.user_id)
    assert praise_owner is not None
    detail = get_thread_detail(demo_db, praise_owner, thread.id)
    assert detail["is_request"] is True
    assert detail["status"] == "request"

    headers = _login(demo_client, f"praise@{DEMO_EMAIL_DOMAIN}")
    inbox = demo_client.get(
        "/api/v1/host/messages?filter=requests", headers=headers
    )
    assert inbox.status_code == 200
    ids = {item["id"] for item in inbox.json()["items"]}
    assert str(thread.id) in ids


def test_archived_thread_remains_readable(
    demo_client: TestClient, demo_db: Session
) -> None:
    mira = get_user_by_email(demo_db, f"fan6@{DEMO_EMAIL_DOMAIN}")
    maze = demo_db.scalar(select(Host).where(Host.slug == "djmaze"))
    assert mira and maze
    thread = demo_db.scalar(
        select(MessageThread).where(
            MessageThread.fan_user_id == mira.id,
            MessageThread.host_id == maze.id,
        )
    )
    assert thread is not None
    assert thread.fan_archived_at is not None
    detail = get_thread_detail(demo_db, mira, thread.id)
    assert len(detail["messages"]) >= 1
    assert any(m["message_type"] == "system" for m in detail["messages"])

    headers = _login(demo_client, f"fan6@{DEMO_EMAIL_DOMAIN}")
    res = demo_client.get(f"/api/v1/messages/{thread.id}", headers=headers)
    assert res.status_code == 200
    assert len(res.json()["messages"]) >= 1


def test_private_event_location_not_exposed_in_message_serializers(
    demo_db: Session,
) -> None:
    # Attach a private-address event to an existing demo thread chip path
    thread = demo_db.scalar(
        select(MessageThread).where(MessageThread.related_event_id.is_not(None)).limit(1)
    )
    assert thread is not None
    event = demo_db.get(Event, thread.related_event_id)
    assert event is not None
    event.address = "12 Secret Street, Victoria Island"
    event.location_visibility = "hidden_until_payment"
    event.venue_name = "Hidden Private Venue"
    demo_db.commit()

    fan = demo_db.get(User, thread.fan_user_id)
    assert fan is not None
    detail = get_thread_detail(demo_db, fan, thread.id)
    chip = detail.get("related_event") or {}
    blob = _blob(detail)
    assert "secret street" not in blob
    assert "hidden private venue" not in blob
    assert "address" not in chip
    assert "venue_name" not in chip
    assert chip.get("path", "").startswith("/events/")


def test_locked_vault_content_not_exposed_in_message_serializers(
    demo_db: Session,
) -> None:
    locked = demo_db.scalar(
        select(VaultItem).where(VaultItem.slug == "unreleased-set")
    )
    assert locked is not None
    assert locked.body and "LOCKED" in locked.body

    # No message body / thread payload may carry locked vault body text
    bodies = " ".join(demo_db.scalars(select(Message.body)).all())
    assert "LOCKED DEMO BODY" not in bodies
    assert "example.com/demo-secret" not in bodies.lower()

    tolu = get_user_by_email(demo_db, f"fan1@{DEMO_EMAIL_DOMAIN}")
    maze = demo_db.scalar(select(Host).where(Host.slug == "djmaze"))
    assert tolu and maze
    thread = demo_db.scalar(
        select(MessageThread).where(
            MessageThread.fan_user_id == tolu.id,
            MessageThread.host_id == maze.id,
        )
    )
    assert thread is not None
    detail = get_thread_detail(demo_db, tolu, thread.id)
    blob = _blob(detail)
    assert "locked demo body" not in blob
    assert "related_order_id" not in detail
    assert "related_ticket_id" not in detail
