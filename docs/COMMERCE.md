# Event-native commerce (Pàdéyá)

Merch expands event commerce on the **shared** `orders` / `order_items` / `payments` stack. There is no parallel merch payment ledger.

Canonical product rules: [MERCHANDISE.md](./MERCHANDISE.md) · APIs: [API.md](./API.md#merch-commerce-expansion) · Schema: [DATABASE.md](./DATABASE.md#event-merch-phase-1) · Routes: [FRONTEND_ROUTES.md](./FRONTEND_ROUTES.md).

## Core rules (enforced in code)

- Money truth: `orders` + `payments` only.
- Merch is not purchased until Paystack webhook / server finalize succeeds (idempotent).
- Inventory commit, merch discount redemptions, POD jobs, revenue splits, and Fan Passport merch badges run **only after** verified payment finalize — never from the browser.
- Shipping addresses are encrypted (`encrypt_sensitive`); never in public serializers or analytics.
- Hidden event locations stay scrubbed on merch catalog/pickup surfaces.
- Vault-exclusive merch: teasers only when locked; no Vault payload leaks.
- Fan Passport merch badges never expose spend, order refs, or private fulfillment data.
- Analytics must not include address, phone, payment secrets, buyer private info, or locked Vault content.

## Features

| Feature | Backend | Frontend |
| --- | --- | --- |
| Shipping addresses | `merch_shipping_addresses` + zones; fee when zones exist | Checkout picker + `ShippingAddressForm`; host ship/deliver; `/host/merchandise/shipping-zones` |
| Host storefront | `GET /u/{username}/merch` | `/u/[username]/merch` (+ `/@…` rewrite) |
| Bundles | `merch_bundles` → expand on `POST /orders` | event bundles API |
| Merch discount codes | `merch_discount_codes` (≠ ticket promos) | checkout + `/host/merchandise/discounts` |
| Merch QR pickup | `typ=padeya.merch.pickup` | `MerchPickupQr` + desk scan |
| Stock alerts | `merch_stock_alerts` | `/host/merchandise/stock-alerts` |
| Size charts | `merch_size_charts` | `/host/merchandise/size-charts` + product size guide modal |
| Reviews | `merch_reviews` (hosts cannot delete) | buyer edit/remove; host reply inbox; admin hide/restore; public list |
| Sponsor merch | product sponsor fields + split | storefront badge |
| POD ready | integrations + manual jobs (after paid webhook) | `/host/merchandise/print-on-demand`, `/admin/merchandise/print-on-demand`; product POD toggle |
| Revenue splits | `merch_revenue_splits` (append-only) | `/host/merchandise/revenue`, `/admin/merchandise/revenue` |
| Abandoned cart | `merch_carts` + recovery job | `/dashboard/cart` |
| Post-event drops | `storefront_visibility=post_event_drop`, `post_event_drop_at`, audience flags; host API + notify job | `/host/events/[id]/post-event-drops`, event page, storefront `kind=post_event`, buyer dashboard |
| Vault-exclusive | access checks + teasers | locked cards |
| Passport badges | criteria after paid finalize | existing badge surfaces |

## Topic notes (shipped)

### 1. Shipping privacy

- Order-scoped `merch_shipping_addresses` store encrypted recipient/phone/street/notes.
- Public catalog, unpaid buyer lists, analytics, and badge meta never include full address or phone.
- Buyers see city/state/country (+ status/tracking) only; host/staff with `merch.fulfill` get decrypted ship-to for shipping lines.
- Host marks `…/ship` and `…/deliver` (manual tracking — **live carrier label APIs deferred**).
- Host shipping zones: `/host/merchandise/shipping-zones` + `GET/POST/PATCH …/shipping-zones`, `POST …/archive`. Only `active` zones apply to new checkout; archived/inactive excluded; past order `shipping_amount` snapshots stay.

### 2. Host storefront

- `host_profiles.merch_storefront_*` (enabled, title, description, visibility `public`/`unlisted`).
- Public: `GET /u/{username}/merch` (+ product detail). Products with storefront visibility (e.g. `host_storefront`, live `post_event_drop`) appear when the storefront is enabled.
- Still event-native commerce — not a generic marketplace.

### 3. Bundles

- `merch_bundles` + variant rules; checkout `item_kind: bundle` expands into ticket + merch lines on `POST /orders`.
- Inventory / max-per-buyer / sales windows enforced server-side; paid finalize commits stock.

### 4. Merch discounts

- `merch_discount_codes` separate from ticket `promo_codes`.
- Optional `merch_discount_code` on `POST /orders`; `POST /merch/discounts/validate` for preview.
- Redemptions (`merch_discount_redemptions`) recorded on verified paid finalize only.

### 5. QR pickup

- Signed QR `typ=padeya.merch.pickup` (never ticket check-in types).
- Buyer: `GET /dashboard/merchandise/{fulfillment_id}/qr`. Desk: `POST /host/events/{event_id}/merchandise/scan-qr`.
- Text `MRCH-*` codes remain desk identifiers alongside QR.

### 6. Stock alerts

- Persisted `merch_stock_alerts`: `low_stock`, `sold_out`, `restocked`, `pre_event_risk`, `high_reserve`.
- Thresholds on product/variant (default 5); host inbox `/host/merchandise/stock-alerts` + notify.
- Complements (does not replace) inventory reserve → commit rules.

### 7. Size charts

- Host-scoped `merch_size_charts` (`chart_json`, units, fit notes); products may set `size_chart_id`.
- Public products can expose the linked chart; no PII.

### 8. Verified product reviews

- One review per paid merch `order_item` after fulfillment exists.
- Public author label is Passport-safe (never email/phone); event chip is title/slug only.
- Hosts may reply; `DELETE /host/merchandise/reviews/{id}` always **403** (hosts cannot delete). Buyers may edit/remove own; admin moderate hide/restore.

### 9. Sponsor-branded merch

- Product fields: `is_sponsor_branded`, brand name/logo/description, optional `sponsor_id`, split type/value.
- Public surfaces show branding only; split amounts live in append-only revenue snapshots (not public catalog).

### 10. POD provider-ready architecture

- `MerchPodProvider` interface + `manual` provider; Printful/Printify/custom are **placeholders** that fall back to manual.
- Jobs (`merch_pod_jobs`) created after paid webhook when product POD-enabled — **no live Printful/Printify sync**.
- Host/admin UIs list jobs, manual fulfill, retry.

### 11. Revenue reports

- Append-only `merch_revenue_splits` on paid finalize (host / platform / sponsor / print-partner buckets).
- Host + admin JSON reports and CSV export — no buyer PII, card data, or Paystack secrets.

### 12. Abandoned cart recovery

- `merch_carts` / `merch_cart_items` for active/abandoned recovery (`/dashboard/cart`).
- Cart never invents paid state, addresses, or payment secrets; resume path points at checkout.
- Recovery notify with min-gap settings; purchase still requires `POST /orders` + Paystack.

### 13. Post-event drops

- `storefront_visibility=post_event_drop` + `post_event_drop_at`; `requires_vip` / `drop_live_notified_at` (migration `0049`).
- Before drop time: teaser / not purchasable; after: sellable on event/storefront rules.
- Buyer list: `GET /dashboard/merchandise/post-event-drops` (static path; must not collide with `/dashboard/merchandise/{item_id}`).
- Completed events: merch/bundle-only `POST /orders` allowed (ticket lines still require `published`).

### 14. Vault-exclusive merch

- `is_vault_exclusive` / `requires_vault_access` (+ optional required Vault item / access type).
- Locked buyers get teasers only — no Vault body, media URLs, or invite codes via merch APIs.

### 15. Fan Passport badges

- After paid finalize: `award_merch_badges_for_user` evaluates criteria (`first_merch_buy`, `merch_collector`, `vip_pack_owner`, `event_drop_supporter`, `vault_merch_member`, `sponsor_drop_supporter`).
- Badge meta: `{criteria_key, source: "merch"}` only — no amounts, order IDs, or addresses.

## Checkout breakdown

`POST /orders` may include ticket lines, merch lines, and/or `item_kind: bundle`. Optional:

- `promo_code` — ticket lines only
- `merch_discount_code` — merch (or configured applies_to)
- `fulfillment_method` — `pickup` \| `shipping` (must match product `pickup_enabled` / `shipping_enabled`)
- `shipping_address` — required when shipping; encrypted (`recipient_name`, `phone`/`phone_number`, `line1`/`address_line_1`, …). Never returned on public/order payloads; buyers get city/state/country hint only; host fulfill staff get decrypted ship-to.

Totals: `subtotal - ticket_discount - merch_discount + shipping` (zone flat fee when host has active zones; ₦0 if none).

Abandoned-cart rows (`merch_carts`) are **not** a second checkout — they only help resume into `POST /orders`.

## Migrations

| Revision | Notes |
| --- | --- |
| `20260718_0047_merch_commerce_expansion` | Commerce tables + product expansion columns (revises `0046`) |
| `20260718_0048_merch_discount_description_currency` | `description` + `currency` on `merch_discount_codes` |
| `20260718_0049_post_event_drop_flags` | `requires_vip`, `drop_live_notified_at` |

## Analytics / finalize safety

- Trusted merch analytics (`track_server_event`) uses stable ≤64-char `request_id` values and nested savepoints so unique collisions never abort Paystack finalize, revenue splits, or cart conversion.
- Badge award analytics failures are non-blocking.

## Future / deferred

| Item | Status |
| --- | --- |
| Live Printful / Printify / custom POD sync | **Deferred** — provider-ready + manual jobs shipped; no live sync |
| Live carrier label / tracking APIs | **Deferred** — host enters tracking manually on ship |
| Buyer multi-channel stock-alert preferences | **Deferred** — host persisted alerts + notify shipped; no buyer prefs UI |
| Delivery time estimates on zones | **Deferred** — zone model has fee/geo only (no ETA field) |
