"""Blog comments — guest + authenticated create, replies, edit, admin moderate."""

from __future__ import annotations

import html
import re
import uuid
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.blog.models import BlogComment, BlogCommentEdit, BlogPost
from app.blog.schemas import CommentCreate, CommentReplyCreate, CommentUpdate
from app.blog.service import _require_blog_perm, get_public_post
from app.core.audit import write_audit_log
from app.core.http_errors import raise_not_found
from app.passport.models import FanPassport
from app.passport.privacy import VISIBILITY_PUBLIC
from app.users.models import User
from app.users.service import user_has_permission


def _user_has_any_permission(user: User, *permission_codes: str) -> bool:
    return any(user_has_permission(user, code) for code in permission_codes)


COMMENT_STATUSES = frozenset({"published", "hidden", "archived"})
# Product already allows guest top-level comments — guest replies follow the same rule.
GUEST_COMMENTS_ALLOWED = True
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_TAG_RE = re.compile(r"<[^>]+>")

PERM_EDIT_OWN = "blog.comments.edit_own"
PERM_REPLY = "blog.comments.reply"
PERM_EDIT_ANY = "admin.blog.comments.edit_any"
PERM_REPLY_ANY = "admin.blog.comments.reply_any"
PERM_MODERATE = "admin.blog.comments.moderate"


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _clean_body(raw: str) -> str:
    text = _TAG_RE.sub("", raw or "")
    text = html.unescape(text).strip()
    if len(text) < 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Comment must be at least 2 characters.",
        )
    if len(text) > 2000:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Comment must be at most 2000 characters.",
        )
    return text


def _is_staff_editor(user: User) -> bool:
    return _user_has_any_permission(
        user,
        PERM_EDIT_ANY,
        PERM_MODERATE,
        "admin.blog.edit",
        "admin.full_access",
    )


def _is_staff_replier(user: User) -> bool:
    return _user_has_any_permission(
        user,
        PERM_REPLY_ANY,
        PERM_MODERATE,
        "admin.blog.edit",
        "admin.full_access",
    )


def _is_moderator(user: User) -> bool:
    return _user_has_any_permission(user, PERM_MODERATE, "admin.full_access")


def _assert_user_can_write(db: Session, user: User) -> None:
    """Block inactive / suspended / banned / read-only accounts from commenting."""
    from app.users.account_status_service import effective_account_status
    from app.users.restrictions import assert_no_restriction

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is inactive.",
        )
    acct = effective_account_status(user)
    if acct in {"suspended", "banned"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot comment while your account is restricted.",
        )
    assert_no_restriction(
        db,
        user.id,
        "read_only_account",
        detail="You cannot comment with a read-only account.",
    )


def _can_edit_comment(row: BlogComment, viewer: User | None) -> bool:
    if viewer is None:
        return False
    if _is_staff_editor(viewer):
        # Staff may edit published or hidden; archived is locked.
        return row.status != "archived"
    if (
        row.user_id
        and row.user_id == viewer.id
        and user_has_permission(viewer, PERM_EDIT_OWN)
    ):
        return row.status == "published" and row.archived_at is None
    return False


def _can_reply_to_root(row: BlogComment, viewer: User | None) -> bool:
    """Reply UI only on top-level comments (one-level threading)."""
    if row.depth != 0 or row.parent_comment_id is not None:
        return False
    if row.status == "archived" or row.archived_at is not None:
        return False
    if row.status == "hidden":
        return viewer is not None and _is_staff_replier(viewer)
    if row.status != "published":
        return False
    if viewer is None:
        return GUEST_COMMENTS_ALLOWED
    if _is_staff_replier(viewer):
        return True
    return user_has_permission(viewer, PERM_REPLY)


def _staff_author_badge(db: Session, row: BlogComment) -> str | None:
    """Public badge only — never emails or private roles."""
    if not row.is_staff_author:
        return None
    if not row.user_id:
        return "Pàdéyá"
    author = db.get(User, row.user_id)
    if author is None:
        return "Pàdéyá"
    if user_has_permission(author, "admin.blog.edit") or user_has_permission(
        author, "admin.full_access"
    ):
        return "Pàdéyá"
    if _user_has_any_permission(author, PERM_MODERATE, PERM_REPLY_ANY):
        return "Moderator"
    return "Pàdéyá"


def _author_fields(db: Session, row: BlogComment) -> dict[str, Any]:
    """Resolve public display name + optional passport link (public only)."""
    if row.user_id:
        user = db.get(User, row.user_id)
        passport = db.scalar(
            select(FanPassport).where(FanPassport.user_id == row.user_id)
        )
        display = (
            (passport.display_name if passport else None)
            or (user.full_name if user else None)
            or "Member"
        )
        username = passport.username if passport else None
        passport_path = (
            f"/f/{username}"
            if username and passport and passport.visibility == VISIBILITY_PUBLIC
            else None
        )
        return {
            "display_name": display,
            "is_guest": False,
            "passport_path": passport_path,
        }
    return {
        "display_name": (row.guest_name or "Guest").strip() or "Guest",
        "is_guest": True,
        "passport_path": None,
    }


def serialize_comment(
    db: Session,
    row: BlogComment,
    *,
    viewer: User | None = None,
    admin: bool = False,
    replies: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    author = _author_fields(db, row)
    is_edited = bool(row.edited_at)
    edited_by_moderator = bool(row.edited_by_admin_id)
    data: dict[str, Any] = {
        "id": row.id,
        "post_id": row.post_id,
        "body": row.body,
        "status": row.status,
        "display_name": author["display_name"],
        "is_guest": author["is_guest"],
        "passport_path": author["passport_path"],
        "created_at": row.created_at,
        "is_mine": bool(viewer and row.user_id and viewer.id == row.user_id),
        "can_edit": _can_edit_comment(row, viewer),
        "can_reply": _can_reply_to_root(row, viewer),
        "is_edited": is_edited,
        "edited_at": row.edited_at,
        "edited_by_moderator": edited_by_moderator,
        "parent_comment_id": row.parent_comment_id,
        "depth": row.depth,
        "reply_count": row.reply_count,
        "is_staff_author": row.is_staff_author,
        "author_badge": _staff_author_badge(db, row),
        "replies": replies if replies is not None else [],
    }
    if admin:
        data["user_id"] = row.user_id
        data["guest_email"] = row.guest_email
        data["archived_at"] = row.archived_at
        data["archived_by"] = row.archived_by
        data["updated_at"] = row.updated_at
        data["edited_by_user_id"] = row.edited_by_user_id
        data["edited_by_admin_id"] = row.edited_by_admin_id
    return data


def list_public_comments(
    db: Session,
    *,
    post_slug: str,
    viewer: User | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Return top-level published comments with nested depth-1 replies."""
    post = get_public_post(db, post_slug)
    rows = list(
        db.scalars(
            select(BlogComment)
            .where(
                BlogComment.post_id == post.id,
                BlogComment.status == "published",
                BlogComment.archived_at.is_(None),
            )
            .order_by(BlogComment.created_at.asc())
            .limit(min(limit, 500))
        ).all()
    )
    roots = [r for r in rows if r.parent_comment_id is None and r.depth == 0]
    replies_by_parent: dict[UUID, list[BlogComment]] = {}
    for r in rows:
        if r.parent_comment_id is not None and r.depth == 1:
            replies_by_parent.setdefault(r.parent_comment_id, []).append(r)

    # Prefer newest top-level last; cap top-level count with limit.
    roots = roots[-min(limit, 200) :] if len(roots) > min(limit, 200) else roots

    out: list[dict[str, Any]] = []
    for root in roots:
        nested = [
            serialize_comment(db, reply, viewer=viewer, replies=[])
            for reply in replies_by_parent.get(root.id, [])
        ]
        out.append(serialize_comment(db, root, viewer=viewer, replies=nested))
    return out


def _guest_fields_from_payload(
    *,
    guest_name: str | None,
    guest_email: str | None,
) -> tuple[str, str | None]:
    name = (guest_name or "").strip()
    if len(name) < 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Name is required for guest comments.",
        )
    email = (guest_email or "").strip().lower() or None
    if email and not _EMAIL_RE.match(email):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Enter a valid email address.",
        )
    return name[:120], email


def create_comment(
    db: Session,
    *,
    post_slug: str,
    payload: CommentCreate,
    user: User | None = None,
) -> BlogComment:
    post = get_public_post(db, post_slug)

    if (payload.website or "").strip():
        return BlogComment(
            id=uuid.uuid4(),
            post_id=post.id,
            user_id=None,
            parent_comment_id=None,
            depth=0,
            reply_count=0,
            is_staff_author=False,
            guest_name=(payload.guest_name or "Guest")[:120],
            guest_email=None,
            body=(payload.body or "Thanks").strip()[:2000] or "Thanks",
            status="published",
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )

    if user is not None:
        _assert_user_can_write(db, user)
    elif not GUEST_COMMENTS_ALLOWED:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sign in to comment.",
        )

    body = _clean_body(payload.body)
    staff = bool(user and _is_staff_replier(user))

    if user is not None:
        row = BlogComment(
            post_id=post.id,
            user_id=user.id,
            parent_comment_id=None,
            depth=0,
            reply_count=0,
            is_staff_author=staff,
            guest_name=None,
            guest_email=None,
            body=body,
            status="published",
        )
    else:
        name, email = _guest_fields_from_payload(
            guest_name=payload.guest_name, guest_email=payload.guest_email
        )
        row = BlogComment(
            post_id=post.id,
            user_id=None,
            parent_comment_id=None,
            depth=0,
            reply_count=0,
            is_staff_author=False,
            guest_name=name,
            guest_email=email,
            body=body,
            status="published",
        )

    db.add(row)
    db.flush()
    write_audit_log(
        db,
        action="blog_comment_create",
        actor_user_id=user.id if user else None,
        resource_type="blog_comment",
        resource_id=str(row.id),
        details={"post_id": str(post.id), "is_guest": user is None, "depth": 0},
    )
    db.commit()
    db.refresh(row)
    return row


def _resolve_reply_root(db: Session, target: BlogComment) -> BlogComment:
    """One-level threading: replies always attach to the top-level parent."""
    if target.parent_comment_id is None and target.depth == 0:
        return target
    root = db.get(BlogComment, target.parent_comment_id)
    if root is None or root.parent_comment_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot reply to this comment.",
        )
    return root


def create_reply(
    db: Session,
    *,
    comment_id: UUID,
    payload: CommentReplyCreate,
    user: User | None = None,
) -> BlogComment:
    target = db.get(BlogComment, comment_id)
    if target is None:
        raise_not_found("Comment not found")

    # Ensure the post is still publicly commentable.
    post = db.get(BlogPost, target.post_id)
    if post is None or post.status != "published" or post.archived_at is not None:
        raise_not_found("Comment not found")

    root = _resolve_reply_root(db, target)

    if (payload.website or "").strip():
        return BlogComment(
            id=uuid.uuid4(),
            post_id=root.post_id,
            user_id=None,
            parent_comment_id=root.id,
            depth=1,
            reply_count=0,
            is_staff_author=False,
            guest_name=(payload.guest_name or "Guest")[:120],
            guest_email=None,
            body=(payload.body or "Thanks").strip()[:2000] or "Thanks",
            status="published",
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )

    staff = bool(user and _is_staff_replier(user))

    if root.status == "archived" or root.archived_at is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot reply to this comment.",
        )
    if root.status == "hidden":
        if not staff:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot reply to this comment.",
            )
    elif root.status != "published":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot reply to this comment.",
        )

    if user is not None:
        _assert_user_can_write(db, user)
        if not staff and not user_has_permission(user, PERM_REPLY):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot reply to this comment.",
            )
    else:
        if not GUEST_COMMENTS_ALLOWED:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Sign in to reply.",
            )

    body = _clean_body(payload.body)

    if user is not None:
        row = BlogComment(
            post_id=root.post_id,
            user_id=user.id,
            parent_comment_id=root.id,
            depth=1,
            reply_count=0,
            is_staff_author=staff,
            guest_name=None,
            guest_email=None,
            body=body,
            status="published",
        )
    else:
        name, email = _guest_fields_from_payload(
            guest_name=payload.guest_name, guest_email=payload.guest_email
        )
        row = BlogComment(
            post_id=root.post_id,
            user_id=None,
            parent_comment_id=root.id,
            depth=1,
            reply_count=0,
            is_staff_author=False,
            guest_name=name,
            guest_email=email,
            body=body,
            status="published",
        )

    db.add(row)
    root.reply_count = int(root.reply_count or 0) + 1
    db.flush()
    write_audit_log(
        db,
        action="blog_comment_reply",
        actor_user_id=user.id if user else None,
        resource_type="blog_comment",
        resource_id=str(row.id),
        details={
            "post_id": str(root.post_id),
            "parent_comment_id": str(root.id),
            "is_guest": user is None,
            "is_staff": staff,
            "depth": 1,
        },
    )
    db.commit()
    db.refresh(row)
    return row


def update_comment(
    db: Session,
    *,
    comment_id: UUID,
    payload: CommentUpdate,
    user: User,
) -> BlogComment:
    row = db.get(BlogComment, comment_id)
    if row is None:
        raise_not_found("Comment not found")

    is_owner = bool(row.user_id and row.user_id == user.id)
    staff = _is_staff_editor(user)

    if staff:
        if row.status == "archived":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This comment can no longer be edited.",
            )
    elif is_owner and user_has_permission(user, PERM_EDIT_OWN):
        if row.status != "published" or row.archived_at is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This comment can no longer be edited.",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own comments.",
        )

    new_body = _clean_body(payload.body)
    previous = row.body
    if new_body == previous:
        return row

    # Staff editing someone else's comment (or own with an edit reason) → moderator path.
    as_staff = staff and (not is_owner or bool(payload.edit_reason))
    if as_staff:
        edit_type = "moderator" if _is_moderator(user) else "admin"
        row.edited_by_admin_id = user.id
        row.edited_by_user_id = None
    else:
        edit_type = "owner"
        row.edited_by_user_id = user.id
        row.edited_by_admin_id = None

    now = _utcnow()
    history = BlogCommentEdit(
        comment_id=row.id,
        edited_by_user_id=user.id if edit_type == "owner" else None,
        edited_by_admin_id=user.id if edit_type != "owner" else None,
        previous_body=previous,
        new_body=new_body,
        reason=(payload.edit_reason or None) if as_staff else None,
        edit_type=edit_type,
    )
    db.add(history)

    row.body = new_body
    row.edited_at = now
    # updated_at via onupdate

    write_audit_log(
        db,
        action="blog_comment_edit",
        actor_user_id=user.id,
        resource_type="blog_comment",
        resource_id=str(row.id),
        details={
            "post_id": str(row.post_id),
            "edit_type": edit_type,
            "has_reason": bool(payload.edit_reason),
        },
    )
    db.commit()
    db.refresh(row)
    return row


def withdraw_own_comment(
    db: Session, *, comment_id: UUID, user: User
) -> BlogComment:
    row = db.get(BlogComment, comment_id)
    if row is None or row.user_id != user.id or row.status == "archived":
        raise_not_found("Comment not found")
    row.status = "archived"
    row.archived_at = _utcnow()
    row.archived_by = user.id
    if row.parent_comment_id and row.depth == 1:
        parent = db.get(BlogComment, row.parent_comment_id)
        if parent is not None and parent.reply_count > 0:
            parent.reply_count = parent.reply_count - 1
    write_audit_log(
        db,
        action="blog_comment_withdraw",
        actor_user_id=user.id,
        resource_type="blog_comment",
        resource_id=str(row.id),
        details={
            "post_id": str(row.post_id),
            "parent_comment_id": str(row.parent_comment_id)
            if row.parent_comment_id
            else None,
        },
    )
    db.commit()
    db.refresh(row)
    return row


def list_admin_comments(
    db: Session,
    *,
    user: User,
    post_id: UUID | None = None,
    status_filter: str | None = None,
    limit: int = 100,
) -> list[BlogComment]:
    _require_blog_perm(
        user,
        "admin.blog.view",
        "admin.blog.edit",
        PERM_EDIT_ANY,
        PERM_MODERATE,
    )
    stmt = select(BlogComment).order_by(BlogComment.created_at.desc())
    if post_id:
        stmt = stmt.where(BlogComment.post_id == post_id)
    if status_filter:
        if status_filter not in COMMENT_STATUSES:
            raise HTTPException(status_code=422, detail="Invalid status filter")
        stmt = stmt.where(BlogComment.status == status_filter)
    stmt = stmt.limit(min(limit, 200))
    return list(db.scalars(stmt).all())


def hide_comment(db: Session, *, user: User, comment_id: UUID) -> BlogComment:
    _require_blog_perm(user, "admin.blog.edit", PERM_MODERATE)
    row = db.get(BlogComment, comment_id)
    if row is None:
        raise_not_found("Comment not found")
    if row.status == "archived":
        raise HTTPException(status_code=400, detail="Archived comments cannot be hidden")
    was_published = row.status == "published"
    row.status = "hidden"
    if was_published and row.parent_comment_id and row.depth == 1:
        parent = db.get(BlogComment, row.parent_comment_id)
        if parent is not None and parent.reply_count > 0:
            parent.reply_count = parent.reply_count - 1
    write_audit_log(
        db,
        action="blog_comment_hide",
        actor_user_id=user.id,
        resource_type="blog_comment",
        resource_id=str(row.id),
        details={"post_id": str(row.post_id)},
    )
    db.commit()
    db.refresh(row)
    return row


def restore_comment(db: Session, *, user: User, comment_id: UUID) -> BlogComment:
    _require_blog_perm(user, "admin.blog.edit", PERM_MODERATE)
    row = db.get(BlogComment, comment_id)
    if row is None:
        raise_not_found("Comment not found")
    if row.status == "archived":
        raise HTTPException(
            status_code=400, detail="Archived comments cannot be restored to public"
        )
    was_hidden = row.status == "hidden"
    row.status = "published"
    row.archived_at = None
    row.archived_by = None
    if was_hidden and row.parent_comment_id and row.depth == 1:
        parent = db.get(BlogComment, row.parent_comment_id)
        if parent is not None:
            parent.reply_count = int(parent.reply_count or 0) + 1
    write_audit_log(
        db,
        action="blog_comment_restore",
        actor_user_id=user.id,
        resource_type="blog_comment",
        resource_id=str(row.id),
        details={"post_id": str(row.post_id)},
    )
    db.commit()
    db.refresh(row)
    return row


def archive_comment(db: Session, *, user: User, comment_id: UUID) -> BlogComment:
    _require_blog_perm(user, "admin.blog.edit", "admin.blog.delete", PERM_MODERATE)
    row = db.get(BlogComment, comment_id)
    if row is None:
        raise_not_found("Comment not found")
    was_published = row.status == "published"
    row.status = "archived"
    row.archived_at = _utcnow()
    row.archived_by = user.id
    if was_published and row.parent_comment_id and row.depth == 1:
        parent = db.get(BlogComment, row.parent_comment_id)
        if parent is not None and parent.reply_count > 0:
            parent.reply_count = parent.reply_count - 1
    write_audit_log(
        db,
        action="blog_comment_archive",
        actor_user_id=user.id,
        resource_type="blog_comment",
        resource_id=str(row.id),
        details={"post_id": str(row.post_id)},
    )
    db.commit()
    db.refresh(row)
    return row
