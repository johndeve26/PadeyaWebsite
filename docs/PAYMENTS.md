# Payments

**Provider:** Paystack  
**Status:** Phase 4 commerce + Phase 10 refunds/balances/manual payouts + configurable fees / platform ledger.  
**Companions:** [FINANCE.md](./FINANCE.md) · [PAYOUTS.md](./PAYOUTS.md) · [HOST_EARNINGS.md](./HOST_EARNINGS.md)

## Critical rules

1. **Never issue tickets from frontend payment success.** Tickets are created only after a **verified Paystack webhook** (`charge.success`) is processed idempotently.
2. **Never create Ambassador commission from frontend payment success.** Conversions/sales are created only inside the same verified finalize path — [AMBASSADORS.md](./AMBASSADORS.md#payment-integration-phase-11).
3. **Support cannot modify financial records.** Support may view/escalate refunds only.
4. **Payout completion is never automatic.** Only a **super admin** may mark a payout as `paid`, and only with **immutable evidence**.
5. **Ledger entries are append-only** (host `ledger_entries` and platform `platform_ledger_entries`). Application code never updates or deletes ledger rows.
6. **Fee math is server-side.** Paystack amount must equal `order.total_amount` (includes buyer-paid fees). Fee snapshots are written **before** payment initialization.
7. **Money formulas** — Buyer total = items − discounts + buyer fees; host net deducts host-paid fees / refunds / ambassadors; platform revenue = buyer fees + host commissions + platform-owned fixed − absorbed costs. See [FINANCE.md](./FINANCE.md#canonical-money-formulas).

Free (₦0) orders are completed server-side in `POST /payments/checkout/{order_id}` using the same finalize path — still not a client “success” callback. Buyer service fees are waived by default when merchandise net is zero.

Orders may include ticket and/or event merch lines (`item_kind`). Merch inventory deducts and pickup fulfillments are created inside `finalize_successful_payment` only — see [MERCH.md](./MERCH.md). Refunds cancel unfulfilled merch; restock only when the product opts in via `restock_on_refund`.

## Configuration (admin)

Paystack keys and mode are **not** in `.env`. After deploy, open **Admin → System → Payment integration** and set test/live mode plus the matching key pair (Paystack dashboard → API Keys & Webhooks).

Boot `.env` still needs:

```
FRONTEND_URL=http://localhost:3000
QR_SIGNING_SECRET=         # optional; falls back to SECRET_KEY
EMAIL_SETTINGS_ENCRYPTION_KEY=   # if using Admin → Email settings locally
```

Email provider/SMTP: **Admin → Email settings** (not `.env`).

Webhook URL (local via tunnel):

```
POST /api/v1/payments/webhooks/paystack
```

Header: `x-paystack-signature` = HMAC-SHA512(body, webhook secret)

## Checkout flow (with fees)

1. Buyer creates order → inventory reserved (`quantity_reserved`)
2. Server applies discounts, then **configurable fees** (see [FINANCE.md](./FINANCE.md#checkout-calculation-order-default))
3. Persist `order_fee_snapshots` + order fee summary columns; `total_amount` = buyer final total
4. Checkout initializes Paystack for that amount (or free finalize)
5. Buyer pays on Paystack
6. Webhook verifies signature + amount + reference (amount must match `order.total_amount`)
7. `payment_webhook_events.event_key` ensures idempotency
8. Order → `paid`, reservations → `quantity_sold`
9. Tickets + signed QR tokens issued once
10. Host balance credited via append-only `sale_credit` for **`host_net_estimate`** (not buyer total)
11. Platform ledger rows written idempotently (`buyer_payment`, revenue, fees, …)
12. Email recorded via log provider (Admin → Email settings in dev/log mode)
13. Ambassadors: `finalize_promo_and_attribution` (v1 sales) + `finalize_ambassador_conversions` (domain) — **only here**, never from frontend success

Buyer fee preview (non-authoritative): `POST /api/v1/payments/fee-quote` (buyer-payer lines only; no host commercial terms).

Checkout may store `referral_code`, `referral_attribution_source`, `ambassador_participant_id`, and `ambassador_attribution_id` on the **pending** order. That is attribution staging only — not earnings. See [AMBASSADORS.md](./AMBASSADORS.md#payment-integration-phase-11).

## Refunds (Phase 10)

- Buyer creates `refund_requests` against a paid order (full refund only; partial is a placeholder)
- Event `refund_policy` / `refund_policy_type` types: `no_refunds`, `refund_until_7_days_before`, `refund_until_24_hours_before`, `partial_refund_only`, `cancelled_event_only`, `admin_controlled`, `custom` (custom requires `refund_policy_text`; buyer requests still go through admin review)
- Support: view + escalate (`under_review`) — **cannot approve**
- Finance admin / super admin: approve or reject
- On approval: tickets → `refunded` (QR revoked), order/payment → `refunded`, host balance debited (`refund_debit`), platform ledger `refund` (+ fee reverse adjustments on full refunds)
- Ambassadors: approved refund reverses v1 `ambassador_sales` + domain `ambassador_conversions` (`status=reversed`, audit). Ticket cancel also reverses commission for the order.

## Host balances & ledgers

- `host_balances` tracks available, pending payout, and lifetime totals
- `ledger_entries` journal host movements (`sale_credit`, `refund_debit`, `payout_hold`, `payout_release`, `payout_paid`, `vault_sale`)
- `platform_ledger_entries` journal platform payment volume, fees, refunds, payouts (unique `dedupe_key`)
- Settlement + platform revenue reports aggregate balances / ledger — [FINANCE.md](./FINANCE.md)

## Payouts (manual)

See [PAYOUTS.md](./PAYOUTS.md).

Statuses: `requested` · `under_review` · `approved` · `rejected` · `paid` · `cancelled`

1. Host requests payout → amount moved available → pending (`payout_hold`)
2. Finance admin reviews (approve / reject / under_review)
3. Reject releases hold (`payout_release`)
4. Super admin marks paid **with evidence** (`payout_evidence`): bank transfer reference, evidence file URL, paid date, paid by, recipient bank snapshot, optional admin note
5. Platform ledger records `host_payout`; paid status cannot be casually reversed

### Ambassadors rewards vs host-balance payouts

These are **different rails**:

| Rail | Who marks paid | What it means |
|---|---|---|
| Host balance `payouts` | Super admin + immutable evidence | Settles host earnings from ticket/merch/Vault sales |
| Ambassadors conversion reward | Host owner **or** permitted team member (`ambassadors.mark_rewards_paid` / `finance.manage_payouts`); admin oversight optional | Records that the host settled an Ambassador’s commission (optional `payout_reference` / `payout_note` on `ambassador_sales`) |

Host Ambassadors “mark paid” does **not** move `host_balances`, create host ledger rows, or complete a platform payout. Refunds still reverse Ambassadors commission on the verified refund path (see above). Details: [AMBASSADORS.md](./AMBASSADORS.md).

## Statuses

**Orders:** `pending` · `paid` · `failed` · `cancelled` · `refunded` · `partially_refunded`  
**Payments:** `pending` · `successful` · `failed` · `abandoned` · `refunded` · `partially_refunded` · `disputed`  
**Tickets:** `reserved` · `active` · `checked_in` · `cancelled` · `refunded` · `expired` · `transferred` · `invalid`

## Overselling

- Availability = `quantity - quantity_sold - quantity_reserved`
- Row locks (`FOR UPDATE`) during reserve / finalize
- Conflict `409` when inventory insufficient

## QR

- Public ticket code (`PDY-…`) + signed JWT payload (`typ=padeya.ticket.qr`)
- Payload includes `code`, `eid`, `jti` — **not** plain ticket UUID
- `ticket_qr_tokens` stores `jti_hash` + signed payload
- Refunded tickets have QR revoked and fail check-in

## Deferred

Live Paystack refund API · partial refunds · automatic payouts · Fan Passport payment extras beyond current commerce
