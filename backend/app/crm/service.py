"""Host CRM services: follow, segments, announcements."""

from __future__ import annotations

import logging
import re
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.core.email import send_email
from app.crm.audience import audience_stats, resolve_segment_members
from app.crm.constants import SYSTEM_SEGMENTS
from app.crm.models import (
    AnnouncementRecipient,
    AudienceSegment,
    HostAnnouncement,
    HostFollower,
)
from app.crm.schemas import (
    AnnouncementCreate,
    AnnouncementUpdate,
    AudienceSegmentCreate,
    FollowRequest,
)
from app.hosts.models import Host
from app.hosts.service import require_user_host
from app.legacy.service import get_host_by_slug
from app.users.models import User

logger = logging.getLogger("padeya.crm")


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "segment"


def ensure_system_segments(db: Session, host_id: UUID) -> list[AudienceSegment]:
    existing = {
        s.slug: s
        for s in db.scalars(
            select(AudienceSegment).where(AudienceSegment.host_id == host_id)
        )
    }
    created = False
    for item in SYSTEM_SEGMENTS:
        if item["slug"] in existing:
            continue
        db.add(
            AudienceSegment(
                host_id=host_id,
                name=item["name"],
                slug=item["slug"],
                segment_key=item["segment_key"],
                description=item["description"],
                filters=None,
                is_system=True,
            )
        )
        created = True
    if created:
        db.commit()
    return list(
        db.scalars(
            select(AudienceSegment)
            .where(AudienceSegment.host_id == host_id)
            .order_by(AudienceSegment.name)
        )
    )


def _notify_host_new_follower(db: Session, *, host: Host, follower: User) -> None:
    """Alert the host owner — generic copy only (no fan PII in notification body)."""
    host_user = db.get(User, host.user_id)
    if host_user is None or host_user.id == follower.id:
        return
    try:
        from app.notifications.service import notify_user

        notify_user(
            db,
            user_id=host_user.id,
            kind="host.new_follower",
            title="New follower on Pàdéyá",
            body="Someone followed your Legacy Page.",
            link_path="/host/followers",
            dedupe_key=f"crm:follow:{host.id}:{follower.id}",
        )
    except Exception:  # noqa: BLE001 — follow must succeed even if notify fails
        logger.exception(
            "host new follower notification failed host=%s follower=%s",
            host.id,
            follower.id,
        )


def follow_host(db: Session, *, user: User, payload: FollowRequest) -> dict:
    from app.users.restrictions import assert_can_follow_hosts

    assert_can_follow_hosts(db, user)

    host: Host | None = None
    if payload.host_id is not None:
        host = db.get(Host, payload.host_id)
    elif payload.host_slug:
        host = get_host_by_slug(db, payload.host_slug)
    if host is None or host.status != "active":
        raise HTTPException(status_code=404, detail="Host not found")

    from app.hosts.fan_self_abuse import assert_not_own_host_follow

    assert_not_own_host_follow(db, user_id=user.id, host_id=host.id)

    existing = db.scalar(
        select(HostFollower).where(
            HostFollower.host_id == host.id,
            HostFollower.user_id == user.id,
        )
    )
    if existing is not None:
        return {
            "host_id": host.id,
            "display_name": host.display_name,
            "username": host.slug,
            "marketing_opt_in": existing.marketing_opt_in,
            "followed_at": existing.created_at,
        }

    row = HostFollower(
        host_id=host.id,
        user_id=user.id,
        marketing_opt_in=False,
    )
    db.add(row)
    write_audit_log(
        db,
        action="crm.follow",
        actor_user_id=user.id,
        resource_type="host",
        resource_id=str(host.id),
    )
    _notify_host_new_follower(db, host=host, follower=user)
    db.commit()
    db.refresh(row)
    return {
        "host_id": host.id,
        "display_name": host.display_name,
        "username": host.slug,
        "marketing_opt_in": row.marketing_opt_in,
        "followed_at": row.created_at,
    }


def unfollow_host(db: Session, *, user: User, host_id: UUID) -> None:
    row = db.scalar(
        select(HostFollower).where(
            HostFollower.host_id == host_id,
            HostFollower.user_id == user.id,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Not following this host")
    db.delete(row)
    write_audit_log(
        db,
        action="crm.unfollow",
        actor_user_id=user.id,
        resource_type="host",
        resource_id=str(host_id),
    )
    db.commit()


def list_my_following(db: Session, user: User) -> list[dict]:
    from app.hosts.fan_self_abuse import is_user_owner_of_host

    rows = db.scalars(
        select(HostFollower)
        .where(HostFollower.user_id == user.id)
        .order_by(HostFollower.created_at.desc())
    ).all()
    out: list[dict] = []
    for row in rows:
        # Never surface own-host follows on Personal following lists.
        if is_user_owner_of_host(
            db, user_id=user.id, host_profile_id=row.host_id
        ):
            continue
        host = db.get(Host, row.host_id)
        if host is None:
            continue
        out.append(
            {
                "host_id": host.id,
                "display_name": host.display_name,
                "username": host.slug,
                "marketing_opt_in": row.marketing_opt_in,
                "followed_at": row.created_at,
            }
        )
    return out


def update_marketing_opt_in(
    db: Session, *, user: User, host_id: UUID, marketing_opt_in: bool
) -> dict:
    from app.hosts.fan_self_abuse import assert_not_own_host_follow

    assert_not_own_host_follow(db, user_id=user.id, host_id=host_id)

    row = db.scalar(
        select(HostFollower).where(
            HostFollower.host_id == host_id,
            HostFollower.user_id == user.id,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Not following this host")
    row.marketing_opt_in = marketing_opt_in
    write_audit_log(
        db,
        action="crm.marketing_opt_in",
        actor_user_id=user.id,
        resource_type="host_follower",
        resource_id=str(row.id),
        details={"marketing_opt_in": marketing_opt_in},
    )
    db.commit()
    host = db.get(Host, host_id)
    assert host is not None
    return {
        "host_id": host.id,
        "display_name": host.display_name,
        "username": host.slug,
        "marketing_opt_in": row.marketing_opt_in,
        "followed_at": row.created_at,
    }


def host_audience_dashboard(db: Session, user: User) -> dict:
    host = require_user_host(db, user)
    ensure_system_segments(db, host.id)
    return audience_stats(db, host.id)


def list_host_followers(db: Session, user: User) -> list[dict]:
    host = require_user_host(db, user)
    return resolve_segment_members(db, host_id=host.id, segment_key="followers")


def list_audience_members(
    db: Session,
    user: User,
    *,
    segment_key: str | None = None,
    segment_id: UUID | None = None,
    event_id: UUID | None = None,
    ticket_type_id: UUID | None = None,
    check_in_status: str | None = None,
) -> list[dict]:
    host = require_user_host(db, user)
    ensure_system_segments(db, host.id)

    key = segment_key or "past_buyers"
    filters: dict = {}
    if segment_id is not None:
        segment = db.get(AudienceSegment, segment_id)
        if segment is None or segment.host_id != host.id:
            raise HTTPException(status_code=404, detail="Segment not found")
        key = segment.segment_key
        filters = dict(segment.filters or {})

    if event_id is not None:
        filters["event_id"] = str(event_id)
    if ticket_type_id is not None:
        filters["ticket_type_id"] = str(ticket_type_id)
    if check_in_status:
        filters["check_in_status"] = check_in_status
        if key == "past_buyers":
            key = "filtered"

    return resolve_segment_members(
        db, host_id=host.id, segment_key=key, filters=filters
    )


def list_segments(db: Session, user: User) -> list[dict]:
    host = require_user_host(db, user)
    segments = ensure_system_segments(db, host.id)
    out: list[dict] = []
    for segment in segments:
        members = resolve_segment_members(
            db,
            host_id=host.id,
            segment_key=segment.segment_key,
            filters=segment.filters,
        )
        out.append(
            {
                "id": segment.id,
                "name": segment.name,
                "slug": segment.slug,
                "segment_key": segment.segment_key,
                "description": segment.description,
                "filters": segment.filters,
                "is_system": segment.is_system,
                "created_at": segment.created_at,
                "member_count": len(members),
            }
        )
    return out


def create_segment(
    db: Session, *, user: User, payload: AudienceSegmentCreate
) -> dict:
    host = require_user_host(db, user)
    ensure_system_segments(db, host.id)
    slug = _slugify(payload.name)
    base = slug
    i = 2
    while db.scalar(
        select(AudienceSegment.id).where(
            AudienceSegment.host_id == host.id,
            AudienceSegment.slug == slug,
        )
    ):
        slug = f"{base}-{i}"
        i += 1

    segment = AudienceSegment(
        host_id=host.id,
        name=payload.name.strip(),
        slug=slug,
        segment_key=payload.segment_key,
        description=payload.description,
        filters=payload.filters,
        is_system=False,
    )
    db.add(segment)
    write_audit_log(
        db,
        action="crm.segment_create",
        actor_user_id=user.id,
        resource_type="audience_segment",
        resource_id=str(segment.id),
        details={"segment_key": payload.segment_key},
    )
    db.commit()
    db.refresh(segment)
    members = resolve_segment_members(
        db,
        host_id=host.id,
        segment_key=segment.segment_key,
        filters=segment.filters,
    )
    return {
        "id": segment.id,
        "name": segment.name,
        "slug": segment.slug,
        "segment_key": segment.segment_key,
        "description": segment.description,
        "filters": segment.filters,
        "is_system": segment.is_system,
        "created_at": segment.created_at,
        "member_count": len(members),
    }


def delete_segment(db: Session, *, user: User, segment_id: UUID) -> None:
    host = require_user_host(db, user)
    segment = db.get(AudienceSegment, segment_id)
    if segment is None or segment.host_id != host.id:
        raise HTTPException(status_code=404, detail="Segment not found")
    if segment.is_system:
        raise HTTPException(status_code=400, detail="System segments cannot be deleted")
    write_audit_log(
        db,
        action="crm.segment_delete",
        actor_user_id=user.id,
        resource_type="audience_segment",
        resource_id=str(segment.id),
        details={"name": segment.name},
    )
    db.delete(segment)
    db.commit()


def cancel_announcement(
    db: Session, *, user: User, announcement_id: UUID
) -> dict:
    host = require_user_host(db, user)
    announcement = db.get(HostAnnouncement, announcement_id)
    if announcement is None or announcement.host_id != host.id:
        raise HTTPException(status_code=404, detail="Announcement not found")
    if announcement.status not in {"draft", "scheduled"}:
        raise HTTPException(
            status_code=400,
            detail="Only draft/scheduled announcements can be cancelled",
        )
    announcement.status = "cancelled"
    write_audit_log(
        db,
        action="crm.announcement_cancel",
        actor_user_id=user.id,
        resource_type="host_announcement",
        resource_id=str(announcement.id),
    )
    db.commit()
    db.refresh(announcement)
    return get_announcement(db, user=user, announcement_id=announcement.id)


def update_announcement(
    db: Session, *, user: User, announcement_id: UUID, payload: AnnouncementUpdate
) -> dict:
    host = require_user_host(db, user)
    announcement = db.get(HostAnnouncement, announcement_id)
    if announcement is None or announcement.host_id != host.id:
        raise HTTPException(status_code=404, detail="Announcement not found")
    if announcement.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft announcements can be edited")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        if key in {"title", "body_email"} and isinstance(value, str):
            setattr(announcement, key, value.strip())
        else:
            setattr(announcement, key, value)
    write_audit_log(
        db,
        action="crm.announcement_update",
        actor_user_id=user.id,
        resource_type="host_announcement",
        resource_id=str(announcement.id),
    )
    db.commit()
    return get_announcement(db, user=user, announcement_id=announcement.id)


def archive_announcement(
    db: Session, *, user: User, announcement_id: UUID
) -> dict:
    """Archive sent/cancelled announcements; recipients remain."""
    host = require_user_host(db, user)
    announcement = db.get(HostAnnouncement, announcement_id)
    if announcement is None or announcement.host_id != host.id:
        raise HTTPException(status_code=404, detail="Announcement not found")
    if announcement.status not in {"sent", "cancelled"}:
        raise HTTPException(
            status_code=400,
            detail="Only sent or cancelled announcements can be archived",
        )
    announcement.status = "archived"
    write_audit_log(
        db,
        action="crm.announcement_archive",
        actor_user_id=user.id,
        resource_type="host_announcement",
        resource_id=str(announcement.id),
    )
    db.commit()
    return get_announcement(db, user=user, announcement_id=announcement.id)


def _whatsapp_export(announcement: HostAnnouncement, recipients: list) -> str:
    lines = [
        f"*{announcement.title}*",
        "",
        announcement.body_whatsapp or announcement.body_email,
        "",
        f"— Recipients ({len(recipients)}):",
    ]
    for r in recipients[:50]:
        lines.append(f"• {r.display_name}")
    if len(recipients) > 50:
        lines.append(f"… and {len(recipients) - 50} more")
    lines.append("")
    lines.append("(WhatsApp broadcast not sent — copy/export only)")
    return "\n".join(lines)


def create_announcement(
    db: Session, *, user: User, payload: AnnouncementCreate
) -> dict:
    host = require_user_host(db, user)
    ensure_system_segments(db, host.id)

    segment = None
    segment_key = payload.segment_key or "followers"
    filters = payload.filters

    if payload.segment_id is not None:
        segment = db.get(AudienceSegment, payload.segment_id)
        if segment is None or segment.host_id != host.id:
            raise HTTPException(status_code=404, detail="Segment not found")
        segment_key = segment.segment_key
        filters = segment.filters

    members = resolve_segment_members(
        db, host_id=host.id, segment_key=segment_key, filters=filters
    )

    announcement = HostAnnouncement(
        host_id=host.id,
        segment_id=segment.id if segment else None,
        title=payload.title.strip(),
        body_email=payload.body_email.strip(),
        body_whatsapp=(payload.body_whatsapp or "").strip() or None,
        channel=payload.channel,
        status="draft",
        delivery_status="not_sent",
        recipient_count=len(members),
    )
    db.add(announcement)
    db.flush()

    for member in members:
        # Email channel: only marketing opt-in; others marked skipped at create time
        can_email = bool(member["marketing_opt_in"])
        recipient_status = "pending"
        skip_reason = None
        if payload.channel in {"email", "both"} and not can_email:
            recipient_status = "skipped"
            skip_reason = "marketing_opt_out"
        db.add(
            AnnouncementRecipient(
                announcement_id=announcement.id,
                user_id=member["user_id"],
                email=member["email"],
                # Prefer greeting_name (settings given name) for {{name}} merge.
                display_name=str(
                    member.get("greeting_name") or member["display_name"] or "there"
                ),
                channel=payload.channel,
                status=recipient_status,
                skip_reason=skip_reason,
            )
        )

    write_audit_log(
        db,
        action="crm.announcement_create",
        actor_user_id=user.id,
        resource_type="host_announcement",
        resource_id=str(announcement.id),
        details={
            "segment_key": segment_key,
            "recipient_count": len(members),
            "channel": payload.channel,
        },
    )
    db.commit()
    return get_announcement(db, user=user, announcement_id=announcement.id)


def list_announcements(db: Session, user: User) -> list[dict]:
    host = require_user_host(db, user)
    rows = db.scalars(
        select(HostAnnouncement)
        .where(HostAnnouncement.host_id == host.id)
        .order_by(HostAnnouncement.created_at.desc())
    ).all()
    return [
        {
            "id": a.id,
            "host_id": a.host_id,
            "segment_id": a.segment_id,
            "title": a.title,
            "body_email": a.body_email,
            "body_whatsapp": a.body_whatsapp,
            "channel": a.channel,
            "status": a.status,
            "delivery_status": a.delivery_status,
            "recipient_count": a.recipient_count,
            "created_at": a.created_at,
            "recipients": [],
            "whatsapp_export": None,
        }
        for a in rows
    ]


def get_announcement(db: Session, *, user: User, announcement_id: UUID) -> dict:
    host = require_user_host(db, user)
    announcement = db.get(HostAnnouncement, announcement_id)
    if announcement is None or announcement.host_id != host.id:
        raise HTTPException(status_code=404, detail="Announcement not found")

    recipients = list(
        db.scalars(
            select(AnnouncementRecipient).where(
                AnnouncementRecipient.announcement_id == announcement.id
            )
        )
    )
    return {
        "id": announcement.id,
        "host_id": announcement.host_id,
        "segment_id": announcement.segment_id,
        "title": announcement.title,
        "body_email": announcement.body_email,
        "body_whatsapp": announcement.body_whatsapp,
        "channel": announcement.channel,
        "status": announcement.status,
        "delivery_status": announcement.delivery_status,
        "recipient_count": announcement.recipient_count,
        "created_at": announcement.created_at,
        "recipients": [
            {
                "id": r.id,
                "user_id": r.user_id,
                "email": r.email,
                "display_name": r.display_name,
                "channel": r.channel,
                "status": r.status,
                "skip_reason": r.skip_reason,
            }
            for r in recipients
        ],
        "whatsapp_export": _whatsapp_export(announcement, recipients),
    }


def _reconcile_recipients_marketing_opt_in(
    db: Session, *, host_id: UUID, recipients: list
) -> int:
    """Promote skipped recipients who opted in after the draft was created."""
    promoted = 0
    for recipient in recipients:
        if recipient.status != "skipped":
            continue
        if recipient.skip_reason != "marketing_opt_out":
            continue
        row = db.scalar(
            select(HostFollower).where(
                HostFollower.host_id == host_id,
                HostFollower.user_id == recipient.user_id,
            )
        )
        if row is None or not row.marketing_opt_in:
            continue
        recipient.status = "pending"
        recipient.skip_reason = None
        promoted += 1
    return promoted


def dispatch_announcement_email(
    db: Session, *, user: User, announcement_id: UUID
) -> dict:
    host = require_user_host(db, user)
    announcement = db.get(HostAnnouncement, announcement_id)
    if announcement is None or announcement.host_id != host.id:
        raise HTTPException(status_code=404, detail="Announcement not found")
    if announcement.channel == "whatsapp":
        raise HTTPException(
            status_code=400,
            detail="WhatsApp is export-only; use the export copy. No WhatsApp send yet.",
        )

    from app.email.config import assert_host_announcement_email_delivery, provider_mode_label

    assert_host_announcement_email_delivery(db)

    recipients = list(
        db.scalars(
            select(AnnouncementRecipient).where(
                AnnouncementRecipient.announcement_id == announcement.id
            )
        )
    )
    _reconcile_recipients_marketing_opt_in(
        db, host_id=host.id, recipients=recipients
    )
    emailed = 0
    skipped = 0
    for recipient in recipients:
        if recipient.status == "skipped":
            skipped += 1
            continue
        if not recipient.email:
            recipient.status = "skipped"
            recipient.skip_reason = "missing_email"
            skipped += 1
            continue
        try:
            from app.email.renderer import render_host_announcement
            from app.users.models import User as UserModel

            fan = db.get(UserModel, recipient.user_id)
            greeting = (
                (fan.full_name or "").strip().split()[0]
                if fan and (fan.full_name or "").strip()
                else (recipient.display_name or "").strip().split()[0]
                if (recipient.display_name or "").strip()
                else "there"
            )

            try:
                subject, text_body, html_body = render_host_announcement(
                    title=announcement.title,
                    body=announcement.body_email,
                    host_name=host.display_name,
                    host_slug=host.slug,
                    db=db,
                    recipient_name=greeting,
                )
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(exc),
                ) from exc
            result = send_email(
                to=recipient.email,
                subject=subject,
                body=text_body,
                html=html_body,
                metadata={
                    "announcement_id": str(announcement.id),
                    "host_id": str(host.id),
                    "type": "host_announcement",
                },
                db=db,
            )
            if not result.ok or result.skipped:
                recipient.status = "failed"
                recipient.skip_reason = result.error or result.provider or "send_failed"
                skipped += 1
                continue
            recipient.status = "sent"
            emailed += 1
        except Exception:  # noqa: BLE001
            recipient.status = "failed"
            recipient.skip_reason = "send_failed"
            skipped += 1

    if emailed > 0:
        announcement.status = "sent"
        announcement.delivery_status = (
            "email_delivered" if skipped == 0 else "email_partial"
        )
    else:
        announcement.delivery_status = "not_sent"
    write_audit_log(
        db,
        action="crm.announcement_dispatch_email",
        actor_user_id=user.id,
        resource_type="host_announcement",
        resource_id=str(announcement.id),
        details={"emailed": emailed, "skipped": skipped, "provider": provider_mode_label(db=db)},
    )
    db.commit()
    return {
        "announcement_id": announcement.id,
        "emailed": emailed,
        "skipped": skipped,
        "delivery_status": announcement.delivery_status,
        "delivery_provider": provider_mode_label(db=db),
    }
