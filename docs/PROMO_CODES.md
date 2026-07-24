# Promo codes (ticket discounts)

Brand: **Pàdéyá**. Host-owned **buyer discount** codes for ticket lines.

This is **not** Ambassadors referral. For open promotion / commission, see [AMBASSADORS.md](./AMBASSADORS.md).

Related: [API.md](./API.md#promos--ambassadors-legacy-phase-8-promos) · [DATABASE.md](./DATABASE.md#promos--ambassadors-phase-8--open-event-ambassadors) · [PAYMENTS.md](./PAYMENTS.md) · [MERCHANDISE.md](./MERCHANDISE.md) (merch discounts are separate)

## What it is

| Concept | Table / field | Purpose |
|---|---|---|
| Ticket promo code | `promo_codes` | Percentage or fixed discount on **ticket** lines |
| Redemption | `promo_redemptions` | Pending → redeemed on paid finalize; released on cancel |
| Order snapshot | `orders.promo_code_id` / `promo_code_snapshot` / `discount_amount` | Immutable at checkout |

Hosts manage codes at `/host/promos` (`GET/POST /api/v1/promos/codes`).

## Rules

- Validated and discounted **only on the backend** at order create — never trust the browser.
- Applies to **ticket lines only**. Merch-only carts reject ticket promo codes.
- Merch uses a separate system: `merch_discount_codes` ([MERCHANDISE.md](./MERCHANDISE.md)).
- Usage commits on verified payment finalize (same webhook path as tickets).
- Limits: usage cap, max per user, expiry, optional event/ticket-type restrictions.

## Ambassadors vs promo codes

| | Ticket promo codes | Ambassadors referral |
|---|---|---|
| Who benefits | Buyer (discount) | Promoter (commission / reward) |
| Checkout field | `promo_code` | `referral_code` (+ optional attribution id) |
| Creates | Order discount | Attribution → conversion after **paid** webhook |
| Uniqueness | Per host code | Per campaign ambassador code |
| Docs | This file | [AMBASSADORS.md](./AMBASSADORS.md) |

An order may carry both a ticket promo **and** an Ambassador referral — they do not replace each other.
