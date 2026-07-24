"""Tests for demo seed sponsorship slots, RBAC seed, and repair mode."""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest
from sqlalchemy import event, func, select

from app.core.config import get_settings
from app.demo.constants import DEMO_HOSTS
from app.demo.models import DemoEntityMarker
from app.demo.seed import repair_demo_data, seed_demo_data
from app.demo.sponsor_demo_seed import SPONSOR_SPECS, seed_rich_sponsor_demo
from app.hosts.models import Host
from app.sponsorships.models import (
    Sponsor,
    SponsorCampaign,
    SponsorSavedItem,
    SponsorshipDeal,
    SponsorshipDeliverable,
    SponsorshipSlot,
)
from app.users.models import Permission, Role, User
from app.users.seed import seed_roles_and_permissions
from app.users.service import get_user_by_email


@pytest.fixture()
def demo_settings(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("FRONTEND_URL", "http://localhost:3000")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture()
def sponsor_demo_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("FRONTEND_URL", "http://localhost:3000")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_seed_roles_and_permissions_idempotent(db_session) -> None:
    seed_roles_and_permissions(db_session)
    perm_count = db_session.scalar(select(func.count()).select_from(Permission)) or 0
    role_count = db_session.scalar(select(func.count()).select_from(Role)) or 0
    assert perm_count > 0
    assert role_count > 0

    query_count = {"n": 0}

    def _count_queries(_conn, _cursor, _statement, _parameters, _context, _executemany):
        query_count["n"] += 1

    event.listen(db_session.bind, "before_cursor_execute", _count_queries)
    try:
        start = time.perf_counter()
        seed_roles_and_permissions(db_session)
        elapsed = time.perf_counter() - start
    finally:
        event.remove(db_session.bind, "before_cursor_execute", _count_queries)

    assert (
        db_session.scalar(select(func.count()).select_from(Permission)) == perm_count
    )
    assert db_session.scalar(select(func.count()).select_from(Role)) == role_count
    assert query_count["n"] <= 12, f"too many RBAC queries: {query_count['n']}"
    assert elapsed < 2.0


def test_base_demo_seed_creates_sponsorship_slots(demo_settings, db_session) -> None:
    result = seed_demo_data(db_session, reset=True)
    assert result["status"] == "seeded"
    published = int(result.get("sponsorship_slots_published") or 0)
    assert published >= 8

    host_ids = [
        row.id
        for row in db_session.scalars(
            select(Host).where(Host.slug.in_([h["slug"] for h in DEMO_HOSTS]))
        ).all()
    ]
    slot_count = (
        db_session.scalar(
            select(func.count())
            .select_from(SponsorshipSlot)
            .where(
                SponsorshipSlot.host_id.in_(host_ids),
                SponsorshipSlot.status == "published",
            )
        )
        or 0
    )
    assert slot_count >= 8


def test_base_demo_seed_writes_completion_marker(demo_settings, db_session) -> None:
    seed_demo_data(db_session, reset=True)
    marker = db_session.scalar(
        select(DemoEntityMarker).where(
            DemoEntityMarker.entity_type == "seed",
            DemoEntityMarker.entity_key == "complete",
        )
    )
    assert marker is not None


def test_repair_partial_demo_data(demo_settings, db_session) -> None:
    seed_demo_data(db_session, reset=True)
    marker = db_session.scalar(
        select(DemoEntityMarker).where(
            DemoEntityMarker.entity_type == "seed",
            DemoEntityMarker.entity_key == "complete",
        )
    )
    assert marker is not None
    db_session.delete(marker)
    db_session.execute(
        User.__table__.delete().where(User.email.like("fan%@demo.padeye.test"))
    )
    db_session.commit()

    repaired = repair_demo_data(db_session)
    assert repaired["status"] == "repaired"
    assert repaired.get("fans", 0) >= 20
    assert repaired["sponsorship_slots_published"] >= 8
    from app.taxonomy.models import Location

    assert (
        db_session.scalar(
            select(func.count())
            .select_from(Location)
            .where(Location.kind == "country")
        )
        or 0
    ) >= 1
    assert get_user_by_email(db_session, "fan1@demo.padeye.test") is not None
    assert db_session.scalar(
        select(DemoEntityMarker.id).where(
            DemoEntityMarker.entity_type == "seed",
            DemoEntityMarker.entity_key == "complete",
        )
    )


def test_sponsor_demo_seed_repairs_partial_rows(
    db_session, demo_settings, sponsor_demo_env
) -> None:
    seed_demo_data(db_session, reset=True)
    with patch("app.notifications.service.notify_user"):
        seed_rich_sponsor_demo(db_session, force=True)

    partial = db_session.scalar(select(Sponsor).where(Sponsor.slug == "neonpalm-drinks"))
    assert partial is not None
    db_session.execute(
        SponsorCampaign.__table__.delete().where(
            SponsorCampaign.sponsor_id == partial.id
        )
    )
    db_session.execute(
        DemoEntityMarker.__table__.delete().where(
            DemoEntityMarker.entity_type == "sponsor_seed",
            DemoEntityMarker.entity_key == "complete",
        )
    )
    db_session.commit()

    with patch("app.notifications.service.notify_user") as notify:
        result = seed_rich_sponsor_demo(db_session, force=True)
    notify.assert_not_called()

    assert result["sponsors"] == 6
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(SponsorCampaign)
            .join(Sponsor, SponsorCampaign.sponsor_id == Sponsor.id)
            .where(Sponsor.slug == "neonpalm-drinks")
        )
        or 0
    ) >= 2
    assert db_session.scalar(
        select(DemoEntityMarker.id).where(
            DemoEntityMarker.entity_type == "sponsor_seed",
            DemoEntityMarker.entity_key == "complete",
        )
    )


def test_sponsor_demo_seed_creates_expected_entities(
    db_session, demo_settings, sponsor_demo_env
) -> None:
    seed_demo_data(db_session, reset=True)
    with patch("app.payments.paystack.initialize_transaction") as init_txn, patch(
        "app.notifications.service.notify_user"
    ) as notify:
        result = seed_rich_sponsor_demo(db_session, force=True)
    init_txn.assert_not_called()
    notify.assert_not_called()

    assert result["sponsors"] == 6
    slugs = {s.slug for s in db_session.scalars(select(Sponsor)).all()}
    assert slugs.issuperset({spec.slug for spec in SPONSOR_SPECS})

    assert (
        db_session.scalar(
            select(func.count())
            .select_from(SponsorCampaign)
            .join(Sponsor, SponsorCampaign.sponsor_id == Sponsor.id)
            .where(Sponsor.slug.in_([s.slug for s in SPONSOR_SPECS]))
        )
        or 0
    ) >= 6
    assert (
        db_session.scalar(select(func.count()).select_from(SponsorSavedItem)) or 0
    ) >= 6
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(SponsorshipDeal)
            .join(Sponsor, SponsorshipDeal.sponsor_id == Sponsor.id)
            .where(Sponsor.slug.in_([s.slug for s in SPONSOR_SPECS]))
        )
        or 0
    ) >= 4
    assert (
        db_session.scalar(select(func.count()).select_from(SponsorshipDeliverable)) or 0
    ) >= 6
    assert db_session.scalar(
        select(DemoEntityMarker.id).where(
            DemoEntityMarker.entity_type == "sponsor_seed",
            DemoEntityMarker.entity_key == "complete",
        )
    )
