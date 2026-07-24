# Fan Passport

**Fan Passport** is the fan-side counterpart to Host Legacy Pages.

| Surface | Meaning |
|--------|---------|
| Host Legacy Page | Public reputation for hosts |
| Fan Passport | Event identity and loyalty history for attendees |
| Fan Passport Directory | Opt-in discovery of **public** Fan Passports (`/fans`) |
| Fan Connect | Optional peer graph + chat — **not** the same as directory |

Product names: **Fan Passport Directory**, **Public Fan Passports**, **Discover fans on Pàdéyá**.

Do **not** call this “All fans”, “User list”, “Every fan”, or a “Database of fans”.

## Directory ≠ Fan Connect

| Surface | Opt-in | Purpose |
|---------|--------|---------|
| Directory (`/fans`) | `visibility=public` + `appear_in_directory` | Discover public Passports |
| Fan Connect (`/connect`) | `fan_connect_enabled` (+ request/discover flags) | Meet fans with shared **public** event context |

- Directory membership never enables Connect.
- Connect suggestions / requests require the **target** Passport to be `public` (unlisted/private are excluded), plus Connect settings — see [FAN_CONNECT.md](./FAN_CONNECT.md).
- **Visitor** public Passport pages may show **Connect** / **Message** / report·block CTAs (`ConnectButton` + safety menu). Message appears only after an accepted Connect relationship unlocks a `fan_fan` thread.
- **Own** public Passport never shows Connect / Message / Follow / Report / Block — see [Own Fan Passport](#own-fan-passport).

## Own Fan Passport

Users may **view**, **preview**, **edit**, and **share** their own public Fan Passport (`/f/{username}` when visibility allows). Ownership is by **user id**:

`isOwnPassport = current_user.id === passport.user_id`

| Allowed on own Passport | Not allowed on own Passport |
|-------------------------|-----------------------------|
| View public content (header, seal, stats, stamps, badges, reviews, vault titles) | Fan Connect request to self |
| Edit Passport → `/dashboard/passport/settings` | Fan↔fan Message / thread with self |
| Personal dashboard → `/dashboard` | Follow self (fan↔fan) |
| Share profile (public link) | Report / block self |

**Own Passport CTA copy**

- Title: “This is your Fan Passport”
- Description: “Preview how your public fan identity appears on Pàdéyá.”
- Buttons: **Edit Passport** · **Personal dashboard** · **Share profile**

**Directory card:** own row shows a **You** badge and Edit / View Passport only — Connect, Message, Report, and Block are hidden.

Exact product errors (backend): “You can’t connect with yourself.” · “You can’t message yourself.” · “You can’t follow yourself.” · “You can’t report yourself.” · “You can’t block yourself.”

Self is never included in Fan Connect suggestions and never counted as a connection (including malformed self-rows).

## Privacy (critical)

### Visibility

| Mode | `/f/{username}` | Listed on `/fans` |
|------|-----------------|-------------------|
| `private` (default) | **404** | Never |
| `unlisted` | Direct link only | Never |
| `public` | Accessible | Only if `appear_in_directory=true` |

### Directory opt-in

- Separate flag: `appear_in_directory` (default **false**).
- Listing requires **all** of: `visibility=public`, `appear_in_directory=true`, active user, username set, not admin-hidden.
- Setting visibility to private/unlisted clears `appear_in_directory`.
- Fans can turn directory visibility off anytime from settings.

### Admin moderation

- Admins may hide a Fan Passport (`admin_hidden_at` / reason): removes from `/fans` and returns 404 on `/f/{username}`.
- Restore clears the hide. Directory listing still requires the fan’s own opt-in.
- Actions are audited (`passport.admin.hide` / `passport.admin.restore`).

### Never expose on public Passport / directory

- email, phone, contact info
- order IDs, payment / refund data
- exact ticket purchases / ticket type names when sensitive
- private / unlisted / secret-location attendance
- hidden venues or street addresses
- locked Vault content (unlock **titles** only when allowed)
- private notes, CRM segments
- internal-only fields beyond safe public IDs already used elsewhere

Public serializers live in `app/passport/public_service.py` and `app/passport/directory_service.py`.

## Routes

| Kind | Path |
|------|------|
| Directory | `/fans` |
| Private dashboard | `/dashboard/passport` |
| Settings | `/dashboard/passport/settings` |
| Public page | `/f/[username]` |
| Admin moderation | `/admin/fans` |

## API

| Method | Path | Notes |
|--------|------|-------|
| GET | `/api/v1/fans` | Directory — public + opt-in only |
| GET | `/api/v1/dashboard/passport` | Private full Passport |
| GET/PATCH | `/api/v1/dashboard/passport/settings` | Profile + Public discovery |
| GET | `/api/v1/f/{username}` | Public / unlisted page (404 if private/hidden) |
| GET | `/api/v1/f/{username}/activity` | Safe attended events |
| GET | `/api/v1/f/{username}/badges` | Earned badges when allowed |
| GET | `/api/v1/admin/fans` | Admin list (moderation) |
| PATCH | `/api/v1/admin/fans/{user_id}/hide` | Hide (reason required) |
| PATCH | `/api/v1/admin/fans/{user_id}/restore` | Restore |

### Directory query params

`q`, `city`, `category`, `badge`, `sort` (`recently_active` · `most_badges` · `most_events` · `most_reviews` · `newest`), `page`, `limit`, `has_reviews`, `has_vault_unlocks`, `min_events`, `max_events`.

## Settings (“Public discovery”)

- Profile visibility: Private / Unlisted / Public
- Show my Fan Passport in the public directory (`appear_in_directory`)
- Public display name, username, avatar, tagline
- Section toggles: badges, followed hosts, public reviews, city/category stats, attended event summaries, Vault unlocks
- Hide private events always (default **true**)

Defaults: `visibility=private`, `appear_in_directory=false`, `hide_private_events_always=true`.

## Merch badges & proof

Merch purchase badges (First Merch Buy, Merch Collector, VIP Pack Owner, Event Drop Supporter, Vault Merch Member, Sponsor Drop Supporter, Culture Fest Collector, Founder Mode Gear) award after **verified payment**. None require pickup today. Refunds revoke merch badges when criteria fail. Public pages hide badges when `show_badges` is off.

Safe merch proof summaries (counts only), e.g. “Supported 3 event merch drops”, “Collected merch from 2 hosts”. Host Legacy aggregates: “N merch items sold”, “N fans collected event merch” — never buyer identities or spend.

## Legacy & Vault

- Fans follow hosts from Legacy Pages; Passport lists followed Legacy links when allowed.
- **Host-as-Fan:** host **owners** cannot follow or publicly review their **own** host; they remain Personal users and may follow/review other hosts normally — [HOST_AS_FAN.md](./HOST_AS_FAN.md) · [REVIEWS.md](./REVIEWS.md).
- Reviews on public Passport never reveal private/secret event attendance.
- Vault section shows unlock **titles** only — never locked payloads.

## Analytics

Client signals (no private PII): `fan_directory_view`, `fan_directory_search`, `fan_directory_filter_used`, `fan_card_impression`, `fan_card_click`, `fan_passport_view`, `fan_directory_opt_in`, `fan_directory_opt_out`.

## Demo

After demo seed:

| Username | Visibility | Directory |
|----------|------------|-----------|
| `demobuyer` | private | no |
| `toluwave` | public | yes |
| `amakaconcerts` | public | yes |
| `chiditech` | public | yes |
| `sadecomedy` | public | yes |
| `kunlevip` | public | **no** (public profile, directory off) |
| `miralagos` | private | no |
| `adafirsttimer` | private | no |
| `bayocampus` | unlisted | no |
| `bodefoodie` | public | yes |
| `yemidirect` | public | **no** (direct link only) |
| `kofiul` | unlisted | no |
| `zainabquiet` | private | no |

Fan Connect demo (separate seed): Mira + Ada excluded; Chidi↔Bayo may be seeded as `connected` for `fan_fan` inbox QA even while Bayo stays unlisted — live eligibility still requires target `public`. See [DEMO_DATA.md](./DEMO_DATA.md#fan-connect-demo).
