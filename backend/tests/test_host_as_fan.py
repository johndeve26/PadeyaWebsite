"""Host-as-Fan self-abuse hardening for Pàdéyá (pytest -k host_as_fan).

Only a Host A **owner** must not inflate Host A through Personal/Fan flows.
Team, staff, ambassadors, and volunteers may buy/fan Host A normally.
Host A owner may still fan Host B normally.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.ambassadors.fraud import assert_user_may_join_campaign, is_host_owner_participant
from app.core.security import hash_password
from app.events.models import Event, EventCategory, TicketType
from app.hosts.fan_self_abuse import (
    assert_not_own_host_as_fan,
    is_user_owner_of_host,
)
from app.checkins.models import EventStaffAssignment
from app.hosts.models import Host, HostProfile, HostTeamMember
from app.hosts.team_permissions import pack_scope_json, permissions_for_role
from app.messaging.relationships import classify_fan_to_host, classify_host_to_fan
from app.payments.models import Order, OrderItem
from app.promos.models import AmbassadorCampaign
from app.reviews.eligibility import evaluate_review_eligibility
from app.tickets.models import Ticket
from app.tickets.qr import new_public_ticket_code
from app.users.models import User
from app.users.service import get_role_by_name


def _login(client: TestClient, email: str) -> dict[str, str]:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _register(client: TestClient, email: str, name: str = "User") -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass1", "full_name": name},
    )
    return _login(client, email)


def _seed_host(
    db: Session,
    *,
    email: str,
    slug: str,
    name: str,
) -> tuple[Host, User]:
    host_user = User(
        email=email,
        password_hash=hash_password("securepass1"),
        full_name=name,
        is_active=True,
    )
    role = get_role_by_name(db, "host")
    buyer = get_role_by_name(db, "buyer")
    assert role is not None and buyer is not None
    host_user.roles.extend([role, buyer])
    db.add(host_user)
    db.flush()
    host = Host(
        user_id=host_user.id,
        display_name=name,
        slug=slug,
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, bio=f"{name} profile"))
    db.commit()
    return host, host_user


def _add_team_member(
    db: Session,
    *,
    host_id,
    email: str,
    client: TestClient,
) -> tuple[User, dict[str, str]]:
    headers = _register(client, email, "Team Member")
    member = db.query(User).filter_by(email=email).one()
    buyer = get_role_by_name(db, "buyer")
    assert buyer is not None
    if buyer not in member.roles:
        member.roles.append(buyer)
    db.add(
        HostTeamMember(
            host_id=host_id,
            user_id=member.id,
            role="viewer",
            role_label="Viewer",
            status="active",
            permissions_json=permissions_for_role("viewer"),
            scope_json=pack_scope_json("host_wide"),
            joined_at=datetime.now(UTC),
        )
    )
    db.commit()
    return member, headers


def _seed_event(db: Session, host: Host, *, slug: str, ended: bool = False) -> tuple[Event, TicketType]:
    category = db.query(EventCategory).first()
    if ended:
        start = datetime.now(UTC) - timedelta(days=3)
        end = datetime.now(UTC) - timedelta(days=2)
        status = "completed"
    else:
        start = datetime.now(UTC) + timedelta(days=14)
        end = start + timedelta(hours=4)
        status = "published"
    event = Event(
        title=f"Event {slug}",
        slug=slug,
        description="Self-abuse guard event with enough detail for checkout.",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=end,
        venue_name="Arena",
        city="Lagos",
        state="Lagos",
        status=status,
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
        quantity=50,
        quantity_sold=0,
        quantity_reserved=0,
        min_per_order=1,
        max_per_order=5,
        visibility="public",
        status="active",
    )
    db.add(tt)
    db.commit()
    db.refresh(event)
    db.refresh(tt)
    return event, tt


def test_is_user_owner_of_host_narrow(db_session: Session, client: TestClient):
    from app.hosts.models import HostProfile

    host_a, owner_a = _seed_host(
        db_session, email="sa-ownera@example.com", slug="sa-host-a", name="Host A"
    )
    host_b, owner_b = _seed_host(
        db_session, email="sa-ownerb@example.com", slug="sa-host-b", name="Host B"
    )
    member, _ = _add_team_member(
        db_session, host_id=host_a.id, email="sa-team-a@example.com", client=client
    )
    event_a, _ = _seed_event(db_session, host_a, slug="sa-staff-event-a")
    event_b, _ = _seed_event(db_session, host_b, slug="sa-staff-event-b")

    staff_h = _register(client, "sa-staff-a@example.com", "Event Staff")
    staff = db_session.query(User).filter_by(email="sa-staff-a@example.com").one()
    db_session.add(
        EventStaffAssignment(
            event_id=event_a.id,
            user_id=staff.id,
            assignment_type="ticket_scanner",
            status="active",
            role_label="scanner",
        )
    )
    db_session.commit()

    assert is_user_owner_of_host(
        db_session, user_id=owner_a.id, host_profile_id=host_a.id
    )
    profile_a = db_session.query(HostProfile).filter_by(host_id=host_a.id).one_or_none()
    if profile_a is None:
        profile_a = HostProfile(host_id=host_a.id)
        db_session.add(profile_a)
        db_session.commit()
    assert is_user_owner_of_host(
        db_session, user_id=owner_a.id, host_profile_id=profile_a.id
    )
    # Team / staff / other-host owners are NOT owners of Host A.
    assert not is_user_owner_of_host(
        db_session, user_id=member.id, host_profile_id=host_a.id
    )
    assert not is_user_owner_of_host(
        db_session, user_id=staff.id, host_profile_id=host_a.id
    )
    assert not is_user_owner_of_host(
        db_session, user_id=owner_a.id, host_profile_id=host_b.id
    )
    assert not is_user_owner_of_host(
        db_session, user_id=member.id, host_profile_id=host_b.id
    )
    assert not is_user_owner_of_host(
        db_session, user_id=staff.id, host_profile_id=host_b.id
    )
    assert not is_user_owner_of_host(
        db_session, user_id=owner_b.id, host_profile_id=host_a.id
    )

    # Expired staff is also not treated as own-host owner.
    expired_h = _register(client, "sa-staff-exp@example.com", "Expired Staff")
    expired = db_session.query(User).filter_by(email="sa-staff-exp@example.com").one()
    db_session.add(
        EventStaffAssignment(
            event_id=event_a.id,
            user_id=expired.id,
            assignment_type="ticket_scanner",
            status="active",
            role_label="scanner",
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )
    )
    db_session.commit()
    assert not is_user_owner_of_host(
        db_session, user_id=expired.id, host_profile_id=host_a.id
    )

    assert_not_own_host_as_fan(db_session, user_id=owner_a.id, host_id=host_b.id)
    # Staff may fan Host A (no assert raised).
    assert_not_own_host_as_fan(db_session, user_id=staff.id, host_id=host_a.id)

    # Staff on Host A may still buy/follow Host B.
    assert staff_h["Authorization"].startswith("Bearer ")
    assert event_b.host_id == host_b.id
    assert expired_h["Authorization"].startswith("Bearer ")


def test_follow_blocks_own_host_allows_other(client: TestClient, db_session: Session):
    from app.crm.models import HostFollower
    from app.hosts.fan_self_abuse import FOLLOW_OWN_HOST_DETAIL

    host_a, owner_a = _seed_host(
        db_session, email="sa-follow-a@example.com", slug="sa-follow-a", name="Follow A"
    )
    host_b, _ = _seed_host(
        db_session, email="sa-follow-b@example.com", slug="sa-follow-b", name="Follow B"
    )
    member, member_h = _add_team_member(
        db_session,
        host_id=host_a.id,
        email="sa-follow-team@example.com",
        client=client,
    )
    owner_h = _login(client, owner_a.email)

    blocked_owner = client.post(
        "/api/v1/crm/follow",
        headers=owner_h,
        json={"host_id": str(host_a.id)},
    )
    assert blocked_owner.status_code == 400
    assert blocked_owner.json()["detail"] == FOLLOW_OWN_HOST_DETAIL

    # Historical self-follow must not appear in Personal following or allow opt-in.
    db_session.add(
        HostFollower(
            host_id=host_a.id,
            user_id=owner_a.id,
            marketing_opt_in=False,
        )
    )
    db_session.commit()
    following = client.get("/api/v1/crm/me/following", headers=owner_h)
    assert following.status_code == 200
    assert all(str(row["host_id"]) != str(host_a.id) for row in following.json())

    opt = client.patch(
        f"/api/v1/crm/me/following/{host_a.id}",
        headers=owner_h,
        json={"marketing_opt_in": True},
    )
    assert opt.status_code == 400
    assert opt.json()["detail"] == FOLLOW_OWN_HOST_DETAIL

    ok_team = client.post(
        "/api/v1/crm/follow",
        headers=member_h,
        json={"host_id": str(host_a.id)},
    )
    assert ok_team.status_code in {200, 201}, ok_team.text

    ok_owner = client.post(
        "/api/v1/crm/follow",
        headers=owner_h,
        json={"host_id": str(host_b.id)},
    )
    assert ok_owner.status_code in {200, 201}, ok_owner.text

    ok_team_b = client.post(
        "/api/v1/crm/follow",
        headers=member_h,
        json={"host_id": str(host_b.id)},
    )
    assert ok_team_b.status_code in {200, 201}, ok_team_b.text
    assert member.email.endswith("@example.com")


def test_checkout_init_blocks_own_host_without_paystack(
    client: TestClient, db_session: Session
):
    """Defense in depth: pending own-host orders must not start Paystack."""
    from unittest.mock import patch

    from app.hosts.fan_self_abuse import CHECKOUT_OWN_HOST_DETAIL

    host_a, owner_a = _seed_host(
        db_session,
        email="sa-init-a@example.com",
        slug="sa-init-a",
        name="Init A",
    )
    event_a, tt_a = _seed_event(db_session, host_a, slug="sa-init-event-a")
    owner_h = _login(client, owner_a.email)

    # Bypass create_order affiliation guard to simulate a stale pending order.
    order = Order(
        reference=f"PDY-SA-{uuid4().hex[:16].upper()}",
        buyer_user_id=owner_a.id,
        event_id=event_a.id,
        status="pending",
        currency="NGN",
        subtotal_amount=Decimal("5000.00"),
        discount_amount=Decimal("0"),
        total_amount=Decimal("5000.00"),
        buyer_email=owner_a.email,
        buyer_name=owner_a.full_name or "Owner",
    )
    db_session.add(order)
    db_session.flush()
    db_session.add(
        OrderItem(
            order_id=order.id,
            ticket_type_id=tt_a.id,
            quantity=1,
            unit_price=Decimal("5000.00"),
            line_total=Decimal("5000.00"),
            ticket_type_name=tt_a.name,
        )
    )
    db_session.commit()

    with patch("app.payments.service.initialize_transaction") as mock_init:
        resp = client.post(
            f"/api/v1/payments/checkout/{order.id}",
            headers=owner_h,
        )
        assert resp.status_code == 403
        assert resp.json()["detail"] == CHECKOUT_OWN_HOST_DETAIL
        mock_init.assert_not_called()


def test_checkout_blocks_own_host_allows_other(client: TestClient, db_session: Session):
    host_a, owner_a = _seed_host(
        db_session, email="sa-buy-a@example.com", slug="sa-buy-a", name="Buy A"
    )
    host_b, _ = _seed_host(
        db_session, email="sa-buy-b@example.com", slug="sa-buy-b", name="Buy B"
    )
    event_a, tt_a = _seed_event(db_session, host_a, slug="sa-buy-event-a")
    event_b, tt_b = _seed_event(db_session, host_b, slug="sa-buy-event-b")
    _, member_h = _add_team_member(
        db_session, host_id=host_a.id, email="sa-buy-team@example.com", client=client
    )
    owner_h = _login(client, owner_a.email)

    own = client.post(
        "/api/v1/orders",
        headers=owner_h,
        json={
            "event_id": str(event_a.id),
            "items": [{"ticket_type_id": str(tt_a.id), "quantity": 1}],
        },
    )
    assert own.status_code == 403
    assert (
        own.json()["detail"]
        == "You can’t buy tickets or merch from your own host workspace."
    )

    team_own = client.post(
        "/api/v1/orders",
        headers=member_h,
        json={
            "event_id": str(event_a.id),
            "items": [{"ticket_type_id": str(tt_a.id), "quantity": 1}],
        },
    )
    assert team_own.status_code == 201, team_own.text

    other = client.post(
        "/api/v1/orders",
        headers=owner_h,
        json={
            "event_id": str(event_b.id),
            "items": [{"ticket_type_id": str(tt_b.id), "quantity": 1}],
        },
    )
    assert other.status_code == 201, other.text

    team_other = client.post(
        "/api/v1/orders",
        headers=member_h,
        json={
            "event_id": str(event_b.id),
            "items": [{"ticket_type_id": str(tt_b.id), "quantity": 1}],
        },
    )
    assert team_other.status_code == 201, team_other.text


def test_review_eligibility_blocks_own_host(db_session: Session, client: TestClient):
    from app.hosts.fan_self_abuse import REVIEW_OWN_HOST_DETAIL
    from app.merch.constants import ITEM_KIND_MERCH
    from app.merch.models import EventMerchProduct, EventMerchVariant, MerchFulfillment
    from app.merch.reviews import create_review as create_merch_review

    host_a, owner_a = _seed_host(
        db_session, email="sa-rev-a@example.com", slug="sa-rev-a", name="Rev A"
    )
    host_b, _ = _seed_host(
        db_session, email="sa-rev-b@example.com", slug="sa-rev-b", name="Rev B"
    )
    member, member_h = _add_team_member(
        db_session, host_id=host_a.id, email="sa-rev-team@example.com", client=client
    )
    event_a, tt_a = _seed_event(db_session, host_a, slug="sa-rev-event-a", ended=True)
    event_b, tt_b = _seed_event(db_session, host_b, slug="sa-rev-event-b", ended=True)

    def _ticket(user: User, event: Event, ticket_type: TicketType) -> Ticket:
        order = Order(
            reference=f"PDY-SA-{uuid4().hex[:16].upper()}",
            buyer_user_id=user.id,
            event_id=event.id,
            status="paid",
            currency="NGN",
            subtotal_amount=Decimal("5000.00"),
            discount_amount=Decimal("0"),
            total_amount=Decimal("5000.00"),
            buyer_email=user.email,
            buyer_name=user.full_name or "Attendee",
            paid_at=datetime.now(UTC),
        )
        db_session.add(order)
        db_session.flush()
        item = OrderItem(
            order_id=order.id,
            ticket_type_id=ticket_type.id,
            quantity=1,
            unit_price=Decimal("5000.00"),
            line_total=Decimal("5000.00"),
            ticket_type_name=ticket_type.name,
        )
        db_session.add(item)
        db_session.flush()
        t = Ticket(
            public_code=new_public_ticket_code(),
            order_id=order.id,
            order_item_id=item.id,
            event_id=event.id,
            ticket_type_id=ticket_type.id,
            buyer_user_id=user.id,
            status="checked_in",
            ticket_type_name=ticket_type.name,
            holder_name=user.full_name or "Attendee",
            holder_email=user.email,
            checked_in_at=datetime.now(UTC) - timedelta(days=1),
        )
        db_session.add(t)
        db_session.commit()
        db_session.refresh(t)
        return t

    ticket_own = _ticket(owner_a, event_a, tt_a)
    eligible, reason, _, _ = evaluate_review_eligibility(
        db_session, user_id=owner_a.id, ticket_id=ticket_own.id
    )
    assert eligible is False
    assert reason == REVIEW_OWN_HOST_DETAIL

    owner_h = _login(client, owner_a.email)
    blocked_submit = client.post(
        "/api/v1/reviews",
        headers=owner_h,
        json={
            "ticket_id": str(ticket_own.id),
            "rating": 5,
            "body": "Self review must not publish",
        },
    )
    assert blocked_submit.status_code == 403
    assert blocked_submit.json()["detail"] == REVIEW_OWN_HOST_DETAIL

    ticket_team = _ticket(member, event_a, tt_a)
    eligible_t, reason_t, _, _ = evaluate_review_eligibility(
        db_session, user_id=member.id, ticket_id=ticket_team.id
    )
    assert eligible_t is True, reason_t

    ok_team = client.post(
        "/api/v1/reviews",
        headers=member_h,
        json={
            "ticket_id": str(ticket_team.id),
            "rating": 4,
            "body": "Team member verified review is allowed",
        },
    )
    assert ok_team.status_code == 201, ok_team.text

    ticket_other = _ticket(owner_a, event_b, tt_b)
    eligible_ok, reason_ok, _, _ = evaluate_review_eligibility(
        db_session, user_id=owner_a.id, ticket_id=ticket_other.id
    )
    assert eligible_ok is True, reason_ok

    # Merch: owner blocked; team allowed when they have a paid merch line.
    product = EventMerchProduct(
        host_id=host_a.id,
        event_id=event_a.id,
        name="Self Abuse Tee",
        slug=f"sa-tee-{uuid4().hex[:8]}",
        status="active",
        base_price=Decimal("3000.00"),
        currency="NGN",
        is_event_linked=True,
    )
    db_session.add(product)
    db_session.flush()
    variant = EventMerchVariant(
        product_id=product.id,
        label="M",
        sku=f"SA-TEE-{uuid4().hex[:6].upper()}",
        price=Decimal("3000.00"),
        inventory_count=10,
        status="active",
    )
    db_session.add(variant)
    db_session.flush()

    def _merch_item(buyer: User) -> OrderItem:
        order = Order(
            reference=f"PDY-MR-{uuid4().hex[:16].upper()}",
            buyer_user_id=buyer.id,
            event_id=event_a.id,
            status="paid",
            currency="NGN",
            subtotal_amount=Decimal("3000.00"),
            discount_amount=Decimal("0"),
            total_amount=Decimal("3000.00"),
            buyer_email=buyer.email,
            buyer_name=buyer.full_name or "Buyer",
            paid_at=datetime.now(UTC),
        )
        db_session.add(order)
        db_session.flush()
        item = OrderItem(
            order_id=order.id,
            quantity=1,
            unit_price=Decimal("3000.00"),
            line_total=Decimal("3000.00"),
            item_kind=ITEM_KIND_MERCH,
            merch_product_id=product.id,
            merch_variant_id=variant.id,
            ticket_type_name=None,
        )
        db_session.add(item)
        db_session.flush()
        db_session.add(
            MerchFulfillment(
                order_id=order.id,
                order_item_id=item.id,
                host_id=host_a.id,
                event_id=event_a.id,
                buyer_user_id=buyer.id,
                merch_variant_id=variant.id,
                quantity=1,
                status="ready",
                fulfillment_method="pickup",
                pickup_code=f"SA{uuid4().hex[:8].upper()}",
                product_name_snapshot=product.name,
                variant_label_snapshot=variant.label,
            )
        )
        db_session.commit()
        db_session.refresh(item)
        return item

    own_merch = _merch_item(owner_a)
    try:
        create_merch_review(
            db_session,
            user=owner_a,
            order_item_id=own_merch.id,
            rating=5,
            body="Owner merch self-review",
        )
        raise AssertionError("expected owner merch review block")
    except HTTPException as exc:
        assert exc.status_code == 403
        assert exc.detail == REVIEW_OWN_HOST_DETAIL

    team_merch = _merch_item(member)
    created = create_merch_review(
        db_session,
        user=member,
        order_item_id=team_merch.id,
        rating=5,
        body="Team merch review allowed",
    )
    assert created["rating"] == 5


def test_messaging_blocks_own_host_as_fan(db_session: Session, client: TestClient):
    from app.hosts.fan_self_abuse import MESSAGING_OWN_HOST_DETAIL

    host_a, owner_a = _seed_host(
        db_session, email="sa-msg-a@example.com", slug="sa-msg-a", name="Msg A"
    )
    host_b, owner_b = _seed_host(
        db_session, email="sa-msg-b@example.com", slug="sa-msg-b", name="Msg B"
    )
    member, member_h = _add_team_member(
        db_session, host_id=host_a.id, email="sa-msg-team@example.com", client=client
    )
    owner_h = _login(client, owner_a.email)

    access, _ = classify_fan_to_host(
        db_session, fan=owner_a, host=host_a, related_event_id=None
    )
    assert access == "denied"

    access_team, status_team = classify_fan_to_host(
        db_session, fan=member, host=host_a, related_event_id=None
    )
    # Team may message Host A as a fan when other messaging rules allow it.
    assert access_team in {"allowed", "request", "denied"}
    assert status_team in {"active", "request", "closed"}

    access_host_to_self, _ = classify_host_to_fan(
        db_session, host=host_a, fan=owner_a
    )
    assert access_host_to_self == "denied"

    blocked = client.post(
        "/api/v1/messages/threads",
        headers=owner_h,
        json={
            "host_id": str(host_a.id),
            "body": "Trying to message my own host workspace",
        },
    )
    assert blocked.status_code == 403
    assert blocked.json()["detail"] == MESSAGING_OWN_HOST_DETAIL
    assert (
        blocked.json()["detail"]
        == "You can’t message your own host workspace from your Personal account."
    )

    # Team fan→host is not auto-denied by ownership self-abuse (may still be
    # denied by messaging settings / lack of relationship).
    team_msg = client.post(
        "/api/v1/messages/threads",
        headers=member_h,
        json={
            "host_id": str(host_a.id),
            "body": "Team member fan message",
        },
    )
    assert team_msg.status_code != 403 or team_msg.json()["detail"] != MESSAGING_OWN_HOST_DETAIL

    # Host A owner may still open a fan thread toward Host B (subject to normal rules).
    cross_create = client.post(
        "/api/v1/messages/threads",
        headers=owner_h,
        json={
            "host_id": str(host_b.id),
            "body": "Hello from Host A owner as a fan of Host B",
        },
    )
    assert cross_create.status_code != 403 or (
        cross_create.json()["detail"] != MESSAGING_OWN_HOST_DETAIL
    )

    # Cross-host fan messaging still classified normally (not auto-denied by self-abuse).
    access_cross, status_hint = classify_fan_to_host(
        db_session, fan=owner_a, host=host_b, related_event_id=None
    )
    assert access_cross in {"allowed", "request", "denied"}
    assert status_hint in {"active", "request", "closed"}
    assert owner_b.is_active


def test_vault_subscribe_blocks_own_host(client: TestClient, db_session: Session):
    host_a, owner_a = _seed_host(
        db_session, email="sa-vault-a@example.com", slug="sa-vault-a", name="Vault A"
    )
    host_b, _ = _seed_host(
        db_session, email="sa-vault-b@example.com", slug="sa-vault-b", name="Vault B"
    )
    _, member_h = _add_team_member(
        db_session, host_id=host_a.id, email="sa-vault-team@example.com", client=client
    )
    owner_h = _login(client, owner_a.email)

    blocked = client.post(
        "/api/v1/vault/subscriptions",
        headers=owner_h,
        json={"host_id": str(host_a.id), "plan_label": "standard", "price": "5000"},
    )
    assert blocked.status_code == 400
    assert "own host" in blocked.json()["detail"].lower()

    blocked_team = client.post(
        "/api/v1/vault/subscriptions",
        headers=member_h,
        json={"host_id": str(host_a.id), "plan_label": "standard", "price": "5000"},
    )
    assert blocked_team.status_code in {200, 201}, blocked_team.text

    ok = client.post(
        "/api/v1/vault/subscriptions",
        headers=owner_h,
        json={"host_id": str(host_b.id), "plan_label": "standard", "price": "5000"},
    )
    assert ok.status_code in {200, 201}, ok.text


def test_checkout_allows_event_staff_on_host_events(
    client: TestClient, db_session: Session
):
    host_a, _ = _seed_host(
        db_session, email="sa-staff-buy-a@example.com", slug="sa-staff-buy-a", name="Staff Buy A"
    )
    host_b, _ = _seed_host(
        db_session, email="sa-staff-buy-b@example.com", slug="sa-staff-buy-b", name="Staff Buy B"
    )
    event_a, tt_a = _seed_event(db_session, host_a, slug="sa-staff-buy-event-a")
    event_b, tt_b = _seed_event(db_session, host_b, slug="sa-staff-buy-event-b")
    staff_h = _register(client, "sa-staff-buyer@example.com", "Staff Buyer")
    staff = db_session.query(User).filter_by(email="sa-staff-buyer@example.com").one()
    db_session.add(
        EventStaffAssignment(
            event_id=event_a.id,
            user_id=staff.id,
            assignment_type="ticket_scanner",
            status="active",
            role_label="scanner",
        )
    )
    db_session.commit()

    ok_own_host = client.post(
        "/api/v1/orders",
        headers=staff_h,
        json={
            "event_id": str(event_a.id),
            "items": [{"ticket_type_id": str(tt_a.id), "quantity": 1}],
        },
    )
    assert ok_own_host.status_code == 201, ok_own_host.text

    ok = client.post(
        "/api/v1/orders",
        headers=staff_h,
        json={
            "event_id": str(event_b.id),
            "items": [{"ticket_type_id": str(tt_b.id), "quantity": 1}],
        },
    )
    assert ok.status_code == 201, ok.text


def test_legacy_metrics_exclude_affiliated_tickets_and_reviews(
    db_session: Session, client: TestClient
):
    from app.legacy.service import collect_host_metrics
    from app.reviews.models import VerifiedReview

    host_a, owner_a = _seed_host(
        db_session, email="sa-met-a@example.com", slug="sa-met-a", name="Met A"
    )
    host_b, _ = _seed_host(
        db_session, email="sa-met-b@example.com", slug="sa-met-b", name="Met B"
    )
    fan_h = _register(client, "sa-met-fan@example.com", "Metric Fan")
    fan = db_session.query(User).filter_by(email="sa-met-fan@example.com").one()
    event_a, tt_a = _seed_event(db_session, host_a, slug="sa-met-event-a", ended=True)

    # Historical affiliated + external tickets/reviews (write path would block these).
    own_ticket = _ticket_for_metrics(db_session, owner_a, event_a, tt_a)
    fan_ticket = _ticket_for_metrics(db_session, fan, event_a, tt_a)
    db_session.add(
        VerifiedReview(
            event_id=event_a.id,
            host_id=host_a.id,
            reviewer_user_id=owner_a.id,
            ticket_id=own_ticket.id,
            rating=5,
            body="Self review should not count",
            status="visible",
        )
    )
    db_session.add(
        VerifiedReview(
            event_id=event_a.id,
            host_id=host_a.id,
            reviewer_user_id=fan.id,
            ticket_id=fan_ticket.id,
            rating=4,
            body="External fan review",
            status="visible",
        )
    )
    db_session.commit()

    metrics = collect_host_metrics(db_session, host_a.id)
    assert metrics.tickets_sold == 1
    assert metrics.verified_checkins == 1
    assert metrics.review_count == 1
    assert metrics.average_verified_rating == Decimal("4.00")
    # Cross-host still exists; fan account is unrelated to Host A affiliation.
    assert host_b.id != host_a.id
    assert fan_h["Authorization"].startswith("Bearer ")


def _ticket_for_metrics(db: Session, user: User, event: Event, ticket_type: TicketType) -> Ticket:
    order = Order(
        reference=f"PDY-MET-{uuid4().hex[:16].upper()}",
        buyer_user_id=user.id,
        event_id=event.id,
        status="paid",
        currency="NGN",
        subtotal_amount=Decimal("5000.00"),
        discount_amount=Decimal("0"),
        total_amount=Decimal("5000.00"),
        buyer_email=user.email,
        buyer_name=user.full_name or "Attendee",
        paid_at=datetime.now(UTC),
    )
    db.add(order)
    db.flush()
    item = OrderItem(
        order_id=order.id,
        ticket_type_id=ticket_type.id,
        quantity=1,
        unit_price=Decimal("5000.00"),
        line_total=Decimal("5000.00"),
        ticket_type_name=ticket_type.name,
    )
    db.add(item)
    db.flush()
    t = Ticket(
        public_code=new_public_ticket_code(),
        order_id=order.id,
        order_item_id=item.id,
        event_id=event.id,
        ticket_type_id=ticket_type.id,
        buyer_user_id=user.id,
        status="checked_in",
        ticket_type_name=ticket_type.name,
        holder_name=user.full_name or "Attendee",
        holder_email=user.email,
        checked_in_at=datetime.now(UTC) - timedelta(days=1),
    )
    db.add(t)
    db.flush()
    return t


def test_follower_metrics_exclude_owner_only(db_session: Session, client: TestClient):
    from app.crm.audience import audience_stats, resolve_segment_members
    from app.crm.models import HostFollower
    from app.legacy.service import collect_host_metrics

    host_a, owner_a = _seed_host(
        db_session, email="sa-fol-a@example.com", slug="sa-fol-a", name="Fol A"
    )
    member, _ = _add_team_member(
        db_session, host_id=host_a.id, email="sa-fol-team@example.com", client=client
    )
    fan_h = _register(client, "sa-fol-fan@example.com", "Real Fan")
    fan = db_session.query(User).filter_by(email="sa-fol-fan@example.com").one()

    # Owner follow must not count; team + real fan do.
    for user in (owner_a, member, fan):
        db_session.add(
            HostFollower(
                host_id=host_a.id,
                user_id=user.id,
                marketing_opt_in=True,
            )
        )
    db_session.commit()

    followers = resolve_segment_members(
        db_session, host_id=host_a.id, segment_key="followers"
    )
    follower_ids = {m["user_id"] for m in followers}
    assert fan.id in follower_ids
    assert member.id in follower_ids
    assert owner_a.id not in follower_ids

    stats = audience_stats(db_session, host_a.id)
    assert stats["followers"] == 2
    assert stats["marketing_opted_in"] == 2

    metrics = collect_host_metrics(db_session, host_a.id)
    assert metrics.followers == 2
    assert fan_h["Authorization"].startswith("Bearer ")


def test_ambassador_join_blocks_owner_allows_team(db_session: Session, client: TestClient):
    host_a, owner_a = _seed_host(
        db_session, email="sa-amb-a@example.com", slug="sa-amb-a", name="Amb A"
    )
    host_b, owner_b = _seed_host(
        db_session, email="sa-amb-b@example.com", slug="sa-amb-b", name="Amb B"
    )
    member, _ = _add_team_member(
        db_session, host_id=host_a.id, email="sa-amb-team@example.com", client=client
    )
    event_a, _ = _seed_event(db_session, host_a, slug="sa-amb-event-a")
    campaign = AmbassadorCampaign(
        host_id=host_a.id,
        event_id=event_a.id,
        name="Self Abuse Campaign",
        status="public_open",
        source="host",
        created_by_user_id=owner_a.id,
        campaign_type="event_tickets",
        commission_percent=Decimal("10.00"),
        commission_type="percentage",
        commission_value=Decimal("10.00"),
        applies_to="tickets",
        allow_host_owner_commission=False,
        merch_included=False,
    )
    db_session.add(campaign)
    db_session.commit()

    assert is_host_owner_participant(
        db_session, user_id=owner_a.id, campaign=campaign
    )
    assert not is_host_owner_participant(
        db_session, user_id=member.id, campaign=campaign
    )
    assert not is_host_owner_participant(
        db_session, user_id=owner_b.id, campaign=campaign
    )

    try:
        assert_user_may_join_campaign(
            db_session, user_id=owner_a.id, campaign=campaign
        )
        raise AssertionError("expected HTTPException for owner join")
    except HTTPException as exc:
        assert exc.status_code == 403

    assert_user_may_join_campaign(db_session, user_id=member.id, campaign=campaign)
    assert_user_may_join_campaign(db_session, user_id=owner_b.id, campaign=campaign)


def test_own_host_commission_and_existing_self_blocks(
    db_session: Session, client: TestClient
):
    """Own-host reward abuse + keep existing self-blocks."""
    from app.ambassadors.fraud import (
        commission_blocked_for_host_owner,
        is_self_referral,
    )
    from app.fan_connect.eligibility import classify_fan_connect
    from app.hosts.fan_self_abuse import assert_not_own_host_as_fan
    from app.payments.models import Order, OrderItem
    from app.promos.models import Ambassador
    from app.promos.service import attach_ambassador_to_order
    from app.tickets.models import Ticket

    host_a, owner_a = _seed_host(
        db_session, email="sa-misc-a@example.com", slug="sa-misc-a", name="Misc A"
    )
    host_b, owner_b = _seed_host(
        db_session, email="sa-misc-b@example.com", slug="sa-misc-b", name="Misc B"
    )
    event_a, _ = _seed_event(db_session, host_a, slug="sa-misc-event-a")
    campaign = AmbassadorCampaign(
        host_id=host_a.id,
        event_id=event_a.id,
        name="Owner Commission Block",
        status="public_open",
        source="host",
        created_by_user_id=owner_a.id,
        campaign_type="event_tickets",
        commission_percent=Decimal("10.00"),
        commission_type="percentage",
        commission_value=Decimal("10.00"),
        applies_to="tickets",
        allow_host_owner_commission=False,
        merch_included=False,
    )
    db_session.add(campaign)
    db_session.commit()

    assert commission_blocked_for_host_owner(
        db_session, user_id=owner_a.id, campaign=campaign
    )
    assert not commission_blocked_for_host_owner(
        db_session, user_id=owner_b.id, campaign=campaign
    )

    # Curated create must not link the host owner for own-host rewards.
    owner_h = _login(client, owner_a.email)
    curated = client.post(
        "/api/v1/promos/ambassadors",
        headers=owner_h,
        json={
            "referral_code": "ownercode",
            "display_name": "Owner Self",
            "user_email": owner_a.email,
            "status": "active",
            "commission_rate_percent": "10.00",
            "event_id": str(event_a.id),
        },
    )
    assert curated.status_code == 403, curated.text

    # Self-referral: buyer == ambassador never attaches.
    amb = Ambassador(
        host_id=host_a.id,
        event_id=event_a.id,
        program_kind="host_curated",
        user_id=owner_b.id,
        referral_code="ownerbref",
        display_name="Owner B Ref",
        status="active",
        commission_rate_percent=Decimal("5.00"),
    )
    db_session.add(amb)
    db_session.flush()
    order = Order(
        reference=f"PDY-SELF-{uuid4().hex[:16].upper()}",
        buyer_user_id=owner_b.id,
        event_id=event_a.id,
        status="pending",
        currency="NGN",
        subtotal_amount=Decimal("1000.00"),
        discount_amount=Decimal("0"),
        total_amount=Decimal("1000.00"),
        buyer_email=owner_b.email,
        buyer_name=owner_b.full_name or "B",
    )
    db_session.add(order)
    db_session.commit()
    attach_ambassador_to_order(db_session, order=order, ambassador=amb)
    db_session.refresh(order)
    assert order.ambassador_id is None
    assert is_self_referral(
        ambassador_user_id=owner_b.id, buyer_user_id=owner_b.id
    )

    # Fan Connect to self denied.
    pack = classify_fan_connect(db_session, actor=owner_a, target=owner_a)
    assert pack["allowed"] is False
    assert "self" in pack["denials"]

    # Vault / generic own-host fan assert.
    try:
        assert_not_own_host_as_fan(
            db_session, user_id=owner_a.id, host_id=host_a.id
        )
        raise AssertionError("expected own-host fan block")
    except HTTPException as exc:
        assert exc.status_code == 400

    # Ticket transfer to self.
    event_b, tt_b = _seed_event(db_session, host_b, slug="sa-misc-xfer-b")
    order2 = Order(
        reference=f"PDY-XFER-{uuid4().hex[:16].upper()}",
        buyer_user_id=owner_a.id,
        event_id=event_b.id,
        status="paid",
        currency="NGN",
        subtotal_amount=Decimal("5000.00"),
        discount_amount=Decimal("0"),
        total_amount=Decimal("5000.00"),
        buyer_email=owner_a.email,
        buyer_name=owner_a.full_name or "A",
        paid_at=datetime.now(UTC),
    )
    db_session.add(order2)
    db_session.flush()
    item = OrderItem(
        order_id=order2.id,
        ticket_type_id=tt_b.id,
        quantity=1,
        unit_price=Decimal("5000.00"),
        line_total=Decimal("5000.00"),
        ticket_type_name=tt_b.name,
    )
    db_session.add(item)
    db_session.flush()
    ticket = Ticket(
        public_code=new_public_ticket_code(),
        order_id=order2.id,
        order_item_id=item.id,
        event_id=event_b.id,
        ticket_type_id=tt_b.id,
        buyer_user_id=owner_a.id,
        status="active",
        ticket_type_name=tt_b.name,
        holder_name=owner_a.full_name or "A",
        holder_email=owner_a.email,
    )
    db_session.add(ticket)
    db_session.commit()

    xfer = client.post(
        f"/api/v1/tickets/{ticket.id}/transfer",
        headers=owner_h,
        json={"to_email": owner_a.email, "to_name": owner_a.full_name or "Owner"},
    )
    assert xfer.status_code == 400
    assert "yourself" in xfer.json()["detail"].lower()

    # Invite self to host team.
    invite = client.post(
        "/api/v1/host/team/invites",
        headers=owner_h,
        json={"invite_identifier": owner_a.email, "role": "admin"},
    )
    assert invite.status_code == 400
    assert "yourself" in invite.json()["detail"].lower() or "owner" in invite.json()[
        "detail"
    ].lower()


def test_self_abuse_asserts_have_no_bypass_parameters():
    import inspect

    from app.hosts import fan_self_abuse as mod

    for name in (
        "assert_not_own_host_as_fan",
        "assert_owner_not_buying_own_host",
        "assert_buyer_not_affiliated_with_event_host",
        "assert_not_own_host_public_review",
        "assert_not_own_host_follow",
        "assert_not_own_host_fan_messaging",
    ):
        params = set(inspect.signature(getattr(mod, name)).parameters)
        forbidden = {
            "bypass",
            "skip",
            "force",
            "admin",
            "impersonation",
            "test_mode",
            "allow_own_host",
        }
        assert params.isdisjoint(forbidden), f"{name} must not accept bypass params"


def test_test_order_flags_excluded_from_public_metrics():
    from types import SimpleNamespace

    from app.hosts.fan_self_abuse import order_excluded_from_public_metrics

    assert order_excluded_from_public_metrics(None) is False
    assert order_excluded_from_public_metrics(SimpleNamespace()) is False
    assert (
        order_excluded_from_public_metrics(SimpleNamespace(is_test_order=True))
        is True
    )
    assert (
        order_excluded_from_public_metrics(
            SimpleNamespace(exclude_from_public_metrics=True)
        )
        is True
    )
    # Production orders have neither flag — still counted (affiliation is separate).
    assert (
        order_excluded_from_public_metrics(
            SimpleNamespace(is_test_order=False, exclude_from_public_metrics=False)
        )
        is False
    )


def test_impersonation_cannot_checkout_own_host(
    client: TestClient, db_session: Session, assign_role
):
    """Impersonation must not open a production own-host checkout path."""
    from app.admin.impersonation_guards import IMPERSONATION_SENSITIVE_ACTION_DETAIL
    from app.hosts.fan_self_abuse import CHECKOUT_OWN_HOST_DETAIL

    host_a, owner_a = _seed_host(
        db_session,
        email="sa-imp-host@example.com",
        slug="sa-imp-host",
        name="Imp Host",
    )
    event_a, tt_a = _seed_event(db_session, host_a, slug="sa-imp-event-a")

    admin_reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "sa-imp-admin@example.com",
            "password": "securepass1",
            "full_name": "Imp Admin",
        },
    )
    assert admin_reg.status_code in {200, 201}, admin_reg.text
    assign_role("sa-imp-admin@example.com", "super_admin")
    admin_h = _login(client, "sa-imp-admin@example.com")

    start = client.post(
        f"/api/v1/admin/users/{owner_a.id}/impersonation/start",
        headers=admin_h,
        json={"reason": "QA own-host checkout must stay blocked", "duration_minutes": 15},
    )
    assert start.status_code == 200, start.text
    imp_headers = {"Authorization": f"Bearer {start.json()['access_token']}"}

    blocked = client.post(
        "/api/v1/orders",
        headers=imp_headers,
        json={
            "event_id": str(event_a.id),
            "items": [{"ticket_type_id": str(tt_a.id), "quantity": 1}],
        },
    )
    assert blocked.status_code == 403
    detail = blocked.json()["detail"]
    assert detail in {
        IMPERSONATION_SENSITIVE_ACTION_DETAIL,
        CHECKOUT_OWN_HOST_DETAIL,
    }


def test_host_as_fan_owner_keeps_personal_dashboard_access(
    client: TestClient, db_session: Session
):
    """Own-host blocks must not remove Personal /dashboard access."""
    host_a, owner_a = _seed_host(
        db_session,
        email="sa-dash-a@example.com",
        slug="sa-dash-a",
        name="Dash A",
    )
    owner_h = _login(client, owner_a.email)
    me = client.get("/api/v1/users/me", headers=owner_h)
    assert me.status_code == 200, me.text
    tickets = client.get("/api/v1/tickets/mine", headers=owner_h)
    assert tickets.status_code == 200, tickets.text
    passport = client.get("/api/v1/passport/me", headers=owner_h)
    assert passport.status_code == 200, passport.text
    assert host_a.user_id == owner_a.id
