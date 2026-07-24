"""Phase 9 ambassador domain table smoke tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.events.models import Event, EventCategory
from app.hosts.models import Host, HostProfile
from app.promos.ambassador_domain import (
    AmbassadorAttribution,
    AmbassadorAuditLog,
    AmbassadorClick,
    AmbassadorConversion,
    AmbassadorParticipant,
    AmbassadorPayout,
    AmbassadorProfile,
)
from app.promos.models import AmbassadorCampaign
from app.users.models import User
from app.users.service import get_role_by_name


def _seed_campaign(db: Session) -> tuple[User, Host, HostProfile, Event, AmbassadorCampaign]:
    tag = uuid4().hex[:8]
    user = User(
        email=f"domain-host-{tag}@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Domain Host",
        is_active=True,
    )
    role = get_role_by_name(db, "host")
    assert role is not None
    user.roles.append(role)
    db.add(user)
    db.flush()
    host = Host(
        user_id=user.id,
        display_name="Domain Host",
        slug=f"domain-host-{tag}",
        status="active",
    )
    db.add(host)
    db.flush()
    profile = HostProfile(host_id=host.id, city="Lagos")
    db.add(profile)
    db.flush()
    category = db.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=5)
    event = Event(
        title="Domain Event",
        slug=f"domain-event-{tag}",
        description="Domain model smoke",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=2),
        city="Lagos",
        status="published",
        featured=False,
        published_at=datetime.now(UTC),
    )
    db.add(event)
    db.flush()
    campaign = AmbassadorCampaign(
        host_id=host.id,
        host_profile_id=profile.id,
        event_id=event.id,
        name="Domain campaign",
        description="Phase 9 shape",
        status="public_open",
        visibility="public_open",
        source="host",
        created_by_user_id=user.id,
        campaign_type="event_tickets",
        commission_type="percentage",
        commission_value=Decimal("5.00"),
        commission_percent=Decimal("5.00"),
        applies_to="tickets",
        hold_period_days=7,
        cookie_window_days=30,
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return user, host, profile, event, campaign


def test_domain_tables_round_trip(db_session: Session):
    host_user, _host, _hp, event, campaign = _seed_campaign(db_session)
    amb_user = User(
        email=f"domain-amb-{uuid4().hex[:8]}@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Amb",
        is_active=True,
    )
    db_session.add(amb_user)
    db_session.flush()

    profile = AmbassadorProfile(
        user_id=amb_user.id,
        status="active",
        public_code_base="AMB",
        terms_accepted_at=datetime.now(UTC),
    )
    db_session.add(profile)
    db_session.flush()

    participant = AmbassadorParticipant(
        campaign_id=campaign.id,
        ambassador_profile_id=profile.id,
        user_id=amb_user.id,
        ambassador_code="DOMAIN01",
        status="active",
    )
    db_session.add(participant)
    db_session.flush()

    click = AmbassadorClick(
        campaign_id=campaign.id,
        participant_id=participant.id,
        event_id=event.id,
        session_id="sess-1",
        landing_url=f"/events/{event.slug}?ref=DOMAIN01",
        referrer_url="https://example.com",
    )
    db_session.add(click)

    attribution = AmbassadorAttribution(
        campaign_id=campaign.id,
        participant_id=participant.id,
        user_id=None,
        session_id="sess-1",
        event_id=event.id,
        source="link",
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )
    db_session.add(attribution)

    conversion = AmbassadorConversion(
        campaign_id=campaign.id,
        participant_id=participant.id,
        buyer_user_id=host_user.id,
        conversion_type="ticket",
        gross_amount=Decimal("5000.00"),
        eligible_amount=Decimal("5000.00"),
        commission_amount=Decimal("250.00"),
        status="pending",
        dedupe_key=f"order:{uuid4()}",
    )
    db_session.add(conversion)

    payout = AmbassadorPayout(
        ambassador_profile_id=profile.id,
        user_id=amb_user.id,
        amount=Decimal("250.00"),
        status="pending",
        payout_method="bank_transfer",
        notes="smoke",
    )
    db_session.add(payout)

    audit = AmbassadorAuditLog(
        actor_user_id=host_user.id,
        action="ambassadors.domain.smoke",
        entity_type="ambassador_campaign",
        entity_id=str(campaign.id),
        metadata_json={"ok": True},
    )
    db_session.add(audit)
    db_session.commit()

    assert db_session.scalar(
        select(AmbassadorProfile).where(AmbassadorProfile.user_id == amb_user.id)
    )
    assert db_session.scalar(
        select(AmbassadorClick).where(AmbassadorClick.participant_id == participant.id)
    )
    assert campaign.cookie_window_days == 30
    assert campaign.visibility == "public_open"
    assert campaign.host_profile_id is not None


def test_conversion_dedupe_unique(db_session: Session):
    _host_user, _host, _hp, _event, campaign = _seed_campaign(db_session)
    amb_user = User(
        email=f"dedupe-amb-{uuid4().hex[:8]}@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Amb",
        is_active=True,
    )
    db_session.add(amb_user)
    db_session.flush()
    profile = AmbassadorProfile(user_id=amb_user.id, status="active")
    db_session.add(profile)
    db_session.flush()
    participant = AmbassadorParticipant(
        campaign_id=campaign.id,
        ambassador_profile_id=profile.id,
        user_id=amb_user.id,
        ambassador_code="DEDUPE01",
        status="active",
    )
    db_session.add(participant)
    db_session.flush()

    key = f"order:{uuid4()}"
    db_session.add(
        AmbassadorConversion(
            campaign_id=campaign.id,
            participant_id=participant.id,
            conversion_type="ticket",
            gross_amount=Decimal("1000"),
            eligible_amount=Decimal("1000"),
            commission_amount=Decimal("50"),
            status="pending",
            dedupe_key=key,
        )
    )
    db_session.commit()

    db_session.add(
        AmbassadorConversion(
            campaign_id=campaign.id,
            participant_id=participant.id,
            conversion_type="ticket",
            gross_amount=Decimal("1000"),
            eligible_amount=Decimal("1000"),
            commission_amount=Decimal("50"),
            status="pending",
            dedupe_key=key,
        )
    )
    try:
        db_session.commit()
        raise AssertionError("expected unique violation on dedupe_key")
    except IntegrityError:
        db_session.rollback()
