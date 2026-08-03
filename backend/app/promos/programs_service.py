"""Admin platform-wide referral programs and enrollments."""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.promos.constants import (
    ENROLLMENT_APPLICATION,
    ENROLLMENT_INVITE_ONLY,
    ENROLLMENT_MANUAL,
    PROGRAM_PLATFORM_WIDE,
    REFERRAL_OWNER_PLATFORM,
    REFERRAL_SCOPE_PLATFORM,
    SAFE_LANDING_PATHS,
)
from app.promos.models import Ambassador
from app.promos.referral_programs import (
    ReferralProgram,
    ReferralProgramExclusion,
    ReferralProgramRule,
)
from app.users.models import User
from app.users.service import get_user_by_email


ALLOWED_PROGRAM_STATUSES = frozenset(
    {"draft", "scheduled", "active", "paused", "ended", "archived"}
)
ALLOWED_ENROLLMENT_MODES = frozenset(
    {ENROLLMENT_INVITE_ONLY, ENROLLMENT_APPLICATION, ENROLLMENT_MANUAL, "public_open"}
)
ALLOWED_STATUS_TRANSITIONS = {
    "draft": {"scheduled", "active", "archived"},
    "scheduled": {"active", "paused", "ended", "archived"},
    "active": {"paused", "ended", "archived"},
    "paused": {"active", "ended", "archived"},
    "ended": {"archived"},
    "archived": set(),
}


def _safe_landing(path: str | None) -> str:
    raw = (path or "/events").strip() or "/events"
    if raw.startswith("http://") or raw.startswith("https://"):
        raise HTTPException(
            status_code=400,
            detail="Landing destination must be an internal path, not an external URL",
        )
    if not raw.startswith("/"):
        raw = f"/{raw}"
    # Allow exact whitelist or /events/... /shop/... /ambassadors/...
    if raw in SAFE_LANDING_PATHS:
        return raw
    for prefix in ("/events/", "/shop/", "/ambassadors/", "/marketplace/"):
        if raw.startswith(prefix):
            return raw
    raise HTTPException(
        status_code=400,
        detail="Landing path is not an approved internal destination",
    )


def _serialize_rule(rule: ReferralProgramRule) -> dict:
    return {
        "id": rule.id,
        "program_id": rule.program_id,
        "product_type": rule.product_type,
        "commission_mode": rule.commission_mode,
        "commission_value": rule.commission_value,
        "maximum_commission_per_item": rule.maximum_commission_per_item,
        "minimum_order_amount": rule.minimum_order_amount,
        "is_active": rule.is_active,
    }


def serialize_program(db: Session, program: ReferralProgram) -> dict:
    rules = list(
        db.scalars(
            select(ReferralProgramRule).where(
                ReferralProgramRule.program_id == program.id
            )
        ).all()
    )
    exclusions = list(
        db.scalars(
            select(ReferralProgramExclusion).where(
                ReferralProgramExclusion.program_id == program.id
            )
        ).all()
    )
    enrollments = list(
        db.scalars(
            select(Ambassador).where(Ambassador.program_id == program.id)
        ).all()
    )
    return {
        "id": program.id,
        "name": program.name,
        "description": program.description,
        "public_description": program.public_description,
        "scope": program.scope,
        "owner_type": program.owner_type,
        "owner_host_id": program.owner_host_id,
        "event_id": program.event_id,
        "status": program.status,
        "enrollment_mode": program.enrollment_mode,
        "starts_at": program.starts_at,
        "ends_at": program.ends_at,
        "attribution_window_days": program.attribution_window_days,
        "default_landing_path": program.default_landing_path,
        "hold_period_days": program.hold_period_days,
        "budget_total": program.budget_total,
        "per_ambassador_cap": program.per_ambassador_cap,
        "created_by_user_id": program.created_by_user_id,
        "created_at": program.created_at,
        "updated_at": program.updated_at,
        "commission_funded_by": "Padeya"
        if program.scope == REFERRAL_SCOPE_PLATFORM
        else "host",
        "rules": [_serialize_rule(r) for r in rules],
        "exclusions": [
            {
                "id": e.id,
                "host_id": e.host_id,
                "event_id": e.event_id,
            }
            for e in exclusions
        ],
        "enrollment_count": len(enrollments),
    }


def list_programs(
    db: Session,
    *,
    scope: str | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    stmt = select(ReferralProgram).order_by(ReferralProgram.created_at.desc())
    if scope:
        stmt = stmt.where(ReferralProgram.scope == scope)
    if status:
        stmt = stmt.where(ReferralProgram.status == status)
    rows = list(db.scalars(stmt.offset(offset).limit(limit)).all())
    return [serialize_program(db, p) for p in rows]


def get_program(db: Session, program_id: UUID) -> ReferralProgram:
    program = db.get(ReferralProgram, program_id)
    if program is None:
        raise HTTPException(status_code=404, detail="Referral program not found")
    return program


def create_platform_program(
    db: Session,
    *,
    admin: User,
    payload: dict,
) -> dict:
    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Program name is required")
    enrollment_mode = payload.get("enrollment_mode") or ENROLLMENT_MANUAL
    if enrollment_mode not in ALLOWED_ENROLLMENT_MODES:
        raise HTTPException(status_code=400, detail="Invalid enrollment_mode")
    status = payload.get("status") or "active"
    if status not in ALLOWED_PROGRAM_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    landing = _safe_landing(payload.get("default_landing_path"))

    ticket_rule = payload.get("ticket_rule") or payload.get("ticket_commission")
    merch_rule = payload.get("merchandise_rule") or payload.get("merchandise_commission")
    if not ticket_rule and not merch_rule:
        raise HTTPException(
            status_code=400,
            detail="Configure at least one of ticket or merchandise earning rules",
        )

    program = ReferralProgram(
        id=uuid.uuid4(),
        name=name,
        description=(payload.get("description") or None),
        public_description=(payload.get("public_description") or None),
        scope=REFERRAL_SCOPE_PLATFORM,
        owner_type=REFERRAL_OWNER_PLATFORM,
        owner_host_id=None,
        event_id=None,
        status=status,
        enrollment_mode=enrollment_mode,
        starts_at=payload.get("starts_at"),
        ends_at=payload.get("ends_at"),
        attribution_window_days=int(payload.get("attribution_window_days") or 30),
        default_landing_path=landing,
        hold_period_days=int(payload.get("hold_period_days") or 7),
        budget_total=payload.get("budget_total"),
        per_ambassador_cap=payload.get("per_ambassador_cap"),
        created_by_user_id=admin.id,
    )
    db.add(program)
    db.flush()

    def _add_rule(product_type: str, raw: dict | None) -> None:
        if not raw:
            return
        mode = (raw.get("commission_mode") or "percentage").strip().lower()
        if mode == "fixed":
            pass
        elif mode in {"percentage", "percent"}:
            mode = "percentage"
        else:
            raise HTTPException(status_code=400, detail="Invalid commission_mode")
        value = Decimal(str(raw.get("commission_value", 5)))
        if value < 0:
            raise HTTPException(status_code=400, detail="commission_value must be >= 0")
        if mode == "percentage" and value > 100:
            raise HTTPException(status_code=400, detail="percentage cannot exceed 100")
        db.add(
            ReferralProgramRule(
                id=uuid.uuid4(),
                program_id=program.id,
                product_type=product_type,
                commission_mode=mode,
                commission_value=value,
                maximum_commission_per_item=raw.get("maximum_commission_per_item"),
                minimum_order_amount=raw.get("minimum_order_amount"),
                is_active=bool(raw.get("is_active", True)),
            )
        )

    _add_rule("ticket", ticket_rule if isinstance(ticket_rule, dict) else None)
    _add_rule("merchandise", merch_rule if isinstance(merch_rule, dict) else None)

    for host_id in payload.get("excluded_host_ids") or []:
        db.add(
            ReferralProgramExclusion(
                id=uuid.uuid4(), program_id=program.id, host_id=UUID(str(host_id))
            )
        )
    for event_id in payload.get("excluded_event_ids") or []:
        db.add(
            ReferralProgramExclusion(
                id=uuid.uuid4(), program_id=program.id, event_id=UUID(str(event_id))
            )
        )

    write_audit_log(
        db,
        action="referral_programs.create",
        actor_user_id=admin.id,
        resource_type="referral_program",
        resource_id=str(program.id),
        details={
            "scope": REFERRAL_SCOPE_PLATFORM,
            "name": program.name,
            "status": program.status,
            "payer": "platform",
        },
    )
    db.commit()
    db.refresh(program)
    return serialize_program(db, program)


def patch_program(
    db: Session, *, admin: User, program_id: UUID, payload: dict
) -> dict:
    program = get_program(db, program_id)
    if program.scope != REFERRAL_SCOPE_PLATFORM:
        raise HTTPException(
            status_code=400,
            detail="Only platform-wide programs can be edited on this endpoint",
        )
    for field in (
        "name",
        "description",
        "public_description",
        "starts_at",
        "ends_at",
        "budget_total",
        "per_ambassador_cap",
    ):
        if field in payload and payload[field] is not None:
            setattr(program, field, payload[field])
    if "attribution_window_days" in payload and payload["attribution_window_days"] is not None:
        program.attribution_window_days = int(payload["attribution_window_days"])
    if "hold_period_days" in payload and payload["hold_period_days"] is not None:
        program.hold_period_days = int(payload["hold_period_days"])
    if "default_landing_path" in payload:
        program.default_landing_path = _safe_landing(payload["default_landing_path"])
    if "enrollment_mode" in payload and payload["enrollment_mode"]:
        if payload["enrollment_mode"] not in ALLOWED_ENROLLMENT_MODES:
            raise HTTPException(status_code=400, detail="Invalid enrollment_mode")
        program.enrollment_mode = payload["enrollment_mode"]

    if "ticket_rule" in payload and payload["ticket_rule"] is not None:
        _upsert_rule(db, program.id, "ticket", payload["ticket_rule"])
    if "merchandise_rule" in payload and payload["merchandise_rule"] is not None:
        _upsert_rule(db, program.id, "merchandise", payload["merchandise_rule"])

    write_audit_log(
        db,
        action="referral_programs.update",
        actor_user_id=admin.id,
        resource_type="referral_program",
        resource_id=str(program.id),
        details={"fields": sorted(payload.keys())},
    )
    db.commit()
    db.refresh(program)
    return serialize_program(db, program)


def _upsert_rule(db: Session, program_id: UUID, product_type: str, raw: dict) -> None:
    existing = db.scalar(
        select(ReferralProgramRule).where(
            ReferralProgramRule.program_id == program_id,
            ReferralProgramRule.product_type == product_type,
        )
    )
    mode = (raw.get("commission_mode") or "percentage").strip().lower()
    if mode == "fixed":
        pass
    elif mode in {"percentage", "percent"}:
        mode = "percentage"
    else:
        raise HTTPException(status_code=400, detail="Invalid commission_mode")
    value = Decimal(str(raw.get("commission_value", 5)))
    if existing is None:
        db.add(
            ReferralProgramRule(
                id=uuid.uuid4(),
                program_id=program_id,
                product_type=product_type,
                commission_mode=mode,
                commission_value=value,
                maximum_commission_per_item=raw.get("maximum_commission_per_item"),
                minimum_order_amount=raw.get("minimum_order_amount"),
                is_active=bool(raw.get("is_active", True)),
            )
        )
    else:
        existing.commission_mode = mode
        existing.commission_value = value
        if "maximum_commission_per_item" in raw:
            existing.maximum_commission_per_item = raw.get("maximum_commission_per_item")
        if "minimum_order_amount" in raw:
            existing.minimum_order_amount = raw.get("minimum_order_amount")
        if "is_active" in raw:
            existing.is_active = bool(raw["is_active"])


def transition_program(
    db: Session, *, admin: User, program_id: UUID, new_status: str
) -> dict:
    program = get_program(db, program_id)
    if new_status not in ALLOWED_PROGRAM_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    allowed = ALLOWED_STATUS_TRANSITIONS.get(program.status, set())
    if new_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition from {program.status} to {new_status}",
        )
    program.status = new_status
    write_audit_log(
        db,
        action="referral_programs.status",
        actor_user_id=admin.id,
        resource_type="referral_program",
        resource_id=str(program.id),
        details={"status": new_status},
    )
    db.commit()
    db.refresh(program)
    return serialize_program(db, program)


def _unique_platform_code(db: Session, *, preferred: str | None = None) -> str:
    base = (preferred or "").strip().lower()
    for _ in range(20):
        code = base or f"pad{secrets.token_hex(3)}"
        if base and _ > 0:
            code = f"{base}{secrets.token_hex(2)}"
        exists = db.scalar(
            select(Ambassador).where(
                Ambassador.referral_code == code,
                Ambassador.program_kind == PROGRAM_PLATFORM_WIDE,
            )
        )
        if exists is None:
            return code
        if not preferred:
            base = ""
    raise HTTPException(status_code=500, detail="Could not allocate referral code")


def _preferred_platform_code_for_user(db: Session, user: User) -> str | None:
    """Fan Passport / unified username is the standard platform-wide code."""
    from app.passport.privacy import is_valid_passport_username, normalize_username
    from app.users.unified_profile import resolve_user_username

    raw = resolve_user_username(db, user)
    if not raw:
        return None
    username = normalize_username(raw)
    if not is_valid_passport_username(username):
        return None
    return username


def sync_platform_referral_codes_for_username(
    db: Session, *, user_id: UUID, username: str
) -> None:
    """Keep active platform-wide codes aligned with Fan Passport username."""
    from app.passport.privacy import is_valid_passport_username, normalize_username

    code = normalize_username(username)
    if not is_valid_passport_username(code):
        return
    clash = db.scalar(
        select(Ambassador).where(
            Ambassador.referral_code == code,
            Ambassador.program_kind == PROGRAM_PLATFORM_WIDE,
            Ambassador.user_id != user_id,
        )
    )
    if clash is not None:
        return
    rows = list(
        db.scalars(
            select(Ambassador).where(
                Ambassador.user_id == user_id,
                Ambassador.program_kind == PROGRAM_PLATFORM_WIDE,
                Ambassador.status.in_(["active", "invited", "pending"]),
            )
        ).all()
    )
    for amb in rows:
        if amb.referral_code == code:
            continue
        amb.referral_code = code


def enroll_user(
    db: Session,
    *,
    admin: User,
    program_id: UUID,
    user_id: UUID | None = None,
    email: str | None = None,
    display_name: str | None = None,
    referral_code: str | None = None,
    status: str = "active",
) -> dict:
    program = get_program(db, program_id)
    if program.scope != REFERRAL_SCOPE_PLATFORM:
        raise HTTPException(
            status_code=400, detail="Enrollment endpoint is for platform programs"
        )
    if program.status in {"ended", "archived"}:
        raise HTTPException(status_code=400, detail="Program is closed")

    user: User | None = None
    if user_id is not None:
        user = db.get(User, user_id)
    elif email:
        user = get_user_by_email(db, email.strip().lower())
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    existing = db.scalar(
        select(Ambassador).where(
            Ambassador.program_id == program.id,
            Ambassador.user_id == user.id,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="User already enrolled")

    preferred = (referral_code or "").strip().lower() or _preferred_platform_code_for_user(
        db, user
    )
    code = _unique_platform_code(db, preferred=preferred)
    amb = Ambassador(
        host_id=None,
        event_id=None,
        campaign_id=None,
        program_id=program.id,
        user_id=user.id,
        program_kind=PROGRAM_PLATFORM_WIDE,
        referral_code=code,
        display_name=(display_name or user.full_name or user.email or "Ambassador")[:160],
        email=user.email,
        status=status if status in {"invited", "pending", "active"} else "active",
        commission_rate_percent=Decimal("0"),
        terms_accepted_at=datetime.now(UTC) if status == "active" else None,
        terms_version="2026-08-03" if status == "active" else None,
    )
    db.add(amb)
    db.flush()
    write_audit_log(
        db,
        action="referral_programs.enroll",
        actor_user_id=admin.id,
        resource_type="ambassador",
        resource_id=str(amb.id),
        details={
            "program_id": str(program.id),
            "user_id": str(user.id),
            "referral_code": code,
            "status": amb.status,
            "code_source": "username" if preferred and code == preferred else "generated",
        },
    )
    db.commit()
    db.refresh(amb)
    return {
        "id": amb.id,
        "program_id": program.id,
        "ambassador_user_id": user.id,
        "status": amb.status,
        "referral_code": amb.referral_code,
        "referral_link_path": f"/r/{amb.referral_code}",
        "display_name": amb.display_name,
        "joined_at": amb.created_at,
    }


def list_enrollments(db: Session, program_id: UUID) -> list[dict]:
    get_program(db, program_id)
    rows = list(
        db.scalars(
            select(Ambassador).where(Ambassador.program_id == program_id)
        ).all()
    )
    return [
        {
            "id": a.id,
            "program_id": a.program_id,
            "ambassador_user_id": a.user_id,
            "status": a.status,
            "referral_code": a.referral_code,
            "referral_link_path": f"/r/{a.referral_code}",
            "display_name": a.display_name,
            "joined_at": a.created_at,
        }
        for a in rows
    ]


def patch_enrollment(
    db: Session, *, admin: User, enrollment_id: UUID, payload: dict
) -> dict:
    amb = db.get(Ambassador, enrollment_id)
    if amb is None or amb.program_kind != PROGRAM_PLATFORM_WIDE:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    status = payload.get("status")
    if status is not None:
        if status not in {"invited", "pending", "active", "suspended", "ended"}:
            raise HTTPException(status_code=400, detail="Invalid enrollment status")
        amb.status = status
    write_audit_log(
        db,
        action="referral_programs.enrollment_update",
        actor_user_id=admin.id,
        resource_type="ambassador",
        resource_id=str(amb.id),
        details={"status": amb.status},
    )
    db.commit()
    db.refresh(amb)
    return {
        "id": amb.id,
        "program_id": amb.program_id,
        "ambassador_user_id": amb.user_id,
        "status": amb.status,
        "referral_code": amb.referral_code,
        "referral_link_path": f"/r/{amb.referral_code}",
        "display_name": amb.display_name,
        "joined_at": amb.created_at,
    }


def resolve_public_referral_code(db: Session, code: str) -> dict:
    """Validate platform (or event) code for /r/{code} redirect."""
    normalized = (code or "").strip().lower()
    if not normalized:
        raise HTTPException(status_code=404, detail="Referral code not found")
    amb = db.scalar(
        select(Ambassador).where(
            Ambassador.referral_code == normalized,
            Ambassador.status == "active",
            Ambassador.program_kind == PROGRAM_PLATFORM_WIDE,
        )
    )
    if amb is None:
        # Fall back: any active ambassador — redirect to events with ?ref=
        amb = db.scalar(
            select(Ambassador).where(
                Ambassador.referral_code == normalized,
                Ambassador.status == "active",
            )
        )
        if amb is None:
            raise HTTPException(status_code=404, detail="Referral code not found")
        landing = "/events"
        if amb.event_id is not None:
            from app.events.models import Event

            event = db.get(Event, amb.event_id)
            if event is not None and event.slug:
                landing = f"/events/{event.slug}?ref={normalized}"
            else:
                landing = f"/events?ref={normalized}"
        else:
            landing = f"/events?ref={normalized}"
        return {
            "referral_code": normalized,
            "program_id": amb.program_id,
            "enrollment_id": amb.id,
            "landing_path": landing,
            "scope": "event" if amb.program_kind != PROGRAM_PLATFORM_WIDE else "platform",
        }

    program = db.get(ReferralProgram, amb.program_id) if amb.program_id else None
    if program is None or program.status != "active":
        raise HTTPException(status_code=404, detail="Referral program is not active")
    landing = program.default_landing_path or "/events"
    sep = "&" if "?" in landing else "?"
    landing = f"{landing}{sep}ref={normalized}"
    return {
        "referral_code": normalized,
        "program_id": program.id,
        "enrollment_id": amb.id,
        "landing_path": landing,
        "scope": "platform",
        "attribution_window_days": program.attribution_window_days,
    }
