"""Vault CRUD, access-aware serialization, purchases, and moderation."""

from __future__ import annotations

import re
import secrets
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.audit import write_audit_log
from app.core.config import get_settings
from app.core.media import get_media_storage
from app.finance.ledger import append_ledger_entry
from app.hosts.models import Host
from app.hosts.service import require_user_host
from app.payments.config import paystack_runtime
from app.payments.paystack import PaystackError, initialize_transaction
from app.users.models import User
from app.users.service import user_has_permission
from app.events.models import Event
from app.memories.models import EventMemory
from app.vault.access import (
    access_code_is_set,
    access_code_matches,
    access_window_state,
    evaluate_access,
    hash_access_code,
    is_admin_hidden,
    item_is_expired,
    lock_reason_label,
    resolve_required_event_id,
    unlock_cap_reached,
    user_has_paid_unlock,
)
from app.vault.models import (
    VaultAccessGrant,
    VaultAccessRule,
    VaultItem,
    VaultMedia,
    VaultPurchase,
    VaultUnlockAttempt,
    VaultView,
)
from app.vault.lifecycle import (
    apply_admin_hide,
    apply_admin_remove,
    apply_admin_restore,
    apply_archive,
    apply_host_restore,
    apply_publish,
    apply_schedule,
    apply_unpublish,
    assert_host_can_edit,
    ensure_vault_item_lifecycle,
    is_publicly_listable,
    normalize_item_status,
)
from app.vault.schemas import (
    VaultItemCreate,
    VaultItemUpdate,
    VaultModerateRequest,
    VaultScheduleRequest,
)

settings = get_settings()


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "vault-item"


def _unique_slug(db: Session, host_id: UUID, base: str) -> str:
    slug = _slugify(base)[:200]
    candidate = slug
    i = 2
    while db.scalar(
        select(VaultItem.id).where(VaultItem.host_id == host_id, VaultItem.slug == candidate)
    ):
        candidate = f"{slug}-{i}"
        i += 1
    return candidate


def _load_item(db: Session, item_id: UUID) -> VaultItem | None:
    return db.scalar(
        select(VaultItem)
        .where(VaultItem.id == item_id)
        .options(
            selectinload(VaultItem.media),
            selectinload(VaultItem.access_rule),
        )
    )


def _require_host_item(db: Session, user: User, item_id: UUID) -> tuple[Host, VaultItem]:
    host = require_user_host(db, user)
    item = _load_item(db, item_id)
    if item is None or item.host_id != host.id:
        raise HTTPException(status_code=404, detail="Vault item not found")
    return host, item


def _attach_media(db: Session, item: VaultItem, media_inputs: list) -> None:
    storage = get_media_storage()
    for idx, m in enumerate(media_inputs):
        if m.filename:
            stored = storage.build_placeholder_url(filename=m.filename, folder="vault")
            url = m.url.strip() or stored.url
            key = stored.key
        else:
            stored = storage.store_remote_url(url=m.url, folder="vault")
            url = stored.url
            key = stored.key
        db.add(
            VaultMedia(
                vault_item_id=item.id,
                media_type=m.media_type,
                url=url,
                storage_key=key,
                label=m.label,
                is_preview=bool(m.is_preview),
                sort_order=m.sort_order if m.sort_order else idx,
            )
        )


def _set_access_rule(db: Session, item: VaultItem, access) -> None:
    rule = item.access_rule
    ticket_ids = (
        [str(t) for t in access.ticket_type_ids] if access.ticket_type_ids else None
    )
    if rule is None:
        rule = VaultAccessRule(vault_item_id=item.id)
        db.add(rule)
        item.access_rule = rule
    rule.access_type = access.access_type
    required_event = getattr(access, "required_event_id", None) or getattr(
        access, "event_id", None
    )
    rule.event_id = required_event
    rule.required_ticket_type_id = getattr(access, "required_ticket_type_id", None)
    rule.ticket_type_ids = ticket_ids
    rule.require_check_in = bool(getattr(access, "require_check_in", False))
    rule.required_legacy_tier = getattr(access, "required_legacy_tier", None)
    code = getattr(access, "access_code", None)
    if code is not None:
        cleaned = str(code).strip()
        if cleaned:
            # Never store plaintext invite codes — hash at rest
            rule.access_code = hash_access_code(cleaned)
        # Empty string means "keep existing code" (codes are never returned to clients)
    rule.max_unlocks = getattr(access, "max_unlocks", None)
    rule.starts_at = getattr(access, "starts_at", None)
    rule.ends_at = getattr(access, "ends_at", None)

    price = getattr(access, "price", None)
    currency = getattr(access, "currency", None) or item.currency or "NGN"
    if price is not None:
        rule.price = Decimal(price)
        item.price = Decimal(price)
    else:
        rule.price = Decimal(item.price or 0)
    rule.currency = currency
    item.currency = currency

    if access.access_type == "one_time_unlock" and Decimal(item.price or 0) <= 0:
        raise HTTPException(
            status_code=400,
            detail="one_time_unlock items require a price greater than zero",
        )
    if access.access_type == "invite_only" and normalize_item_status(item.status) in {
        "published",
        "scheduled",
    }:
        if not (rule.access_code or "").strip():
            raise HTTPException(
                status_code=400,
                detail="invite_only published items require an access_code",
            )


def _validate_related_links(
    db: Session,
    *,
    host_id: UUID,
    related_event_id: UUID | None,
    related_memory_id: UUID | None,
) -> None:
    if related_event_id is not None:
        event = db.get(Event, related_event_id)
        if event is None or event.host_id != host_id:
            raise HTTPException(status_code=400, detail="related_event_id is invalid")
    if related_memory_id is not None:
        memory = db.get(EventMemory, related_memory_id)
        if memory is None or memory.host_id != host_id:
            raise HTTPException(status_code=400, detail="related_memory_id is invalid")
        if related_event_id is not None and memory.event_id != related_event_id:
            raise HTTPException(
                status_code=400,
                detail="related_memory_id must belong to related_event_id",
            )


def _public_related_event(db: Session, event_id: UUID | None) -> dict | None:
    if event_id is None:
        return None
    event = db.get(Event, event_id)
    if event is None or event.status != "published":
        return None
    return {
        "id": str(event.id),
        "title": event.title,
        "slug": event.slug,
        "href": f"/events/{event.slug}",
    }


def _public_related_memory(db: Session, memory_id: UUID | None) -> dict | None:
    """Public teaser for a published Event Memory — never includes recap body/media."""
    if memory_id is None:
        return None
    memory = db.get(EventMemory, memory_id)
    if (
        memory is None
        or memory.status != "published"
        or memory.moderation_status == "removed"
    ):
        return None
    event = db.get(Event, memory.event_id)
    host = db.get(Host, memory.host_id)
    if event is None or host is None:
        return None
    return {
        "id": str(memory.id),
        "event_id": str(memory.event_id),
        "event_title": event.title,
        "event_slug": event.slug,
        "host_username": host.slug,
        "href": f"/u/{host.slug}/memories/{event.slug}",
    }


def _serialize_access_public(
    *,
    rule: VaultAccessRule | None,
    item: VaultItem,
    has_access: bool,
    owner_view: bool,
) -> dict | None:
    if rule is None:
        return {
            "access_type": "free",
            "price": item.price,
            "currency": item.currency,
            "required_event_id": None,
            "event_id": None,
            "required_ticket_type_id": None,
            "ticket_type_ids": None,
            "require_check_in": False,
            "required_legacy_tier": None,
            "access_code": None,
            "access_code_set": False,
            "max_unlocks": None,
            "starts_at": None,
            "ends_at": None,
        }

    access_type = rule.access_type
    price = rule.price if rule.price is not None else item.price
    show_ticket_scope = owner_view or access_type in {
        "ticket_holder_only",
        "checked_in_attendee_only",
        "vip_ticket_holder_only",
    }
    # Never return invite access codes to clients — hashed at rest, omitted from API
    return {
        "access_type": access_type,
        "price": price if (owner_view or access_type == "one_time_unlock") else Decimal("0"),
        "currency": rule.currency or item.currency,
        "required_event_id": rule.event_id if show_ticket_scope or owner_view else None,
        "event_id": rule.event_id if show_ticket_scope or owner_view else None,
        "required_ticket_type_id": (
            rule.required_ticket_type_id if show_ticket_scope else None
        ),
        "ticket_type_ids": rule.ticket_type_ids if owner_view else None,
        "require_check_in": rule.require_check_in if show_ticket_scope else False,
        "required_legacy_tier": rule.required_legacy_tier if owner_view else None,
        "access_code": None,
        "access_code_set": (
            access_code_is_set(rule) if access_type == "invite_only" else False
        ),
        "max_unlocks": rule.max_unlocks if owner_view else None,
        "starts_at": rule.starts_at,
        "ends_at": rule.ends_at,
    }


def serialize_item(
    db: Session,
    item: VaultItem,
    *,
    user: User | None,
    include_locked: bool = False,
) -> dict:
    """Access-aware serialization. Locked secrets are never returned without entitlement.

    When locked, responses omit: body, file_url, external_url, private media URLs,
    and access codes. Invite-only locked responses are limited to preview fields.
    """
    host = db.get(Host, item.host_id)
    has_access, reason = evaluate_access(db, item=item, user=user)
    owner_view = include_locked
    if owner_view:
        has_access = True
        reason = reason or "owner_view"

    locked = not has_access
    invite_locked = locked and bool(
        item.access_rule and item.access_rule.access_type == "invite_only"
    )

    media_out = []
    for m in item.media or []:
        if has_access:
            media_out.append(
                {
                    "id": m.id,
                    "media_type": m.media_type,
                    "url": m.url,
                    "label": m.label,
                    "is_preview": m.is_preview,
                    "sort_order": m.sort_order,
                    "locked": False,
                }
            )
        elif m.is_preview and m.url and not invite_locked:
            # Public preview media only — never enumerate private media placeholders
            media_out.append(
                {
                    "id": m.id,
                    "media_type": m.media_type,
                    "url": m.url,
                    "label": m.label,
                    "is_preview": True,
                    "sort_order": m.sort_order,
                    "locked": False,
                }
            )
        # Private / non-preview media omitted entirely when locked

    access = _serialize_access_public(
        rule=item.access_rule,
        item=item,
        has_access=has_access,
        owner_view=owner_view,
    )

    ensure_vault_item_lifecycle(item)
    status = normalize_item_status(item.status)
    expired = item_is_expired(item) or status == "expired"
    tags = [str(t) for t in (item.tags or []) if t] if (has_access or not invite_locked) else []
    related_event_id = resolve_required_event_id(item.access_rule, item) or item.related_event_id
    related_event = _public_related_event(db, related_event_id)
    related_memory = _public_related_memory(db, item.related_memory_id)

    # Invite-only locked: preview surface only
    description = None if invite_locked else item.description
    preview_text = item.preview_text

    return {
        "id": item.id,
        "host_id": item.host_id,
        "host_username": host.slug if host else None,
        "host_display_name": host.display_name if host else None,
        "title": item.title,
        "slug": item.slug,
        "content_type": item.content_type if (has_access or not invite_locked) else "exclusive",
        "status": status if owner_view else ("published" if status == "published" else status),
        "description": description,
        "preview_text": preview_text,
        "body": item.body if has_access else None,
        "cover_url": item.cover_url,
        "file_url": item.file_url if has_access else None,
        "external_url": item.external_url if has_access else None,
        "related_event_id": related_event_id if (has_access or not invite_locked) else None,
        "related_memory_id": (
            item.related_memory_id if (has_access or not invite_locked) else None
        ),
        "related_event": related_event,
        "related_memory": related_memory,
        "tags": tags,
        "price": (
            (item.access_rule.price if item.access_rule and item.access_rule.price is not None else item.price)
            if (has_access or (item.access_rule and item.access_rule.access_type == "one_time_unlock"))
            else Decimal("0")
        ),
        "currency": (
            (item.access_rule.currency if item.access_rule else None) or item.currency
        ),
        "moderation_status": item.moderation_status if owner_view else "none",
        "moderation_note": item.moderation_note if owner_view else None,
        "moderated_at": item.moderated_at if owner_view else None,
        "published_at": item.published_at,
        "expires_at": item.expires_at if (owner_view or not invite_locked) else None,
        "archived_at": item.archived_at if owner_view else None,
        "created_at": item.created_at if owner_view else item.published_at or item.created_at,
        "access": access,
        "media": media_out,
        "has_access": has_access,
        # Always return the evaluate_access reason so buyers can see
        # purchased / follower / ticket-holder / VIP / checked-in grants.
        "access_reason": reason,
        "lock_reason": None if has_access else lock_reason_label(reason),
        "locked": locked,
        "expired": expired,
        "share_path": f"/@{host.slug}/vault/{item.slug}" if host else None,
        "cta_label": _public_cta_label(
            access_type=item.access_rule.access_type if item.access_rule else "free",
            locked=locked,
            expired=expired,
        ),
    }


def _public_cta_label(*, access_type: str, locked: bool, expired: bool) -> str:
    if not locked:
        return "Open"
    if expired:
        return "Expired"
    if access_type == "one_time_unlock":
        return "Unlock"
    if access_type == "invite_only":
        return "Enter code"
    if access_type == "followers_only":
        return "Follow to unlock"
    if access_type in {
        "ticket_holder_only",
        "checked_in_attendee_only",
        "vip_ticket_holder_only",
    }:
        return "Unlock with ticket"
    return "View"


def serialize_catalog_card(
    db: Session,
    item: VaultItem,
    *,
    user: User | None,
    featured: bool = False,
) -> dict:
    """Slim public catalog row — never includes locked content fields."""
    full = serialize_item(db, item, user=user, include_locked=False)
    access_type = (full.get("access") or {}).get("access_type") or "free"
    price = full["price"] if access_type == "one_time_unlock" else None
    content_type = full.get("content_type") or item.content_type or "text_post"
    if content_type == "exclusive":
        content_type = item.content_type or "text_post"
    return {
        "id": full["id"],
        "host_username": full["host_username"],
        "title": full["title"],
        "slug": full["slug"],
        "preview_text": full["preview_text"],
        "cover_url": full["cover_url"],
        "content_type": content_type,
        "access_type": access_type,
        "locked": full["locked"],
        "has_access": full["has_access"],
        "price": price,
        "currency": full["currency"] if price is not None else None,
        "related_event": full.get("related_event"),
        "related_memory": full.get("related_memory"),
        "share_path": full.get("share_path"),
        "cta_label": full.get("cta_label") or "View",
        "expired": full["expired"],
        "featured": featured,
    }


def _serialize_related_vault_cards(
    db: Session,
    *,
    rows: list[VaultItem],
    user: User | None,
    limit: int,
) -> list[dict]:
    cards: list[dict] = []
    dirty = False
    seen: set[UUID] = set()
    for row in rows:
        if row.id in seen:
            continue
        seen.add(row.id)
        if ensure_vault_item_lifecycle(row):
            dirty = True
        if is_publicly_listable(row) and not is_admin_hidden(row):
            cards.append(serialize_catalog_card(db, row, user=user, featured=False))
        if len(cards) >= limit:
            break
    if dirty:
        db.commit()
    return cards


def list_public_vault_for_event(
    db: Session,
    *,
    event_id: UUID,
    user: User | None,
    limit: int = 6,
) -> list[dict]:
    """Published Vault teasers tied to an event (related_event_id or access rule)."""
    event = db.get(Event, event_id)
    if event is None or event.status != "published":
        raise HTTPException(status_code=404, detail="Event not found")

    rows = db.scalars(
        select(VaultItem)
        .outerjoin(VaultAccessRule, VaultAccessRule.vault_item_id == VaultItem.id)
        .where(
            VaultItem.host_id == event.host_id,
            or_(
                VaultItem.related_event_id == event_id,
                VaultAccessRule.event_id == event_id,
            ),
        )
        .options(selectinload(VaultItem.media), selectinload(VaultItem.access_rule))
        .order_by(VaultItem.created_at.desc())
        .limit(max(limit * 3, 12))
    ).all()
    return _serialize_related_vault_cards(db, rows=list(rows), user=user, limit=limit)


def list_public_vault_for_memory(
    db: Session,
    *,
    memory_id: UUID,
    user: User | None,
    limit: int = 6,
) -> list[dict]:
    """Published Vault teasers tied to a memory or its event."""
    memory = db.get(EventMemory, memory_id)
    if (
        memory is None
        or memory.status != "published"
        or memory.moderation_status == "removed"
    ):
        raise HTTPException(status_code=404, detail="Event memory not found")

    rows = db.scalars(
        select(VaultItem)
        .outerjoin(VaultAccessRule, VaultAccessRule.vault_item_id == VaultItem.id)
        .where(
            VaultItem.host_id == memory.host_id,
            or_(
                VaultItem.related_memory_id == memory_id,
                VaultItem.related_event_id == memory.event_id,
                VaultAccessRule.event_id == memory.event_id,
            ),
        )
        .options(selectinload(VaultItem.media), selectinload(VaultItem.access_rule))
        .order_by(VaultItem.created_at.desc())
        .limit(max(limit * 3, 12))
    ).all()
    return _serialize_related_vault_cards(db, rows=list(rows), user=user, limit=limit)


def create_vault_item(db: Session, *, user: User, payload: VaultItemCreate) -> dict:
    host = require_user_host(db, user)
    _validate_related_links(
        db,
        host_id=host.id,
        related_event_id=payload.related_event_id,
        related_memory_id=payload.related_memory_id,
    )
    slug = _unique_slug(db, host.id, payload.slug or payload.title)
    now = datetime.now(UTC)
    status = normalize_item_status(payload.status)
    item = VaultItem(
        host_id=host.id,
        title=payload.title.strip(),
        slug=slug,
        content_type=payload.content_type,
        status=status,
        description=payload.description,
        preview_text=payload.preview_text,
        body=payload.body,
        cover_url=payload.cover_url,
        file_url=payload.file_url,
        external_url=payload.external_url,
        related_event_id=payload.related_event_id,
        related_memory_id=payload.related_memory_id,
        tags=payload.tags,
        price=Decimal(payload.price or 0),
        currency=payload.currency or "NGN",
        published_at=now if status == "published" else None,
        expires_at=payload.expires_at,
    )
    db.add(item)
    db.flush()
    _set_access_rule(db, item, payload.access)
    if status == "scheduled":
        apply_schedule(item, starts_at=payload.access.starts_at)
    _attach_media(db, item, payload.media)
    write_audit_log(
        db,
        action="vault.item_create",
        actor_user_id=user.id,
        resource_type="vault_item",
        resource_id=str(item.id),
        details={
            "slug": slug,
            "access_type": payload.access.access_type,
            "status": item.status,
        },
    )
    db.commit()
    item = _load_item(db, item.id)
    assert item is not None
    return serialize_item(db, item, user=user, include_locked=True)


def update_vault_item(
    db: Session, *, user: User, item_id: UUID, payload: VaultItemUpdate
) -> dict:
    host, item = _require_host_item(db, user, item_id)
    ensure_vault_item_lifecycle(item)
    assert_host_can_edit(item)
    data = payload.model_dump(exclude_unset=True)
    related_event_id = (
        data["related_event_id"]
        if "related_event_id" in data
        else item.related_event_id
    )
    related_memory_id = (
        data["related_memory_id"]
        if "related_memory_id" in data
        else item.related_memory_id
    )
    if "related_event_id" in data or "related_memory_id" in data:
        _validate_related_links(
            db,
            host_id=host.id,
            related_event_id=related_event_id,
            related_memory_id=related_memory_id,
        )
    if "title" in data and data["title"] is not None:
        item.title = data["title"].strip()
    if "slug" in data and data["slug"]:
        new_slug = _slugify(str(data["slug"]))[:200]
        if new_slug != item.slug:
            taken = db.scalar(
                select(VaultItem.id).where(
                    VaultItem.host_id == host.id,
                    VaultItem.slug == new_slug,
                    VaultItem.id != item.id,
                )
            )
            if taken:
                raise HTTPException(status_code=409, detail="Vault slug already in use")
            item.slug = new_slug
    if "content_type" in data and data["content_type"] is not None:
        item.content_type = data["content_type"]
    if "description" in data:
        item.description = data["description"]
    if "preview_text" in data:
        item.preview_text = data["preview_text"]
    if "body" in data:
        item.body = data["body"]
    if "cover_url" in data:
        item.cover_url = data["cover_url"]
    if "file_url" in data:
        item.file_url = data["file_url"]
    if "external_url" in data:
        item.external_url = data["external_url"]
    if "related_event_id" in data:
        item.related_event_id = data["related_event_id"]
    if "related_memory_id" in data:
        item.related_memory_id = data["related_memory_id"]
    if "tags" in data:
        item.tags = data["tags"]
    if "expires_at" in data:
        item.expires_at = data["expires_at"]
    if "price" in data and data["price"] is not None:
        item.price = Decimal(data["price"])
    if "status" in data and data["status"] is not None:
        next_status = normalize_item_status(data["status"])
        if next_status == "published":
            apply_publish(item)
        elif next_status == "draft":
            if normalize_item_status(item.status) in {"published", "scheduled"}:
                apply_unpublish(item)
            else:
                item.status = "draft"
        elif next_status == "scheduled":
            starts = None
            if payload.access is not None:
                starts = payload.access.starts_at
            elif item.access_rule is not None:
                starts = item.access_rule.starts_at
            apply_schedule(item, starts_at=starts)
        elif next_status == "archived":
            apply_archive(item, user_id=user.id)
    if payload.access is not None:
        _set_access_rule(db, item, payload.access)
    if payload.media is not None:
        for m in list(item.media):
            db.delete(m)
        db.flush()
        _attach_media(db, item, payload.media)

    write_audit_log(
        db,
        action="vault.item_update",
        actor_user_id=user.id,
        resource_type="vault_item",
        resource_id=str(item.id),
        details={"status": item.status},
    )
    db.commit()
    item = _load_item(db, item.id)
    assert item is not None
    return serialize_item(db, item, user=user, include_locked=True)


def _item_has_unlock_history(db: Session, item_id: UUID) -> bool:
    """Any paid unlock / grant counts as purchase history — blocks hard delete."""
    paid = db.scalar(
        select(func.count())
        .select_from(VaultPurchase)
        .where(
            VaultPurchase.vault_item_id == item_id,
            VaultPurchase.status == "paid",
        )
    )
    return int(paid or 0) > 0


def _serialize_host_item(db: Session, user: User, item_id: UUID) -> dict:
    item = _load_item(db, item_id)
    assert item is not None
    if ensure_vault_item_lifecycle(item):
        db.commit()
        item = _load_item(db, item_id)
        assert item is not None
    return serialize_item(db, item, user=user, include_locked=True)


def publish_vault_item(db: Session, *, user: User, item_id: UUID) -> dict:
    _, item = _require_host_item(db, user, item_id)
    ensure_vault_item_lifecycle(item)
    assert_host_can_edit(item)
    apply_publish(item)
    if item.access_rule and item.access_rule.access_type == "invite_only":
        if not (item.access_rule.access_code or "").strip():
            raise HTTPException(
                status_code=400,
                detail="invite_only published items require an access_code",
            )
    write_audit_log(
        db,
        action="vault.item_publish",
        actor_user_id=user.id,
        resource_type="vault_item",
        resource_id=str(item.id),
    )
    try:
        from app.admin_notifications.orchestrator import dispatch_typed
        from app.hosts.models import Host

        host = db.get(Host, item.host_id)
        host_label = (
            (getattr(host, "display_name", None) or getattr(host, "name", None) or "a host")
            if host
            else "a host"
        )
        slug = getattr(host, "slug", None) if host else None
        dispatch_typed(
            db,
            type_key="vault.item_published",
            context={
                "host_id": str(item.host_id),
                "context_id": str(item.id),
                "item_title": item.title,
                "host_name": host_label,
            },
            title=f"New Vault drop from {host_label}",
            body=(item.title or "A new Vault item is live on Pàdéyá.")[:240],
            link_path=f"/@{slug}/vault" if slug else "/dashboard/vault",
            dedupe_key=f"vault.item_published:{item.id}",
        )
    except Exception:  # noqa: BLE001
        # Never block publish on notification fan-out.
        pass
    db.commit()
    return _serialize_host_item(db, user, item_id)


def unpublish_vault_item(db: Session, *, user: User, item_id: UUID) -> dict:
    _, item = _require_host_item(db, user, item_id)
    ensure_vault_item_lifecycle(item)
    assert_host_can_edit(item)
    apply_unpublish(item)
    write_audit_log(
        db,
        action="vault.item_unpublish",
        actor_user_id=user.id,
        resource_type="vault_item",
        resource_id=str(item.id),
    )
    db.commit()
    return _serialize_host_item(db, user, item_id)


def schedule_vault_item(
    db: Session,
    *,
    user: User,
    item_id: UUID,
    payload: VaultScheduleRequest | None = None,
) -> dict:
    _, item = _require_host_item(db, user, item_id)
    ensure_vault_item_lifecycle(item)
    assert_host_can_edit(item)
    starts_at = None
    if payload is not None and payload.starts_at is not None:
        starts_at = payload.starts_at
    elif item.access_rule is not None:
        starts_at = item.access_rule.starts_at
    apply_schedule(item, starts_at=starts_at)
    write_audit_log(
        db,
        action="vault.item_schedule",
        actor_user_id=user.id,
        resource_type="vault_item",
        resource_id=str(item.id),
        details={"starts_at": starts_at.isoformat() if starts_at else None},
    )
    db.commit()
    return _serialize_host_item(db, user, item_id)


def archive_vault_item(db: Session, *, user: User, item_id: UUID) -> dict:
    _, item = _require_host_item(db, user, item_id)
    ensure_vault_item_lifecycle(item)
    apply_archive(item, user_id=user.id)
    write_audit_log(
        db,
        action="vault.item_archive",
        actor_user_id=user.id,
        resource_type="vault_item",
        resource_id=str(item.id),
    )
    db.commit()
    return _serialize_host_item(db, user, item_id)


def restore_vault_item(db: Session, *, user: User, item_id: UUID) -> dict:
    _, item = _require_host_item(db, user, item_id)
    ensure_vault_item_lifecycle(item)
    apply_host_restore(item)
    write_audit_log(
        db,
        action="vault.item_restore",
        actor_user_id=user.id,
        resource_type="vault_item",
        resource_id=str(item.id),
    )
    db.commit()
    return _serialize_host_item(db, user, item_id)


def delete_vault_item(db: Session, *, user: User, item_id: UUID) -> None:
    """Hard-delete draft items only when there is no unlock/purchase history."""
    if not (
        user_has_permission(user, "vault.delete_draft_own")
        or user_has_permission(user, "vault.create")
        or user_has_permission(user, "admin.full_access")
    ):
        raise HTTPException(status_code=403, detail="Insufficient permission")
    _, item = _require_host_item(db, user, item_id)
    ensure_vault_item_lifecycle(item)
    status = normalize_item_status(item.status)
    if status != "draft":
        raise HTTPException(
            status_code=400,
            detail="Only draft Vault items can be hard-deleted — archive or unpublish instead",
        )
    if _item_has_unlock_history(db, item.id):
        raise HTTPException(
            status_code=400,
            detail="Unlocked or purchased Vault items cannot be deleted — archive instead",
        )
    write_audit_log(
        db,
        action="vault.item_delete",
        actor_user_id=user.id,
        resource_type="vault_item",
        resource_id=str(item.id),
        details={"title": item.title, "slug": item.slug, "status": status},
    )
    db.delete(item)
    db.commit()


def list_host_vault_items(db: Session, user: User) -> list[dict]:
    host = require_user_host(db, user)
    rows = db.scalars(
        select(VaultItem)
        .where(VaultItem.host_id == host.id)
        .options(selectinload(VaultItem.media), selectinload(VaultItem.access_rule))
        .order_by(VaultItem.created_at.desc())
    ).all()
    return [serialize_item(db, r, user=user, include_locked=True) for r in rows]


def get_host_vault_item(db: Session, user: User, item_id: UUID) -> dict:
    _, item = _require_host_item(db, user, item_id)
    return serialize_item(db, item, user=user, include_locked=True)


def preview_vault_item_as_fan(db: Session, user: User, item_id: UUID) -> dict:
    """Serialize an item as an anonymous fan would see it (locked content protected)."""
    _, item = _require_host_item(db, user, item_id)
    return serialize_item(db, item, user=None, include_locked=False)


_TICKET_ACCESS_TYPES = frozenset(
    {
        "ticket_holder_only",
        "checked_in_attendee_only",
        "vip_ticket_holder_only",
    }
)


def _item_performance_maps(
    db: Session, *, host_id: UUID
) -> tuple[dict[UUID, int], dict[UUID, int], dict[UUID, Decimal]]:
    view_rows = db.execute(
        select(VaultView.vault_item_id, func.count())
        .join(VaultItem, VaultItem.id == VaultView.vault_item_id)
        .where(VaultItem.host_id == host_id)
        .group_by(VaultView.vault_item_id)
    ).all()
    unlock_rows = db.execute(
        select(VaultPurchase.vault_item_id, func.count(), func.coalesce(func.sum(VaultPurchase.amount), 0))
        .where(
            VaultPurchase.host_id == host_id,
            VaultPurchase.status == "paid",
        )
        .group_by(VaultPurchase.vault_item_id)
    ).all()
    views = {row[0]: int(row[1]) for row in view_rows}
    unlocks = {row[0]: int(row[1]) for row in unlock_rows}
    earnings = {row[0]: Decimal(row[2] or 0) for row in unlock_rows}
    return views, unlocks, earnings


def serialize_studio_item(
    db: Session,
    item: VaultItem,
    *,
    user: User,
    views: dict[UUID, int],
    unlocks: dict[UUID, int],
    earnings: dict[UUID, Decimal],
) -> dict:
    base = serialize_item(db, item, user=user, include_locked=True)
    access_type = (
        item.access_rule.access_type if item.access_rule else "free"
    )
    is_paid = access_type == "one_time_unlock"
    is_ticket = access_type in _TICKET_ACCESS_TYPES
    is_free = access_type == "free"
    is_gated = not is_free and access_type != "admin_hidden"
    return {
        **base,
        "view_count": views.get(item.id, 0),
        "unlock_count": unlocks.get(item.id, 0),
        "earnings": earnings.get(item.id, Decimal("0")),
        "is_access_gated": is_gated,
        "is_paid": is_paid,
        "is_ticket_gated": is_ticket,
        "is_expired": item_is_expired(item)
        or normalize_item_status(item.status) == "expired",
        "is_archived": normalize_item_status(item.status) == "archived",
        "is_scheduled": normalize_item_status(item.status) == "scheduled",
        "is_hidden_by_admin": normalize_item_status(item.status) == "hidden_by_admin",
    }


def list_host_studio_items(db: Session, user: User) -> list[dict]:
    host = require_user_host(db, user)
    rows = db.scalars(
        select(VaultItem)
        .where(VaultItem.host_id == host.id)
        .options(selectinload(VaultItem.media), selectinload(VaultItem.access_rule))
        .order_by(VaultItem.created_at.desc())
    ).all()
    views, unlocks, earnings = _item_performance_maps(db, host_id=host.id)
    return [
        serialize_studio_item(
            db, row, user=user, views=views, unlocks=unlocks, earnings=earnings
        )
        for row in rows
    ]


def get_vault_studio_summary(db: Session, user: User) -> dict:
    """Host Vault Content Studio overview: items, stats, earnings, Legacy feature."""
    from app.legacy.models import HostLegacyContentBlock, HostLegacyFeaturedItem
    from app.legacy.studio import ensure_default_blocks, ensure_legacy_page

    host = require_user_host(db, user)
    ensure_legacy_page(db, host.id)
    ensure_default_blocks(db, host.id)
    db.commit()

    featured = db.scalar(
        select(HostLegacyFeaturedItem).where(
            HostLegacyFeaturedItem.host_id == host.id,
            HostLegacyFeaturedItem.placement == "featured_vault_item",
        )
    )
    vault_block = db.scalar(
        select(HostLegacyContentBlock).where(
            HostLegacyContentBlock.host_id == host.id,
            HostLegacyContentBlock.block_type == "vault_preview",
        )
    )
    items = list_host_studio_items(db, user)
    earnings = host_earnings(db, user)

    published = [i for i in items if i["status"] == "published"]
    locked = [i for i in items if i["is_access_gated"]]
    free = [
        i
        for i in items
        if (i.get("access") or {}).get("access_type") == "free"
    ]
    paid_items = [i for i in items if i["is_paid"]]
    ticket_items = [i for i in items if i["is_ticket_gated"]]
    expired = [i for i in items if i["is_expired"]]
    archived = [i for i in items if i["is_archived"]]
    drafts = [i for i in items if i["status"] == "draft"]

    top = None
    if items:
        ranked = sorted(
            items,
            key=lambda i: (
                Decimal(i.get("earnings") or 0),
                int(i.get("unlock_count") or 0),
                int(i.get("view_count") or 0),
            ),
            reverse=True,
        )
        best = ranked[0]
        if (
            Decimal(best.get("earnings") or 0) > 0
            or int(best.get("unlock_count") or 0) > 0
            or int(best.get("view_count") or 0) > 0
        ):
            top = {
                "id": best["id"],
                "title": best["title"],
                "slug": best["slug"],
                "cover_url": best.get("cover_url"),
                "view_count": int(best.get("view_count") or 0),
                "unlock_count": int(best.get("unlock_count") or 0),
                "earnings": Decimal(best.get("earnings") or 0),
                "access_type": (best.get("access") or {}).get("access_type"),
            }

    return {
        "host_id": host.id,
        "host_username": host.slug,
        "share_path": f"/@{host.slug}/vault",
        "earnings": earnings,
        "stats": {
            "total_items": len(items),
            "published_items": len(published),
            "locked_items": len(locked),
            "free_items": len(free),
            "paid_unlocks": int(earnings["paid_purchase_count"]),
            "view_count": int(earnings["view_count"]),
            "gross_revenue": earnings["gross_revenue"],
            "draft_items": len(drafts),
            "archived_items": len(archived),
            "expired_items": len(expired),
            "paid_items": len(paid_items),
            "ticket_holder_items": len(ticket_items),
        },
        "items": items,
        "top_item": top,
        "featured_vault_item_id": featured.item_id if featured else None,
        "legacy_vault_block_visible": bool(vault_block.is_visible) if vault_block else True,
    }


def list_public_vault(
    db: Session, *, username: str, user: User | None
) -> list[dict]:
    from app.legacy.models import HostLegacyFeaturedItem

    host = db.scalar(select(Host).where(Host.slug == username.lower()))
    if host is None or host.status != "active":
        raise HTTPException(status_code=404, detail="Host not found")
    featured = db.scalar(
        select(HostLegacyFeaturedItem).where(
            HostLegacyFeaturedItem.host_id == host.id,
            HostLegacyFeaturedItem.placement == "featured_vault_item",
        )
    )
    featured_id = featured.item_id if featured else None
    rows = db.scalars(
        select(VaultItem)
        .where(
            VaultItem.host_id == host.id,
            VaultItem.status.in_(["published", "scheduled", "expired", "disabled"]),
            VaultItem.moderation_status.in_(["none", "approved", "flagged"]),
        )
        .options(selectinload(VaultItem.media), selectinload(VaultItem.access_rule))
        .order_by(VaultItem.created_at.desc())
    ).all()
    cards = []
    dirty = False
    for row in rows:
        if ensure_vault_item_lifecycle(row):
            dirty = True
        if is_publicly_listable(row) and not is_admin_hidden(row):
            cards.append(
                serialize_catalog_card(
                    db,
                    row,
                    user=user,
                    featured=featured_id is not None and row.id == featured_id,
                )
            )
    if dirty:
        db.commit()
    cards.sort(key=lambda c: (not c.get("featured"),), reverse=False)
    return cards


def get_public_vault_item(
    db: Session, *, username: str, item_slug: str, user: User | None
) -> dict:
    host = db.scalar(select(Host).where(Host.slug == username.lower()))
    if host is None:
        raise HTTPException(status_code=404, detail="Host not found")
    item = db.scalar(
        select(VaultItem)
        .where(VaultItem.host_id == host.id, VaultItem.slug == item_slug)
        .options(selectinload(VaultItem.media), selectinload(VaultItem.access_rule))
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Vault item not found")
    if ensure_vault_item_lifecycle(item):
        db.commit()
        item = _load_item(db, item.id)
        assert item is not None
    status = normalize_item_status(item.status)
    if item.moderation_status == "removed" or status in {
        "archived",
        "hidden_by_admin",
        "draft",
        "scheduled",
        "expired",
    }:
        # Non-live statuses stay private; hosts use studio preview routes
        raise HTTPException(status_code=404, detail="Vault item not found")
    if is_admin_hidden(item):
        from app.hosts.models import Host as HostModel

        host_row = db.get(HostModel, item.host_id)
        is_owner = (
            user is not None and host_row is not None and host_row.user_id == user.id
        )
        if not is_owner and not (
            user is not None and user_has_permission(user, "vault.moderate")
        ):
            raise HTTPException(status_code=404, detail="Vault item not found")
    if status != "published":
        if user is None or not evaluate_access(db, item=item, user=user)[0]:
            raise HTTPException(status_code=404, detail="Vault item not found")

    has_access, _ = evaluate_access(db, item=item, user=user)
    db.add(
        VaultView(
            vault_item_id=item.id,
            user_id=user.id if user else None,
            had_access=has_access,
        )
    )
    db.commit()
    return serialize_item(db, item, user=user)


def _serialize_purchase(db: Session, purchase: VaultPurchase) -> dict:
    item = db.get(VaultItem, purchase.vault_item_id)
    return {
        "id": purchase.id,
        "vault_item_id": purchase.vault_item_id,
        "host_id": purchase.host_id,
        "amount": purchase.amount,
        "currency": purchase.currency,
        "status": purchase.status,
        "payment_reference": purchase.payment_reference,
        "authorization_url": purchase.authorization_url,
        "access_code": purchase.access_code,
        "paid_at": purchase.paid_at,
        "created_at": purchase.created_at,
        "item_title": item.title if item else None,
        "item_slug": item.slug if item else None,
        "free_checkout": purchase.amount == 0,
    }


def _record_unlock_attempt(
    db: Session,
    *,
    item: VaultItem,
    user: User,
    status: str,
    purchase: VaultPurchase | None = None,
    detail: str | None = None,
) -> None:
    db.add(
        VaultUnlockAttempt(
            vault_item_id=item.id,
            host_id=item.host_id,
            user_id=user.id,
            status=status,
            vault_purchase_id=purchase.id if purchase else None,
            payment_reference=purchase.payment_reference if purchase else None,
            detail=detail,
        )
    )


def _ensure_vault_access_grant(
    db: Session,
    *,
    purchase: VaultPurchase,
    source: str,
) -> tuple[VaultAccessGrant, bool]:
    """Create or return the unique (item, user) grant. Returns (grant, created)."""
    existing = db.scalar(
        select(VaultAccessGrant)
        .where(
            VaultAccessGrant.vault_item_id == purchase.vault_item_id,
            VaultAccessGrant.user_id == purchase.user_id,
        )
        .with_for_update()
    )
    if existing is not None:
        return existing, False

    grant = VaultAccessGrant(
        vault_item_id=purchase.vault_item_id,
        host_id=purchase.host_id,
        user_id=purchase.user_id,
        source=source,
        vault_purchase_id=purchase.id,
        granted_at=datetime.now(UTC),
    )
    db.add(grant)
    try:
        with db.begin_nested():
            db.flush()
        return grant, True
    except IntegrityError:
        existing = db.scalar(
            select(VaultAccessGrant).where(
                VaultAccessGrant.vault_item_id == purchase.vault_item_id,
                VaultAccessGrant.user_id == purchase.user_id,
            )
        )
        if existing is None:
            raise
        return existing, False


def _ensure_vault_sale_ledger(
    db: Session,
    *,
    purchase: VaultPurchase,
    actor_user_id: UUID | None,
) -> bool:
    """Credit host once per paid purchase id. Returns True when a new entry was written."""
    # Prefer host net from checkout fee metadata when present.
    credit_amount = Decimal(purchase.amount)
    raw = purchase.raw_response if isinstance(purchase.raw_response, dict) else {}
    fee_meta = raw.get("checkout_fees") if isinstance(raw, dict) else None
    if isinstance(fee_meta, dict) and fee_meta.get("host_net_estimate") is not None:
        credit_amount = Decimal(str(fee_meta["host_net_estimate"]))
    if credit_amount <= 0:
        return False
    from app.finance.models import LedgerEntry

    existing_credit = db.scalar(
        select(LedgerEntry).where(
            LedgerEntry.host_id == purchase.host_id,
            LedgerEntry.entry_type == "vault_sale",
            LedgerEntry.reference_type == "vault_purchase",
            LedgerEntry.reference_id == str(purchase.id),
        )
    )
    if existing_credit is not None:
        from app.finance.platform_ledger import record_platform_entries_for_vault_purchase

        fee_meta = fee_meta if isinstance(fee_meta, dict) else {}
        record_platform_entries_for_vault_purchase(
            db,
            purchase_id=purchase.id,
            host_id=purchase.host_id,
            user_id=purchase.user_id,
            amount=Decimal(purchase.amount),
            currency=purchase.currency or "NGN",
            buyer_fee_total=Decimal(str(fee_meta.get("buyer_fee_total") or 0)),
            host_fee_total=Decimal(str(fee_meta.get("host_fee_total") or 0)),
            processing_fee_total=Decimal(
                str(fee_meta.get("processing_fee_total") or 0)
            ),
            payment_reference=purchase.payment_reference,
            actor_user_id=actor_user_id or purchase.user_id,
        )
        return False
    try:
        with db.begin_nested():
            append_ledger_entry(
                db,
                host_id=purchase.host_id,
                entry_type="vault_sale",
                direction="credit",
                amount=credit_amount,
                currency=purchase.currency,
                reference_type="vault_purchase",
                reference_id=str(purchase.id),
                description=f"Vault unlock {purchase.payment_reference}",
                created_by_user_id=actor_user_id or purchase.user_id,
                available_delta=credit_amount,
                lifetime_earned_delta=credit_amount,
            )
        from app.finance.platform_ledger import record_platform_entries_for_vault_purchase

        fee_meta = fee_meta if isinstance(fee_meta, dict) else {}
        record_platform_entries_for_vault_purchase(
            db,
            purchase_id=purchase.id,
            host_id=purchase.host_id,
            user_id=purchase.user_id,
            amount=Decimal(purchase.amount),
            currency=purchase.currency or "NGN",
            buyer_fee_total=Decimal(str(fee_meta.get("buyer_fee_total") or 0)),
            host_fee_total=Decimal(str(fee_meta.get("host_fee_total") or 0)),
            processing_fee_total=Decimal(
                str(fee_meta.get("processing_fee_total") or 0)
            ),
            payment_reference=purchase.payment_reference,
            actor_user_id=actor_user_id or purchase.user_id,
        )
        return True
    except IntegrityError:
        return False


def start_vault_unlock(
    db: Session, *, user: User, item_id: UUID
) -> dict:
    from app.users.restrictions import assert_can_use_vault

    assert_can_use_vault(db, user)
    from app.demo.guards import demo_mode_enabled

    item = _load_item(db, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Vault item not found")
    ensure_vault_item_lifecycle(item)
    if normalize_item_status(item.status) != "published":
        raise HTTPException(status_code=404, detail="Vault item not found")
    if item.moderation_status == "removed":
        raise HTTPException(status_code=404, detail="Vault item not found")
    if item_is_expired(item):
        raise HTTPException(status_code=400, detail="This Vault item has expired")
    if is_admin_hidden(item):
        raise HTTPException(status_code=404, detail="Vault item not found")
    rule = item.access_rule
    if rule is None or rule.access_type != "one_time_unlock":
        raise HTTPException(
            status_code=400, detail="This item is not available for one-time unlock"
        )
    window = access_window_state(rule)
    if window is not None:
        raise HTTPException(status_code=400, detail=f"Unlock unavailable ({window})")
    if unlock_cap_reached(db, item=item) and not user_has_paid_unlock(
        db, item_id=item.id, user_id=user.id
    ):
        _record_unlock_attempt(
            db, item=item, user=user, status="rejected", detail="max_unlocks"
        )
        db.commit()
        raise HTTPException(status_code=400, detail="Maximum unlocks reached")
    has_access, _reason = evaluate_access(db, item=item, user=user)
    if has_access or user_has_paid_unlock(db, item_id=item.id, user_id=user.id):
        _record_unlock_attempt(
            db, item=item, user=user, status="already_unlocked"
        )
        db.commit()
        raise HTTPException(status_code=400, detail="You already have access")

    amount = Decimal(rule.price if rule.price is not None else item.price)
    currency = rule.currency or item.currency or "NGN"

    from app.finance.fees.checkout_fees import calculate_vault_checkout_fees

    vault_fees = calculate_vault_checkout_fees(
        db,
        host_id=item.host_id,
        vault_subtotal=amount,
        currency=currency,
    )
    list_price = amount
    amount = vault_fees.final_total
    host_net = vault_fees.host_net_estimate
    fee_meta = {
        "list_price": str(list_price),
        "buyer_fee_total": str(vault_fees.buyer_fee_total),
        "host_fee_total": str(vault_fees.host_fee_total),
        "host_net_estimate": str(host_net),
        "processing_fee_total": str(vault_fees.processing_fee_total),
        "buyer_fee_lines": [
            {
                "fee_key": line.fee_key,
                "label": line.label,
                "amount_minor": line.amount_minor,
            }
            for line in vault_fees.buyer_lines
        ],
    }

    # Reuse an open pending checkout for this buyer+item (idempotent retries).
    pending = db.scalar(
        select(VaultPurchase)
        .where(
            VaultPurchase.vault_item_id == item.id,
            VaultPurchase.user_id == user.id,
            VaultPurchase.status == "pending",
        )
        .order_by(VaultPurchase.created_at.desc())
        .with_for_update()
    )
    if pending is not None and Decimal(pending.amount) != amount:
        pending.status = "abandoned"
        pending = None

    if pending is not None and pending.authorization_url and amount > 0:
        _record_unlock_attempt(
            db,
            item=item,
            user=user,
            status="reused_pending",
            purchase=pending,
        )
        db.commit()
        db.refresh(pending)
        return {
            "purchase": _serialize_purchase(db, pending),
            "public_key": paystack_runtime(db).public_key or None,
        }

    if pending is None:
        reference = f"PDY-VLT-{secrets.token_hex(8).upper()}"
        purchase = VaultPurchase(
            vault_item_id=item.id,
            host_id=item.host_id,
            user_id=user.id,
            amount=amount,
            currency=currency,
            status="pending",
            payment_reference=reference,
            provider="paystack" if amount > 0 else "internal",
            raw_response={"checkout_fees": fee_meta},
        )
        db.add(purchase)
        db.flush()
    else:
        purchase = pending
        reference = purchase.payment_reference
        purchase.amount = amount
        existing_raw = dict(purchase.raw_response or {})
        existing_raw["checkout_fees"] = fee_meta
        purchase.raw_response = existing_raw

    _record_unlock_attempt(
        db, item=item, user=user, status="started", purchase=purchase
    )

    if amount <= 0:
        finalize_vault_purchase(
            db,
            purchase=purchase,
            provider_payment_id="free",
            raw_payload={"type": "free_vault_unlock"},
            actor_user_id=user.id,
        )
        _record_unlock_attempt(
            db, item=item, user=user, status="finalized", purchase=purchase, detail="free"
        )
        db.commit()
        db.refresh(purchase)
        return {
            "purchase": _serialize_purchase(db, purchase),
            "public_key": None,
        }

    # Demo mode only (never production): mock paid unlock without Paystack / tickets.
    env = (settings.app_env or "").strip().lower()
    if demo_mode_enabled() and env not in {"production", "prod"}:
        purchase.provider = "demo"
        finalize_vault_purchase(
            db,
            purchase=purchase,
            provider_payment_id="demo",
            raw_payload={"type": "demo_vault_unlock", "demo_mode": True},
            actor_user_id=user.id,
        )
        _record_unlock_attempt(
            db, item=item, user=user, status="finalized", purchase=purchase, detail="demo"
        )
        db.commit()
        db.refresh(purchase)
        return {
            "purchase": _serialize_purchase(db, purchase),
            "public_key": None,
        }

    callback_url = (
        f"{settings.frontend_url.rstrip('/')}/dashboard/vault"
        f"?purchase={purchase.id}"
    )
    try:
        data = initialize_transaction(
            email=user.email,
            amount_kobo=int(amount * 100),
            reference=reference,
            callback_url=callback_url,
            metadata={
                "vault_purchase_id": str(purchase.id),
                "vault_item_id": str(item.id),
                "buyer_user_id": str(user.id),
                "type": "vault_unlock",
                # Explicit: Vault unlocks never issue event tickets
                "issues_tickets": False,
            },
            db=db,
        )
    except PaystackError as exc:
        purchase.status = "failed"
        _record_unlock_attempt(
            db,
            item=item,
            user=user,
            status="failed",
            purchase=purchase,
            detail=str(exc)[:240],
        )
        db.commit()
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    purchase.authorization_url = data.get("authorization_url")
    purchase.access_code = data.get("access_code")
    merged = dict(data) if isinstance(data, dict) else {"paystack": data}
    merged["checkout_fees"] = fee_meta
    purchase.raw_response = merged
    purchase.provider = "paystack"
    write_audit_log(
        db,
        action="vault.unlock_checkout",
        actor_user_id=user.id,
        resource_type="vault_purchase",
        resource_id=str(purchase.id),
        details={"reference": reference, "amount": str(amount)},
    )
    _record_unlock_attempt(
        db,
        item=item,
        user=user,
        status="redirected",
        purchase=purchase,
        detail="paystack",
    )
    db.commit()
    db.refresh(purchase)
    return {
        "purchase": _serialize_purchase(db, purchase),
        "public_key": paystack_runtime(db).public_key or None,
    }


def _create_access_grant(
    db: Session,
    *,
    item: VaultItem,
    user: User,
    provider: str,
    access_code: str | None = None,
    actor_user_id: UUID | None = None,
) -> dict:
    if user_has_paid_unlock(db, item_id=item.id, user_id=user.id):
        raise HTTPException(status_code=400, detail="You already have access")

    if unlock_cap_reached(db, item=item):
        raise HTTPException(status_code=400, detail="Maximum unlocks reached")

    reference = f"PDY-VLT-{secrets.token_hex(8).upper()}"
    purchase = VaultPurchase(
        vault_item_id=item.id,
        host_id=item.host_id,
        user_id=user.id,
        amount=Decimal("0"),
        currency=(item.access_rule.currency if item.access_rule else item.currency)
        or "NGN",
        status="pending",
        payment_reference=reference,
        provider=provider,
        access_code=access_code,
    )
    db.add(purchase)
    db.flush()
    finalize_vault_purchase(
        db,
        purchase=purchase,
        provider_payment_id=provider,
        raw_payload={"type": provider, "access_code_used": bool(access_code)},
        actor_user_id=actor_user_id or user.id,
        grant_source=provider,
    )
    db.commit()
    db.refresh(purchase)
    return {
        "purchase": _serialize_purchase(db, purchase),
        "item": serialize_item(db, item, user=user, include_locked=False),
    }


def redeem_vault_invite(
    db: Session, *, user: User, item_id: UUID, access_code: str
) -> dict:
    item = _load_item(db, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Vault item not found")
    ensure_vault_item_lifecycle(item)
    if normalize_item_status(item.status) != "published":
        raise HTTPException(status_code=404, detail="Vault item not found")
    if item.moderation_status == "removed" or is_admin_hidden(item):
        raise HTTPException(status_code=404, detail="Vault item not found")
    if item_is_expired(item):
        raise HTTPException(status_code=400, detail="This Vault item has expired")
    rule = item.access_rule
    if rule is None or rule.access_type != "invite_only":
        raise HTTPException(status_code=400, detail="This item is not invite-only")
    window = access_window_state(rule)
    if window is not None:
        raise HTTPException(status_code=400, detail=f"Unlock unavailable ({window})")
    if not access_code_matches(rule, access_code):
        raise HTTPException(status_code=403, detail="Invalid access code")
    return _create_access_grant(
        db,
        item=item,
        user=user,
        provider="invite_code",
        access_code=None,  # never persist redeemed plaintext codes
        actor_user_id=user.id,
    )


def grant_vault_access(
    db: Session, *, host_user: User, item_id: UUID, buyer_user_id: UUID
) -> dict:
    _, item = _require_host_item(db, host_user, item_id)
    buyer = db.get(User, buyer_user_id)
    if buyer is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user_has_paid_unlock(db, item_id=item.id, user_id=buyer.id):
        raise HTTPException(status_code=400, detail="User already has access")
    return _create_access_grant(
        db,
        item=item,
        user=buyer,
        provider="manual_grant",
        actor_user_id=host_user.id,
    )


def finalize_vault_purchase(
    db: Session,
    *,
    purchase: VaultPurchase,
    provider_payment_id: str | None,
    raw_payload: dict,
    actor_user_id: UUID | None = None,
    grant_source: str | None = None,
) -> VaultPurchase:
    """Mark purchase paid, upsert access grant, credit ledger once.

    Safe under duplicate webhooks: row lock + grant uniqueness + ledger repair.
    Never issues event tickets.
    """
    # Lock the row so concurrent webhooks cannot double-credit the host ledger.
    locked = db.scalar(
        select(VaultPurchase)
        .where(VaultPurchase.id == purchase.id)
        .with_for_update()
    )
    if locked is None:
        raise HTTPException(status_code=404, detail="Vault purchase not found")

    source = grant_source or (
        locked.provider
        if locked.provider in {"invite_code", "manual_grant", "demo", "internal"}
        else "purchase"
    )

    # Already paid: repair grant/ledger if a prior crash skipped them.
    if locked.status == "paid":
        _ensure_vault_access_grant(db, purchase=locked, source=source)
        _ensure_vault_sale_ledger(
            db, purchase=locked, actor_user_id=actor_user_id
        )
        return locked

    item = db.get(VaultItem, locked.vault_item_id)
    if item is not None and unlock_cap_reached(db, item=item):
        if not user_has_paid_unlock(
            db, item_id=locked.vault_item_id, user_id=locked.user_id
        ):
            raise HTTPException(status_code=400, detail="Maximum unlocks reached")

    now = datetime.now(UTC)
    locked.status = "paid"
    locked.paid_at = now
    locked.provider_payment_id = provider_payment_id
    locked.raw_response = raw_payload

    grant, grant_created = _ensure_vault_access_grant(
        db, purchase=locked, source=source
    )

    if grant_created:
        try:
            from app.merch.notifications import maybe_notify_buyer_vault_merch_unlocked

            maybe_notify_buyer_vault_merch_unlocked(
                db,
                user_id=locked.user_id,
                host_id=locked.host_id,
                vault_item_id=locked.vault_item_id,
            )
        except Exception:
            # Never block Vault unlock on optional merch notify.
            pass

    # Only the grant-owning purchase credits the host. Duplicate paid rows
    # (race) mark paid for audit but skip a second ledger credit.
    should_credit = locked.amount > 0 and (
        grant_created or grant.vault_purchase_id == locked.id
    )
    if should_credit:
        _ensure_vault_sale_ledger(
            db, purchase=locked, actor_user_id=actor_user_id
        )
    elif (
        locked.amount > 0
        and not grant_created
        and grant.vault_purchase_id is not None
        and grant.vault_purchase_id != locked.id
    ):
        write_audit_log(
            db,
            action="vault.unlock_duplicate_payment",
            actor_user_id=actor_user_id or locked.user_id,
            resource_type="vault_purchase",
            resource_id=str(locked.id),
            details={
                "reference": locked.payment_reference,
                "grant_id": str(grant.id),
                "primary_purchase_id": str(grant.vault_purchase_id),
            },
        )

    # Close any other pending checkouts for this buyer+item
    db.execute(
        update(VaultPurchase)
        .where(
            VaultPurchase.vault_item_id == locked.vault_item_id,
            VaultPurchase.user_id == locked.user_id,
            VaultPurchase.status == "pending",
            VaultPurchase.id != locked.id,
        )
        .values(status="superseded")
    )

    write_audit_log(
        db,
        action="vault.unlock_paid",
        actor_user_id=actor_user_id or locked.user_id,
        resource_type="vault_purchase",
        resource_id=str(locked.id),
        details={
            "reference": locked.payment_reference,
            "amount": str(locked.amount),
            "grant_id": str(grant.id),
            "grant_created": grant_created,
            "issues_tickets": False,
        },
    )

    from app.analytics.trusted import emit_vault_purchase, emit_vault_unlock_success

    item_for_meta = item or db.get(VaultItem, locked.vault_item_id)
    access_type = (
        item_for_meta.access_rule.access_type
        if item_for_meta and item_for_meta.access_rule
        else None
    )
    related_event_id = (
        resolve_required_event_id(
            item_for_meta.access_rule if item_for_meta else None,
            item_for_meta,
        )
        if item_for_meta
        else None
    ) or (item_for_meta.related_event_id if item_for_meta else None)

    emit_vault_purchase(
        db,
        vault_purchase_id=locked.id,
        host_id=locked.host_id,
        user_id=locked.user_id,
        amount=locked.amount,
        currency=locked.currency or "NGN",
        vault_item_id=locked.vault_item_id,
        access_type=access_type,
        related_event_id=related_event_id,
    )
    if grant_created or grant.vault_purchase_id == locked.id:
        emit_vault_unlock_success(
            db,
            host_id=locked.host_id,
            user_id=locked.user_id,
            vault_item_id=locked.vault_item_id,
            access_type=access_type,
            related_event_id=related_event_id,
            vault_purchase_id=locked.id,
            source=source,
        )
    return locked


def get_my_vault_purchase(
    db: Session, *, user: User, purchase_id: UUID
) -> dict:
    purchase = db.get(VaultPurchase, purchase_id)
    if purchase is None or purchase.user_id != user.id:
        raise HTTPException(status_code=404, detail="Vault purchase not found")
    return _serialize_purchase(db, purchase)


def get_vault_purchase_by_reference(
    db: Session, reference: str, *, for_update: bool = False
) -> VaultPurchase | None:
    q = select(VaultPurchase).where(VaultPurchase.payment_reference == reference)
    if for_update:
        q = q.with_for_update()
    return db.scalar(q)


def list_my_vault_purchases(db: Session, user: User) -> list[dict]:
    rows = db.scalars(
        select(VaultPurchase)
        .where(VaultPurchase.user_id == user.id)
        .order_by(VaultPurchase.created_at.desc())
    ).all()
    return [_serialize_purchase(db, r) for r in rows]


_ACCESS_LABELS = {
    "purchased": "Purchased",
    "follower": "Follower",
    "ticket_holder": "Ticket-holder",
    "vip_ticket_holder": "VIP",
    "checked_in_attendee": "Checked-in",
    "free": "Free",
    "host_owner": "Host",
}


def _access_label(reason: str | None) -> str:
    if not reason:
        return "Exclusive"
    return _ACCESS_LABELS.get(reason, reason.replace("_", " ").title())


def _buyer_relevant_host_ids(db: Session, user: User) -> set[UUID]:
    from app.crm.models import HostFollower
    from app.tickets.models import Ticket

    followed = set(
        db.scalars(
            select(HostFollower.host_id).where(HostFollower.user_id == user.id)
        ).all()
    )
    ticket_hosts = set(
        db.scalars(
            select(Event.host_id)
            .join(Ticket, Ticket.event_id == Event.id)
            .where(
                Ticket.buyer_user_id == user.id,
                Ticket.status.in_(["active", "checked_in"]),
            )
            .distinct()
        ).all()
    )
    purchase_hosts = set(
        db.scalars(
            select(VaultPurchase.host_id).where(
                VaultPurchase.user_id == user.id,
                VaultPurchase.status == "paid",
            )
        ).all()
    )
    return followed | ticket_hosts | purchase_hosts


def get_buyer_vault_library(db: Session, user: User) -> dict:
    """Fan content library: unlocked, followed, ticket-holder, unlockable, activity."""
    from app.crm.models import HostFollower
    from app.vault.lifecycle import is_publicly_listable
    from sqlalchemy import or_

    host_ids = _buyer_relevant_host_ids(db, user)
    paid_purchases = db.scalars(
        select(VaultPurchase)
        .where(
            VaultPurchase.user_id == user.id,
            VaultPurchase.status == "paid",
        )
        .order_by(VaultPurchase.created_at.desc())
    ).all()
    purchased_ids = {p.vault_item_id for p in paid_purchases}
    followed_ids = set(
        db.scalars(
            select(HostFollower.host_id).where(HostFollower.user_id == user.id)
        ).all()
    )

    item_query = select(VaultItem).options(
        selectinload(VaultItem.media),
        selectinload(VaultItem.access_rule),
    )
    rows: list[VaultItem] = []
    if host_ids or purchased_ids:
        clauses = []
        if host_ids:
            clauses.append(VaultItem.host_id.in_(host_ids))
        if purchased_ids:
            clauses.append(VaultItem.id.in_(purchased_ids))
        rows = list(
            db.scalars(
                item_query.where(
                    or_(*clauses),
                    VaultItem.status.in_(["published", "scheduled", "expired"]),
                )
                .order_by(
                    VaultItem.published_at.desc().nullslast(),
                    VaultItem.created_at.desc(),
                )
                .limit(120)
            )
        )

    unlocked: list[dict] = []
    followed_host_drops: list[dict] = []
    ticket_holder_content: list[dict] = []
    unlockable: list[dict] = []
    seen_unlocked: set[UUID] = set()

    for row in rows:
        ensure_vault_item_lifecycle(row)
        if is_admin_hidden(row):
            continue
        if not is_publicly_listable(row) and row.id not in purchased_ids:
            continue

        serialized = serialize_item(db, row, user=user, include_locked=False)
        reason = serialized.get("access_reason")
        if serialized["has_access"]:
            if row.id in seen_unlocked:
                continue
            seen_unlocked.add(row.id)
            entry = {
                **serialized,
                "access_label": _access_label(reason),
                "library_group": "unlocked",
            }
            unlocked.append(entry)
            if reason == "follower" or (
                reason == "free" and row.host_id in followed_ids
            ):
                followed_host_drops.append({**entry, "library_group": "followed"})
            if reason in {
                "ticket_holder",
                "vip_ticket_holder",
                "checked_in_attendee",
            }:
                ticket_holder_content.append({**entry, "library_group": "ticket"})
        elif not serialized.get("expired"):
            access_type = (serialized.get("access") or {}).get("access_type") or "free"
            label_map = {
                "one_time_unlock": "Paid unlock",
                "followers_only": "Follow to unlock",
                "ticket_holder_only": "Ticket-holder",
                "vip_ticket_holder_only": "VIP",
                "checked_in_attendee_only": "Checked-in",
                "invite_only": "Invite-only",
            }
            unlockable.append(
                {
                    **serialized,
                    "access_label": label_map.get(access_type, "Locked"),
                    "library_group": "unlockable",
                }
            )

    missing_purchase_ids = purchased_ids - seen_unlocked
    if missing_purchase_ids:
        extra = db.scalars(
            select(VaultItem)
            .where(VaultItem.id.in_(missing_purchase_ids))
            .options(
                selectinload(VaultItem.media),
                selectinload(VaultItem.access_rule),
            )
        ).all()
        for row in extra:
            serialized = serialize_item(db, row, user=user, include_locked=False)
            if not serialized["has_access"]:
                continue
            unlocked.append(
                {
                    **serialized,
                    "access_label": _access_label(serialized.get("access_reason")),
                    "library_group": "unlocked",
                }
            )
            seen_unlocked.add(row.id)

    purchases = list_my_vault_purchases(db, user)
    activity: list[dict] = []
    for p in purchases[:20]:
        activity.append(
            {
                "id": f"purchase-{p['id']}",
                "kind": "purchase",
                "title": p.get("item_title") or "Vault unlock",
                "detail": f"{p['status']} · {p['currency']} {p['amount']}",
                "at": p["paid_at"] or p["created_at"],
                "href": f"/dashboard/vault/{p['vault_item_id']}",
                "access_label": "Purchased" if p["status"] == "paid" else p["status"],
                "host_username": None,
            }
        )
    for item in unlocked[:20]:
        activity.append(
            {
                "id": f"access-{item['id']}",
                "kind": "access",
                "title": item["title"],
                "detail": item.get("access_label"),
                "at": item.get("published_at") or item["created_at"],
                "href": (
                    f"/@{item['host_username']}/vault/{item['slug']}"
                    if item.get("host_username")
                    else f"/dashboard/vault/{item['id']}"
                ),
                "access_label": item.get("access_label"),
                "host_username": item.get("host_username"),
            }
        )
    activity.sort(
        key=lambda a: a["at"] or datetime.min.replace(tzinfo=UTC),
        reverse=True,
    )

    return {
        "unlocked": unlocked,
        "followed_host_drops": followed_host_drops,
        "ticket_holder_content": ticket_holder_content,
        "unlockable": unlockable[:48],
        "activity": activity[:24],
        "purchases": purchases,
        "stats": {
            "unlocked_count": len(unlocked),
            "followed_count": len(followed_host_drops),
            "ticket_count": len(ticket_holder_content),
            "unlockable_count": len(unlockable),
            "purchase_count": len([p for p in purchases if p["status"] == "paid"]),
        },
    }


def list_my_accessible_items(db: Session, user: User) -> list[dict]:
    """All published Vault items the buyer can currently open."""
    return get_buyer_vault_library(db, user)["unlocked"]


def host_earnings(db: Session, user: User) -> dict:
    host = require_user_host(db, user)
    paid = db.scalars(
        select(VaultPurchase).where(
            VaultPurchase.host_id == host.id, VaultPurchase.status == "paid"
        )
    ).all()
    gross = sum((p.amount for p in paid), Decimal("0"))
    views = db.scalar(
        select(func.count())
        .select_from(VaultView)
        .join(VaultItem, VaultItem.id == VaultView.vault_item_id)
        .where(VaultItem.host_id == host.id)
    ) or 0
    published = db.scalar(
        select(func.count())
        .select_from(VaultItem)
        .where(VaultItem.host_id == host.id, VaultItem.status == "published")
    ) or 0
    total_purchases = db.scalar(
        select(func.count())
        .select_from(VaultPurchase)
        .where(VaultPurchase.host_id == host.id)
    ) or 0
    return {
        "host_id": host.id,
        "currency": "NGN",
        "gross_revenue": gross,
        "purchase_count": int(total_purchases),
        "paid_purchase_count": len(paid),
        "view_count": int(views),
        "published_item_count": int(published),
    }


def _admin_performance_maps(
    db: Session, item_ids: list[UUID]
) -> tuple[
    dict[UUID, int],
    dict[UUID, int],
    dict[UUID, int],
    dict[UUID, Decimal],
    dict[UUID, int],
]:
    """Views, paid unlocks, paid counts, revenue, grants for a set of items."""
    if not item_ids:
        return {}, {}, {}, {}, {}

    view_rows = db.execute(
        select(VaultView.vault_item_id, func.count())
        .where(VaultView.vault_item_id.in_(item_ids))
        .group_by(VaultView.vault_item_id)
    ).all()
    unlock_rows = db.execute(
        select(
            VaultPurchase.vault_item_id,
            func.count(),
            func.coalesce(func.sum(VaultPurchase.amount), 0),
        )
        .where(
            VaultPurchase.vault_item_id.in_(item_ids),
            VaultPurchase.status == "paid",
        )
        .group_by(VaultPurchase.vault_item_id)
    ).all()
    grant_rows = db.execute(
        select(VaultAccessGrant.vault_item_id, func.count())
        .where(VaultAccessGrant.vault_item_id.in_(item_ids))
        .group_by(VaultAccessGrant.vault_item_id)
    ).all()

    views = {row[0]: int(row[1]) for row in view_rows}
    unlocks = {row[0]: int(row[1]) for row in unlock_rows}
    revenue = {row[0]: Decimal(row[2] or 0) for row in unlock_rows}
    grants = {row[0]: int(row[1]) for row in grant_rows}
    return views, unlocks, unlocks, revenue, grants


def list_admin_vault_items(
    db: Session,
    user: User,
    *,
    status: str | None = None,
    moderation_status: str | None = None,
    access_type: str | None = None,
    host_id: UUID | None = None,
    host_username: str | None = None,
    q: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    if not (
        user_has_permission(user, "vault.moderate")
        or user_has_permission(user, "admin.full_access")
    ):
        raise HTTPException(status_code=403, detail="Insufficient permission")

    query = (
        select(VaultItem)
        .options(selectinload(VaultItem.media), selectinload(VaultItem.access_rule))
        .order_by(VaultItem.created_at.desc())
    )
    if status:
        query = query.where(VaultItem.status == status)
    if moderation_status:
        query = query.where(VaultItem.moderation_status == moderation_status)
    if host_id is not None:
        query = query.where(VaultItem.host_id == host_id)
    if host_username:
        host = db.scalar(
            select(Host).where(Host.slug == host_username.strip().lower().lstrip("@"))
        )
        if host is None:
            return []
        query = query.where(VaultItem.host_id == host.id)
    if access_type:
        query = query.join(
            VaultAccessRule, VaultAccessRule.vault_item_id == VaultItem.id
        ).where(VaultAccessRule.access_type == access_type)
    if q and q.strip():
        term = f"%{q.strip().lower()}%"
        query = query.outerjoin(Host, Host.id == VaultItem.host_id).where(
            or_(
                func.lower(VaultItem.title).like(term),
                func.lower(VaultItem.slug).like(term),
                func.lower(VaultItem.content_type).like(term),
                func.lower(Host.slug).like(term),
                func.lower(Host.display_name).like(term),
            )
        )

    limit = max(1, min(int(limit), 200))
    offset = max(0, int(offset))
    rows = db.scalars(query.offset(offset).limit(limit)).all()
    item_ids = [r.id for r in rows]
    views, unlocks, paid_counts, revenue, grants = _admin_performance_maps(
        db, item_ids
    )

    out: list[dict] = []
    for row in rows:
        base = serialize_item(db, row, user=user, include_locked=True)
        access_type_val = (
            row.access_rule.access_type if row.access_rule else "free"
        )
        out.append(
            {
                **base,
                "access_type": access_type_val,
                "view_count": views.get(row.id, 0),
                "unlock_count": unlocks.get(row.id, 0),
                "paid_purchase_count": paid_counts.get(row.id, 0),
                "grant_count": grants.get(row.id, 0),
                "gross_revenue": revenue.get(row.id, Decimal("0")),
                # Reserved until a Vault reports queue exists
                "report_count": 0,
            }
        )
    return out


def moderate_vault_item(
    db: Session, *, user: User, item_id: UUID, payload: VaultModerateRequest
) -> dict:
    from app.vault.constants import MODERATION_ACTIONS_REQUIRE_NOTE

    if not (
        user_has_permission(user, "vault.moderate")
        or user_has_permission(user, "admin.full_access")
    ):
        raise HTTPException(status_code=403, detail="Insufficient permission")
    item = _load_item(db, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Vault item not found")

    ensure_vault_item_lifecycle(item)
    action = payload.action
    note = (payload.note or "").strip() or None
    if action in MODERATION_ACTIONS_REQUIRE_NOTE and not note:
        raise HTTPException(
            status_code=400,
            detail="Moderation reason is required for this action",
        )

    now = datetime.now(UTC)
    item.moderated_by_user_id = user.id
    item.moderated_at = now
    item.moderation_note = note

    if action == "flag":
        item.moderation_status = "flagged"
    elif action == "approve":
        item.moderation_status = "approved"
        if normalize_item_status(item.status) in {"archived", "hidden_by_admin"}:
            apply_admin_restore(item)
    elif action == "hide":
        apply_admin_hide(item, user_id=user.id, now=now)
    elif action in {"archive", "remove"}:
        # archive and remove both soft-end the drop; remove marks moderation removed
        apply_admin_remove(item, user_id=user.id, now=now)
    elif action == "restore":
        apply_admin_restore(item)

    write_audit_log(
        db,
        action=f"vault.moderate.{action}",
        actor_user_id=user.id,
        resource_type="vault_item",
        resource_id=str(item.id),
        details={
            "note": item.moderation_note,
            "status": item.status,
            "moderation_status": item.moderation_status,
        },
    )
    db.commit()
    item = _load_item(db, item.id)
    assert item is not None
    base = serialize_item(db, item, user=user, include_locked=True)
    views, unlocks, paid_counts, revenue, grants = _admin_performance_maps(
        db, [item.id]
    )
    return {
        **base,
        "access_type": (
            item.access_rule.access_type if item.access_rule else "free"
        ),
        "view_count": views.get(item.id, 0),
        "unlock_count": unlocks.get(item.id, 0),
        "paid_purchase_count": paid_counts.get(item.id, 0),
        "grant_count": grants.get(item.id, 0),
        "gross_revenue": revenue.get(item.id, Decimal("0")),
        "report_count": 0,
    }
