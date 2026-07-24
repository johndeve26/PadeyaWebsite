# Pàdéyá local demo content

Local-development-only seed data for end-to-end demos and QA. **Never runs automatically in production.**

**Product docs (canonical):** [docs/DEMO_DATA.md](../../../docs/DEMO_DATA.md) · [docs/MESSAGING.md](../../../docs/MESSAGING.md) · [docs/PRIVACY.md](../../../docs/PRIVACY.md).

## Architecture

| Piece | Path |
| --- | --- |
| CLI seed | `python -m scripts.seed_demo_data` (`--reset` optional) |
| CLI reset | `python -m scripts.reset_demo_data` |
| Orchestrator | `app/demo/seed.py` → `seed_demo_data()` |
| Constants | `app/demo/constants.py` (emails, hosts, password, `demo-` prefix) |
| Guards | `app/demo/guards.py` (blocks `APP_ENV=production`) |
| Reset | `app/demo/reset.py` |
| Messaging | `app/demo/messaging_seed.py` (idempotent fan↔host threads) |
| Messaging chat features | `app/demo/messaging_chat_features_seed.py` (edit / reply / pin / star demos) |
| Fan Connect | `app/demo/fan_connect_seed.py` (settings, suggestions, requests, `fan_fan` thread) |
| Host team | `app/demo/team_seed.py` (DJ Maze admin / gate / pickup / viewer + pending invite) |
| Open Ambassadors | `app/demo/ambassadors_seed.py` (Afrobeats Night Ambassador Drive · TOLUAFRO / AMAKA20 / CHIDILIVE) |
| Analytics | `app/demo/analytics_seed.py` |
| FE helper | `/demo` (`frontend/src/app/demo/page.tsx`) |

There is **no** `backend/app/seeds/` package and **no** HTTP seed API — extend `app/demo/*` only.

### Full seed creates

Users · named fan personas (`toluwave`…`bayocampus` on `fan1`–`fan8`) · volume fans (`fan9`–`fan20`) · hosts (DJ Maze Icon, Comedy/Tech Established, Praise/Mainland Rising) · events · tickets · check-ins · reviews · followers · Vault · Fan Passports · messaging threads/notifications/reports · **Fan Connect** (opt-in settings, suggested/pending/connected/blocked pairs, Chidi↔Bayo `fan_fan` thread) · **DJ Maze host team** (Event Ops Manager, Gate Scanner, Pickup Staff, Sponsor Observer, pending invite) · **Open Event Ambassadors** (DJ Maze · Afrobeats Night Ambassador Drive · Tolu/Amaka/Chidi codes + clicks/checkout/conversions) · memories · analytics · sponsorships · support demo cases · Legacy studio · **event merch** (advanced commerce catalog + persona flows via `app/demo/merch_seed.py` / `merch_commerce_seed.py` — bundles, Vault exclusive, QR pickup, abandoned carts, shipping, `LAUGH10`, reviews).

### Product context for messaging

Each main host has **2–3 showcase events** (≥1 upcoming + ≥1 completed), ticket holders (≈5 per showcase event; global filler distributed across upcoming showcase events), check-ins + verified reviews on completed showcase, ≥5 followers, Vault drops, Legacy stats/tiers, and sponsor-ready flags where `DEMO_HOSTS` says so (Praise is intentionally not sponsor-ready).

Each main fan persona (`DEMO_PERSONA_CONTEXT`) has followed hosts (CRM), upcoming tickets, attended/checked-in events, verified reviews where scripted, badges, Vault unlocks where scripted (Amaka/Kunle paid Maze set; Tolu Mainland teaser), and Passport visibility (public / private / unlisted). This keeps Message Host / Message Fan CTAs tied to real product relationships.

Demo emails (`@demo.padeye.test`) are login-only — never written onto public Passport/Legacy surfaces.

### Rerun rules

| Command | Behavior |
| --- | --- |
| `seed_demo_data` (no flag) | If marker `seed/complete` exists: refresh Studio/taxonomy/placements/Legacy/Vault + **idempotent** persona context + passport + messaging + open Ambassadors top-up. **Does not** re-run full commerce loops (avoids duplicate bulk tickets). |
| `seed_demo_data --reset` | Wipe demo users/hosts/events/orders/tickets, then full seed. |
| Messaging alone | Safe to call `seed_messaging_demo` repeatedly — skips existing `(fan, host)` threads. |

Do **not** delete only the complete marker and re-run full seed without `--reset` — commerce can duplicate orders.

## Safety

- Seed/reset **refuse** when `APP_ENV=production`.
- Set `DEMO_MODE=true` for the frontend `/demo` helper page.
- Demo emails use `@demo.padeye.test`.
- Demo event slugs use the `demo-` prefix.
- Images are local SVG assets under `frontend/public/demo/` (no external URLs).
- Payments use mocked finalize paths (no live Paystack charges).
- Email: use **Admin → Email settings** log / dev mode locally (no inbox delivery).

## Vault coverage

Each demo host ships published Vault drops with mixed access (`free`, `followers_only`, `one_time_unlock`, `ticket_holder_only`, `checked_in_attendee_only`, `vip_ticket_holder_only`, `invite_only`):

| Host | Drops |
| --- | --- |
| DJ Maze | Unreleased Afrobeats DJ Set, BTS Afrobeats, VIP Photo Gallery, Mainland After Dark Teaser, Detty Friday ticket-holder recap + admin-hidden sample |
| Lagos Comedy Hub | Early Access: Laugh Lagos Live, Backstage: Sunday Comedy Room (`DEMO-INVITE`) |
| Mainland Vibes | Food & Culture Fest Recap, Creative Market Teaser (paid; locked for Demo Buyer) |
| Tech Connect Africa | Founder Mixer Slide Deck (free), Product Demo Night Replay (check-in) |
| Praise Experience | Worship Night Ibadan Rehearsal (free), Choir & Community Backstage (VIP) |

### Showcase events (messaging-linked)

DJ Maze: Afrobeats Night Live · Detty Friday Rooftop · Mainland After Dark  
Comedy: Laugh Lagos Live · Sunday Comedy Room  
Tech: Founders Mixer Lagos · Product Demo Night  
Praise: Choir & Community Live · Worship Night Ibadan  
Mainland: Mainland Food & Culture Fest · Lagos Creative Market  

Each has tickets/orders; completed ones also have check-ins + reviews. Location modes are `full_public` or `area_only` only (no secret streets in public serializers).

Demo Buyer: paid unlock + invite redeem + follower/ticket/VIP/check-in unlocks where entitled; Vault views + `vault_sale` earnings seeded.

## Messaging coverage

Rich fan↔host inbox data (`app/demo/messaging_seed.py`). Threads outside the inbox QA allowlist are pruned so dashboard counts stay stable.

### Fan inbox QA

| Fan | Conditions |
| --- | --- |
| Tolu (`toluwave`) | 3 active · 1 unread host reply · 1 archived · 1 blocked |
| Amaka (`amakaconcerts`) | 2 active · 1 unread · 1 Vault-related (Detty) |
| Chidi (`chiditech`) | 2 active · 1 reported |

### Host inbox QA

| Host | Conditions |
| --- | --- |
| DJ Maze | 4 threads · 1 unread fan msg · 1 archived · 1 event inquiry · 1 ticket-holder |
| Lagos Comedy Hub | 3 threads · 1 blocked · 1 follower · 1 event inquiry |
| Tech Connect Africa | 3 threads · 1 Vault · 1 reported · 1 ticket-holder |
| Praise Experience | 1 message request (Ada) |
| Mainland Vibes | 2 active threads |

System messages cover event link, request, archived, blocked, report, Vault refresh (centered UI).

### Host Legacy ↔ messaging

Message Host CTA on `/@djmaze`, `/@lagoscomedyhub`, `/@techconnectafrica`, `/@praiseexperience`, `/@mainlandvibes`:

| Host | Followers | Ticket / check-in | Public → request | Auto-reply |
| --- | --- | --- | --- | --- |
| DJ Maze | yes | yes | yes | off |
| Lagos Comedy Hub | yes | yes | yes | on (safe demo text) |
| Tech Connect Africa | no | yes | yes | off |
| Praise Experience | yes | yes | yes (requests) | off |
| Mainland Vibes | yes | yes | yes | off |

Logged-out click → `/login?next=/@{username}`. Existing threads reopen; blocked/denied show safe errors.

### Fan Passport ↔ messaging

| Fan | Passport | Directory | Hosts may Message Fan when |
| --- | --- | --- | --- |
| Tolu | public | yes | followed **or** attended (not cold public) |
| Amaka | public | yes | hosts she **follows** |
| Chidi | public | yes | hosts she **attended** |
| Kunle | public | no | hosts he **attended** only |
| Mira | private | no | no public Message Fan |
| Ada | private | no | Ada messages hosts via **event pages** |
| Bayo | unlisted | no | direct `/f/bayocampus` link; Message Fan if relationship + settings allow |

CTA: `HostMessageFanButton` on public/unlisted Passports only — hidden unless `/host/messages/can-message-by-username` allows.

### Message settings screens

| Screen | Login as | Highlights |
| --- | --- | --- |
| `/dashboard/messages/settings` | Tolu / Amaka / Chidi | Public messaging **off**; requests vary; Tolu has blocked Comedy host |
| `/host/messages/settings` | DJ Maze / Comedy | Comedy **auto-reply on**; Maze has a blocked fan; Tech followers **off** |

API: `GET/PATCH /messages/settings` includes `blocked_users` (display names only).

### Admin message reports

`/admin/message-reports` demo rows:

| Case | Status | Notes |
| --- | --- | --- |
| Bayo ↔ Tech Connect | `reviewing` | reason `other`, demo admin notes, one message `moderation_status=hidden` |
| Chidi ↔ Mainland | `open` | fan inbox reported sample |
| Amaka ↔ Comedy | `resolved` | `resolved_by` demo admin, note “Demo resolved report.” |

Participants see `[Message hidden by moderation]` for hidden bodies. Detail page supports status changes + hide/restore.

### Message notifications

Safe summaries only (no full message bodies), each linked to the correct thread, with read + unread examples:

| Title | Audience |
| --- | --- |
| New message from DJ Maze | Amaka (unread) |
| Message request from Ada First Timer | Praise host (unread) |
| Host replied to your event question | Sade / Chidi (read) |
| New message about Afrobeats Night Live | DJ Maze host (unread) |
| Your message report is being reviewed | Bayo (unread) |
| Your conversation was archived | Tolu (read) |
| New Vault-related reply from Tech Connect Africa | Chidi (unread) |

Privacy: **Pàdéyá** only — no emails, phones, WhatsApp, bank details, payment links, private addresses, locked Vault bodies, order/payment IDs, or CRM notes in message views. Seed copy uses safe placeholders (`Open your Pàdéyá ticket`, `Check your dashboard`, `Use your QR code at check-in`, Vault unlock/refresh lines) and never pushes chats off-platform. Guard: `app/demo/messaging_privacy.py`.

QA: `/dashboard/messages`, `/host/messages`, `/admin/message-reports` after seed.

### `/demo` messaging shortcuts

One-click buttons on `/demo` call the normal `/auth/login` flow with `DemoPass123!`, then navigate:

| Group | Shortcut | Session | Route |
| --- | --- | --- | --- |
| Buyer | Tolu / Amaka / Chidi inbox | `fan1`–`fan3` | `/dashboard/messages` |
| Buyer | Ada message request test | `fan7` | `/dashboard/messages?filter=requests` |
| Host | Maze / Comedy / Tech / Mainland | host emails | `/host/messages` |
| Host | Praise message requests | `praise@` | `/host/messages?filter=requests` |
| Admin | Message reports / reported thread / users | `admin@` | `/admin/message-reports` (+ detail) · `/admin/users` |
| Admin | Notifications | Amaka (`fan2`) | `/dashboard/notifications` → message notifications |

### Frontend display (seeded QA)

Demo inboxes should show names, avatars (host + fan), related event chips/mini-cards, last-message previews, unread + status badges (request / archived / reported / blocked), relative timestamps, system messages, composers, report/block, and privacy reminder. Empty state remains for accounts with no threads.

## Event Studio coverage

Demo events are intentionally rich so every Studio step has data to exercise:

- Location privacy mix: full public, area-only, hidden until payment, 24h reveal, secret / manual, online-only, hybrid
- Agenda, lineup (performers/speakers), checkout questions
- Entry requirements, dress code, accessibility, parking, refund/cancellation copy
- Ticket benefits + table perks
- Gallery / social share media, sponsors, SEO + social metadata

Re-seed with `--reset` (or re-run seed) to refresh thin older rows.

## Commands

From `backend/` (venv active, DB migrated):

```bash
# Seed (idempotent — skips if already complete)
python -m scripts.seed_demo_data

# Clear demo data, then seed again
python -m scripts.seed_demo_data --reset

# Clear demo data only
python -m scripts.reset_demo_data
```

## Demo password

All demo users: `DemoPass123!`

See root README and `/demo` (when `DEMO_MODE=true`) for account emails and flow links.
