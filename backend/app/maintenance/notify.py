"""Maintenance advance notifications (in-app / email / push)."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.email.service import enqueue_template
from app.maintenance.models import MaintenanceNotification
from app.notifications.service import notify_user
from app.users.models import User

logger = logging.getLogger("padeya.maintenance.notify")


def _audience_user_ids(db: Session, audience: str, actor: User) -> list[UUID]:
    if audience == "admins":
        # Approximate: users with any admin-ish role name
        from app.users.models import Role, UserRole

        rows = db.scalars(
            select(User.id)
            .join(UserRole, UserRole.user_id == User.id)
            .join(Role, Role.id == UserRole.role_id)
            .where(Role.name.in_(["super_admin", "admin", "support_agent", "finance_admin"]))
            .distinct()
        ).all()
        return list(rows)
    if audience == "self":
        return [actor.id]
    # all_users / hosts / ticket_buyers / upcoming — v1: all active users (capped)
    rows = db.scalars(
        select(User.id).where(User.is_active.is_(True)).limit(5000)
    ).all()
    return list(rows)


def deliver_maintenance_notification(
    db: Session,
    *,
    row: MaintenanceNotification,
    actor: User,
) -> int:
    user_ids = _audience_user_ids(db, row.audience, actor)
    channels = {str(c).lower() for c in (row.channels or [])}
    count = 0
    for uid in user_ids:
        try:
            if "in_app" in channels or "push" in channels:
                notify_user(
                    db,
                    user_id=uid,
                    kind="system.maintenance",
                    title=row.title[:120],
                    body=row.body[:500],
                    link_path="/maintenance",
                    dedupe_key=f"maint-notice:{row.id}:{uid}",
                    send_push="push" in channels,
                )
                count += 1
            if "email" in channels:
                user = db.get(User, uid)
                if user and user.email:
                    enqueue_template(
                        db,
                        template="security_alert",
                        to=user.email,
                        context={
                            "detail": f"{row.title}\n\n{row.body[:800]}",
                            "full_name": user.full_name or user.email,
                        },
                        recipient_user_id=uid,
                        dedupe_key=f"maint-email:{row.id}:{uid}",
                        force=True,
                    )
                    count += 1
        except Exception:  # noqa: BLE001
            logger.exception("maintenance notify failed user=%s", uid)
    return count


def send_test_to_self(
    db: Session,
    *,
    actor: User,
    title: str,
    body: str,
    channels: list[str],
) -> int:
    row = MaintenanceNotification(
        title=title,
        body=body,
        channels=channels,
        audience="self",
        created_by_admin_id=actor.id,
        status="sent",
    )
    db.add(row)
    db.flush()
    n = deliver_maintenance_notification(db, row=row, actor=actor)
    row.delivery_count = n
    from datetime import UTC, datetime

    row.sent_at = datetime.now(UTC)
    return n
