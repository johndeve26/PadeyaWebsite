"""Legacy Page aggregation, tier scoring, and admin recalculation."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.audit import write_audit_log
from app.events.models import Event
from app.hosts.models import Host
from app.hosts.schemas import HostProfileUpdate
from app.hosts.service import require_user_host, update_host_profile
from app.legacy.models import HostLegacyScore, HostLegacyScoreHistory, LegacyTier
from app.legacy.scoring import (
    ScoreInputs,
    compute_composite_score,
    requirement_checklist,
    select_tier,
)
from app.legacy.seed import seed_legacy_tiers
from app.reviews.models import VerifiedReview
from app.tickets.models import Ticket
from app.users.models import User


def get_host_by_slug(db: Session, slug: str) -> Host | None:
    return db.scalar(
        select(Host)
        .where(Host.slug == slug.lower())
        .options(
            selectinload(Host.profile),
            selectinload(Host.verifications),
        )
    )


def _latest_verification_status(host: Host) -> str | None:
    if not host.verifications:
        return None
    latest = sorted(host.verifications, key=lambda v: v.created_at, reverse=True)[0]
    return latest.status


def ensure_tiers(db: Session) -> list[LegacyTier]:
    tiers = list(db.scalars(select(LegacyTier).order_by(LegacyTier.rank.asc())).all())
    if not tiers:
        seed_legacy_tiers(db)
        tiers = list(db.scalars(select(LegacyTier).order_by(LegacyTier.rank.asc())).all())
    return tiers


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def collect_host_metrics(db: Session, host_id: UUID) -> ScoreInputs:
    now = datetime.now(UTC)

    events_hosted = db.scalar(
        select(func.count())
        .select_from(Event)
        .where(
            Event.host_id == host_id,
            Event.status.in_(["published", "completed", "paused"]),
        )
    ) or 0

    # Count completed status, and auto-treat ended published events as completed for scoring
    completed_status = db.scalar(
        select(func.count())
        .select_from(Event)
        .where(Event.host_id == host_id, Event.status == "completed")
    ) or 0
    ended_published = db.scalars(
        select(Event).where(
            Event.host_id == host_id,
            Event.status == "published",
        )
    ).all()
    ended_count = sum(1 for e in ended_published if _aware(e.end_datetime) < now)
    completed_events = int(completed_status) + int(ended_count)

    tickets = list(
        db.scalars(
            select(Ticket)
            .join(Event, Event.id == Ticket.event_id)
            .where(
                Event.host_id == host_id,
                Ticket.status.in_(["active", "checked_in"]),
            )
        )
    )
    from app.hosts.fan_self_abuse import (
        is_user_owner_of_host,
        order_excluded_from_public_metrics,
    )
    from app.payments.models import Order

    order_ids = {t.order_id for t in tickets if t.order_id}
    orders_by_id = {
        o.id: o
        for o in db.scalars(select(Order).where(Order.id.in_(order_ids))).all()
    } if order_ids else {}

    external_tickets = [
        t
        for t in tickets
        if not is_user_owner_of_host(
            db, user_id=t.buyer_user_id, host_profile_id=host_id
        )
        and not order_excluded_from_public_metrics(
            orders_by_id.get(t.order_id) if t.order_id else None
        )
    ]
    tickets_sold = len(external_tickets)
    verified_checkins = sum(1 for t in external_tickets if t.status == "checked_in")

    review_rows = list(
        db.scalars(
            select(VerifiedReview).where(
                VerifiedReview.host_id == host_id,
                VerifiedReview.status == "visible",
            )
        )
    )
    external_reviews = [
        r
        for r in review_rows
        if not is_user_owner_of_host(
            db, user_id=r.reviewer_user_id, host_profile_id=host_id
        )
    ]
    review_count = len(external_reviews)
    if external_reviews:
        avg_rating = sum(int(r.rating) for r in external_reviews) / review_count
    else:
        avg_rating = None

    score_row = db.scalar(select(HostLegacyScore).where(HostLegacyScore.host_id == host_id))

    from app.crm.follower_count import count_host_followers

    followers = count_host_followers(db, host_id)
    repeat_buyers_rate = score_row.repeat_buyers_rate if score_row else None
    refund_dispute_rate = score_row.refund_dispute_rate if score_row else None

    return ScoreInputs(
        average_verified_rating=(
            Decimal(str(round(float(avg_rating), 2))) if avg_rating is not None else None
        ),
        review_count=int(review_count),
        completed_events=completed_events,
        tickets_sold=int(tickets_sold),
        verified_checkins=int(verified_checkins),
        refund_dispute_rate=refund_dispute_rate,
        events_hosted=int(events_hosted),
        followers=followers,
        repeat_buyers_rate=repeat_buyers_rate,
    )


def refresh_host_legacy_score(
    db: Session,
    host_id: UUID,
    *,
    reason: str = "recalc",
    force_history: bool = False,
) -> HostLegacyScore:
    tiers = ensure_tiers(db)
    inputs = collect_host_metrics(db, host_id)
    composite, factors = compute_composite_score(inputs)
    tier = select_tier(tiers, score=composite, inputs=inputs)

    score = db.scalar(select(HostLegacyScore).where(HostLegacyScore.host_id == host_id))
    previous_score = Decimal(score.composite_score) if score and score.composite_score is not None else None
    previous_tier_slug: str | None = None
    if score and score.tier_id:
        prev_tier = db.get(LegacyTier, score.tier_id)
        previous_tier_slug = prev_tier.slug if prev_tier else None

    if score is None:
        score = HostLegacyScore(host_id=host_id)
        db.add(score)

    score.events_hosted = inputs.events_hosted
    score.completed_events = inputs.completed_events
    score.tickets_sold = inputs.tickets_sold
    score.verified_checkins = inputs.verified_checkins
    score.average_verified_rating = inputs.average_verified_rating
    score.review_count = inputs.review_count
    score.followers = inputs.followers
    score.repeat_buyers_rate = inputs.repeat_buyers_rate
    score.refund_dispute_rate = inputs.refund_dispute_rate
    score.composite_score = composite
    score.factor_scores = {k: float(v) for k, v in factors.items()}
    score.tier_id = tier.id if tier else None
    score.legacy_status = tier.name if tier else "New Host"
    score.updated_at = datetime.now(UTC)

    changed = (
        previous_score is None
        or previous_score != composite
        or previous_tier_slug != (tier.slug if tier else None)
    )
    if force_history or changed:
        db.add(
            HostLegacyScoreHistory(
                host_id=host_id,
                tier_id=tier.id if tier else None,
                previous_tier_slug=previous_tier_slug,
                tier_slug=tier.slug if tier else "new-host",
                composite_score=composite,
                previous_composite_score=previous_score,
                factor_scores={k: float(v) for k, v in factors.items()},
                metrics_snapshot={
                    "events_hosted": inputs.events_hosted,
                    "completed_events": inputs.completed_events,
                    "tickets_sold": inputs.tickets_sold,
                    "verified_checkins": inputs.verified_checkins,
                    "average_verified_rating": (
                        float(inputs.average_verified_rating)
                        if inputs.average_verified_rating is not None
                        else None
                    ),
                    "review_count": inputs.review_count,
                    "followers": inputs.followers,
                    "repeat_buyers_rate": (
                        float(inputs.repeat_buyers_rate)
                        if inputs.repeat_buyers_rate is not None
                        else None
                    ),
                    "refund_dispute_rate": (
                        float(inputs.refund_dispute_rate)
                        if inputs.refund_dispute_rate is not None
                        else None
                    ),
                },
                reason=reason,
            )
        )

    db.flush()
    return score


def _serialize_tier(tier: LegacyTier | None) -> dict | None:
    if tier is None:
        return None
    return {
        "id": tier.id,
        "slug": tier.slug,
        "name": tier.name,
        "rank": tier.rank,
        "min_score": tier.min_score,
        "description": tier.description,
        "requirements": tier.requirements,
        "is_active": tier.is_active,
    }


def build_tier_progress(db: Session, host_id: UUID) -> dict:
    from app.legacy.presentation import (
        build_next_tier_summary,
        display_score,
        factor_contributions,
        provisional_state,
        public_factor_bands,
    )

    score = refresh_host_legacy_score(db, host_id, reason="progress_view")
    tiers = ensure_tiers(db)
    inputs = collect_host_metrics(db, host_id)
    current = db.get(LegacyTier, score.tier_id) if score.tier_id else None
    next_tier = None
    if current is not None:
        higher = [t for t in tiers if t.is_active and t.rank > current.rank]
        next_tier = min(higher, key=lambda t: t.rank) if higher else None
    else:
        next_tier = next((t for t in tiers if t.is_active and t.rank > 0), None)

    current_score = Decimal(score.composite_score)
    is_top_tier = next_tier is None and current is not None
    if next_tier is None:
        progress_pct = Decimal("100")
    else:
        floor = Decimal(current.min_score) if current else Decimal("0")
        ceiling = Decimal(next_tier.min_score)
        span = ceiling - floor
        if span <= 0:
            progress_pct = Decimal("100")
        else:
            progress_pct = max(
                Decimal("0"),
                min(Decimal("100"), ((current_score - floor) / span) * 100),
            ).quantize(Decimal("0.01"))

    target_reqs = next_tier.requirements if next_tier else (current.requirements if current else {})
    checklist = requirement_checklist(target_reqs, inputs)
    met = [c for c in checklist if c["met"]]
    remaining = [c for c in checklist if not c["met"]]

    suggestions: list[str] = []
    for item in remaining:
        if item["key"] == "completed_events":
            suggestions.append("Complete more published events to grow your Legacy.")
        elif item["key"] == "tickets_sold":
            suggestions.append("Sell more tickets on upcoming events.")
        elif item["key"] == "verified_checkins":
            suggestions.append("Drive door check-ins — only checked-in attendees count.")
        elif item["key"] == "review_count":
            suggestions.append("Encourage checked-in guests to leave verified reviews after events.")
        elif item["key"] == "average_rating":
            suggestions.append("Improve guest experience to raise your verified rating.")
    if not suggestions and next_tier is None:
        suggestions.append("You are at the top Legacy tier. Keep hosting consistently.")
    elif not suggestions:
        suggestions.append("Keep stacking completed events and verified reviews to push the score.")

    history = db.scalars(
        select(HostLegacyScoreHistory)
        .where(HostLegacyScoreHistory.host_id == host_id)
        .order_by(HostLegacyScoreHistory.created_at.desc())
        .limit(20)
    ).all()

    metrics = {
        "events_hosted": score.events_hosted,
        "completed_events": score.completed_events,
        "tickets_sold": score.tickets_sold,
        "verified_checkins": score.verified_checkins,
        "average_verified_rating": score.average_verified_rating,
        "review_count": score.review_count,
        "followers": score.followers,
        "repeat_buyers_rate": score.repeat_buyers_rate,
        "refund_dispute_rate": score.refund_dispute_rate,
    }
    provisional = provisional_state(
        completed_events=int(score.completed_events),
        review_count=int(score.review_count),
    )
    next_summary = build_next_tier_summary(
        composite_score=current_score,
        current_tier=current,
        next_tier=next_tier,
        inputs=inputs,
    )

    return {
        "host_id": host_id,
        "composite_score": score.composite_score,
        "display_score": display_score(score.composite_score),
        "factor_scores": score.factor_scores or {},
        "factor_contributions": factor_contributions(
            score.factor_scores, metrics=metrics
        ),
        "factor_bands": public_factor_bands(
            score.factor_scores,
            refund_rate_unknown=score.refund_dispute_rate is None,
        ),
        "current_tier": _serialize_tier(current),
        "next_tier": _serialize_tier(next_tier),
        "next_tier_summary": next_summary,
        "progress_percentage": progress_pct,
        "requirements_met": met,
        "requirements_remaining": remaining,
        "suggested_actions": suggestions,
        "metrics": metrics,
        "history": [
            {
                "id": h.id,
                "tier_slug": h.tier_slug,
                "previous_tier_slug": h.previous_tier_slug,
                "composite_score": h.composite_score,
                "previous_composite_score": h.previous_composite_score,
                "reason": h.reason,
                "created_at": h.created_at,
                "factor_scores": h.factor_scores,
            }
            for h in history
        ],
        "is_provisional": provisional["is_provisional"],
        "provisional_reasons": provisional["provisional_reasons"],
        "is_top_tier": is_top_tier,
        "last_recalculated_at": score.updated_at,
        "owner_self_actions_excluded": True,
    }


def _event_card(event: Event, *, memory_path: str | None = None) -> dict:
    return {
        "id": event.id,
        "title": event.title,
        "slug": event.slug,
        "start_datetime": event.start_datetime,
        "end_datetime": event.end_datetime,
        "city": event.city,
        "banner_url": event.banner_url,
        "status": event.status,
        "memory_path": memory_path,
    }


def build_legacy_page(
    db: Session,
    *,
    slug: str | None = None,
    host: Host | None = None,
    rescore: bool = True,
) -> dict:
    """Assemble Legacy page stats/events/reviews.

    ``rescore=False`` serves the stored score (public page reads) so GET does not
    run collect_host_metrics + commit on every view. Missing scores still refresh.
    """
    if host is None:
        if not slug:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Legacy Page not found"
            )
        host = get_host_by_slug(db, slug)
    if host is None or host.status != "active":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Legacy Page not found")

    if rescore:
        score = refresh_host_legacy_score(db, host.id, reason="page_view")
        db.commit()
    else:
        score = db.scalar(
            select(HostLegacyScore).where(HostLegacyScore.host_id == host.id)
        )
        if score is None:
            score = refresh_host_legacy_score(db, host.id, reason="page_view_bootstrap")
            db.commit()

    now = datetime.now(UTC)
    events = db.scalars(
        select(Event)
        .where(
            Event.host_id == host.id,
            Event.status.in_(["published", "completed", "paused"]),
        )
        .order_by(Event.start_datetime.desc())
        .limit(80)
    ).all()

    from app.memories.service import list_public_host_memories

    memory_cards = list_public_host_memories(db, host.id)
    memory_by_event = {c["event_id"]: c["share_path"] for c in memory_cards}

    upcoming: list[dict] = []
    past: list[dict] = []
    for event in events:
        end = _aware(event.end_datetime)
        memory_path = memory_by_event.get(event.id)
        if end >= now and event.status in ("published", "paused"):
            upcoming.append(_event_card(event, memory_path=memory_path))
        else:
            past.append(_event_card(event, memory_path=memory_path))

    upcoming.sort(key=lambda e: e["start_datetime"])
    verified = _latest_verification_status(host) == "verified"
    profile = host.profile
    tier = db.get(LegacyTier, score.tier_id) if score.tier_id else None

    from app.passport.merch_proof import host_merch_proof_counts, host_merch_proof_summaries
    from app.reviews.service import list_visible_host_reviews
    from app.crm.follower_count import count_host_followers
    from app.legacy.presentation import (
        build_legacy_trust_summary,
        score_inputs_from_metrics,
    )

    merch_counts = host_merch_proof_counts(db, host.id)
    merch_summaries = host_merch_proof_summaries(db, host.id)

    from app.taxonomy import service as taxonomy_service
    from app.users.gender import (
        HIDDEN_GENDER_PAYLOAD,
        host_shows_personal_gender,
        public_cache_safe_gender_payload,
    )
    from app.users.models import User as UserModel

    tax = taxonomy_service.get_host_taxonomy(db, host.id)
    type_slugs = tax.get("host_type_slugs") or []
    shows_personal = host_shows_personal_gender(type_slugs)
    owner = db.get(UserModel, host.user_id)
    if not shows_personal or owner is None:
        gender_payload = dict(HIDDEN_GENDER_PAYLOAD)
    else:
        gender_payload = public_cache_safe_gender_payload(owner)

    live_followers = count_host_followers(db, host.id)
    tiers = ensure_tiers(db)
    next_tier = None
    is_top_tier = False
    if tier is not None:
        higher = [t for t in tiers if t.is_active and t.rank > tier.rank]
        next_tier = min(higher, key=lambda t: t.rank) if higher else None
        is_top_tier = next_tier is None
    else:
        next_tier = next((t for t in tiers if t.is_active and t.rank > 0), None)

    trust_inputs = score_inputs_from_metrics(
        {
            "events_hosted": score.events_hosted,
            "completed_events": score.completed_events,
            "tickets_sold": score.tickets_sold,
            "verified_checkins": score.verified_checkins,
            "average_verified_rating": score.average_verified_rating,
            "review_count": score.review_count,
            "followers": live_followers,
            "repeat_buyers_rate": score.repeat_buyers_rate,
            "refund_dispute_rate": score.refund_dispute_rate,
        }
    )
    legacy_trust = build_legacy_trust_summary(
        composite_score=score.composite_score,
        tier=tier,
        legacy_status=score.legacy_status,
        factor_scores=score.factor_scores,
        completed_events=int(score.completed_events),
        tickets_sold=int(score.tickets_sold),
        verified_checkins=int(score.verified_checkins),
        average_verified_rating=score.average_verified_rating,
        review_count=int(score.review_count),
        followers=live_followers,
        repeat_buyers_rate=score.repeat_buyers_rate,
        refund_dispute_rate=score.refund_dispute_rate,
        next_tier=next_tier,
        inputs=trust_inputs,
        last_recalculated_at=score.updated_at,
        is_top_tier=is_top_tier,
    )

    return {
        "host_id": host.id,
        "display_name": host.display_name,
        "username": host.slug,
        "status": host.status,
        "verified": verified,
        "legacy_status": score.legacy_status,
        "tier": _serialize_tier(tier),
        "composite_score": score.composite_score,
        "profile": profile,
        "shows_personal_gender": shows_personal,
        **gender_payload,
        "stats": {
            "events_hosted": score.events_hosted,
            "tickets_sold": score.tickets_sold,
            "verified_checkins": score.verified_checkins,
            "average_verified_rating": score.average_verified_rating,
            "review_count": score.review_count,
            # Live count — denormalized score.followers can lag when public
            # pages assemble with rescore=False after follow/unfollow.
            "followers": live_followers,
            "repeat_buyers_rate": score.repeat_buyers_rate,
            "refund_dispute_rate": score.refund_dispute_rate,
            "legacy_status": score.legacy_status,
            "composite_score": score.composite_score,
            "completed_events": score.completed_events,
            "merch_items_sold": merch_counts["merch_items_sold"],
            "fans_collected_merch": merch_counts["fans_collected_merch"],
            "merch_proof_summaries": merch_summaries,
        },
        "legacy_trust": legacy_trust,
        "about": profile.bio if profile else None,
        "upcoming_events": upcoming,
        "past_events": past,
        "event_memories": memory_cards,
        "reviews": list_visible_host_reviews(db, host.id),
        "follow_enabled": True,
        "share_path": f"/@{host.slug}",
    }


def get_my_legacy_page(db: Session, user: User) -> dict:
    from app.legacy.studio import get_host_legacy_studio

    return get_host_legacy_studio(db, user)


def get_my_tier_progress(db: Session, user: User) -> dict:
    host = require_user_host(db, user)
    progress = build_tier_progress(db, host.id)
    db.commit()
    return progress


def update_my_legacy_profile(
    db: Session,
    *,
    user: User,
    payload: HostProfileUpdate,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict:
    host = update_host_profile(db, user=user, payload=payload)
    write_audit_log(
        db,
        action="legacy.profile_update",
        actor_user_id=user.id,
        resource_type="host",
        resource_id=str(host.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return build_legacy_page(db, slug=host.slug)


def list_tiers(db: Session) -> list[LegacyTier]:
    return ensure_tiers(db)


def update_tier(
    db: Session,
    *,
    user: User,
    tier_id: UUID,
    payload: dict,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> LegacyTier:
    tier = db.get(LegacyTier, tier_id)
    if tier is None:
        raise HTTPException(status_code=404, detail="Tier not found")

    if "min_score" in payload and payload["min_score"] is not None:
        tier.min_score = Decimal(str(payload["min_score"]))
    if "description" in payload:
        tier.description = payload["description"]
    if "requirements" in payload and payload["requirements"] is not None:
        tier.requirements = payload["requirements"]
    if "is_active" in payload and payload["is_active"] is not None:
        tier.is_active = bool(payload["is_active"])
    if "name" in payload and payload["name"]:
        tier.name = payload["name"]

    audit_details = {
        key: (float(value) if isinstance(value, Decimal) else value)
        for key, value in payload.items()
    }
    write_audit_log(
        db,
        action="legacy.tier_update",
        actor_user_id=user.id,
        resource_type="legacy_tier",
        resource_id=str(tier.id),
        details=audit_details,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    db.refresh(tier)
    return tier


def list_host_tier_summaries(db: Session) -> list[dict]:
    from app.legacy.presentation import display_score, provisional_state

    ensure_tiers(db)
    hosts = db.scalars(select(Host).where(Host.status == "active").order_by(Host.display_name)).all()
    out: list[dict] = []
    for host in hosts:
        score = refresh_host_legacy_score(db, host.id, reason="admin_list")
        tier = db.get(LegacyTier, score.tier_id) if score.tier_id else None
        provisional = provisional_state(
            completed_events=int(score.completed_events),
            review_count=int(score.review_count),
        )
        out.append(
            {
                "host_id": host.id,
                "display_name": host.display_name,
                "username": host.slug,
                "composite_score": score.composite_score,
                "display_score": display_score(score.composite_score),
                "is_provisional": provisional["is_provisional"],
                "completed_events": int(score.completed_events),
                "review_count": int(score.review_count),
                "factor_scores": score.factor_scores,
                "tier": _serialize_tier(tier),
                "legacy_status": score.legacy_status,
                "updated_at": score.updated_at,
            }
        )
    db.commit()
    return out


def recalculate_host(
    db: Session,
    *,
    user: User,
    host_id: UUID,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> HostLegacyScore:
    host = db.get(Host, host_id)
    if host is None:
        raise HTTPException(status_code=404, detail="Host not found")
    score = refresh_host_legacy_score(
        db, host_id, reason="admin_recalc", force_history=True
    )
    write_audit_log(
        db,
        action="legacy.recalculate_host",
        actor_user_id=user.id,
        resource_type="host",
        resource_id=str(host_id),
        details={"composite_score": float(score.composite_score), "tier": score.legacy_status},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    db.refresh(score)
    return score


def recalculate_all_hosts(
    db: Session,
    *,
    user: User,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict:
    hosts = db.scalars(select(Host.id)).all()
    count = 0
    for host_id in hosts:
        refresh_host_legacy_score(db, host_id, reason="admin_recalc_all", force_history=True)
        count += 1
    write_audit_log(
        db,
        action="legacy.recalculate_all",
        actor_user_id=user.id,
        resource_type="legacy",
        resource_id="all",
        details={"hosts": count},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return {"recalculated": count}


def list_host_score_history(db: Session, host_id: UUID, *, limit: int = 50) -> list[dict]:
    host = db.get(Host, host_id)
    if host is None:
        raise HTTPException(status_code=404, detail="Host not found")
    rows = db.scalars(
        select(HostLegacyScoreHistory)
        .where(HostLegacyScoreHistory.host_id == host_id)
        .order_by(HostLegacyScoreHistory.created_at.desc())
        .limit(limit)
    ).all()
    return [
        {
            "id": h.id,
            "host_id": h.host_id,
            "tier_slug": h.tier_slug,
            "previous_tier_slug": h.previous_tier_slug,
            "composite_score": h.composite_score,
            "previous_composite_score": h.previous_composite_score,
            "factor_scores": h.factor_scores,
            "metrics_snapshot": h.metrics_snapshot,
            "reason": h.reason,
            "created_at": h.created_at,
        }
        for h in rows
    ]


def complete_event_and_recalc(
    db: Session,
    *,
    user: User,
    event_id: UUID,
) -> Event:
    from app.events.service import get_event_by_id
    from app.hosts.service import get_host_by_user_id
    from app.users.service import user_has_permission

    event = get_event_by_id(db, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    host = get_host_by_user_id(db, user.id)
    is_owner = host is not None and host.id == event.host_id
    if not is_owner and not user_has_permission(user, "admin.full_access"):
        raise HTTPException(status_code=403, detail="Not allowed to complete this event")

    if event.status not in {"published", "paused"}:
        raise HTTPException(
            status_code=400,
            detail="Only published or paused events can be marked completed",
        )

    event.status = "completed"
    write_audit_log(
        db,
        action="events.complete",
        actor_user_id=user.id,
        resource_type="event",
        resource_id=str(event.id),
    )
    from app.memories.service import ensure_event_memory

    ensure_event_memory(db, event)
    refresh_host_legacy_score(db, event.host_id, reason="event_completed", force_history=True)
    db.commit()
    db.refresh(event)
    return event
