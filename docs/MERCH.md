# Event merch — technical index

**Canonical product doc:** [MERCHANDISE.md](./MERCHANDISE.md)

Brand: **Pàdéyá** · API prefix: `/api/v1` · Package: `backend/app/merch/`

**Invariant:** Event-native merch only (host → event → product; same-cart checkout; event pickup; webhook-trusted stock; privacy-safe) — see [Product invariants](./MERCHANDISE.md#product-invariants).

This file keeps a compact API / schema / route index for implementers. Product concept, workflows, privacy, Phase 1 + commerce expansion, and deferred future improvements live in [MERCHANDISE.md](./MERCHANDISE.md) · [COMMERCE.md](./COMMERCE.md).

## Permissions

| Actor | Capability |
| --- | --- |
| Host owner | `merch.manage_own` on owned events — catalog, pricing, orders, fulfill |
| Host team (hybrid) | Org toggles `merch.scan_pickup_qr` / `merch.mark_picked_up` (+ scope) — see below |
| Event staff | `assignment_type` `merch_pickup` / `event_ops` on assigned events — desk only |
| Global RBAC staff | `merch.view_fulfillment` / `merch.fulfill` + assignment — desk only (no catalog edit) |
| Buyer | Own merch via `/merch/mine` or `/dashboard/merchandise` |
| Admin | `merch.view_admin` + `merch.moderate` — view, hide/remove, reports (no payment secrets) |
| Support | `merch.view_admin` only — no moderate, no ledger edits |

### Host team desk

Pickup authorization is **hybrid** (owner · host team · event staff). Overview: [TEAMS.md](./TEAMS.md#merch-pickup-scanner) · toggles: [HOST_PERMISSIONS.md](./HOST_PERMISSIONS.md).

| Allow when | Notes |
|---|---|
| Host owner | Full |
| Active team + `merch.scan_pickup_qr` / `merch.mark_picked_up` + host-wide | All host events |
| Active team + same perms + event in scope | Assigned events only |
| Active staff `merch_pickup` / `event_ops` | Per-event desk |

**Deny:** suspended/removed membership · wrong host · missing merch desk permission · ticket-only staff without merch type.

| Privacy rule | Behavior |
|---|---|
| Desk scan response | Nulls `buyer_email`, `shipping_address`, QR token |
| Shipping decrypt | Owner or `merch.manage_shipping` only (`can_reveal_shipping_address`) |
| Payment refs | Never on desk/audit metadata |

Scan endpoint: `POST /host/events/{event_id}/merchandise/scan-qr` (rejects ticket QR `typ`). Audited in `desk_scan_audit_logs` (`merch.scan_pickup`).

Frontend: `/host/desk` shows **Pickup** when `canScanMerch` for the active workspace.

## Data model

Merch reuses `orders` / `order_items` / `payments`. Pickup state is `merch_fulfillments`.

| Table | Purpose |
| --- | --- |
| `event_merch_products` | Catalog; moderation: `clear`/`flagged`/`hidden`/`removed` (+ storefront/vault/sponsor/shipping/POD/drop fields) |
| `event_merch_variants` | SKUs + `inventory_count`, `reserved_quantity`, `sold_quantity` |
| `order_items` | Polymorphic: `item_kind` = `ticket` \| `merch` \| `bundle` + snapshots |
| `merch_fulfillments` | Pickup / shipping / POD projection |
| `event_merch_fulfillment_events` | Append-only desk timeline |
| `merch_product_reports` | Buyer reports |
| Commerce tables | Bundles, discounts, shipping, size charts, reviews, stock alerts, carts, POD, revenue — [DATABASE.md](./DATABASE.md#event-merch-phase-1) |

See [DATABASE.md](./DATABASE.md#event-merch-phase-1) · [COMMERCE.md](./COMMERCE.md).

## APIs (selected)

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/merch/events/{event_id}/catalog` | Public | Active sellable products |
| GET | `/events/{event_slug}/merchandise` | Public | Alias — catalog by slug |
| GET/POST | `/merch/events/{event_id}/products` | Host | List / create |
| GET/POST | `/host/events/{event_id}/merchandise` | Host | Alias — list / create |
| PATCH | `/merch/products/{id}` | Host | Update / pause |
| PATCH | `/host/events/{event_id}/merchandise/{id}` · `/pause` · `/archive` | Host | Alias update / pause / archive |
| POST/PATCH | `/merch/products/{id}/variants`, `/merch/variants/{id}` | Host | Variant CRUD |
| GET | `/merch/host/events/{event_id}/fulfillments` | Host/staff | Pickup queue |
| GET | `/host/events/{event_id}/merchandise/orders` | Host/staff | Alias — pickup queue |
| POST | `/merch/fulfillments/{id}/fulfill` | Host/staff | Mark picked up |
| PATCH | `/host/merchandise/order-items/{id}/ready` · `/picked-up` | Host/staff | Alias by fulfillment or order_item id |
| GET | `/merch/mine` | Buyer | Purchases + pickup codes |
| GET | `/dashboard/merchandise` · `/{item_id}` | Buyer | Alias — mine / single item |
| POST | `/merch/products/{id}/report` | Buyer | Report a listing |
| GET | `/merch/admin/products` | Admin | Product list |
| GET | `/admin/merchandise` | Admin | Alias — product list |
| PATCH | `/admin/merchandise/{id}/hide` · `/restore` | Admin | Alias — moderate hide/restore |
| POST | `/merch/admin/products/{id}/moderate` | Admin | flag / clear / hide / remove / restore |

Orders: `POST /orders` accepts ticket / merch / `bundle` lines. Full tables: [API.md](./API.md#event-merch-phase-1) · [API.md](./API.md#merch-commerce-expansion).

## Frontend

See [FRONTEND_ROUTES.md](./FRONTEND_ROUTES.md) and [MERCHANDISE.md](./MERCHANDISE.md#frontend-routes-overview).

## Ambassadors (merch attribution)

`event_merch` campaigns and `applies_to=merch|tickets_and_merch` attribute **verified paid** merch lines only. Same webhook invariant as inventory: never create commission from frontend success. Merch discount codes (`merch_discount_codes`) are unrelated to Ambassador codes. Product rules: [AMBASSADORS.md](./AMBASSADORS.md).

## Related

- [TEAMS.md](./TEAMS.md) · [HOST_PERMISSIONS.md](./HOST_PERMISSIONS.md) — hybrid pickup auth + toggles
- [MERCHANDISE.md](./MERCHANDISE.md) — product concept, Phase 1 + commerce expansion, workflows, privacy, [future](./MERCHANDISE.md#future-improvements-deferred)
- [AMBASSADORS.md](./AMBASSADORS.md) — open Ambassadors / merch campaign attribution
- [COMMERCE.md](./COMMERCE.md) — shipping, storefront, bundles, discounts, QR, alerts, charts, reviews, sponsor, POD, revenue, cart, drops, Vault, badges
- [ROADMAP.md](./ROADMAP.md) — Phase 4 commerce + Later (live POD/carrier sync)
- [SECURITY.md](./SECURITY.md#event-merch) · [PRIVACY.md](./PRIVACY.md#host-team)
- [ANALYTICS_TRACKING_PLAN.md](./ANALYTICS_TRACKING_PLAN.md#event-merch-signals)
- [DEMO_DATA.md](./DEMO_DATA.md#event-merch-demo)
