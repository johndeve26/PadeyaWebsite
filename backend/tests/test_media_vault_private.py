"""Vault must never land private files on public padeya-media."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.hosts.models import Host, HostProfile
from app.users.models import User
from app.users.service import get_role_by_name
from app.vault.models import VaultItem
from app.vault.schemas import VaultMediaInput
from app.vault.service import _attach_media, _validate_vault_file_url


def _host_item(db: Session) -> VaultItem:
    user = User(
        email=f"vault-media-{uuid4().hex[:8]}@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Vault Host",
        is_active=True,
    )
    user.roles.append(get_role_by_name(db, "host"))
    db.add(user)
    db.flush()
    host = Host(
        user_id=user.id,
        display_name="Vault Host",
        slug=f"vault-host-{uuid4().hex[:6]}",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, bio="x"))
    item = VaultItem(
        host_id=host.id,
        title="Private Drop",
        slug=f"drop-{uuid4().hex[:6]}",
        content_type="file",
        status="draft",
        price=Decimal("0"),
        currency="NGN",
        published_at=None,
        created_at=datetime.now(UTC),
    )
    db.add(item)
    db.flush()
    return item


def test_vault_file_url_rejects_public_cdn():
    with pytest.raises(HTTPException) as exc:
        _validate_vault_file_url("https://media.padeya.com/hosts/x/file.pdf")
    assert exc.value.status_code == 400


def test_vault_attach_rejects_public_url_for_non_preview(db_session: Session):
    item = _host_item(db_session)
    media = [
        VaultMediaInput(
            media_type="file",
            url="https://media.padeya.com/vault/secret.webp",
            is_preview=False,
        )
    ]
    with pytest.raises(HTTPException) as exc:
        _attach_media(db_session, item, media)
    assert exc.value.status_code == 400
    assert "public media" in str(exc.value.detail).lower()


def test_vault_attach_uses_private_key_not_public_url(db_session: Session):
    item = _host_item(db_session)
    media = [
        VaultMediaInput(
            media_type="file",
            filename="secret.pdf",
            url="private://pending",
            is_preview=False,
        )
    ]
    _attach_media(db_session, item, media)
    db_session.flush()
    row = item.media[0]
    assert row.storage_key
    assert row.storage_key.startswith("vault/")
    assert "media.padeya.com" not in (row.url or "")
    assert not (row.url or "").startswith("/media/")
