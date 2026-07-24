"""Server-side trusted analytics emitters.

Public track endpoints must never accept these actions from the client.
Use ``track_server_event`` from payment, ticket, check-in, review, refund,
vault, promo, and payout flows.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.analytics.dedupe import claim_dedupe_key, generate_dedupe_key
from app.analytics.dimensions import build_analytics_row_dimensions, scrub_metadata
from app.analytics.models import AnalyticsEvent, ConversionEvent
from app.analytics.taxonomy import (
    TrackedAction,
    conversion_stage_for_action,
    is_known_tracked_action,
    is_server_only_action,
    normalize_tracked_action,
    require_known_tracked_action,
)

logger = logging.getLogger(__name__)


def _stable_request_id(rid: str | None, *, max_len: int = 64) -> str | None:
    """Fit request_id into the unique String(64) column without collisions.

    Naive truncation drops distinguishing suffixes (e.g. badge_key) and can make
    two distinct emissions share one request_id — poison the commerce session.
    """
    if rid is None:
        return None
    cleaned = rid.strip()
    if not cleaned:
        return None
    if len(cleaned) <= max_len:
        return cleaned
    return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()[:max_len]


def track_server_event(
    db: Session,
    *,
    event_name: str,
    target_event_id: UUID | None = None,
    host_id: UUID | None = None,
    user_id: UUID | None = None,
    metadata: dict[str, Any] | None = None,
    value: Decimal | float | int | None = None,
    currency: str | None = None,
    session_id: str | None = None,
    anonymous_id: str | None = None,
    order_id: UUID | None = None,
    request_id: str | None = None,
    environment: str | None = None,
) -> AnalyticsEvent | None:
    """Trusted server-side analytics write.

    Validates taxonomy, scrubs metadata, stores value/currency safely, and
    dedupes via request_id / order identity. Never call from public track routes.
    """
    action = require_known_tracked_action(
        normalize_tracked_action(event_name) or (event_name or "")
    )
    if not is_server_only_action(action) and not is_known_tracked_action(action):
        raise ValueError(f"Unknown analytics event_name: {event_name}")

    rid = request_id
    if not rid and order_id is not None:
        rid = f"trusted:{action}:ord:{order_id}"
    if not rid and metadata:
        for key in (
            "refund_request_id",
            "vault_purchase_id",
            "payout_request_id",
            "promo_code_id",
        ):
            if metadata.get(key):
                rid = f"trusted:{action}:{key}:{metadata[key]}"
                break
    rid = _stable_request_id(rid)

    key = generate_dedupe_key(
        f"trusted:{action}",
        request_id=rid,
        target_event_id=target_event_id,
        session_id=session_id,
        anonymous_id=anonymous_id,
        user_id=user_id,
        order_id=order_id,
    )
    if key and not claim_dedupe_key(
        db,
        dedupe_key=key,
        scope=f"trusted:{action}",
        target_event_id=target_event_id,
        session_id=session_id,
        anonymous_id=anonymous_id,
        ttl_hours=None,
        window_seconds=None,
    ):
        return None

    meta = scrub_metadata(
        {
            **(metadata or {}),
            "tracked_action": action,
            "trusted": True,
            "target_event_id": str(target_event_id) if target_event_id else None,
        },
        strict_allowlist=True,
    )
    if order_id is not None:
        meta["order_id"] = str(order_id)
    if value is not None:
        meta["conversion_value"] = str(value)
        meta["amount"] = str(value)
    if currency:
        meta["currency"] = str(currency)[:16]

    dims = build_analytics_row_dimensions(
        anonymous_id=anonymous_id,
        request_id=rid,
        metadata=meta,
        environment=environment or "server",
        target_event_id=target_event_id,
        is_bot=False,
    )
    # Nested savepoint: analytics unique collisions must never abort commerce.
    try:
        with db.begin_nested():
            row = AnalyticsEvent(
                event_name=action,
                entity_type="event" if target_event_id else "commerce",
                entity_id=target_event_id,
                host_id=host_id,
                user_id=user_id,
                session_id=session_id,
                **dims,
            )
            db.add(row)

            stage = conversion_stage_for_action(action)
            if stage and target_event_id is not None:
                amt = Decimal(str(value)) if value is not None else None
                linked_order_id = None
                if order_id is not None:
                    from app.payments.models import Order

                    if db.get(Order, order_id) is not None:
                        linked_order_id = order_id
                db.add(
                    ConversionEvent(
                        event_id=target_event_id,
                        host_id=host_id,
                        user_id=user_id,
                        session_id=session_id,
                        stage=stage,
                        order_id=linked_order_id,
                        amount=amt,
                    )
                )
            db.flush()
        return row
    except IntegrityError:
        logger.warning(
            "trusted analytics write skipped (integrity) action=%s request_id=%s",
            action,
            rid,
        )
        return None


# --- Convenience wrappers (call track_server_event) ---


def emit_trusted_action(
    db: Session,
    *,
    tracked_action: str,
    target_event_id: UUID | None = None,
    host_id: UUID | None = None,
    user_id: UUID | None = None,
    session_id: str | None = None,
    anonymous_id: str | None = None,
    order_id: UUID | None = None,
    amount: Decimal | float | int | None = None,
    metadata: dict[str, Any] | None = None,
    request_id: str | None = None,
    environment: str | None = None,
    currency: str | None = None,
) -> AnalyticsEvent | None:
    """Back-compat alias for ``track_server_event``."""
    return track_server_event(
        db,
        event_name=tracked_action,
        target_event_id=target_event_id,
        host_id=host_id,
        user_id=user_id,
        metadata=metadata,
        value=amount,
        currency=currency,
        session_id=session_id,
        anonymous_id=anonymous_id,
        order_id=order_id,
        request_id=request_id,
        environment=environment,
    )


def emit_payment_success(
    db: Session,
    *,
    order_id: UUID,
    event_id: UUID,
    host_id: UUID,
    buyer_user_id: UUID | None,
    amount: Decimal | float | int | None,
    ticket_count: int = 0,
    currency: str | None = "NGN",
) -> None:
    track_server_event(
        db,
        event_name=TrackedAction.PAYMENT_SUCCESS,
        target_event_id=event_id,
        host_id=host_id,
        user_id=buyer_user_id,
        order_id=order_id,
        value=amount,
        currency=currency,
        request_id=f"trusted:payment_success:ord:{order_id}",
        metadata={
            "quantity": ticket_count,
            "payment_reference": str(order_id),
        },
    )


def emit_ticket_issued(
    db: Session,
    *,
    order_id: UUID,
    event_id: UUID,
    host_id: UUID,
    buyer_user_id: UUID | None,
    ticket_count: int,
) -> None:
    track_server_event(
        db,
        event_name=TrackedAction.TICKET_ISSUED,
        target_event_id=event_id,
        host_id=host_id,
        user_id=buyer_user_id,
        order_id=order_id,
        request_id=f"trusted:ticket_issued:ord:{order_id}",
        metadata={"quantity": ticket_count},
    )


def emit_payment_failed(
    db: Session,
    *,
    order_id: UUID,
    event_id: UUID,
    host_id: UUID,
    buyer_user_id: UUID | None = None,
) -> None:
    track_server_event(
        db,
        event_name=TrackedAction.PAYMENT_FAILED,
        target_event_id=event_id,
        host_id=host_id,
        user_id=buyer_user_id,
        order_id=order_id,
        request_id=f"trusted:payment_failed:ord:{order_id}",
    )


def emit_checkin_success(
    db: Session,
    *,
    event_id: UUID,
    host_id: UUID,
    user_id: UUID | None,
    ticket_id: UUID | None = None,
) -> None:
    track_server_event(
        db,
        event_name=TrackedAction.CHECKIN_SUCCESS,
        target_event_id=event_id,
        host_id=host_id,
        user_id=user_id,
        request_id=f"trusted:checkin_success:tkt:{ticket_id}" if ticket_id else None,
    )


def emit_review_submitted(
    db: Session,
    *,
    event_id: UUID,
    host_id: UUID,
    user_id: UUID,
    review_id: UUID | None = None,
) -> None:
    track_server_event(
        db,
        event_name=TrackedAction.REVIEW_SUBMITTED,
        target_event_id=event_id,
        host_id=host_id,
        user_id=user_id,
        request_id=f"trusted:review_submitted:rev:{review_id}" if review_id else None,
    )


def emit_refund_approved(
    db: Session,
    *,
    refund_request_id: UUID,
    order_id: UUID,
    event_id: UUID | None,
    host_id: UUID,
    amount: Decimal | float | int,
    currency: str = "NGN",
    actor_user_id: UUID | None = None,
) -> None:
    track_server_event(
        db,
        event_name=TrackedAction.REFUND_APPROVED,
        target_event_id=event_id,
        host_id=host_id,
        user_id=actor_user_id,
        order_id=order_id,
        value=amount,
        currency=currency,
        request_id=f"trusted:refund_approved:rr:{refund_request_id}",
        metadata={"refund_request_id": str(refund_request_id)},
    )


def emit_vault_purchase(
    db: Session,
    *,
    vault_purchase_id: UUID,
    host_id: UUID,
    user_id: UUID | None,
    amount: Decimal | float | int,
    currency: str = "NGN",
    vault_item_id: UUID | None = None,
    access_type: str | None = None,
    related_event_id: UUID | None = None,
) -> None:
    track_server_event(
        db,
        event_name=TrackedAction.VAULT_PURCHASE,
        host_id=host_id,
        user_id=user_id,
        value=amount,
        currency=currency,
        request_id=f"trusted:vault_purchase:{vault_purchase_id}",
        metadata={
            "vault_purchase_id": str(vault_purchase_id),
            **({"vault_item_id": str(vault_item_id)} if vault_item_id else {}),
            **({"access_type": access_type} if access_type else {}),
            **(
                {"related_event_id": str(related_event_id)}
                if related_event_id
                else {}
            ),
            "locked_state": "unlocked",
            "source_page": "vault_unlock",
        },
    )


def emit_vault_unlock_success(
    db: Session,
    *,
    host_id: UUID,
    user_id: UUID | None,
    vault_item_id: UUID,
    access_type: str | None = None,
    related_event_id: UUID | None = None,
    vault_purchase_id: UUID | None = None,
    source: str = "purchase",
) -> None:
    """Trusted unlock funnel success (paid / invite / grant)."""
    track_server_event(
        db,
        event_name=TrackedAction.VAULT_UNLOCK_SUCCESS,
        host_id=host_id,
        user_id=user_id,
        request_id=(
            f"trusted:vault_unlock_success:"
            f"{vault_purchase_id or vault_item_id}:{user_id or 'anon'}"
        ),
        metadata={
            "vault_item_id": str(vault_item_id),
            **(
                {"vault_purchase_id": str(vault_purchase_id)}
                if vault_purchase_id
                else {}
            ),
            **({"access_type": access_type} if access_type else {}),
            **(
                {"related_event_id": str(related_event_id)}
                if related_event_id
                else {}
            ),
            "locked_state": "unlocked",
            "source_page": source,
        },
    )


def emit_promo_redemption(
    db: Session,
    *,
    order_id: UUID,
    event_id: UUID,
    host_id: UUID | None,
    user_id: UUID | None,
    promo_code_id: UUID,
    discount: Decimal | float | int,
    currency: str = "NGN",
) -> None:
    track_server_event(
        db,
        event_name=TrackedAction.PROMO_REDEMPTION,
        target_event_id=event_id,
        host_id=host_id,
        user_id=user_id,
        order_id=order_id,
        value=discount,
        currency=currency,
        request_id=f"trusted:promo_redemption:ord:{order_id}",
        metadata={
            "promo_code_id": str(promo_code_id),
            "discount": str(discount),
        },
    )


def emit_ambassador_sale(
    db: Session,
    *,
    order_id: UUID,
    event_id: UUID,
    host_id: UUID | None,
    ambassador_id: UUID,
    revenue: Decimal | float | int,
    commission: Decimal | float | int,
    tickets_sold: int,
    currency: str = "NGN",
    buyer_user_id: UUID | None = None,
) -> None:
    track_server_event(
        db,
        event_name=TrackedAction.AMBASSADOR_SALE,
        target_event_id=event_id,
        host_id=host_id,
        user_id=buyer_user_id,
        order_id=order_id,
        value=revenue,
        currency=currency,
        request_id=f"trusted:ambassador_sale:ord:{order_id}",
        metadata={
            "ambassador_id": str(ambassador_id),
            "commission": str(commission),
            "quantity": tickets_sold,
        },
    )


def emit_payout_completed(
    db: Session,
    *,
    payout_request_id: UUID,
    host_id: UUID,
    amount: Decimal | float | int,
    currency: str = "NGN",
    actor_user_id: UUID | None = None,
) -> None:
    """Admin-finance analytics only — not exposed in host visitor funnels."""
    track_server_event(
        db,
        event_name=TrackedAction.PAYOUT_COMPLETED,
        host_id=host_id,
        user_id=actor_user_id,
        value=amount,
        currency=currency,
        request_id=f"trusted:payout_completed:{payout_request_id}",
        metadata={"payout_request_id": str(payout_request_id)},
    )


def emit_sponsor_sale(
    db: Session,
    *,
    order_id: UUID,
    order_item_id: UUID,
    event_id: UUID,
    host_id: UUID,
    merch_product_id: UUID,
    quantity: int,
    sponsor_brand_name: str | None = None,
    currency: str | None = "NGN",
) -> None:
    """Sponsor-branded merch sale after verified payment — no buyer PII."""
    track_server_event(
        db,
        event_name=TrackedAction.SPONSOR_SALE,
        target_event_id=event_id,
        host_id=host_id,
        order_id=order_id,
        currency=currency,
        request_id=f"trusted:sponsor_sale:item:{order_item_id}",
        metadata={
            "merch_product_id": str(merch_product_id),
            "order_item_id": str(order_item_id),
            "sponsor_brand_name": sponsor_brand_name,
            "quantity": quantity,
            # Explicitly omit buyer email/phone/address/payment secrets
        },
    )


def emit_merch_payment_confirmed(
    db: Session,
    *,
    order_id: UUID,
    event_id: UUID,
    host_id: UUID,
    buyer_user_id: UUID | None,
    merch_item_count: int,
    currency: str | None = "NGN",
) -> None:
    """Payment verified for an order that includes merch (no payment secrets)."""
    track_server_event(
        db,
        event_name=TrackedAction.MERCH_PAYMENT_CONFIRMED,
        target_event_id=event_id,
        host_id=host_id,
        user_id=buyer_user_id,
        order_id=order_id,
        currency=currency,
        request_id=f"trusted:merch_payment_confirmed:ord:{order_id}",
        metadata={"merch_item_count": merch_item_count, "quantity": merch_item_count},
    )


def emit_merch_purchase_completed(
    db: Session,
    *,
    order_id: UUID,
    event_id: UUID,
    host_id: UUID,
    buyer_user_id: UUID | None,
    merch_item_count: int,
    currency: str | None = "NGN",
) -> None:
    """Merch fulfillments created after verified payment."""
    track_server_event(
        db,
        event_name=TrackedAction.MERCH_PURCHASE_COMPLETED,
        target_event_id=event_id,
        host_id=host_id,
        user_id=buyer_user_id,
        order_id=order_id,
        currency=currency,
        request_id=f"trusted:merch_purchase_completed:ord:{order_id}",
        metadata={"merch_item_count": merch_item_count, "quantity": merch_item_count},
    )


def emit_merch_picked_up(
    db: Session,
    *,
    fulfillment_id: UUID,
    event_id: UUID,
    host_id: UUID,
    actor_user_id: UUID | None,
    merch_product_id: UUID | None = None,
    merch_variant_id: UUID | None = None,
    quantity: int = 1,
    fulfillment_method: str | None = None,
) -> None:
    track_server_event(
        db,
        event_name=TrackedAction.MERCH_PICKED_UP,
        target_event_id=event_id,
        host_id=host_id,
        user_id=actor_user_id,
        request_id=f"trusted:merch_picked_up:{fulfillment_id}",
        metadata={
            "fulfillment_id": str(fulfillment_id),
            "merch_product_id": str(merch_product_id) if merch_product_id else None,
            "merch_variant_id": str(merch_variant_id) if merch_variant_id else None,
            "quantity": quantity,
            "fulfillment_method": fulfillment_method or "pickup",
        },
    )


# Back-compat alias
emit_merch_marked_picked_up = emit_merch_picked_up


def emit_merch_qr_scanned(
    db: Session,
    *,
    fulfillment_id: UUID,
    event_id: UUID,
    host_id: UUID,
    actor_user_id: UUID | None,
    merch_product_id: UUID | None = None,
    merch_variant_id: UUID | None = None,
    method: str = "qr",
) -> None:
    track_server_event(
        db,
        event_name=TrackedAction.MERCH_QR_SCANNED,
        target_event_id=event_id,
        host_id=host_id,
        user_id=actor_user_id,
        request_id=f"trusted:merch_qr_scanned:{fulfillment_id}:{method}",
        metadata={
            "fulfillment_id": str(fulfillment_id),
            "merch_product_id": str(merch_product_id) if merch_product_id else None,
            "merch_variant_id": str(merch_variant_id) if merch_variant_id else None,
            "fulfillment_method": "pickup",
            "method": method,
        },
    )


def emit_merch_shipped(
    db: Session,
    *,
    fulfillment_id: UUID,
    event_id: UUID | None,
    host_id: UUID,
    actor_user_id: UUID | None,
    merch_product_id: UUID | None = None,
    merch_variant_id: UUID | None = None,
    quantity: int = 1,
) -> None:
    track_server_event(
        db,
        event_name=TrackedAction.MERCH_SHIPPED,
        target_event_id=event_id,
        host_id=host_id,
        user_id=actor_user_id,
        request_id=f"trusted:merch_shipped:{fulfillment_id}",
        metadata={
            "fulfillment_id": str(fulfillment_id),
            "merch_product_id": str(merch_product_id) if merch_product_id else None,
            "merch_variant_id": str(merch_variant_id) if merch_variant_id else None,
            "quantity": quantity,
            "fulfillment_method": "shipping",
        },
    )


def emit_merch_delivered(
    db: Session,
    *,
    fulfillment_id: UUID,
    event_id: UUID | None,
    host_id: UUID,
    actor_user_id: UUID | None,
    merch_product_id: UUID | None = None,
    merch_variant_id: UUID | None = None,
    quantity: int = 1,
) -> None:
    track_server_event(
        db,
        event_name=TrackedAction.MERCH_DELIVERED,
        target_event_id=event_id,
        host_id=host_id,
        user_id=actor_user_id,
        request_id=f"trusted:merch_delivered:{fulfillment_id}",
        metadata={
            "fulfillment_id": str(fulfillment_id),
            "merch_product_id": str(merch_product_id) if merch_product_id else None,
            "merch_variant_id": str(merch_variant_id) if merch_variant_id else None,
            "quantity": quantity,
            "fulfillment_method": "shipping",
        },
    )


def emit_merch_review_submitted(
    db: Session,
    *,
    event_id: UUID | None,
    host_id: UUID,
    buyer_user_id: UUID | None,
    merch_product_id: UUID,
    order_item_id: UUID | None = None,
) -> None:
    track_server_event(
        db,
        event_name=TrackedAction.MERCH_REVIEW_SUBMITTED,
        target_event_id=event_id,
        host_id=host_id,
        user_id=buyer_user_id,
        request_id=f"trusted:merch_review_submitted:item:{order_item_id or merch_product_id}",
        metadata={
            "merch_product_id": str(merch_product_id),
            "order_item_id": str(order_item_id) if order_item_id else None,
        },
    )


def emit_merch_abandoned_cart_created(
    db: Session,
    *,
    cart_id: UUID,
    event_id: UUID | None,
    host_id: UUID | None,
    buyer_user_id: UUID | None,
    merch_item_count: int,
) -> None:
    track_server_event(
        db,
        event_name=TrackedAction.MERCH_ABANDONED_CART_CREATED,
        target_event_id=event_id,
        host_id=host_id,
        user_id=buyer_user_id,
        request_id=f"trusted:merch_abandoned_cart_created:{cart_id}",
        metadata={
            "cart_id": str(cart_id),
            "merch_item_count": merch_item_count,
        },
    )


def emit_merch_abandoned_cart_recovered(
    db: Session,
    *,
    cart_id: UUID,
    event_id: UUID | None,
    host_id: UUID | None,
    buyer_user_id: UUID | None,
    order_id: UUID | None = None,
    method: str = "reactivated",
) -> None:
    track_server_event(
        db,
        event_name=TrackedAction.MERCH_ABANDONED_CART_RECOVERED,
        target_event_id=event_id,
        host_id=host_id,
        user_id=buyer_user_id,
        order_id=order_id,
        request_id=f"trusted:merch_abandoned_cart_recovered:{cart_id}:{method}",
        metadata={
            "cart_id": str(cart_id),
            "method": method,
        },
    )


def emit_merch_badge_awarded(
    db: Session,
    *,
    buyer_user_id: UUID,
    badge_key: str,
    event_id: UUID | None = None,
    host_id: UUID | None = None,
) -> None:
    track_server_event(
        db,
        event_name=TrackedAction.MERCH_BADGE_AWARDED,
        target_event_id=event_id,
        host_id=host_id,
        user_id=buyer_user_id,
        request_id=f"trusted:merch_badge_awarded:{buyer_user_id}:{badge_key}",
        metadata={"badge_key": badge_key},
    )


def emit_merch_sold_out(
    db: Session,
    *,
    event_id: UUID,
    host_id: UUID,
    merch_product_id: UUID,
    merch_variant_id: UUID,
) -> None:
    track_server_event(
        db,
        event_name=TrackedAction.MERCH_SOLD_OUT,
        target_event_id=event_id,
        host_id=host_id,
        request_id=f"trusted:merch_sold_out:var:{merch_variant_id}",
        metadata={
            "merch_product_id": str(merch_product_id),
            "merch_variant_id": str(merch_variant_id),
        },
    )


def emit_host_merch_product_created(
    db: Session,
    *,
    event_id: UUID,
    host_id: UUID,
    actor_user_id: UUID | None,
    merch_product_id: UUID,
    product_status: str | None = None,
) -> None:
    track_server_event(
        db,
        event_name=TrackedAction.HOST_MERCH_PRODUCT_CREATED,
        target_event_id=event_id,
        host_id=host_id,
        user_id=actor_user_id,
        request_id=f"trusted:host_merch_product_created:{merch_product_id}",
        metadata={
            "merch_product_id": str(merch_product_id),
            "product_status": product_status,
        },
    )


def emit_host_merch_product_updated(
    db: Session,
    *,
    event_id: UUID,
    host_id: UUID,
    actor_user_id: UUID | None,
    merch_product_id: UUID,
    product_status: str | None = None,
) -> None:
    track_server_event(
        db,
        event_name=TrackedAction.HOST_MERCH_PRODUCT_UPDATED,
        target_event_id=event_id,
        host_id=host_id,
        user_id=actor_user_id,
        request_id=(
            f"trusted:host_merch_product_updated:{merch_product_id}:"
            f"{datetime.now(UTC).isoformat()}"
        ),
        metadata={
            "merch_product_id": str(merch_product_id),
            "product_status": product_status,
        },
    )


def emit_host_merch_product_paused(
    db: Session,
    *,
    event_id: UUID,
    host_id: UUID,
    actor_user_id: UUID | None,
    merch_product_id: UUID,
) -> None:
    track_server_event(
        db,
        event_name=TrackedAction.HOST_MERCH_PRODUCT_PAUSED,
        target_event_id=event_id,
        host_id=host_id,
        user_id=actor_user_id,
        request_id=f"trusted:host_merch_product_paused:{merch_product_id}",
        metadata={
            "merch_product_id": str(merch_product_id),
            "product_status": "paused",
        },
    )


def emit_admin_merch_hidden(
    db: Session,
    *,
    event_id: UUID,
    host_id: UUID,
    actor_user_id: UUID | None,
    merch_product_id: UUID,
) -> None:
    track_server_event(
        db,
        event_name=TrackedAction.ADMIN_MERCH_HIDDEN,
        target_event_id=event_id,
        host_id=host_id,
        user_id=actor_user_id,
        request_id=f"trusted:admin_merch_hidden:{merch_product_id}",
        metadata={
            "merch_product_id": str(merch_product_id),
            "moderation_status": "hidden",
        },
    )
