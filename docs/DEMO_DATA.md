# Demo data (local development)

Local-only seed data for end-to-end demos and messaging QA. **Never runs in production.**

Canonical implementation: `backend/app/demo/` · CLI: `python -m scripts.seed_demo_data` · FE hub: `/demo` when `DEMO_MODE=true`.

Related: [MESSAGING.md](./MESSAGING.md) · [PRIVACY.md](./PRIVACY.md) · [SECURITY.md](./SECURITY.md) · backend notes: [`backend/app/demo/README.md`](../backend/app/demo/README.md).

## Safety / privacy notes

- Seed and reset **refuse** when `APP_ENV=production`.
- Demo emails use `@demo.padeye.test` — **login only**; never written onto public Passport / Legacy / message serializers.
- Shared password for all demo accounts: `DemoPass123!`
- Event slugs use the `demo-` prefix; host slugs are stable (`djmaze`, `lagoscomedyhub`, …).
- Payments finalize on mocked paths (no live Paystack charges). Keep **Admin → Email settings** on log / dev mode locally.
- Images are local SVGs under `frontend/public/demo/` (no external asset URLs).
- Messaging copy is guarded by `app/demo/messaging_privacy.py` (`assert_safe_demo_copy`) — no WhatsApp, phones, emails, bank/payment links, private streets, locked Vault bodies, order/payment IDs, or CRM notes in seeded messages / notification summaries.
- Safe placeholders only: “Open your Pàdéyá ticket”, “Check your dashboard”, “Use your QR code at check-in”, “Your ticket-holder Vault access should unlock”, “Refresh your Vault page”.
- Private / unlisted fans (`miralagos`, `adafirsttimer`, `bayocampus`) stay out of the Fan Passport Directory.
- Set `DEMO_MODE=true` so `/demo` is available in the Next.js app.

## Admin impersonation (demo QA)

Seed accounts behave like real accounts for auth and support tooling:

- **Normal login** — every `@demo.padeye.test` account still signs in with `DemoPass123!` (use `/demo` credentials or Messaging/Fan Connect shortcuts).
- **Impersonation** — `admin@demo.padeye.test` (or any admin with `admin.users.impersonate`) can impersonate seed buyers/hosts/fans the same way as production users. Platform roles (`super_admin`, `support_agent`, `finance_admin`) remain blocked as targets.
- **Banner** — while impersonating a seed user, the global banner shows **Audited session** and **Demo seed account** (admin-visible only).
- **Internal audit retained** — never skipped in demo/`DEMO_MODE`. Start metadata may include `demo_seed_target: true`.
- **Target is not notified** — no email, in-app, or push when impersonation starts.
- **No Host-as-Fan bypass** — impersonation and demo mode do **not** override own-host **owner** product rules (checkout, follow, review, messaging, ambassador commissions). Team/staff/ambassadors may still buy and fan that host normally. Seed accounts may buy/follow **other** hosts normally. Do not use live Paystack for owner own-host tests. A dedicated local test-order helper is deferred; if added later it must never count toward public metrics.

`/demo` Impersonation QA shortcuts: Impersonate Demo Buyer · Impersonate Tolu · Impersonate DJ Maze · Open Admin Users · Login as Demo Buyer (normal). Admin Users also accepts email lookup (`buyer@demo.padeye.test`).

See [SECURITY.md](./SECURITY.md#admin-user-impersonation) · [ADMIN.md](./ADMIN.md#user-impersonation).

## How to reset / reseed

From `backend/` (venv active, migrations applied):

```bash
# Idempotent seed (refreshes Studio/taxonomy/placements + messaging top-up if already seeded)
python -m scripts.seed_demo_data

# Wipe demo-scoped data, then full seed
python -m scripts.seed_demo_data --reset

# Wipe demo-scoped data only
python -m scripts.reset_demo_data
```

| Command | Behavior |
| --- | --- |
| `seed_demo_data` | If marker `seed/complete` exists: refresh + **idempotent** persona / passport / messaging / merch / open Ambassadors top-up. Does **not** re-run full commerce loops. |
| `seed_demo_data --reset` | Delete demo users/hosts/events/orders/tickets (scoped), then full seed. |

### Rich sponsor demo (6 fictional brands)

Separate from the minimal `_seed_sponsorships` rows in the main demo seed. Run **after** `seed_demo_data`:

```bash
# From backend/ — requires DEMO_MODE=true or SPONSOR_DEMO_SEED_ENABLED=true
DEMO_MODE=true python -m scripts.seed_sponsor_demo_data
DEMO_MODE=true python -m scripts.seed_sponsor_demo_data --force   # re-apply interactions
```

**Guards:** Refuses `APP_ENV=production`. Requires `DEMO_MODE=true` **or** `SPONSOR_DEMO_SEED_ENABLED=true`. Prints `Seeding fictional sponsor demo data only.`

**Brands (fictional):** NeonPalm Drinks, KoraWave Pay, Jollof Republic, CampusWave, NovaSkin Beauty, PulseFrame Media — each with team users `@demo.padeya.test`, **5 demo events**, **2–3 pack hosts**, **3–5 published slots**, campaigns, saved items, inquiries, deals/invoices, placements, deliverables, and recommendation feedback where applicable.

| Slug | Public directory + `/sponsors/[slug]` | Public profile sections |
| --- | --- | --- |
| `neonpalm-drinks` | Yes (verified) | ≥2 approved public case-study campaigns; ≥5 sponsored events; partnered hosts |
| `korawave-pay` | Yes | ≥1 public campaign; ≥3 sponsored events (+ proposed/unpaid deals in workspace only) |
| `novaskin-beauty` | Yes | Public campaigns + ≥5 sponsored events |
| `pulseframe-media` | Yes | Completed placement track record (≥5 sponsored events) |
| `jollof-republic` | **No** (pending verification) | Workspace/admin rich data only |
| `campuswave` | **No** (under_review + unlisted) | Moderation/recommendation QA only |

Event pack slugs: `demo-spn-{sponsor-slug}-{event-key}`. Public verified sponsors should show **≥5 sponsored events**, **≥2 partnered hosts**, **2+ public case-study campaigns** (where seeded), and **up to 3 related sponsors** on `/sponsors/[slug]` after seed.

**Login:** `sponsor-owner-{slug}@demo.padeya.test` (and `-manager-`, `-viewer-`) with shared `DemoPass123!`.

**Payment / notifications:** No Paystack API calls and no `notify_user` during seed; paid deals use `PDY-SPN-DEMO-*` references and redacted `sponsorship_payment_events` rows only. Public API never returns invoice amounts, payment refs, team, or internal notes.

**Tests:** `pytest tests/test_sponsor_demo_seed.py` · **FE smoke:** `node frontend/scripts/sponsor-demo-smoke.mjs`


Seeded by `backend/app/demo/merch_seed.py` + `merch_marketplace_seed.py` + `merch_commerce_seed.py` (`seed_demo_merch` via `_seed_merch`) — idempotent by product name (event) or host+name (standalone). Vault seeds **before** merch so Vault-exclusive purchases work. Product rules: [MERCHANDISE.md](./MERCHANDISE.md).

**Guards:** `APP_ENV=production` always blocks. `NODE_ENV=production` also blocks unless `DEMO_SEED_ENABLED=true`. Never auto-seed in production.

**Marketplace coverage (30+ products):** standalone host shops, event merch, checkout add-ons, post-event drops, Vault exclusives, bundles, sold-out / low-stock, pickup-only, delivery/manual, digital placeholders. Images from `frontend/public/demo/merch/*.svg`.

**Seed wiring notes (required for persona commerce):**

- `fan1`–`fan20` must be present in the `users` map passed to merch seed (merged after `_seed_commerce`).
- Demo merch orders supply required Studio `checkout_answers` (same pattern as ticket commerce).
- Durable catalog/discount/bundle rows are committed before persona `_safe` order steps (helpers that `db.commit()` cannot run inside nested savepoints).
- Abandoned cart (`fan7` / Food & Flow) is seeded **last** so later order failures cannot wipe it.

**Catalog (event key → products)**

| Event key | Products |
| --- | --- |
| `afrobeats-night-live` | Afrobeats Night Tee (sold-out XL/White), Neon Cap (low stock + sponsor), VIP Glow Wristband, Vault-exclusive Backstage Hoodie, post-event Afrobeats Recap Poster + marketplace add-ons/drops (Glow Wristband, Photo Booth Pass, Checked-in Tee, Backstage Lanyard, Sold Out Island Tee, Pickup-Only Cap) |
| `detty-friday-live` | Detty December Poster, Afterparty Access Band, VIP Aftermovie Poster |
| `lagos-comedy-jam` | Comedy Cap; “I Survived The Front Row” T-shirt; Event Face Mask; Event Crew Cap; `LAUGH10`; Ticket + Comedy Cap Bundle |
| `founders-mixer-lagos` | Founder Mode Tote Bag; Product Builder Notebook; sponsor Startup Pack; POD Builder Sticker Sheet; Silent Disco LED Band; Fan Memory Photo Pack |
| `worship-under-stars` | Worship Night Wristband; Praise Experience Tee (+ size chart); post-event Praise Night Recap Pin; Vault Members Praise Drop Tee |
| `food-and-flow` | Face Mask; Culture Fest Bucket Hat; Drink Voucher Bundle; Beach Fest Bucket Hat; Delivery Manual Merch Kit |
| `mainland-vibes-summer` | Afrobeat Night Live Tee |

**Standalone host shops (5 hosts):** Mainland Vibes Logo Tee, Island Nights Dad Cap, Campus Rave Hoodie, Alte Cruise Tote, Lagos Nightlife Stickers, Comedy Night Mug, plus Vault exclusives (Vault Member Hoodie, Host Legacy Poster, Private Listening Tee, Vault Gold Wristband, Digital Wallpaper Pack).

Merch-only checkout enabled on Afrobeats / Detty / Founders / Comedy / Food & Flow / Mainland Summer for demo.

**Persona fulfillments / commerce states**

| Buyer | Purchase | State |
| --- | --- | --- |
| Tolu `fan1` | Ticket + T-shirt Bundle | `awaiting_pickup` |
| Amaka `fan2` | VIP wristband + Neon Cap; Backstage Hoodie (Vault unlocked) | ready for pickup + signed QR; hoodie paid |
| Chidi `fan3` | Founder Mode Tote Bag | `awaiting_pickup` |
| Sade `fan4` | Comedy Cap + published review | `awaiting_pickup` |
| Kunle `fan5` | sponsor Startup Pack | `awaiting_pickup` (+ revenue split row) |
| Ada `fan7` | abandoned cart (Bucket Hat) | `abandoned`, recovery-eligible |
| Bayo `fan8` | Bucket Hat shipping | `shipped` (private address) |
| Mira `fan6` | Face Mask shipping | `delivered` |
| Demo Buyer | refunded tee; picked-up VIP wristband (QR); Recap Poster drop | `refunded` / `fulfilled` / drop paid |

Also covers: low stock alert (Neon Cap), sold out variant + Sold Out Island Tee, Vault locked teaser, `MERCH10`, Lagos shipping zones, demo in-app notifications (`merch.confirmed`, pickup ready, drop live, Vault unlocked), extra bundles (VIP + Merch Pack, Couple Ticket + Caps, Group Pass + Wristbands, Vault Access + Hoodie Bundle).

Host UI: `/host/merchandise` (+ orders/fulfillment hubs, discounts, …) · Buyer: `/dashboard/merchandise`, `/merch` marketplace · Storefront: `/@djmaze/merch`, `/merch/hosts/[username]` · Admin: `/admin/merchandise` / `/admin/merch`. Commerce index: [COMMERCE.md](./COMMERCE.md).

`seed_messaging_demo` alone skips existing `(fan_user_id, host_id)` threads (one thread per pair).

Do **not** delete only the complete marker and re-run full seed without `--reset` — commerce can duplicate orders.

## Demo users (roles)

Password for every account: **`DemoPass123!`**

| Email | Name | Role |
| --- | --- | --- |
| `buyer@demo.padeye.test` | Demo Buyer | buyer |
| `host@demo.padeye.test` | DJ Maze | host |
| `host2@demo.padeye.test` | Lagos Comedy Hub | host |
| `mainland@demo.padeye.test` | Mainland Vibes | host |
| `tech@demo.padeye.test` | Tech Connect Africa | host |
| `praise@demo.padeye.test` | Praise Experience | host |
| `staff@demo.padeye.test` | Gate Staff | host_staff |
| `ops@demo.padeye.test` | Event Ops Manager | DJ Maze team **admin** (host-wide) |
| `gate@demo.padeye.test` | Gate Scanner | DJ Maze team **scanner** · `tickets.scan_qr` / `tickets.check_in` · **Afrobeats Night Live** only |
| `pickup@demo.padeye.test` | Pickup Staff | DJ Maze team **merch_staff** · `merch.scan_pickup_qr` / `merch.mark_picked_up` · **Afrobeats Night Live** only |
| `sponsor-observer@demo.padeye.test` | Sponsor Observer | **Host-side only:** DJ Maze team **viewer** · `sponsors.view` + `analytics.view_sponsors` on `/host/sponsorships` — **not** a sponsor brand workspace (use `sponsor-owner-*@demo.padeya.test` after rich sponsor seed) |
| `team-invitee@demo.padeye.test` | Pending Teammate | Pending invite · accept at `/team/invite/demo-padeya-team-invite-afrobeats` |
| `support@demo.padeye.test` | Demo Support Agent | support_agent |
| `finance@demo.padeye.test` | Finance Admin | finance_admin |
| `admin@demo.padeye.test` | Demo Super Admin | super_admin |
| `fan1@` … `fan8@demo.padeye.test` | Named fan personas (below) | buyer |
| `fan9@` … `fan20@demo.padeye.test` | Volume fans (commerce filler) | buyer |

### DJ Maze host team

Seeded by `app/demo/team_seed.py` (idempotent on every seed/refresh):

| Member | Role label | Scope |
| --- | --- | --- |
| DJ Maze (`host@`) | Owner (not a membership) | Full |
| Event Ops Manager | Admin | Host-wide |
| Gate Scanner | Scanner Staff | Afrobeats Night Live only |
| Pickup Staff | Merch Staff | Afrobeats Night Live only |
| Sponsor Observer | Viewer | Host-wide sponsors read-only |
| Pending Teammate | Pending invite | Scanner · Afrobeats |

`/demo` shortcuts: Open Host Team · Open Gate Scanner account · Open Pickup Staff account · Open Team Audit Log · Open Invite Accept page.

## Demo hosts

| Slug | Display name | Owner email | Tier | City | Notes |
| --- | --- | --- | --- | --- | --- |
| `djmaze` | DJ Maze | `host@` | Icon | Lagos | Nightlife · sponsor-ready · Vault |
| `lagoscomedyhub` | Lagos Comedy Hub | `host2@` | Established | Lagos | Comedy · auto-reply on |
| `techconnectafrica` | Tech Connect Africa | `tech@` | Established | Lagos | Tech · followers messaging off |
| `praiseexperience` | Praise Experience | `praise@` | Rising | Ibadan | Gospel · **not** sponsor-ready |
| `mainlandvibes` | Mainland Vibes | `mainland@` | Rising | Lagos | Lifestyle · sponsor-ready |

Legacy QA: `/@djmaze`, `/@lagoscomedyhub`, `/@techconnectafrica`, `/@praiseexperience`, `/@mainlandvibes`.

### Showcase events (messaging-linked)

| Host | Upcoming / live | Completed |
| --- | --- | --- |
| DJ Maze | Afrobeats Night Live · Mainland After Dark | Detty Friday Rooftop |
| Comedy | Laugh Lagos Live | Sunday Comedy Room |
| Tech | Founders Mixer Lagos | Product Demo Night |
| Praise | Choir & Community Live | Worship Night Ibadan |
| Mainland | Lagos Creative Market | Mainland Food & Culture Fest |

## Demo fans (named personas)

| Email | Name | Username | Passport | Directory | Messaging notes |
| --- | --- | --- | --- | --- | --- |
| `fan1@` | Tolu Nightlife Explorer | `toluwave` | public | yes | Follow **or** attended hosts may Message Fan |
| `fan2@` | Amaka Concert Lover | `amakaconcerts` | public | yes | Hosts she **follows** |
| `fan3@` | Chidi Tech Regular | `chiditech` | public | yes | Hosts she **attended** |
| `fan4@` | Sade Comedy Fan | `sadecomedy` | public | yes | Follow / attended |
| `fan5@` | Kunle VIP Regular | `kunlevip` | public | **no** | Attended only |
| `fan6@` | Mira Lagos Explorer | `miralagos` | **private** | no | No public Message Fan |
| `fan7@` | Ada First Timer | `adafirsttimer` | **private** | no | Messages hosts via event pages (request) |
| `fan8@` | Bayo Campus Fan | `bayocampus` | **unlisted** | no | Direct `/f/bayocampus` only |

Persona product context (`DEMO_PERSONA_CONTEXT`): tickets, check-ins, reviews, Vault unlocks — keeps Message Host / Message Fan CTAs tied to real relationships.

## Fan Connect demo

Seeded by `app/demo/fan_connect_seed.py` (via `seed_demo_data`). Directory membership alone never enables Connect. Private Passport / Connect-off fans stay excluded. Product rules: [FAN_CONNECT.md](./FAN_CONNECT.md).

### Settings

| Fan | Connect | Notes |
| --- | --- | --- |
| Tolu (`fan1`) | on | Same-events discoverable · requests enabled |
| Amaka (`fan2`) | on | Same-events discoverable |
| Chidi (`fan3`) | on | Tech / same-host discoverable |
| Sade (`fan4`) | on | Comedy interests |
| Kunle (`fan5`) | on | Nightlife / premium-public interest (no VIP spend in reasons) |
| Mira (`fan6`) | **off** | Private Passport — excluded |
| Ada (`fan7`) | **off** | Must not appear |
| Bayo (`fan8`) | on | Tech event interests (Passport remains **unlisted** for directory QA) |
| Bode (`fan12`) | on | Blocked by Tolu (demo) |

### Relationships

| Pair | Status | Safe reasons / notes |
| --- | --- | --- |
| Tolu ↔ Amaka | `suggested` | Afrobeats Night Live · both follow DJ Maze |
| Tolu → Sade | `request_sent` | Lagos Comedy Hub · Sunday Comedy Room intro |
| Chidi ↔ Bayo | `connected` | Product Demo Night · Tech Connect Africa · `fan_fan` thread |
| Amaka → Kunle | `request_sent` | Detty Friday Rooftop · Nightlife |
| Ada ↔ Mira | excluded | Mira private · Ada Connect off |
| Tolu ↔ Bode | `blocked` | Excluded from suggestions · messaging disabled · open admin report |

**Note:** Live eligibility requires the **target** Passport to be `public`. The Chidi↔Bayo connected pair is a **seeded relationship exception** so demo can exercise `fan_fan` inbox UX while Bayo stays unlisted for Passport directory QA. Mira + Ada never appear as suggestion partners.

### Seed count keys

Returned by `seed_fan_connect_demo`:

| Key | Demo expectation |
| --- | --- |
| `fan_connect_enabled` | ≥ 6 |
| `fan_connect_suggested` | 1 (Tolu↔Amaka) |
| `fan_connect_pending` | 2 (Tolu→Sade, Amaka→Kunle) |
| `fan_connect_accepted` | 1 (Chidi↔Bayo) |
| `fan_connect_blocked` | 1 (Tolu↔Bode) |
| `fan_connect_messages` | ≥ 5 (system + chat lines) |
| `fan_connect_attachments` | 2 (agenda PNG + schedule PDF) |
| `fan_connect_reports` | 1 |
| `fan_connect_excluded` | 2 (Mira + Ada) |

### Fan↔fan thread (Chidi ↔ Bayo)

System: “You connected through Product Demo Night on Pàdéyá.” (pinned) plus privacy-safe chat lines (demo circle / watch first / builders / see you there / look for you near the demo circle). Chat features seed (`messaging_chat_features_seed.py`): reply, edit, pin, star for Chidi, and a read/unread cursor demo. No phone numbers, VIP spend, or private venues.

Safe demo attachments (generated placeholders in private storage via `app/demo/messaging_attachments_seed.py`):

| File | Kind | Notes |
| --- | --- | --- |
| `product-demo-night-agenda.png` | image | Branded placeholder — not a real venue map |
| `demo-night-schedule.pdf` | PDF | Title-only schedule placeholder |

### Chat feature demos

Applied by `app/demo/messaging_chat_features_seed.py` (after scripted bodies + attachments). Privacy-safe copy only.

| Thread | Features |
| --- | --- |
| Tolu ↔ DJ Maze | Timestamps · edited QR tip (`message_edits`) · reply to doors message · **shared** pinned Afrobeats context · **personal** star for Tolu · `afrobeats-entry-map.png` |
| Chidi ↔ Bayo | Reply · **shared** pinned Fan Connect system line · edited builders line · **personal** star for Chidi · peer read-cursor lag |
| Bayo ↔ Tech (reported) | Reply context on the moderated message · admin report detail · hide/restore QA · no private fields in serializers |

### `/demo` shortcuts

**Fan Connect:** Open Fan Connect · Open Tolu Fan Connect · Open Chidi connections · Open pending requests · Open fan-fan message thread · Open Fan Connect admin reports.

**Message QA:** Open Tolu ↔ DJ Maze thread · Open Chidi ↔ Bayo thread · Open Starred messages (`?filter=starred`) · Open pinned message demo · Open Tolu/Amaka/Chidi/Ada inboxes · host inboxes · Open Reported Thread (admin).

## Demo messaging scenarios

Seeded by `app/demo/messaging_seed.py` (via `seed_demo_data`). One thread per `(fan, host)`. Threads outside the inbox QA allowlist are pruned so dashboard counts stay stable.

| # | Fan ↔ Host | Event / topic | State |
| --- | --- | --- | --- |
| 1 | Tolu ↔ DJ Maze | Afrobeats Night Live · check-in / friends | active · ticket-holder · edit/reply/pin/star · `afrobeats-entry-map.png` (public entry-flow graphic only) |
| 2 | Amaka ↔ DJ Maze | Detty Friday · Vault drop | active · unread for fan |
| 3 | Sade ↔ DJ Maze | Mainland After Dark · inquiry | active · event inquiry (no ticket) |
| 4 | Amaka ↔ Comedy | General follower | active |
| 5 | Sade / others ↔ Comedy | Laugh / Sunday Comedy | active · event inquiry |
| 6 | Tolu ↔ Comedy | Sunday Comedy Room | **blocked** |
| 7 | Mira ↔ DJ Maze | Mainland After Dark | **archived** (fan + host) |
| 8 | Bayo ↔ Tech | Product Demo Night | **reported** (`reviewing`) · `demo-moderation-sample.png` for admin attachment QA |
| 9 | Chidi ↔ Tech | Product Demo / Vault | active · Vault Q&A |
| 10 | Chidi ↔ Mainland | Food & Culture | **reported** (`open`) |
| 11 | Ada ↔ Praise | Worship Night Ibadan | **request** |
| 12 | Tolu ↔ Praise | Choir follow-up | **fan-archived** |
| — | Tolu ↔ Tech / Mainland | Founders / Food Fest | active (ticket / dashboard) |

System messages cover event link, request, archived, blocked, report, Vault refresh.

## Demo inbox states

### Fan inbox QA

| Fan | Login | Expected |
| --- | --- | --- |
| Tolu | `fan1@` | 3 active · 1 unread host reply · 1 archived · 1 blocked |
| Amaka | `fan2@` | 2 active · 1 unread · 1 Vault-related |
| Chidi | `fan3@` | 2 active · 1 reported |
| Ada | `fan7@` | Request filter (`?filter=requests`) · Praise |

### Host inbox QA

| Host | Login | Expected |
| --- | --- | --- |
| DJ Maze | `host@` | 4 threads · 1 unread · 1 archived · event inquiry · ticket-holder |
| Lagos Comedy Hub | `host2@` | 3 · blocked · follower · event inquiry |
| Tech Connect | `tech@` | 3 · Vault · reported · ticket-holder |
| Praise | `praise@` | 1 message request (Ada) — use `?filter=requests` |
| Mainland Vibes | `mainland@` | 2 active |

### Message settings (seeded variety)

| Screen | Login | Highlights |
| --- | --- | --- |
| `/dashboard/messages/settings` | Tolu / Amaka / Chidi | Public messaging off; Tolu blocks Comedy host |
| `/host/messages/settings` | Maze / Comedy | Comedy auto-reply **on**; Maze has a blocked fan |

## Demo admin report examples

`/admin/message-reports` (login `admin@`):

| Case | Status | Notes |
| --- | --- | --- |
| Bayo ↔ Tech Connect | `reviewing` | Demo admin notes; one message `moderation_status=hidden`; attachment `demo-moderation-sample.png` for hide/restore/review QA |
| Chidi ↔ Mainland | `open` | Fan-inbox reported sample |
| Amaka ↔ Comedy | `resolved` | Resolved by demo admin |

Participants see `[Message hidden by moderation]` for hidden bodies. Detail: `/admin/message-reports/[id]` (status + hide/restore + attachment moderation).

### Demo message attachments

Seeded by `app/demo/messaging_attachments_seed.py` (called from Fan Connect + messaging seeds). Files are generated locally (PNG via Pillow, minimal PDF) and stored under private `message_attachments` storage — never under public `/media`.

| Thread | Files | Safety |
| --- | --- | --- |
| Chidi ↔ Bayo (`fan_fan`) | `product-demo-night-agenda.png`, `demo-night-schedule.pdf` | Placeholders only |
| Tolu ↔ DJ Maze | `afrobeats-entry-map.png` | Public gate/check-in/hall labels — **no** street address or private venue screenshot |
| Bayo ↔ Tech (reported) | `demo-moderation-sample.png` | Safe sample for admin moderation metadata |

`seed_messaging_demo` returns `attachments` (≥ 2 when Maze + Tech reported threads seed). No unsafe MIME types, executables, or private address/venue imagery.

Realtime (WS) is not seeded — after login, clients connect to `WS /api/v1/messages/ws` against live demo threads for typing / unread / attach QA. Product protocol: [MESSAGING.md](./MESSAGING.md).

## Open Event Ambassadors (demo)

Seeded by `backend/app/demo/ambassadors_seed.py` (`seed_demo_open_ambassadors`) — idempotent via `demo_entity_markers` (`open_ambassadors/*`). Runs on full seed and on refresh top-up (after merch). Product rules: [AMBASSADORS.md](./AMBASSADORS.md).

| Piece | Value |
| --- | --- |
| Host | DJ Maze (`host@demo.padeye.test`) |
| Event | Afrobeats Night Live (`demo-afrobeats-night-live`) |
| Campaign | **Afrobeats Night Ambassador Drive** (`public_open`, tickets + merch, 10%, leaderboard reward) |
| Participants | Tolu Nightlife Explorer · Amaka Concert Lover · Chidi Tech Regular |
| Codes | `TOLUAFRO` · `AMAKA20` · `CHIDILIVE` (stored lowercase) |

**Funnel ledger (buyers are other fans — no self-referral):**

| Sample | What it demos |
| --- | --- |
| Promo / domain clicks | Click counts toward leaderboard |
| Pending checkout orders | Checkout started (never earns commission) |
| Paid ticket + merch orders | Verified conversions after payment finalize |
| `attributed` / `pending` | Pending commission |
| `approved` / `payable` | Payable commission |
| `reversed` | Refunded / reversed commission |

Also keeps the older curated host ambassadors (`tola-demo`, …) from `_seed_promos_ambassadors` for legacy host-partner QA — separate from this open campaign.

### `/demo` Ambassadors shortcuts

| Shortcut | Session | Route |
| --- | --- | --- |
| Open Ambassadors landing | `fan1@` | `/ambassadors` |
| Open Event with Promote CTA | `fan1@` | `/events/demo-afrobeats-night-live` |
| Open Tolu Ambassador Dashboard | `fan1@` | `/dashboard/ambassador` |
| Open Host Ambassador Dashboard | `host@` | `/host/ambassadors` |
| Open Admin Ambassador Conversions | `admin@` | `/admin/ambassadors/conversions` |

## `/demo` messaging shortcuts

One-click buttons call the normal auth login API with `DemoPass123!`, then navigate:

| Group | Shortcut | Session | Route |
| --- | --- | --- | --- |
| Buyer | Tolu / Amaka / Chidi inbox | `fan1`–`fan3` | `/dashboard/messages` |
| Buyer | Ada message request test | `fan7` | `/dashboard/messages?filter=requests` |
| Host | Maze / Comedy / Tech / Mainland | host emails | `/host/messages` |
| Host | Praise message requests | `praise@` | `/host/messages?filter=requests` |
| Admin | Message reports / reported thread | `admin@` | `/admin/message-reports` (+ detail) |
| Admin | Notifications QA | Amaka (`fan2`) | `/dashboard/notifications` |

## Architecture map

| Piece | Path |
| --- | --- |
| Orchestrator | `app/demo/seed.py` |
| Constants | `app/demo/constants.py` |
| Messaging seed | `app/demo/messaging_seed.py` |
| Attachment demo seed | `app/demo/messaging_attachments_seed.py` |
| Open Ambassadors seed | `app/demo/ambassadors_seed.py` |
| Privacy guard | `app/demo/messaging_privacy.py` |
| Guards / reset | `app/demo/guards.py`, `app/demo/reset.py` |
| Markers | `demo_entity_markers` (scoped wipe) |
| FE hub | `frontend/src/app/demo/page.tsx` |
| Backend tests | `tests/test_demo_seed.py`, `tests/test_demo_messaging_privacy.py`, `tests/test_demo_messaging_attachments_seed.py` |
| FE smoke | `npm run test:messaging` |

There is **no** HTTP seed API and **no** `backend/app/seeds/` package — extend `app/demo/*` only.
