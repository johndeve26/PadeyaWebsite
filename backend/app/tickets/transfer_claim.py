"""Pending ticket transfer claim tokens (recipient without account yet)."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_token
from app.tickets.advanced_models import TicketTransfer

TRANSFER_CLAIM_TTL_HOURS = 72


def issue_transfer_claim_token(db: Session, transfer: TicketTransfer) -> str:
    raw = secrets.token_urlsafe(32)
    transfer.claim_token_hash = hash_token(raw)
    transfer.claim_token_expires_at = datetime.now(UTC) + timedelta(
        hours=TRANSFER_CLAIM_TTL_HOURS
    )
    db.flush()
    return raw


def find_pending_transfer_by_claim_token(
    db: Session, raw_token: str
) -> TicketTransfer | None:
    token_hash = hash_token(raw_token.strip())
    transfer = db.scalar(
        select(TicketTransfer).where(
            TicketTransfer.claim_token_hash == token_hash,
            TicketTransfer.status == "pending",
        )
    )
    if transfer is None:
        return None
    expires = transfer.claim_token_expires_at
    if expires is None:
        return None
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if expires < datetime.now(UTC):
        return None
    return transfer
