# Finance

**Brand:** Pàdéyá  
**Scope:** Configurable fees, checkout snapshots, host earnings, platform ledger, refunds, and manual payouts.  
**Companions:** [PAYMENTS.md](./PAYMENTS.md) · [PAYOUTS.md](./PAYOUTS.md) · [HOST_EARNINGS.md](./HOST_EARNINGS.md) · [CRUD_MATRIX.md](./CRUD_MATRIX.md) · [API.md](./API.md) · [DATABASE.md](./DATABASE.md) · [SECURITY.md](./SECURITY.md)

## Product rules (invariants)

1. **Server is the source of truth** for money. Frontend fee quotes are previews only.
2. **Buyer-paid fees** increase the buyer total and belong to **platform revenue** — they never inflate host gross.
3. **Host-paid fees** (commissions / fixed product fees) are deducted from **host net** — they are not shown as buyer fees at checkout.
4. **Fee snapshots** are immutable. Admin rate changes do not rewrite past orders.
5. **Host ledger** (`ledger_entries`) and **platform ledger** (`platform_ledger_entries`) are append-only. Corrections use new adjustment / reversal rows.
6. **Tickets / merch / Vault entitlements** issue only after verified payment finalize (webhook or free-order server path).
7. **Support cannot** approve refunds, review payouts, mark payouts paid, manage fees, or read platform/host finance ledgers.

## Platform revenue streams

| Stream | Who pays | Ledger / order fields | Notes |
| --- | --- | --- | --- |
| Ticket commission | Host | `host_commission` (category `ticket`) · `orders.host_fee_total` | % and/or fixed on post-discount ticket net |
| Merch commission | Host | `host_commission` (category `merch`) | Same pattern on merch net |
| Vault commission | Host | `host_commission` (category `vault`) | Vault unlock checkout |
| Buyer platform / service fee | Buyer | `buyer_platform_fee` · `orders.buyer_fee_total` | Default payer = buyer |
| Payment processing fee | Buyer (default) or host if configured | `processing_fee` · `orders.processing_fee_total` | Calculated after service fee when buyer-paid |
| Gross payment volume | Buyer | `buyer_payment` | Equals verified Paystack / free-order total |

**Platform revenue** uses the [canonical formula](#canonical-money-formulas) below. Reports also subtract fee reversals on full refunds.

## Buyer-paid vs host-paid fees

| Payer | Effect on buyer checkout | Effect on host earnings |
| --- | --- | --- |
| **Buyer** | Added to final total; shown in buyer fee breakdown | Not included in host gross |
| **Host** | Hidden from buyer checkout | Deducted from host net |
| **Platform** (absorbed) | Not charged to buyer | Does not credit host |

Help copy (admin + host):

- “Buyer platform fee is paid by the buyer.”
- “Host commission is deducted from host earnings.”
- “Fee settings can differ by host.”
- “Order fee snapshots preserve the fee terms used at the time of sale.”

## Fee settings & host overrides

| Resource | Table | Who manages |
| --- | --- | --- |
| Global schedule | `platform_fee_settings` | Finance admin (`admin.finance.manage_fees`) |
| Per-host override | `host_fee_overrides` | Finance admin (`admin.finance.manage_host_overrides`) |
| Immutable sale lines | `order_fee_snapshots` | System at order create (before Paystack init) |

**Resolution:** enabled host override in effective window **beats** matching global setting. Disabled / out-of-window overrides are ignored.

**Admin UI:** `/admin/finance/fees`, `/admin/finance/host-overrides`, `/admin/hosts/[hostId]/fees`  
**Preview:** admin fee calculator mirrors checkout math (not a payment API).

## Canonical money formulas

These are the product source of truth for checkout, earnings, and platform reporting.

### Buyer total

```
Buyer total =
  item subtotal
  − discounts
  + buyer platform/service fees
  + buyer-paid processing fees
```

Shipping (when charged) is added to the buyer total with merchandise. Paystack amount **must** equal this total (`order.total_amount` / `final_total`).

Buyer fees never inflate host gross. Buyer checkout shows **buyer-payer lines only**.

### Host net

```
Host net =
  item subtotal
  − discounts
  − host commission
  − host-paid fixed fees
  − host-paid processing fees
  − refunds/chargebacks
  − ambassador rewards where applicable
```

Shipping credited to the host (when applicable) is included in the merchandise / host-gross base before host-paid deductions.

**At checkout:** `host_net_estimate` = post-discount items (+ shipping) − host-paid fees (commission, fixed, host-paid processing).  
**On earnings reports:** reported net also subtracts refunds/chargebacks and ambassador rewards.  
**Ledger credit** after verified payment uses `host_net_estimate` (idempotent `sale_credit` / `vault_sale`). Full host formula: [HOST_EARNINGS.md](./HOST_EARNINGS.md).

### Platform revenue

```
Platform revenue =
  buyer platform/service fees
  + host commissions
  + platform-owned fixed fees
  − platform-absorbed costs
```

Buyer-paid processing fees collected by Pàdéyá are included with platform fee revenue in ledger/reports. Host-paid processing reduces host net and credits platform. Fees with `payer=platform` are absorbed (not charged to buyer or host) and reduce platform margin.

Order snapshot field `platform_revenue_total` ≈ buyer fees + host fees at sale time. Admin platform revenue report aggregates append-only `platform_ledger_entries` (and refund reversals).

## Checkout calculation order (default)

1. Item subtotals (tickets, merch, bundles; Vault separately on unlock)
2. Apply promo / merch discounts
3. Calculate **buyer-paid** service / platform fees on post-discount merchandise
4. Calculate **processing fee** if buyer-paid (base = merchandise + service fees)
5. Apply **Buyer total** formula → `final_total`
6. In parallel: apply host-paid commission / fixed / processing → `host_net_estimate`

Free merchandise net (₦0 after discounts): buyer platform/processing fees are **waived by default** unless configured otherwise. True free orders skip Paystack redirect and still finalize server-side.

Webhook verifies Paystack amount equals `order.total_amount` (kobo).

## Order fee summary columns

On `orders` (major units):

- `buyer_fee_total`, `host_fee_total`, `processing_fee_total`
- `platform_revenue_total` (buyer fees + host fees at calc time)
- `host_net_estimate` (post-discount items + shipping − host-paid fees)

Detail lives in `order_fee_snapshots` (integer minor units). Buyer APIs expose **buyer-payer lines only**.

## Ledgers

### Host ledger (`ledger_entries`)

Types: `sale_credit`, `refund_debit`, `payout_hold`, `payout_release`, `payout_paid`, `vault_sale`, `adjustment`.  
Updates `host_balances` under row lock. Host/admin read; support blocked.

### Platform ledger (`platform_ledger_entries`)

Append-only platform journal with unique `dedupe_key`. Written on:

- Verified payment finalize (orders + Vault)
- Refund approval (refund + fee reverse adjustments)
- Payout mark-paid (`host_payout`)

Reports: `/admin/finance/platform-revenue` · CSV export audited. Payment references **masked**; raw Paystack payloads never exposed.

## Refunds

On finance approve:

1. Tickets / merch fulfillments invalidated or cancelled per rules
2. Host `refund_debit` on host ledger
3. Platform `refund` (+ adjustments reversing buyer fee / commission on full refunds)
4. Ambassador sales/conversions reversed

## Payouts

Manual only — [PAYOUTS.md](./PAYOUTS.md). Host request → finance review → **super_admin** mark paid with immutable evidence.

## Permissions (finance)

| Capability | Typical grant |
| --- | --- |
| View / manage fee settings | `admin.finance.view_fees` / `manage_fees` |
| Host fee overrides | `admin.finance.manage_host_overrides` |
| Export finance CSVs | `admin.finance.export_event_sales` / `view_fees` / finance_admin |
| Platform revenue / platform ledger | finance_admin, `view_fees`, `export_event_sales`, `payouts.review`, super_admin |
| Host earnings (own) | `finance.view_sales_summary` / `finance.view_payouts` |
| Refund approve | `refunds.approve` (not support-only) |
| Payout review | `payouts.review` |
| Payout mark paid | **super_admin only** |

Host `payments.view` alone is **not** enough for admin earnings / platform revenue.

## Audit logs

| Action | When |
| --- | --- |
| `finance.fee_*` / override CRUD | Fee setting changes |
| `payments.successful` | Verified finalize |
| `finance.refund_approve` / reject | Refund review |
| `finance.payout_*` | Payout review / mark paid |
| `finance.platform_revenue_export` | Platform revenue CSV |
| `finance.host_earnings_export` | Admin host earnings CSV |

## Help & UI routes

| Audience | Routes |
| --- | --- |
| Host | `/host/earnings`, `/host/events/[id]/earnings`, `/host/payouts` |
| Admin | `/admin/finance/*`, `/admin/finance/platform-revenue`, `/admin/ledger`, `/admin/payouts` |
| Help article | `/help/.../how-padeya-fees-and-host-earnings-work` |

## Remaining limitations

- Partial refunds are limited / placeholder vs full refund path
- Live Paystack refund API not wired (manual finance approve path)
- Automatic payouts deferred (manual evidence only)
- Ambassador rewards are shown on host earnings; primary host ledger credit still uses `host_net_estimate` (ambassador settlement is a separate rail)
- Analytics “platform fee rate” placeholder may still appear in older analytics copy — checkout uses configurable fee settings, not that placeholder
