"""Host onboarding and profile services."""

from __future__ import annotations

import re
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.audit import write_audit_log
from app.hosts.models import Host, HostProfile, HostVerification
from app.hosts.schemas import HostOnboardRequest, HostProfileUpdate
from app.passport.models import FanPassport
from app.users.models import User
from app.users.service import get_role_by_name


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "host"


def unique_host_slug(db: Session, base: str) -> str:
    slug = slugify(base)
    candidate = slug
    i = 2
    while db.scalar(select(Host.id).where(Host.slug == candidate)):
        candidate = f"{slug}-{i}"
        i += 1
    return candidate


def _host_slug_for_onboard(db: Session, user: User, display_name: str) -> str:
    passport = db.scalar(
        select(FanPassport.username).where(FanPassport.user_id == user.id)
    )
    if passport:
        taken = db.scalar(select(Host.id).where(Host.slug == passport).limit(1))
        if taken is None:
            return passport
    return unique_host_slug(db, display_name)


def get_host_by_user_id(db: Session, user_id: uuid.UUID) -> Host | None:
    return db.scalar(
        select(Host)
        .where(Host.user_id == user_id)
        .options(
            selectinload(Host.profile),
            selectinload(Host.verifications),
        )
    )


def get_host_by_id(db: Session, host_id: uuid.UUID) -> Host | None:
    return db.scalar(
        select(Host)
        .where(Host.id == host_id)
        .options(selectinload(Host.profile))
    )


def require_user_host(db: Session, user: User) -> Host:
    host = get_host_by_user_id(db, user.id)
    if host is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Host profile not found. Complete onboarding first.",
        )
    return host


def require_actor_host(
    db: Session,
    user: User,
    *,
    permission: str | tuple[str, ...] = "events.read_own",
) -> Host:
    """Resolve host from active workspace or owned host; team members included."""
    from app.users.service import user_has_permission

    if user_has_permission(user, "admin.full_access"):
        from app.teams.workspace_pref import get_active_workspace_id

        active = get_active_workspace_id(db, user_id=user.id)
        if active is not None:
            host = get_host_by_id(db, active)
            if host is not None and host.status == "active":
                return host
        owned = get_host_by_user_id(db, user.id)
        if owned is not None:
            return owned

    from app.hosts.team_access import require_host_for_permission

    host, _ = require_host_for_permission(
        db,
        user=user,
        host_id=None,
        permission=permission,
    )
    return host


def onboard_host(
    db: Session,
    *,
    user: User,
    payload: HostOnboardRequest,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> Host:
    existing = get_host_by_user_id(db, user.id)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Host profile already exists",
        )

    host_role = get_role_by_name(db, "host")
    if host_role is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Host role is not seeded",
        )
    if host_role not in user.roles:
        user.roles.append(host_role)

    host = Host(
        user_id=user.id,
        display_name=payload.display_name.strip(),
        slug=_host_slug_for_onboard(db, user, payload.display_name.strip()),
        status="active",
    )
    db.add(host)
    db.flush()

    profile = HostProfile(
        host_id=host.id,
        bio=payload.bio,
        website=payload.website,
        city=payload.city,
        state=payload.state,
        country=payload.country,
    )
    # Carry over the account photo so Host Legacy matches Fan Passport.
    passport_avatar = db.scalar(
        select(FanPassport.avatar_url).where(FanPassport.user_id == user.id)
    )
    if passport_avatar:
        profile.avatar_url = passport_avatar
    verification = HostVerification(host_id=host.id, status="pending")
    db.add(profile)
    db.add(verification)

    write_audit_log(
        db,
        action="hosts.onboard",
        actor_user_id=user.id,
        resource_type="host",
        resource_id=str(host.id),
        details={"display_name": host.display_name},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return require_user_host(db, user)


def update_host_profile(
    db: Session,
    *,
    user: User,
    payload: HostProfileUpdate,
) -> Host:
    from app.taxonomy import service as taxonomy_service

    host = require_user_host(db, user)
    data = payload.model_dump(exclude_unset=True)

    taxonomy_keys = {
        "host_type_slugs",
        "category_slugs",
        "audience_slugs",
        "primary_city_slug",
        "service_area_slugs",
        "niche_positioning",
    }
    taxonomy_payload = {k: data.pop(k) for k in list(data) if k in taxonomy_keys}

    if "display_name" in data and data["display_name"]:
        from app.users.unified_profile import apply_unified_display_name

        apply_unified_display_name(db, user, data.pop("display_name"))

    if host.profile is None:
        host.profile = HostProfile(host_id=host.id)

    if "avatar_url" in data:
        from app.users.unified_profile import apply_unified_avatar

        apply_unified_avatar(db, user, data.pop("avatar_url"))

    if "niche_positioning" in taxonomy_payload:
        links = dict(host.profile.social_links or {})
        niche = taxonomy_payload.pop("niche_positioning")
        if niche:
            links["niche_positioning"] = niche
        else:
            links.pop("niche_positioning", None)
        host.profile.social_links = links or None

    for field, value in data.items():
        setattr(host.profile, field, value)

    if taxonomy_payload:
        taxonomy_service.sync_host_taxonomy(
            db,
            host_id=host.id,
            host_type_slugs=taxonomy_payload.get("host_type_slugs"),
            category_slugs=taxonomy_payload.get("category_slugs"),
            audience_slugs=taxonomy_payload.get("audience_slugs"),
            primary_city_slug=taxonomy_payload.get("primary_city_slug"),
            service_area_slugs=taxonomy_payload.get("service_area_slugs"),
        )

    db.commit()
    return require_user_host(db, user)
