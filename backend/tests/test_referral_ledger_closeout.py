"""Item-level attribution, append-only ledger, settlement separation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.events.models import Event, EventCategory, TicketType
from app.finance.earnings_service import _ambassador_by_order
from app.hosts.models import Host, HostProfile
from app.payments.models import Order, OrderItem
from app.promos.attribution import resolve_winning_attributions_for_order
from app.promos.commission import reverse_ambassador_sale_for_order
from app.promos.constants import PAYER_HOST, PAYER_PLATFORM
from app.promos.ledger_service import (
    remaining_reversible_amount,
    reverse_commission_for_order_item,
)
from app.promos.models import AmbassadorSale
from app.promos.referral_ledger import ReferralAttribution, ReferralCommissionEntry
from app.promos.reporting import get_admin_referral_summary, get_ambassador_referral_summary
from app.promos.service import finalize_promo_and_attribution
from app.users.models import User
from app.users.service import get_role_by_name


def _login(client: TestClient, email: str) -> dict[str, str]:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _admin(client: TestClient, assign_role, email: str) -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "securepass1",
            "full_name": "Ledger Admin",
            "gender": "prefer_not_to_say",
        },
    )
    assign_role(email, "super_admin")
    return _login(client, email)


def _seed(db: Session, *, tag: str):
    host_email = f"led-host-{tag}@example.com"
    host_user = User(
        email=host_email,
        password_hash=hash_password("securepass1"),
        full_name="Ledger Host",
        is_active=True,
    )
    role = get_role_by_name(db, "host")
    assert role is not None
    host_user.roles.append(role)
    fan = User(
        email=f"led-fan-{tag}@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Ledger Fan",
        is_active=True,
    )
    buyer = User(
        email=f"led-buyer-{tag}@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Ledger Buyer",
        is_active=True,
    )
    db.add_all([host_user, fan, buyer])
    db.flush()
    host = Host(
        user_id=host_user.id,
        display_name="Ledger Host",
        slug=f"led-host-{tag}",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, city="Lagos"))
    category = db.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=4)
    event = Event(
        title="Ledger Night",
        slug=f"led-night-{tag}",
        description="Ledger tests",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=3),
        city="Lagos",
        status="published",
        featured=False,
        published_at=datetime.now(UTC),
    )
    db.add(event)
    db.flush()
    tt1 = TicketType(
        event_id=event.id,
        name="GA",
        type="regular",
        price=Decimal("10000.00"),
        quantity=50,
        quantity_sold=0,
        quantity_reserved=0,
        min_per_order=1,
        max_per_order=5,
        visibility="public",
        status="active",
    )
    tt2 = TicketType(
        event_id=event.id,
        name="VIP",
        type="vip",
        price=Decimal("20000.00"),
        quantity=20,
        quantity_sold=0,
        quantity_reserved=0,
        min_per_order=1,
        max_per_order=2,
        visibility="public",
        status="active",
    )
    db.add_all([tt1, tt2])
    db.commit()
    return host, event, fan, buyer, host_email, tt1, tt2


def _order_with_items(db: Session, *, event: Event, buyer: User, lines: list[dict]) -> Order:
    subtotal = sum((line["unit"] * line["qty"] for line in lines), Decimal("0"))
    order = Order(
        event_id=event.id,
        host_id=event.host_id,
        buyer_user_id=buyer.id,
        buyer_email=buyer.email,
        buyer_name=buyer.full_name or "Buyer",
        status="paid",
        currency="NGN",
        subtotal_amount=subtotal,
        discount_amount=Decimal("0"),
        total_amount=subtotal,
        reference=f"led-{uuid4().hex[:12]}",
    )
    db.add(order)
    db.flush()
    for line in lines:
        db.add(
            OrderItem(
                order_id=order.id,
                item_kind=line["kind"],
                ticket_type_id=line.get("ticket_type_id"),
                merch_product_id=line.get("merch_product_id"),
                ticket_type_name=line.get("name"),
                product_name=line.get("name"),
                quantity=line["qty"],
                unit_price=line["unit"],
                line_total=line["unit"] * line["qty"],
            )
        )
    db.commit()
    order = db.get(Order, order.id)
    assert order is not None
    _ = list(order.items)
    return order


def test_multi_ticket_line_item_attribution_and_ledger(
    client: TestClient, db_session: Session, assign_role
):
    tag = uuid4().hex[:8]
    host, event, fan, buyer, host_email, tt1, tt2 = _seed(db_session, tag=tag)
    admin = _admin(client, assign_role, f"led-admin-{tag}@example.com")
    host_h = _login(client, host_email)

    prog = client.post(
        "/api/v1/promos/admin/referral-programs",
        headers=admin,
        json={
            "name": "Ledger Platform",
            "ticket_rule": {"commission_mode": "percentage", "commission_value": 10},
            "merchandise_rule": {
                "commission_mode": "percentage",
                "commission_value": 5,
            },
        },
    ).json()
    plat = client.post(
        f"/api/v1/promos/admin/referral-programs/{prog['id']}/enrollments",
        headers=admin,
        json={"email": fan.email, "referral_code": f"plat{tag}"},
    ).json()

    camp = client.post(
        "/api/v1/promos/campaigns",
        headers=host_h,
        json={
            "event_id": str(event.id),
            "name": "Host GA",
            "campaign_type": "event_tickets",
            "commission_type": "percentage",
            "commission_value": 5,
            "commission_percent": 5,
            "status": "public_open",
        },
    )
    assert camp.status_code in {200, 201}, camp.text
    amb = client.post(
        "/api/v1/promos/ambassadors",
        headers=host_h,
        json={
            "event_id": str(event.id),
            "campaign_id": camp.json()["id"],
            "display_name": "Host Amb",
            "email": fan.email,
            "referral_code": f"host{tag}",
            "commission_rate_percent": 5,
        },
    )
    assert amb.status_code == 201, amb.text
    host_code = amb.json()["referral_code"]

    order = _order_with_items(
        db_session,
        event=event,
        buyer=buyer,
        lines=[
            {
                "kind": "ticket",
                "ticket_type_id": tt1.id,
                "name": "GA",
                "qty": 1,
                "unit": Decimal("10000"),
            },
            {
                "kind": "ticket",
                "ticket_type_id": tt2.id,
                "name": "VIP",
                "qty": 1,
                "unit": Decimal("20000"),
            },
        ],
    )
    # Host code wins for both ticket lines (same event campaign)
    order.referral_code = host_code
    order.platform_referral_code = plat["referral_code"]
    db_session.commit()

    winners = resolve_winning_attributions_for_order(db_session, order=order)
    assert len(winners) == 2
    assert all(w.payer_type == PAYER_HOST for w in winners)
    assert len({w.attribution_item_key for w in winners}) == 2

    finalize_promo_and_attribution(db_session, order=order)
    db_session.commit()

    attrs = list(
        db_session.scalars(
            select(ReferralAttribution).where(ReferralAttribution.order_id == order.id)
        )
    )
    assert len(attrs) == 2
    earnings = list(
        db_session.scalars(
            select(ReferralCommissionEntry).where(
                ReferralCommissionEntry.order_id == order.id,
                ReferralCommissionEntry.entry_type == "earning",
            )
        )
    )
    assert len(earnings) == 2
    total = sum((Decimal(e.commission_amount) for e in earnings), Decimal("0"))
    assert total == Decimal("1500.00")  # 5% of 10k + 5% of 20k

    # Duplicate finalize is idempotent
    finalize_promo_and_attribution(db_session, order=order)
    db_session.commit()
    assert (
        db_session.scalar(
            select(ReferralCommissionEntry).where(
                ReferralCommissionEntry.order_id == order.id,
                ReferralCommissionEntry.entry_type == "earning",
            )
        )
        is not None
    )
    assert (
        db_session.query(ReferralCommissionEntry)
        .filter(
            ReferralCommissionEntry.order_id == order.id,
            ReferralCommissionEntry.entry_type == "earning",
        )
        .count()
        == 2
    )


def test_platform_item_ledger_and_no_host_deduction(
    client: TestClient, db_session: Session, assign_role
):
    tag = uuid4().hex[:8]
    host, event, fan, buyer, _he, tt1, _tt2 = _seed(db_session, tag=tag)
    admin = _admin(client, assign_role, f"led-admin2-{tag}@example.com")
    prog = client.post(
        "/api/v1/promos/admin/referral-programs",
        headers=admin,
        json={
            "name": "Plat only",
            "ticket_rule": {"commission_mode": "percentage", "commission_value": 10},
        },
    ).json()
    plat = client.post(
        f"/api/v1/promos/admin/referral-programs/{prog['id']}/enrollments",
        headers=admin,
        json={"email": fan.email},
    ).json()
    order = _order_with_items(
        db_session,
        event=event,
        buyer=buyer,
        lines=[
            {
                "kind": "ticket",
                "ticket_type_id": tt1.id,
                "name": "GA",
                "qty": 1,
                "unit": Decimal("10000"),
            }
        ],
    )
    order.referral_code = plat["referral_code"]
    db_session.commit()
    finalize_promo_and_attribution(db_session, order=order)
    db_session.commit()

    earning = db_session.scalar(
        select(ReferralCommissionEntry).where(
            ReferralCommissionEntry.order_id == order.id,
            ReferralCommissionEntry.entry_type == "earning",
        )
    )
    assert earning is not None
    assert earning.payer_type == PAYER_PLATFORM
    assert earning.commission_amount == Decimal("1000.00")
    assert _ambassador_by_order(db_session, [order.id]).get(order.id, Decimal("0")) == Decimal(
        "0"
    )


def test_partial_and_full_reversal_append_only(
    client: TestClient, db_session: Session, assign_role
):
    tag = uuid4().hex[:8]
    _host, event, fan, buyer, _he, tt1, _tt2 = _seed(db_session, tag=tag)
    admin = _admin(client, assign_role, f"led-admin3-{tag}@example.com")
    prog = client.post(
        "/api/v1/promos/admin/referral-programs",
        headers=admin,
        json={
            "name": "Refund ledger",
            "ticket_rule": {"commission_mode": "percentage", "commission_value": 10},
        },
    ).json()
    plat = client.post(
        f"/api/v1/promos/admin/referral-programs/{prog['id']}/enrollments",
        headers=admin,
        json={"email": fan.email},
    ).json()
    order = _order_with_items(
        db_session,
        event=event,
        buyer=buyer,
        lines=[
            {
                "kind": "ticket",
                "ticket_type_id": tt1.id,
                "name": "GA",
                "qty": 1,
                "unit": Decimal("10000"),
            }
        ],
    )
    order.referral_code = plat["referral_code"]
    db_session.commit()
    finalize_promo_and_attribution(db_session, order=order)
    db_session.commit()
    earning = db_session.scalar(
        select(ReferralCommissionEntry).where(
            ReferralCommissionEntry.order_id == order.id,
            ReferralCommissionEntry.entry_type == "earning",
        )
    )
    assert earning is not None
    original_amount = Decimal(earning.commission_amount)
    item_id = earning.order_item_id
    assert item_id is not None

    # 50% partial
    rev1 = reverse_commission_for_order_item(
        db_session,
        order_id=order.id,
        order_item_id=item_id,
        refunded_base=Decimal("5000"),
        reason="Partial refund",
        source_event_id=f"refund-partial-{order.id}",
    )
    db_session.commit()
    assert rev1 is not None
    assert Decimal(rev1.commission_amount) == Decimal("-500.00")
    assert remaining_reversible_amount(db_session, earning=earning) == Decimal("500.00")
    db_session.refresh(earning)
    assert Decimal(earning.commission_amount) == original_amount  # immutable

    # Complete remaining
    rev2 = reverse_commission_for_order_item(
        db_session,
        order_id=order.id,
        order_item_id=item_id,
        refunded_base=Decimal("5000"),
        reason="Remaining refund",
        source_event_id=f"refund-rest-{order.id}",
    )
    db_session.commit()
    assert rev2 is not None
    assert remaining_reversible_amount(db_session, earning=earning) == Decimal("0")

    # Duplicate refund event
    dup = reverse_commission_for_order_item(
        db_session,
        order_id=order.id,
        order_item_id=item_id,
        refunded_base=Decimal("5000"),
        reason="Dup",
        source_event_id=f"refund-rest-{order.id}",
    )
    assert dup is not None
    assert dup.id == rev2.id

    reverse_ambassador_sale_for_order(
        db_session, order_id=order.id, reason="compat mark"
    )
    db_session.commit()


def test_reporting_and_idor(
    client: TestClient, db_session: Session, assign_role
):
    tag = uuid4().hex[:8]
    _host, event, fan, buyer, host_email, tt1, _ = _seed(db_session, tag=tag)
    admin = _admin(client, assign_role, f"led-admin4-{tag}@example.com")
    other = User(
        email=f"led-other-{tag}@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Other",
        is_active=True,
    )
    db_session.add(other)
    db_session.commit()

    prog = client.post(
        "/api/v1/promos/admin/referral-programs",
        headers=admin,
        json={
            "name": "Report Prog",
            "ticket_rule": {"commission_mode": "percentage", "commission_value": 8},
        },
    ).json()
    plat = client.post(
        f"/api/v1/promos/admin/referral-programs/{prog['id']}/enrollments",
        headers=admin,
        json={"email": fan.email},
    ).json()
    order = _order_with_items(
        db_session,
        event=event,
        buyer=buyer,
        lines=[
            {
                "kind": "ticket",
                "ticket_type_id": tt1.id,
                "name": "GA",
                "qty": 1,
                "unit": Decimal("10000"),
            }
        ],
    )
    order.referral_code = plat["referral_code"]
    db_session.commit()
    finalize_promo_and_attribution(db_session, order=order)
    db_session.commit()

    fan_user = db_session.scalar(select(User).where(User.email == fan.email))
    assert fan_user is not None
    summary = get_ambassador_referral_summary(db_session, user=fan_user)
    assert Decimal(summary["net_commission"]) == Decimal("800.00")
    admin_sum = get_admin_referral_summary(db_session)
    assert Decimal(admin_sum["platform_funded_commission"]) >= Decimal("800.00")

    # Host cannot create platform program
    host_h = _login(client, host_email)
    denied = client.post(
        "/api/v1/promos/admin/referral-programs",
        headers=host_h,
        json={
            "name": "Nope",
            "ticket_rule": {"commission_mode": "percentage", "commission_value": 1},
        },
    )
    assert denied.status_code in {401, 403}

    # Other ambassador cannot see fan earnings via me endpoint
    client.post(
        "/api/v1/auth/register",
        json={
            "email": other.email,
            "password": "securepass1",
            "full_name": "Other",
            "gender": "prefer_not_to_say",
        },
    )
    other_h = _login(client, other.email)
    mine = client.get("/api/v1/referrals/me/earnings", headers=other_h)
    assert mine.status_code == 200
    assert mine.json() == []

    # Host platform attributed sales readable
    host_plat = client.get(
        "/api/v1/host/referrals/platform-attributed-sales", headers=host_h
    )
    assert host_plat.status_code == 200
    assert len(host_plat.json()) >= 1
    assert host_plat.json()[0]["commission_funded_by"] == "Padeya"
