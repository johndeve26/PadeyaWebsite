"""Score and rank sponsorship opportunities for a sponsor campaign."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.events.models import Event, EventCategory
from app.hosts.models import Host, HostProfile
from app.legacy.models import HostLegacyPage, HostLegacyScore, LegacyTier
from app.sponsor_profiles.recommendations import constants as C
from app.sponsor_profiles.recommendations.models import (
    CampaignRecommendationDismissal,
    CampaignRecommendationFeedback,
)
from app.sponsor_profiles.saved_service import _enrich_item
from app.sponsorships.models import (
    Sponsor,
    SponsorCampaign,
    SponsorSavedItem,
    SponsorshipSlot,
)
from app.sponsorships.service import _is_publicly_visible, host_is_verified


def _now() -> datetime:
    return datetime.now(UTC)


def _norm(value: str | None) -> str:
    return (value or "").strip().lower()


def _norm_list(values: list[str] | None) -> set[str]:
    if not values:
        return set()
    return {_norm(v) for v in values if v and _norm(v)}


def _token_match(a: set[str], b: set[str]) -> bool:
    if not a or not b:
        return False
    for x in a:
        for y in b:
            if x in y or y in x:
                return True
    return bool(a & b)


def _reason(code: str) -> dict[str, str]:
    return {"code": code, "label": C.REASON_LABELS[code]}


@dataclass
class ScoreResult:
    score: int
    breakdown: dict[str, int] = field(default_factory=dict)
    reasons: list[dict[str, str]] = field(default_factory=list)
    excluded: str | None = None


@dataclass
class CandidateContext:
    host_id: uuid.UUID
    host: Host
    profile: HostProfile | None
    legacy_page: HostLegacyPage | None
    legacy_score: HostLegacyScore | None
    tier: LegacyTier | None
    slot: SponsorshipSlot | None
    event: Event | None
    event_category: EventCategory | None
    host_categories: set[str]
    host_city: str
    slot_price: Decimal | None
    upcoming_event: bool
    audience_estimate: int | None


def _host_categories(
    page: HostLegacyPage | None, sponsor: Sponsor, campaign: SponsorCampaign
) -> set[str]:
    out: set[str] = set()
    if page and page.primary_category_slug:
        out.add(_norm(page.primary_category_slug))
    if page and page.host_type_slug:
        out.add(_norm(page.host_type_slug))
    if sponsor.industry:
        out.add(_norm(sponsor.industry))
    out |= _norm_list(sponsor.categories)
    out |= _norm_list(campaign.target_categories)
    hints = C.OBJECTIVE_CATEGORY_HINTS.get(campaign.objective, ())
    out |= {_norm(h) for h in hints}
    return {x for x in out if x}


def _item_categories(ctx: CandidateContext, item_type: str) -> set[str]:
    cats = set(ctx.host_categories)
    if item_type == "sponsorship_slot" and ctx.slot:
        cats.add(_norm(ctx.slot.slot_type))
    if item_type == "event" and ctx.event_category:
        cats.add(_norm(ctx.event_category.slug))
        cats.add(_norm(ctx.event_category.name))
    return {c for c in cats if c}


def _score_category(
    campaign: SponsorCampaign,
    sponsor: Sponsor,
    ctx: CandidateContext,
    item_type: str,
    saved_tokens: set[str],
) -> tuple[int, list[dict[str, str]]]:
    targets = _norm_list(campaign.target_categories)
    if sponsor.categories:
        targets |= _norm_list(sponsor.categories)
    if sponsor.industry:
        targets.add(_norm(sponsor.industry))
    hints = {_norm(h) for h in C.OBJECTIVE_CATEGORY_HINTS.get(campaign.objective, ())}
    item_cats = _item_categories(ctx, item_type)
    reasons: list[dict[str, str]] = []
    if not targets and not hints:
        return 12, reasons
    matched = _token_match(targets, item_cats) or _token_match(hints, item_cats)
    if matched:
        reasons.append(_reason(C.REASON_CATEGORY))
        return C.MAX_CATEGORY, reasons
    if _token_match(saved_tokens, item_cats):
        reasons.append(_reason(C.REASON_SAVED))
        return min(C.MAX_CATEGORY, 22), reasons
    return 8, reasons


def _score_location(campaign: SponsorCampaign, ctx: CandidateContext) -> tuple[int, list[dict[str, str]]]:
    targets = _norm_list(campaign.target_locations)
    if not targets:
        return 10, []
    locs: set[str] = set()
    if ctx.profile and ctx.profile.city:
        locs.add(_norm(ctx.profile.city))
    if ctx.profile and ctx.profile.state:
        locs.add(_norm(ctx.profile.state))
    if ctx.event and ctx.event.city:
        locs.add(_norm(ctx.event.city))
    if ctx.event and ctx.event.area:
        locs.add(_norm(ctx.event.area))
    if _token_match(targets, locs):
        return C.MAX_LOCATION, [_reason(C.REASON_LOCATION)]
    return 4, []


def _score_budget(campaign: SponsorCampaign, price: Decimal | None) -> tuple[int, list[dict[str, str]]]:
    if price is None:
        return 10, []
    lo = campaign.budget_min
    hi = campaign.budget_max
    if lo is None and hi is None:
        return 12, []
    p = float(price)
    if lo is not None and hi is not None:
        if float(lo) <= p <= float(hi):
            return C.MAX_BUDGET, [_reason(C.REASON_BUDGET)]
        mid = (float(lo) + float(hi)) / 2
        span = max(float(hi) - float(lo), 1.0)
        dist = abs(p - mid) / span
        if dist <= 1.5:
            return max(8, C.MAX_BUDGET - int(dist * 8)), []
        return 2, []
    if hi is not None and p <= float(hi) * 1.15:
        return C.MAX_BUDGET, [_reason(C.REASON_BUDGET)]
    if lo is not None and p >= float(lo) * 0.85:
        return C.MAX_BUDGET, [_reason(C.REASON_BUDGET)]
    return 4, []


def _score_trust(ctx: CandidateContext, verified: bool) -> tuple[int, list[dict[str, str]]]:
    pts = 0
    reasons: list[dict[str, str]] = []
    if verified:
        pts += 5
        reasons.append(_reason(C.REASON_VERIFIED))
    score = ctx.legacy_score
    if score:
        if score.review_count and score.review_count >= 5:
            pts += 4
            reasons.append(_reason(C.REASON_ACTIVITY))
        elif score.verified_checkins and score.verified_checkins >= 20:
            pts += 3
            reasons.append(_reason(C.REASON_ACTIVITY))
        if ctx.tier and ctx.tier.rank:
            pts += min(4, max(1, ctx.tier.rank // 2))
    return min(C.MAX_TRUST, pts), reasons


def _score_timing(ctx: CandidateContext) -> tuple[int, list[dict[str, str]]]:
    if ctx.upcoming_event:
        return C.MAX_TIMING, [_reason(C.REASON_UPCOMING)]
    return 3, []


def _score_feedback_boost(
    db: Session,
    *,
    campaign_id: uuid.UUID,
    item_type: str,
    item_id: uuid.UUID,
) -> int:
    rows = db.scalars(
        select(CampaignRecommendationFeedback.action).where(
            CampaignRecommendationFeedback.campaign_id == campaign_id,
            CampaignRecommendationFeedback.item_type == item_type,
            CampaignRecommendationFeedback.item_id == item_id,
        )
    ).all()
    boost = 0
    for action in rows[-20:]:
        if action == C.FEEDBACK_MORE_LIKE_THIS:
            boost = max(boost, C.MAX_FEEDBACK)
        elif action == C.FEEDBACK_SAVED:
            boost = max(boost, 6)
        elif action == C.FEEDBACK_CLICKED:
            boost = max(boost, 3)
    return min(C.MAX_FEEDBACK, boost)


def _is_dismissed(
    db: Session,
    *,
    campaign_id: uuid.UUID,
    item_type: str,
    item_id: uuid.UUID,
) -> bool:
    row = db.scalar(
        select(CampaignRecommendationDismissal).where(
            CampaignRecommendationDismissal.campaign_id == campaign_id,
            CampaignRecommendationDismissal.item_type == item_type,
            CampaignRecommendationDismissal.item_id == item_id,
        )
    )
    if row is None:
        return False
    exp = row.expires_at
    if exp is not None and exp.tzinfo is None:
        exp = exp.replace(tzinfo=UTC)
    if exp is None or exp > _now():
        return True
    return False


def score_opportunity(
    db: Session,
    *,
    campaign: SponsorCampaign,
    sponsor: Sponsor,
    item_type: str,
    item_id: uuid.UUID,
    ctx: CandidateContext,
    verified: bool,
    saved_tokens: set[str],
) -> ScoreResult:
    if _is_dismissed(db, campaign_id=campaign.id, item_type=item_type, item_id=item_id):
        return ScoreResult(score=0, excluded="dismissed")

    price = ctx.slot_price if item_type == "sponsorship_slot" else ctx.slot_price
    cat_pts, cat_reasons = _score_category(
        campaign, sponsor, ctx, item_type, saved_tokens
    )
    loc_pts, loc_reasons = _score_location(campaign, ctx)
    budget_pts, budget_reasons = _score_budget(campaign, price)
    trust_pts, trust_reasons = _score_trust(ctx, verified)
    time_pts, time_reasons = _score_timing(ctx)
    fb_pts = _score_feedback_boost(
        db, campaign_id=campaign.id, item_type=item_type, item_id=item_id
    )

    breakdown = {
        "category": cat_pts,
        "location": loc_pts,
        "budget": budget_pts,
        "trust": trust_pts,
        "timing": time_pts,
        "feedback": fb_pts,
    }
    total = min(C.SCORE_MAX, sum(breakdown.values()))
    reasons: list[dict[str, str]] = []
    seen: set[str] = set()
    for r in cat_reasons + loc_reasons + budget_reasons + trust_reasons + time_reasons:
        if r["code"] not in seen:
            seen.add(r["code"])
            reasons.append(r)
    if not reasons and total >= C.SCORE_MIN_SHOW:
        reasons.append(_reason(C.REASON_CATEGORY))
    return ScoreResult(score=total, breakdown=breakdown, reasons=reasons[:4])


def _public_audience_estimate(score: HostLegacyScore | None) -> int | None:
    if score is None:
        return None
    if score.verified_checkins and score.verified_checkins >= 10:
        return min(score.verified_checkins, 5000)
    if score.followers and score.followers >= 10:
        return min(score.followers, 5000)
    return None


def _build_candidates(db: Session, *, sponsor_id: uuid.UUID) -> list[tuple[str, uuid.UUID, CandidateContext]]:
    slots = list(db.scalars(select(SponsorshipSlot)).all())
    host_ids: set[uuid.UUID] = set()
    event_ids: set[uuid.UUID] = set()
    visible_slots: list[SponsorshipSlot] = []
    for slot in slots:
        if not _is_publicly_visible(db, slot):
            continue
        visible_slots.append(slot)
        host_ids.add(slot.host_id)
        if slot.event_id:
            event_ids.add(slot.event_id)

    hosts = {
        h.id: h
        for h in db.scalars(select(Host).where(Host.id.in_(host_ids))).all()
    } if host_ids else {}
    profiles = {
        p.host_id: p
        for p in db.scalars(select(HostProfile).where(HostProfile.host_id.in_(host_ids))).all()
    } if host_ids else {}
    pages = {
        p.host_id: p
        for p in db.scalars(select(HostLegacyPage).where(HostLegacyPage.host_id.in_(host_ids))).all()
    } if host_ids else {}
    scores = {
        s.host_id: s
        for s in db.scalars(select(HostLegacyScore).where(HostLegacyScore.host_id.in_(host_ids))).all()
    } if host_ids else {}
    tier_ids = {s.tier_id for s in scores.values() if s.tier_id}
    tiers = {
        t.id: t
        for t in db.scalars(select(LegacyTier).where(LegacyTier.id.in_(tier_ids))).all()
    } if tier_ids else {}

    events: dict[uuid.UUID, Event] = {}
    categories: dict[uuid.UUID, EventCategory] = {}
    if event_ids:
        events = {
            e.id: e
            for e in db.scalars(select(Event).where(Event.id.in_(event_ids))).all()
        }
        cat_ids = {e.primary_category_id for e in events.values() if e.primary_category_id}
        if cat_ids:
            categories = {
                c.id: c
                for c in db.scalars(
                    select(EventCategory).where(EventCategory.id.in_(cat_ids))
                ).all()
            }

    now = _now()
    out: list[tuple[str, uuid.UUID, CandidateContext]] = []
    seen: set[tuple[str, uuid.UUID]] = set()

    def add(item_type: str, item_id: uuid.UUID, ctx: CandidateContext) -> None:
        key = (item_type, item_id)
        if key in seen:
            return
        seen.add(key)
        out.append((item_type, item_id, ctx))

    for slot in visible_slots:
        host = hosts.get(slot.host_id)
        if host is None or host.status != "active":
            continue
        if not host_is_verified(db, host.id):
            continue
        page = pages.get(host.id)
        score_row = scores.get(host.id)
        tier = tiers.get(score_row.tier_id) if score_row and score_row.tier_id else None
        event = events.get(slot.event_id) if slot.event_id else None
        if event is not None and event.status != "published":
            event = None
        if event is not None and event.visibility not in ("listed", "approval_required"):
            event = None
        cat = (
            categories.get(event.primary_category_id)
            if event and event.primary_category_id
            else None
        )
        upcoming = bool(
            event
            and event.end_datetime
            and (
                event.end_datetime.replace(tzinfo=UTC)
                if event.end_datetime.tzinfo is None
                else event.end_datetime
            )
            >= now
        )
        host_cats: set[str] = set()
        if page and page.primary_category_slug:
            host_cats.add(_norm(page.primary_category_slug))
        if page and page.host_type_slug:
            host_cats.add(_norm(page.host_type_slug))
        ctx = CandidateContext(
            host_id=host.id,
            host=host,
            profile=profiles.get(host.id),
            legacy_page=page,
            legacy_score=score_row,
            tier=tier,
            slot=slot,
            event=event,
            event_category=cat,
            host_categories=host_cats,
            host_city=_norm(profiles.get(host.id).city if profiles.get(host.id) else None),
            slot_price=slot.price,
            upcoming_event=upcoming,
            audience_estimate=_public_audience_estimate(score_row),
        )
        add("sponsorship_slot", slot.id, ctx)
        add("host", host.id, ctx)
        if event:
            add("event", event.id, ctx)

    return out


def _saved_tokens(db: Session, sponsor_id: uuid.UUID) -> set[str]:
    rows = db.scalars(
        select(SponsorSavedItem).where(SponsorSavedItem.sponsor_id == sponsor_id)
    ).all()
    tokens: set[str] = set()
    for row in rows:
        enriched = _enrich_item(db, row)
        if enriched.get("title"):
            tokens.add(_norm(str(enriched["title"])))
        tokens.add(_norm(row.item_type))
    return tokens


def _score_label(score: int) -> str | None:
    if score >= 80:
        return "Strong match"
    if score >= 60:
        return "Good match"
    if score >= C.SCORE_MIN_SHOW:
        return "Worth a look"
    return None


def list_campaign_recommendations(
    db: Session,
    *,
    campaign: SponsorCampaign,
    sponsor: Sponsor,
    limit: int = C.RECOMMENDATIONS_CAP,
    debug: bool = False,
) -> dict[str, Any]:
    excluded_counts: dict[str, int] = {}
    saved_tokens = _saved_tokens(db, sponsor.id)

    candidates = _build_candidates(db, sponsor_id=sponsor.id)
    ranked: list[dict[str, Any]] = []
    debug_rows: list[dict[str, Any]] = []

    for item_type, item_id, ctx in candidates:
        verified = host_is_verified(db, ctx.host_id)
        result = score_opportunity(
            db,
            campaign=campaign,
            sponsor=sponsor,
            item_type=item_type,
            item_id=item_id,
            ctx=ctx,
            verified=verified,
            saved_tokens=saved_tokens,
        )
        if result.excluded:
            excluded_counts[result.excluded] = excluded_counts.get(result.excluded, 0) + 1
            continue
        if result.score < C.SCORE_MIN_SHOW:
            excluded_counts["below_min_score"] = excluded_counts.get("below_min_score", 0) + 1
            continue
        if not result.reasons:
            excluded_counts["no_safe_reason"] = excluded_counts.get("no_safe_reason", 0) + 1
            continue

        saved_by = sponsor.owner_user_id or sponsor.user_id or campaign.created_by_user_id
        fake_saved = SponsorSavedItem(
            sponsor_id=sponsor.id,
            saved_by_user_id=saved_by,
            item_type=item_type,
            item_id=item_id,
        )
        enriched = _enrich_item(db, fake_saved)
        payload = {
            "item_type": item_type,
            "item_id": item_id,
            "score": result.score,
            "score_label": _score_label(result.score),
            "reasons": result.reasons,
            "title": enriched.get("title"),
            "subtitle": enriched.get("subtitle"),
            "href": enriched.get("href"),
            "available": enriched.get("available", False),
            "host_display_name": ctx.host.display_name,
            "slot_price": float(ctx.slot_price) if ctx.slot_price is not None else None,
            "audience_estimate": ctx.audience_estimate,
        }
        ranked.append((result.score, payload))
        if debug:
            debug_rows.append(
                {
                    "item_type": item_type,
                    "item_id": str(item_id),
                    "score": result.score,
                    "breakdown": result.breakdown,
                    "reason_codes": [r["code"] for r in result.reasons],
                }
            )

    ranked.sort(key=lambda x: x[0], reverse=True)
    items = [p for _, p in ranked[:limit]]

    out: dict[str, Any] = {"items": items, "total": len(items)}
    if debug:
        out["debug"] = {
            "candidate_count": len(candidates),
            "excluded": excluded_counts,
            "top": debug_rows[:15],
        }
    return out
