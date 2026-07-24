"""Fee resolution and integer-minor-unit calculation services."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.finance.fees.constants import (
    DEFAULT_FEE_CATEGORIES,
    DEFAULT_FEE_LABELS,
    MERCH_FEE_KEYS,
    TICKET_FEE_KEYS,
    VAULT_FEE_KEYS,
)
from app.finance.fees.fee_settings_service import FeeSettingsService
from app.finance.fees.host_fee_override_service import HostFeeOverrideService
from app.finance.fees.models import HostFeeOverride, OrderFeeSnapshot, PlatformFeeSetting
from app.finance.fees.money import apply_percentage, sum_minor
from app.finance.fees.schemas import (
    CalculatedFeeLine,
    FeeBreakdown,
    ResolvedFeeSetting,
)


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _now() -> datetime:
    return datetime.now(UTC)


def _infer_fee_type(
    percentage_value: Decimal | None,
    fixed_value: int | None,
) -> str:
    has_pct = percentage_value is not None
    has_fixed = fixed_value is not None
    if has_pct and has_fixed:
        return "mixed"
    if has_fixed:
        return "fixed"
    return "percentage"


def _compute_line_amount(
    *,
    base_minor: int,
    fee_type: str,
    percentage_value: Decimal | None,
    fixed_value: int | None,
) -> int:
    pct_part = 0
    fixed_part = 0
    if fee_type in {"percentage", "mixed"}:
        pct_part = apply_percentage(base_minor, percentage_value)
    if fee_type in {"fixed", "mixed"}:
        fixed_part = int(fixed_value or 0)
    return sum_minor(pct_part, fixed_part)


class FeeCalculationService:
    """Resolve active fees and compute buyer/host amounts in minor units."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = FeeSettingsService(db)
        self.overrides = HostFeeOverrideService(db)

    def get_active_fee_settings(
        self,
        host_id: UUID | None,
        category: str | None = None,
        *,
        at: datetime | None = None,
        fee_keys: list[str] | tuple[str, ...] | None = None,
    ) -> list[ResolvedFeeSetting]:
        """Return resolved fees for category; host override beats global."""
        moment = _aware(at or _now())
        keys = list(fee_keys) if fee_keys is not None else None
        globals_ = self.settings.get_active_global_settings(
            category=category if keys is None else None,
            at=moment,
            fee_keys=keys,
        )
        # When fee_keys filter is used, also include globals that match keys
        # even if category differs (e.g. buyer_service_fee is "general").
        if keys is not None and category is not None:
            extra = self.settings.get_active_global_settings(at=moment, fee_keys=keys)
            by_id = {g.id: g for g in globals_}
            for row in extra:
                by_id.setdefault(row.id, row)
            globals_ = list(by_id.values())

        override_map: dict[str, HostFeeOverride] = {}
        if host_id is not None:
            override_map = self.overrides.get_active_overrides(
                host_id, at=moment, fee_keys=keys
            )

        resolved: dict[str, ResolvedFeeSetting] = {}
        for row in globals_:
            if keys is not None and row.fee_key not in keys:
                continue
            if category is not None and keys is None and row.category != category:
                continue
            resolved[row.fee_key] = self._from_global(row)

        for fee_key, override in override_map.items():
            if keys is not None and fee_key not in keys:
                continue
            base = resolved.get(fee_key)
            label = base.label if base else DEFAULT_FEE_LABELS.get(fee_key, fee_key)
            cat = base.category if base else DEFAULT_FEE_CATEGORIES.get(fee_key, "general")
            currency = base.currency if base else "NGN"
            applies_to = base.applies_to if base else "all"
            pct = override.percentage_value
            fixed = override.fixed_value
            if base is not None:
                if pct is None:
                    pct = base.percentage_value
                if fixed is None:
                    fixed = base.fixed_value
            resolved[fee_key] = ResolvedFeeSetting(
                fee_key=fee_key,
                label=label,
                category=cat,
                fee_type=_infer_fee_type(pct, fixed),
                percentage_value=pct,
                fixed_value=fixed,
                currency=currency,
                payer=override.payer,
                enabled=True,
                applies_to=applies_to,
                source="host_override",
                setting_id=base.setting_id if base else None,
                override_id=override.id,
            )

        return sorted(resolved.values(), key=lambda r: r.fee_key)

    def _from_global(self, row: PlatformFeeSetting) -> ResolvedFeeSetting:
        return ResolvedFeeSetting(
            fee_key=row.fee_key,
            label=row.label,
            category=row.category,
            fee_type=row.fee_type,
            percentage_value=row.percentage_value,
            fixed_value=row.fixed_value,
            currency=row.currency,
            payer=row.payer,
            enabled=row.enabled,
            applies_to=row.applies_to,
            source="global",
            setting_id=row.id,
            override_id=None,
        )

    def _calculate_for_keys(
        self,
        *,
        base_amount_minor: int,
        host_id: UUID | None,
        fee_keys: tuple[str, ...] | list[str],
        currency: str = "NGN",
        at: datetime | None = None,
        # Optional ambassador deduction awareness (later payouts phase).
        ambassador_deduction_minor: int = 0,
    ) -> FeeBreakdown:
        if base_amount_minor < 0:
            raise ValueError("base_amount_minor must be >= 0")
        if ambassador_deduction_minor < 0:
            raise ValueError("ambassador_deduction_minor must be >= 0")

        settings = self.get_active_fee_settings(
            host_id, category=None, at=at, fee_keys=list(fee_keys)
        )
        lines: list[CalculatedFeeLine] = []
        buyer_fees = 0
        host_fees = 0
        platform_absorbed = 0

        for setting in settings:
            if not setting.enabled:
                continue
            amount = _compute_line_amount(
                base_minor=base_amount_minor,
                fee_type=setting.fee_type,
                percentage_value=setting.percentage_value,
                fixed_value=setting.fixed_value,
            )
            if amount == 0 and setting.fee_type != "fixed":
                # Still snapshot zero percentage lines? Skip empty.
                if setting.percentage_value in (None, Decimal("0"), Decimal("0.0")):
                    if setting.fixed_value in (None, 0):
                        continue
            line = CalculatedFeeLine(
                fee_key=setting.fee_key,
                label=setting.label,
                category=setting.category,
                fee_type=setting.fee_type,
                percentage_value=setting.percentage_value,
                fixed_value=setting.fixed_value,
                payer=setting.payer,
                amount_minor=amount,
                currency=setting.currency or currency,
                source=setting.source,
            )
            lines.append(line)
            if setting.payer == "buyer":
                buyer_fees = sum_minor(buyer_fees, amount)
            elif setting.payer == "host":
                host_fees = sum_minor(host_fees, amount)
            else:
                platform_absorbed = sum_minor(platform_absorbed, amount)

        buyer_total = sum_minor(base_amount_minor, buyer_fees)
        host_net = sum_minor(base_amount_minor, -host_fees, -ambassador_deduction_minor)
        if host_net < 0:
            host_net = 0

        return FeeBreakdown(
            currency=currency,
            base_amount_minor=base_amount_minor,
            lines=lines,
            buyer_fees_minor=buyer_fees,
            host_fees_minor=host_fees,
            platform_absorbed_minor=platform_absorbed,
            buyer_total_minor=buyer_total,
            host_net_minor=host_net,
        )

    def calculate_ticket_fees(
        self,
        *,
        ticket_subtotal_minor: int,
        host_id: UUID | None,
        currency: str = "NGN",
        at: datetime | None = None,
        ambassador_deduction_minor: int = 0,
    ) -> FeeBreakdown:
        return self._calculate_for_keys(
            base_amount_minor=ticket_subtotal_minor,
            host_id=host_id,
            fee_keys=TICKET_FEE_KEYS,
            currency=currency,
            at=at,
            ambassador_deduction_minor=ambassador_deduction_minor,
        )

    def calculate_merch_fees(
        self,
        *,
        merch_subtotal_minor: int,
        host_id: UUID | None,
        currency: str = "NGN",
        at: datetime | None = None,
        ambassador_deduction_minor: int = 0,
    ) -> FeeBreakdown:
        return self._calculate_for_keys(
            base_amount_minor=merch_subtotal_minor,
            host_id=host_id,
            fee_keys=MERCH_FEE_KEYS,
            currency=currency,
            at=at,
            ambassador_deduction_minor=ambassador_deduction_minor,
        )

    def calculate_vault_fees(
        self,
        *,
        vault_subtotal_minor: int,
        host_id: UUID | None,
        currency: str = "NGN",
        at: datetime | None = None,
        ambassador_deduction_minor: int = 0,
    ) -> FeeBreakdown:
        return self._calculate_for_keys(
            base_amount_minor=vault_subtotal_minor,
            host_id=host_id,
            fee_keys=VAULT_FEE_KEYS,
            currency=currency,
            at=at,
            ambassador_deduction_minor=ambassador_deduction_minor,
        )

    def calculate_buyer_total(
        self,
        *,
        base_amount_minor: int,
        calculated_fees: FeeBreakdown | list[CalculatedFeeLine],
    ) -> int:
        """Buyer pays base + buyer-payer fees (platform absorbs / host fees excluded)."""
        if isinstance(calculated_fees, FeeBreakdown):
            return calculated_fees.buyer_total_minor
        buyer_fees = 0
        for line in calculated_fees:
            if line.payer == "buyer":
                buyer_fees = sum_minor(buyer_fees, line.amount_minor)
        return sum_minor(base_amount_minor, buyer_fees)

    def calculate_host_net_earnings(
        self,
        *,
        base_amount_minor: int,
        calculated_fees: FeeBreakdown | list[CalculatedFeeLine],
        ambassador_deduction_minor: int = 0,
    ) -> int:
        """Host net = base − host-payer fees − optional ambassador deduction."""
        if ambassador_deduction_minor < 0:
            raise ValueError("ambassador_deduction_minor must be >= 0")
        if isinstance(calculated_fees, FeeBreakdown):
            host_fees = calculated_fees.host_fees_minor
        else:
            host_fees = 0
            for line in calculated_fees:
                if line.payer == "host":
                    host_fees = sum_minor(host_fees, line.amount_minor)
        net = sum_minor(base_amount_minor, -host_fees, -ambassador_deduction_minor)
        return net if net > 0 else 0

    def create_order_fee_snapshot(
        self,
        order_id: UUID,
        calculated_fees: FeeBreakdown | list[CalculatedFeeLine],
        *,
        host_id: UUID | None = None,
    ) -> list[OrderFeeSnapshot]:
        """Persist immutable fee lines for an order. Idempotent per (order, fee_key)."""
        lines = (
            calculated_fees.lines
            if isinstance(calculated_fees, FeeBreakdown)
            else list(calculated_fees)
        )
        existing = {
            row.fee_key: row
            for row in self.db.scalars(
                select(OrderFeeSnapshot).where(OrderFeeSnapshot.order_id == order_id)
            ).all()
        }
        created: list[OrderFeeSnapshot] = []
        for line in lines:
            if line.fee_key in existing:
                created.append(existing[line.fee_key])
                continue
            snap = OrderFeeSnapshot(
                order_id=order_id,
                host_id=host_id,
                fee_key=line.fee_key,
                label=line.label,
                category=line.category,
                fee_type=line.fee_type,
                percentage_value=line.percentage_value,
                fixed_value=line.fixed_value,
                payer=line.payer,
                amount=line.amount_minor,
                currency=line.currency,
                source=line.source,
            )
            self.db.add(snap)
            created.append(snap)
        self.db.flush()
        return created

    def list_order_fee_snapshots(self, order_id: UUID) -> list[OrderFeeSnapshot]:
        return list(
            self.db.scalars(
                select(OrderFeeSnapshot)
                .where(OrderFeeSnapshot.order_id == order_id)
                .order_by(OrderFeeSnapshot.created_at.asc())
            ).all()
        )


# Module-level helpers matching the requested function names.


def get_active_fee_settings(
    db: Session,
    host_id: UUID | None,
    category: str | None,
    *,
    at: datetime | None = None,
) -> list[ResolvedFeeSetting]:
    return FeeCalculationService(db).get_active_fee_settings(
        host_id, category, at=at
    )


def calculate_ticket_fees(
    db: Session,
    *,
    ticket_subtotal_minor: int,
    host_id: UUID | None,
    currency: str = "NGN",
    at: datetime | None = None,
    ambassador_deduction_minor: int = 0,
) -> FeeBreakdown:
    return FeeCalculationService(db).calculate_ticket_fees(
        ticket_subtotal_minor=ticket_subtotal_minor,
        host_id=host_id,
        currency=currency,
        at=at,
        ambassador_deduction_minor=ambassador_deduction_minor,
    )


def calculate_merch_fees(
    db: Session,
    *,
    merch_subtotal_minor: int,
    host_id: UUID | None,
    currency: str = "NGN",
    at: datetime | None = None,
    ambassador_deduction_minor: int = 0,
) -> FeeBreakdown:
    return FeeCalculationService(db).calculate_merch_fees(
        merch_subtotal_minor=merch_subtotal_minor,
        host_id=host_id,
        currency=currency,
        at=at,
        ambassador_deduction_minor=ambassador_deduction_minor,
    )


def calculate_vault_fees(
    db: Session,
    *,
    vault_subtotal_minor: int,
    host_id: UUID | None,
    currency: str = "NGN",
    at: datetime | None = None,
    ambassador_deduction_minor: int = 0,
) -> FeeBreakdown:
    return FeeCalculationService(db).calculate_vault_fees(
        vault_subtotal_minor=vault_subtotal_minor,
        host_id=host_id,
        currency=currency,
        at=at,
        ambassador_deduction_minor=ambassador_deduction_minor,
    )


def create_order_fee_snapshot(
    db: Session,
    order_id: UUID,
    calculated_fees: FeeBreakdown | list[CalculatedFeeLine],
    *,
    host_id: UUID | None = None,
) -> list[OrderFeeSnapshot]:
    return FeeCalculationService(db).create_order_fee_snapshot(
        order_id, calculated_fees, host_id=host_id
    )


def calculate_buyer_total(
    *,
    base_amount_minor: int,
    calculated_fees: FeeBreakdown | list[CalculatedFeeLine],
) -> int:
    if isinstance(calculated_fees, FeeBreakdown):
        return calculated_fees.buyer_total_minor
    buyer_fees = 0
    for line in calculated_fees:
        if line.payer == "buyer":
            buyer_fees = sum_minor(buyer_fees, line.amount_minor)
    return sum_minor(base_amount_minor, buyer_fees)


def calculate_host_net_earnings(
    *,
    base_amount_minor: int,
    calculated_fees: FeeBreakdown | list[CalculatedFeeLine],
    ambassador_deduction_minor: int = 0,
) -> int:
    if ambassador_deduction_minor < 0:
        raise ValueError("ambassador_deduction_minor must be >= 0")
    if isinstance(calculated_fees, FeeBreakdown):
        host_fees = calculated_fees.host_fees_minor
    else:
        host_fees = 0
        for line in calculated_fees:
            if line.payer == "host":
                host_fees = sum_minor(host_fees, line.amount_minor)
    net = sum_minor(base_amount_minor, -host_fees, -ambassador_deduction_minor)
    return net if net > 0 else 0
