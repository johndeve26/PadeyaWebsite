"""Host saved bank account lifecycle — archive only, never hard-delete."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.core.sensitive import account_last4, encrypt_sensitive
from app.hosts.lifecycle_schemas import HostBankAccountCreate, HostBankAccountUpdate
from app.hosts.models import HostBankAccount
from app.hosts.team_access import require_host_for_permission
from app.users.models import User
from app.auth.verified_email import assert_verified_email


def list_bank_accounts(
    db: Session, *, user: User, include_archived: bool = False
) -> list[HostBankAccount]:
    host, _ = require_host_for_permission(
        db, user=user, host_id=None, permission="finance.manage_payout_settings"
    )
    q = select(HostBankAccount).where(HostBankAccount.host_id == host.id)
    if not include_archived:
        q = q.where(HostBankAccount.archived_at.is_(None))
    return list(db.scalars(q.order_by(HostBankAccount.created_at.desc())))


def get_bank_account(db: Session, *, user: User, account_id: uuid.UUID) -> HostBankAccount:
    host, _ = require_host_for_permission(
        db, user=user, host_id=None, permission="finance.manage_payout_settings"
    )
    row = db.get(HostBankAccount, account_id)
    if row is None or row.host_id != host.id:
        raise HTTPException(status_code=404, detail="Bank account not found")
    return row


def _clear_default(db: Session, host_id: uuid.UUID) -> None:
    db.execute(
        update(HostBankAccount)
        .where(HostBankAccount.host_id == host_id, HostBankAccount.is_default.is_(True))
        .values(is_default=False)
    )


def create_bank_account(
    db: Session, *, user: User, payload: HostBankAccountCreate
) -> HostBankAccount:
    assert_verified_email(user)
    host, _ = require_host_for_permission(
        db, user=user, host_id=None, permission="finance.manage_payout_settings"
    )
    try:
        last4 = account_last4(payload.account_number)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if payload.is_default:
        _clear_default(db, host.id)

    row = HostBankAccount(
        host_id=host.id,
        label=payload.label.strip(),
        bank_name=payload.bank_name.strip(),
        account_name=payload.account_name.strip(),
        account_number_last4=last4,
        account_number_encrypted=encrypt_sensitive(payload.account_number.strip()),
        currency=payload.currency.upper(),
        status="active",
        is_default=payload.is_default,
        created_by=user.id,
        updated_by=user.id,
    )
    db.add(row)
    db.flush()
    write_audit_log(
        db,
        action="hosts.bank_create",
        actor_user_id=user.id,
        resource_type="host_bank_account",
        resource_id=str(row.id),
        details={"last4": last4, "bank_name": row.bank_name},
    )
    db.commit()
    db.refresh(row)
    return row


def update_bank_account(
    db: Session, *, user: User, account_id: uuid.UUID, payload: HostBankAccountUpdate
) -> HostBankAccount:
    assert_verified_email(user)
    row = get_bank_account(db, user=user, account_id=account_id)
    if row.archived_at is not None:
        raise HTTPException(status_code=400, detail="Restore account before updating")
    data = payload.model_dump(exclude_unset=True)
    if "account_number" in data and data["account_number"]:
        try:
            last4 = account_last4(data["account_number"])
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        row.account_number_last4 = last4
        row.account_number_encrypted = encrypt_sensitive(data["account_number"].strip())
        data.pop("account_number")
        data["account_number_last4"] = last4
    for field in ("label", "bank_name", "account_name"):
        if field in data and data[field] is not None:
            setattr(row, field, data[field].strip())
    if "currency" in data and data["currency"] is not None:
        row.currency = data["currency"].upper()
    if data.get("is_default") is True:
        _clear_default(db, row.host_id)
        row.is_default = True
    elif data.get("is_default") is False:
        row.is_default = False
    row.updated_by = user.id
    write_audit_log(
        db,
        action="hosts.bank_update",
        actor_user_id=user.id,
        resource_type="host_bank_account",
        resource_id=str(row.id),
        details={k: v for k, v in data.items() if k != "account_number"},
    )
    db.commit()
    db.refresh(row)
    return row


def archive_bank_account(
    db: Session, *, user: User, account_id: uuid.UUID
) -> HostBankAccount:
    row = get_bank_account(db, user=user, account_id=account_id)
    if row.archived_at is not None:
        return row
    row.status = "archived"
    row.is_default = False
    row.archived_at = datetime.now(UTC)
    row.archived_by = user.id
    row.updated_by = user.id
    write_audit_log(
        db,
        action="hosts.bank_archive",
        actor_user_id=user.id,
        resource_type="host_bank_account",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    return row


def restore_bank_account(
    db: Session, *, user: User, account_id: uuid.UUID
) -> HostBankAccount:
    row = get_bank_account(db, user=user, account_id=account_id)
    row.status = "active"
    row.archived_at = None
    row.archived_by = None
    row.updated_by = user.id
    write_audit_log(
        db,
        action="hosts.bank_restore",
        actor_user_id=user.id,
        resource_type="host_bank_account",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    return row


def delete_bank_account_blocked() -> None:
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail="Hard delete blocked for bank accounts; use POST .../archive",
    )
