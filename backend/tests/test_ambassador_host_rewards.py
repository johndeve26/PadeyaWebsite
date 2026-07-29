"""Host owner / team reward approval for host-owned Ambassador campaigns."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from sqlalchemy import select

from app.core.audit import AuditLog
from app.core.security import hash_password
from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostProfile, HostTeamMember
from app.hosts.team_permissions import pack_scope_json, permissions_for_role
from app.messaging.models import InAppNotification
from app.payments.models import Order
from app.promos.models import Ambassador, AmbassadorCampaign, AmbassadorSale
from app.users.models import User
from app.users.service import get_role_by_name


def _login(client: TestClient, email: str) -> dict[str, str]:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _register(client: TestClient, email: str, name: str) -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass1", "full_name": name, "gender": "prefer_not_to_say"},
    )
    return _login(client, email)


def _seed_host_campaign(db: Session, *, suffix: str) -> tuple[Host, Event, Ambassador, AmbassadorSale]:
    host_user = User(
        email=f"rew-host-{suffix}@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Reward Host",
        is_active=True,
    )
    role = get_role_by_name(db, "host")
    assert role is not None
    host_user.roles.append(role)
    db.add(host_user)
    db.flush()
    host = Host(
        user_id=host_user.id,
        display_name=f"Reward Host {suffix}",
        slug=f"reward-host-{suffix}",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, city="Lagos"))
    category = db.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=10)
    event = Event(
        title=f"Reward Night {suffix}",
        slug=f"reward-night-{suffix}",
        description="Host reward test event.",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=4),
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
            price=Decimal("5000.00"),
            quantity=100,
            quantity_sold=0,
            quantity_reserved=0,
            min_per_order=1,
            max_per_order=5,
            visibility="public",
            status="active",
        )
    )
    campaign = AmbassadorCampaign(
        host_id=host.id,
        event_id=event.id,
        name="Host Ambassadors",
        status="public_open",
        source="host",
        campaign_type="event_tickets",
        commission_percent=Decimal("5.00"),
        commission_type="percentage",
        commission_value=Decimal("5.00"),
        applies_to="tickets",
        hold_period_days=0,
    )
    db.add(campaign)
    db.flush()

    amb_user = User(
        email=f"rew-amb-{suffix}@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Amb User",
        is_active=True,
    )
    db.add(amb_user)
    db.flush()
    amb = Ambassador(
        host_id=host.id,
        event_id=event.id,
        campaign_id=campaign.id,
        user_id=amb_user.id,
        program_kind="open_event",
        referral_code=f"REW{suffix.upper()[:6]}",
        display_name="Amb User",
        status="active",
    )
    db.add(amb)
    db.flush()

    buyer = User(
        email=f"rew-buyer-{suffix}@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Buyer",
        is_active=True,
    )
    db.add(buyer)
    db.flush()
    order = Order(
        event_id=event.id,
        buyer_user_id=buyer.id,
        buyer_email=buyer.email,
        buyer_name=buyer.full_name,
        status="paid",
        currency="NGN",
        subtotal_amount=Decimal("5000"),
        discount_amount=Decimal("0"),
        total_amount=Decimal("5000"),
        reference=f"ref-{uuid4().hex[:10]}",
    )
    db.add(order)
    db.flush()
    sale = AmbassadorSale(
        ambassador_id=amb.id,
        order_id=order.id,
        event_id=event.id,
        tickets_sold=1,
        merch_units_sold=0,
        revenue_amount=Decimal("5000"),
        commission_owed=Decimal("250"),
        status="attributed",
        hold_until=None,
    )
    db.add(sale)
    db.commit()
    return host, event, amb, sale


def test_host_owner_can_approve_reject_and_mark_paid(
    client: TestClient, db_session: Session
):
    host, event, amb, sale = _seed_host_campaign(db_session, suffix="own")
    host_h = _login(client, "rew-host-own@example.com")

    approved = client.post(
        f"/api/v1/host/ambassadors/conversions/{sale.id}/reward-status",
        headers=host_h,
        json={"status": "approved"},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"

    # Idempotent approve
    again = client.post(
        f"/api/v1/host/ambassadors/conversions/{sale.id}/reward-status",
        headers=host_h,
        json={"status": "approved"},
    )
    assert again.status_code == 200
    assert again.json()["status"] == "approved"

    # Reject requires reason
    missing = client.post(
        f"/api/v1/host/ambassadors/conversions/{sale.id}/reward-status",
        headers=host_h,
        json={"status": "rejected"},
    )
    assert missing.status_code == 400

    rejected = client.post(
        f"/api/v1/host/ambassadors/conversions/{sale.id}/reward-status",
        headers=host_h,
        json={"status": "rejected", "reason": "Does not meet campaign rules"},
    )
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["status"] == "rejected"
    assert rejected.json()["rejection_reason"]

    # Fresh sale → approve → paid with payout meta
    buyer2 = User(
        email="rew-buyer2-own@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Buyer2",
        is_active=True,
    )
    db_session.add(buyer2)
    db_session.flush()
    order2 = Order(
        event_id=event.id,
        buyer_user_id=buyer2.id,
        buyer_email=buyer2.email,
        buyer_name=buyer2.full_name,
        status="paid",
        currency="NGN",
        subtotal_amount=Decimal("5000"),
        discount_amount=Decimal("0"),
        total_amount=Decimal("5000"),
        reference=f"ref-{uuid4().hex[:10]}",
    )
    db_session.add(order2)
    db_session.flush()
    sale2 = AmbassadorSale(
        ambassador_id=amb.id,
        order_id=order2.id,
        event_id=event.id,
        tickets_sold=1,
        merch_units_sold=0,
        revenue_amount=Decimal("5000"),
        commission_owed=Decimal("250"),
        status="attributed",
        hold_until=None,
    )
    db_session.add(sale2)
    db_session.commit()

    assert (
        client.post(
            f"/api/v1/host/ambassadors/conversions/{sale2.id}/reward-status",
            headers=host_h,
            json={"status": "approved"},
        ).status_code
        == 200
    )
    paid = client.post(
        f"/api/v1/host/ambassadors/conversions/{sale2.id}/reward-status",
        headers=host_h,
        json={
            "status": "paid",
            "payout_reference": "TRF-123",
            "payout_note": "Bank transfer completed",
        },
    )
    assert paid.status_code == 200, paid.text
    body = paid.json()
    assert body["status"] == "paid"
    assert body["payout_reference"] == "TRF-123"
    assert body["payout_note"] == "Bank transfer completed"
    assert host.id

    approved_audit = db_session.scalars(
        select(AuditLog).where(
            AuditLog.action == "ambassador_reward_approved",
            AuditLog.resource_id == str(sale2.id),
        )
    ).first()
    assert approved_audit is not None
    details = approved_audit.details or {}
    assert details["actor_type"] == "host_owner"
    assert details["host_profile_id"] == str(host.id)
    assert details["old_status"] == "attributed"
    assert details["new_status"] == "approved"
    assert details["conversion_id"] == str(sale2.id)

    paid_audit = db_session.scalars(
        select(AuditLog).where(
            AuditLog.action == "ambassador_reward_marked_paid",
            AuditLog.resource_id == str(sale2.id),
        )
    ).first()
    assert paid_audit is not None
    assert (paid_audit.details or {}).get("payout_reference") == "TRF-123"

    audit_list = client.get(
        f"/api/v1/host/ambassadors/reward-audit?host_id={host.id}",
        headers=host_h,
    )
    assert audit_list.status_code == 200, audit_list.text
    actions = {row["action"] for row in audit_list.json()}
    assert "ambassador_reward_approved" in actions
    assert "ambassador_reward_marked_paid" in actions

    amb_notif = (
        db_session.query(InAppNotification)
        .filter(InAppNotification.kind == "ambassador.reward_approved")
        .all()
    )
    assert amb_notif
    assert "Reward Night" in (amb_notif[0].body or "")
    assert "@example.com" not in (amb_notif[0].body or "")


def test_team_member_needs_permission_and_cannot_self_approve(
    client: TestClient, db_session: Session
):
    host, _event, amb, sale = _seed_host_campaign(db_session, suffix="tm")
    host_h = _login(client, "rew-host-tm@example.com")

    # Team member without reward permission
    member_h = _register(client, "rew-tm@example.com", "Team Member")
    member = db_session.query(User).filter_by(email="rew-tm@example.com").one()
    perms = permissions_for_role("event_manager")
    assert perms["ambassadors.approve_rewards"] is False
    db_session.add(
        HostTeamMember(
            host_id=host.id,
            user_id=member.id,
            role="event_manager",
            role_label="Event Manager",
            status="active",
            permissions_json=perms,
            scope_json=pack_scope_json("host_wide"),
            joined_at=datetime.now(UTC),
        )
    )
    db_session.commit()

    denied = client.post(
        f"/api/v1/host/ambassadors/conversions/{sale.id}/reward-status"
        f"?host_id={host.id}",
        headers=member_h,
        json={"status": "approved"},
    )
    assert denied.status_code == 403, denied.text

    # Grant approve
    row = db_session.query(HostTeamMember).filter_by(user_id=member.id).one()
    perms["ambassadors.approve_rewards"] = True
    row.permissions_json = perms
    db_session.commit()

    ok = client.post(
        f"/api/v1/host/ambassadors/conversions/{sale.id}/reward-status"
        f"?host_id={host.id}",
        headers=member_h,
        json={"status": "approved"},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["status"] == "approved"

    team_audit = db_session.scalars(
        select(AuditLog).where(
            AuditLog.action == "ambassador_reward_approved",
            AuditLog.resource_id == str(sale.id),
        )
    ).first()
    assert team_audit is not None
    assert (team_audit.details or {}).get("actor_type") == "team_member"

    host_team_notif = (
        db_session.query(InAppNotification)
        .filter(InAppNotification.kind == "host.ambassador_team_reward")
        .all()
    )
    assert host_team_notif
    assert "team member" in (host_team_notif[0].body or "").lower()

    # Ambassador cannot approve own reward
    amb_h = _login(client, "rew-amb-tm@example.com")
    # Make ambassador a team member with approve (still blocked for self)
    amb_user = db_session.get(User, amb.user_id)
    assert amb_user is not None
    self_perms = permissions_for_role("admin")
    self_perms["ambassadors.approve_rewards"] = True
    db_session.add(
        HostTeamMember(
            host_id=host.id,
            user_id=amb_user.id,
            role="admin",
            role_label="Admin",
            status="active",
            permissions_json=self_perms,
            scope_json=pack_scope_json("host_wide"),
            joined_at=datetime.now(UTC),
        )
    )
    db_session.commit()

    # Create a fresh attributed sale for self-approve attempt
    buyer2 = User(
        email="rew-buyer2-tm@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Buyer2",
        is_active=True,
    )
    db_session.add(buyer2)
    db_session.flush()
    order2 = Order(
        event_id=sale.event_id,
        buyer_user_id=buyer2.id,
        buyer_email=buyer2.email,
        buyer_name=buyer2.full_name,
        status="paid",
        currency="NGN",
        subtotal_amount=Decimal("5000"),
        discount_amount=Decimal("0"),
        total_amount=Decimal("5000"),
        reference=f"ref-{uuid4().hex[:10]}",
    )
    db_session.add(order2)
    db_session.flush()
    sale2 = AmbassadorSale(
        ambassador_id=amb.id,
        order_id=order2.id,
        event_id=sale.event_id,
        tickets_sold=1,
        merch_units_sold=0,
        revenue_amount=Decimal("5000"),
        commission_owed=Decimal("250"),
        status="attributed",
        hold_until=None,
    )
    db_session.add(sale2)
    db_session.commit()

    self_deny = client.post(
        f"/api/v1/host/ambassadors/conversions/{sale2.id}/reward-status"
        f"?host_id={host.id}",
        headers=amb_h,
        json={"status": "approved"},
    )
    assert self_deny.status_code == 403
    assert "own reward" in self_deny.json()["detail"].lower()

    # Suspended team member loses access on a fresh attributed sale
    sale2.status = "attributed"
    row.status = "suspended"
    db_session.commit()
    suspended = client.post(
        f"/api/v1/host/ambassadors/conversions/{sale2.id}/reward-status"
        f"?host_id={host.id}",
        headers=member_h,
        json={"status": "approved"},
    )
    assert suspended.status_code == 403

    # Host can reverse (approved, not paid)
    rev = client.post(
        f"/api/v1/host/ambassadors/conversions/{sale.id}/reverse",
        headers=host_h,
        json={"reason": "Suspected fraud pattern"},
    )
    assert rev.status_code == 200, rev.text
    assert rev.json()["status"] == "reversed"


def test_mark_paid_via_finance_manage_payouts(
    client: TestClient, db_session: Session
):
    host, _event, _amb, sale = _seed_host_campaign(db_session, suffix="fin")
    host_h = _login(client, "rew-host-fin@example.com")
    # Host approves first
    assert (
        client.post(
            f"/api/v1/host/ambassadors/conversions/{sale.id}/reward-status",
            headers=host_h,
            json={"status": "approved"},
        ).status_code
        == 200
    )

    member_h = _register(client, "rew-fin-tm@example.com", "Finance TM")
    member = db_session.query(User).filter_by(email="rew-fin-tm@example.com").one()
    perms = permissions_for_role("viewer")
    perms["finance.manage_payouts"] = True
    db_session.add(
        HostTeamMember(
            host_id=host.id,
            user_id=member.id,
            role="viewer",
            role_label="Viewer",
            status="active",
            permissions_json=perms,
            scope_json=pack_scope_json("host_wide"),
            joined_at=datetime.now(UTC),
        )
    )
    db_session.commit()

    paid = client.post(
        f"/api/v1/host/ambassadors/conversions/{sale.id}/reward-status"
        f"?host_id={host.id}",
        headers=member_h,
        json={"status": "paid"},
    )
    assert paid.status_code == 200, paid.text
    assert paid.json()["status"] == "paid"

    export = client.get(
        f"/api/v1/host/ambassadors/conversions/export?host_id={host.id}",
        headers=member_h,
    )
    # export needs ambassadors.export OR finance.view_payouts — not manage_payouts alone
    assert export.status_code == 403

    row = db_session.query(HostTeamMember).filter_by(user_id=member.id).one()
    perms["finance.view_payouts"] = True
    row.permissions_json = perms
    db_session.commit()
    export_ok = client.get(
        f"/api/v1/host/ambassadors/conversions/export?host_id={host.id}",
        headers=member_h,
    )
    assert export_ok.status_code == 200, export_ok.text
    assert "commission_owed" in export_ok.text


def test_platform_campaign_rewards_admin_only(
    client: TestClient, db_session: Session, assign_role
):
    host, event, amb, sale = _seed_host_campaign(db_session, suffix="plat")
    campaign = db_session.get(AmbassadorCampaign, amb.campaign_id)
    assert campaign is not None
    campaign.source = "platform"
    db_session.commit()

    host_h = _login(client, "rew-host-plat@example.com")
    denied = client.post(
        f"/api/v1/host/ambassadors/conversions/{sale.id}/reward-status",
        headers=host_h,
        json={"status": "approved"},
    )
    assert denied.status_code == 403

    client.post(
        "/api/v1/auth/register",
        json={
            "email": "rew-admin@example.com",
            "password": "securepass1",
            "full_name": "Admin",
        "gender": "prefer_not_to_say"},
    )
    assign_role("rew-admin@example.com", "super_admin")
    admin_h = _login(client, "rew-admin@example.com")
    ok = client.post(
        f"/api/v1/promos/admin/conversions/{sale.id}/reward-status",
        headers=admin_h,
        json={"status": "approved"},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["status"] == "approved"
    admin_audit = db_session.scalars(
        select(AuditLog).where(
            AuditLog.action == "ambassador_reward_status_changed_by_admin",
            AuditLog.resource_id == str(sale.id),
        )
    ).first()
    assert admin_audit is not None
    assert event.id


def test_cannot_approve_another_hosts_campaign(
    client: TestClient, db_session: Session
):
    host_a, _e, _amb, sale_a = _seed_host_campaign(db_session, suffix="xa")
    host_b, _e2, _amb2, _sale_b = _seed_host_campaign(db_session, suffix="xb")
    host_b_h = _login(client, "rew-host-xb@example.com")
    denied = client.post(
        f"/api/v1/host/ambassadors/conversions/{sale_a.id}/reward-status"
        f"?host_id={host_b.id}",
        headers=host_b_h,
        json={"status": "approved"},
    )
    assert denied.status_code in {403, 404}
    assert host_a.id != host_b.id


def test_mark_rewards_paid_permission_gate(
    client: TestClient, db_session: Session
):
    host, _event, _amb, sale = _seed_host_campaign(db_session, suffix="mp")
    host_h = _login(client, "rew-host-mp@example.com")
    assert (
        client.post(
            f"/api/v1/host/ambassadors/conversions/{sale.id}/reward-status",
            headers=host_h,
            json={"status": "approved"},
        ).status_code
        == 200
    )

    member_h = _register(client, "rew-mp-tm@example.com", "Mark Paid TM")
    member = db_session.query(User).filter_by(email="rew-mp-tm@example.com").one()
    perms = permissions_for_role("viewer")
    perms["ambassadors.view_conversions"] = True
    db_session.add(
        HostTeamMember(
            host_id=host.id,
            user_id=member.id,
            role="viewer",
            role_label="Viewer",
            status="active",
            permissions_json=perms,
            scope_json=pack_scope_json("host_wide"),
            joined_at=datetime.now(UTC),
        )
    )
    db_session.commit()

    denied = client.post(
        f"/api/v1/host/ambassadors/conversions/{sale.id}/reward-status"
        f"?host_id={host.id}",
        headers=member_h,
        json={"status": "paid"},
    )
    assert denied.status_code == 403

    row = db_session.query(HostTeamMember).filter_by(user_id=member.id).one()
    perms["ambassadors.mark_rewards_paid"] = True
    row.permissions_json = perms
    db_session.commit()

    paid = client.post(
        f"/api/v1/host/ambassadors/conversions/{sale.id}/reward-status"
        f"?host_id={host.id}",
        headers=member_h,
        json={"status": "paid", "payout_reference": "PAY-1"},
    )
    assert paid.status_code == 200, paid.text
    assert paid.json()["status"] == "paid"
    assert "order_id" not in paid.json() or paid.json().get("order_id") is None

    paid_notif = (
        db_session.query(InAppNotification)
        .filter(InAppNotification.kind == "ambassador.reward_marked_paid")
        .all()
    )
    assert paid_notif


def test_reverse_without_reason_rejected(
    client: TestClient, db_session: Session
):
    host, _e, _amb, sale = _seed_host_campaign(db_session, suffix="rr")
    host_h = _login(client, "rew-host-rr@example.com")
    assert (
        client.post(
            f"/api/v1/host/ambassadors/conversions/{sale.id}/reward-status",
            headers=host_h,
            json={"status": "approved"},
        ).status_code
        == 200
    )
    missing = client.post(
        f"/api/v1/host/ambassadors/conversions/{sale.id}/reward-status",
        headers=host_h,
        json={"status": "reversed"},
    )
    assert missing.status_code == 400
    short = client.post(
        f"/api/v1/host/ambassadors/conversions/{sale.id}/reward-status",
        headers=host_h,
        json={"status": "reversed", "reason": "no"},
    )
    assert short.status_code == 400


def test_pending_order_cannot_be_approved(
    client: TestClient, db_session: Session
):
    host, _e, amb, sale = _seed_host_campaign(db_session, suffix="pend")
    order = db_session.get(Order, sale.order_id)
    assert order is not None
    order.status = "pending"
    db_session.commit()
    host_h = _login(client, "rew-host-pend@example.com")
    denied = client.post(
        f"/api/v1/host/ambassadors/conversions/{sale.id}/reward-status",
        headers=host_h,
        json={"status": "approved"},
    )
    assert denied.status_code == 400
    assert amb.id


def test_refunded_order_cannot_be_marked_paid(
    client: TestClient, db_session: Session
):
    host, _e, _amb, sale = _seed_host_campaign(db_session, suffix="ref")
    host_h = _login(client, "rew-host-ref@example.com")
    assert (
        client.post(
            f"/api/v1/host/ambassadors/conversions/{sale.id}/reward-status",
            headers=host_h,
            json={"status": "approved"},
        ).status_code
        == 200
    )
    order = db_session.get(Order, sale.order_id)
    assert order is not None
    order.status = "refunded"
    db_session.commit()
    denied = client.post(
        f"/api/v1/host/ambassadors/conversions/{sale.id}/reward-status",
        headers=host_h,
        json={"status": "paid"},
    )
    assert denied.status_code == 400


def test_host_conversion_dto_hides_buyer_private_data(
    client: TestClient, db_session: Session
):
    host, _e, _amb, sale = _seed_host_campaign(db_session, suffix="priv")
    host_h = _login(client, "rew-host-priv@example.com")
    listed = client.get(
        f"/api/v1/host/ambassadors/conversions?host_id={host.id}",
        headers=host_h,
    )
    assert listed.status_code == 200, listed.text
    rows = listed.json()
    assert rows
    row = next(r for r in rows if r["id"] == str(sale.id))
    for forbidden in (
        "order_id",
        "order_reference",
        "payment_reference",
        "buyer_email",
        "buyer_phone",
        "shipping_address",
        "ticket_qr",
        "pickup_qr",
        "attendees",
        "fan_connect",
        "address",
    ):
        assert forbidden not in row or row.get(forbidden) in (None, "")
    assert row.get("ambassador_display_name")
    assert row.get("campaign_id")
    assert row.get("eligible_sale_amount") is not None
    assert row.get("commission_owed") is not None
    assert row.get("status")
    assert row.get("payout_status")
    assert row.get("created_at")

    flagged = client.post(
        f"/api/v1/host/ambassadors/conversions/{sale.id}/flag"
        f"?host_id={host.id}",
        headers=host_h,
        json={"reason": "Pattern looks like self-referral ring"},
    )
    assert flagged.status_code == 200, flagged.text
    assert flagged.json()["flag_type"] == "suspicious_conversion"
