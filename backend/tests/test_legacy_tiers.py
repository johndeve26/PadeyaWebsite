"""Legacy tier scoring and admin management tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostProfile
from app.legacy.constants import SCORE_WEIGHTS
from app.legacy.models import HostLegacyScore, HostLegacyScoreHistory, LegacyTier
from app.legacy.scoring import ScoreInputs, compute_composite_score, select_tier
from app.legacy.service import refresh_host_legacy_score
from app.payments.models import Order, OrderItem
from app.reviews.models import VerifiedReview
from app.tickets.models import Ticket
from app.tickets.qr import new_public_ticket_code
from app.users.models import User
from app.users.service import get_role_by_name


def test_score_weighting_sums_and_rating_factor():
    assert sum(SCORE_WEIGHTS.values()) == Decimal("1.00")
    score, factors = compute_composite_score(
        ScoreInputs(
            average_verified_rating=Decimal("5"),
            review_count=10,
            completed_events=0,
            tickets_sold=0,
            verified_checkins=0,
            refund_dispute_rate=None,
            events_hosted=0,
            followers=0,
            repeat_buyers_rate=None,
        )
    )
    assert factors["verified_rating"] == Decimal("100.00")
    # 100 * 0.30 + refund placeholder 80 * 0.10 = 30 + 8 = 38
    assert score == Decimal("38.00")


def test_tier_calculation_selects_by_score_and_requirements():
    tiers = [
        SimpleNamespace(
            slug="new-host",
            name="New Host",
            rank=0,
            min_score=Decimal("0"),
            is_active=True,
            requirements={"min_completed_events": 0},
        ),
        SimpleNamespace(
            slug="rising",
            name="Rising",
            rank=1,
            min_score=Decimal("20"),
            is_active=True,
            requirements={
                "min_completed_events": 1,
                "min_tickets_sold": 25,
                "min_verified_checkins": 10,
                "min_average_rating": 3.5,
                "min_review_count": 1,
            },
        ),
        SimpleNamespace(
            slug="established",
            name="Established",
            rank=2,
            min_score=Decimal("40"),
            is_active=True,
            requirements={
                "min_completed_events": 3,
                "min_tickets_sold": 150,
                "min_verified_checkins": 75,
                "min_average_rating": 4.0,
                "min_review_count": 5,
            },
        ),
    ]
    weak = ScoreInputs(
        average_verified_rating=None,
        review_count=0,
        completed_events=0,
        tickets_sold=0,
        verified_checkins=0,
        refund_dispute_rate=None,
        events_hosted=0,
        followers=0,
        repeat_buyers_rate=None,
    )
    assert select_tier(tiers, score=Decimal("50"), inputs=weak).slug == "new-host"

    strong = ScoreInputs(
        average_verified_rating=Decimal("4.5"),
        review_count=8,
        completed_events=4,
        tickets_sold=200,
        verified_checkins=100,
        refund_dispute_rate=Decimal("2"),
        events_hosted=4,
        followers=50,
        repeat_buyers_rate=Decimal("10"),
    )
    assert select_tier(tiers, score=Decimal("45"), inputs=strong).slug == "established"


def _make_buyer(db: Session, email: str, name: str) -> User:
    user = User(
        email=email,
        password_hash=hash_password("securepass1"),
        full_name=name,
        is_active=True,
    )
    role = get_role_by_name(db, "buyer")
    assert role is not None
    user.roles.append(role)
    db.add(user)
    db.flush()
    return user


def _seed_host_with_metrics(
    db: Session,
    *,
    completed_events: int = 1,
    tickets: int = 30,
    checkins: int = 15,
    reviews: int = 2,
) -> Host:
    host_user = User(
        email="tier-host@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Tier Host",
        is_active=True,
    )
    host_role = get_role_by_name(db, "host")
    assert host_role is not None
    host_user.roles.append(host_role)
    db.add(host_user)
    db.flush()

    host = Host(
        user_id=host_user.id,
        display_name="Tier Host",
        slug="tier-host",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, bio="Tier test host"))

    category = db.query(EventCategory).first()
    ticket_rows: list[Ticket] = []

    for i in range(completed_events):
        start = datetime.now(UTC) - timedelta(days=10 + i)
        event = Event(
            title=f"Tier Event {i}",
            slug=f"tier-event-{i}",
            description="Completed event used for Legacy tier scoring tests.",
            category_id=category.id if category else None,
            host_id=host.id,
            start_datetime=start,
            end_datetime=start + timedelta(hours=3),
            city="Lagos",
            status="completed",
            featured=False,
            published_at=start - timedelta(days=1),
        )
        db.add(event)
        db.flush()
        tt = TicketType(
            event_id=event.id,
            name="GA",
            type="regular",
            price=Decimal("1000.00"),
            quantity=500,
            quantity_sold=0,
            quantity_reserved=0,
            min_per_order=1,
            max_per_order=5,
            visibility="public",
            status="active",
        )
        db.add(tt)
        db.flush()

        per_event_tickets = tickets // completed_events + (
            tickets % completed_events if i == 0 else 0
        )
        per_event_checkins = checkins // completed_events + (
            checkins % completed_events if i == 0 else 0
        )
        for n in range(per_event_tickets):
            buyer = _make_buyer(db, f"tier-buyer-{i}-{n}@example.com", f"Buyer {i}-{n}")
            order = Order(
                reference=f"PDY-TIER-{i}-{n}",
                buyer_user_id=buyer.id,
                event_id=event.id,
                status="paid",
                currency="NGN",
                subtotal_amount=Decimal("1000.00"),
                total_amount=Decimal("1000.00"),
                buyer_email=buyer.email,
                buyer_name=buyer.full_name,
                paid_at=datetime.now(UTC),
            )
            db.add(order)
            db.flush()
            item = OrderItem(
                order_id=order.id,
                ticket_type_id=tt.id,
                quantity=1,
                unit_price=Decimal("1000.00"),
                line_total=Decimal("1000.00"),
                ticket_type_name="GA",
            )
            db.add(item)
            db.flush()
            status = "checked_in" if n < per_event_checkins else "active"
            ticket = Ticket(
                public_code=new_public_ticket_code(),
                order_id=order.id,
                order_item_id=item.id,
                event_id=event.id,
                ticket_type_id=tt.id,
                buyer_user_id=buyer.id,
                status=status,
                ticket_type_name="GA",
                holder_name=buyer.full_name,
                holder_email=buyer.email,
                checked_in_at=datetime.now(UTC) if status == "checked_in" else None,
            )
            db.add(ticket)
            db.flush()
            ticket_rows.append(ticket)

    checked_in = [t for t in ticket_rows if t.status == "checked_in"]
    for idx, ticket in enumerate(checked_in[:reviews]):
        db.add(
            VerifiedReview(
                event_id=ticket.event_id,
                host_id=host.id,
                reviewer_user_id=ticket.buyer_user_id,
                ticket_id=ticket.id,
                rating=5,
                body="Verified review body for Legacy tier scoring coverage.",
                status="visible",
            )
        )

    db.commit()
    return host


def test_tier_upgrade_and_history(db_session: Session):
    host = _seed_host_with_metrics(db_session)
    score = refresh_host_legacy_score(
        db_session, host.id, reason="test_upgrade", force_history=True
    )
    db_session.commit()

    assert score.legacy_status == "Rising"
    tier = db_session.get(LegacyTier, score.tier_id)
    assert tier is not None
    assert tier.slug == "rising"
    assert Decimal(score.composite_score) >= Decimal("20")

    history = db_session.query(HostLegacyScoreHistory).filter_by(host_id=host.id).all()
    assert len(history) >= 1
    assert any(h.reason == "test_upgrade" for h in history)


def test_tier_downgrade_when_thresholds_rise(
    client: TestClient, db_session: Session, assign_role
):
    host = _seed_host_with_metrics(db_session)
    refresh_host_legacy_score(db_session, host.id, reason="seed", force_history=True)
    db_session.commit()
    score = db_session.query(HostLegacyScore).filter_by(host_id=host.id).one()
    assert score.legacy_status == "Rising"

    client.post(
        "/api/v1/auth/register",
        json={
            "email": "legacy-admin@example.com",
            "password": "securepass1",
            "full_name": "Legacy Admin",
        },
    )
    assign_role("legacy-admin@example.com", "finance_admin")
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "legacy-admin@example.com", "password": "securepass1"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    rising = db_session.query(LegacyTier).filter_by(slug="rising").one()
    updated = client.patch(
        f"/api/v1/legacy/admin/tiers/{rising.id}",
        headers=headers,
        json={"min_score": "95.00"},
    )
    assert updated.status_code == 200, updated.text
    assert Decimal(updated.json()["min_score"]) == Decimal("95.00")

    recalc = client.post(
        f"/api/v1/legacy/admin/hosts/{host.id}/recalculate",
        headers=headers,
    )
    assert recalc.status_code == 200, recalc.text
    assert recalc.json()["legacy_status"] == "New Host"

    history = client.get(
        f"/api/v1/legacy/admin/hosts/{host.id}/history",
        headers=headers,
    )
    assert history.status_code == 200
    assert any(row["previous_tier_slug"] == "rising" for row in history.json())


def test_admin_threshold_update_and_recalc_all(
    client: TestClient, db_session: Session, assign_role
):
    host = _seed_host_with_metrics(db_session)
    refresh_host_legacy_score(db_session, host.id, reason="seed", force_history=True)
    db_session.commit()

    email = "legacy-ops@example.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass1", "full_name": "Ops"},
    )
    assign_role(email, "finance_admin")
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    tiers = client.get("/api/v1/legacy/admin/tiers", headers=headers)
    assert tiers.status_code == 200
    assert len(tiers.json()) == 6

    hosts = client.get("/api/v1/legacy/admin/hosts", headers=headers)
    assert hosts.status_code == 200
    assert any(h["username"] == "tier-host" for h in hosts.json())

    all_recalc = client.post("/api/v1/legacy/admin/recalculate-all", headers=headers)
    assert all_recalc.status_code == 200
    assert all_recalc.json()["recalculated"] >= 1


def test_host_tier_progress_endpoint(client: TestClient, db_session: Session):
    _seed_host_with_metrics(db_session)
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "tier-host@example.com", "password": "securepass1"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    progress = client.get("/api/v1/legacy/me/tier", headers=headers)
    assert progress.status_code == 200, progress.text
    body = progress.json()
    assert body["current_tier"]["slug"] == "rising"
    assert body["next_tier"]["slug"] == "established"
    assert "progress_percentage" in body
    assert isinstance(body["requirements_met"], list)
    assert isinstance(body["requirements_remaining"], list)
    assert isinstance(body["suggested_actions"], list)
