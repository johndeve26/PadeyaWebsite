"""Tests for local demo seed/reset safety and consistency."""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app.core.config import get_settings
from app.demo.constants import DEMO_EMAIL_DOMAIN, DEMO_EVENT_SLUG_PREFIX, DEMO_PASSWORD
from app.demo.guards import DemoEnvironmentError, assert_demo_ops_allowed
from app.demo.models import DemoEntityMarker, DemoSupportCase
from app.demo.reset import reset_demo_data
from app.demo.seed import seed_demo_data
from app.events.models import Event
from app.hosts.models import Host
from app.reviews.models import VerifiedReview
from app.tickets.models import Ticket
from app.users.models import User
from app.users.service import get_user_by_email, user_has_role
from app.vault.models import VaultItem
from app.vault.service import get_public_vault_item, serialize_item


@pytest.fixture()
def demo_settings(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("FRONTEND_URL", "http://localhost:3000")
    get_settings.cache_clear()
    yield get_settings()
    get_settings.cache_clear()


def test_production_blocks_demo_seed(monkeypatch: pytest.MonkeyPatch, db_session) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setenv("SECRET_KEY", "unit-test-production-secret-key-32chars")
    monkeypatch.setenv("CORS_ORIGINS", "https://padeya.com")
    monkeypatch.setenv("FRONTEND_URL", "https://padeya.com")
    get_settings.cache_clear()
    with pytest.raises(DemoEnvironmentError):
        assert_demo_ops_allowed(operation="demo seed")
    with pytest.raises(DemoEnvironmentError):
        seed_demo_data(db_session, reset=False)
    get_settings.cache_clear()
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-not-for-production")
    get_settings.cache_clear()


def test_demo_seed_idempotent_and_consistent(demo_settings, db_session) -> None:
    first = seed_demo_data(db_session, reset=True)
    assert first["status"] == "seeded"
    assert first["hosts"] >= 5
    assert first["events"] >= 20
    assert first["tickets"] >= 50
    assert first["checked_in"] >= 20
    assert first["reviews"] >= 20

    buyer = get_user_by_email(db_session, f"buyer@{DEMO_EMAIL_DOMAIN}")
    host = get_user_by_email(db_session, f"host@{DEMO_EMAIL_DOMAIN}")
    admin = get_user_by_email(db_session, f"admin@{DEMO_EMAIL_DOMAIN}")
    support = get_user_by_email(db_session, f"support@{DEMO_EMAIL_DOMAIN}")
    assert buyer is not None and user_has_role(buyer, "buyer")
    assert host is not None and user_has_role(host, "host")
    assert admin is not None and user_has_role(admin, "super_admin")
    assert support is not None and user_has_role(support, "support_agent")
    assert buyer.full_name == "Demo Buyer"
    assert admin.full_name == "Demo Super Admin"
    assert support.full_name == "Demo Support Agent"

    from app.crm.models import HostFollower
    from app.demo.constants import (
        DEMO_FAN_PERSONAS,
        DEMO_HOSTS,
        DEMO_PERSONA_CONTEXT,
        DEMO_SHOWCASE_EVENTS,
        SHOWCASE_COMPLETED_KEYS,
        SHOWCASE_UPCOMING_KEYS,
    )
    from app.hosts.models import HostVerification
    from app.legacy.models import HostLegacyPage, HostLegacyScore, LegacyTier
    from app.passport.models import FanBadge, FanPassport, UserBadge
    from app.sponsorships.models import HostSponsorshipSettings
    from app.vault.models import VaultItem, VaultPurchase

    # Named fan personas + Passport privacy + messaging settings matrix
    from app.messaging.models import MessageSettings

    for persona in DEMO_FAN_PERSONAS:
        fan = get_user_by_email(db_session, persona["email"])
        assert fan is not None, persona["email"]
        assert fan.full_name == persona["full_name"]
        pp = db_session.scalar(
            select(FanPassport).where(FanPassport.user_id == fan.id)
        )
        assert pp is not None
        assert pp.username == persona["username"]
        assert pp.visibility == persona["visibility"]
        expect_dir = bool(persona["appear_in_directory"]) and persona["visibility"] == "public"
        assert pp.appear_in_directory is expect_dir
        # Login email must not appear on public Passport fields
        assert persona["email"] not in (pp.bio or "")
        assert persona["email"] not in (pp.tagline or "")
        earned = {
            b.slug
            for b in db_session.scalars(
                select(FanBadge)
                .join(UserBadge, UserBadge.badge_id == FanBadge.id)
                .where(UserBadge.user_id == fan.id)
            ).all()
        }
        for slug in persona["badge_slugs"]:
            assert slug in earned, f"{persona['username']} missing badge {slug}"
        settings = db_session.scalar(
            select(MessageSettings).where(MessageSettings.user_id == fan.id)
        )
        assert settings is not None, persona["username"]
        assert settings.allow_messages_from_hosts_i_follow is bool(
            persona["allow_messages_from_hosts_i_follow"]
        )
        assert settings.allow_messages_from_hosts_i_attended is bool(
            persona["allow_messages_from_hosts_i_attended"]
        )
        assert settings.allow_messages_from_public is bool(
            persona["allow_messages_from_public"]
        )
        assert settings.message_requests_enabled is bool(
            persona["message_requests_enabled"]
        )
        # No cold public Message Fan for demo personas
        assert settings.allow_messages_from_public is False

    # Message settings variety: Tolu blocked list + Comedy auto-reply + Maze host block
    from app.messaging.service import get_settings_payload

    tolu_settings_user = get_user_by_email(db_session, f"fan1@{DEMO_EMAIL_DOMAIN}")
    assert tolu_settings_user is not None
    tolu_payload = get_settings_payload(db_session, tolu_settings_user)
    assert tolu_payload["allow_messages_from_public"] is False
    assert tolu_payload["message_requests_enabled"] is True
    assert len(tolu_payload["blocked_users"]) >= 1
    assert any(
        "Comedy" in (b["display_name"] or "") or b.get("username") == "lagoscomedyhub"
        for b in tolu_payload["blocked_users"]
    )

    maze_settings_host = db_session.scalar(select(Host).where(Host.slug == "djmaze"))
    assert maze_settings_host is not None
    maze_owner = db_session.get(User, maze_settings_host.user_id)
    assert maze_owner is not None
    maze_payload = get_settings_payload(db_session, maze_owner)
    assert maze_payload["auto_reply_enabled"] is False
    assert len(maze_payload["blocked_users"]) >= 1

    comedy_settings_host = db_session.scalar(
        select(Host).where(Host.slug == "lagoscomedyhub")
    )
    assert comedy_settings_host is not None
    comedy_owner = db_session.get(User, comedy_settings_host.user_id)
    assert comedy_owner is not None
    comedy_payload = get_settings_payload(db_session, comedy_owner)
    assert comedy_payload["auto_reply_enabled"] is True
    assert comedy_payload["auto_reply_message"]
    assert "Pàdéyá" in comedy_payload["auto_reply_message"]
    assert "Keep this conversation here" in comedy_payload["auto_reply_message"]
    assert "whatsapp" not in comedy_payload["auto_reply_message"].lower()

    # Host roles: verified, tiers, cities, sponsor-ready, Vault CTA + Message Host settings
    from app.demo.messaging_seed import _HOST_MESSAGING_SPECS

    for spec in DEMO_HOSTS:
        h = db_session.scalar(select(Host).where(Host.slug == spec["slug"]))
        assert h is not None, spec["slug"]
        assert h.display_name == spec["display_name"]
        assert h.profile is not None
        assert h.profile.city == spec["city"]
        verified = db_session.scalar(
            select(HostVerification).where(
                HostVerification.host_id == h.id,
                HostVerification.status == "verified",
            )
        )
        assert verified is not None
        score = db_session.scalar(
            select(HostLegacyScore).where(HostLegacyScore.host_id == h.id)
        )
        assert score is not None and score.tier_id is not None
        tier = db_session.get(LegacyTier, score.tier_id)
        assert tier is not None and tier.slug == spec["tier_slug"]
        page = db_session.scalar(
            select(HostLegacyPage).where(HostLegacyPage.host_id == h.id)
        )
        assert page is not None
        host_msg = _HOST_MESSAGING_SPECS.get(spec["slug"])
        assert host_msg is not None, spec["slug"]
        hs = db_session.scalar(
            select(MessageSettings).where(MessageSettings.user_id == h.user_id)
        )
        assert hs is not None
        assert hs.allow_messages_from_followers is bool(
            host_msg["allow_messages_from_followers"]
        )
        assert hs.allow_messages_from_ticket_buyers is bool(
            host_msg["allow_messages_from_ticket_buyers"]
        )
        assert hs.allow_messages_from_public_host is bool(
            host_msg["allow_messages_from_public_host"]
        )
        assert hs.allow_event_inquiries is bool(host_msg["allow_event_inquiries"])
        assert hs.message_requests_enabled is bool(
            host_msg["message_requests_enabled"]
        )
        assert hs.auto_reply_enabled is bool(host_msg["auto_reply_enabled"])
        if host_msg["auto_reply_enabled"]:
            assert hs.auto_reply_message and "Pàdéyá" in hs.auto_reply_message
        else:
            assert not hs.auto_reply_enabled
        assert page.sponsorship_available is bool(spec["sponsor_ready"])
        assert page.primary_category_slug == spec["primary_category_slug"]
        if spec["vault_enabled"]:
            assert page.primary_cta_type == "vault"
        settings = db_session.scalar(
            select(HostSponsorshipSettings).where(
                HostSponsorshipSettings.host_id == h.id
            )
        )
        assert settings is not None
        assert settings.accepting_sponsors is bool(spec["sponsor_ready"])

    # Host product context for messaging (events, tickets, check-ins, follows, Vault)
    for slug in [h["slug"] for h in DEMO_HOSTS]:
        host_row = db_session.scalar(select(Host).where(Host.slug == slug))
        assert host_row is not None
        host_showcase = [e for e in DEMO_SHOWCASE_EVENTS if e["host_slug"] == slug]
        assert 2 <= len(host_showcase) <= 3, slug
        assert any(e["lifecycle"] == "upcoming" for e in host_showcase), slug
        assert any(e["lifecycle"] == "completed" for e in host_showcase), slug
        host_events = list(
            db_session.scalars(select(Event).where(Event.host_id == host_row.id)).all()
        )
        assert len(host_events) >= 2, slug
        ticket_n = (
            db_session.scalar(
                select(func.count())
                .select_from(Ticket)
                .join(Event)
                .where(Event.host_id == host_row.id)
            )
            or 0
        )
        assert 5 <= ticket_n, f"{slug} ticket holders too low: {ticket_n}"
        followers_n = (
            db_session.scalar(
                select(func.count())
                .select_from(HostFollower)
                .where(HostFollower.host_id == host_row.id)
            )
            or 0
        )
        assert followers_n >= 5, slug
        completed_showcase = [
            e for e in host_showcase if e["lifecycle"] == "completed"
        ]
        for row in completed_showcase:
            ev = db_session.scalar(
                select(Event).where(
                    Event.slug == f"{DEMO_EVENT_SLUG_PREFIX}{row['key']}"
                )
            )
            assert ev is not None and ev.status == "completed"
            checked = (
                db_session.scalar(
                    select(func.count())
                    .select_from(Ticket)
                    .where(
                        Ticket.event_id == ev.id,
                        Ticket.status == "checked_in",
                    )
                )
                or 0
            )
            assert checked >= 1, row["key"]
            rev_n = (
                db_session.scalar(
                    select(func.count())
                    .select_from(VerifiedReview)
                    .where(VerifiedReview.event_id == ev.id)
                )
                or 0
            )
            assert rev_n >= 1, row["key"]

    # Fan persona product context (tickets, attendance, reviews, Vault unlocks)
    for row in DEMO_PERSONA_CONTEXT:
        fan = get_user_by_email(db_session, str(row["email"]))
        assert fan is not None, row["email"]
        for key in list(row.get("upcoming") or []):
            ev = db_session.scalar(
                select(Event).where(Event.slug == f"{DEMO_EVENT_SLUG_PREFIX}{key}")
            )
            assert ev is not None
            ticket = db_session.scalar(
                select(Ticket).where(
                    Ticket.event_id == ev.id,
                    Ticket.buyer_user_id == fan.id,
                    Ticket.status.in_(("active", "checked_in")),
                )
            )
            assert ticket is not None, (row["email"], key)
        for key in list(row.get("attended") or []):
            ev = db_session.scalar(
                select(Event).where(Event.slug == f"{DEMO_EVENT_SLUG_PREFIX}{key}")
            )
            assert ev is not None
            ticket = db_session.scalar(
                select(Ticket).where(
                    Ticket.event_id == ev.id,
                    Ticket.buyer_user_id == fan.id,
                    Ticket.status == "checked_in",
                )
            )
            assert ticket is not None, (row["email"], "attended", key)
        review_key = row.get("review_event")
        if review_key:
            ev = db_session.scalar(
                select(Event).where(
                    Event.slug == f"{DEMO_EVENT_SLUG_PREFIX}{review_key}"
                )
            )
            assert ev is not None
            rev = db_session.scalar(
                select(VerifiedReview).where(
                    VerifiedReview.event_id == ev.id,
                    VerifiedReview.reviewer_user_id == fan.id,
                )
            )
            assert rev is not None, (row["email"], review_key)
        for slug in list(row.get("vault_paid_slugs") or []):
            purchase = db_session.scalar(
                select(VaultPurchase)
                .join(VaultItem, VaultItem.id == VaultPurchase.vault_item_id)
                .where(
                    VaultPurchase.user_id == fan.id,
                    VaultPurchase.status == "paid",
                    VaultItem.slug == slug,
                )
            )
            assert purchase is not None, (row["email"], slug)

    assert len(SHOWCASE_UPCOMING_KEYS) >= 5
    assert len(SHOWCASE_COMPLETED_KEYS) >= 5

    # Password hash is set (login path tested elsewhere); marker present
    marker = db_session.scalar(
        select(DemoEntityMarker).where(
            DemoEntityMarker.entity_type == "seed",
            DemoEntityMarker.entity_key == "complete",
        )
    )
    assert marker is not None

    maze = db_session.scalar(select(Host).where(Host.slug == "djmaze"))
    assert maze is not None

    from app.demo.constants import DEMO_SHOWCASE_EVENTS, SHOWCASE_COMPLETED_KEYS
    from app.events.privacy import apply_location_privacy
    from app.messaging.models import (
        InAppNotification,
        Message,
        MessageBlock,
        MessageReport,
        MessageThread,
    )
    from app.tickets.models import Ticket as TicketModel

    vault_linked_keys = {
        "afrobeats-night-live",
        "mainland-after-dark",
        "lagos-comedy-jam",
        "island-comedy-night",
        "founders-mixer-lagos",
        "startup-demo-evening",
        "praise-experience-live",
        "worship-under-stars",
        "food-and-flow",
        "mainland-vibes-summer",
    }

    # Showcase events: titles, tickets, commerce, messaging links, public-safe locations
    for row in DEMO_SHOWCASE_EVENTS:
        slug = f"{DEMO_EVENT_SLUG_PREFIX}{row['key']}"
        ev = db_session.scalar(select(Event).where(Event.slug == slug))
        assert ev is not None, slug
        assert ev.title == row["title"]
        assert ev.banner_url
        assert ev.location_visibility in {"full_public", "area_only"}
        assert len(ev.ticket_types) >= 1
        ticket_n = db_session.scalar(
            select(func.count())
            .select_from(TicketModel)
            .where(TicketModel.event_id == ev.id)
        )
        assert (ticket_n or 0) >= 1, slug
        linked = db_session.scalar(
            select(func.count())
            .select_from(MessageThread)
            .where(MessageThread.related_event_id == ev.id)
        )
        assert (linked or 0) >= 1, f"no message thread for {slug}"
        if row["key"] in SHOWCASE_COMPLETED_KEYS:
            assert ev.status == "completed"
            checked = db_session.scalar(
                select(func.count())
                .select_from(TicketModel)
                .where(
                    TicketModel.event_id == ev.id,
                    TicketModel.status == "checked_in",
                )
            )
            assert (checked or 0) >= 1, slug
            reviews = db_session.scalar(
                select(func.count())
                .select_from(VerifiedReview)
                .where(VerifiedReview.event_id == ev.id)
            )
            assert (reviews or 0) >= 1, slug
        else:
            assert ev.status == "published"
        if row["key"] in vault_linked_keys:
            vault_n = db_session.scalar(
                select(func.count())
                .select_from(VaultItem)
                .where(VaultItem.related_event_id == ev.id)
            )
            assert (vault_n or 0) >= 1, f"missing Vault link for {slug}"
        # Public serializer must not leak hidden street addresses for area_only
        if ev.location_visibility == "area_only":
            data = {
                "address": ev.address,
                "venue_name": ev.venue_name,
                "venue": {
                    "name": ev.venue_name,
                    "address": ev.address,
                    "city": ev.city,
                    "state": ev.state,
                },
            }
            scrubbed = apply_location_privacy(ev, data, access="public")
            assert scrubbed.get("address") is None
            assert "Admiralty" not in (scrubbed.get("venue_name") or "")
            assert "Awolowo" not in (scrubbed.get("venue_name") or "")
            venue = scrubbed.get("venue") or {}
            if isinstance(venue, dict):
                assert venue.get("address") is None

    thread_count = db_session.scalar(select(func.count()).select_from(MessageThread))
    message_count = db_session.scalar(select(func.count()).select_from(Message))
    assert (thread_count or 0) >= 10
    assert (message_count or 0) >= 20
    assert (db_session.scalar(select(func.count()).select_from(MessageReport)) or 0) >= 3
    report_statuses = set(
        db_session.scalars(select(MessageReport.status)).all()
    )
    assert "reviewing" in report_statuses
    assert "resolved" in report_statuses
    assert "open" in report_statuses
    resolved_demo = db_session.scalar(
        select(MessageReport).where(MessageReport.status == "resolved")
    )
    assert resolved_demo is not None
    assert resolved_demo.admin_notes == "Demo resolved report."
    assert resolved_demo.resolved_by_user_id is not None
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(Message)
            .where(Message.moderation_status == "hidden")
        )
        or 0
    ) >= 1
    assert (db_session.scalar(select(func.count()).select_from(MessageBlock)) or 0) >= 1
    assert (
        db_session.scalar(select(func.count()).select_from(InAppNotification)) or 0
    ) >= 7
    # Privacy: demo bodies must not leak contact/payment/private data
    from app.demo.messaging_privacy import DEMO_MESSAGE_BANNED_SUBSTRINGS

    bodies = " ".join(db_session.scalars(select(Message.body)).all()).lower()
    for banned in DEMO_MESSAGE_BANNED_SUBSTRINGS:
        assert banned not in bodies, banned
    # Prefer on-platform guidance
    assert "open your pàdéyá ticket" in bodies
    assert "use your qr code at check-in" in bodies
    assert "refresh your vault page" in bodies
    assert "check your dashboard" in bodies
    assert "your ticket-holder vault access should unlock" in bodies
    assert "whatsapp" not in bodies
    assert "outside padeya" not in bodies

    # Conversation 1: Tolu ↔ DJ Maze / Afrobeats Night Live (fan read, host unread)
    from app.messaging import constants as MC
    from app.messaging.service import _thread_unread
    from app.passport.models import FanPassport as FanPassportModel

    tolu = get_user_by_email(db_session, f"fan1@{DEMO_EMAIL_DOMAIN}")
    assert tolu is not None
    tolu_pp = db_session.scalar(
        select(FanPassportModel).where(FanPassportModel.user_id == tolu.id)
    )
    assert tolu_pp is not None and tolu_pp.username == "toluwave"
    afrobeats_ev = db_session.scalar(
        select(Event).where(Event.slug == f"{DEMO_EVENT_SLUG_PREFIX}afrobeats-night-live")
    )
    assert afrobeats_ev is not None
    conv1 = db_session.scalar(
        select(MessageThread).where(
            MessageThread.fan_user_id == tolu.id,
            MessageThread.host_id == maze.id,
        )
    )
    assert conv1 is not None
    assert conv1.status == "active"
    assert conv1.related_event_id == afrobeats_ev.id
    assert conv1.related_ticket_id is not None
    assert conv1.related_order_id is not None
    assert conv1.host_user_id == maze.user_id
    assert conv1.initiated_by_user_id is not None
    assert conv1.last_message_at is not None
    assert _thread_unread(conv1, as_fan=True) is False
    assert _thread_unread(conv1, as_fan=False) is True
    conv1_msgs = list(
        db_session.scalars(
            select(Message)
            .where(Message.thread_id == conv1.id)
            .order_by(Message.created_at.asc())
        ).all()
    )
    conv1_bodies = [m.body for m in conv1_msgs]
    assert conv1_msgs[0].message_type == "system"
    assert conv1_bodies[0] == "This conversation is connected to Afrobeats Night Live."
    assert conv1_bodies[-1] == "Thanks — I’ll aim for 7:15 PM so check-in is easy."
    assert "Afrobeats Night Live" in conv1_bodies[1]
    assert "7 PM" in conv1_bodies[2]
    assert "open your pàdéyá ticket" in conv1_bodies[4].lower()
    assert "use your qr code at check-in" in conv1_bodies[4].lower()
    assert "phone" not in conv1_bodies[3].lower()
    assert "phone" not in conv1_bodies[4].lower()
    assert len(conv1_bodies) == 9
    assert "Done. They’ve both booked now." in conv1_bodies
    from app.messaging.models import MessageAttachment

    conv1_atts = {
        a.original_filename
        for a in db_session.scalars(
            select(MessageAttachment).where(
                MessageAttachment.thread_id == conv1.id,
                MessageAttachment.deleted_at.is_(None),
            )
        ).all()
    }
    assert "afrobeats-entry-map.png" in conv1_atts

    # Conversation 2: Amaka ↔ DJ Maze / Detty Friday Rooftop (unread for fan)
    amaka = get_user_by_email(db_session, f"fan2@{DEMO_EMAIL_DOMAIN}")
    assert amaka is not None
    amaka_pp = db_session.scalar(
        select(FanPassportModel).where(FanPassportModel.user_id == amaka.id)
    )
    assert amaka_pp is not None and amaka_pp.username == "amakaconcerts"
    detty_ev = db_session.scalar(
        select(Event).where(Event.slug == f"{DEMO_EVENT_SLUG_PREFIX}detty-friday-live")
    )
    assert detty_ev is not None
    from app.crm.models import HostFollower

    assert (
        db_session.scalar(
            select(HostFollower.id).where(
                HostFollower.user_id == amaka.id,
                HostFollower.host_id == maze.id,
            )
        )
        is not None
    )
    conv2 = db_session.scalar(
        select(MessageThread).where(
            MessageThread.fan_user_id == amaka.id,
            MessageThread.host_id == maze.id,
        )
    )
    assert conv2 is not None
    assert conv2.status == "active"
    assert conv2.related_event_id == detty_ev.id
    assert conv2.related_ticket_id is not None
    assert conv2.related_order_id is not None
    assert conv2.initiated_by_user_id == maze.user_id
    assert _thread_unread(conv2, as_fan=True) is True
    assert _thread_unread(conv2, as_fan=False) is False
    conv2_bodies = list(
        db_session.scalars(
            select(Message.body)
            .where(Message.thread_id == conv2.id)
            .order_by(Message.created_at.asc())
        ).all()
    )
    assert len(conv2_bodies) == 4
    assert "Detty Friday Rooftop" in conv2_bodies[0]
    assert "Pàdéyá ticket" in conv2_bodies[1]
    assert "Vault drop" in conv2_bodies[3]
    assert conv2_bodies[-1].startswith("Also, there will be a ticket-holder Vault drop")

    # Conversation 3: Sade ↔ DJ Maze / Mainland After Dark (event inquiry, no ticket)
    sade = get_user_by_email(db_session, f"fan4@{DEMO_EMAIL_DOMAIN}")
    assert sade is not None
    sade_pp = db_session.scalar(
        select(FanPassportModel).where(FanPassportModel.user_id == sade.id)
    )
    assert sade_pp is not None and sade_pp.username == "sadecomedy"
    comedy_host = db_session.scalar(select(Host).where(Host.slug == "lagoscomedyhub"))
    after_dark_ev_sade = db_session.scalar(
        select(Event).where(Event.slug == f"{DEMO_EVENT_SLUG_PREFIX}mainland-after-dark")
    )
    assert comedy_host is not None and after_dark_ev_sade is not None
    conv3 = db_session.scalar(
        select(MessageThread).where(
            MessageThread.fan_user_id == sade.id,
            MessageThread.host_id == maze.id,
        )
    )
    assert conv3 is not None
    assert conv3.status == "active"
    assert conv3.related_event_id == after_dark_ev_sade.id
    assert conv3.related_ticket_id is None
    assert conv3.related_order_id is None
    assert conv3.initiated_by_user_id == sade.id
    conv3_bodies = list(
        db_session.scalars(
            select(Message.body)
            .where(Message.thread_id == conv3.id)
            .order_by(Message.created_at.asc())
        ).all()
    )
    assert len(conv3_bodies) == 4
    assert "Mainland After Dark" in conv3_bodies[0]
    assert "relaxed night" in conv3_bodies[1].lower()
    assert conv3_bodies[-1] == "Great. See you at check-in."

    # Conversation 11: Chidi ↔ Tech Connect / Product Demo Night (Vault, no locked payload)
    chidi = get_user_by_email(db_session, f"fan3@{DEMO_EMAIL_DOMAIN}")
    assert chidi is not None
    chidi_pp = db_session.scalar(
        select(FanPassportModel).where(FanPassportModel.user_id == chidi.id)
    )
    assert chidi_pp is not None and chidi_pp.username == "chiditech"
    tech_host = db_session.scalar(select(Host).where(Host.slug == "techconnectafrica"))
    past_tech_ev = db_session.scalar(
        select(Event).where(Event.slug == f"{DEMO_EVENT_SLUG_PREFIX}startup-demo-evening")
    )
    assert tech_host is not None and past_tech_ev is not None
    assert (
        db_session.scalar(
            select(HostFollower.id).where(
                HostFollower.user_id == chidi.id,
                HostFollower.host_id == tech_host.id,
            )
        )
        is not None
    )
    past_checkin = db_session.scalar(
        select(Ticket).where(
            Ticket.buyer_user_id == chidi.id,
            Ticket.event_id == past_tech_ev.id,
            Ticket.status == "checked_in",
        )
    )
    assert past_checkin is not None
    conv11 = db_session.scalar(
        select(MessageThread).where(
            MessageThread.fan_user_id == chidi.id,
            MessageThread.host_id == tech_host.id,
        )
    )
    assert conv11 is not None
    assert conv11.status == "active"
    assert conv11.related_event_id == past_tech_ev.id
    assert conv11.related_ticket_id == past_checkin.id
    conv11_msgs = list(
        db_session.scalars(
            select(Message)
            .where(Message.thread_id == conv11.id)
            .order_by(Message.created_at.asc())
        ).all()
    )
    assert len(conv11_msgs) == 5
    assert "slide deck in Vault" in conv11_msgs[0].body
    assert (
        "Your ticket-holder Vault access should unlock"
        in conv11_msgs[1].body
    )
    assert "replay" in conv11_msgs[2].body.lower()
    assert "Refresh your Vault page" in conv11_msgs[3].body
    assert "Check your dashboard" in conv11_msgs[3].body
    assert conv11_msgs[4].sender_role == "system"
    assert conv11_msgs[4].message_type == "system"
    assert conv11_msgs[4].body == "Refresh your Vault page."
    joined11 = " ".join(m.body for m in conv11_msgs).lower()
    for banned in (
        "locked demo body",
        "example.com/demo-secret",
        "/demo/vault/",
        "whatsapp",
        "password",
        "http://",
    ):
        assert banned not in joined11, banned

    # Conversation 5: Ada ↔ Praise / Worship Night (message request, pending)
    ada = get_user_by_email(db_session, f"fan7@{DEMO_EMAIL_DOMAIN}")
    assert ada is not None
    ada_pp = db_session.scalar(
        select(FanPassportModel).where(FanPassportModel.user_id == ada.id)
    )
    assert ada_pp is not None and ada_pp.username == "adafirsttimer"
    praise_host = db_session.scalar(select(Host).where(Host.slug == "praiseexperience"))
    worship_ev = db_session.scalar(
        select(Event).where(Event.slug == f"{DEMO_EVENT_SLUG_PREFIX}worship-under-stars")
    )
    assert praise_host is not None and worship_ev is not None
    # No prior follow relationship for a true message request
    assert (
        db_session.scalar(
            select(HostFollower.id).where(
                HostFollower.user_id == ada.id,
                HostFollower.host_id == praise_host.id,
            )
        )
        is None
    )
    conv5 = db_session.scalar(
        select(MessageThread).where(
            MessageThread.fan_user_id == ada.id,
            MessageThread.host_id == praise_host.id,
        )
    )
    assert conv5 is not None
    assert conv5.status == MC.THREAD_STATUS_REQUEST
    assert conv5.accepted_at is None
    assert conv5.related_event_id == worship_ev.id
    assert conv5.related_ticket_id is None
    assert conv5.initiated_by_user_id == ada.id
    assert _thread_unread(conv5, as_fan=False) is True
    conv5_msgs = list(
        db_session.scalars(
            select(Message)
            .where(Message.thread_id == conv5.id)
            .order_by(Message.created_at.asc())
        ).all()
    )
    assert len(conv5_msgs) == 2
    assert "first Pàdéyá event" in conv5_msgs[0].body
    assert conv5_msgs[0].sender_role == "fan"
    assert conv5_msgs[1].message_type == "system"
    assert conv5_msgs[1].sender_role == "system"
    assert conv5_msgs[1].body == "This conversation is a message request."

    # Conversation 6 (inbox QA): Tolu ↔ Mainland Vibes / Food & Culture Fest
    mainland_host = db_session.scalar(select(Host).where(Host.slug == "mainlandvibes"))
    food_ev = db_session.scalar(
        select(Event).where(Event.slug == f"{DEMO_EVENT_SLUG_PREFIX}food-and-flow")
    )
    assert mainland_host is not None and food_ev is not None
    conv6 = db_session.scalar(
        select(MessageThread).where(
            MessageThread.fan_user_id == tolu.id,
            MessageThread.host_id == mainland_host.id,
        )
    )
    assert conv6 is not None
    assert conv6.status == "active"
    assert conv6.related_event_id == food_ev.id
    conv6_bodies = list(
        db_session.scalars(
            select(Message.body)
            .where(Message.thread_id == conv6.id)
            .order_by(Message.created_at.asc())
        ).all()
    )
    assert len(conv6_bodies) == 5
    assert "premium experience" in conv6_bodies[0].lower()
    assert "priority entry" in conv6_bodies[1].lower()
    assert "Pàdéyá" in conv6_bodies[3]
    assert "dashboard" in conv6_bodies[-1].lower()
    joined6 = " ".join(conv6_bodies).lower()
    for banned in ("ngn", "₦", "paystack", "bank", "transfer", "whatsapp", "@"):
        assert banned not in joined6, banned

    # Conversation 7: Mira ↔ DJ Maze / Mainland After Dark (archived for fan + host)
    mira = get_user_by_email(db_session, f"fan6@{DEMO_EMAIL_DOMAIN}")
    assert mira is not None
    mira_pp = db_session.scalar(
        select(FanPassportModel).where(FanPassportModel.user_id == mira.id)
    )
    assert mira_pp is not None and mira_pp.username == "miralagos"
    after_dark_ev = db_session.scalar(
        select(Event).where(Event.slug == f"{DEMO_EVENT_SLUG_PREFIX}mainland-after-dark")
    )
    assert after_dark_ev is not None
    conv7 = db_session.scalar(
        select(MessageThread).where(
            MessageThread.fan_user_id == mira.id,
            MessageThread.host_id == maze.id,
        )
    )
    assert conv7 is not None
    assert conv7.status == "active"
    assert conv7.fan_archived_at is not None
    assert conv7.host_archived_at is not None
    assert conv7.related_event_id == after_dark_ev.id
    assert conv7.fan_last_read_at is not None
    assert conv7.host_last_read_at is not None
    last7 = db_session.get(Message, conv7.last_message_id)
    assert last7 is not None
    assert last7.message_type == "system"
    assert last7.body == "This conversation was archived."
    assert conv7.fan_last_read_at >= last7.created_at
    assert conv7.host_last_read_at >= last7.created_at
    conv7_bodies = list(
        db_session.scalars(
            select(Message.body)
            .where(Message.thread_id == conv7.id)
            .order_by(Message.created_at.asc())
        ).all()
    )
    assert len(conv7_bodies) == 5
    assert "check-in was smooth" in conv7_bodies[0].lower()
    assert "Legacy Page" in conv7_bodies[1]
    assert conv7_bodies[2] == "I left a review already."
    assert conv7_bodies[3] == "Thank you. We appreciate it."
    assert conv7_bodies[4] == "This conversation was archived."

    # Conversation 8: Bayo ↔ Tech Connect / Product Demo Night (fan report, reviewing)
    bayo = get_user_by_email(db_session, f"fan8@{DEMO_EMAIL_DOMAIN}")
    assert bayo is not None
    bayo_pp = db_session.scalar(
        select(FanPassportModel).where(FanPassportModel.user_id == bayo.id)
    )
    assert bayo_pp is not None and bayo_pp.username == "bayocampus"
    tech_host = db_session.scalar(
        select(Host).where(Host.slug == "techconnectafrica")
    )
    product_demo_ev = db_session.scalar(
        select(Event).where(
            Event.slug == f"{DEMO_EVENT_SLUG_PREFIX}startup-demo-evening"
        )
    )
    assert tech_host is not None and product_demo_ev is not None
    conv8 = db_session.scalar(
        select(MessageThread).where(
            MessageThread.fan_user_id == bayo.id,
            MessageThread.host_id == tech_host.id,
        )
    )
    assert conv8 is not None
    assert conv8.status == "reported"
    assert conv8.related_event_id == product_demo_ev.id
    assert conv8.related_ticket_id is None
    assert conv8.related_order_id is None
    conv8_bodies = list(
        db_session.scalars(
            select(Message.body)
            .where(Message.thread_id == conv8.id)
            .order_by(Message.created_at.asc())
        ).all()
    )
    assert len(conv8_bodies) == 6
    assert "demo night ticket" in conv8_bodies[0].lower()
    assert conv8_bodies[4] == "Okay, thank you."
    assert conv8_bodies[5] == "A report was submitted for this conversation."
    joined8 = " ".join(conv8_bodies).lower()
    for banned in ("ngn", "₦", "paystack", "bank", "transfer", "order #", "whatsapp"):
        assert banned not in joined8, banned
    report8 = db_session.scalar(
        select(MessageReport).where(
            MessageReport.thread_id == conv8.id,
            MessageReport.reporter_user_id == bayo.id,
        )
    )
    assert report8 is not None
    assert report8.reported_user_id == tech_host.user_id
    assert report8.reason == "other"
    assert report8.details == "Demo report example for moderation testing."
    assert report8.status == "reviewing"
    assert report8.admin_notes is not None
    assert "Demo admin notes" in report8.admin_notes
    hidden_msg = db_session.scalar(
        select(Message).where(
            Message.thread_id == conv8.id,
            Message.moderation_status == "hidden",
        )
    )
    assert hidden_msg is not None
    assert hidden_msg.status == "hidden"
    assert hidden_msg.body == "Can I still attend if I arrive late?"
    conv8_atts = {
        a.original_filename
        for a in db_session.scalars(
            select(MessageAttachment).where(
                MessageAttachment.thread_id == conv8.id,
                MessageAttachment.deleted_at.is_(None),
            )
        ).all()
    }
    assert "demo-moderation-sample.png" in conv8_atts

    # Conversation 9: Tolu ↔ Lagos Comedy Hub / Sunday Comedy Room (blocked UI)
    tolu = get_user_by_email(db_session, f"fan1@{DEMO_EMAIL_DOMAIN}")
    assert tolu is not None
    comedy_host = db_session.scalar(
        select(Host).where(Host.slug == "lagoscomedyhub")
    )
    sunday_ev = db_session.scalar(
        select(Event).where(
            Event.slug == f"{DEMO_EVENT_SLUG_PREFIX}island-comedy-night"
        )
    )
    assert comedy_host is not None and sunday_ev is not None
    conv9 = db_session.scalar(
        select(MessageThread).where(
            MessageThread.fan_user_id == tolu.id,
            MessageThread.host_id == comedy_host.id,
        )
    )
    assert conv9 is not None
    assert conv9.status == "blocked"
    assert conv9.related_event_id == sunday_ev.id
    conv9_msgs = list(
        db_session.scalars(
            select(Message)
            .where(Message.thread_id == conv9.id)
            .order_by(Message.created_at.asc())
        ).all()
    )
    assert len(conv9_msgs) == 3
    assert conv9_msgs[0].body == "Can I ask about Sunday Comedy Room?"
    assert conv9_msgs[1].body == "Sure. What would you like to know?"
    assert conv9_msgs[2].sender_role == "system"
    assert conv9_msgs[2].message_type == "system"
    assert conv9_msgs[2].body == "This user has been blocked."
    block9 = db_session.scalar(
        select(MessageBlock).where(
            MessageBlock.blocker_user_id == tolu.id,
            MessageBlock.blocked_user_id == comedy_host.user_id,
        )
    )
    assert block9 is not None
    assert block9.reason == "Demo blocked conversation"
    assert block9.host_id == comedy_host.id
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(MessageReport)
            .where(MessageReport.thread_id == conv9.id)
        )
        or 0
    ) == 0

    # Conversation 10: Amaka ↔ Lagos Comedy Hub — Legacy Page (follower, no event)
    amaka = get_user_by_email(db_session, f"fan2@{DEMO_EMAIL_DOMAIN}")
    assert amaka is not None
    amaka_pp = db_session.scalar(
        select(FanPassportModel).where(FanPassportModel.user_id == amaka.id)
    )
    assert amaka_pp is not None and amaka_pp.username == "amakaconcerts"
    assert comedy_host is not None
    follow10 = db_session.scalar(
        select(HostFollower.id).where(
            HostFollower.user_id == amaka.id,
            HostFollower.host_id == comedy_host.id,
        )
    )
    assert follow10 is not None
    conv10 = db_session.scalar(
        select(MessageThread).where(
            MessageThread.fan_user_id == amaka.id,
            MessageThread.host_id == comedy_host.id,
        )
    )
    assert conv10 is not None
    assert conv10.status == "active"
    assert conv10.related_ticket_id is None
    conv10_bodies = list(
        db_session.scalars(
            select(Message.body)
            .where(Message.thread_id == conv10.id)
            .order_by(Message.created_at.asc())
        ).all()
    )
    assert len(conv10_bodies) == 3
    assert "Legacy Page" in conv10_bodies[0]
    assert "Vault drops" in conv10_bodies[1]
    assert conv10_bodies[2] == "Nice. I’ll keep checking."

    # Conversation 12: Ada ↔ Mainland Vibes / Lagos Creative Market (event discovery)
    ada12 = get_user_by_email(db_session, f"fan7@{DEMO_EMAIL_DOMAIN}")
    assert ada12 is not None
    mainland_host12 = db_session.scalar(
        select(Host).where(Host.slug == "mainlandvibes")
    )
    creative_ev = db_session.scalar(
        select(Event).where(
            Event.slug == f"{DEMO_EVENT_SLUG_PREFIX}mainland-vibes-summer"
        )
    )
    assert mainland_host12 is not None and creative_ev is not None
    assert (
        db_session.scalar(
            select(HostFollower.id).where(
                HostFollower.user_id == ada12.id,
                HostFollower.host_id == mainland_host12.id,
            )
        )
        is not None
    )
    conv12 = db_session.scalar(
        select(MessageThread).where(
            MessageThread.fan_user_id == ada12.id,
            MessageThread.host_id == mainland_host12.id,
        )
    )
    assert conv12 is not None
    assert conv12.status == "active"
    assert conv12.related_event_id == creative_ev.id
    assert conv12.related_ticket_id is None
    conv12_bodies = list(
        db_session.scalars(
            select(Message.body)
            .where(Message.thread_id == conv12.id)
            .order_by(Message.created_at.asc())
        ).all()
    )
    assert len(conv12_bodies) == 4
    assert "attending alone" in conv12_bodies[0].lower()
    assert "relaxed daytime" in conv12_bodies[1].lower()
    assert conv12_bodies[2] == "Great. I’ll book one ticket."
    assert "Check your dashboard" in conv12_bodies[3]
    assert "Open your Pàdéyá ticket" in conv12_bodies[3]
    joined12 = " ".join(conv12_bodies).lower()
    for banned in ("whatsapp", "street", "ngn", "₦", "paystack", "@gmail"):
        assert banned not in joined12, banned

    # System message UI samples (distinct type/role; no private data)
    expected_system = {
        "This conversation is connected to Afrobeats Night Live.",
        "This conversation is a message request.",
        "This conversation was archived.",
        "This user has been blocked.",
        "A report was submitted for this conversation.",
        "Refresh your Vault page.",
    }
    system_bodies = set(
        db_session.scalars(
            select(Message.body).where(
                Message.message_type == "system",
                Message.sender_role == "system",
            )
        ).all()
    )
    assert expected_system <= system_bodies
    for body in expected_system:
        low = body.lower()
        for banned in ("@", "ngn", "₦", "paystack", "whatsapp", "bank"):
            assert banned not in low, (body, banned)

    # Inbox QA states (fan + host dashboards)
    praise_host = db_session.scalar(select(Host).where(Host.slug == "praiseexperience"))
    assert praise_host is not None

    def _fan_threads(uid):
        return list(
            db_session.scalars(
                select(MessageThread).where(MessageThread.fan_user_id == uid)
            ).all()
        )

    def _host_threads(hid):
        return list(
            db_session.scalars(
                select(MessageThread).where(MessageThread.host_id == hid)
            ).all()
        )

    tolu_threads = _fan_threads(tolu.id)
    assert len(tolu_threads) == 5
    assert (
        sum(
            1
            for t in tolu_threads
            if t.status == "active" and t.fan_archived_at is None
        )
        == 3
    )
    assert sum(1 for t in tolu_threads if t.fan_archived_at is not None) == 1
    assert sum(1 for t in tolu_threads if t.status == "blocked") == 1
    assert any(
        t.status == "active"
        and t.fan_archived_at is None
        and _thread_unread(t, as_fan=True)
        for t in tolu_threads
    ), "Tolu should have 1 unread host reply"

    amaka_threads = _fan_threads(amaka.id)
    assert len(amaka_threads) == 2
    assert all(t.status == "active" and t.fan_archived_at is None for t in amaka_threads)
    assert sum(1 for t in amaka_threads if _thread_unread(t, as_fan=True)) == 1
    assert any(
        "Vault" in " ".join(
            db_session.scalars(
                select(Message.body).where(Message.thread_id == t.id)
            ).all()
        )
        or "Vault" in (t.subject or "")
        for t in amaka_threads
    ), "Amaka should have a Vault-related conversation"

    chidi_threads = _fan_threads(chidi.id)
    # Host inbox threads (Comedy + Tech). Fan Connect Chidi↔Bayo may use
    # fan_user_id or fan_b_user_id depending on UUID order, so only assert host floor.
    assert (
        sum(1 for t in chidi_threads if t.status == "active" and t.fan_archived_at is None)
        >= 2
    )
    assert sum(1 for t in chidi_threads if t.status == "reported") == 1

    maze_threads = _host_threads(maze.id)
    assert len(maze_threads) == 4
    assert sum(1 for t in maze_threads if _thread_unread(t, as_fan=False)) == 1
    assert sum(1 for t in maze_threads if t.host_archived_at is not None) == 1
    assert any(
        t.related_event_id is not None and t.related_ticket_id is None and t.status == "active"
        for t in maze_threads
        if t.host_archived_at is None
    ), "Maze event inquiry"
    assert any(
        t.related_ticket_id is not None for t in maze_threads
    ), "Maze ticket-holder conversation"

    comedy_threads = _host_threads(comedy_host.id)
    assert len(comedy_threads) == 3
    assert sum(1 for t in comedy_threads if t.status == "blocked") == 1
    assert any(
        t.related_event_id is None and t.status == "active" for t in comedy_threads
    ) or any(
        t.fan_user_id == amaka.id and t.status == "active" for t in comedy_threads
    ), "Comedy general follower conversation"
    assert any(
        t.related_event_id is not None
        and t.related_ticket_id is None
        and t.status == "active"
        for t in comedy_threads
    ), "Comedy event inquiry"

    tech_threads = _host_threads(tech_host.id)
    assert len(tech_threads) == 3
    assert any("Vault" in (t.subject or "") for t in tech_threads)
    assert sum(1 for t in tech_threads if t.status == "reported") == 1
    assert any(t.related_ticket_id is not None for t in tech_threads)

    praise_threads = _host_threads(praise_host.id)
    assert sum(1 for t in praise_threads if t.status == "request") == 1

    mainland_threads = _host_threads(mainland_host.id)
    assert (
        sum(1 for t in mainland_threads if t.status == "active" and t.fan_archived_at is None)
        == 2
    )

    # Rich messaging seed: required thread type coverage
    all_threads = list(db_session.scalars(select(MessageThread)).all())
    assert any(t.status == MC.THREAD_STATUS_ACTIVE for t in all_threads)
    assert any(t.status == MC.THREAD_STATUS_REQUEST for t in all_threads)
    assert any(t.status == MC.THREAD_STATUS_REPORTED for t in all_threads)
    assert any(t.status == MC.THREAD_STATUS_BLOCKED for t in all_threads)
    assert any(t.fan_archived_at is not None for t in all_threads)
    assert any(t.host_archived_at is not None for t in all_threads)
    assert any(
        t.related_event_id is not None and _thread_unread(t, as_fan=False)
        for t in all_threads
    )
    assert any(
        t.related_event_id is not None and _thread_unread(t, as_fan=True)
        for t in all_threads
    )
    assert any(t.related_ticket_id is not None for t in all_threads)
    assert any(
        t.initiated_by_user_id == t.host_user_id for t in all_threads
    ), "expected host-initiated thread"
    vault_hit = any(
        "Vault" in (t.subject or "") or "vault" in (t.subject or "").lower()
        for t in all_threads
    )
    assert vault_hit, "expected Vault access question thread"

    # Message notifications: safe summaries, thread links, read + unread
    notes = list(db_session.scalars(select(InAppNotification)).all())
    titles = {n.title for n in notes}
    expected_titles = {
        "New message from DJ Maze",
        "Message request from Ada First Timer",
        "Host replied to your event question",
        "New message about Afrobeats Night Live",
        "Your message report is being reviewed",
        "Your conversation was archived",
        "New Vault-related reply from Tech Connect Africa",
    }
    assert expected_titles <= titles
    assert any(n.read_at is None for n in notes), "expected unread notifications"
    assert any(n.read_at is not None for n in notes), "expected read notifications"
    for n in notes:
        if n.title not in expected_titles and n.thread_id is None:
            continue
        if n.title in expected_titles:
            assert n.thread_id is not None, n.title
            assert n.link_path is not None and str(n.thread_id) in n.link_path, n.title
            assert n.link_path.startswith(("/dashboard/messages/", "/host/messages/"))
            low = f"{n.title} {n.body}".lower()
            for banned in (
                "whatsapp",
                "paystack",
                "bank",
                "+234",
                "@demo.",
                "locked demo body",
                "password",
            ):
                assert banned not in low, (n.title, banned)
            # Summaries only — not full scripted conversation dumps
            assert len(n.body) <= 240
            assert "Should I have access to the slide deck" not in n.body
            assert "Buy tickets cheaper" not in n.body

    # Idempotent messaging seed (direct re-run creates zero new threads)
    from app.demo.messaging_seed import seed_messaging_demo
    from app.hosts.models import Host as HostModel

    hosts_map = {
        h.slug: h for h in db_session.scalars(select(HostModel)).all() if h.slug
    }
    events_map = {
        e.slug.replace(DEMO_EVENT_SLUG_PREFIX, "", 1): e
        for e in db_session.scalars(
            select(Event).where(Event.slug.startswith(DEMO_EVENT_SLUG_PREFIX))
        ).all()
    }
    users_map = {
        u.email: u
        for u in db_session.scalars(
            select(User).where(User.email.like(f"%@{DEMO_EMAIL_DOMAIN}"))
        ).all()
    }
    again = seed_messaging_demo(
        db_session, users=users_map, hosts=hosts_map, events=events_map
    )
    assert again["threads"] == 0
    thread_count_2 = db_session.scalar(select(func.count()).select_from(MessageThread))
    assert thread_count_2 == thread_count

    events = list(
        db_session.scalars(
            select(Event).where(Event.slug.startswith(DEMO_EVENT_SLUG_PREFIX))
        ).all()
    )
    assert len(events) >= 20

    tickets = list(
        db_session.scalars(
            select(Ticket)
            .join(Event)
            .where(Event.slug.startswith(DEMO_EVENT_SLUG_PREFIX))
        ).all()
    )
    checked = [t for t in tickets if t.status == "checked_in"]
    assert len(checked) >= 20

    # Checked-in tickets used for reviews should stay consistent
    for review in db_session.scalars(select(VerifiedReview)).all():
        ticket = db_session.get(Ticket, review.ticket_id)
        assert ticket is not None
        assert ticket.status == "checked_in"
        assert ticket.event_id == review.event_id

    # Vault catalog: mixed access types across demo hosts
    from sqlalchemy.orm import selectinload

    from app.vault.models import VaultPurchase, VaultView

    expected_vault = {
        "djmaze": {
            "unreleased-set",
            "bts-afrobeats",
            "vip-gallery",
            "after-dark-teaser",
            "detty-friday-recap",
            "admin-hidden-drop",
        },
        "lagoscomedyhub": {"comedy-early", "backstage-comedy"},
        "mainlandvibes": {"recap-video", "secret-location"},
        "techconnectafrica": {
            "founder-deck",
            "product-demo-replay",
            "product-demo-deck",
        },
        "praiseexperience": {"worship-rehearsal", "vip-choir-backstage"},
    }
    access_types_seen: set[str] = set()
    for host_slug, slugs in expected_vault.items():
        host_row = db_session.scalar(select(Host).where(Host.slug == host_slug))
        assert host_row is not None, host_slug
        items = list(
            db_session.scalars(
                select(VaultItem)
                .where(VaultItem.host_id == host_row.id)
                .options(selectinload(VaultItem.access_rule))
            ).all()
        )
        have = {i.slug for i in items}
        assert slugs.issubset(have), f"{host_slug}: missing {slugs - have}"
        for item in items:
            if item.slug in slugs and item.access_rule:
                access_types_seen.add(item.access_rule.access_type)

    for required in (
        "free",
        "followers_only",
        "one_time_unlock",
        "ticket_holder_only",
        "checked_in_attendee_only",
        "vip_ticket_holder_only",
        "invite_only",
    ):
        assert required in access_types_seen, f"missing access_type {required}"

    hidden = db_session.scalar(
        select(VaultItem).where(
            VaultItem.slug == "admin-hidden-drop",
            VaultItem.host_id == maze.id,
        )
    )
    assert hidden is not None
    assert hidden.status == "hidden_by_admin"
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as hidden_exc:
        get_public_vault_item(
            db_session, username="djmaze", item_slug="admin-hidden-drop", user=None
        )
    assert hidden_exc.value.status_code == 404

    # Demo Buyer paid unlock + views + second paid unlock (fan) for earnings
    buyer_purchase = db_session.scalar(
        select(VaultPurchase).where(
            VaultPurchase.user_id == buyer.id,
            VaultPurchase.status == "paid",
        )
    )
    assert buyer_purchase is not None
    views = (
        db_session.scalar(select(func.count()).select_from(VaultView)) or 0
    )
    assert views >= 10

    # Locked Vault body must not leak on public serialize without access
    locked = db_session.scalar(
        select(VaultItem)
        .where(
            VaultItem.slug == "unreleased-set",
            VaultItem.host_id == maze.id,
        )
        .options(selectinload(VaultItem.access_rule))
    )
    assert locked is not None
    assert locked.body and "LOCKED" in locked.body
    public = get_public_vault_item(
        db_session, username="djmaze", item_slug="unreleased-set", user=None
    )
    assert public.get("has_access") is False
    assert public.get("body") in (None, "")
    assert "LOCKED DEMO BODY" not in str(public.get("body") or "")
    serialized = serialize_item(db_session, locked, user=None)
    assert serialized.get("body") in (None, "")

    # Buyer can unlock the paid set they purchased
    buyer_view = get_public_vault_item(
        db_session, username="djmaze", item_slug="unreleased-set", user=buyer
    )
    assert buyer_view.get("has_access") is True
    assert "LOCKED DEMO BODY" in str(buyer_view.get("body") or "")

    # Demo analytics: varied 90d stream + rollups; purchases never exceed tickets
    from app.analytics.models import AnalyticsEvent
    from app.analytics.rollup_models import EventDailyAnalytics
    from app.analytics.taxonomy import TrackedAction
    from app.demo.analytics_seed import MARKER_KEY, MARKER_TYPE

    analytics_marker = db_session.scalar(
        select(DemoEntityMarker).where(
            DemoEntityMarker.entity_type == MARKER_TYPE,
            DemoEntityMarker.entity_key == MARKER_KEY,
        )
    )
    assert analytics_marker is not None

    maze_event = db_session.scalar(
        select(Event).where(Event.slug == f"{DEMO_EVENT_SLUG_PREFIX}afrobeats-night-live")
    )
    assert maze_event is not None
    impressions = (
        db_session.scalar(
            select(func.count())
            .select_from(AnalyticsEvent)
            .where(
                AnalyticsEvent.target_event_id == maze_event.id,
                AnalyticsEvent.event_name == TrackedAction.EVENT_CARD_IMPRESSION,
            )
        )
        or 0
    )
    assert impressions >= 100

    issued = (
        db_session.scalar(
            select(func.count())
            .select_from(AnalyticsEvent)
            .where(
                AnalyticsEvent.target_event_id == maze_event.id,
                AnalyticsEvent.event_name == TrackedAction.TICKET_ISSUED,
            )
        )
        or 0
    )
    maze_tickets = (
        db_session.scalar(
            select(func.count())
            .select_from(Ticket)
            .where(
                Ticket.event_id == maze_event.id,
                Ticket.status.in_(("active", "checked_in")),
            )
        )
        or 0
    )
    assert issued <= maze_tickets

    daily_rollups = (
        db_session.scalar(
            select(func.count())
            .select_from(EventDailyAnalytics)
            .where(EventDailyAnalytics.event_id == maze_event.id)
        )
        or 0
    )
    assert daily_rollups >= 20

    # Source / campaign / device dimensions present
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(AnalyticsEvent)
            .where(
                AnalyticsEvent.target_event_id == maze_event.id,
                AnalyticsEvent.source == "instagram",
            )
        )
        or 0
    ) >= 1
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(AnalyticsEvent)
            .where(
                AnalyticsEvent.campaign.in_(
                    ("detty-december", "early-bird-drop", "influencer-tola")
                )
            )
        )
        or 0
    ) >= 1
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(AnalyticsEvent)
            .where(AnalyticsEvent.device_type == "mobile")
        )
        or 0
    ) >= (
        db_session.scalar(
            select(func.count())
            .select_from(AnalyticsEvent)
            .where(AnalyticsEvent.device_type == "desktop")
        )
        or 0
    )

    # Location hierarchy + event location assignment
    from app.events.models import EventCategory
    from app.placements.constants import (
        PLACEMENT_CATEGORY_PAGE,
        PLACEMENT_HOMEPAGE,
        STATUS_ACTIVE,
    )
    from app.placements.models import FeaturedPlacement
    from app.taxonomy.models import Location

    nigeria = db_session.scalar(
        select(Location).where(Location.kind == "country", Location.slug == "nigeria")
    )
    assert nigeria is not None
    lagos_state = db_session.scalar(
        select(Location).where(Location.kind == "state", Location.slug == "lagos")
    )
    lagos_city = db_session.scalar(
        select(Location).where(Location.kind == "city", Location.slug == "lagos")
    )
    assert lagos_state is not None and lagos_city is not None
    assert lagos_state.parent_id == nigeria.id
    assert lagos_city.parent_id == lagos_state.id

    area_slugs = {
        row.slug
        for row in db_session.scalars(
            select(Location).where(
                Location.kind == "area", Location.parent_id == lagos_city.id
            )
        ).all()
    }
    assert {
        "lekki",
        "victoria-island",
        "ikeja",
        "yaba",
        "mainland",
    }.issubset(area_slugs)
    mainland = db_session.scalar(
        select(Location).where(Location.kind == "area", Location.slug == "mainland")
    )
    assert mainland is not None and mainland.name == "Lagos Mainland"

    for city_slug, state_slug in (
        ("ibadan", "oyo"),
        ("akure", "ondo"),
        ("abuja", "fct"),
    ):
        city = db_session.scalar(
            select(Location).where(Location.kind == "city", Location.slug == city_slug)
        )
        state = db_session.scalar(
            select(Location).where(Location.kind == "state", Location.slug == state_slug)
        )
        assert city is not None and state is not None
        assert city.parent_id == state.id

    located = [e for e in events if e.location_id is not None]
    assert len(located) >= 15

    summer = db_session.scalar(
        select(Event).where(
            Event.slug == f"{DEMO_EVENT_SLUG_PREFIX}mainland-vibes-summer"
        )
    )
    assert summer is not None and summer.location_id == mainland.id

    assert first.get("placement_slots_assigned", 0) >= 6

    def _slot_event_title(placement_key: str, slot_number: int) -> str | None:
        row = db_session.scalar(
            select(FeaturedPlacement).where(
                FeaturedPlacement.placement_key == placement_key,
                FeaturedPlacement.slot_number == slot_number,
                FeaturedPlacement.status == STATUS_ACTIVE,
            )
        )
        if row is None or row.event_id is None:
            return None
        ev = db_session.get(Event, row.event_id)
        return ev.title if ev else None

    assert _slot_event_title(PLACEMENT_HOMEPAGE, 1) == "Lagos Creative Market"
    assert _slot_event_title(PLACEMENT_HOMEPAGE, 2) == "Afrobeats Night Live"
    assert _slot_event_title(f"city_page:{lagos_city.id}", 1) == "Laugh Lagos Live"
    assert _slot_event_title(f"city_page:{lagos_city.id}", 2) == "Founders Mixer Lagos"

    nightlife = db_session.scalar(
        select(EventCategory).where(EventCategory.slug == "nightlife")
    )
    tech = db_session.scalar(
        select(EventCategory).where(EventCategory.slug == "tech")
    )
    lifestyle = db_session.scalar(
        select(EventCategory).where(EventCategory.slug == "lifestyle")
    )
    assert nightlife is not None and tech is not None and lifestyle is not None
    assert (
        _slot_event_title(f"{PLACEMENT_CATEGORY_PAGE}:{lifestyle.id}", 1)
        == "Lagos Creative Market"
    )
    assert (
        _slot_event_title(f"{PLACEMENT_CATEGORY_PAGE}:{nightlife.id}", 1)
        == "Mainland After Dark"
    )
    assert (
        _slot_event_title(f"{PLACEMENT_CATEGORY_PAGE}:{tech.id}", 1)
        == "Product Builders Meetup"
    )

    second = seed_demo_data(db_session, reset=False)
    assert second["status"] == "already_seeded"
    assert second.get("placement_slots_assigned", 0) >= 6

    user_count_before = db_session.scalar(
        select(func.count())
        .select_from(User)
        .where(User.email.like(f"%@{DEMO_EMAIL_DOMAIN}"))
    )
    event_count_before = len(events)

    # Reset clears only demo data
    non_demo = User(
        email="keeper@example.com",
        password_hash="x",
        full_name="Keeper",
        is_active=True,
    )
    db_session.add(non_demo)
    db_session.commit()

    counts = reset_demo_data(db_session)
    assert counts["users"] >= 7
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(User)
            .where(User.email.like(f"%@{DEMO_EMAIL_DOMAIN}"))
        )
        or 0
    ) == 0
    assert db_session.scalar(select(User).where(User.email == "keeper@example.com"))
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(Event)
            .where(Event.slug.startswith(DEMO_EVENT_SLUG_PREFIX))
        )
        or 0
    ) == 0
    assert (
        db_session.scalar(select(func.count()).select_from(DemoSupportCase)) or 0
    ) == 0

    # Reseed after reset
    again = seed_demo_data(db_session, reset=False)
    assert again["status"] == "seeded"
    assert again["password"] == DEMO_PASSWORD
    assert user_count_before is not None
    assert event_count_before >= 20


