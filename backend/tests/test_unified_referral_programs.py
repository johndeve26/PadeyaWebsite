"""Unified referral: platform-wide programs, conflict priority, host settlement."""

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
from app.promos.constants import PAYER_HOST, PAYER_PLATFORM, PROGRAM_PLATFORM_WIDE
from app.promos.models import Ambassador, AmbassadorSale
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
            "full_name": "Ref Admin",
            "gender": "prefer_not_to_say",
        },
    )
    assign_role(email, "super_admin")
    return _login(client, email)


def _seed_event(db: Session, *, tag: str) -> tuple[Host, Event, User, User, str]:
    host_email = f"uni-host-{tag}@example.com"
    host_user = User(
        email=host_email,
        password_hash=hash_password("securepass1"),
        full_name="Uni Host",
        is_active=True,
    )
    role = get_role_by_name(db, "host")
    assert role is not None
    host_user.roles.append(role)
    fan = User(
        email=f"uni-fan-{tag}@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Uni Fan",
        is_active=True,
    )
    buyer = User(
        email=f"uni-buyer-{tag}@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Uni Buyer",
        is_active=True,
    )
    db.add_all([host_user, fan, buyer])
    db.flush()
    host = Host(
        user_id=host_user.id,
        display_name="Uni Host",
        slug=f"uni-host-{tag}",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, city="Lagos"))
    category = db.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=5)
    event = Event(
        title="Uni Ref Night",
        slug=f"uni-ref-{tag}",
        description="Unified referral tests.",
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
    db.add(
        TicketType(
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
    )
    db.commit()
    return host, event, fan, buyer, host_email


def _paid_order(
    db: Session,
    *,
    event: Event,
    buyer: User,
    tickets: int = 1,
    ticket_unit: Decimal = Decimal("10000.00"),
) -> Order:
    from uuid import UUID

    tt = db.query(TicketType).filter(TicketType.event_id == event.id).first()
    line = ticket_unit * tickets
    order = Order(
        event_id=event.id,
        host_id=event.host_id,
        buyer_user_id=buyer.id,
        buyer_email=buyer.email,
        buyer_name=buyer.full_name or "Buyer",
        status="paid",
        currency="NGN",
        subtotal_amount=line,
        discount_amount=Decimal("0"),
        total_amount=line,
        reference=f"uref-{uuid4().hex[:12]}",
    )
    db.add(order)
    db.flush()
    db.add(
        OrderItem(
            order_id=order.id,
            item_kind="ticket",
            ticket_type_id=tt.id if tt else None,
            ticket_type_name="GA",
            quantity=tickets,
            unit_price=ticket_unit,
            line_total=line,
        )
    )
    db.commit()
    order = db.get(Order, order.id)
    assert order is not None
    _ = list(order.items)
    return order


def test_admin_creates_platform_program_and_enrolls(
    client: TestClient, db_session: Session, assign_role
):
    tag = uuid4().hex[:8]
    _host, _event, fan, _buyer, host_email = _seed_event(db_session, tag=tag)
    admin = _admin(client, assign_role, f"uni-admin-{tag}@example.com")

    create = client.post(
        "/api/v1/promos/admin/referral-programs",
        headers=admin,
        json={
            "name": "Padeya Platform Ambassadors",
            "default_landing_path": "/events",
            "ticket_rule": {
                "commission_mode": "percentage",
                "commission_value": 4,
            },
            "merchandise_rule": {
                "commission_mode": "percentage",
                "commission_value": 6,
            },
        },
    )
    assert create.status_code == 201, create.text
    body = create.json()
    assert body["scope"] == "platform"
    assert body["commission_funded_by"] == "Padeya"
    assert body["event_id"] is None
    assert len(body["rules"]) == 2

    enroll = client.post(
        f"/api/v1/promos/admin/referral-programs/{body['id']}/enrollments",
        headers=admin,
        json={"email": fan.email},
    )
    assert enroll.status_code == 201, enroll.text
    code = enroll.json()["referral_code"]
    assert enroll.json()["referral_link_path"] == f"/r/{code}"

    resolve = client.get(f"/api/v1/promos/referral/resolve/{code}")
    assert resolve.status_code == 200, resolve.text
    assert "ref=" in resolve.json()["landing_path"]

    host = _login(client, host_email)
    denied = client.post(
        "/api/v1/promos/admin/referral-programs",
        headers=host,
        json={
            "name": "Nope",
            "ticket_rule": {"commission_mode": "percentage", "commission_value": 1},
        },
    )
    assert denied.status_code in {401, 403}


def test_platform_commission_does_not_reduce_host_settlement(
    client: TestClient, db_session: Session, assign_role
):
    tag = uuid4().hex[:8]
    _host, event, fan, buyer, _he = _seed_event(db_session, tag=tag)
    admin = _admin(client, assign_role, f"uni-admin-s-{tag}@example.com")
    created = client.post(
        "/api/v1/promos/admin/referral-programs",
        headers=admin,
        json={
            "name": "Settle Program",
            "ticket_rule": {
                "commission_mode": "percentage",
                "commission_value": 10,
            },
        },
    ).json()
    enroll = client.post(
        f"/api/v1/promos/admin/referral-programs/{created['id']}/enrollments",
        headers=admin,
        json={"email": fan.email},
    ).json()

    order = _paid_order(db_session, event=event, buyer=buyer, tickets=1)
    order.referral_code = enroll["referral_code"]
    order.platform_referral_code = enroll["referral_code"]
    db_session.commit()

    finalize_promo_and_attribution(db_session, order=order)
    db_session.commit()

    sales = list(
        db_session.scalars(
            select(AmbassadorSale).where(AmbassadorSale.order_id == order.id)
        )
    )
    assert len(sales) == 1
    assert sales[0].payer_type == PAYER_PLATFORM
    assert sales[0].commission_owed == Decimal("1000.00")

    host_deduction = _ambassador_by_order(db_session, [order.id])
    assert host_deduction.get(order.id, Decimal("0")) == Decimal("0")


def test_host_event_campaign_beats_platform(
    client: TestClient, db_session: Session, assign_role
):
    tag = uuid4().hex[:8]
    host, event, fan, buyer, host_email = _seed_event(db_session, tag=tag)
    admin = _admin(client, assign_role, f"uni-admin-c-{tag}@example.com")
    host_headers = _login(client, host_email)

    prog = client.post(
        "/api/v1/promos/admin/referral-programs",
        headers=admin,
        json={
            "name": "Conflict Platform",
            "ticket_rule": {
                "commission_mode": "percentage",
                "commission_value": 8,
            },
        },
    ).json()
    plat_enroll = client.post(
        f"/api/v1/promos/admin/referral-programs/{prog['id']}/enrollments",
        headers=admin,
        json={"email": fan.email, "referral_code": f"plat{tag}"},
    ).json()

    camp = client.post(
        "/api/v1/promos/campaigns",
        headers=host_headers,
        json={
            "event_id": str(event.id),
            "name": "Host Tickets",
            "campaign_type": "event_tickets",
            "commission_type": "percentage",
            "commission_value": 5,
            "commission_percent": 5,
            "status": "public_open",
        },
    )
    assert camp.status_code in {200, 201}, camp.text
    campaign_id = camp.json()["id"]

    created_amb = client.post(
        "/api/v1/promos/ambassadors",
        headers=host_headers,
        json={
            "event_id": str(event.id),
            "campaign_id": campaign_id,
            "display_name": "Host Amb",
            "email": fan.email,
            "referral_code": f"host{tag}",
            "commission_rate_percent": 5,
        },
    )
    assert created_amb.status_code == 201, created_amb.text
    host_code = created_amb.json()["referral_code"]

    order = _paid_order(db_session, event=event, buyer=buyer, tickets=1)
    order.referral_code = host_code
    order.platform_referral_code = plat_enroll["referral_code"]
    db_session.commit()

    winners = resolve_winning_attributions_for_order(db_session, order=order)
    assert len(winners) == 1
    assert winners[0].payer_type == PAYER_HOST

    finalize_promo_and_attribution(db_session, order=order)
    db_session.commit()
    sales = list(
        db_session.scalars(
            select(AmbassadorSale).where(AmbassadorSale.order_id == order.id)
        )
    )
    assert len(sales) == 1
    assert sales[0].payer_type == PAYER_HOST
    assert sales[0].commission_owed == Decimal("500.00")


def test_excluded_event_no_platform_commission(
    client: TestClient, db_session: Session, assign_role
):
    tag = uuid4().hex[:8]
    _host, event, fan, buyer, _he = _seed_event(db_session, tag=tag)
    admin = _admin(client, assign_role, f"uni-admin-e-{tag}@example.com")
    prog = client.post(
        "/api/v1/promos/admin/referral-programs",
        headers=admin,
        json={
            "name": "Excluded",
            "ticket_rule": {
                "commission_mode": "percentage",
                "commission_value": 5,
            },
            "excluded_event_ids": [str(event.id)],
        },
    ).json()
    enroll = client.post(
        f"/api/v1/promos/admin/referral-programs/{prog['id']}/enrollments",
        headers=admin,
        json={"email": fan.email},
    ).json()
    order = _paid_order(db_session, event=event, buyer=buyer, tickets=1)
    order.referral_code = enroll["referral_code"]
    db_session.commit()
    finalize_promo_and_attribution(db_session, order=order)
    db_session.commit()
    assert (
        db_session.scalar(
            select(AmbassadorSale).where(AmbassadorSale.order_id == order.id)
        )
        is None
    )


def test_refund_reverses_platform_sale(
    client: TestClient, db_session: Session, assign_role
):
    tag = uuid4().hex[:8]
    _host, event, fan, buyer, _he = _seed_event(db_session, tag=tag)
    admin = _admin(client, assign_role, f"uni-admin-r-{tag}@example.com")
    prog = client.post(
        "/api/v1/promos/admin/referral-programs",
        headers=admin,
        json={
            "name": "Refund Prog",
            "ticket_rule": {
                "commission_mode": "percentage",
                "commission_value": 5,
            },
        },
    ).json()
    enroll = client.post(
        f"/api/v1/promos/admin/referral-programs/{prog['id']}/enrollments",
        headers=admin,
        json={"email": fan.email},
    ).json()
    order = _paid_order(db_session, event=event, buyer=buyer, tickets=1)
    order.referral_code = enroll["referral_code"]
    db_session.commit()
    finalize_promo_and_attribution(db_session, order=order)
    db_session.commit()
    sale = db_session.scalar(
        select(AmbassadorSale).where(AmbassadorSale.order_id == order.id)
    )
    assert sale is not None
    assert sale.status == "attributed"
    reverse_ambassador_sale_for_order(
        db_session, order_id=order.id, reason="Full refund"
    )
    db_session.commit()
    db_session.refresh(sale)
    assert sale.status == "reversed"


def test_open_redirect_rejected(client: TestClient, db_session: Session, assign_role):
    tag = uuid4().hex[:8]
    admin = _admin(client, assign_role, f"uni-admin-o-{tag}@example.com")
    bad = client.post(
        "/api/v1/promos/admin/referral-programs",
        headers=admin,
        json={
            "name": "Bad landing",
            "default_landing_path": "https://evil.example",
            "ticket_rule": {
                "commission_mode": "percentage",
                "commission_value": 1,
            },
        },
    )
    assert bad.status_code == 400


def test_platform_wide_kind_on_enrollment(
    client: TestClient, db_session: Session, assign_role
):
    tag = uuid4().hex[:8]
    _host, _event, fan, _buyer, _he = _seed_event(db_session, tag=tag)
    admin = _admin(client, assign_role, f"uni-admin-k-{tag}@example.com")
    prog = client.post(
        "/api/v1/promos/admin/referral-programs",
        headers=admin,
        json={
            "name": "Kind check",
            "ticket_rule": {
                "commission_mode": "percentage",
                "commission_value": 3,
            },
        },
    ).json()
    enroll = client.post(
        f"/api/v1/promos/admin/referral-programs/{prog['id']}/enrollments",
        headers=admin,
        json={"email": fan.email},
    ).json()
    amb = db_session.get(Ambassador, UUID(enroll["id"]))
    assert amb is not None
    assert amb.program_kind == PROGRAM_PLATFORM_WIDE
    assert amb.host_id is None
    assert amb.event_id is None


def test_admin_ambassadors_list_includes_platform_wide_null_host(
    client: TestClient, db_session: Session, assign_role
):
    """Overview fails if response_model rejects null host_id (platform enrollments)."""
    tag = uuid4().hex[:8]
    _host, _event, fan, _buyer, _he = _seed_event(db_session, tag=tag)
    admin = _admin(client, assign_role, f"uni-admin-list-{tag}@example.com")
    prog = client.post(
        "/api/v1/promos/admin/referral-programs",
        headers=admin,
        json={
            "name": "List null host",
            "ticket_rule": {
                "commission_mode": "percentage",
                "commission_value": 4,
            },
        },
    ).json()
    enroll = client.post(
        f"/api/v1/promos/admin/referral-programs/{prog['id']}/enrollments",
        headers=admin,
        json={"email": fan.email, "referral_code": f"nullh{tag}"},
    )
    assert enroll.status_code == 201, enroll.text
    amb_id = enroll.json()["id"]

    listed = client.get("/api/v1/promos/admin/ambassadors", headers=admin)
    assert listed.status_code == 200, listed.text
    row = next(r for r in listed.json() if r["id"] == amb_id)
    assert row["host_id"] is None
    assert row["program_kind"] == PROGRAM_PLATFORM_WIDE
    assert row["program_id"] == prog["id"]

    summary = client.get("/api/v1/promos/admin/reports/summary", headers=admin)
    assert summary.status_code == 200, summary.text
    settings = client.get("/api/v1/promos/admin/settings", headers=admin)
    assert settings.status_code == 200, settings.text
