"""Marketplace merch demo seed coverage (standalone, drops, Vault, guards)."""

from __future__ import annotations

import os

import pytest
from sqlalchemy import func, select

from app.core.config import get_settings
from app.demo.constants import DEMO_EMAIL_DOMAIN
from app.demo.guards import DemoEnvironmentError, assert_demo_ops_allowed
from app.demo.seed import seed_demo_data
from app.hosts.models import Host
from app.merch.models import EventMerchProduct, MerchBundle, MerchFulfillment


@pytest.fixture()
def demo_settings(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("FRONTEND_URL", "http://localhost:3000")
    monkeypatch.delenv("NODE_ENV", raising=False)
    monkeypatch.delenv("DEMO_SEED_ENABLED", raising=False)
    get_settings.cache_clear()
    yield get_settings()
    get_settings.cache_clear()


def test_demo_ops_blocked_in_app_env_production(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(DemoEnvironmentError, match="APP_ENV=production"):
        assert_demo_ops_allowed(operation="demo merch seed")


def test_demo_ops_blocked_when_node_env_production_without_flag(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("NODE_ENV", "production")
    monkeypatch.delenv("DEMO_SEED_ENABLED", raising=False)
    get_settings.cache_clear()
    with pytest.raises(DemoEnvironmentError):
        assert_demo_ops_allowed(operation="demo merch seed")
    get_settings.cache_clear()


def test_demo_ops_allowed_with_demo_seed_enabled_under_node_production(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("NODE_ENV", "production")
    monkeypatch.setenv("DEMO_SEED_ENABLED", "true")
    get_settings.cache_clear()
    assert_demo_ops_allowed(operation="demo merch seed")  # must not raise
    get_settings.cache_clear()


def test_marketplace_merch_seed_coverage(demo_settings, db_session, client) -> None:
    result = seed_demo_data(db_session, reset=True)
    assert result["status"] == "seeded"

    total = db_session.scalar(
        select(func.count())
        .select_from(EventMerchProduct)
        .where(EventMerchProduct.archived_at.is_(None))
    )
    assert total is not None and total >= 30

    standalone = db_session.scalars(
        select(EventMerchProduct).where(
            EventMerchProduct.event_id.is_(None),
            EventMerchProduct.archived_at.is_(None),
            EventMerchProduct.marketplace_kind == "standalone",
        )
    ).all()
    assert len(standalone) >= 5
    assert any(p.name == "Mainland Vibes Logo Tee" for p in standalone)
    assert all(p.image_url for p in standalone)

    # At least 5 hosts with storefront standalone/shop products
    host_ids = {p.host_id for p in standalone}
    assert len(host_ids) >= 5

    drops = db_session.scalars(
        select(EventMerchProduct).where(
            EventMerchProduct.storefront_visibility == "post_event_drop",
            EventMerchProduct.archived_at.is_(None),
        )
    ).all()
    assert len(drops) >= 4
    assert any(p.name == "Checked-in Only Event Tee" for p in drops)

    vault = db_session.scalars(
        select(EventMerchProduct).where(
            EventMerchProduct.is_vault_exclusive.is_(True),
            EventMerchProduct.archived_at.is_(None),
        )
    ).all()
    assert len(vault) >= 3
    assert any("Vault" in (p.name or "") or p.is_vault_exclusive for p in vault)

    addons = db_session.scalars(
        select(EventMerchProduct).where(
            EventMerchProduct.marketplace_kind == "event_addon",
            EventMerchProduct.archived_at.is_(None),
        )
    ).all()
    assert len(addons) >= 3

    sold_out = db_session.scalar(
        select(EventMerchProduct).where(
            EventMerchProduct.name == "Sold Out Island Tee",
            EventMerchProduct.archived_at.is_(None),
        )
    )
    assert sold_out is not None

    bundles = db_session.scalars(
        select(MerchBundle).where(MerchBundle.archived_at.is_(None))
    ).all()
    assert len(bundles) >= 4

    fulfillments = db_session.scalar(select(func.count()).select_from(MerchFulfillment))
    assert fulfillments is not None and fulfillments >= 5

    # Idempotent re-seed does not duplicate standalone products
    before = total
    seed_demo_data(db_session, reset=False)
    after = db_session.scalar(
        select(func.count())
        .select_from(EventMerchProduct)
        .where(EventMerchProduct.archived_at.is_(None))
    )
    assert after == before

    # Host shops enabled
    mainland = db_session.scalar(select(Host).where(Host.slug == "mainlandvibes"))
    assert mainland is not None

    home = client.get("/api/v1/merch/home")
    assert home.status_code == 200
    body = home.json()
    host_shops = body.get("host_shops") or []
    assert len(host_shops) >= 5, host_shops
    assert len(body.get("drops") or []) >= 4
    assert len(body.get("vault_exclusives") or []) >= 4
