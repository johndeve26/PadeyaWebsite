"""Canonical ambassador referral landing tracking (promos + domain endpoints)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ambassadors.fraud import (
    hash_tracking_fingerprint,
    hash_tracking_ip,
    hash_tracking_ua,
    maybe_flag_click_spike,
    maybe_flag_inflated_click_ratio,
)
from app.ambassadors.referral_click_stats import (
    DEFAULT_UNIQUE_WINDOW_HOURS,
    DUPLICATE_WINDOW_SECONDS,
    _referral_clicks_table_error,
)
from app.ambassadors.service import _find_participant_by_code
from app.auth.models import User
from app.core.config import get_settings
from app.events.models import Event
from app.promos.ambassador_domain import (
    AmbassadorAttribution,
    AmbassadorCampaign,
    AmbassadorParticipant,
)
from app.promos.constants import PROGRAM_HOST_CURATED
from app.promos.models import Ambassador, PromoClick
from app.promos.referral_clicks import ReferralClick
from app.promos.service import (
    _ambassador_attribution_allowed,
    _aware,
    resolve_ambassador_for_event,
)
from sqlalchemy.exc import OperationalError, ProgrammingError


@dataclass(frozen=True)
class ReferralLandingInput:
    referral_code: str
    source: str
    target_type: str
    event_id: UUID | None = None
    merch_product_id: UUID | None = None
    campaign_id: UUID | None = None
    host_id: UUID | None = None
    target_id: UUID | None = None
    landing_path: str | None = None
    landing_url: str | None = None
    referrer_url: str | None = None
    session_id: str | None = None
    anonymous_visitor_id: str | None = None
    visitor_fingerprint: str | None = None
    prefer_merch: bool = False
    user: User | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    unique_window_hours: int = DEFAULT_UNIQUE_WINDOW_HOURS


def _hash_visitor(
    *,
    user_id: UUID | None,
    anonymous_visitor_id: str | None,
    visitor_fingerprint: str | None,
    ip_hash: str | None,
    user_agent_hash: str | None,
) -> str | None:
    secret = get_settings().secret_key
    if user_id is not None:
        raw = f"{secret}|vid|user|{user_id}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:64]
    anon = (anonymous_visitor_id or "").strip()
    if anon:
        return hash_tracking_fingerprint(anon)
    fp = hash_tracking_fingerprint(visitor_fingerprint)
    if fp:
        return fp
    if ip_hash and user_agent_hash:
        raw = f"{secret}|vid|ipua|{ip_hash}|{user_agent_hash}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:64]
    if ip_hash:
        raw = f"{secret}|vid|ip|{ip_hash}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:64]
    return None


def _scope_key(
    *,
    ambassador_id: UUID | None,
    participant_id: UUID | None,
    campaign_id: UUID | None,
    event_id: UUID | None,
    target_type: str,
    target_id: UUID | None,
) -> str:
    parts = [
        str(ambassador_id or ""),
        str(participant_id or ""),
        str(campaign_id or ""),
        str(event_id or ""),
        target_type,
        str(target_id or ""),
    ]
    return "|".join(parts)


def _dedupe_keys(
    *,
    scope: str,
    visitor_hash: str | None,
    ip_hash: str | None,
    event_id: UUID | None,
    ambassador_id: UUID | None,
) -> tuple[str | None, str | None]:
    secret = get_settings().secret_key
    total_raw = f"{secret}|total|{scope}|{ip_hash or ''}|{event_id or ''}|{ambassador_id or ''}"
    total_click_key = hashlib.sha256(total_raw.encode("utf-8")).hexdigest()[:64]
    if not visitor_hash:
        return total_click_key, None
    unique_raw = f"{secret}|unique|{scope}|{visitor_hash}"
    unique_click_key = hashlib.sha256(unique_raw.encode("utf-8")).hexdigest()[:64]
    return total_click_key, unique_click_key


def _resolve_v1_ambassador(
    db: Session, inp: ReferralLandingInput
) -> Ambassador | None:
    code = inp.referral_code.strip().lower()
    if not code:
        return None
    if inp.event_id is not None:
        event = db.get(Event, inp.event_id)
        if event is None:
            raise HTTPException(status_code=404, detail="Event not found")
        return resolve_ambassador_for_event(
            db,
            referral_code=code,
            event=event,
            prefer_merch=inp.prefer_merch
            or inp.target_type == "merch"
            or inp.source == "merch_page",
        )
    ambassador = db.scalar(
        select(Ambassador)
        .where(
            Ambassador.referral_code == code,
            Ambassador.status == "active",
            Ambassador.program_kind == PROGRAM_HOST_CURATED,
            Ambassador.event_id.is_(None),
        )
        .order_by(Ambassador.created_at.desc())
    )
    if ambassador is None:
        ambassador = db.scalar(
            select(Ambassador)
            .where(
                Ambassador.referral_code == code,
                Ambassador.status == "active",
            )
            .order_by(Ambassador.created_at.desc())
        )
    if ambassador is not None and not _ambassador_attribution_allowed(db, ambassador):
        return None
    return ambassador


def _resolve_participant(
    db: Session,
    *,
    code: str,
    campaign_id: UUID | None,
    event_id: UUID | None,
    ambassador: Ambassador | None,
) -> AmbassadorParticipant | None:
    participant = _find_participant_by_code(
        db, code=code, campaign_id=campaign_id, event_id=event_id
    )
    if participant is not None:
        return participant
    if ambassador is None or ambassador.user_id is None:
        return None
    if ambassador.campaign_id is not None:
        return db.scalar(
            select(AmbassadorParticipant).where(
                AmbassadorParticipant.user_id == ambassador.user_id,
                AmbassadorParticipant.campaign_id == ambassador.campaign_id,
                AmbassadorParticipant.status == "active",
            )
        )
    return None


class ReferralTrackingService:
    @staticmethod
    def record_landing(db: Session, inp: ReferralLandingInput) -> dict:
        code = inp.referral_code.strip().lower()
        if not code:
            raise HTTPException(status_code=400, detail="Referral code required")

        ambassador = _resolve_v1_ambassador(db, inp)
        participant = _resolve_participant(
            db,
            code=code,
            campaign_id=inp.campaign_id or (ambassador.campaign_id if ambassador else None),
            event_id=inp.event_id,
            ambassador=ambassador,
        )
        if ambassador is None and participant is None:
            raise HTTPException(status_code=404, detail="Ambassador code not found")

        campaign_id = inp.campaign_id
        if campaign_id is None and participant is not None:
            campaign_id = participant.campaign_id
        if campaign_id is None and ambassador is not None:
            campaign_id = ambassador.campaign_id

        campaign = db.get(AmbassadorCampaign, campaign_id) if campaign_id else None
        if participant is not None and campaign is not None:
            from app.ambassadors.service import campaign_is_joinable

            if not campaign_is_joinable(campaign):
                raise HTTPException(status_code=400, detail="Campaign is not active")

        event_id = inp.event_id
        if event_id is None and campaign is not None:
            event_id = campaign.event_id
        if event_id is None and ambassador is not None:
            event_id = ambassador.event_id

        host_id = inp.host_id
        if host_id is None and ambassador is not None:
            host_id = ambassador.host_id
        if host_id is None and event_id is not None:
            event = db.get(Event, event_id)
            if event is not None:
                host_id = event.host_id

        ip_hash = hash_tracking_ip(inp.ip_address)
        ua_hash = hash_tracking_ua(inp.user_agent)
        user_id = inp.user.id if inp.user else None
        visitor_hash = _hash_visitor(
            user_id=user_id,
            anonymous_visitor_id=inp.anonymous_visitor_id,
            visitor_fingerprint=inp.visitor_fingerprint,
            ip_hash=ip_hash,
            user_agent_hash=ua_hash,
        )

        scope = _scope_key(
            ambassador_id=ambassador.id if ambassador else None,
            participant_id=participant.id if participant else None,
            campaign_id=campaign_id,
            event_id=event_id,
            target_type=inp.target_type,
            target_id=inp.target_id or event_id,
        )
        total_click_key, unique_click_key = _dedupe_keys(
            scope=scope,
            visitor_hash=visitor_hash,
            ip_hash=ip_hash,
            event_id=event_id,
            ambassador_id=ambassador.id if ambassador else None,
        )

        now = datetime.now(UTC)
        is_duplicate_30s = False
        is_unique_24h = False
        landing = inp.landing_url or inp.landing_path
        referral_click_id = None
        try:
            if total_click_key:
                recent = db.scalar(
                    select(ReferralClick)
                    .where(
                        ReferralClick.total_click_key == total_click_key,
                        ReferralClick.is_duplicate_30s.is_(False),
                    )
                    .order_by(ReferralClick.created_at.desc())
                )
                if recent is not None:
                    age = now - _aware(recent.created_at)
                    if age.total_seconds() < DUPLICATE_WINDOW_SECONDS:
                        is_duplicate_30s = True

            if unique_click_key and visitor_hash:
                since = now - timedelta(hours=inp.unique_window_hours)
                prior_unique = db.scalar(
                    select(ReferralClick.id).where(
                        ReferralClick.unique_click_key == unique_click_key,
                        ReferralClick.is_unique_24h.is_(True),
                        ReferralClick.created_at >= since,
                    )
                )
                is_unique_24h = prior_unique is None

            row = ReferralClick(
                ambassador_id=ambassador.id if ambassador else None,
                participant_id=participant.id if participant else None,
                campaign_id=campaign_id,
                event_id=event_id,
                merch_product_id=inp.merch_product_id
                or (campaign.merch_product_id if campaign else None),
                host_id=host_id,
                referral_code=code,
                target_type=inp.target_type,
                target_id=inp.target_id or event_id,
                source=inp.source,
                visitor_hash=visitor_hash,
                user_id=user_id,
                ip_hash=ip_hash,
                user_agent_hash=ua_hash,
                total_click_key=total_click_key,
                unique_click_key=unique_click_key,
                is_unique_24h=is_unique_24h and not is_duplicate_30s,
                is_duplicate_30s=is_duplicate_30s,
                metadata_json={
                    "landing": landing,
                    "referrer": inp.referrer_url,
                    "session_id": inp.session_id,
                },
            )
            db.add(row)
            db.flush()
            referral_click_id = row.id
        except (ProgrammingError, OperationalError) as exc:
            db.rollback()
            if not _referral_clicks_table_error(exc):
                raise
            is_duplicate_30s = False
            is_unique_24h = True
            referral_click_id = None

        if ambassador is not None and not is_duplicate_30s:
            db.add(
                PromoClick(
                    ambassador_id=ambassador.id,
                    event_id=event_id,
                    landing_path=landing,
                    ip_hash=ip_hash,
                    user_agent_hash=ua_hash,
                )
            )

        attribution_id = None
        expires_at = None
        if participant is not None and campaign is not None and not is_duplicate_30s:
            cookie_days = int(
                getattr(campaign, "cookie_window_days", 30) or 30
            )
            expires_at = now + timedelta(days=cookie_days)
            attribution = AmbassadorAttribution(
                campaign_id=campaign.id,
                participant_id=participant.id,
                user_id=user_id,
                session_id=inp.session_id,
                event_id=event_id,
                merch_product_id=inp.merch_product_id or campaign.merch_product_id,
                source="link",
                expires_at=expires_at,
            )
            db.add(attribution)
            db.flush()
            attribution_id = attribution.id
            maybe_flag_click_spike(
                db,
                campaign_id=campaign.id,
                participant_id=participant.id,
                ip_hash=ip_hash,
            )
            maybe_flag_inflated_click_ratio(
                db,
                campaign_id=campaign.id,
                participant_id=participant.id,
            )

        db.commit()
        return {
            "ok": True,
            "click_id": referral_click_id,
            "referral_click_id": referral_click_id,
            "attribution_id": attribution_id,
            "participant_id": participant.id if participant else None,
            "campaign_id": campaign_id,
            "ambassador_id": ambassador.id if ambassador else None,
            "expires_at": expires_at,
            "is_duplicate_30s": is_duplicate_30s,
            "is_unique_24h": is_unique_24h and not is_duplicate_30s,
            "total_clicks_counted": not is_duplicate_30s,
        }

    @staticmethod
    def record_promos_referral(
        db: Session,
        *,
        referral_code: str,
        event_id: UUID | None,
        landing_path: str | None,
        source: str = "event_page",
        anonymous_visitor_id: str | None = None,
        user: User | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> PromoClick:
        result = ReferralTrackingService.record_landing(
            db,
            ReferralLandingInput(
                referral_code=referral_code,
                source=source,
                target_type="merch"
                if source == "merch_page"
                else ("event" if event_id else "host"),
                event_id=event_id,
                landing_path=landing_path,
                anonymous_visitor_id=anonymous_visitor_id,
                user=user,
                ip_address=ip_address,
                user_agent=user_agent,
                prefer_merch=source == "merch_page",
            ),
        )
        ambassador_id = result.get("ambassador_id")
        if ambassador_id:
            legacy = db.scalar(
                select(PromoClick)
                .where(PromoClick.ambassador_id == ambassador_id)
                .order_by(PromoClick.created_at.desc())
            )
            if legacy is not None:
                return legacy
        raise HTTPException(status_code=404, detail="Ambassador code not found")

    @staticmethod
    def record_domain_track_click(
        db: Session,
        *,
        payload,
        user: User | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict:
        source = "campaign_link"
        if payload.merch_product_id:
            source = "merch_page"
        elif payload.event_id:
            source = "event_page"
        target_type = "merch" if payload.merch_product_id else "event"
        if not payload.event_id and not payload.merch_product_id:
            target_type = "campaign"
        return ReferralTrackingService.record_landing(
            db,
            ReferralLandingInput(
                referral_code=payload.ambassador_code,
                source=source,
                target_type=target_type,
                event_id=payload.event_id,
                merch_product_id=payload.merch_product_id,
                campaign_id=payload.campaign_id,
                landing_url=payload.landing_url,
                referrer_url=payload.referrer_url,
                session_id=payload.session_id,
                visitor_fingerprint=payload.visitor_fingerprint,
                user=user,
                ip_address=ip_address,
                user_agent=user_agent,
            ),
        )
