# Merchandise marketplace

Brand: **Pàdéyá** · Package: `backend/app/merch/` · API prefix: `/api/v1`

Host merch sold as **standalone shop items**, **event-attached merch**, **checkout add-ons**, **post-event drops**, **Vault exclusives**, and **bundles**. Host is required; event is optional. See also [COMMERCE.md](./COMMERCE.md).

Canonical product doc. Technical API tables also live in [API.md](./API.md); schema tables in [DATABASE.md](./DATABASE.md); routes in [FRONTEND_ROUTES.md](./FRONTEND_ROUTES.md). The shorter [MERCH.md](./MERCH.md) points here.

## Product invariants

> Merch is a **host revenue tool and fan discovery surface** — not only an event add-on.
>
> 1. **Host is required; event is optional** — standalone shop items live on the host; event merch/add-ons/drops attach when needed.
> 2. **Public marketplace** — `/merch` discovers featured, event, host-shop, drop, and Vault teaser listings.
> 3. **Educational guide** — `/merch-guide` explains formats, how it works, fees, and policies (Resources nav). Not a redirect away from the marketplace.
> 4. **Pickup by default** — shipping/POD optional per product; addresses encrypted and private.
> 5. **Server-trusted payment & inventory** — Paystack webhook finalize; never trust the browser for stock or fulfillment.
> 6. **Privacy protected** — no buyer email/phone, payment secrets, private venue details, Vault payloads, or desk notes exposed to buyers.
> 7. **Eligibility before purchase** — active product, inventory, ticket/check-in/VIP/Vault rules, buyer restrictions, own-host block.

## Product concept

- Chain: **host → (optional event) → product → variant (inventory) → order/payment → fulfillment**
- Marketplace kinds: `standalone` | `event_addon` | `event_merch` | `post_event_drop` | `vault_exclusive` | `bundle`
- Merch is **not** a `TicketType`; pickup uses `typ=padeya.merch.pickup` (never ticket check-in QR)
- Checkout reuses the existing `orders` → `order_items` → `payments` stack (polymorphic `item_kind=merch`)
- Standalone host-shop orders may omit `event_id` and set `orders.host_id`
- Pickup state lives on `merch_fulfillments` (1:1 with the merch line)
- All money stays inside Pàdéyá / Paystack — no external payment links in listings

## Phase 1 scope (shipped)

Phase 1 event-linked merch is **shipped**. Marketplace discovery + standalone create are **shipped** on the same domain. Do not rebuild. Verify against this list; product detail lives in the sections below.

| Shipped | Notes |
| --- | --- |
| Marketplace `/merch` | Featured, event merch, host shops, drops, Vault teasers, categories + filters |
| Merch guide `/merch-guide` | Educational resource (formats, workflow, fees, policies) |
| Standalone merch | `POST /host/merch` without event; host-scoped slug; host-shop checkout via `host_id` |
| Event-linked merch | Host Merch Studio + event page / `/events/[slug]/merch` catalog |
| Variants / inventory | Variant SKUs, reserve → sell, sales windows, `requires_ticket`, `max_per_buyer` |
| Checkout add-ons | Polymorphic `item_kind=merch` on existing `POST /orders` + Paystack |
| Buyer dashboard | `/dashboard/merchandise` + pickup codes |
| Host fulfillment | Orders queue + pickup desk (`MRCH-*` text codes) |
| Admin moderation | Hide / restore / reports (`/admin/merchandise`, `/admin/merch/*` aliases) |
| Demo data | `backend/app/demo/merch_seed.py` — see [DEMO_DATA.md](./DEMO_DATA.md#event-merch-demo) |

Also shipped with Phase 1: in-app merch notifications (including host `merch.low_stock`), messaging context for merch lines, and merch analytics.

## Commerce expansion (shipped)

Advanced merch features land on the same orders/Paystack stack. Full index: [COMMERCE.md](./COMMERCE.md).

| Feature | Status |
| --- | --- |
| Shipping/delivery addresses | Shipped — encrypted; host ship/deliver; zones UI `/host/merchandise/shipping-zones` (carrier labels deferred) |
| Merch-only host storefront | Shipped — `/u/[username]/merch` |
| Ticket + merch bundles | Shipped — expand on `POST /orders` |
| Merch discount codes | Shipped — separate from ticket promos |
| Merch QR pickup | Shipped — `typ=padeya.merch.pickup` |
| Stock alerts | Shipped — persisted `merch_stock_alerts` (low/sold-out/restock/pre-event/high-reserve) + host inbox |
| Size charts | Shipped — `merch_size_charts` |
| Product reviews | Shipped — verified purchase; hosts cannot delete (403) |
| Sponsor-branded merch | Shipped — product fields + revenue split |
| Print-on-demand | Provider-ready + manual jobs (**live** Printful/Printify sync = future) |
| Revenue split reports | Shipped — append-only `merch_revenue_splits` + CSV |
| Abandoned cart recovery | Shipped — `merch_carts` (never invents paid state) |
| Post-event merch drops | Shipped — schedule + storefront visibility (+ `0049` flags); merch-only checkout allowed on **completed** events |
| Vault-exclusive merch | Shipped — teaser + eligibility (no Vault payload leaks) |
| Fan Passport merch badges | Shipped — after verified payment only |

Migrations: `20260718_0047` … `0049` — see [COMMERCE.md](./COMMERCE.md#migrations).

**Verification (2026-07-18):** merch backend suite **112 passed**; FE lint/build/PWA + `merch-smoke` green. Stabilization notes: [EXECUTION_TRACKER.md](./EXECUTION_TRACKER.md).

## Host workflow

1. Open **Merch Studio** for an event (`/host/events/[id]/merchandise`) or global `/host/merchandise`
2. Create product: name, type, description, cover/gallery, base price, status
3. Add variants (size/color/options, SKU, price override, inventory)
4. Set sales rules: window, requires ticket, max per buyer, show/featured on event page
5. Set pickup copy: location label, time window, public instructions; desk-only `fulfillment_notes`
6. Publish (`active`) — drafts stay host-only; pause/archive for soft EOL
7. After sales: **Orders** + **Fulfillment desk** — search pickup code, mark ready, confirm pickup, add notes
8. Message buyer from desk/order row when relationship allows (merch order-item context)

Permissions: `merch.manage_own` (catalog + fulfill). Staff: `merch.view_fulfillment` / `merch.fulfill` on assigned events — desk only, no pricing edit.

## Buyer workflow

1. Browse merch on the event page or `/events/[slug]/merch`
2. Choose variant + qty → add to checkout (same cart as tickets when applicable)
3. Pay via existing Paystack checkout (`POST /orders` + payment init)
4. After webhook: email + in-app **merch confirmed**; pickup code on `/dashboard/merchandise`
5. Collect at the event — show pickup code (and ticket if required)
6. Optional: Message host about a merch line; Report unsafe listings

Buyers only see their own merch rows (`/dashboard/merchandise`, `/merch/mine`).

## Checkout / payment rules

| Rule | Behavior |
| --- | --- |
| Same event | All lines in an order must share one `event_id` |
| Ticket + merch | Always allowed |
| Merch-only | Allowed when `event.allow_merch_only_checkout` **or** buyer already has an active ticket for that event |
| Promo codes | Apply to **ticket lines only**; rejected for merch-only carts — [PROMO_CODES.md](./PROMO_CODES.md) |
| Merch discounts | Optional `merch_discount_code` (separate from ticket promos); usage committed on paid finalize |
| Ambassadors | Optional `referral_code` attributes merch (and/or ticket) lines per campaign `applies_to`; conversions only on paid finalize; refunds reverse — [AMBASSADORS.md](./AMBASSADORS.md). Not the same as merch discount codes. |
| Trust | Inventory, fulfillments, discount redemptions, POD jobs, revenue splits, Passport merch badges, Ambassador conversions — only inside verified Paystack webhook finalize |
| Idempotency | Webhook finalize must not double-deduct stock or duplicate fulfillments / splits / redemptions / ambassador conversions |
| Eligibility | Server checks stock, sales window, product/host/event status, moderation, Vault/drop gates, `requires_ticket`, `max_per_buyer` (paid + pending) |

## Inventory rules

- Stock lives on **variants** (`inventory_count`, `reserved_quantity`, `sold_quantity`)
- Pending checkout **reserves** stock; paid finalize **commits** the sale
- Cannot oversell available stock
- Draft / paused / archived / admin-hidden products are not purchasable and stay out of the public catalog
- Refund of unfulfilled lines: cancel fulfillment; **restock only if** product `restock_on_refund` is true (default off)
- Stock alerts: persisted `merch_stock_alerts` + host notify when thresholds / sold-out / restock / pre-event risk / high reserve fire (see [COMMERCE.md](./COMMERCE.md#6-stock-alerts))

## Fulfillment rules

Pickup: `awaiting_pickup` → `collect_at_stand` → `fulfilled` · `cancelled`

Shipping: `awaiting_shipment` → `shipped` → `delivered` · `cancelled` (host `…/ship` + `…/deliver`)

| Rule | Behavior |
| --- | --- |
| Codes | Unique `MRCH-********` text codes — desk identifiers, not ticket QR (pickup lines) |
| Confirm once | Double pickup rejected |
| Cancelled / refunded | Cannot be picked up / shipped |
| Desk notes | Audited; never shown to buyers |
| Staff | Host or assigned staff with fulfill permission; decrypted ship-to only for shipping lines |
| Product channels | `pickup_enabled` / `shipping_enabled` (at least one) |

Buyer display labels map to confirmed / ready for pickup / picked up / preparing shipment / shipped / delivered / pending payment / cancelled / refunded.

## Privacy rules

Do **not** expose via merch APIs or UI:

- Buyer email / phone
- Full shipping street / phone / delivery notes (encrypted; never public or analytics)
- Payment IDs, Paystack refs, card data, amounts on admin merch order lists
- Private order secrets
- Host private contact
- Desk-only `fulfillment_notes`
- Private / hidden venue streets in public catalog or unpaid buyer rows

Buyers may see their own safe delivery summary (city/state/country + status/tracking). Host/staff with `merch.fulfill` see decrypted ship-to for shipping fulfillments only.

Pickup instructions must be **public-safe** before purchase (`app/merch/privacy.py`). Listing create/update rejects off-platform payment links, contact extraction, and banned terms (`app/merch/content_safety.py`).

Messaging about merch may pass `related_merch_order_item_id` and a system line `This conversation is about {product_name}.` — still no email/phone in payloads. See [PRIVACY.md](./PRIVACY.md) · [SECURITY.md](./SECURITY.md#event-merch).

## Admin moderation

| Capability | Permission |
| --- | --- |
| List / view products, orders, reports | `merch.view_admin` |
| Hide / restore / archive / resolve reports | `merch.moderate` |
| Support | `merch.view_admin` only — no moderate, no ledger edits |

- Moderation statuses: `clear` · `flagged` · `hidden` · `removed`
- Admin-hidden: not public/purchasable; host sees status + reason; cannot reactivate until restore
- Reports: `open` → `reviewing` → `resolved` / `dismissed` (reason, details, reporter, product snapshot, admin notes)
- Hide / archive / restore require a reason and write audit logs
- UI: `/admin/merchandise`, `/[id]`, `/orders`, `/reports`

## Notifications

| Kind | When |
| --- | --- |
| `merch.confirmed` (+ legacy `merch.paid`) | Paid fulfillments created |
| `merch.ready_for_pickup` | Status → `collect_at_stand` |
| `merch.picked_up` | Status → `fulfilled` |
| `merch.shipped` | Host marks shipping line shipped |
| `merch.delivered` | Host marks shipping line delivered |
| `merch.refunded` | Merch lines cancelled on refund |
| `merch.host_sale` | Host on paid merch finalize |
| `merch.low_stock` / stock-alert kinds | Persisted stock alerts + host notify after inventory changes |
| `merch.host_pickup` | Staff marks picked up |
| `merch.badge_earned` | Fan Passport merch badge awarded (badge name only) |

Bodies include event/product names only — never Paystack refs, amounts, or card data.

### Fan Passport merch badges

Awarded **after verified payment** (fulfillment created on webhook). None currently require pickup/`fulfilled` before award. Refunds that cancel unfulfilled merch re-evaluate and **revoke** badges when criteria no longer hold. Public Passport shows badges only when `show_badges` is on. Badge meta and proof summaries never include spend, order IDs, or payment data.

## Analytics

Client: section/product/variant/checkout/pickup views. Trusted server: payment confirmed, purchase completed, picked up, sold out, host create/update/pause, admin hide.

See [ANALYTICS_TRACKING_PLAN.md](./ANALYTICS_TRACKING_PLAN.md#event-merch-signals).

## Data model (summary)

| Table | Purpose |
| --- | --- |
| `event_merch_products` | Catalog + moderation + pickup/shipping/POD/vault/sponsor/drop fields |
| `event_merch_variants` | SKUs + inventory / reserved / sold + optional POD refs |
| `order_items` | Polymorphic `ticket` \| `merch` \| `bundle` (+ merch/bundle FKs + snapshots) |
| `merch_fulfillments` | Pickup / shipping / POD projection |
| `event_merch_fulfillment_events` | Append-only desk timeline |
| Commerce expansion tables | Bundles, discounts, shipping, size charts, reviews, stock alerts, carts, POD, revenue splits — [DATABASE.md](./DATABASE.md#event-merch-phase-1) |
| `merch_product_reports` | Buyer reports |
| `message_threads.related_merch_order_item_id` | Optional messaging context |

## APIs (overview)

Canonical: `/api/v1/merch/*` + commerce routes in `commerce_router`. Preferred aliases: `/host/events/{id}/merchandise`, `/events/{slug}/merchandise`, `/dashboard/merchandise`, `/admin/merchandise`, `/u/{username}/merch`. Checkout money path: **`POST /orders`** only — abandoned carts resume into orders; no parallel merch payment ledger.

Full tables: [API.md](./API.md#event-merch-phase-1) · [API.md](./API.md#merch-commerce-expansion) · [MERCH.md](./MERCH.md#apis-selected).

## Frontend routes (overview)

| Surface | Routes |
| --- | --- |
| Public | Event page section · `/events/[slug]/merch` · `/u/[username]/merch` · checkout |
| Buyer | `/dashboard/merchandise` · `/dashboard/cart` · order receipt merch lines |
| Host | Merch Studio + orders + fulfillment desk · discounts · size charts · stock alerts · revenue · POD · reviews |
| Admin | `/admin/merchandise` (+ detail, orders, reports, reviews, revenue, POD) |

Full table: [FRONTEND_ROUTES.md](./FRONTEND_ROUTES.md).

## Demo data

Rich catalog + advanced commerce personas via `backend/app/demo/merch_seed.py` + `merch_commerce_seed.py` (idempotent, `assert_demo_ops_allowed`). Bundles, Vault exclusive, QR pickup, abandoned carts, shipping, `LAUGH10`, reviews — see [DEMO_DATA.md](./DEMO_DATA.md#event-merch-demo).

## Future improvements (deferred)

**Document only — do not implement** unless already trivially present. Commerce expansion topics above are **shipped**; only the rows below remain future.

| Item | Status | Notes |
| --- | --- | --- |
| Live carrier label / tracking APIs | Future | Host enters tracking manually today |
| Live Printful / Printify / custom POD sync | Future | Provider interface + manual jobs shipped; placeholders fall back to manual |
| Buyer multi-channel stock-alert preferences | Future | Host persisted alerts + notify already shipped |
| Generic marketplace / non-event shop | Out of scope | Keep event-native (host → event → product + optional host storefront) |

Shipping/delivery for event merch is **shipped** (encrypted addresses, zones, host ship/deliver). See [COMMERCE.md](./COMMERCE.md).
