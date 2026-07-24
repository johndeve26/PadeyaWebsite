"""Temporary debug — host shops after demo seed."""

from __future__ import annotations

import pytest

from app.demo.seed import seed_demo_data
from app.merch.marketplace import list_marketplace_host_shops


@pytest.fixture()
def demo_settings(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("FRONTEND_URL", "http://localhost:3000")
    from app.core.config import get_settings

    get_settings.cache_clear()
    yield get_settings()
    get_settings.cache_clear()


def test_debug_host_shops_after_demo_seed(demo_settings, db_session, client) -> None:
    from sqlalchemy import select

    from app.hosts.models import HostProfile

    seed_demo_data(db_session, reset=True)
    shops = list_marketplace_host_shops(db_session, limit=24)
    print("HOST_SHOPS_COUNT", len(shops))
    for s in shops:
        print("SHOP", s.get("host_slug"), s.get("merch_count"))
    res = client.get("/api/v1/merch/home")
    assert res.status_code == 200
    body = res.json()
    print("API_HOST_SHOPS", len(body.get("host_shops") or []))
    assert len(body.get("host_shops") or []) >= 1, body.get("host_shops")

    for profile in db_session.scalars(select(HostProfile)).all():
        profile.merch_storefront_enabled = False
    db_session.commit()
    disabled = list_marketplace_host_shops(db_session, limit=24)
    print("HOST_SHOPS_STOREFRONT_DISABLED", len(disabled))
    assert len(disabled) >= 1, "Host shops must not depend on merch_storefront_enabled"
