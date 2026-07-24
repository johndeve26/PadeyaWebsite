# Payouts

**Brand:** Pàdéyá  
**Status:** Manual host-balance payouts with immutable evidence.  
**Companions:** [FINANCE.md](./FINANCE.md) · [PAYMENTS.md](./PAYMENTS.md) · [HOST_EARNINGS.md](./HOST_EARNINGS.md) · [SECURITY.md](./SECURITY.md)

## Scope

This document covers **host balance payouts** (ticket / merch / Vault net credited to `host_balances`).  
Ambassador “mark reward paid” is a **separate rail** — see [AMBASSADORS.md](./AMBASSADORS.md) and [PAYMENTS.md](./PAYMENTS.md#ambassadors-rewards-vs-host-balance-payouts).

## Rules

1. Payout completion is **never automatic**.
2. Only a **super admin** may mark a payout `paid`.
3. Mark-paid requires **immutable** `payout_evidence` (bank transfer reference, evidence file URL, paid_at, paid_by, recipient bank snapshot).
4. Support cannot review or complete payouts.
5. Host ledger + platform ledger entries for payouts are **append-only**.

## Statuses

`requested` · `under_review` · `approved` · `rejected` · `paid` · `cancelled`

## Flow

1. **Host** requests payout from available balance → `payout_hold` (available → pending).
2. **Finance admin** reviews: approve / reject / under_review.
3. Reject → `payout_release` (pending → available).
4. **Super admin** marks paid with evidence → `payout_paid` on host ledger + `host_payout` on platform ledger; `lifetime_paid_out` increases.
5. Paid status is not casually reversed.

## Reporting

| Metric | Source |
| --- | --- |
| Pending payout | `host_balances.pending_payout_balance` |
| Paid out | `host_balances.lifetime_paid_out` / platform `host_payout` entries |
| Open requests | Count of `requested` / `under_review` / `approved` |
| Host earnings UI | Net after fees; link to `/host/payouts` for cash-out |

Admin: `/admin/payouts` · `/admin/finance/platform-revenue` (payouts completed / pending cards).

## APIs

| Method | Path | Auth |
| --- | --- | --- |
| GET/POST | `/api/v1/finance/host/payouts` | Host (`payouts.request` for create) |
| GET | `/api/v1/finance/admin/payouts` | Finance / super |
| POST | `/api/v1/finance/admin/payouts/{id}/review` | `payouts.review` |
| POST | `/api/v1/finance/admin/payouts/{id}/mark-paid` | **super_admin only** |

## Audit

- `finance.payout_review` / related review actions
- `finance.payout_mark_paid` (includes evidence metadata; no raw secrets)

## Deferred

Automatic / scheduled payouts · instant Paystack transfer payouts · multi-currency settlement beyond NGN primary path.
