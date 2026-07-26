"""Support tickets API — public, user, host, and admin surfaces."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile, status
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user_optional, require_permission
from app.core.database import get_db
from app.support.constants import CATEGORIES, CATEGORY_LABELS, PRIORITIES, STATUSES
from app.support.rate_limit import rate_limit_public_support
from app.support.schemas import (
    SupportAssignRequest,
    SupportCaseCreate,
    SupportCasePublic,
    SupportCategoryUpdate,
    SupportDeflectionEventCreate,
    SupportEscalateRequest,
    SupportInternalNoteCreate,
    SupportMessageCreate,
    SupportPriorityUpdate,
    SupportPublicCreate,
    SupportPublicReply,
    SupportSettingsPublic,
    SupportSettingsUpdate,
    SupportStatusUpdate,
)
from app.support.service import (
    add_attachment,
    add_internal_note,
    get_attachment_for_download,
    open_support_attachment_bytes,
    add_message,
    add_public_message,
    archive_case,
    assign_case,
    close_case,
    create_case,
    create_public_ticket,
    escalate_case,
    get_case,
    get_case_by_number_public,
    get_settings_dict,
    list_my_cases,
    list_staff_cases,
    record_deflection_event,
    reopen_case,
    resolve_case,
    soft_delete_attachment,
    update_category,
    update_priority,
    update_settings,
    update_status,
)
from app.users.models import User

router = APIRouter(tags=["support"])


@router.get("/support/health")
async def support_module_health() -> dict[str, str]:
    return {"module": "support", "status": "ok"}


@router.get("/support/meta")
def support_meta() -> dict:
    return {
        "categories": [
            {"value": c, "label": CATEGORY_LABELS.get(c, c)} for c in CATEGORIES
        ],
        "statuses": list(STATUSES),
        "priorities": list(PRIORITIES),
    }


@router.post("/support/deflection-events", status_code=status.HTTP_201_CREATED)
def support_deflection_events(
    payload: SupportDeflectionEventCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)] = None,
) -> dict:
    """Public-safe Help deflection analytics (no PII required)."""
    return record_deflection_event(
        db, payload=payload, user_id=user.id if user else None
    )


# --- User / host tickets (also aliased as /cases for compatibility) ---


@router.post(
    "/support/tickets",
    response_model=SupportCasePublic,
    status_code=status.HTTP_201_CREATED,
)
@router.post(
    "/support/cases",
    response_model=SupportCasePublic,
    status_code=status.HTTP_201_CREATED,
)
def create_support_ticket(
    payload: SupportCaseCreate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> SupportCasePublic:
    return SupportCasePublic.model_validate(create_case(db, user=user, payload=payload))


@router.post(
    "/support/tickets/public",
    response_model=SupportCasePublic,
    status_code=status.HTTP_201_CREATED,
)
def create_public_support_ticket(
    payload: SupportPublicCreate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> SupportCasePublic:
    rate_limit_public_support(request)
    return SupportCasePublic.model_validate(create_public_ticket(db, payload=payload))


@router.get("/support/tickets", response_model=list[SupportCasePublic])
@router.get("/support/cases/mine", response_model=list[SupportCasePublic])
def my_tickets(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[SupportCasePublic]:
    return [SupportCasePublic.model_validate(c) for c in list_my_cases(db, user)]


@router.get("/support/tickets/by-number/{ticket_number}", response_model=SupportCasePublic)
def public_ticket_lookup(
    ticket_number: str,
    db: Annotated[Session, Depends(get_db)],
    email: str | None = None,
    token: str | None = None,
) -> SupportCasePublic:
    return SupportCasePublic.model_validate(
        get_case_by_number_public(
            db, ticket_number=ticket_number, email=email, token=token
        )
    )


@router.post(
    "/support/tickets/by-number/{ticket_number}/reply",
    response_model=SupportCasePublic,
)
def public_ticket_reply(
    ticket_number: str,
    payload: SupportPublicReply,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> SupportCasePublic:
    """Requester follow-up without login — same email/token proof as lookup."""
    rate_limit_public_support(request)
    return SupportCasePublic.model_validate(
        add_public_message(db, ticket_number=ticket_number, payload=payload)
    )


@router.get("/support/tickets/{ticket_id}", response_model=SupportCasePublic)
def get_support_ticket(
    ticket_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> SupportCasePublic:
    return SupportCasePublic.model_validate(
        get_case(db, user=user, case_id=ticket_id)
    )


@router.get("/support/cases/{case_id}", response_model=SupportCasePublic)
def get_support_case(
    case_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> SupportCasePublic:
    return SupportCasePublic.model_validate(get_case(db, user=user, case_id=case_id))


@router.post("/support/tickets/{ticket_id}/reply", response_model=SupportCasePublic)
def post_reply(
    ticket_id: UUID,
    payload: SupportMessageCreate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> SupportCasePublic:
    return SupportCasePublic.model_validate(
        add_message(db, user=user, case_id=ticket_id, payload=payload)
    )


@router.post("/support/cases/{case_id}/messages", response_model=SupportCasePublic)
def post_message_legacy(
    case_id: UUID,
    payload: SupportMessageCreate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> SupportCasePublic:
    return SupportCasePublic.model_validate(
        add_message(db, user=user, case_id=case_id, payload=payload)
    )


@router.post(
    "/support/tickets/{ticket_id}/attachments",
    response_model=SupportCasePublic,
)
async def post_attachment(
    ticket_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    file: UploadFile = File(...),
    is_internal: bool = Form(default=False),
) -> SupportCasePublic:
    return SupportCasePublic.model_validate(
        await add_attachment(
            db, user=user, case_id=ticket_id, file=file, is_internal=is_internal
        )
    )


@router.post(
    "/support/cases/{case_id}/attachments",
    response_model=SupportCasePublic,
)
async def post_attachment_legacy(
    case_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    file: UploadFile = File(...),
    is_internal: bool = Form(default=False),
) -> SupportCasePublic:
    return SupportCasePublic.model_validate(
        await add_attachment(
            db, user=user, case_id=case_id, file=file, is_internal=is_internal
        )
    )


@router.get("/support/tickets/{ticket_id}/attachments/{attachment_id}")
def download_attachment(
    ticket_id: UUID,
    attachment_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> Response:
    """Authorized support attachment download — never a public media URL."""
    att = get_attachment_for_download(
        db, user=user, case_id=ticket_id, attachment_id=attachment_id
    )
    from app.core.media_private import get_private_media_storage

    private = get_private_media_storage()
    if private.supports_presign() and att.storage_key:
        try:
            if private.exists(att.storage_key):
                signed = private.presign_get(att.storage_key, expires_in=900)
                return RedirectResponse(
                    url=signed,
                    status_code=307,
                    headers={"Cache-Control": "private, no-store"},
                )
        except Exception:
            pass
    data = open_support_attachment_bytes(att)
    return Response(
        content=data,
        media_type=att.content_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{att.filename}"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.patch("/support/tickets/{ticket_id}/status", response_model=SupportCasePublic)
def user_patch_status(
    ticket_id: UUID,
    payload: SupportStatusUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> SupportCasePublic:
    # Users may only close their own tickets via close endpoint; staff via admin
    if payload.status == "closed":
        return SupportCasePublic.model_validate(close_case(db, user=user, case_id=ticket_id))
    return SupportCasePublic.model_validate(
        update_status(db, user=user, case_id=ticket_id, payload=payload)
    )


# --- Legacy staff list on /support/cases ---


@router.get("/support/cases", response_model=list[SupportCasePublic])
def staff_cases_legacy(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    status_filter: str | None = Query(default=None, alias="status"),
    priority: str | None = None,
    category: str | None = None,
    q: str | None = None,
) -> list[SupportCasePublic]:
    return [
        SupportCasePublic.model_validate(c)
        for c in list_staff_cases(
            db,
            user,
            status_filter=status_filter,
            priority=priority,
            category=category,
            q=q,
        )
    ]


@router.post("/support/cases/{case_id}/notes", response_model=SupportCasePublic)
def post_internal_note_legacy(
    case_id: UUID,
    payload: SupportInternalNoteCreate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> SupportCasePublic:
    return SupportCasePublic.model_validate(
        add_internal_note(db, user=user, case_id=case_id, payload=payload)
    )


@router.post("/support/cases/{case_id}/assign", response_model=SupportCasePublic)
def post_assign_legacy(
    case_id: UUID,
    payload: SupportAssignRequest,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> SupportCasePublic:
    return SupportCasePublic.model_validate(
        assign_case(db, user=user, case_id=case_id, payload=payload)
    )


@router.patch("/support/cases/{case_id}/priority", response_model=SupportCasePublic)
def patch_priority_legacy(
    case_id: UUID,
    payload: SupportPriorityUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> SupportCasePublic:
    return SupportCasePublic.model_validate(
        update_priority(db, user=user, case_id=case_id, payload=payload)
    )


@router.patch("/support/cases/{case_id}/category", response_model=SupportCasePublic)
def patch_category_legacy(
    case_id: UUID,
    payload: SupportCategoryUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> SupportCasePublic:
    return SupportCasePublic.model_validate(
        update_category(db, user=user, case_id=case_id, payload=payload)
    )


@router.post("/support/cases/{case_id}/escalate", response_model=SupportCasePublic)
def post_escalate_legacy(
    case_id: UUID,
    payload: SupportEscalateRequest,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> SupportCasePublic:
    return SupportCasePublic.model_validate(
        escalate_case(db, user=user, case_id=case_id, payload=payload)
    )


@router.post("/support/cases/{case_id}/resolve", response_model=SupportCasePublic)
def post_resolve_legacy(
    case_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> SupportCasePublic:
    return SupportCasePublic.model_validate(resolve_case(db, user=user, case_id=case_id))


@router.post("/support/cases/{case_id}/close", response_model=SupportCasePublic)
def post_close_legacy(
    case_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> SupportCasePublic:
    return SupportCasePublic.model_validate(close_case(db, user=user, case_id=case_id))


@router.post("/support/cases/{case_id}/archive", response_model=SupportCasePublic)
def post_archive_legacy(
    case_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> SupportCasePublic:
    return SupportCasePublic.model_validate(archive_case(db, user=user, case_id=case_id))


# --- Admin support APIs ---


@router.get("/admin/support/tickets", response_model=list[SupportCasePublic])
def admin_list_tickets(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.support.view"))],
    status_filter: str | None = Query(default=None, alias="status"),
    priority: str | None = None,
    category: str | None = None,
    requester_context: str | None = None,
    assigned_to: UUID | None = None,
    q: str | None = None,
) -> list[SupportCasePublic]:
    return [
        SupportCasePublic.model_validate(c)
        for c in list_staff_cases(
            db,
            user,
            status_filter=status_filter,
            priority=priority,
            category=category,
            requester_context=requester_context,
            assigned_to=assigned_to,
            q=q,
        )
    ]


@router.get("/admin/support/tickets/{ticket_id}", response_model=SupportCasePublic)
def admin_get_ticket(
    ticket_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.support.view"))],
) -> SupportCasePublic:
    return SupportCasePublic.model_validate(get_case(db, user=user, case_id=ticket_id))


@router.post(
    "/admin/support/tickets/{ticket_id}/reply", response_model=SupportCasePublic
)
def admin_reply(
    ticket_id: UUID,
    payload: SupportMessageCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.support.reply"))],
) -> SupportCasePublic:
    return SupportCasePublic.model_validate(
        add_message(db, user=user, case_id=ticket_id, payload=payload)
    )


@router.post(
    "/admin/support/tickets/{ticket_id}/internal-note",
    response_model=SupportCasePublic,
)
def admin_internal_note(
    ticket_id: UUID,
    payload: SupportInternalNoteCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.support.internal_notes"))],
) -> SupportCasePublic:
    return SupportCasePublic.model_validate(
        add_internal_note(db, user=user, case_id=ticket_id, payload=payload)
    )


@router.patch(
    "/admin/support/tickets/{ticket_id}/assign", response_model=SupportCasePublic
)
def admin_assign(
    ticket_id: UUID,
    payload: SupportAssignRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.support.assign"))],
) -> SupportCasePublic:
    return SupportCasePublic.model_validate(
        assign_case(db, user=user, case_id=ticket_id, payload=payload)
    )


@router.patch(
    "/admin/support/tickets/{ticket_id}/priority", response_model=SupportCasePublic
)
def admin_priority(
    ticket_id: UUID,
    payload: SupportPriorityUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.support.assign"))],
) -> SupportCasePublic:
    return SupportCasePublic.model_validate(
        update_priority(db, user=user, case_id=ticket_id, payload=payload)
    )


@router.patch(
    "/admin/support/tickets/{ticket_id}/category", response_model=SupportCasePublic
)
def admin_category(
    ticket_id: UUID,
    payload: SupportCategoryUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.support.assign"))],
) -> SupportCasePublic:
    return SupportCasePublic.model_validate(
        update_category(db, user=user, case_id=ticket_id, payload=payload)
    )


@router.patch(
    "/admin/support/tickets/{ticket_id}/status", response_model=SupportCasePublic
)
def admin_status(
    ticket_id: UUID,
    payload: SupportStatusUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.support.resolve"))],
) -> SupportCasePublic:
    return SupportCasePublic.model_validate(
        update_status(db, user=user, case_id=ticket_id, payload=payload)
    )


@router.post(
    "/admin/support/tickets/{ticket_id}/resolve", response_model=SupportCasePublic
)
def admin_resolve(
    ticket_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.support.resolve"))],
) -> SupportCasePublic:
    return SupportCasePublic.model_validate(resolve_case(db, user=user, case_id=ticket_id))


@router.post(
    "/admin/support/tickets/{ticket_id}/close", response_model=SupportCasePublic
)
def admin_close(
    ticket_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.support.close"))],
) -> SupportCasePublic:
    return SupportCasePublic.model_validate(close_case(db, user=user, case_id=ticket_id))


@router.post(
    "/admin/support/tickets/{ticket_id}/reopen", response_model=SupportCasePublic
)
def admin_reopen(
    ticket_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.support.resolve"))],
) -> SupportCasePublic:
    return SupportCasePublic.model_validate(reopen_case(db, user=user, case_id=ticket_id))


@router.post(
    "/admin/support/tickets/{ticket_id}/escalate", response_model=SupportCasePublic
)
def admin_escalate(
    ticket_id: UUID,
    payload: SupportEscalateRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.support.assign"))],
) -> SupportCasePublic:
    return SupportCasePublic.model_validate(
        escalate_case(db, user=user, case_id=ticket_id, payload=payload)
    )


@router.delete(
    "/admin/support/tickets/{ticket_id}/attachments/{attachment_id}",
    response_model=SupportCasePublic,
)
def admin_delete_attachment(
    ticket_id: UUID,
    attachment_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("admin.support.delete_attachment"))
    ],
) -> SupportCasePublic:
    return SupportCasePublic.model_validate(
        soft_delete_attachment(
            db, user=user, case_id=ticket_id, attachment_id=attachment_id
        )
    )


@router.get("/admin/support/settings", response_model=SupportSettingsPublic)
def admin_get_settings(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.support.view"))],
) -> SupportSettingsPublic:
    return SupportSettingsPublic.model_validate(get_settings_dict(db))


@router.patch("/admin/support/settings", response_model=SupportSettingsPublic)
def admin_patch_settings(
    payload: SupportSettingsUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.support.manage_settings"))],
) -> SupportSettingsPublic:
    return SupportSettingsPublic.model_validate(
        update_settings(db, user=user, payload=payload)
    )
