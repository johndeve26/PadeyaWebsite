"""User-facing push subscription + preference routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser
from app.core.database import get_db
from app.email.prefs import get_or_create_preferences, update_preferences
from app.notifications.settings_service import get_active_push_settings
from app.push.schemas import (
    PushPreferencesPublic,
    PushPreferencesUpdate,
    PushSubscriptionCreate,
    PushSubscriptionDelete,
    PushSubscriptionListResponse,
    PushSubscriptionPublic,
)
from app.push.service import (
    list_user_subscriptions,
    register_subscription,
    serialize_subscription_public,
    unregister_subscription,
)

router = APIRouter(tags=["push"])


@router.get("/push/vapid-public-key")
def get_vapid_public_key(db: Annotated[Session, Depends(get_db)]) -> dict[str, str | bool]:
    row = get_active_push_settings(db)
    if row is None or not row.push_enabled or not row.vapid_public_key:
        return {"enabled": False, "public_key": ""}
    return {"enabled": True, "public_key": row.vapid_public_key}


@router.get("/push/subscriptions", response_model=PushSubscriptionListResponse)
def get_push_subscriptions(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    include_inactive: Annotated[bool, Query()] = False,
) -> PushSubscriptionListResponse:
    rows = list_user_subscriptions(
        db, user_id=user.id, include_inactive=include_inactive
    )
    return PushSubscriptionListResponse(
        items=[
            PushSubscriptionPublic.model_validate(serialize_subscription_public(r))
            for r in rows
        ],
        total=len(rows),
    )


@router.post("/push/subscriptions", response_model=PushSubscriptionPublic)
def create_push_subscription(
    payload: PushSubscriptionCreate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    user_agent: Annotated[str | None, Header(alias="User-Agent")] = None,
) -> PushSubscriptionPublic:
    del request
    try:
        row = register_subscription(
            db,
            user_id=user.id,
            subscription={
                "endpoint": payload.endpoint,
                "p256dh": payload.p256dh,
                "auth": payload.auth,
                "user_agent": payload.user_agent or user_agent,
                "device_label": payload.device_label,
                "platform": payload.platform,
            },
        )
    except ValueError as exc:
        detail = str(exc)
        code = 503 if "not enabled" in detail.lower() else 400
        raise HTTPException(status_code=code, detail=detail) from exc
    db.commit()
    db.refresh(row)
    return PushSubscriptionPublic.model_validate(serialize_subscription_public(row))


@router.delete("/push/subscriptions")
def delete_push_subscription(
    payload: PushSubscriptionDelete,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict[str, bool]:
    if not payload.endpoint and not payload.subscription_id:
        raise HTTPException(
            status_code=400, detail="endpoint or subscription_id is required"
        )
    ok = unregister_subscription(
        db,
        user_id=user.id,
        endpoint=payload.endpoint,
        subscription_id=payload.subscription_id,
    )
    db.commit()
    return {"revoked": ok}


@router.delete("/push/subscriptions/{subscription_id}")
def delete_push_subscription_by_id(
    subscription_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict[str, bool]:
    ok = unregister_subscription(
        db, user_id=user.id, subscription_id=subscription_id
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Subscription not found")
    db.commit()
    return {"revoked": True}


def _push_prefs_public(prefs) -> PushPreferencesPublic:
    return PushPreferencesPublic(
        push_enabled=bool(prefs.push_enabled),
        push_ticket_updates=bool(prefs.push_ticket_updates),
        push_merch_updates=bool(prefs.push_merch_updates),
        push_event_reminders=bool(prefs.push_event_reminders),
        push_messages=bool(prefs.push_messages),
        push_message_previews=bool(getattr(prefs, "push_message_previews", False)),
        push_fan_connect=bool(prefs.push_fan_connect),
        push_sponsor_updates=bool(prefs.push_sponsor_updates),
        push_host_activity=bool(prefs.push_host_activity),
        push_reviews=bool(getattr(prefs, "push_reviews", True)),
        push_marketing=bool(prefs.push_marketing),
        push_security=True,
    )


@router.get("/push/preferences", response_model=PushPreferencesPublic)
def get_push_preferences(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> PushPreferencesPublic:
    prefs = get_or_create_preferences(db, user.id)
    db.commit()
    return _push_prefs_public(prefs)


@router.patch("/push/preferences", response_model=PushPreferencesPublic)
def patch_push_preferences(
    payload: PushPreferencesUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> PushPreferencesPublic:
    updates = payload.model_dump(exclude_unset=True)
    prefs = update_preferences(db, user_id=user.id, updates=updates)
    db.commit()
    return _push_prefs_public(prefs)
