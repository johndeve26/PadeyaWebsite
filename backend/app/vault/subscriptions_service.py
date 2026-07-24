"""Vault subscription create/cancel/archive lifecycle."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.hosts.models import Host
from app.hosts.service import get_host_by_id, require_user_host
from app.users.models import User
from app.users.service import user_has_permission
from app.vault.models import VaultSubscription


def create_subscription(
    db: Session,
    *,
    user: User,
    host_id: uuid.UUID,
    plan_label: str = "standard",
    price: Decimal = Decimal("0.00"),
    currency: str = "NGN",
) -> VaultSubscription:
    host = get_host_by_id(db, host_id)
    if host is None:
        raise HTTPException(status_code=404, detail="Host not found")

    from app.hosts.fan_self_abuse import assert_not_own_host_as_fan

    assert_not_own_host_as_fan(
        db,
        user_id=user.id,
        host_id=host.id,
        detail=(
            "You can’t subscribe to your own host vault. "
            "Subscribe to other hosts on Pàdéyá instead."
        ),
    )

    existing = db.scalar(
        select(VaultSubscription).where(
            VaultSubscription.host_id == host_id,
            VaultSubscription.buyer_user_id == user.id,
        )
    )
    if existing is not None:
        if existing.status == "active" and existing.archived_at is None:
            raise HTTPException(status_code=409, detail="Already subscribed")
        existing.status = "active"
        existing.plan_label = plan_label
        existing.price = price
        existing.currency = currency.upper()
        existing.started_at = datetime.now(UTC)
        existing.cancelled_at = None
        existing.ends_at = None
        existing.archived_at = None
        existing.archived_by = None
        write_audit_log(
            db,
            action="vault.subscription_reactivate",
            actor_user_id=user.id,
            resource_type="vault_subscription",
            resource_id=str(existing.id),
        )
        db.commit()
        db.refresh(existing)
        return existing

    row = VaultSubscription(
        host_id=host_id,
        buyer_user_id=user.id,
        status="active",
        plan_label=plan_label,
        price=price,
        currency=currency.upper(),
        started_at=datetime.now(UTC),
    )
    db.add(row)
    db.flush()
    write_audit_log(
        db,
        action="vault.subscription_create",
        actor_user_id=user.id,
        resource_type="vault_subscription",
        resource_id=str(row.id),
        details={"host_id": str(host_id), "plan_label": plan_label},
    )
    db.commit()
    db.refresh(row)
    return row


def list_my_subscriptions(
    db: Session, *, user: User, include_archived: bool = False
) -> list[VaultSubscription]:
    q = select(VaultSubscription).where(VaultSubscription.buyer_user_id == user.id)
    if not include_archived:
        q = q.where(VaultSubscription.archived_at.is_(None))
    return list(db.scalars(q.order_by(VaultSubscription.created_at.desc())))


def list_host_subscriptions(
    db: Session, *, user: User, include_archived: bool = False
) -> list[VaultSubscription]:
    host = require_user_host(db, user)
    q = select(VaultSubscription).where(VaultSubscription.host_id == host.id)
    if not include_archived:
        q = q.where(VaultSubscription.archived_at.is_(None))
    return list(db.scalars(q.order_by(VaultSubscription.created_at.desc())))


def _get_owned_or_admin(
    db: Session, *, user: User, subscription_id: uuid.UUID
) -> VaultSubscription:
    row = db.get(VaultSubscription, subscription_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Subscription not found")
    if row.buyer_user_id == user.id or user_has_permission(user, "admin.full_access"):
        return row
    host = db.scalar(select(Host).where(Host.user_id == user.id))
    if host is not None and host.id == row.host_id:
        return row
    raise HTTPException(status_code=403, detail="Not authorized for this subscription")


def cancel_subscription(
    db: Session, *, user: User, subscription_id: uuid.UUID
) -> VaultSubscription:
    row = _get_owned_or_admin(db, user=user, subscription_id=subscription_id)
    if row.status == "cancelled":
        return row
    row.status = "cancelled"
    row.cancelled_at = datetime.now(UTC)
    write_audit_log(
        db,
        action="vault.subscription_cancel",
        actor_user_id=user.id,
        resource_type="vault_subscription",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    return row


def archive_subscription(
    db: Session, *, user: User, subscription_id: uuid.UUID
) -> VaultSubscription:
    row = _get_owned_or_admin(db, user=user, subscription_id=subscription_id)
    if row.status not in {"cancelled", "expired"} and row.archived_at is None:
        raise HTTPException(
            status_code=400,
            detail="Cancel subscription before archiving",
        )
    if row.archived_at is not None:
        return row
    row.archived_at = datetime.now(UTC)
    row.archived_by = user.id
    write_audit_log(
        db,
        action="vault.subscription_archive",
        actor_user_id=user.id,
        resource_type="vault_subscription",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    return row


def restore_subscription(
    db: Session, *, user: User, subscription_id: uuid.UUID
) -> VaultSubscription:
    row = _get_owned_or_admin(db, user=user, subscription_id=subscription_id)
    if row.archived_at is None:
        return row
    row.archived_at = None
    row.archived_by = None
    write_audit_log(
        db,
        action="vault.subscription_restore",
        actor_user_id=user.id,
        resource_type="vault_subscription",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    return row


def delete_subscription_blocked() -> None:
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail="Hard delete blocked for subscriptions; use cancel/archive",
    )


def list_active_subscriber_user_ids(db: Session, host_id: uuid.UUID) -> list[uuid.UUID]:
    return list(
        db.scalars(
            select(VaultSubscription.buyer_user_id).where(
                VaultSubscription.host_id == host_id,
                VaultSubscription.status == "active",
                VaultSubscription.archived_at.is_(None),
            )
        )
    )
