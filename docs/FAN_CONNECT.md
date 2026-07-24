# Fan Connect (Pàdéyá)

Privacy-first way for fans to connect with other fans who share **public** event context — without phone numbers, private venues, or random DMs.

## Purpose

- **Fan Passport** = public event identity and loyalty history.
- **Fan Connect** = optional connect graph + chat unlock after mutual accept.

Copy anchors:

- “Meet fans going where you’re going.”
- “Connect with people attending the same events, following the same hosts, and building their Pàdéyá Passport — without sharing phone numbers or private details.”

Prefer “shared event energy”, “going to the same event”, “fans who follow your hosts”, “build your Pàdéyá circle” — avoid dating-app language.

## Opt-in defaults (private)

| Setting | Default |
|---------|---------|
| `fan_connect_enabled` | `false` |
| `discoverable_for_same_events` | `false` |
| `discoverable_for_similar_interests` | `false` |
| `allow_connection_requests` | `false` |
| `show_shared_hosts` | `true` |
| `show_shared_categories` | `true` |
| `show_shared_public_events` | `true` |
| `show_public_city` | `false` |
| `hide_private_events_always` | `true` (always enforced on ensure) |
| `request_policy` | `same_event` |

**Request policies:** `same_event` · `same_host` · `public_passports` · `nobody`

**Limits:** intro ≤ 280 chars · ≤ 10 requests/hour · suggestions cap 12 · **directional** decline cooldown (requester-only; admin default **30 days**, 0–365).

### Decline cooldown (directional)

When **B** declines **A**’s request:

- **A** cannot send another request to **B** until `requester_cooldown_until` (admin default or per-decline choice).
- **A** still sees **B** in suggestions when privacy allows (disabled cooldown CTA).
- **B** sees **Send connect request** with helper copy after declining **A**.
- **B** may send a new request to **A** immediately (new pending **B → A**).
- Decline is **not** a block, mutual hide, or two-way cooldown.

Admin: `/admin/fan-connect/settings` · runtime key `fan_connect_decline_cooldown_days` (0–365). User decline modal: platform default, 7 / 30 / 90 / 365 days.

API: `GET /fan-connect/decline-cooldown-options` · `POST …/decline` body `{ "cooldown_days": optional }` · `can-connect` includes `cooldown_until`, `can_send_connect_request`, `viewer_declined_target`.

## Directory vs Connect

| Surface | Gate |
|---------|------|
| `/fans` directory | Passport `public` + `appear_in_directory` |
| Fan Connect | Explicit Connect opt-in + eligibility below |

Public Passport ≠ Connect enabled. Directory membership ≠ connection requests allowed. See [FAN_PASSPORT.md](./FAN_PASSPORT.md).

## Self-actions (own Passport)

Users **cannot** Fan Connect with themselves. Enforcement:

- Eligibility denial code `self` — copy: “You can’t connect with yourself.”
- `POST /fan-connect/requests` to own username → `400`
- Suggestions never include the viewer
- Malformed self `fan_connections` rows are excluded from connection counts
- Report / block of self → `400` (“You can’t report yourself.” / “You can’t block yourself.”)

Own public Passport shows **Edit Passport** / **Personal dashboard** / **Share profile** instead of Connect / Message / Report / Block. See [FAN_PASSPORT.md#own-fan-passport](./FAN_PASSPORT.md#own-fan-passport).

## Eligibility

### Target (must pass for suggestions / new requests)

1. Active user, not messaging-suspended
2. Passport exists with username; `visibility === public` (private/unlisted → denied)
3. Not admin-hidden
4. `fan_connect_enabled`
5. `allow_connection_requests` (and `request_policy` ≠ `nobody`)
6. For discovery: `discoverable_for_same_events` **or** `discoverable_for_similar_interests`
7. Neither side blocked (`fan_connection_blocks` **or** `message_blocks`)
8. No open request / already connected / decline cooldown (lifecycle)
9. No prior serious report hard-stop (≥3 open reports **or** serious keyword match)
10. ≥1 safe shared public reason with viewer
11. Matching score ≥ **40**

### Actor (viewer / requester)

- Must have `fan_connect_enabled` and a Passport username
- Actor Passport need **not** be public (only the target must be)

### Common denial codes

`self` · `inactive` · `blocked` · `messaging_suspended` · `prior_serious_report` · `actor_connect_off` · `target_connect_off` · `actor_passport_missing` · `passport_missing` · `admin_hidden` · `passport_not_public` · `connection_blocked` · `request_pending` · `already_connected` · `decline_cooldown` · `target_requests_off` · `target_policy_nobody` · `target_not_discoverable` · `policy_requires_shared_event` · `policy_requires_shared_host` · `no_shared_public_context`

## Matching algorithm (`FanConnectScoringService`)

Range **0–100**. Cards shown only when score ≥ 40, both eligible, and ≥1 safe reason.

| Signal | Points |
|--------|--------|
| Same upcoming public event | +35 |
| Both ticketed to that upcoming event | +20 extra |
| Same completed public checked-in event | +15 |
| Follows same host | +12 each, max +24 |
| Shared favorite category/scene | +8 each, max +24 |
| Same public city/area (both `show_public_city`) | +10 |
| Shared public badge | +6 each, max +18 |
| Both recently active (30 days) | +8 |
| Mutual accepted connection | +10 |

| Penalty | Points |
|---------|--------|
| Recently declined | −40 |
| Too many outgoing requests (≥5) | −25 |
| Low trust / new account (&lt;7 days) | −15 |
| Spam / report risk | −30 |

**Labels:** 80–100 Strong connection · 60–79 Good connection · 40–59 Similar interests · &lt;40 hidden (`score_band`: `strong` / `good` / `similar` / `hidden`).

## Safe reasons vs unsafe reasons

### Safe reason codes (`SAFE_REASON_CODES`)

Stored in `reasons_json` / shown on cards:

| Code | Example label |
|------|----------------|
| `shared_upcoming_event` | “You’re both going to Afrobeats Night Live” |
| `shared_checked_in` | “You both have verified check-ins at tech events” / “You’re both checked in at …” |
| `shared_public_event` | “You share public event check-ins” |
| `shared_host` | “You both follow DJ Maze” |
| `shared_category` | “You both like comedy events” |
| `shared_city` | “You’re both into events in Lagos” |
| `shared_badge` | “You both earned event merch badges” / named badge |

### Never generated / never exposed

Private attendance · hidden venues · exact private location · ticket type · VIP/table · order/payment/refund/spend · phone/email · shipping · CRM notes · locked Vault content · full message bodies (analytics / notifications).

City appears only when **both** fans opted in (`show_public_city`). `hide_private_events_always` is always enforced.

Intro text is filtered for contact patterns (WhatsApp, phone, email, URLs, etc.).

## Connection lifecycle

| Status | Meaning | Messaging |
|--------|---------|-----------|
| `suggested` | System recommendation; no relationship yet | No |
| `request_sent` | Current user sent a request | No |
| `request_received` | Viewer-facing alias when current user received a request (DB stores `request_sent`) | No |
| `connected` | Mutual accept | Yes — `fan_fan` thread |
| `declined` | Declined; **requester-only cooldown** (`requester_cooldown_until`) | No |
| `blocked` | Excluded from suggestions | No |
| `removed` | Previous connection ended; reconnect required | No |

### Actions

| Action | Effect |
|--------|--------|
| Send request | → `request_sent` (from suggested / removed / declined after cooldown) |
| Accept request | → `connected`; unlocks `fan_fan` thread + system line |
| Decline request | → `declined` + cooldown |
| Cancel request | → `removed` (no decline cooldown) |
| Remove connection | → `removed`; closes `fan_fan` messaging |
| Block fan | → `blocked`; excluded from suggestions; messaging disabled |
| Report fan | Opens `fan_connection_reports` (`open`); status unchanged unless also blocked |

Report statuses: `open` · `reviewing` · `resolved` · `dismissed`.

## `fan_fan` messaging rules

See also [MESSAGING.md](./MESSAGING.md) (shared WebSocket, attachments, typing, unread, chat features).

- Chat **only** when connection status is `connected` and `removed_at` is null (`can_send_message` / Fan Connect gate)
- Accept creates/unlocks a `fan_fan` thread and posts: `You connected through [safe reason] on Pàdéyá.`
- Emits WS `connection.accepted` so inboxes unlock without reload
- No thread, messages, **or attachments** before accept (`can_attach` false until connected)
- Remove closes messaging; block disables send + active WS events (pin/edit/reply follow the same send gate)
- Inbox shows a **Fan Connect** badge + safe connection context (never VIP/spend/private venue)
- Stay in-app — no phone/email/WhatsApp exposure; attachment notifications use generic copy only
- **Chat features on `fan_fan`:** same UX as fan↔host (timestamps, edit, reply, shared pins, personal stars, action menu) — permissions stay connection-only; pins are shared in-thread; stars remain private to each fan
- **Connect reports** (`/admin/fan-connect/reports`) ≠ **message reports** (`/admin/message-reports`). Admins open `fan_fan` message threads / attachments only when reported via messaging.

## Block / report behavior

| Surface | Behavior |
|---------|----------|
| User block | `POST /fan-connect/block` → connection `blocked`; future suggestions excluded; messaging off. **Cannot block yourself.** |
| User report | `POST /fan-connect/report` → `fan_connection_reports` row with safe context. **Cannot report yourself.** |
| Admin | Overview, blocks, reports list/detail/resolve, per-user moderation history, soft-disable Connect (settings off — no hard delete) |
| Message moderation | Reported `fan_fan` threads only via `/admin/message-reports` |

Permission: user `fan_connect.use`; admin `admin.full_access`.

## Privacy guarantees

- Defaults off; directory ≠ Connect
- Target must be public Passport; private/unlisted/admin-hidden never suggested
- Self Connect / report / block denied; self never suggested or counted as a connection
- Shared context = public-safe events / hosts / categories / dual-opt-in city / public badges only
- `reasons_json` and suggestion cards never carry unsafe fields
- Notifications never include private event details or full message bodies
- Analytics never track private attendance, venues, ticket types, spend, contact, Vault bodies, or message text — see [ANALYTICS_TRACKING_PLAN.md](./ANALYTICS_TRACKING_PLAN.md)

Also indexed in [PRIVACY.md](./PRIVACY.md).

## Notifications

In-app via `GET /messages/notifications` (`fan_connect.*`).

| Event | Kind | Title / body pattern |
|-------|------|----------------------|
| New request | `fan_connect.request` | “{Name} sent you a Fan Connect request.” |
| Accepted | `fan_connect.accepted` | “{Name} accepted your Fan Connect request.” |
| Declined | `fan_connect.declined` | “{Name} declined your Fan Connect request.” |
| Removed | `fan_connect.removed` | “{Name} removed your Fan Connect connection.” |
| New fan↔fan message | `fan_connect.message` | Title: “New message from a connected fan” · Body: “You have a new message from a connected fan on Pàdéyá.” |

## Analytics

Client: `fan_connect_page_view`, `fan_connect_settings_updated`, `fan_connect_suggestion_impression`, `fan_connect_suggestion_clicked`.

Trusted: `fan_connect_enabled` / `_disabled`, request sent/accepted/declined, connection removed, blocked/reported, `fan_fan_message_thread_created`, `fan_fan_message_sent`.

## Demo data

Seeded by `app/demo/fan_connect_seed.py`. See [DEMO_DATA.md](./DEMO_DATA.md#fan-connect-demo).

Highlights: Tolu↔Amaka suggested · Tolu→Sade pending · Chidi↔Bayo connected + `fan_fan` · Amaka→Kunle pending · Tolu↔Bode blocked + report · Mira + Ada excluded (`fan_connect_excluded: 2`).

## API

All under `/api/v1`. Suggestion cards include public display name, username, avatar, tagline, safe city (if allowed), public badges, match label, score band, safe reasons, connection status, and CTA — never phone/email, payments, hidden venues, or private attendance.

| Path | Purpose |
|------|---------|
| `GET/PATCH /fan-connect/settings` | Own settings |
| `GET /fan-connect/suggestions` | Suggestions (`mode`, `lat`/`lng`/`radius_km` one-time, `event_id`, `category`, `city`, `area`, `limit`, `page`/`cursor`). Default `mode=mixed` uses a diversity mixer (strong / shared-event / nearby / FoF / fresh quotas) so distance alone cannot dominate. |
| `POST /fan-connect/suggestions/{user_id}/dismiss` | Not interested — exclude for 60 days (−30 after window) |
| `POST /fan-connect/suggestions/{user_id}/more-like-this` | Personalization feedback (+5 similar views) |
| `POST/GET/DELETE /fan-connect/location/preference` | Explicit city/area preference only — **never** auto-store browser GPS from suggestions GET |
| `GET /fan-connect/events` | Public-safe nights for Connect UI |
| `GET /events/{event_slug}/fan-connect` | Event-scoped suggestions |
| `GET /fan-connect/can-connect/{username}` | Eligibility + shared context |
| `GET/POST /fan-connect/requests` | List / create |
| `POST …/requests/{id}/accept\|decline\|cancel` | Request lifecycle |
| `GET /fan-connect/connections` | Connected |
| `POST …/connections/{id}/remove` | Soft end → `removed` |
| `POST …/connections/{id}/disconnect` | Alias of remove |
| `POST /fan-connect/block` | Block fan (`204`) |
| `POST /fan-connect/report` | Report fan |
| `GET /admin/fan-connect/overview` | Admin moderation counts |
| `GET /admin/fan-connect/blocks` | Block history (display names) |
| `GET /admin/fan-connect/reports` | Admin report list (+ safe connection context) |
| `GET /admin/fan-connect/reports/{id}` | Report detail |
| `POST /admin/fan-connect/reports/{id}/resolve` | Resolve / dismiss |
| `GET /admin/fan-connect/users/{id}/moderation` | Block / report history for a fan |
| `POST /admin/fan-connect/users/{id}/disable` | Soft-disable Connect |
| `GET /admin/fan-connect/debug/score` | Admin score breakdown (bands/keys; no raw GPS) |

Legacy aliases also exist under `/fan-connect/admin/*` for overview/blocks/reports.

Full inventory: [API.md](./API.md#fan-connect). Schema: [DATABASE.md](./DATABASE.md#fan-connect). Routes: [FRONTEND_ROUTES.md](./FRONTEND_ROUTES.md).

## Frontend

| Path | Purpose |
|------|---------|
| `/connect` | Hub: hero + same events / hosts / scenes / requests / connections |
| `/connect/suggestions` | Shared event energy |
| `/connect/events` | Public-safe nights for Connect |
| `/connect/requests` | Incoming / outgoing requests |
| `/connect/connections` | Accepted connections |
| `/connect/settings` | Privacy & settings — off by default |
| `/dashboard/connect/*` | Redirect aliases → `/connect/*` |
| `/events/[slug]` | Optional “Going too? Connect with fans.” — 3-card preview; hidden for private/hidden/preview; enable CTA if Connect is off |
| `/admin/fan-connect` | Admin overview |
| `/admin/fan-connect/reports` | Connect reports + safe context + disable |
| `/admin/fan-connect/blocks` | Block history |
| `/admin/fan-connect/users/[userId]` | Per-fan block / report history |
| `/admin/message-reports` | Moderate `fan_fan` threads **only when reported** as messages |
| Public `/f/[username]` | **Visitor:** Connect / Message / report·block. **Own Passport:** Edit Passport · Personal dashboard · Share profile (no self social CTAs) |

`FanConnectCard` shows avatar, name, @username, tagline, safe city, badges, match label, safe reasons, and CTAs (Connect / Request sent / Accept / Decline / Message / View Passport). Message CTA appears only when `connected` with a `thread_id`.

Chat uses the existing fan messages inbox (`fan_fan` threads).

Frontend smoke: `npm run test:fan-connect` (`frontend/scripts/fan-connect-smoke.mjs`).
