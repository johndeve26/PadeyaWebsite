"""Fan Passport merch purchase badges — award after paid, privacy, refunds."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.events.models import Event, EventCategory
from app.hosts.models import Host, HostProfile
from app.messaging.models import InAppNotification
from app.merch.fulfillment import cancel_fulfillments_for_refunded_order
from app.merch.models import EventMerchProduct, EventMerchVariant, MerchFulfillment
from app.passport.badges import evaluate_badge_criteria
from app.passport.constants import MERCH_BADGE_CRITERIA
from app.passport.merch_proof import (
    fan_merch_proof_summaries,
    host_merch_proof_summaries,
)
from app.passport.models import FanBadge, UserBadge
from app.passport.seed import seed_fan_badges
from app.payments.models import Order, OrderItem
from app.users.models import User
from app.users.service import get_role_by_name
from tests.test_merch import (
    _create_active_product,
    _login,
    _pay_order,
    _register_buyer,
    _seed_host_event,
)


def _order_merch(
    client: TestClient,
    buyer_headers: dict[str, str],
    *,
    event_id: UUID,
    variant_id: str,
) -> dict:
    res = client.post(
        "/api/v1/orders",
        headers=buyer_headers,
        json={
            "event_id": str(event_id),
            "items": [
                {
                    "item_kind": "merch",
                    "merch_variant_id": variant_id,
                    "quantity": 1,
                }
            ],
        },
    )
    assert res.status_code in {200, 201}, res.text
    return res.json()


def test_merch_badge_catalog_seeded(db_session: Session):
    seed_fan_badges(db_session)
    keys = {
        b.criteria_key
        for b in db_session.scalars(select(FanBadge).where(FanBadge.is_active.is_(True)))
    }
    assert MERCH_BADGE_CRITERIA.issubset(keys)
    assert "culture_fest_collector" in keys
    assert "founder_mode_gear" in keys


def test_first_merch_buy_awarded_after_paid_not_before(
    client: TestClient, db_session: Session
):
    _, _, event, _ = _seed_host_event(db_session)
    event.allow_merch_only_checkout = True
    db_session.commit()
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id)
    variant_id = product["variants"][0]["id"]
    buyer_headers = _register_buyer(client, "merch-badge-before@example.com")
    buyer = db_session.query(User).filter_by(email="merch-badge-before@example.com").one()

    order = _order_merch(
        client, buyer_headers, event_id=event.id, variant_id=variant_id
    )
    assert (
        db_session.scalar(
            select(MerchFulfillment.id).where(MerchFulfillment.order_id == UUID(order["id"]))
        )
        is None
    )
    badges_before = client.get("/api/v1/passport/me/badges", headers=buyer_headers).json()
    by_slug = {b["slug"]: b for b in badges_before}
    assert by_slug["first-merch-buy"]["earned"] is False

    _pay_order(client, buyer_headers, order)
    db_session.expire_all()

    ub = db_session.scalar(
        select(UserBadge)
        .join(FanBadge, FanBadge.id == UserBadge.badge_id)
        .where(
            UserBadge.user_id == buyer.id,
            FanBadge.criteria_key == "first_merch_buy",
        )
    )
    assert ub is not None
    assert ub.meta is not None
    meta_s = json.dumps(ub.meta)
    assert "amount" not in meta_s.lower()
    assert "price" not in meta_s.lower()
    assert "7500" not in meta_s
    assert str(order["id"]) not in meta_s
    assert ub.meta.get("source") == "merch"
    assert ub.meta.get("criteria_key") == "first_merch_buy"

    note = db_session.scalar(
        select(InAppNotification).where(
            InAppNotification.user_id == buyer.id,
            InAppNotification.kind == "merch.badge_earned",
        )
    )
    assert note is not None
    assert "Pàdéyá" in note.title
    assert "7500" not in (note.body or "")
    assert order["reference"] not in (note.body or "")


def test_public_passport_hides_merch_badges_when_prefs_off(
    client: TestClient, db_session: Session
):
    _, host, event, _ = _seed_host_event(db_session)
    event.allow_merch_only_checkout = True
    db_session.commit()
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id)
    variant_id = product["variants"][0]["id"]
    buyer_headers = _register_buyer(client, "merch-badge-public@example.com")
    buyer = db_session.query(User).filter_by(email="merch-badge-public@example.com").one()

    order = _order_merch(
        client, buyer_headers, event_id=event.id, variant_id=variant_id
    )
    _pay_order(client, buyer_headers, order)

    client.patch(
        "/api/v1/passport/me/settings",
        headers=buyer_headers,
        json={
            "visibility": "public",
            "username": "merchbadgepub",
            "show_badges": True,
        },
    )
    page = client.get("/api/v1/f/merchbadgepub")
    assert page.status_code == 200
    body = page.json()
    assert body["badges_earned_count"] >= 1
    assert any(b["slug"] == "first-merch-buy" for b in body["badges"])

    client.patch(
        "/api/v1/passport/me/settings",
        headers=buyer_headers,
        json={"show_badges": False},
    )
    hidden = client.get("/api/v1/f/merchbadgepub").json()
    assert hidden["badges"] == []
    assert hidden["badges_earned_count"] == 0
    assert hidden.get("merch_proof_summaries") == []

    mine = client.get("/api/v1/passport/me/badges", headers=buyer_headers).json()
    assert next(b for b in mine if b["slug"] == "first-merch-buy")["earned"] is True

    summaries = fan_merch_proof_summaries(db_session, buyer.id)
    blob = " ".join(summaries)
    assert "7500" not in blob
    assert "NGN" not in blob
    host_lines = host_merch_proof_summaries(db_session, host.id)
    assert any("merch item" in line for line in host_lines)
    assert any("fan" in line and "merch" in line for line in host_lines)


def test_refund_revokes_first_merch_buy(client: TestClient, db_session: Session):
    _, _, event, _ = _seed_host_event(db_session)
    event.allow_merch_only_checkout = True
    db_session.commit()
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id)
    variant_id = product["variants"][0]["id"]
    buyer_headers = _register_buyer(client, "merch-badge-refund@example.com")
    buyer = db_session.query(User).filter_by(email="merch-badge-refund@example.com").one()

    order = _order_merch(
        client, buyer_headers, event_id=event.id, variant_id=variant_id
    )
    _pay_order(client, buyer_headers, order)
    db_session.expire_all()

    assert (
        db_session.scalar(
            select(UserBadge.id)
            .join(FanBadge, FanBadge.id == UserBadge.badge_id)
            .where(
                UserBadge.user_id == buyer.id,
                FanBadge.criteria_key == "first_merch_buy",
            )
        )
        is not None
    )

    order_row = db_session.get(Order, UUID(order["id"]))
    assert order_row is not None
    cancel_fulfillments_for_refunded_order(db_session, order=order_row)
    db_session.commit()

    assert (
        db_session.scalar(
            select(UserBadge.id)
            .join(FanBadge, FanBadge.id == UserBadge.badge_id)
            .where(
                UserBadge.user_id == buyer.id,
                FanBadge.criteria_key == "first_merch_buy",
            )
        )
        is None
    )


def test_culture_fest_and_founder_mode_criteria(
    client: TestClient, db_session: Session
):
    art = db_session.query(EventCategory).filter_by(slug="arts-culture").first()
    if art is None:
        art = EventCategory(
            name="Arts & Culture", slug="arts-culture", description="Culture"
        )
        db_session.add(art)
        db_session.flush()
    tech = db_session.query(EventCategory).filter_by(slug="tech").first()
    if tech is None:
        tech = EventCategory(name="Tech", slug="tech", description="Tech")
        db_session.add(tech)
        db_session.flush()

    host_user = User(
        email="culture-badge-host@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Culture Host",
        is_active=True,
    )
    host_user.roles.append(get_role_by_name(db_session, "host"))
    db_session.add(host_user)
    db_session.flush()
    host = Host(
        user_id=host_user.id,
        display_name="Culture Host",
        slug="techconnectafrica",
        status="active",
    )
    db_session.add(host)
    db_session.flush()
    db_session.add(HostProfile(host_id=host.id, bio="Host"))

    buyer_headers = _register_buyer(client, "culture-founder-buyer@example.com")
    buyer = db_session.query(User).filter_by(email="culture-founder-buyer@example.com").one()

    start = datetime.now(UTC) + timedelta(days=5)
    culture_event = Event(
        title="Lagos Culture Fest",
        slug="lagos-culture-fest",
        description="Culture fest merch badge test event with enough detail.",
        category_id=art.id,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=4),
        city="Lagos",
        status="published",
        published_at=datetime.now(UTC),
    )
    founders_event = Event(
        title="Founders Mixer Lagos",
        slug="founders-mixer-lagos",
        description="Founders mixer merch badge test event with enough detail.",
        category_id=tech.id,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=3),
        city="Lagos",
        status="published",
        published_at=datetime.now(UTC),
    )
    db_session.add_all([culture_event, founders_event])
    db_session.flush()

    def _variant(event: Event, name: str) -> EventMerchVariant:
        p = EventMerchProduct(
            event_id=event.id,
            host_id=host.id,
            name=name,
            slug=name.lower().replace(" ", "-")[:40],
            base_price=Decimal("5000.00"),
            currency="NGN",
            status="active",
            product_type="t_shirt",
        )
        db_session.add(p)
        db_session.flush()
        v = EventMerchVariant(
            product_id=p.id,
            label="M",
            inventory_count=10,
            sold_quantity=0,
            reserved_quantity=0,
            status="active",
        )
        db_session.add(v)
        db_session.flush()
        return v

    culture_v = _variant(culture_event, "Fest Tee")
    founder_v = _variant(founders_event, "Founder Mode Tote")

    flags = evaluate_badge_criteria(db_session, buyer.id)
    assert flags["culture_fest_collector"] is False
    assert flags["founder_mode_gear"] is False

    order = Order(
        buyer_user_id=buyer.id,
        event_id=culture_event.id,
        status="paid",
        currency="NGN",
        subtotal_amount=Decimal("10000.00"),
        total_amount=Decimal("10000.00"),
        reference=f"ref-culture-{buyer.id.hex[:8]}",
        buyer_email=buyer.email,
        buyer_name=buyer.full_name,
    )
    db_session.add(order)
    db_session.flush()

    for idx, (event, variant, name) in enumerate(
        (
            (culture_event, culture_v, "Fest Tee"),
            (founders_event, founder_v, "Founder Mode Tote"),
        )
    ):
        item = OrderItem(
            order_id=order.id,
            item_kind="merch",
            merch_variant_id=variant.id,
            merch_product_id=variant.product_id,
            quantity=1,
            unit_price=Decimal("5000.00"),
            line_total=Decimal("5000.00"),
            product_name=name,
            variant_label="M",
        )
        db_session.add(item)
        db_session.flush()
        db_session.add(
            MerchFulfillment(
                order_id=order.id,
                order_item_id=item.id,
                event_id=event.id,
                host_id=host.id,
                buyer_user_id=buyer.id,
                merch_variant_id=variant.id,
                quantity=1,
                status="awaiting_pickup",
                pickup_code=f"MRCH-TEST{idx}{buyer.id.hex[:4].upper()}",
                product_name_snapshot=name,
                variant_label_snapshot="M",
            )
        )
    db_session.commit()

    flags = evaluate_badge_criteria(db_session, buyer.id)
    assert flags["culture_fest_collector"] is True
    assert flags["founder_mode_gear"] is True
    assert flags["first_merch_buy"] is True
    assert buyer_headers is not None
