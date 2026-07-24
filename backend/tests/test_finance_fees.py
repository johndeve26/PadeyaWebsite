"""Pàdéyá finance fee architecture tests (integer minor units)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.audit import AuditLog
from app.core.security import hash_password
from app.events.models import Event, EventCategory
from app.finance.fees.constants import (
    FEE_KEY_BUYER_SERVICE,
    FEE_KEY_TICKET_COMMISSION,
    FEE_KEY_TICKET_FIXED,
)
from app.finance.fees.fee_calculation_service import (
    FeeCalculationService,
    calculate_buyer_total,
    calculate_host_net_earnings,
)
from app.finance.fees.fee_settings_service import FeeSettingsService
from app.finance.fees.host_fee_override_service import HostFeeOverrideService
from app.finance.fees.models import OrderFeeSnapshot, PlatformFeeSetting
from app.finance.fees.money import apply_percentage, major_to_minor
from app.finance.fees.schemas import (
    HostFeeOverrideCreate,
    PlatformFeeSettingCreate,
    PlatformFeeSettingUpdate,
)
from app.hosts.models import Host, HostProfile
from app.payments.models import Order
from app.users.models import User
from app.users.service import get_role_by_name


def _seed_admin_and_host(db: Session) -> tuple[User, Host]:
    admin = User(
        email="fee-admin@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Fee Admin",
        is_active=True,
    )
    role = get_role_by_name(db, "finance_admin")
    assert role is not None
    admin.roles.append(role)
    db.add(admin)
    db.flush()

    host_user = User(
        email="fee-host@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Fee Host",
        is_active=True,
    )
    host_role = get_role_by_name(db, "host")
    assert host_role is not None
    host_user.roles.append(host_role)
    db.add(host_user)
    db.flush()

    host = Host(
        user_id=host_user.id,
        display_name="Fee Host",
        slug="fee-host",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, bio="Fee host"))
    db.flush()
    return admin, host


def _seed_order(db: Session, *, host: Host, buyer: User | None = None) -> Order:
    if buyer is None:
        buyer = User(
            email="fee-buyer@example.com",
            password_hash=hash_password("securepass1"),
            full_name="Fee Buyer",
            is_active=True,
        )
        buyer_role = get_role_by_name(db, "buyer")
        assert buyer_role is not None
        buyer.roles.append(buyer_role)
        db.add(buyer)
        db.flush()

    category = db.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=14)
    event = Event(
        title="Fee Event",
        slug="fee-event",
        description="Event used for fee architecture snapshot tests with detail.",
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

    order = Order(
        buyer_user_id=buyer.id,
        event_id=event.id,
        status="pending",
        currency="NGN",
        subtotal_amount=Decimal("10000.00"),
        discount_amount=Decimal("0"),
        total_amount=Decimal("10000.00"),
        reference="FEE-TEST-ORDER-1",
        buyer_email=buyer.email,
        buyer_name=buyer.full_name or "Fee Buyer",
    )
    db.add(order)
    db.flush()
    return order


def _create_ticket_commission(
    db: Session,
    admin: User,
    *,
    percentage: str = "10.00",
    enabled: bool = True,
    effective_from: datetime | None = None,
) -> PlatformFeeSetting:
    svc = FeeSettingsService(db)
    return svc.create_setting(
        PlatformFeeSettingCreate(
            fee_key=FEE_KEY_TICKET_COMMISSION,
            label="Ticket commission",
            category="ticket",
            fee_type="percentage",
            percentage_value=Decimal(percentage),
            fixed_value=None,
            currency="NGN",
            payer="host",
            enabled=enabled,
            applies_to="all",
            effective_from=effective_from or (datetime.now(UTC) - timedelta(days=1)),
        ),
        admin=admin,
    )


def _create_buyer_service_fee(
    db: Session,
    admin: User,
    *,
    percentage: str = "5.00",
    fixed_value: int | None = None,
    fee_type: str = "percentage",
) -> PlatformFeeSetting:
    svc = FeeSettingsService(db)
    return svc.create_setting(
        PlatformFeeSettingCreate(
            fee_key=FEE_KEY_BUYER_SERVICE,
            label="Buyer platform / service fee",
            category="general",
            fee_type=fee_type,
            percentage_value=Decimal(percentage) if fee_type != "fixed" else None,
            fixed_value=fixed_value,
            currency="NGN",
            payer="buyer",
            enabled=True,
            applies_to="all",
            effective_from=datetime.now(UTC) - timedelta(days=1),
        ),
        admin=admin,
    )


def test_global_ticket_percentage_fee_applies(db_session: Session) -> None:
    admin, host = _seed_admin_and_host(db_session)
    _create_ticket_commission(db_session, admin, percentage="10.00")
    db_session.commit()

    base = major_to_minor(Decimal("10000.00"))  # 1_000_000 kobo
    breakdown = FeeCalculationService(db_session).calculate_ticket_fees(
        ticket_subtotal_minor=base,
        host_id=host.id,
    )
    commission = next(line for line in breakdown.lines if line.fee_key == FEE_KEY_TICKET_COMMISSION)
    assert commission.amount_minor == 100_000  # 10% of 1_000_000
    assert commission.payer == "host"
    assert commission.source == "global"


def test_buyer_service_fee_applies_to_buyer_total(db_session: Session) -> None:
    admin, host = _seed_admin_and_host(db_session)
    _create_buyer_service_fee(db_session, admin, percentage="5.00")
    db_session.commit()

    base = major_to_minor(Decimal("10000.00"))
    breakdown = FeeCalculationService(db_session).calculate_ticket_fees(
        ticket_subtotal_minor=base,
        host_id=host.id,
    )
    assert breakdown.buyer_fees_minor == 50_000
    assert calculate_buyer_total(base_amount_minor=base, calculated_fees=breakdown) == 1_050_000
    assert breakdown.buyer_total_minor == 1_050_000


def test_host_commission_reduces_host_earnings(db_session: Session) -> None:
    admin, host = _seed_admin_and_host(db_session)
    _create_ticket_commission(db_session, admin, percentage="10.00")
    db_session.commit()

    base = major_to_minor(Decimal("10000.00"))
    breakdown = FeeCalculationService(db_session).calculate_ticket_fees(
        ticket_subtotal_minor=base,
        host_id=host.id,
    )
    assert breakdown.host_fees_minor == 100_000
    assert calculate_host_net_earnings(
        base_amount_minor=base, calculated_fees=breakdown
    ) == 900_000
    assert breakdown.host_net_minor == 900_000


def test_host_override_beats_global_setting(db_session: Session) -> None:
    admin, host = _seed_admin_and_host(db_session)
    _create_ticket_commission(db_session, admin, percentage="10.00")
    HostFeeOverrideService(db_session).create_override(
        HostFeeOverrideCreate(
            host_id=host.id,
            fee_key=FEE_KEY_TICKET_COMMISSION,
            percentage_value=Decimal("3.00"),
            fixed_value=None,
            payer="host",
            enabled=True,
            effective_from=datetime.now(UTC) - timedelta(hours=1),
            reason="Preferred partner rate",
        ),
        admin=admin,
    )
    db_session.commit()

    base = major_to_minor(Decimal("10000.00"))
    breakdown = FeeCalculationService(db_session).calculate_ticket_fees(
        ticket_subtotal_minor=base,
        host_id=host.id,
    )
    commission = next(line for line in breakdown.lines if line.fee_key == FEE_KEY_TICKET_COMMISSION)
    assert commission.source == "host_override"
    assert commission.amount_minor == 30_000
    assert breakdown.host_net_minor == 970_000


def test_disabled_fee_does_not_apply(db_session: Session) -> None:
    admin, host = _seed_admin_and_host(db_session)
    _create_ticket_commission(db_session, admin, percentage="10.00", enabled=False)
    db_session.commit()

    base = major_to_minor(Decimal("10000.00"))
    breakdown = FeeCalculationService(db_session).calculate_ticket_fees(
        ticket_subtotal_minor=base,
        host_id=host.id,
    )
    assert all(line.fee_key != FEE_KEY_TICKET_COMMISSION for line in breakdown.lines)
    assert breakdown.host_fees_minor == 0
    assert breakdown.host_net_minor == base


def test_fee_snapshot_stored_on_order(db_session: Session) -> None:
    admin, host = _seed_admin_and_host(db_session)
    _create_ticket_commission(db_session, admin, percentage="10.00")
    _create_buyer_service_fee(db_session, admin, percentage="2.50")
    order = _seed_order(db_session, host=host)
    db_session.commit()

    calc = FeeCalculationService(db_session)
    base = major_to_minor(Decimal("10000.00"))
    breakdown = calc.calculate_ticket_fees(ticket_subtotal_minor=base, host_id=host.id)
    snaps = calc.create_order_fee_snapshot(order.id, breakdown, host_id=host.id)
    db_session.commit()

    assert len(snaps) >= 2
    stored = calc.list_order_fee_snapshots(order.id)
    assert {s.fee_key for s in stored} >= {FEE_KEY_TICKET_COMMISSION, FEE_KEY_BUYER_SERVICE}
    commission = next(s for s in stored if s.fee_key == FEE_KEY_TICKET_COMMISSION)
    assert commission.amount == 100_000
    assert commission.order_id == order.id


def test_old_order_snapshot_does_not_change_after_fee_update(db_session: Session) -> None:
    admin, host = _seed_admin_and_host(db_session)
    setting = _create_ticket_commission(db_session, admin, percentage="10.00")
    order = _seed_order(db_session, host=host)
    db_session.commit()

    calc = FeeCalculationService(db_session)
    base = major_to_minor(Decimal("10000.00"))
    breakdown = calc.calculate_ticket_fees(ticket_subtotal_minor=base, host_id=host.id)
    calc.create_order_fee_snapshot(order.id, breakdown, host_id=host.id)
    db_session.commit()

    FeeSettingsService(db_session).update_setting(
        setting.id,
        PlatformFeeSettingUpdate(percentage_value=Decimal("25.00")),
        admin=admin,
    )
    db_session.commit()

    stored = db_session.query(OrderFeeSnapshot).filter_by(order_id=order.id).all()
    commission = next(s for s in stored if s.fee_key == FEE_KEY_TICKET_COMMISSION)
    assert commission.amount == 100_000
    assert Decimal(str(commission.percentage_value)) == Decimal("10.0000") or Decimal(
        str(commission.percentage_value)
    ) == Decimal("10.00")

    # New calc uses updated rate; snapshot stays frozen.
    new_breakdown = calc.calculate_ticket_fees(ticket_subtotal_minor=base, host_id=host.id)
    new_line = next(l for l in new_breakdown.lines if l.fee_key == FEE_KEY_TICKET_COMMISSION)
    assert new_line.amount_minor == 250_000


def test_fixed_fee_works(db_session: Session) -> None:
    admin, host = _seed_admin_and_host(db_session)
    FeeSettingsService(db_session).create_setting(
        PlatformFeeSettingCreate(
            fee_key=FEE_KEY_TICKET_FIXED,
            label="Ticket fixed fee",
            category="ticket",
            fee_type="fixed",
            percentage_value=None,
            fixed_value=150_00,  # ₦150.00
            currency="NGN",
            payer="host",
            enabled=True,
            applies_to="all",
            effective_from=datetime.now(UTC) - timedelta(days=1),
        ),
        admin=admin,
    )
    db_session.commit()

    base = major_to_minor(Decimal("5000.00"))
    breakdown = FeeCalculationService(db_session).calculate_ticket_fees(
        ticket_subtotal_minor=base,
        host_id=host.id,
    )
    fixed = next(line for line in breakdown.lines if line.fee_key == FEE_KEY_TICKET_FIXED)
    assert fixed.amount_minor == 15_000
    assert breakdown.host_net_minor == base - 15_000


def test_mixed_percentage_plus_fixed_fee_works(db_session: Session) -> None:
    admin, host = _seed_admin_and_host(db_session)
    _create_buyer_service_fee(
        db_session,
        admin,
        percentage="2.50",
        fixed_value=100_00,  # ₦100
        fee_type="mixed",
    )
    db_session.commit()

    base = major_to_minor(Decimal("10000.00"))  # 1_000_000
    breakdown = FeeCalculationService(db_session).calculate_ticket_fees(
        ticket_subtotal_minor=base,
        host_id=host.id,
    )
    service = next(line for line in breakdown.lines if line.fee_key == FEE_KEY_BUYER_SERVICE)
    # 2.5% of 1_000_000 = 25_000 + 10_000 fixed = 35_000
    assert service.amount_minor == 35_000
    assert service.fee_type == "mixed"
    assert breakdown.buyer_total_minor == 1_035_000


def test_money_calculations_avoid_float_errors(db_session: Session) -> None:
    # Classic float trap: 0.1 + 0.2 != 0.3 — integer path must stay exact.
    assert apply_percentage(10_00, Decimal("10")) == 100
    assert apply_percentage(333_33, Decimal("10")) == 3_333  # half-up of 3333.3
    assert apply_percentage(10_00, Decimal("0.1")) == 1
    assert major_to_minor(Decimal("0.1") + Decimal("0.2")) == 30

    admin, host = _seed_admin_and_host(db_session)
    _create_ticket_commission(db_session, admin, percentage="0.10")
    db_session.commit()

    base = 999_99  # awkward minor amount
    breakdown = FeeCalculationService(db_session).calculate_ticket_fees(
        ticket_subtotal_minor=base,
        host_id=host.id,
    )
    commission = next(line for line in breakdown.lines if line.fee_key == FEE_KEY_TICKET_COMMISSION)
    # 0.10% of 99999 = 99.999 → 100 half-up
    assert commission.amount_minor == 100
    assert isinstance(commission.amount_minor, int)
    assert isinstance(breakdown.buyer_total_minor, int)
    assert isinstance(breakdown.host_net_minor, int)


def test_fee_setting_changes_are_audited(db_session: Session) -> None:
    admin, _host = _seed_admin_and_host(db_session)
    setting = _create_ticket_commission(db_session, admin, percentage="8.00")
    FeeSettingsService(db_session).update_setting(
        setting.id,
        PlatformFeeSettingUpdate(enabled=False),
        admin=admin,
    )
    db_session.commit()

    actions = {
        row.action
        for row in db_session.query(AuditLog)
        .filter(AuditLog.action.like("finance.fee_%"))
        .all()
    }
    assert "finance.fee_setting_create" in actions
    assert "finance.fee_setting_update" in actions


def test_effective_dates_respected(db_session: Session) -> None:
    admin, host = _seed_admin_and_host(db_session)
    now = datetime.now(UTC)
    FeeSettingsService(db_session).create_setting(
        PlatformFeeSettingCreate(
            fee_key=FEE_KEY_TICKET_COMMISSION,
            label="Future commission",
            category="ticket",
            fee_type="percentage",
            percentage_value=Decimal("50.00"),
            currency="NGN",
            payer="host",
            enabled=True,
            applies_to="all",
            effective_from=now + timedelta(days=30),
        ),
        admin=admin,
    )
    db_session.commit()

    breakdown = FeeCalculationService(db_session).calculate_ticket_fees(
        ticket_subtotal_minor=1_000_000,
        host_id=host.id,
        at=now,
    )
    assert all(line.fee_key != FEE_KEY_TICKET_COMMISSION for line in breakdown.lines)
