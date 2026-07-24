# Legacy Page & Content Studio

**Status:** Phase 1 Content Studio implemented (tiers + verified reviews + memories retained).

## What Legacy means

Legacy is the host’s **permanent public reputation and monetization hub** on Pàdéyá — not a basic profile page.

It combines:

- Public host identity (name, username, media, tagline, bio)
- Verified reputation (tier, score, stats, followers)
- Upcoming and past events
- Event Memories
- Verified reviews (checked-in attendees only)
- Vault preview — exclusive host content fans unlock by follow, ticket, attendance, VIP, or purchase (locked content stays protected)
- Sponsorship / contact CTAs
- Related discovery links

Public routes:

| URL | Notes |
| --- | --- |
| `/@{username}` | Canonical Legacy Page (middleware rewrite → `/u/{username}`) |
| `/u/[username]` | App route for Legacy |
| `/@{username}/vault` | Host Vault |
| `/@{username}/memories/[eventSlug]` | Event Memory |

## How hosts manage Legacy

Host Studio routes:

| Route | Purpose |
| --- | --- |
| `/host/legacy` | Studio overview + live preview |
| `/host/legacy/edit` | Identity, CTAs, socials, contact, sponsorship |
| `/host/legacy/content` | Content blocks + featured items |
| `/host/legacy/preview` | Full public preview |
| `/host/legacy/tier` | Tier progress |

Hosts can only manage their own Legacy settings. Admin moderation remains on abusive content via existing permissions (`legacy.manage` / review moderation).

## Content blocks

Blocks live in `host_legacy_content_blocks` and support:

- visible / hidden
- title override
- description override (optional)
- sort order
- layout style
- source type: `automatic` | `manual`
- item limit (where relevant)
- config JSONB

Default blocks (created automatically if missing):

1. About  
2. Upcoming Events  
3. Past Events  
4. Event Memories  
5. Verified Reviews  
6. Vault Preview  
7. Sponsor Packages / Sponsorship CTA  
8. Related Discovery  
(+ optional Photo Gallery, Featured Video, FAQ, Contact CTA)

Public API returns **visible blocks only**. Hidden sections do not leak their items in the public payload.

### Reviews rule

Hosts **cannot** delete, edit, or hide individual negative reviews via Legacy. They may hide the entire Reviews block; when they do, the public page shows a trust note. Admin moderation still controls abusive content.

### Vault rule

**Vault** = exclusive host content fans unlock through following, buying tickets, attending events, VIP access, or one-time purchase. Full product rules: [VAULT.md](./VAULT.md).

Legacy is a **teaser surface** for Vault — never an unlock surface.

Hosts configure the Vault Preview block on `/host/legacy/content`:

- Title and description overrides
- Source: `automatic` (featured + newest published) or `manual` (`config.vault_item_ids`)
- Layout: `locked_cards`, `featured_spotlight`, or `compact_row`
- Featured pin via `featured_vault_item` (always surfaces first when set)
- Hosts can also feature a drop from Vault Studio edit → Legacy

**Public Legacy invariants**

- Cards show title, teaser, cover, access type, locked badge only
- Locked `body`, private media URLs, invite codes, and entitlement state are never returned
- Open Vault CTA → `/u/[username]/vault` (or `/@{username}/vault`)
- `admin_hidden` / non-published drops are omitted
- Unlock (follow, ticket, VIP, check-in, purchase, invite) happens on Vault routes — not on Legacy

## Featured items

`host_legacy_featured_items` pins:

- upcoming / past event
- review
- vault item
- memory
- sponsor slot / media (types supported)

## APIs

| Method | Path | Auth |
| --- | --- | --- |
| GET/PATCH | `/api/v1/host/legacy` | Host |
| GET/POST | `/api/v1/host/legacy/content-blocks` | Host |
| PATCH/DELETE | `/api/v1/host/legacy/content-blocks/{id}` | Host |
| POST | `/api/v1/host/legacy/content-blocks/reorder` | Host |
| POST | `/api/v1/host/legacy/content-blocks/{id}/toggle` | Host |
| GET/POST | `/api/v1/host/legacy/featured-items` | Host |
| GET | `/api/v1/u/{username}/legacy` | Public |
| GET | `/api/v1/legacy/{username}` | Public (compat) |
| GET/PATCH | `/api/v1/legacy/me` | Host (compat) |

## Connections

- Event detail → host Legacy (`/@{host_slug}`)
- Legacy → upcoming events, Vault, Memories, sponsorship
- Review → event attended label
- Memory → event + host Legacy
- Vault item → host Legacy / Vault paths

## Tiers (unchanged core)

Named tiers from weighted composite score (New Host → Legend). See score factors in prior phases; admin can recalculate and edit thresholds.

## Privacy & moderation

- Public payload: visible blocks only; no private contact when preference is hidden
- Vault locked content protected on Legacy (teasers only — see Vault rule above)
- Reviews verified-only; hosts cannot scrub negative reviews
- Admin `legacy.manage` / review moderation remains authoritative
- Vault moderation (`vault.moderate`, `/admin/vault`) is separate from Legacy block config
