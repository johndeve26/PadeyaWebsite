# Host earnings

**Brand:** Pàdéyá  
**Companions:** [FINANCE.md](./FINANCE.md) · [PAYOUTS.md](./PAYOUTS.md) · [PAYMENTS.md](./PAYMENTS.md) · [API.md](./API.md)

## What hosts see

Hosts view **net revenue after Pàdéyá deductions**, not buyer checkout totals.

| Surface | Path |
| --- | --- |
| Portfolio earnings | `/host/earnings` |
| Per-event earnings | `/host/events/[id]/earnings` |
| Payouts / balance | `/host/payouts` |
| Fee terms (own only) | Included on earnings report (`fee_terms`) |
| Vault-only rollup | `/host/vault/earnings` (links into payouts) |

Admin: `/admin/finance/earnings`, `/admin/hosts/[hostId]/earnings`, `/admin/events/[id]/earnings`.

## Help copy (host)

- **Buyer platform fee is paid by the buyer.** It does not increase your gross sales.
- **Host commission is deducted from host earnings.**
- **Fee settings can differ by host.** Your report shows *your* resolved rates only.
- **Order fee snapshots preserve the fee terms used at the time of sale.** Later admin edits do not change old orders.

## Definitions

| Term | Meaning |
| --- | --- |
| **Gross ticket / merch / Vault sales** | Line item value before host deductions |
| **Discounts** | Promo + merch discounts |
| **Host gross** | Item subtotal after discounts (+ shipping). **Excludes** buyer-paid platform fees |
| **Pàdéyá commission** | Host-paid ticket/merch/Vault fees |
| **Processing (host-paid)** | Only when processing fee payer = host |
| **Ambassador rewards** | Active commission owed on referred sales (display deduction) |
| **Refunds** | Completed refund debits |
| **Net earnings** | Host gross − host fees − ambassadors − refunds |
| **Pending / paid out** | From `host_balances` (host-wide reports) |

## Formula

Canonical product formula ([FINANCE.md](./FINANCE.md#canonical-money-formulas)):

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

Implementation mapping:

```
host_gross = (ticket_subtotal + merch_subtotal − discounts) + shipping
           + vault merchandise net (when included)
           # excludes buyer platform/service fees and buyer-paid processing

buyer_fees = orders.buyer_fee_total          # platform only — not in host_gross

host_net_estimate = host_gross − host_fee_total
# host_fee_total = host commission + host-paid fixed + host-paid processing

reported_net ≈ Σ host_net_estimate − ambassador_rewards − refunds/chargebacks
```

Ledger credit after verified payment uses `host_net_estimate` (idempotent `sale_credit` / `vault_sale`).

## Per-order breakdown

Each paid order / Vault unlock row includes:

- Buyer paid total (may include buyer fees)
- Item subtotal, discounts, host gross
- Buyer-paid fees (informational; platform revenue)
- Host-paid deductions, platform revenue, host net
- Payment status + payout/credit status

CSV export: `GET /finance/host/earnings/export.csv` (and admin equivalents).

## Permissions

| Actor | Access |
| --- | --- |
| Host owner / team with `finance.view_sales_summary` or `finance.view_payouts` | Own host earnings |
| Another host | **Cannot** read this host’s earnings |
| Finance admin / super | Any host via admin APIs |
| Support | Blocked from finance earnings / ledgers |

## Related

Payout cash-out: [PAYOUTS.md](./PAYOUTS.md). Platform-wide fee revenue: [FINANCE.md](./FINANCE.md#platform-revenue-streams).
