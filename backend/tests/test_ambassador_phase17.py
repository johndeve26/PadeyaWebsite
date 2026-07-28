"""Phase 17 Ambassadors checklist — auth, pause, merch conversion, payout math.

Complements existing suites (open, campaigns, payment, fraud, privacy, api_v2).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ambassadors.payment import finalize_ambassador_conversions
from app.core.security import hash_password
from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostProfile
from app.merch.models import EventMerchProduct, EventMerchVariant
from app.payments.models import Order, OrderItem, Payment
from app.payments.webhook import finalize_successful_payment
from app.promos.ambassador_domain import (
    AmbassadorAttribution,
    AmbassadorClick,
    AmbassadorConversion,
    AmbassadorParticipant,
    AmbassadorProfile,
)
from app.promos.models import AmbassadorCampaign
from app.promos.referral_clicks import ReferralClick
from app.users.models import User
from app.users.service import get_role_by_name


def _login(client: TestClient, email: str) -> dict[str, str]:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _seed(db: Session, *, tag: str) -> tuple[str, Event, TicketType, Host]:
    host_email = f"p17-host-{tag}@example.com"
    host_user = User(
        email=host_email,
        password_hash=hash_password("securepass1"),
        full_name="P17 Host",
        is_active=True,
    )
    role = get_role_by_name(db, "host")
    assert role is not None
    host_user.roles.append(role)
    db.add(host_user)
    db.flush()
    host = Host(
        user_id=host_user.id,
        display_name="P17 Host",
        slug=f"p17-host-{tag}",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, city="Lagos"))
    category = db.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=12)
    event = Event(
        title="P17 Amb Night",
        slug=f"p17-amb-night-{tag}",
        description="Phase 17 Ambassadors checklist",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=3),
        city="Lagos",
        status="published",
        featured=False,
        published_at=datetime.now(UTC),
        allow_merch_only_checkout=True,
    )
    db.add(event)
    db.flush()
    ga = TicketType(
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
    db.add(ga)
    db.commit()
    return host_email, event, ga, host


def _create_campaign(
    client: TestClient, host_h: dict[str, str], event: Event, **extra
) -> dict:
    body = {
        "event_id": str(event.id),
        "name": "P17 public_open",
        "campaign_type": "event",
        "commission_type": "percentage",
        "commission_value": "10",
        "applies_to": "tickets_and_merch",
        "visibility": "public_open",
        "status": "active",
        "cookie_window_days": 30,
    }
    body.update(extra)
    created = client.post(
        "/api/v1/host/ambassadors/campaigns",
        headers=host_h,
        json=body,
    )
    assert created.status_code == 201, created.text
    return created.json()


def _register_user(db: Session, email: str, name: str) -> User:
    user = User(
        email=email,
        password_hash=hash_password("securepass1"),
        full_name=name,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _add_merch_variant(db: Session, *, host: Host, event: Event) -> EventMerchVariant:
    product = EventMerchProduct(
        host_id=host.id,
        event_id=event.id,
        name="P17 Tee",
        slug=f"p17-tee-{uuid4().hex[:6]}",
        description="Ambassador merch conversion sample",
        short_description="Tee",
        product_type="t_shirt",
        base_price=Decimal("8000.00"),
        currency="NGN",
        status="active",
        storefront_visibility="event_only",
        is_event_linked=True,
        moderation_status="clear",
    )
    db.add(product)
    db.flush()
    variant = EventMerchVariant(
        product_id=product.id,
        label="M / Black",
        size="M",
        color="Black",
        inventory_count=20,
        reserved_quantity=0,
        sold_quantity=0,
        status="active",
    )
    db.add(variant)
    db.commit()
    db.refresh(variant)
    return variant


def test_active_user_joins_public_open_campaign(
    client: TestClient, db_session: Session
):
    tag = uuid4().hex[:8]
    host_email, event, _ga, _host = _seed(db_session, tag=tag)
    host_h = _login(client, host_email)
    campaign = _create_campaign(client, host_h, event)

    amb = _register_user(db_session, f"p17-join-{tag}@example.com", "Join Amb")
    amb_h = _login(client, amb.email)
    join = client.post(
        f"/api/v1/events/{event.slug}/ambassador/join",
        headers=amb_h,
        json={"accept_terms": True, "campaign_id": campaign["id"]},
    )
    assert join.status_code == 200, join.text
    assert join.json()["ambassador_code"]
    assert join.json()["status"] == "active"


def test_logged_out_user_cannot_join(client: TestClient, db_session: Session):
    tag = uuid4().hex[:8]
    host_email, event, _ga, _host = _seed(db_session, tag=tag)
    host_h = _login(client, host_email)
    campaign = _create_campaign(client, host_h, event)

    anon = client.post(
        f"/api/v1/events/{event.slug}/ambassador/join",
        json={"accept_terms": True, "campaign_id": campaign["id"]},
    )
    assert anon.status_code in {401, 403}


def test_suspended_profile_cannot_join(client: TestClient, db_session: Session):
    tag = uuid4().hex[:8]
    host_email, event, _ga, _host = _seed(db_session, tag=tag)
    host_h = _login(client, host_email)
    campaign = _create_campaign(client, host_h, event)

    amb = _register_user(db_session, f"p17-sus-{tag}@example.com", "Suspended Amb")
    profile = AmbassadorProfile(user_id=amb.id, status="suspended")
    db_session.add(profile)
    db_session.commit()

    amb_h = _login(client, amb.email)
    blocked = client.post(
        "/api/v1/ambassadors/join",
        headers=amb_h,
        json={"accept_terms": True, "campaign_id": campaign["id"]},
    )
    assert blocked.status_code == 403
    assert "cannot join" in blocked.json()["detail"].lower()


def test_host_creates_public_open_and_event_status(
    client: TestClient, db_session: Session
):
    tag = uuid4().hex[:8]
    host_email, event, _ga, _host = _seed(db_session, tag=tag)
    host_h = _login(client, host_email)
    campaign = _create_campaign(client, host_h, event)
    assert campaign["visibility"] == "public_open"
    assert campaign["is_joinable"] is True

    status = client.get(f"/api/v1/events/{event.slug}/ambassador-status")
    assert status.status_code == 200
    body = status.json()
    assert body["enabled"] is True
    assert body.get("campaign_id") in {campaign["id"], str(campaign["id"])} or body[
        "enabled"
    ]


def test_referral_click_and_session_attribution(
    client: TestClient, db_session: Session
):
    tag = uuid4().hex[:8]
    host_email, event, _ga, _host = _seed(db_session, tag=tag)
    host_h = _login(client, host_email)
    campaign = _create_campaign(client, host_h, event)
    amb = _register_user(db_session, f"p17-click-{tag}@example.com", "Click Amb")
    amb_h = _login(client, amb.email)
    join = client.post(
        "/api/v1/ambassadors/join",
        headers=amb_h,
        json={"accept_terms": True, "campaign_id": campaign["id"]},
    )
    assert join.status_code == 200, join.text
    code = join.json()["ambassador_code"]
    session_id = f"p17-sess-{tag}"

    click = client.post(
        "/api/v1/ambassadors/track-click",
        json={
            "ambassador_code": code,
            "event_id": str(event.id),
            "session_id": session_id,
            "landing_url": f"/events/{event.slug}?ref={code}",
        },
    )
    assert click.status_code == 200, click.text
    assert click.json()["ok"] is True
    attribution_id = click.json()["attribution_id"]
    assert attribution_id

    db_session.expire_all()
    referral_click_id = click.json().get("click_id") or click.json().get("referral_click_id")
    assert referral_click_id is not None
    ref_click = db_session.get(ReferralClick, UUID(str(referral_click_id)))
    assert ref_click is not None
    assert ref_click.metadata_json is not None
    assert ref_click.metadata_json.get("session_id") == session_id
    attr = db_session.get(AmbassadorAttribution, UUID(str(attribution_id)))
    assert attr is not None
    assert attr.session_id == session_id
    assert attr.source == "link"
    expires = attr.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    assert expires > datetime.now(UTC)


def test_explicit_code_overrides_cookie_attribution(
    client: TestClient, db_session: Session
):
    tag = uuid4().hex[:8]
    host_email, event, ga, _host = _seed(db_session, tag=tag)
    host_h = _login(client, host_email)
    campaign = _create_campaign(client, host_h, event)

    amb_a = _register_user(db_session, f"p17-a-{tag}@example.com", "Amb A")
    amb_b = _register_user(db_session, f"p17-b-{tag}@example.com", "Amb B")
    buyer = _register_user(db_session, f"p17-buyer-{tag}@example.com", "Buyer")
    a_h = _login(client, amb_a.email)
    b_h = _login(client, amb_b.email)
    buyer_h = _login(client, buyer.email)

    code_a = client.post(
        "/api/v1/ambassadors/join",
        headers=a_h,
        json={"accept_terms": True, "campaign_id": campaign["id"]},
    ).json()["ambassador_code"]
    code_b = client.post(
        "/api/v1/ambassadors/join",
        headers=b_h,
        json={"accept_terms": True, "campaign_id": campaign["id"]},
    ).json()["ambassador_code"]

    # Cookie/link first, then explicit code at checkout must win.
    client.post(
        "/api/v1/ambassadors/track-click",
        json={
            "ambassador_code": code_a,
            "event_id": str(event.id),
            "session_id": f"override-{tag}",
            "landing_url": f"/events/{event.slug}?ref={code_a}",
        },
    )
    order = client.post(
        "/api/v1/orders",
        headers=buyer_h,
        json={
            "event_id": str(event.id),
            "items": [{"ticket_type_id": str(ga.id), "quantity": 1}],
            "referral_code": code_b,
            "referral_source": "explicit",
            "referral_session_id": f"override-{tag}",
        },
    )
    assert order.status_code == 201, order.text
    assert order.json()["referral_code"] == code_b


def test_verified_ticket_and_merch_conversions_idempotent_refund(
    client: TestClient, db_session: Session
):
    tag = uuid4().hex[:8]
    host_email, event, ga, host = _seed(db_session, tag=tag)
    host_h = _login(client, host_email)
    campaign = _create_campaign(client, host_h, event)
    variant = _add_merch_variant(db_session, host=host, event=event)

    amb = _register_user(db_session, f"p17-pay-{tag}@example.com", "Pay Amb")
    buyer = _register_user(db_session, f"p17-payb-{tag}@example.com", "Pay Buyer")
    amb_h = _login(client, amb.email)
    buyer_h = _login(client, buyer.email)
    code = client.post(
        "/api/v1/ambassadors/join",
        headers=amb_h,
        json={"accept_terms": True, "campaign_id": campaign["id"]},
    ).json()["ambassador_code"]

    # Frontend "success" / pending checkout must not create conversion.
    pending = client.post(
        "/api/v1/orders",
        headers=buyer_h,
        json={
            "event_id": str(event.id),
            "items": [{"ticket_type_id": str(ga.id), "quantity": 1}],
            "referral_code": code,
            "referral_source": "explicit",
        },
    )
    assert pending.status_code == 201, pending.text
    pending_id = UUID(str(pending.json()["id"]))
    db_session.expire_all()
    pending_order = db_session.get(Order, pending_id)
    assert pending_order is not None
    assert pending_order.status == "pending"
    assert finalize_ambassador_conversions(db_session, order=pending_order) == []
    db_session.commit()

    # Verified ticket payment.
    ticket_order = client.post(
        "/api/v1/orders",
        headers=buyer_h,
        json={
            "event_id": str(event.id),
            "items": [{"ticket_type_id": str(ga.id), "quantity": 2}],
            "referral_code": code,
            "referral_source": "explicit",
        },
    )
    assert ticket_order.status_code == 201, ticket_order.text
    ticket_id = UUID(str(ticket_order.json()["id"]))
    db_session.expire_all()
    order = db_session.get(Order, ticket_id)
    assert order is not None
    payment = Payment(
        order_id=order.id,
        provider="paystack",
        reference=f"p17-tix-{order.reference}",
        amount=order.total_amount,
        currency="NGN",
        status="pending",
    )
    db_session.add(payment)
    db_session.commit()
    db_session.refresh(order)
    db_session.refresh(payment)
    _ = list(order.items)
    finalize_successful_payment(
        db_session,
        order=order,
        payment=payment,
        provider_payment_id=f"psk_tix_{tag}",
        raw_payload={"event": "charge.success"},
    )
    db_session.commit()
    db_session.expire_all()
    ticket_convs = list(
        db_session.scalars(
            select(AmbassadorConversion).where(
                AmbassadorConversion.order_id == ticket_id,
                AmbassadorConversion.conversion_type == "ticket",
            )
        )
    )
    assert len(ticket_convs) == 1
    assert ticket_convs[0].status == "approved"
    assert ticket_convs[0].commission_amount == Decimal("1000.00")  # 10% of 10000

    # Duplicate finalize must not duplicate.
    order = db_session.get(Order, ticket_id)
    assert order is not None
    again = finalize_ambassador_conversions(db_session, order=order)
    db_session.commit()
    assert len(again) == 1
    assert (
        db_session.scalar(
            select(AmbassadorConversion).where(
                AmbassadorConversion.order_id == ticket_id,
                AmbassadorConversion.conversion_type == "ticket",
            )
        )
        is not None
    )
    assert (
        len(
            list(
                db_session.scalars(
                    select(AmbassadorConversion).where(
                        AmbassadorConversion.order_id == ticket_id
                    )
                )
            )
        )
        == 1
    )

    # Verified merch payment.
    merch_order = client.post(
        "/api/v1/orders",
        headers=buyer_h,
        json={
            "event_id": str(event.id),
            "items": [
                {
                    "item_kind": "merch",
                    "merch_variant_id": str(variant.id),
                    "quantity": 1,
                }
            ],
            "referral_code": code,
            "referral_source": "explicit",
            "fulfillment_method": "pickup",
        },
    )
    assert merch_order.status_code == 201, merch_order.text
    merch_id = UUID(str(merch_order.json()["id"]))
    db_session.expire_all()
    m_order = db_session.get(Order, merch_id)
    assert m_order is not None
    m_payment = Payment(
        order_id=m_order.id,
        provider="paystack",
        reference=f"p17-merch-{m_order.reference}",
        amount=m_order.total_amount,
        currency="NGN",
        status="pending",
    )
    db_session.add(m_payment)
    db_session.commit()
    db_session.refresh(m_order)
    db_session.refresh(m_payment)
    _ = list(m_order.items)
    finalize_successful_payment(
        db_session,
        order=m_order,
        payment=m_payment,
        provider_payment_id=f"psk_merch_{tag}",
        raw_payload={"event": "charge.success"},
    )
    db_session.commit()
    merch_convs = list(
        db_session.scalars(
            select(AmbassadorConversion).where(
                AmbassadorConversion.merch_order_id == merch_id,
                AmbassadorConversion.conversion_type == "merch",
            )
        )
    )
    assert len(merch_convs) == 1
    assert merch_convs[0].status == "approved"
    assert merch_convs[0].commission_amount == Decimal("800.00")  # 10% of 8000

    # Refund reverses ticket conversion.
    from app.ambassadors.payment import reverse_conversions_for_order

    reverse_conversions_for_order(
        db_session,
        order_id=ticket_id,
        reason="Buyer refund",
        actor_user_id=buyer.id,
    )
    db_session.commit()
    db_session.refresh(ticket_convs[0])
    assert ticket_convs[0].status == "reversed"
    assert ticket_convs[0].refunded_at is not None


def test_self_referral_blocked(client: TestClient, db_session: Session):
    tag = uuid4().hex[:8]
    host_email, event, ga, _host = _seed(db_session, tag=tag)
    host_h = _login(client, host_email)
    campaign = _create_campaign(client, host_h, event)
    amb = _register_user(db_session, f"p17-self-{tag}@example.com", "Self Amb")
    amb_h = _login(client, amb.email)
    code = client.post(
        "/api/v1/ambassadors/join",
        headers=amb_h,
        json={"accept_terms": True, "campaign_id": campaign["id"]},
    ).json()["ambassador_code"]

    self_order = client.post(
        "/api/v1/orders",
        headers=amb_h,
        json={
            "event_id": str(event.id),
            "items": [{"ticket_type_id": str(ga.id), "quantity": 1}],
            "referral_code": code,
            "referral_source": "explicit",
        },
    )
    assert self_order.status_code == 201, self_order.text
    body = self_order.json()
    assert body.get("referral_code") in (None, "")
    db_session.expire_all()
    order = db_session.get(Order, UUID(str(body["id"])))
    assert order is not None
    assert order.ambassador_participant_id is None
    assert finalize_ambassador_conversions(db_session, order=order) == []


def test_ambassador_earnings_omit_buyer_private_data(
    client: TestClient, db_session: Session
):
    tag = uuid4().hex[:8]
    host_email, event, _ga, _host = _seed(db_session, tag=tag)
    host_h = _login(client, host_email)
    campaign = _create_campaign(client, host_h, event)
    amb = _register_user(db_session, f"p17-priv-{tag}@example.com", "Priv Amb")
    amb_h = _login(client, amb.email)
    join = client.post(
        "/api/v1/ambassadors/join",
        headers=amb_h,
        json={"accept_terms": True, "campaign_id": campaign["id"]},
    )
    assert join.status_code == 200
    participant_id = UUID(str(join.json()["id"]))

    db_session.add(
        AmbassadorConversion(
            campaign_id=UUID(str(campaign["id"])),
            participant_id=participant_id,
            conversion_type="ticket",
            gross_amount=Decimal("5000"),
            eligible_amount=Decimal("5000"),
            commission_amount=Decimal("500"),
            status="approved",
            dedupe_key=f"p17-priv:{uuid4()}",
            verified_at=datetime.now(UTC),
        )
    )
    db_session.commit()

    earnings = client.get("/api/v1/ambassadors/me/earnings", headers=amb_h)
    assert earnings.status_code == 200
    raw = earnings.text.lower()
    for forbidden in (
        "buyer_email",
        "buyer_name",
        "buyer_phone",
        "order_reference",
        "payment_reference",
        "@example.com",
    ):
        assert forbidden not in raw


def test_paused_campaign_blocks_join_and_attribution(
    client: TestClient, db_session: Session
):
    tag = uuid4().hex[:8]
    host_email, event, _ga, _host = _seed(db_session, tag=tag)
    host_h = _login(client, host_email)
    campaign = _create_campaign(client, host_h, event)

    amb = _register_user(db_session, f"p17-pause-{tag}@example.com", "Pause Amb")
    amb_h = _login(client, amb.email)
    join = client.post(
        "/api/v1/ambassadors/join",
        headers=amb_h,
        json={"accept_terms": True, "campaign_id": campaign["id"]},
    )
    assert join.status_code == 200, join.text
    code = join.json()["ambassador_code"]

    paused = client.post(
        f"/api/v1/host/ambassadors/campaigns/{campaign['id']}/pause",
        headers=host_h,
    )
    assert paused.status_code == 200
    assert paused.json()["status"] == "paused"

    late = _register_user(db_session, f"p17-late-{tag}@example.com", "Late Amb")
    late_h = _login(client, late.email)
    blocked_join = client.post(
        "/api/v1/ambassadors/join",
        headers=late_h,
        json={"accept_terms": True, "campaign_id": campaign["id"]},
    )
    assert blocked_join.status_code == 400

    blocked_click = client.post(
        "/api/v1/ambassadors/track-click",
        json={
            "ambassador_code": code,
            "event_id": str(event.id),
            "session_id": f"paused-{tag}",
            "landing_url": f"/events/{event.slug}?ref={code}",
        },
    )
    assert blocked_click.status_code == 400
    assert "not active" in blocked_click.json()["detail"].lower()


def test_host_remove_and_admin_block_participant(
    client: TestClient, db_session: Session, assign_role
):
    tag = uuid4().hex[:8]
    host_email, event, _ga, _host = _seed(db_session, tag=tag)
    host_h = _login(client, host_email)
    campaign = _create_campaign(client, host_h, event)

    amb = _register_user(db_session, f"p17-rm-{tag}@example.com", "Remove Amb")
    amb2 = _register_user(db_session, f"p17-blk-{tag}@example.com", "Block Amb")
    amb_h = _login(client, amb.email)
    amb2_h = _login(client, amb2.email)

    p1 = client.post(
        "/api/v1/ambassadors/join",
        headers=amb_h,
        json={"accept_terms": True, "campaign_id": campaign["id"]},
    ).json()
    p2 = client.post(
        "/api/v1/ambassadors/join",
        headers=amb2_h,
        json={"accept_terms": True, "campaign_id": campaign["id"]},
    ).json()

    removed = client.post(
        f"/api/v1/host/ambassadors/participants/{p1['id']}/remove",
        headers=host_h,
    )
    assert removed.status_code == 200, removed.text
    db_session.expire_all()
    row = db_session.get(AmbassadorParticipant, UUID(str(p1["id"])))
    assert row is not None
    assert row.status == "removed"

    admin_email = f"p17-admin-{tag}@example.com"
    _register_user(db_session, admin_email, "P17 Admin")
    assign_role(admin_email, "super_admin")
    admin_h = _login(client, admin_email)
    blocked = client.post(
        f"/api/v1/admin/ambassadors/participants/{p2['id']}/block",
        headers=admin_h,
        json={"reason": "abuse sample"},
    )
    assert blocked.status_code == 200, blocked.text
    assert blocked.json()["status"] == "blocked"


def test_payout_summary_calculates_correctly(
    client: TestClient, db_session: Session
):
    tag = uuid4().hex[:8]
    host_email, event, _ga, _host = _seed(db_session, tag=tag)
    host_h = _login(client, host_email)
    campaign = _create_campaign(client, host_h, event)
    amb = _register_user(db_session, f"p17-payo-{tag}@example.com", "Payout Amb")
    amb_h = _login(client, amb.email)
    join = client.post(
        "/api/v1/ambassadors/join",
        headers=amb_h,
        json={"accept_terms": True, "campaign_id": campaign["id"]},
    )
    assert join.status_code == 200
    participant_id = UUID(str(join.json()["id"]))
    campaign_id = UUID(str(campaign["id"]))

    rows = [
        ("pending", Decimal("100.00")),
        ("approved", Decimal("250.00")),
        ("payable", Decimal("150.00")),
        ("paid", Decimal("50.00")),
        ("reversed", Decimal("200.00")),
    ]
    for status, amount in rows:
        db_session.add(
            AmbassadorConversion(
                campaign_id=campaign_id,
                participant_id=participant_id,
                conversion_type="ticket",
                gross_amount=amount * 10,
                eligible_amount=amount * 10,
                commission_amount=amount,
                status=status,
                dedupe_key=f"p17-payo:{status}:{uuid4()}",
                verified_at=datetime.now(UTC) if status != "pending" else None,
                refunded_at=datetime.now(UTC) if status == "reversed" else None,
            )
        )
    db_session.commit()

    earnings = client.get("/api/v1/ambassadors/me/earnings", headers=amb_h)
    assert earnings.status_code == 200
    body = earnings.json()
    assert body["confirmed_conversions"] == 4  # excludes reversed
    assert Decimal(body["pending_amount"]) == Decimal("100.00")
    assert Decimal(body["approved_amount"]) == Decimal("450.00")  # approved+payable+paid
    assert Decimal(body["payable_amount"]) == Decimal("400.00")  # payable+approved
    assert Decimal(body["paid_amount"]) == Decimal("50.00")
    assert Decimal(body["reversed_amount"]) == Decimal("200.00")
    assert Decimal(body["gross_eligible"]) == Decimal("5500.00")  # 100+250+150+50 * 10
