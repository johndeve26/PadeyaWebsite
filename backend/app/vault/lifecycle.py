"""Vault item lifecycle transitions and effective status refresh."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.vault.access import access_window_state, item_is_expired
from app.vault.constants import ITEM_STATUSES, LEGACY_ITEM_STATUS_MAP
from app.vault.models import VaultItem

HOST_EDITABLE_STATUSES = frozenset(
    {"draft", "published", "scheduled", "expired", "archived"}
)
HOST_RESTORE_FROM = frozenset({"archived", "expired"})
PUBLIC_LISTABLE_STATUSES = frozenset({"published"})
NON_PUBLIC_STATUSES = frozenset(
    {"draft", "scheduled", "expired", "archived", "hidden_by_admin"}
)


def normalize_item_status(status: str | None) -> str:
    if not status:
        return "draft"
    return LEGACY_ITEM_STATUS_MAP.get(status, status)


def is_publicly_listable(item: VaultItem) -> bool:
    status = normalize_item_status(item.status)
    if status not in PUBLIC_LISTABLE_STATUSES:
        return False
    if item.moderation_status == "removed":
        return False
    if item_is_expired(item):
        return False
    return True


def ensure_vault_item_lifecycle(item: VaultItem, *, now: datetime | None = None) -> bool:
    """
    Apply time-based transitions in place.
    Returns True when status changed.
    - disabled → archived (legacy)
    - published/scheduled + expires_at passed → expired
    - scheduled + access start reached → published
    """
    current = now or datetime.now(UTC)
    changed = False
    status = normalize_item_status(item.status)
    if status != item.status:
        item.status = status
        changed = True

    if status in {"published", "scheduled"} and item_is_expired(item, now=current):
        item.status = "expired"
        return True

    if status == "scheduled":
        window = access_window_state(item.access_rule, now=current)
        if window != "not_started":
            item.status = "published"
            if item.published_at is None:
                item.published_at = current
            changed = True

    return changed


def assert_host_can_edit(item: VaultItem) -> None:
    status = normalize_item_status(item.status)
    if status == "hidden_by_admin":
        raise HTTPException(
            status_code=403,
            detail="Hidden by admin — host cannot edit until restored by moderation",
        )
    if item.moderation_status == "removed":
        raise HTTPException(
            status_code=403,
            detail="Removed by moderation — host cannot edit",
        )
    if status not in HOST_EDITABLE_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Vault item status '{status}' cannot be edited by host",
        )


def apply_publish(item: VaultItem, *, now: datetime | None = None) -> None:
    current = now or datetime.now(UTC)
    status = normalize_item_status(item.status)
    if status in {"archived", "hidden_by_admin"}:
        raise HTTPException(
            status_code=400,
            detail="Restore the drop before publishing",
        )
    if status == "expired":
        raise HTTPException(
            status_code=400,
            detail="Expired drops must be restored to draft before publishing",
        )
    item.status = "published"
    item.archived_at = None
    item.archived_by = None
    if item.published_at is None:
        item.published_at = current


def apply_unpublish(item: VaultItem) -> None:
    status = normalize_item_status(item.status)
    if status not in {"published", "scheduled"}:
        raise HTTPException(
            status_code=400,
            detail="Only published or scheduled drops can be unpublished",
        )
    item.status = "draft"


def apply_schedule(item: VaultItem, *, starts_at: datetime | None) -> None:
    status = normalize_item_status(item.status)
    if status in {"archived", "hidden_by_admin", "expired"}:
        raise HTTPException(
            status_code=400,
            detail="Restore the drop before scheduling",
        )
    if starts_at is None:
        raise HTTPException(
            status_code=400,
            detail="Schedule requires an access start time",
        )
    if starts_at.tzinfo is None:
        starts_at = starts_at.replace(tzinfo=UTC)
    if starts_at <= datetime.now(UTC):
        raise HTTPException(
            status_code=400,
            detail="Schedule start must be in the future — use publish for immediate go-live",
        )
    rule = item.access_rule
    if rule is None:
        raise HTTPException(
            status_code=400,
            detail="Access rule required before scheduling",
        )
    rule.starts_at = starts_at
    item.status = "scheduled"
    item.archived_at = None
    item.archived_by = None


def apply_archive(item: VaultItem, *, user_id, now: datetime | None = None) -> None:
    current = now or datetime.now(UTC)
    status = normalize_item_status(item.status)
    if status == "archived":
        return
    if status == "hidden_by_admin":
        raise HTTPException(
            status_code=403,
            detail="Hidden by admin — host cannot archive; contact support",
        )
    item.status = "archived"
    item.archived_at = current
    item.archived_by = user_id


def apply_host_restore(item: VaultItem) -> None:
    status = normalize_item_status(item.status)
    if status == "hidden_by_admin" or item.moderation_status == "removed":
        raise HTTPException(
            status_code=403,
            detail="Only admins can restore moderated or admin-hidden drops",
        )
    if status not in HOST_RESTORE_FROM:
        raise HTTPException(
            status_code=400,
            detail="Only archived or expired drops can be restored by the host",
        )
    item.status = "draft"
    item.archived_at = None
    item.archived_by = None


def apply_admin_hide(item: VaultItem, *, user_id, now: datetime | None = None) -> None:
    current = now or datetime.now(UTC)
    item.status = "hidden_by_admin"
    item.moderation_status = "flagged"
    item.archived_at = current
    item.archived_by = user_id


def apply_admin_remove(item: VaultItem, *, user_id, now: datetime | None = None) -> None:
    current = now or datetime.now(UTC)
    item.status = "archived"
    item.moderation_status = "removed"
    item.archived_at = current
    item.archived_by = user_id


def apply_admin_restore(item: VaultItem) -> None:
    """Admin restore from hidden/archived/removed → published (or draft if never live)."""
    item.moderation_status = "approved"
    item.archived_at = None
    item.archived_by = None
    if item.published_at is not None and not item_is_expired(item):
        item.status = "published"
    else:
        item.status = "draft"


def persist_lifecycle_if_changed(db: Session, item: VaultItem) -> None:
    if ensure_vault_item_lifecycle(item):
        db.add(item)
        db.commit()
