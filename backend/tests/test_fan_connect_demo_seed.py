"""Fan Connect demo seed — relationships, exclusions, fan↔fan thread."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_password
from app.demo.constants import DEMO_EMAIL_DOMAIN, DEMO_PASSWORD
from app.demo.fan_connect_seed import seed_fan_connect_demo
from app.fan_connect import constants as C
from app.fan_connect.eligibility import canonical_pair, ensure_connect_settings
from app.fan_connect.models import FanConnection, FanConnectionBlock, FanConnectionReport
from app.messaging import constants as MC
from app.messaging.models import Message, MessageThread
from app.passport.privacy import VISIBILITY_PRIVATE, VISIBILITY_PUBLIC, VISIBILITY_UNLISTED
from app.passport.service import ensure_passport
from app.users.models import User
from app.users.service import get_role_by_name, get_user_by_email


@pytest.fixture()
def demo_settings(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("FRONTEND_URL", "http://localhost:3000")
    get_settings.cache_clear()
    yield get_settings()
    get_settings.cache_clear()


def _ensure_demo_fan(db, *, n: int, name: str, visibility: str) -> User:
    email = f"fan{n}@{DEMO_EMAIL_DOMAIN}"
    user = get_user_by_email(db, email)
    if user is None:
        user = User(
            email=email,
            password_hash=hash_password(DEMO_PASSWORD),
            full_name=name,
            is_active=True,
        )
        db.add(user)
        db.flush()
        role = get_role_by_name(db, "buyer")
        if role is not None:
            user.roles.append(role)
    else:
        user.full_name = name
    pp = ensure_passport(db, user)
    pp.username = f"demo{n}"
    pp.display_name = name
    pp.visibility = visibility
    pp.appear_in_directory = visibility == VISIBILITY_PUBLIC
    db.flush()
    return user


def test_fan_connect_demo_seed_scenarios(demo_settings, db_session) -> None:
    tolu = _ensure_demo_fan(
        db_session, n=1, name="Tolu Nightlife Explorer", visibility=VISIBILITY_PUBLIC
    )
    amaka = _ensure_demo_fan(
        db_session, n=2, name="Amaka Concert Lover", visibility=VISIBILITY_PUBLIC
    )
    chidi = _ensure_demo_fan(
        db_session, n=3, name="Chidi Tech Regular", visibility=VISIBILITY_PUBLIC
    )
    sade = _ensure_demo_fan(
        db_session, n=4, name="Sade Comedy Fan", visibility=VISIBILITY_PUBLIC
    )
    kunle = _ensure_demo_fan(
        db_session, n=5, name="Kunle VIP Regular", visibility=VISIBILITY_PUBLIC
    )
    mira = _ensure_demo_fan(
        db_session, n=6, name="Mira Lagos Explorer", visibility=VISIBILITY_PRIVATE
    )
    ada = _ensure_demo_fan(
        db_session, n=7, name="Ada First Timer", visibility=VISIBILITY_PRIVATE
    )
    bayo = _ensure_demo_fan(
        db_session, n=8, name="Bayo Campus Fan", visibility=VISIBILITY_UNLISTED
    )
    bode = _ensure_demo_fan(
        db_session, n=12, name="Bode Food & Flow", visibility=VISIBILITY_PUBLIC
    )
    db_session.commit()

    counts = seed_fan_connect_demo(db_session)
    assert counts["fan_connect_enabled"] >= 6
    assert counts["fan_connect_suggested"] == 1
    assert counts["fan_connect_pending"] == 2
    assert counts["fan_connect_accepted"] == 1
    assert counts["fan_connect_blocked"] == 1
    assert counts["fan_connect_messages"] >= 5
    assert counts["fan_connect_attachments"] == 2
    assert counts["fan_connect_reports"] == 1
    assert counts["fan_connect_excluded"] == 2  # Mira + Ada

    assert ensure_connect_settings(db_session, tolu).fan_connect_enabled is True
    assert ensure_connect_settings(db_session, tolu).discoverable_for_same_events is True
    assert ensure_connect_settings(db_session, tolu).allow_connection_requests is True
    assert ensure_connect_settings(db_session, amaka).discoverable_for_same_events is True
    assert ensure_connect_settings(db_session, mira).fan_connect_enabled is False
    assert ensure_connect_settings(db_session, ada).fan_connect_enabled is False
    assert ensure_passport(db_session, mira).visibility == VISIBILITY_PRIVATE
    assert ensure_passport(db_session, ada).visibility == VISIBILITY_PRIVATE

    def pair(a: User, b: User) -> FanConnection | None:
        low, high = canonical_pair(a.id, b.id)
        return db_session.scalar(
            select(FanConnection).where(
                FanConnection.user_low_id == low,
                FanConnection.user_high_id == high,
            )
        )

    sug = pair(tolu, amaka)
    assert sug is not None and sug.status == C.STATUS_SUGGESTED
    labels = " ".join(str(r.get("label", "")) for r in (sug.reasons_json or []))
    assert "Afrobeats Night Live" in labels
    assert "DJ Maze" in labels

    pending_sade = pair(tolu, sade)
    assert pending_sade is not None and pending_sade.status == C.STATUS_REQUEST_SENT
    assert pending_sade.requester_user_id == tolu.id
    assert "Lagos Comedy Hub" in (pending_sade.request_message or "")

    connected = pair(chidi, bayo)
    assert connected is not None and connected.status == C.STATUS_CONNECTED
    assert connected.message_thread_id is not None
    thread = db_session.get(MessageThread, connected.message_thread_id)
    assert thread is not None
    assert thread.thread_type == MC.THREAD_TYPE_FAN_FAN
    bodies = [
        m.body
        for m in db_session.scalars(
            select(Message).where(Message.thread_id == thread.id)
        ).all()
    ]
    assert any("Product Demo Night" in b and "Pàdéyá" in b for b in bodies)
    assert any("demo circle" in b for b in bodies)
    assert any("pitch next time" in b for b in bodies)

    from app.messaging.models import MessageAttachment

    att_names = {
        a.original_filename
        for a in db_session.scalars(
            select(MessageAttachment).where(
                MessageAttachment.thread_id == thread.id,
                MessageAttachment.deleted_at.is_(None),
            )
        ).all()
    }
    assert "product-demo-night-agenda.png" in att_names
    assert "demo-night-schedule.pdf" in att_names

    pending_kunle = pair(amaka, kunle)
    assert pending_kunle is not None and pending_kunle.status == C.STATUS_REQUEST_SENT
    assert pair(ada, mira) is None

    # Mira/Ada never appear as suggestion partners for enabled demo fans
    for excluded in (mira, ada):
        for partner in (tolu, amaka, chidi, sade, kunle, bode):
            row = pair(excluded, partner)
            assert row is None or row.status != C.STATUS_SUGGESTED

    blocked = pair(tolu, bode)
    assert blocked is not None and blocked.status == C.STATUS_BLOCKED
    assert (
        db_session.scalar(
            select(FanConnectionBlock).where(
                FanConnectionBlock.blocker_user_id == tolu.id,
                FanConnectionBlock.blocked_user_id == bode.id,
            )
        )
        is not None
    )
    assert (
        db_session.scalar(
            select(FanConnectionReport).where(
                FanConnectionReport.reporter_user_id == tolu.id,
                FanConnectionReport.reported_user_id == bode.id,
            )
        )
        is not None
    )

    # Idempotent refresh
    again = seed_fan_connect_demo(db_session)
    assert again["fan_connect_accepted"] == 1
    assert again["fan_connect_pending"] == 2
