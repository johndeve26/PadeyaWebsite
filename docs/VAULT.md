# Vault

**Status:** Vault Content Studio implemented (Phase 11 core + host studio upgrade).

## What Vault means

**Vault = exclusive host content fans unlock through following, buying tickets, attending events, VIP access, or one-time purchase.**

Vault is the premium creator layer on Pàdéyá — not a file dump. Hosts publish drops (sets, galleries, recaps, decks, announcements); fans unlock them by relationship, attendance, invite, or payment. Vault surfaces on:

- Public catalog `/@{username}/vault`
- Item detail `/@{username}/vault/[itemSlug]`
- Legacy Preview block on `/@{username}`
- Host Studio `/host/vault*`
- Buyer library `/dashboard/vault`

Canonical UI copy: `frontend/src/lib/vault-copy.ts`. Full product reference for this module.

### Example drops

Behind-the-scenes recaps · unreleased DJ sets · early-access ticket drops · VIP photo galleries · ticket-holder recap videos · founder slide decks · private announcements · discount drops

---

## Access types

Server-side evaluation in `app/vault/access.py` — never trust the client.

| Type | Who unlocks | Notes |
| --- | --- | --- |
| `free` | Anyone (published item) | Full body/media returned publicly |
| `followers_only` | Users who follow the host | CRM follow required |
| `ticket_holder_only` | Valid active/checked-in ticket | Optional `required_event_id` / ticket-type scope |
| `checked_in_attendee_only` | Checked-in ticket only | `require_check_in` enforced |
| `vip_ticket_holder_only` | VIP / VVIP ticket type | Optional event scope |
| `one_time_unlock` | Paid purchase (`PDY-VLT-*`) | Grant + ledger after verified payment |
| `invite_only` | Access-code redeem or host manual grant | Codes hashed at rest; never returned |
| `admin_hidden` | Not public | Host/admin only; omitted from catalog/Legacy |

### Access rule fields

`access_type` · `price` / `currency` · `required_event_id` (`event_id` alias) · `required_ticket_type_id` / `ticket_type_ids` · `require_check_in` · `access_code` (write-only) · `max_unlocks` · `starts_at` / `ends_at` · `required_legacy_tier` (stored, not enforced yet)

---

## Host creation flow

Hosts create drops in Vault Studio (`vault.create` permission).

| Step | Route / UI | What the host sets |
| --- | --- | --- |
| 1. Content | `/host/vault/new` → Content | Title, slug, content type, description, preview teaser, locked body |
| 2. Media | Media step | Cover, preview vs private media, `file_url` / `external_url` when needed |
| 3. Access | Access step | Access type + price/event/invite/window rules |
| 4. Related | Related step | Optional `related_event_id`, `related_memory_id`, Legacy feature |
| 5. Preview & publish | Preview step | Fan (locked) vs owner preview; publish / schedule / save draft |

**Studio hub:** `/host/vault` (metrics, filters, performance cards) · edit `/host/vault/[id]/edit` · fan preview `/host/vault/[id]/preview` · earnings `/host/vault/earnings`.

**Lifecycle actions:** publish · unpublish → draft · schedule · archive · restore (archived/expired → draft) · hard delete **draft only** if no unlock/purchase history. Items with unlock history must be archived — never hard-deleted.

**Statuses:** `draft` · `published` · `scheduled` · `expired` · `archived` · `hidden_by_admin`

**Content types:** `text_post` · `image_gallery` · `video` · `audio` · `file_download` · `early_access` · `discount_drop` · `ticket_holder_recap` · `vip_content` · `external_link` · `announcement`  
(Aliases: `file` → `file_download`, `livestream_replay` → `ticket_holder_recap`.)

---

## Public locked / unlocked behavior

| State | Catalog card | Item detail |
| --- | --- | --- |
| **Locked** | Title, teaser, cover, access type, lock badge, price (if paid), related event teaser, CTA | Preview fields + lock message + unlock CTAs; **no** `body`, `file_url`, `external_url`, or private media URLs |
| **Unlocked** | Same public card metadata + unlocked badge | Full body, private media, downloads, external links |

Rules:

- Public catalog (`GET /vault/public/{username}`) returns slim `VaultCatalogCard` rows only — never nested media bodies.
- Private/non-preview media are **omitted** when locked (not returned as `url: null`).
- Preview media (`is_preview=true`) may appear while locked.
- Draft, scheduled, expired, archived, and `hidden_by_admin` items are not listed and 404 on public detail.
- Buyer library (`/dashboard/vault`) re-checks access via `/vault/me/*` — never trusts a cached unlock flag alone.

---

## Legacy connection

Vault is the exclusive-content block on the host Legacy Page.

| Surface | Behavior |
| --- | --- |
| `/host/legacy/content` | Configure `vault_preview`: title/description, source `automatic` \| `manual` (`config.vault_item_ids`), layout `locked_cards` \| `featured_spotlight` \| `compact_row` |
| Featured pin | `featured_vault_item` always surfaces first when set |
| Public `/@{username}` | Locked teaser cards only; CTA → `/u/[username]/vault` |
| Host feature from Vault edit | Can pin a drop onto Legacy |

**Invariant:** Public Legacy never returns Vault `body`, private media URLs, invite codes, or unlock entitlement state. See [LEGACY_PAGE.md](./LEGACY_PAGE.md).

---

## Event / memory connection

| Direction | Behavior |
| --- | --- |
| Vault → event | Optional `related_event_id` + access-rule `required_event_id` for ticket/VIP/check-in gates |
| Vault → memory | Optional `related_memory_id` (must belong to host / event) |
| Event detail `/events/[slug]` | Related Vault teaser section (same host) |
| Event Memory `/@{username}/memories/[eventSlug]` | Related Vault teasers for that night |
| APIs | `GET /vault/related/event/{event_id}`, `GET /vault/related/memory/{memory_id}` |

Reverse lists return catalog teasers only — never locked bodies or private media. Item detail links to related event, related memory, and host Legacy.

---

## Payment / unlock rules

### One-time unlock (`one_time_unlock`)

1. Buyer starts checkout → `POST /vault/unlock/{id}` → Paystack reference `PDY-VLT-*`
2. Pending checkout for the same buyer+item is **reused** (no double init)
3. Access is granted only after **verified** Paystack webhook (or free/demo finalize server-side)
4. Finalize writes idempotent `vault_access_grants` (`UNIQUE(item, user)`) + paid `vault_purchases`
5. Host earnings: append-only `vault_sale` ledger keyed by purchase id (idempotent)
6. Frontend polls `/vault/me/purchases/{id}` after return — **never** trusts client “payment success” alone
7. Vault unlocks **never** issue event tickets

`DEMO_MODE=true` may finalize unlocks without Paystack; disabled in production by config.

### Other unlock paths

| Path | Mechanism |
| --- | --- |
| Followers | Live CRM follow check |
| Ticket / VIP / check-in | Live ticket status (+ VIP type / checked_in) |
| Invite | `POST /vault/redeem/{id}` with code, or host `POST /vault/host/items/{id}/grant` |
| Free | Published + not expired |

`vault_unlock_attempts` logs checkout attempts (append-only; no entitlement).

---

## Privacy / security rules

Backend enforcement — frontend hiding is not enough:

- Locked responses never include `body`, `file_url`, `external_url`, or private media URLs
- Invite access codes are **hashed at rest** and **never returned** (`access_code` always null; `access_code_set` may be true)
- Invite-only locked detail is limited to preview/teaser fields
- `admin_hidden` / `hidden_by_admin` omitted from public catalog and Legacy; public detail 404
- Hosts manage only their own items; cross-host edit returns 404
- Prefer storage abstraction (`LocalMediaStorage`); do not embed secrets in client bundles
- Service worker must never cache Vault API, checkout, or locked media routes
- Subscriptions (`vault_subscriptions`) do **not** grant content access yet

---

## Moderation

| Surface | Behavior |
| --- | --- |
| `/admin/vault` | Filter by status, access type, host, search; unlock/purchase summary per row |
| `GET /vault/admin/items` | `vault.moderate` or `admin.full_access` |
| `POST /vault/admin/items/{id}/moderate` | `flag` · `approve` · `hide` · `archive` · `remove` · `restore` |

- Hide / archive / remove / restore require a moderation **reason** (stored + audited)
- Hide → `hidden_by_admin`; host cannot edit until admin restore
- Support does **not** get `vault.moderate` by default
- Reports column reserved (`report_count`) until a Vault report queue exists

---

## Models

| Table | Role |
| --- | --- |
| `vault_items` | Drop identity, body, media refs, status, moderation |
| `vault_media` | URLs via storage; `is_preview` may be public |
| `vault_access_rules` | Access type + price/event/invite/window |
| `vault_purchases` | Paystack / invite / manual / demo purchase rows |
| `vault_access_grants` | Idempotent entitlement `UNIQUE(item, user)` |
| `vault_unlock_attempts` | Append-only checkout attempt log |
| `vault_views` | View telemetry with `had_access` |
| `vault_subscriptions` | CRM list only (no content unlock yet) |

---

## APIs (summary)

See [API.md](./API.md) for the full route table. Key surfaces:

| Area | Paths |
| --- | --- |
| Public | `GET /vault/public/{username}`, `GET /vault/public/{username}/{slug}`, related event/memory |
| Unlock | `POST /vault/unlock/{id}`, `POST /vault/redeem/{id}`, Paystack webhook |
| Buyer | `GET /vault/me/library`, `/me/purchases`, `/me/items` |
| Host | `/vault/host/studio`, `/host/items*`, publish/archive/restore/grant/earnings |
| Admin | `/vault/admin/items`, `/admin/items/{id}/moderate` |

---

## Analytics

Client + trusted Vault funnel events (`vault_page_view`, `vault_item_*`, `vault_unlock_*`, `vault_follow_unlock`, `vault_ticket_unlock`, `vault_media_open`, `vault_download_click`; trusted `vault_purchase`). Metadata: `host_id`, `vault_item_id`, `access_type`, `related_event_id`, `locked_state`, `source_page`. See [ANALYTICS_TRACKING_PLAN.md](./ANALYTICS_TRACKING_PLAN.md).

---

## Constraints / deferred

- Hosts manage only their own items (`vault.create`)
- Do not trust client gates or frontend payment success
- Subscriptions do not unlock Vault content yet
- Invite-token deep-link grant path deferred (code redeem + manual grant work today)
- Tests: `backend/tests/test_vault.py`; FE smoke: `npm run test:vault`
