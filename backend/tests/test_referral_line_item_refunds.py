"""Line-item referral commission reversals (REFERRAL-P1-002)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.events.models import Event, EventCategory, TicketType
from app.finance.earnings_service import _ambassador_by_order
from app.hosts.models import Host, HostProfile
from app.payments.models import Order, OrderItem
from app.promos.constants import PAYER_HOST, PAYER_PLATFORM
from app.promos.ledger_service import (
    remaining_reversible_amount,
    reverse_commission_for_order_item,
)
from app.promos.referral_ledger import ReferralAttribution, ReferralCommissionEntry
from app.promos.refund_allocations import (
    LineRefundAllocation,
    ReferralRefundAllocationError,
    apply_line_item_referral_reversals,
    apply_referral_reversals_for_finance_refund,
    earnings_are_homogeneous,
)
from app.promos.reporting import get_admin_referral_summary, get_ambassador_referral_summary
from app.promos.service import finalize_promo_and_attribution
from app.users.models import User
from app.users.service import get_role_by_name


def _seed(db: Session, *, tag: str):
    host_user = User(
        email=f"ref-host-{tag}@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Refund Host",
        is_active=True,
    )
    role = get_role_by_name(db, "host")
    assert role is not None
    host_user.roles.append(role)
    fan = User(
        email=f"ref-fan-{tag}@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Refund Fan",
        is_active=True,
    )
    buyer = User(
        email=f"ref-buyer-{tag}@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Refund Buyer",
        is_active=True,
    )
    db.add_all([host_user, fan, buyer])
    db.flush()
    host = Host(
        user_id=host_user.id,
        display_name="Refund Host",
        slug=f"ref-host-{tag}",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, city="Lagos"))
    category = db.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=5)
    event = Event(
        title="Refund Night",
        slug=f"ref-night-{tag}",
        description="Refund tests",
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
    tt = TicketType(
        event_id=event.id,
        name="GA",
        type="regular",
        price=Decimal("5000.00"),
        quantity=100,
        quantity_sold=0,
        quantity_reserved=0,
        min_per_order=1,
        max_per_order=10,
        visibility="public",
        status="active",
    )
    db.add(tt)
    db.commit()
    return host, event, fan, buyer, tt


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
        reference=f"ref-{uuid4().hex[:12]}",
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


def _manual_earning(
    db: Session,
    *,
    order: Order,
    item: OrderItem,
    fan: User,
    payer_type: str,
    mode: str,
    rate: Decimal,
    amount: Decimal,
    enrollment_id=None,
) -> ReferralCommissionEntry:
    from app.promos.models import Ambassador

    amb = enrollment_id
    if amb is None:
        amb_row = Ambassador(
            user_id=fan.id,
            host_id=order.host_id if payer_type == PAYER_HOST else None,
            event_id=order.event_id if payer_type == PAYER_HOST else None,
            display_name="Refund Amb",
            email=fan.email,
            referral_code=f"r{uuid4().hex[:10]}",
            status="active",
            commission_rate_percent=rate if mode == "percentage" else Decimal("0"),
            program_kind="host_curated" if payer_type == PAYER_HOST else "platform_wide",
        )
        db.add(amb_row)
        db.flush()
        amb = amb_row.id
        amb_user = fan.id
    else:
        amb_row = db.get(Ambassador, amb)
        assert amb_row is not None
        amb_user = amb_row.user_id

    attr = ReferralAttribution(
        order_id=order.id,
        order_item_id=item.id,
        attribution_item_key=str(item.id),
        enrollment_id=amb,
        ambassador_user_id=amb_user,
        event_id=order.event_id,
        host_id=order.host_id,
        product_type="ticket" if item.item_kind == "ticket" else "merchandise",
        product_id=item.ticket_type_id or item.merch_product_id,
        payer_type=payer_type,
        winning_scope="event" if payer_type == PAYER_HOST else "platform",
        idempotency_key=f"referral-attr:{order.id}:{item.id}",
        resolved_at=datetime.now(UTC),
    )
    db.add(attr)
    db.flush()
    entry = ReferralCommissionEntry(
        attribution_id=attr.id,
        enrollment_id=amb,
        ambassador_user_id=amb_user,
        order_id=order.id,
        order_item_id=item.id,
        attribution_item_key=str(item.id),
        event_id=order.event_id,
        host_id=order.host_id,
        product_type=attr.product_type,
        payer_type=payer_type,
        entry_type="earning",
        gross_item_amount=Decimal(item.line_total),
        eligible_commission_base=Decimal(item.line_total),
        commission_mode=mode,
        commission_rate=rate,
        commission_amount=amount,
        currency="NGN",
        status="pending",
        idempotency_key=f"referral-earning:{order.id}:{item.id}",
        source_event_id=f"order-paid:{order.id}",
    )
    db.add(entry)
    db.flush()
    return entry


def test_quantity_aware_percentage_reversals(db_session: Session):
    tag = uuid4().hex[:8]
    _host, event, fan, buyer, tt = _seed(db_session, tag=tag)
    order = _order_with_items(
        db_session,
        event=event,
        buyer=buyer,
        lines=[
            {
                "kind": "ticket",
                "ticket_type_id": tt.id,
                "name": "GA",
                "qty": 4,
                "unit": Decimal("5000"),
            }
        ],
    )
    item = order.items[0]
    earning = _manual_earning(
        db_session,
        order=order,
        item=item,
        fan=fan,
        payer_type=PAYER_PLATFORM,
        mode="percentage",
        rate=Decimal("10"),
        amount=Decimal("2000.00"),
    )
    db_session.commit()

    # Refund 1 ticket → ₦500
    r1 = reverse_commission_for_order_item(
        db_session,
        order_id=order.id,
        order_item_id=item.id,
        refunded_base=Decimal("5000"),
        reason="qty1",
        source_event_id=f"refund-q1-{order.id}",
        refunded_quantity=1,
    )
    db_session.commit()
    assert r1 is not None
    assert Decimal(r1.commission_amount) == Decimal("-500.00")

    # Refund 2 more → ₦1000
    r2 = reverse_commission_for_order_item(
        db_session,
        order_id=order.id,
        order_item_id=item.id,
        refunded_base=Decimal("10000"),
        reason="qty2",
        source_event_id=f"refund-q2-{order.id}",
        refunded_quantity=2,
    )
    db_session.commit()
    assert Decimal(r2.commission_amount) == Decimal("-1000.00")

    # Final 1 → ₦500
    r3 = reverse_commission_for_order_item(
        db_session,
        order_id=order.id,
        order_item_id=item.id,
        refunded_base=Decimal("5000"),
        reason="qty3",
        source_event_id=f"refund-q3-{order.id}",
        refunded_quantity=1,
    )
    db_session.commit()
    assert Decimal(r3.commission_amount) == Decimal("-500.00")
    assert remaining_reversible_amount(db_session, earning=earning) == Decimal("0")
    db_session.refresh(earning)
    assert Decimal(earning.commission_amount) == Decimal("2000.00")


def test_fixed_commission_quantity_reversal(db_session: Session):
    """Fixed per-unit: refunding one unit reverses one unit of earning."""
    tag = uuid4().hex[:8]
    _host, event, fan, buyer, tt = _seed(db_session, tag=tag)
    order = _order_with_items(
        db_session,
        event=event,
        buyer=buyer,
        lines=[
            {
                "kind": "merch",
                "name": "Tee",
                "qty": 4,
                "unit": Decimal("3000"),
            }
        ],
    )
    item = order.items[0]
    # ₦250 fixed × 4 = ₦1000
    earning = _manual_earning(
        db_session,
        order=order,
        item=item,
        fan=fan,
        payer_type=PAYER_PLATFORM,
        mode="fixed",
        rate=Decimal("250"),
        amount=Decimal("1000.00"),
    )
    db_session.commit()

    rev = apply_line_item_referral_reversals(
        db_session,
        order=order,
        allocations=[
            LineRefundAllocation(
                order_item_id=item.id,
                refunded_quantity=1,
                refunded_item_subtotal=Decimal("3000"),
                allocation_id="fixed-unit-1",
            )
        ],
        refund_event_id=f"finance-refund:{uuid4()}",
        reason="fixed unit refund",
    )
    db_session.commit()
    assert len(rev) == 1
    assert Decimal(rev[0].commission_amount) == Decimal("-250.00")
    assert remaining_reversible_amount(db_session, earning=earning) == Decimal("750.00")


def test_mixed_payer_partial_refund_only_affects_allocated_item(db_session: Session):
    tag = uuid4().hex[:8]
    host, event, fan, buyer, tt = _seed(db_session, tag=tag)
    order = _order_with_items(
        db_session,
        event=event,
        buyer=buyer,
        lines=[
            {
                "kind": "ticket",
                "ticket_type_id": tt.id,
                "name": "Host GA",
                "qty": 1,
                "unit": Decimal("10000"),
            },
            {
                "kind": "ticket",
                "ticket_type_id": tt.id,
                "name": "Plat VIP",
                "qty": 1,
                "unit": Decimal("20000"),
            },
            {
                "kind": "merch",
                "name": "Eligible Tee",
                "qty": 1,
                "unit": Decimal("8000"),
            },
            {
                "kind": "merch",
                "name": "Excluded Cap",
                "qty": 1,
                "unit": Decimal("4000"),
            },
        ],
    )
    items = {i.product_name or i.ticket_type_name: i for i in order.items}
    a = items["Host GA"]
    b = items["Plat VIP"]
    c = items["Eligible Tee"]
    d = items["Excluded Cap"]

    earn_a = _manual_earning(
        db_session,
        order=order,
        item=a,
        fan=fan,
        payer_type=PAYER_HOST,
        mode="percentage",
        rate=Decimal("10"),
        amount=Decimal("1000.00"),
    )
    earn_b = _manual_earning(
        db_session,
        order=order,
        item=b,
        fan=fan,
        payer_type=PAYER_PLATFORM,
        mode="percentage",
        rate=Decimal("5"),
        amount=Decimal("1000.00"),
        enrollment_id=earn_a.enrollment_id,
    )
    earn_c = _manual_earning(
        db_session,
        order=order,
        item=c,
        fan=fan,
        payer_type=PAYER_PLATFORM,
        mode="fixed",
        rate=Decimal("400"),
        amount=Decimal("400.00"),
        enrollment_id=earn_a.enrollment_id,
    )
    db_session.commit()
    assert (
        db_session.scalar(
            select(ReferralCommissionEntry).where(
                ReferralCommissionEntry.order_item_id == d.id
            )
        )
        is None
    )

    admin_before = get_admin_referral_summary(db_session)
    plat_before = Decimal(str(admin_before["platform_funded_commission"]))
    host_before = Decimal(str(admin_before["host_funded_commission"]))
    amb_before = get_ambassador_referral_summary(db_session, user=fan)
    net_before = Decimal(str(amb_before["net_commission"]))

    refund_id = uuid4()
    revs = apply_line_item_referral_reversals(
        db_session,
        order=order,
        allocations=[
            LineRefundAllocation(
                order_item_id=b.id,
                refunded_quantity=1,
                refunded_item_subtotal=Decimal("20000"),
                allocation_id=f"alloc-b-{refund_id}",
            )
        ],
        refund_event_id=f"finance-refund:{refund_id}",
        reason="Partial ITEM B only",
    )
    db_session.commit()
    assert len(revs) == 1
    assert Decimal(revs[0].commission_amount) == Decimal("-1000.00")
    assert revs[0].payer_type == PAYER_PLATFORM
    assert remaining_reversible_amount(db_session, earning=earn_a) == Decimal("1000.00")
    assert remaining_reversible_amount(db_session, earning=earn_b) == Decimal("0")
    assert remaining_reversible_amount(db_session, earning=earn_c) == Decimal("400.00")

    host_liability = _ambassador_by_order(db_session, [order.id])
    assert host_liability.get(order.id, Decimal("0")) == Decimal("1000.00")

    admin_after = get_admin_referral_summary(db_session)
    assert Decimal(str(admin_after["platform_funded_commission"])) == plat_before - Decimal(
        "1000.00"
    )
    assert Decimal(str(admin_after["host_funded_commission"])) == host_before
    amb_after = get_ambassador_referral_summary(db_session, user=fan)
    assert Decimal(str(amb_after["net_commission"])) == net_before - Decimal("1000.00")

    # Refund ITEM A (host) independently
    refund_id2 = uuid4()
    revs2 = apply_line_item_referral_reversals(
        db_session,
        order=order,
        allocations=[
            LineRefundAllocation(
                order_item_id=a.id,
                refunded_quantity=1,
                refunded_item_subtotal=Decimal("10000"),
                allocation_id=f"alloc-a-{refund_id2}",
            )
        ],
        refund_event_id=f"finance-refund:{refund_id2}",
        reason="Partial ITEM A",
    )
    db_session.commit()
    assert len(revs2) == 1
    assert revs2[0].payer_type == PAYER_HOST
    assert remaining_reversible_amount(db_session, earning=earn_a) == Decimal("0")
    host_liability2 = _ambassador_by_order(db_session, [order.id])
    assert host_liability2.get(order.id, Decimal("0")) == Decimal("0")


def test_refund_idempotency_same_allocation(db_session: Session):
    tag = uuid4().hex[:8]
    _host, event, fan, buyer, tt = _seed(db_session, tag=tag)
    order = _order_with_items(
        db_session,
        event=event,
        buyer=buyer,
        lines=[
            {
                "kind": "ticket",
                "ticket_type_id": tt.id,
                "name": "GA",
                "qty": 2,
                "unit": Decimal("5000"),
            }
        ],
    )
    item = order.items[0]
    _manual_earning(
        db_session,
        order=order,
        item=item,
        fan=fan,
        payer_type=PAYER_PLATFORM,
        mode="percentage",
        rate=Decimal("10"),
        amount=Decimal("1000.00"),
    )
    db_session.commit()

    event_id = f"finance-refund:{uuid4()}"
    alloc = LineRefundAllocation(
        order_item_id=item.id,
        refunded_quantity=1,
        refunded_item_subtotal=Decimal("5000"),
        allocation_id="stable-alloc-1",
    )
    first = apply_line_item_referral_reversals(
        db_session,
        order=order,
        allocations=[alloc],
        refund_event_id=event_id,
        reason="first",
    )
    db_session.commit()
    second = apply_line_item_referral_reversals(
        db_session,
        order=order,
        allocations=[alloc],
        refund_event_id=event_id,
        reason="retry",
    )
    db_session.commit()
    assert len(first) == 1 and len(second) == 1
    assert first[0].id == second[0].id
    revs = list(
        db_session.scalars(
            select(ReferralCommissionEntry).where(
                ReferralCommissionEntry.order_id == order.id,
                ReferralCommissionEntry.entry_type == "reversal",
            )
        )
    )
    assert len(revs) == 1


def test_validation_rejects_bad_allocations(db_session: Session):
    tag = uuid4().hex[:8]
    _host, event, fan, buyer, tt = _seed(db_session, tag=tag)
    order = _order_with_items(
        db_session,
        event=event,
        buyer=buyer,
        lines=[
            {
                "kind": "ticket",
                "ticket_type_id": tt.id,
                "name": "GA",
                "qty": 1,
                "unit": Decimal("5000"),
            }
        ],
    )
    item = order.items[0]
    _manual_earning(
        db_session,
        order=order,
        item=item,
        fan=fan,
        payer_type=PAYER_PLATFORM,
        mode="percentage",
        rate=Decimal("10"),
        amount=Decimal("500.00"),
    )
    db_session.commit()

    with pytest.raises(ReferralRefundAllocationError):
        apply_line_item_referral_reversals(
            db_session,
            order=order,
            allocations=[
                LineRefundAllocation(
                    order_item_id=uuid4(),
                    refunded_quantity=1,
                    refunded_item_subtotal=Decimal("100"),
                )
            ],
            refund_event_id="x",
            reason="bad",
        )

    with pytest.raises(ReferralRefundAllocationError):
        apply_line_item_referral_reversals(
            db_session,
            order=order,
            allocations=[
                LineRefundAllocation(
                    order_item_id=item.id,
                    refunded_quantity=5,
                    refunded_item_subtotal=Decimal("5000"),
                )
            ],
            refund_event_id="y",
            reason="qty",
        )


def test_mixed_partial_without_allocations_requires_explicit(db_session: Session):
    tag = uuid4().hex[:8]
    _host, event, fan, buyer, tt = _seed(db_session, tag=tag)
    order = _order_with_items(
        db_session,
        event=event,
        buyer=buyer,
        lines=[
            {
                "kind": "ticket",
                "ticket_type_id": tt.id,
                "name": "A",
                "qty": 1,
                "unit": Decimal("10000"),
            },
            {
                "kind": "ticket",
                "ticket_type_id": tt.id,
                "name": "B",
                "qty": 1,
                "unit": Decimal("10000"),
            },
        ],
    )
    a, b = order.items[0], order.items[1]
    e1 = _manual_earning(
        db_session,
        order=order,
        item=a,
        fan=fan,
        payer_type=PAYER_HOST,
        mode="percentage",
        rate=Decimal("10"),
        amount=Decimal("1000.00"),
    )
    _manual_earning(
        db_session,
        order=order,
        item=b,
        fan=fan,
        payer_type=PAYER_PLATFORM,
        mode="percentage",
        rate=Decimal("5"),
        amount=Decimal("500.00"),
        enrollment_id=e1.enrollment_id,
    )
    db_session.commit()
    earnings = list(
        db_session.scalars(
            select(ReferralCommissionEntry).where(
                ReferralCommissionEntry.order_id == order.id,
                ReferralCommissionEntry.entry_type == "earning",
            )
        )
    )
    assert not earnings_are_homogeneous(earnings)

    with pytest.raises(HTTPException) as ei:
        apply_referral_reversals_for_finance_refund(
            db_session,
            order=order,
            refund_id=uuid4(),
            requested_amount=Decimal("5000"),
            reason="partial",
            actor_user_id=None,
            allocations=None,
            is_full_refund=False,
        )
    assert ei.value.status_code == 400
    detail = ei.value.detail
    assert isinstance(detail, dict)
    assert detail["code"] == "requires_referral_refund_allocation"


def test_full_refund_without_allocations_reverses_all(db_session: Session):
    tag = uuid4().hex[:8]
    _host, event, fan, buyer, tt = _seed(db_session, tag=tag)
    order = _order_with_items(
        db_session,
        event=event,
        buyer=buyer,
        lines=[
            {
                "kind": "ticket",
                "ticket_type_id": tt.id,
                "name": "A",
                "qty": 1,
                "unit": Decimal("10000"),
            },
            {
                "kind": "ticket",
                "ticket_type_id": tt.id,
                "name": "B",
                "qty": 1,
                "unit": Decimal("10000"),
            },
        ],
    )
    a, b = order.items[0], order.items[1]
    e1 = _manual_earning(
        db_session,
        order=order,
        item=a,
        fan=fan,
        payer_type=PAYER_HOST,
        mode="percentage",
        rate=Decimal("10"),
        amount=Decimal("1000.00"),
    )
    e2 = _manual_earning(
        db_session,
        order=order,
        item=b,
        fan=fan,
        payer_type=PAYER_PLATFORM,
        mode="percentage",
        rate=Decimal("5"),
        amount=Decimal("500.00"),
        enrollment_id=e1.enrollment_id,
    )
    db_session.commit()
    rows, flag = apply_referral_reversals_for_finance_refund(
        db_session,
        order=order,
        refund_id=uuid4(),
        requested_amount=Decimal("20000"),
        reason="full",
        actor_user_id=None,
        allocations=None,
        is_full_refund=True,
    )
    db_session.commit()
    assert flag is False
    assert len(rows) == 2
    assert remaining_reversible_amount(db_session, earning=e1) == Decimal("0")
    assert remaining_reversible_amount(db_session, earning=e2) == Decimal("0")


def test_platform_finalize_quantity_then_line_refund(
    client: TestClient, db_session: Session, assign_role
):
    """End-to-end-ish: platform finalize + quantity line refund via ledger helpers."""
    tag = uuid4().hex[:8]
    _host, event, fan, buyer, tt = _seed(db_session, tag=tag)
    client.post(
        "/api/v1/auth/register",
        json={
            "email": f"ref-admin-{tag}@example.com",
            "password": "securepass1",
            "full_name": "Admin",
            "gender": "prefer_not_to_say",
        },
    )
    assign_role(f"ref-admin-{tag}@example.com", "super_admin")
    login = client.post(
        "/api/v1/auth/login",
        json={"email": f"ref-admin-{tag}@example.com", "password": "securepass1"},
    )
    admin = {"Authorization": f"Bearer {login.json()['access_token']}"}
    prog = client.post(
        "/api/v1/promos/admin/referral-programs",
        headers=admin,
        json={
            "name": f"Qty Prog {tag}",
            "ticket_rule": {"commission_mode": "percentage", "commission_value": 10},
        },
    ).json()
    plat = client.post(
        f"/api/v1/promos/admin/referral-programs/{prog['id']}/enrollments",
        headers=admin,
        json={"email": fan.email, "referral_code": f"qty{tag}"},
    ).json()
    order = _order_with_items(
        db_session,
        event=event,
        buyer=buyer,
        lines=[
            {
                "kind": "ticket",
                "ticket_type_id": tt.id,
                "name": "GA",
                "qty": 4,
                "unit": Decimal("5000"),
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
    assert Decimal(earning.commission_amount) == Decimal("2000.00")
    item = order.items[0]
    rev = apply_line_item_referral_reversals(
        db_session,
        order=order,
        allocations=[
            LineRefundAllocation(
                order_item_id=item.id,
                refunded_quantity=1,
                refunded_item_subtotal=Decimal("5000"),
            )
        ],
        refund_event_id=f"finance-refund:{uuid4()}",
        reason="one ticket",
    )
    db_session.commit()
    assert Decimal(rev[0].commission_amount) == Decimal("-500.00")
