"""Public pricing API tests — no host overrides or admin notes leaked."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.finance.fees.constants import (
    FEE_KEY_BUYER_SERVICE,
    FEE_KEY_TICKET_COMMISSION,
)
from app.finance.fees.models import HostFeeOverride, PlatformFeeSetting
from app.hosts.models import Host, HostProfile
from app.core.security import hash_password
from app.users.models import User
from app.users.service import get_role_by_name


def test_public_pricing_returns_structure_without_settings(
    client: TestClient,
) -> None:
    res = client.get("/api/v1/pricing/public")
    assert res.status_code == 200
    data = res.json()
    assert "note" in data
    assert "categories" in data
    assert "fees" in data
    assert len(data["categories"]) >= 7
    labels = {c["label"] for c in data["categories"]}
    assert "Ticket sales" in labels
    assert "Buyer platform / service fee" in labels
    assert "High-volume / custom host agreements" in labels
    # No invented rates when settings missing
    for fee in data["fees"]:
        assert fee["percentage_value"] is None
        assert fee["fixed_value_major"] is None
        assert "notes" not in fee
        assert "reason" not in fee


def test_public_pricing_publishes_buyer_rates_hides_host_rates(
    client: TestClient,
    db_session: Session,
) -> None:
    now = datetime.now(UTC)
    db_session.add(
        PlatformFeeSetting(
            fee_key=FEE_KEY_TICKET_COMMISSION,
            label="Ticket commission",
            category="ticket",
            fee_type="percentage",
            percentage_value=Decimal("5.0000"),
            fixed_value=None,
            currency="NGN",
            payer="host",
            enabled=True,
            applies_to="all",
            notes="INTERNAL DO NOT LEAK",
            effective_from=now - timedelta(days=1),
            effective_to=None,
        )
    )
    db_session.add(
        PlatformFeeSetting(
            fee_key=FEE_KEY_BUYER_SERVICE,
            label="Buyer platform / service fee",
            category="general",
            fee_type="percentage",
            percentage_value=Decimal("2.5000"),
            fixed_value=None,
            currency="NGN",
            payer="buyer",
            enabled=True,
            applies_to="all",
            notes="secret buyer note",
            effective_from=now - timedelta(days=1),
            effective_to=None,
        )
    )
    db_session.commit()

    res = client.get("/api/v1/pricing/public")
    assert res.status_code == 200
    data = res.json()
    body = res.text
    assert "INTERNAL DO NOT LEAK" not in body
    assert "secret buyer note" not in body

    by_key = {f["fee_key"]: f for f in data["fees"]}
    host_fee = by_key[FEE_KEY_TICKET_COMMISSION]
    assert host_fee["rates_public"] is False
    assert host_fee["percentage_value"] is None
    assert host_fee["display_rate"] == "May vary"
    assert host_fee["may_vary_by_host"] is True

    buyer_fee = by_key[FEE_KEY_BUYER_SERVICE]
    assert buyer_fee["rates_public"] is True
    assert Decimal(str(buyer_fee["percentage_value"])) == Decimal("2.5000")
    assert "2.5" in (buyer_fee["display_rate"] or "")


def test_public_pricing_never_exposes_host_overrides(
    client: TestClient,
    db_session: Session,
) -> None:
    now = datetime.now(UTC)
    host_user = User(
        email="pricing-host@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Pricing Host",
        is_active=True,
    )
    role = get_role_by_name(db_session, "host")
    assert role is not None
    host_user.roles.append(role)
    db_session.add(host_user)
    db_session.flush()
    host = Host(
        user_id=host_user.id,
        display_name="Pricing Host",
        slug="pricing-host",
        status="active",
    )
    db_session.add(host)
    db_session.flush()
    db_session.add(HostProfile(host_id=host.id, bio="x"))
    db_session.add(
        PlatformFeeSetting(
            fee_key=FEE_KEY_TICKET_COMMISSION,
            label="Ticket commission",
            category="ticket",
            fee_type="percentage",
            percentage_value=Decimal("5.0000"),
            currency="NGN",
            payer="host",
            enabled=True,
            applies_to="all",
            effective_from=now - timedelta(days=1),
        )
    )
    db_session.flush()
    db_session.add(
        HostFeeOverride(
            host_id=host.id,
            fee_key=FEE_KEY_TICKET_COMMISSION,
            percentage_value=Decimal("3.0000"),
            fixed_value=None,
            payer="host",
            enabled=True,
            effective_from=now - timedelta(days=1),
            reason="VIP festival deal — SECRET",
        )
    )
    db_session.commit()

    res = client.get("/api/v1/pricing/public")
    assert res.status_code == 200
    body = res.text
    assert "VIP festival deal" not in body
    assert "SECRET" not in body
    assert "3.0000" not in body
    assert str(host.id) not in body
