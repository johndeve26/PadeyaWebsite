"""Integer minor-unit money helpers for fee calculations.

Never use floating point for final money amounts. Prefer integer minor units
(e.g. kobo for NGN). Decimal is allowed only for percentage rates and for
converting to/from major-unit storage elsewhere in the platform.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

# ISO currencies we settle in today use 2 fractional digits.
DEFAULT_CURRENCY_EXPONENT = 2
CURRENCY_EXPONENTS: dict[str, int] = {
    "NGN": 2,
    "USD": 2,
    "GBP": 2,
    "EUR": 2,
}


def currency_exponent(currency: str) -> int:
    return CURRENCY_EXPONENTS.get(currency.upper(), DEFAULT_CURRENCY_EXPONENT)


def major_to_minor(amount: Decimal | str | int, *, currency: str = "NGN") -> int:
    """Convert a major-unit amount to integer minor units (half-up)."""
    if isinstance(amount, int):
        # Treat bare int as already-major only when it would be ambiguous —
        # callers should pass Decimal/str for major units. Int is accepted as
        # major whole units (e.g. 100 NGN → 10000 kobo).
        amount_dec = Decimal(amount)
    else:
        amount_dec = Decimal(str(amount))
    exp = currency_exponent(currency)
    scale = Decimal(10) ** exp
    return int((amount_dec * scale).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def minor_to_major(amount_minor: int, *, currency: str = "NGN") -> Decimal:
    """Convert integer minor units to a quantized major-unit Decimal."""
    exp = currency_exponent(currency)
    scale = Decimal(10) ** exp
    quant = Decimal(10) ** -exp
    return (Decimal(amount_minor) / scale).quantize(quant, rounding=ROUND_HALF_UP)


def apply_percentage(base_minor: int, percentage: Decimal | str | None) -> int:
    """Return `percentage`% of `base_minor` as an integer (half-up).

    `percentage` is a human rate (e.g. Decimal("5.25") for 5.25%), never a float.
    """
    if percentage is None:
        return 0
    pct = Decimal(str(percentage))
    if pct == 0 or base_minor == 0:
        return 0
    raw = Decimal(base_minor) * pct / Decimal(100)
    return int(raw.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def sum_minor(*amounts: int) -> int:
    """Sum integer minor amounts without float intermediate."""
    total = 0
    for value in amounts:
        total += int(value)
    return total
