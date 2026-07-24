"""Vault API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user_optional, require_permission
from app.core.database import get_db
from app.users.models import User
from app.vault import subscriptions_service
from app.vault.schemas import (
    VaultAdminItemPublic,
    VaultCatalogCard,
    VaultCheckoutResponse,
    VaultEarningsPublic,
    VaultInviteRedeemRequest,
    VaultItemCreate,
    VaultItemPublic,
    VaultItemUpdate,
    VaultLibrarySummary,
    VaultManualGrantRequest,
    VaultModerateRequest,
    VaultPurchasePublic,
    VaultScheduleRequest,
    VaultStudioSummary,
    VaultSubscriptionCreate,
    VaultSubscriptionPublic,
)
from app.events.schemas import MessageResponse
from app.vault.service import (
    archive_vault_item,
    create_vault_item,
    delete_vault_item,
    get_buyer_vault_library,
    get_host_vault_item,
    get_public_vault_item,
    get_vault_studio_summary,
    grant_vault_access,
    host_earnings,
    list_admin_vault_items,
    list_host_vault_items,
    list_my_accessible_items,
    list_my_vault_purchases,
    get_my_vault_purchase,
    list_public_vault,
    list_public_vault_for_event,
    list_public_vault_for_memory,
    moderate_vault_item,
    preview_vault_item_as_fan,
    publish_vault_item,
    redeem_vault_invite,
    restore_vault_item,
    schedule_vault_item,
    start_vault_unlock,
    unpublish_vault_item,
    update_vault_item,
)

router = APIRouter(prefix="/vault", tags=["vault"])


@router.get("/health")
async def vault_module_health() -> dict[str, str]:
    return {"module": "vault", "status": "ok"}


# --- Public Legacy Vault ---


@router.get("/related/event/{event_id}", response_model=list[VaultCatalogCard])
def public_vault_for_event(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> list[VaultCatalogCard]:
    """Teaser cards for Vault drops tied to a published event."""
    return [
        VaultCatalogCard.model_validate(r)
        for r in list_public_vault_for_event(db, event_id=event_id, user=user)
    ]


@router.get("/related/memory/{memory_id}", response_model=list[VaultCatalogCard])
def public_vault_for_memory(
    memory_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> list[VaultCatalogCard]:
    """Teaser cards for Vault drops tied to a published Event Memory / its event."""
    return [
        VaultCatalogCard.model_validate(r)
        for r in list_public_vault_for_memory(db, memory_id=memory_id, user=user)
    ]


@router.get("/public/{username}", response_model=list[VaultCatalogCard])
def public_vault_list(
    username: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> list[VaultCatalogCard]:
    return [
        VaultCatalogCard.model_validate(r)
        for r in list_public_vault(db, username=username, user=user)
    ]


@router.get("/public/{username}/{item_slug}", response_model=VaultItemPublic)
def public_vault_item(
    username: str,
    item_slug: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> VaultItemPublic:
    return VaultItemPublic.model_validate(
        get_public_vault_item(db, username=username, item_slug=item_slug, user=user)
    )


# --- Buyer ---


@router.post(
    "/unlock/{item_id}",
    response_model=VaultCheckoutResponse,
    status_code=status.HTTP_201_CREATED,
)
def unlock_item(
    item_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> VaultCheckoutResponse:
    result = start_vault_unlock(db, user=user, item_id=item_id)
    return VaultCheckoutResponse(
        purchase=VaultPurchasePublic.model_validate(result["purchase"]),
        public_key=result["public_key"],
    )


@router.post(
    "/redeem/{item_id}",
    response_model=VaultItemPublic,
    status_code=status.HTTP_201_CREATED,
)
def redeem_invite(
    item_id: UUID,
    payload: VaultInviteRedeemRequest,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> VaultItemPublic:
    result = redeem_vault_invite(
        db, user=user, item_id=item_id, access_code=payload.access_code
    )
    return VaultItemPublic.model_validate(result["item"])


@router.get("/me/purchases", response_model=list[VaultPurchasePublic])
def my_purchases(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[VaultPurchasePublic]:
    return [
        VaultPurchasePublic.model_validate(r) for r in list_my_vault_purchases(db, user)
    ]


@router.get("/me/purchases/{purchase_id}", response_model=VaultPurchasePublic)
def my_purchase(
    purchase_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> VaultPurchasePublic:
    """Poll post-Paystack return status. Never grants access from the client."""
    return VaultPurchasePublic.model_validate(
        get_my_vault_purchase(db, user=user, purchase_id=purchase_id)
    )


@router.get("/me/items", response_model=list[VaultItemPublic])
def my_items(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[VaultItemPublic]:
    return [
        VaultItemPublic.model_validate(r) for r in list_my_accessible_items(db, user)
    ]


@router.get("/me/library", response_model=VaultLibrarySummary)
def my_vault_library(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> VaultLibrarySummary:
    """Fan content library — unlocked, followed, ticket-holder, unlockable, activity."""
    return VaultLibrarySummary.model_validate(get_buyer_vault_library(db, user))


# --- Host ---


@router.get("/host/studio", response_model=VaultStudioSummary)
def host_vault_studio(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("vault.create", "admin.full_access"))],
) -> VaultStudioSummary:
    return VaultStudioSummary.model_validate(get_vault_studio_summary(db, user))


@router.get("/host/items", response_model=list[VaultItemPublic])
def host_items(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("vault.create", "admin.full_access"))],
) -> list[VaultItemPublic]:
    return [
        VaultItemPublic.model_validate(r) for r in list_host_vault_items(db, user)
    ]


@router.post(
    "/host/items",
    response_model=VaultItemPublic,
    status_code=status.HTTP_201_CREATED,
)
def host_create_item(
    payload: VaultItemCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("vault.create", "admin.full_access"))],
) -> VaultItemPublic:
    return VaultItemPublic.model_validate(create_vault_item(db, user=user, payload=payload))


@router.get("/host/items/{item_id}", response_model=VaultItemPublic)
def host_get_item(
    item_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("vault.create", "admin.full_access"))],
) -> VaultItemPublic:
    return VaultItemPublic.model_validate(get_host_vault_item(db, user, item_id))


@router.get("/host/items/{item_id}/preview", response_model=VaultItemPublic)
def host_preview_item_as_fan(
    item_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("vault.create", "admin.full_access"))],
) -> VaultItemPublic:
    """Preview locked fan view — body and non-preview media URLs stay hidden."""
    return VaultItemPublic.model_validate(preview_vault_item_as_fan(db, user, item_id))


@router.patch("/host/items/{item_id}", response_model=VaultItemPublic)
def host_update_item(
    item_id: UUID,
    payload: VaultItemUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("vault.create", "admin.full_access"))],
) -> VaultItemPublic:
    return VaultItemPublic.model_validate(
        update_vault_item(db, user=user, item_id=item_id, payload=payload)
    )


@router.post("/host/items/{item_id}/publish", response_model=VaultItemPublic)
def host_publish_item(
    item_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("vault.create", "admin.full_access"))],
) -> VaultItemPublic:
    return VaultItemPublic.model_validate(
        publish_vault_item(db, user=user, item_id=item_id)
    )


@router.post("/host/items/{item_id}/unpublish", response_model=VaultItemPublic)
def host_unpublish_item(
    item_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("vault.create", "admin.full_access"))],
) -> VaultItemPublic:
    return VaultItemPublic.model_validate(
        unpublish_vault_item(db, user=user, item_id=item_id)
    )


@router.post("/host/items/{item_id}/schedule", response_model=VaultItemPublic)
def host_schedule_item(
    item_id: UUID,
    payload: VaultScheduleRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("vault.create", "admin.full_access"))],
) -> VaultItemPublic:
    return VaultItemPublic.model_validate(
        schedule_vault_item(db, user=user, item_id=item_id, payload=payload)
    )


@router.post("/host/items/{item_id}/archive", response_model=VaultItemPublic)
def host_archive_item(
    item_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("vault.create", "admin.full_access"))],
) -> VaultItemPublic:
    return VaultItemPublic.model_validate(
        archive_vault_item(db, user=user, item_id=item_id)
    )


@router.post("/host/items/{item_id}/restore", response_model=VaultItemPublic)
def host_restore_item(
    item_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("vault.restore", "vault.create", "admin.full_access"))
    ],
) -> VaultItemPublic:
    return VaultItemPublic.model_validate(
        restore_vault_item(db, user=user, item_id=item_id)
    )


@router.post(
    "/host/items/{item_id}/grant",
    response_model=VaultPurchasePublic,
    status_code=status.HTTP_201_CREATED,
)
def host_grant_access(
    item_id: UUID,
    payload: VaultManualGrantRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("vault.create", "admin.full_access"))],
) -> VaultPurchasePublic:
    result = grant_vault_access(
        db, host_user=user, item_id=item_id, buyer_user_id=payload.user_id
    )
    return VaultPurchasePublic.model_validate(result["purchase"])


@router.delete("/host/items/{item_id}", response_model=MessageResponse)
def host_delete_item(
    item_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User,
        Depends(
            require_permission(
                "vault.delete_draft_own", "vault.create", "admin.full_access"
            )
        ),
    ],
) -> MessageResponse:
    delete_vault_item(db, user=user, item_id=item_id)
    return MessageResponse(message="Vault item deleted")


@router.get("/host/earnings", response_model=VaultEarningsPublic)
def host_vault_earnings(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("vault.create", "admin.full_access"))],
) -> VaultEarningsPublic:
    return VaultEarningsPublic.model_validate(host_earnings(db, user))


# --- Subscriptions ---


@router.post(
    "/subscriptions",
    response_model=VaultSubscriptionPublic,
    status_code=status.HTTP_201_CREATED,
)
def create_subscription(
    payload: VaultSubscriptionCreate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> VaultSubscriptionPublic:
    row = subscriptions_service.create_subscription(
        db,
        user=user,
        host_id=payload.host_id,
        plan_label=payload.plan_label,
        price=payload.price,
        currency=payload.currency,
    )
    return VaultSubscriptionPublic.model_validate(row)


@router.get("/subscriptions/mine", response_model=list[VaultSubscriptionPublic])
def my_subscriptions(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    include_archived: bool = False,
) -> list[VaultSubscriptionPublic]:
    rows = subscriptions_service.list_my_subscriptions(
        db, user=user, include_archived=include_archived
    )
    return [VaultSubscriptionPublic.model_validate(r) for r in rows]


@router.get("/host/subscriptions", response_model=list[VaultSubscriptionPublic])
def host_subscriptions(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("vault.create", "admin.full_access"))],
    include_archived: bool = False,
) -> list[VaultSubscriptionPublic]:
    rows = subscriptions_service.list_host_subscriptions(
        db, user=user, include_archived=include_archived
    )
    return [VaultSubscriptionPublic.model_validate(r) for r in rows]


@router.post(
    "/subscriptions/{subscription_id}/cancel",
    response_model=VaultSubscriptionPublic,
)
def cancel_subscription(
    subscription_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> VaultSubscriptionPublic:
    return VaultSubscriptionPublic.model_validate(
        subscriptions_service.cancel_subscription(
            db, user=user, subscription_id=subscription_id
        )
    )


@router.post(
    "/subscriptions/{subscription_id}/archive",
    response_model=VaultSubscriptionPublic,
)
def archive_subscription(
    subscription_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> VaultSubscriptionPublic:
    return VaultSubscriptionPublic.model_validate(
        subscriptions_service.archive_subscription(
            db, user=user, subscription_id=subscription_id
        )
    )


@router.post(
    "/subscriptions/{subscription_id}/restore",
    response_model=VaultSubscriptionPublic,
)
def restore_subscription(
    subscription_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> VaultSubscriptionPublic:
    return VaultSubscriptionPublic.model_validate(
        subscriptions_service.restore_subscription(
            db, user=user, subscription_id=subscription_id
        )
    )


@router.delete(
    "/subscriptions/{subscription_id}",
    status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
)
def delete_subscription() -> None:
    subscriptions_service.delete_subscription_blocked()


# --- Admin moderation ---


@router.get("/admin/items", response_model=list[VaultAdminItemPublic])
def admin_items(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("vault.moderate", "admin.full_access"))
    ],
    status: str | None = None,
    moderation_status: str | None = None,
    access_type: str | None = None,
    host_id: UUID | None = None,
    host_username: str | None = None,
    q: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[VaultAdminItemPublic]:
    return [
        VaultAdminItemPublic.model_validate(r)
        for r in list_admin_vault_items(
            db,
            user,
            status=status,
            moderation_status=moderation_status,
            access_type=access_type,
            host_id=host_id,
            host_username=host_username,
            q=q,
            limit=limit,
            offset=offset,
        )
    ]


@router.post("/admin/items/{item_id}/moderate", response_model=VaultAdminItemPublic)
def admin_moderate(
    item_id: UUID,
    payload: VaultModerateRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("vault.moderate", "admin.full_access"))
    ],
) -> VaultAdminItemPublic:
    return VaultAdminItemPublic.model_validate(
        moderate_vault_item(db, user=user, item_id=item_id, payload=payload)
    )
