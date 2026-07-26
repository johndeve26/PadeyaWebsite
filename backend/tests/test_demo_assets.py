"""Tests for demo asset URL helpers and Smartlance legacy rewrite."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.config import get_settings
from app.demo import assets
from app.demo.legacy_url_backfill import backfill_legacy_smartlance_demo_urls
from app.events.models import Event
from app.memories.models import EventMemoryMedia
from sqlalchemy.orm import Session


@pytest.fixture()
def frontend_padeya(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("FRONTEND_URL", "https://padeya.com")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_demo_asset_url_is_relative_not_absolute(frontend_padeya) -> None:
    url = assets.memory_image("detty-friday-memory")
    assert url == "/demo/memories/detty-friday-memory.svg"
    assert "smartlancedesigns.com" not in url
    assert not url.startswith("http")


def test_event_banner_relative(frontend_padeya) -> None:
    assert assets.event_banner("afrobeats-night-live") == (
        "/demo/events/afrobeats-night-live.svg"
    )


def test_normalize_rewrites_smartlance_to_relative(frontend_padeya) -> None:
    old = (
        "https://padeya.smartlancedesigns.com/demo/memories/detty-friday-memory.svg"
    )
    assert assets.normalize_demo_asset_url(old) == (
        "/demo/memories/detty-friday-memory.svg"
    )
    assert assets.rewrite_legacy_smartlance_demo_url(old) == (
        "/demo/memories/detty-friday-memory.svg"
    )


def test_normalize_rewrites_http_and_www_variants(frontend_padeya) -> None:
    assert assets.rewrite_legacy_smartlance_demo_url(
        "http://www.padeya.smartlancedesigns.com/demo/events/x.svg"
    ) == "/demo/events/x.svg"


def test_normalize_leaves_relative_and_r2(frontend_padeya) -> None:
    assert assets.normalize_demo_asset_url("/demo/events/afrobeats-night-live.svg") == (
        "/demo/events/afrobeats-night-live.svg"
    )
    r2 = "https://media.padeya.com/memories/events/abc/photo.webp"
    assert assets.normalize_demo_asset_url(r2) == r2
    assert assets.rewrite_legacy_smartlance_demo_url(r2) == r2


def test_normalize_leaves_external_urls(frontend_padeya) -> None:
    external = "https://cdn.example.com/poster.jpg"
    assert assets.normalize_demo_asset_url(external) == external
    assert assets.rewrite_legacy_smartlance_demo_url(external) == external


def test_normalize_collapses_absolute_padeya_demo_to_relative(frontend_padeya) -> None:
    assert assets.normalize_demo_asset_url(
        "https://padeya.com/demo/hosts/djmaze-avatar.svg"
    ) == "/demo/hosts/djmaze-avatar.svg"


def test_detty_friday_memory_svg_exists_in_frontend_public() -> None:
    root = Path(__file__).resolve().parents[2] / "frontend" / "public"
    asset = root / "demo" / "memories" / "detty-friday-memory.svg"
    assert asset.is_file(), f"Missing static asset: {asset}"


def test_seed_helpers_never_emit_smartlance_hostname(frontend_padeya) -> None:
    samples = [
        assets.memory_image("detty-friday-memory"),
        assets.event_banner("detty-friday-live"),
        assets.event_gallery("afrobeats-night-live"),
        assets.host_avatar("djmaze"),
        assets.host_cover("djmaze"),
        assets.fan_avatar("toluwave"),
        assets.merch_image("tee"),
        assets.sponsor_logo("acme-events"),
        assets.vault_cover("vip-gallery"),
    ]
    for url in samples:
        assert url.startswith("/demo/"), url
        assert "smartlancedesigns.com" not in url
        assert "media.padeya.com" not in url


def test_backfill_only_rewrites_smartlance_demo_urls(
    db_session: Session, frontend_padeya
) -> None:
    from datetime import UTC, datetime, timedelta
    from uuid import uuid4

    from app.core.security import hash_password
    from app.hosts.models import Host, HostProfile
    from app.users.models import User
    from app.users.service import get_role_by_name

    user = User(
        email=f"legacy-demo-{uuid4().hex[:8]}@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Legacy Demo",
        is_active=True,
    )
    user.roles.append(get_role_by_name(db_session, "host"))
    db_session.add(user)
    db_session.flush()
    host = Host(
        user_id=user.id,
        display_name="Legacy Host",
        slug=f"legacy-{uuid4().hex[:6]}",
        status="active",
    )
    db_session.add(host)
    db_session.flush()
    db_session.add(HostProfile(host_id=host.id, bio="x"))
    start = datetime.now(UTC) - timedelta(days=2)
    event = Event(
        title="Legacy Demo Event",
        slug=f"legacy-demo-{uuid4().hex[:6]}",
        description="Legacy URL backfill fixture",
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=3),
        venue_name="Hall",
        city="Lagos",
        status="completed",
        banner_url=(
            "https://padeya.smartlancedesigns.com/demo/memories/detty-friday-memory.svg"
        ),
        social_share_image_url="https://media.padeya.com/memories/events/x.webp",
    )
    db_session.add(event)
    db_session.flush()

    from app.memories.service import ensure_event_memory

    memory = ensure_event_memory(db_session, event)
    media = EventMemoryMedia(
        memory_id=memory.id,
        media_type="image",
        url="https://padeya.smartlancedesigns.com/demo/events/afrobeats-night-live.svg",
        thumbnail_url="https://cdn.example.com/keep-me.jpg",
        storage_key="demo-mem:test:01",
        uploader_role="host",
        status="active",
    )
    db_session.add(media)
    db_session.commit()

    # Dry-run does not persist.
    dry = backfill_legacy_smartlance_demo_urls(db_session, dry_run=True)
    assert dry.updated >= 2
    db_session.refresh(event)
    assert event.banner_url.startswith("https://padeya.smartlancedesigns.com/")

    applied = backfill_legacy_smartlance_demo_urls(db_session, dry_run=False)
    assert applied.updated >= 2
    db_session.refresh(event)
    db_session.refresh(media)
    assert event.banner_url == "/demo/memories/detty-friday-memory.svg"
    assert event.social_share_image_url == (
        "https://media.padeya.com/memories/events/x.webp"
    )
    assert media.url == "/demo/events/afrobeats-night-live.svg"
    assert media.thumbnail_url == "https://cdn.example.com/keep-me.jpg"

    # Idempotent second run.
    again = backfill_legacy_smartlance_demo_urls(db_session, dry_run=False)
    assert again.updated == 0
