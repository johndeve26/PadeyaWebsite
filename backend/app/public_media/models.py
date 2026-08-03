"""Normalized public media asset + variant rows."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.database import Base


class PublicMediaAsset(Base):
    __tablename__ = "public_media_assets"
    __table_args__ = (
        Index("ix_public_media_assets_owner", "owner_type", "owner_id"),
        Index("ix_public_media_assets_role_status", "media_role", "processing_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    media_role: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # Controlled source key — never expose in public API responses.
    source_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_mime: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_byte_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    alt_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    focal_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    focal_y: Mapped[float | None] = mapped_column(Float, nullable=True)
    processing_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="ready", index=True
    )
    processing_version: Mapped[str] = mapped_column(
        String(16), nullable=False, default="v1"
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    replaced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    variants: Mapped[list[PublicMediaVariant]] = relationship(
        "PublicMediaVariant",
        back_populates="asset",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class PublicMediaVariant(Base):
    __tablename__ = "public_media_variants"
    __table_args__ = (
        UniqueConstraint(
            "asset_id", "variant_type", name="uq_public_media_variants_asset_type"
        ),
        Index("ix_public_media_variants_asset", "asset_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("public_media_assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    variant_type: Mapped[str] = mapped_column(String(32), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    public_url: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(64), nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    byte_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    quality: Mapped[int | None] = mapped_column(Integer, nullable=True)
    processing_version: Mapped[str] = mapped_column(
        String(16), nullable=False, default="v1"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    asset: Mapped[PublicMediaAsset] = relationship(
        "PublicMediaAsset", back_populates="variants"
    )
