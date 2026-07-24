"""Focused checks that demo merch seed creates key commerce artifacts (no PII/secrets)."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.demo.constants import DEMO_EMAIL_DOMAIN
from app.demo.seed import seed_demo_data
from app.merch.models import (
    EventMerchProduct,
    MerchBundle,
    MerchCart,
    MerchDiscountCode,
    MerchReview,
)


@pytest.fixture()
def demo_settings(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("FRONTEND_URL", "http://localhost:3000")
    get_settings.cache_clear()
    yield get_settings()
    get_settings.cache_clear()


def test_demo_merch_seed_key_commerce_artifacts(demo_settings, db_session) -> None:
    result = seed_demo_data(db_session, reset=True)
    assert result["status"] == "seeded"

    laugh10 = db_session.scalar(
        select(MerchDiscountCode).where(MerchDiscountCode.code == "LAUGH10")
    )
    assert laugh10 is not None
    assert laugh10.status == "active"

    bundle = db_session.scalar(
        select(MerchBundle).where(
            MerchBundle.name == "Ticket + T-shirt Bundle",
            MerchBundle.archived_at.is_(None),
        )
    )
    assert bundle is not None
    assert bundle.status == "active"

    comedy_bundle = db_session.scalar(
        select(MerchBundle).where(
            MerchBundle.name == "Ticket + Comedy Cap Bundle",
            MerchBundle.archived_at.is_(None),
        )
    )
    assert comedy_bundle is not None

    abandoned = db_session.scalar(
        select(MerchCart).where(
            MerchCart.status == "abandoned",
            MerchCart.buyer_user_id.is_not(None),
            MerchCart.recovery_sent_at.is_(None),
        )
    )
    assert abandoned is not None

    vault_hoodie = db_session.scalar(
        select(EventMerchProduct).where(
            EventMerchProduct.name == "Backstage Hoodie",
            EventMerchProduct.is_vault_exclusive.is_(True),
            EventMerchProduct.archived_at.is_(None),
        )
    )
    assert vault_hoodie is not None
    assert vault_hoodie.storefront_visibility == "vault_exclusive"

    post_drop = db_session.scalar(
        select(EventMerchProduct).where(
            EventMerchProduct.name == "Afrobeats Recap Poster",
            EventMerchProduct.storefront_visibility == "post_event_drop",
            EventMerchProduct.archived_at.is_(None),
        )
    )
    assert post_drop is not None
    assert post_drop.post_event_drop_at is not None

    sade_review = db_session.scalar(
        select(MerchReview).where(
            MerchReview.status == "published",
            MerchReview.rating >= 1,
        )
    )
    assert sade_review is not None
    # Public review body must not leak private shipping / payment fields.
    body = (sade_review.body or "").lower()
    assert "phone" not in body
    assert "paystack" not in body
    assert DEMO_EMAIL_DOMAIN not in body
