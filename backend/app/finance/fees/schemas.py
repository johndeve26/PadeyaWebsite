"""Pydantic schemas for fee settings, overrides, and snapshots."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.finance.fees.constants import FEE_CATEGORIES, FEE_PAYERS, FEE_TYPES


class PlatformFeeSettingCreate(BaseModel):
    fee_key: str = Field(min_length=2, max_length=64)
    label: str = Field(min_length=1, max_length=200)
    category: str
    fee_type: str
    percentage_value: Decimal | None = None
    fixed_value: int | None = Field(default=None, ge=0)
    currency: str = Field(default="NGN", min_length=3, max_length=8)
    payer: str
    enabled: bool = True
    applies_to: str = Field(default="all", max_length=128)
    notes: str | None = Field(default=None, max_length=2000)
    effective_from: datetime
    effective_to: datetime | None = None

    @field_validator("category")
    @classmethod
    def valid_category(cls, value: str) -> str:
        if value not in FEE_CATEGORIES:
            raise ValueError(f"category must be one of {FEE_CATEGORIES}")
        return value

    @field_validator("fee_type")
    @classmethod
    def valid_fee_type(cls, value: str) -> str:
        if value not in FEE_TYPES:
            raise ValueError(f"fee_type must be one of {FEE_TYPES}")
        return value

    @field_validator("payer")
    @classmethod
    def valid_payer(cls, value: str) -> str:
        if value not in FEE_PAYERS:
            raise ValueError(f"payer must be one of {FEE_PAYERS}")
        return value

    @model_validator(mode="after")
    def validate_values(self) -> PlatformFeeSettingCreate:
        if self.fee_type == "percentage" and self.percentage_value is None:
            raise ValueError("percentage_value required for percentage fee_type")
        if self.fee_type == "fixed" and self.fixed_value is None:
            raise ValueError("fixed_value required for fixed fee_type")
        if self.fee_type == "mixed" and (
            self.percentage_value is None or self.fixed_value is None
        ):
            raise ValueError("mixed fee_type requires percentage_value and fixed_value")
        if self.effective_to is not None and self.effective_to <= self.effective_from:
            raise ValueError("effective_to must be after effective_from")
        return self


class PlatformFeeSettingUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=200)
    fee_type: str | None = None
    percentage_value: Decimal | None = None
    fixed_value: int | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=8)
    payer: str | None = None
    enabled: bool | None = None
    applies_to: str | None = Field(default=None, max_length=128)
    notes: str | None = Field(default=None, max_length=2000)
    effective_from: datetime | None = None
    effective_to: datetime | None = None

    @field_validator("fee_type")
    @classmethod
    def valid_fee_type(cls, value: str | None) -> str | None:
        if value is not None and value not in FEE_TYPES:
            raise ValueError(f"fee_type must be one of {FEE_TYPES}")
        return value

    @field_validator("payer")
    @classmethod
    def valid_payer(cls, value: str | None) -> str | None:
        if value is not None and value not in FEE_PAYERS:
            raise ValueError(f"payer must be one of {FEE_PAYERS}")
        return value


class PlatformFeeSettingPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    fee_key: str
    label: str
    category: str
    fee_type: str
    percentage_value: Decimal | None
    fixed_value: int | None
    currency: str
    payer: str
    enabled: bool
    applies_to: str
    notes: str | None = None
    effective_from: datetime
    effective_to: datetime | None
    created_by_admin_id: UUID | None
    updated_by_admin_id: UUID | None
    created_at: datetime
    updated_at: datetime


class HostFeeOverrideCreate(BaseModel):
    host_id: UUID
    fee_key: str = Field(min_length=2, max_length=64)
    percentage_value: Decimal | None = None
    fixed_value: int | None = Field(default=None, ge=0)
    payer: str
    enabled: bool = True
    effective_from: datetime
    effective_to: datetime | None = None
    reason: str | None = Field(default=None, max_length=2000)

    @field_validator("payer")
    @classmethod
    def valid_payer(cls, value: str) -> str:
        if value not in FEE_PAYERS:
            raise ValueError(f"payer must be one of {FEE_PAYERS}")
        return value

    @model_validator(mode="after")
    def validate_dates(self) -> HostFeeOverrideCreate:
        if self.effective_to is not None and self.effective_to <= self.effective_from:
            raise ValueError("effective_to must be after effective_from")
        if self.percentage_value is None and self.fixed_value is None:
            raise ValueError("override requires percentage_value and/or fixed_value")
        return self


class HostFeeOverrideUpdate(BaseModel):
    percentage_value: Decimal | None = None
    fixed_value: int | None = Field(default=None, ge=0)
    payer: str | None = None
    enabled: bool | None = None
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    reason: str | None = Field(default=None, max_length=2000)

    @field_validator("payer")
    @classmethod
    def valid_payer(cls, value: str | None) -> str | None:
        if value is not None and value not in FEE_PAYERS:
            raise ValueError(f"payer must be one of {FEE_PAYERS}")
        return value


class HostFeeOverridePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    host_id: UUID
    fee_key: str
    percentage_value: Decimal | None
    fixed_value: int | None
    payer: str
    enabled: bool
    effective_from: datetime
    effective_to: datetime | None
    reason: str | None
    created_by_admin_id: UUID | None
    updated_by_admin_id: UUID | None
    created_at: datetime
    updated_at: datetime


class OrderFeeSnapshotPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_id: UUID
    host_id: UUID | None
    fee_key: str
    label: str
    category: str
    fee_type: str
    percentage_value: Decimal | None
    fixed_value: int | None
    payer: str
    amount: int
    currency: str
    source: str
    created_at: datetime


class ResolvedFeeSetting(BaseModel):
    """Merged global + host-override view used by calculation."""

    fee_key: str
    label: str
    category: str
    fee_type: str
    percentage_value: Decimal | None
    fixed_value: int | None
    currency: str
    payer: str
    enabled: bool
    applies_to: str
    source: str
    setting_id: UUID | None = None
    override_id: UUID | None = None


class CalculatedFeeLine(BaseModel):
    fee_key: str
    label: str
    category: str
    fee_type: str
    percentage_value: Decimal | None
    fixed_value: int | None
    payer: str
    amount_minor: int
    currency: str
    source: str


class FeeBreakdown(BaseModel):
    currency: str
    base_amount_minor: int
    lines: list[CalculatedFeeLine]
    buyer_fees_minor: int
    host_fees_minor: int
    platform_absorbed_minor: int
    buyer_total_minor: int
    host_net_minor: int
