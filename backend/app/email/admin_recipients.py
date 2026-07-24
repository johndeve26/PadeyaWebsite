"""Admin platform email recipient parsing and resolution."""

from __future__ import annotations

import re
from typing import Literal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.email.admin_catalog import AdminTemplateCatalogEntry
from app.email.models import EmailAdminTemplate
from app.users.models import User

RecipientMode = Literal["group", "custom", "group_and_custom"]

MAX_RECIPIENTS_PER_TEMPLATE = 20
MAX_TEST_RECIPIENTS = 5

# Practical single-address check (not full RFC 5322).
_EMAIL_RE = re.compile(
    r"^[a-z0-9][a-z0-9._+\-]*@[a-z0-9][a-z0-9.\-]*\.[a-z]{2,}$",
    re.IGNORECASE,
)

RECIPIENT_MODES: frozenset[str] = frozenset({"group", "custom", "group_and_custom"})


class RecipientParseError(ValueError):
    def __init__(self, message: str, *, invalid: str | None = None) -> None:
        super().__init__(message)
        self.invalid = invalid


def parse_recipient_emails(
    raw: str,
    *,
    max_count: int = MAX_RECIPIENTS_PER_TEMPLATE,
) -> list[str]:
    """Parse comma/semicolon-separated emails → normalized, deduped list."""
    if raw is None:
        return []
    text = str(raw).strip()
    if not text:
        return []

    normalized = text.replace(";", ",")
    parts = [p.strip() for p in normalized.split(",")]
    out: list[str] = []
    seen: set[str] = set()

    for part in parts:
        if not part:
            continue
        email = part.lower()
        if not _EMAIL_RE.match(email):
            raise RecipientParseError(
                f"Invalid email: {part}",
                invalid=part,
            )
        if email in seen:
            continue
        seen.add(email)
        out.append(email)
        if len(out) > max_count:
            raise RecipientParseError(
                f"At most {max_count} recipient emails allowed per template.",
            )

    return out


def parse_recipient_emails_http(raw: str, *, max_count: int = MAX_RECIPIENTS_PER_TEMPLATE) -> list[str]:
    try:
        return parse_recipient_emails(raw, max_count=max_count)
    except RecipientParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def effective_recipient_mode(row: EmailAdminTemplate | None, *, default_group: str) -> RecipientMode:
    if row is not None and row.recipient_mode in RECIPIENT_MODES:
        return row.recipient_mode  # type: ignore[return-value]
    if default_group == "custom":
        return "custom"
    return "group"


def effective_recipient_group(
    cat: AdminTemplateCatalogEntry,
    row: EmailAdminTemplate | None,
) -> str:
    if row is not None and row.recipient_group:
        return row.recipient_group
    if row is not None and row.default_recipient_group:
        return row.default_recipient_group
    return cat.default_recipient_group


def resolve_admin_template_recipient_list(
    db: Session,
    *,
    template_key: str,
    row: EmailAdminTemplate | None = None,
) -> list[tuple[User | None, str]]:
    from app.email.admin_catalog import catalog_entry

    entry = catalog_entry(template_key)
    if entry is None:
        return []
    if row is None:
        from sqlalchemy import select

        row = db.scalar(
            select(EmailAdminTemplate).where(EmailAdminTemplate.key == template_key)
        )
    mode = effective_recipient_mode(row, default_group=entry.default_recipient_group)
    group = effective_recipient_group(entry, row)
    custom = list(row.custom_recipient_emails if row else [])
    return resolve_template_recipients(
        db,
        mode=mode,
        group=group,
        custom_emails=custom,
        users_for_group_fn=_users_for_group,
    )


def _users_for_group(db: Session, group: str) -> list[User]:
    from sqlalchemy import select

    from app.users.models import Permission, Role

    if group == "custom":
        return []

    if group == "super_admin":
        role = db.scalar(select(Role).where(Role.name == "super_admin"))
        if role is None:
            return []
        return [u for u in role.users if u.is_active and u.email]

    codes = GROUP_PERMISSIONS.get(group, ())
    if not codes:
        return []

    perm_ids = db.scalars(select(Permission.id).where(Permission.code.in_(codes))).all()
    if not perm_ids:
        return []

    q = (
        select(User)
        .join(User.roles)
        .join(Role.permissions)
        .where(Permission.id.in_(perm_ids), User.is_active.is_(True))
        .distinct()
    )
    return list(db.scalars(q))


GROUP_PERMISSIONS: dict[str, tuple[str, ...]] = {
    "super_admin": ("admin.full_access",),
    "support": ("admin.support.view_all", "admin.support.view"),
    "moderation": ("reviews.moderate", "merch.moderate", "vault.moderate"),
    "finance": ("payments.view", "admin.finance.view_fees", "refunds.review"),
    "operations": ("admin.events.view", "hosts.verify", "events.review"),
    "marketing": ("sponsorships.moderate",),
}


def resolve_template_recipients(
    db: Session,
    *,
    mode: RecipientMode,
    group: str,
    custom_emails: list[str],
    users_for_group_fn,
) -> list[tuple[User | None, str]]:
    """Combine group + custom per mode; dedupe; cap at MAX_RECIPIENTS_PER_TEMPLATE."""
    out: list[tuple[User | None, str]] = []
    seen: set[str] = set()

    def add_user(user: User | None, email: str) -> None:
        norm = email.strip().lower()
        if not norm or norm in seen:
            return
        if len(out) >= MAX_RECIPIENTS_PER_TEMPLATE:
            return
        seen.add(norm)
        out.append((user, norm))

    use_group = mode in ("group", "group_and_custom")
    use_custom = mode in ("custom", "group_and_custom")

    if use_group and group and group != "custom":
        for user in users_for_group_fn(db, group):
            email = (user.email or "").strip()
            if email:
                add_user(user, email)

    if use_custom:
        for email in custom_emails:
            add_user(None, email)

    return out
