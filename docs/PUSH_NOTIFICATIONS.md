# Pàdéyá browser push notifications

Brand: **Pàdéyá**. Product overview (in-app + email + push channels): [NOTIFICATIONS.md](./NOTIFICATIONS.md). Lifecycle: [CRUD_MATRIX.md](./CRUD_MATRIX.md). Ops: [OPERATIONS.md](./OPERATIONS.md).

This doc is the push deep-dive: permission UX, iPhone/iPad Home Screen support, VAPID, subscriptions, outbox, worker, privacy, templates, admin test, unsupported-browser fallback, and troubleshooting.

## Architecture

```
Product event (after payment verify where required)
  → notify_user() / enqueue_push()
  → push_events (pending | skipped)
  → process_push_outbox.py (worker)
  → provider: log | web_push (pywebpush + VAPID)
  → active push_subscriptions on the user’s devices
  → service worker (public/sw.js) shows notification
  → notificationclick → same-origin action_url
```

Module: `backend/app/push/`

| File | Role |
|---|---|
| `service.py` | Register/unregister, enqueue, drain, test push, cleanup |
| `provider.py` | `LogPushProvider` · `WebPushProvider` · safe `PushPayload` |
| `privacy.py` | Context whitelist, scrub copy, safe action URLs |
| `templates.py` | Short title/body catalog + kind aliases |
| `worker.py` | Drain helpers + subscription maintenance |
| `router.py` | User VAPID / subscriptions / preferences |
| `admin_router.py` | Admin settings, test, deliveries, events |
| `models.py` | `PushEvent` outbox |

Related: `app/notifications/prefs.py` (gating) · `app/notifications/triggers.py` · `app/notifications/settings_service.py` (VAPID CRUD) · `app/notifications/push.py` (encrypt keys / failure handling).

## Browser permission behavior

**Never request permission on page load or first visit.**

1. User opens `/dashboard/settings/notifications` — sees current state only (no prompt).
2. User clicks **Enable notifications**.
3. Browser permission prompt appears (`Notification.requestPermission()` only here).
4. If accepted: create push subscription → save to backend → success state (“Enabled on this device”).
5. If denied: show **Notifications are blocked for this browser. You can enable them later in your browser or device settings.**
6. User can disable this device or remove others from the same panel.

Android and desktop keep this same click-to-prompt flow.

Settings card (`PushSettingsPanel` on `/dashboard/settings/notifications`) uses a status badge + short body:

| Status | Badge |
|---|---|
| `enabled` | Enabled |
| `not_enabled` | Not enabled |
| `denied` | Permission denied |
| `unsupported` | Unsupported browser |
| `install_required` | Install required (iPhone/iPad tab) |
| `admin_disabled` | Admin disabled |
| `no_active_device` | No active device |

Install steps use expandable **How to install** (`PushInstallDetails`). Buttons are full-width on small screens; layout uses `min-w-0` / theme tokens for dark/light.

Device helpers: `lib/push-device.ts` · `PushHomeScreenHint`.  
Frontend: `hooks/usePushNotifications.ts` · `components/notifications/PushSettingsPanel.tsx` · `PushPermissionPrompt.tsx` · `components/pwa/InstallPrompt.tsx`.  
SW registration: `PwaProvider` registers `/sw.js` in production, and also in `next dev` when the page is served over HTTPS on a non-localhost host (custom domain / tunnel). Plain `localhost` `next dev` still unregisters the SW so HMR isn’t cache-fought.

### Detection (UX guidance only)

`detectPushDeviceContext()` snapshots four signals — **not** for security or authorization:

| Signal | Checks |
|---|---|
| iPhone / iPad / iPod | `navigator.userAgent` (`iPhone`/`iPad`/`iPod`) · `navigator.platform` + `maxTouchPoints` for iPadOS Mac spoof |
| Home Screen / PWA | `matchMedia('(display-mode: standalone)')` · `navigator.standalone` on iOS |
| Push supported | `'Notification' in window` · `'serviceWorker' in navigator` · `'PushManager' in window` |
| Permission | `Notification.permission` → `default` \| `granted` \| `denied` (null if Notification API missing). Never reads permission by calling `requestPermission` on load. |

## iPhone and iPad support

Browser push on iPhone and iPad is more constrained than on Android or desktop.

- Push may require Pàdéyá installed as a **Home Screen app / PWA** (standalone display), then opened from that icon.
- This applies to **Safari and other iPhone browsers** (Chrome, Firefox, Edge, and Safari) — not a Safari-only limitation.
- The user must still **grant permission after tapping Enable notifications** (never prompted on page load).
- **Normal browser tabs** on iPhone/iPad may not support Web Push; settings show **Install required** with expandable **How to install** steps.
- **In-app notifications** (toast + `/dashboard/notifications`) still work without browser push.
- **Android and desktop** behavior is unchanged: Enable in a normal tab (or install prompt when available), then grant permission.

### Settings UX on iPhone/iPad

| Context | Behavior |
|---|---|
| Browser tab (not installed) | Status **Install required** — Share / menu → Add to Home Screen → open from icon → Enable |
| Already installed Home Screen / PWA | Normal **Enable notifications** flow — install copy is not the main warning |
| Installed but APIs still missing | **Unsupported browser** state |
| Permission denied | Denied copy — enable later in browser/device settings |
| Granted + subscription | **Push notifications are enabled on this device.** + device list |

Do not document this as “Safari only”, “Safari is broken”, or claim Chrome will definitely work in a normal iPhone tab.

## VAPID setup

Admin page: `/admin/push/settings` (alias `/admin/settings/push`).

1. Open as `super_admin` (`admin.full_access`).
2. Choose provider: `log` (safe default — records only) or `web_push`.
3. Generate VAPID keys (or paste public + private).
4. Set subject (default `mailto:support@padeya.com`).
5. Enable push (`push_enabled`).
6. Save → send a **test push** to yourself after enabling on a real device.

Security:

- Private key stored only as `vapid_private_key_encrypted` (Fernet / `EMAIL_SETTINGS_ENCRYPTION_KEY` family).
- API never returns the private key or ciphertext — only `vapid_private_configured` / public key hints.
- Clients receive the public key via `GET /api/v1/push/vapid-public-key` → `{ enabled, public_key }` (empty when push off).
- Never log VAPID private material, endpoints, or payload bodies.

## Push subscriptions

Table: `push_subscriptions` — one user, many devices (unique `endpoint`).

| Concern | Behavior |
|---|---|
| Keys | Spec `p256dh` / `auth` Fernet-encrypted at rest |
| List | User sees devices; **keys never returned** |
| Remove | `DELETE /push/subscriptions/{id}` or by endpoint |
| Inactive | `is_active=false` / `revoked_at` → never targeted |
| Auto-deactivate | HTTP 404/410 or ≥5 consecutive failures |

APIs (auth required):

| Method | Path |
|---|---|
| GET | `/api/v1/push/vapid-public-key` |
| GET / POST | `/api/v1/push/subscriptions` |
| DELETE | `/api/v1/push/subscriptions` · `/api/v1/push/subscriptions/{id}` |
| GET / PATCH | `/api/v1/push/preferences` |

Unauthenticated register → `401`/`403`.

## Push outbox (`push_events`)

Mirrors the email outbox.

1. Domain code calls `notify_user(..., send_push=True)` or `enqueue_push` **after** payment verification for commerce.
2. Prefs + admin kill switch evaluated at enqueue → `pending` or `skipped` (with reason).
3. Worker drains pending rows.
4. Provider delivers to **active** subscriptions only.
5. Status → `sent` / `failed` / `skipped`; devices may deactivate on expiry.

Statuses: `pending` · `sent` · `failed` · `skipped`.  
Dedupe: unique `dedupe_key` (e.g. `push:order:{id}:ticket.confirmed`).  
Per-device attempts also append to `push_delivery_events`.

Skip reasons (examples): `push_disabled`, `push_enabled_off`, `pref_*_off`, `marketing_unsubscribed`, `message_push_rate_limited`, `no_active_subscriptions`.

## Worker command

```bash
cd backend
# One-shot
PYTHONPATH=. python scripts/process_push_outbox.py --once

# Long-running (Compose default — loop + subscription maintenance)
PYTHONPATH=. python scripts/process_push_outbox.py
# Equivalent:
PYTHONPATH=. python scripts/process_push_outbox.py --loop --maintenance
```

Docker: service `push_worker` in `docker-compose.yml` / `docker-compose.prod.yml`  
(`command: python scripts/process_push_outbox.py`).

```bash
docker compose up -d push_worker
docker compose logs push_worker --tail=100
```

Env (worker): `PUSH_QUEUE_ENABLED`, `PUSH_WORKER_POLL_SECONDS`, `PUSH_WORKER_BATCH_SIZE`.  
Logs **batch counts only** (`attempted` / `sent` / `failed` / `skipped` / `deactivated_subscriptions`) — never title, body, endpoints, or VAPID.

## Privacy rules

Never put any of the following in push title, body, context, or wire JSON:

- Private chat bodies or attachment / download URLs
- Hidden venues, private streets, private join URLs
- Payment / Paystack / order references
- Full pickup or entry codes
- Shipping addresses, phone numbers, emails
- Locked Vault content
- Fan Connect graphs / private attendee lists

Enforcement layers:

1. **Enqueue** — `sanitize_push_context` whitelist (`app/push/privacy.py`)
2. **Wire** — `PushPayload.to_json()` keys only: `title`, `body`, `action_url`, `notification_id`, `tag`, `timestamp`, `icon`, `badge`
3. **Service worker** — `ALLOWED_PUSH_KEYS` + scrub + `safeActionUrl` (`padeya-pwa-v24` in `public/sw.js`); never open Vault/checkout deep links from push

Messaging defaults:

- Title/body: “You have a new message on Pàdéyá.” / “Open Pàdéyá to read it…”
- Opt-in `push_message_previews`: “Name sent you a message.” — still never full chat text

Also: [PRIVACY.md](./PRIVACY.md) · [SECURITY.md](./SECURITY.md).

## Templates and triggers

Catalog: `backend/app/push/templates.py` (snake_case).  
`notify_user` maps dotted in-app kinds (e.g. `ticket.confirmed` → `ticket_confirmed`).

| Area | Templates |
|---|---|
| Tickets | `ticket_confirmed`, `ticket_qr_ready`, `ticket_event_reminder`, `ticket_event_cancelled`, `ticket_refund_update` |
| Merch | `merch_order_confirmed`, `merch_pickup_ready`, `merch_shipping_update`, `merch_picked_up`, `merch_refund_update`, `post_event_drop_available`, `merch_cart_reminder` |
| Messaging | `new_message`, `message_request`, `attachment_received` |
| Fan Connect | `fan_connect_request`, `fan_connect_accepted`, `fan_connect_message` |
| Host / sponsor / admin | sales, reviews, sponsor inquiry, reports, support |

Marketing-gated (opt-in `push_marketing`): `post_event_drop_available`, `merch_cart_reminder`.

Channel matrix + prefs: [NOTIFICATIONS.md](./NOTIFICATIONS.md).  
Presence: message email/push only when the recipient is **away** (no active messaging WebSocket).

## Admin test push

| Field | Value |
|---|---|
| Title | `Pàdéyá test notification` |
| Body | `Push notifications are working.` |
| Action | `/dashboard/notifications` |

- Self: `POST /api/v1/admin/push/settings/test`
- Other user: `POST /api/v1/admin/push/settings/test-user` (email or `user_id`)
- Lookup devices first: `GET /api/v1/admin/push/subscriptions/lookup`
- Requires admin push enabled + at least one **active** subscription
- Uses `force_push` so user category prefs do not block the test
- Safe `400` if the target has no active device

Also: deliveries `GET /admin/push/deliveries` · outbox `GET /admin/push/events` · cleanup `POST /admin/push/cleanup-subscriptions`.

## Unsupported browser fallback

When `PushManager` / `Notification` / service workers are unavailable (`pushSupported === false`):

- Title: **Push notifications are not available in this browser**
- Body: in-app notifications still work; try Home Screen install or a supported desktop/Android browser
- Actions: **Open notification center** · expandable **How to install**
- **Do not** show Enable notifications or call `Notification.requestPermission`
- iPhone/iPad browser tabs use **Install required** when `needsHomeScreenForPush`

Denied permission (supported browsers only) uses site-settings guidance; no silent re-prompt loops.

## Troubleshooting

| Issue | What to check |
|---|---|
| **Permission denied** | User blocked the prompt or site notifications. Copy: *Notifications are blocked for this browser…* They must re-enable in browser/device site settings, reopen Pàdéyá (Home Screen icon on iPhone/iPad), then try **Enable notifications** again. No silent re-prompt while still denied. |
| **App not installed** (iPhone/iPad) | Status **Install required**. User should Share / browser menu → **Add to Home Screen**, open that icon, then Enable. Normal tabs may not expose Web Push. |
| **Service worker unavailable** | Production builds register `/sw.js` via `PwaProvider`. `next dev` unregisters the SW — push will not work there. Confirm HTTPS, SW registered (`navigator.serviceWorker`), and `'PushManager' in window`. |
| **Admin push disabled** | Settings badge **Admin disabled**. Super admin: `/admin/push/settings` → enable `push_enabled` and save. Public VAPID endpoint returns empty when off. |
| **No VAPID key configured** | Admin must generate or paste public + private keys and save. Private key is encrypted at rest and never returned. Clients need `GET /api/v1/push/vapid-public-key` with `enabled` + `public_key`. Provider should be `web_push` for real delivery (not only `log`). |
| **Push worker not running** | Outbox stays `pending`. Ensure `push_worker` is up (`docker compose` service runs `python scripts/process_push_outbox.py`). Check worker logs for batch counts only (no payload/endpoint/VAPID private). Confirm `PUSH_QUEUE_ENABLED` and provider mode in prod. |

Related ops: [OPERATIONS.md](./OPERATIONS.md). In-app center still works if browser push is down.

## Preferences (summary)

Stored on `user_email_preferences`. Master `push_enabled` defaults **on** and blocks all categories (including security) when off. See full table in [NOTIFICATIONS.md](./NOTIFICATIONS.md#preference-keys).

UI: `/dashboard/settings/notifications`.

## Migrations

| Revision | Change |
|---|---|
| `20260719_0063` | Provider settings, subscriptions, delivery events, base push prefs |
| `20260719_0064` | Provider mode `log` / `web_push` |
| `20260719_0065` | Subscription lifecycle fields |
| `20260719_0066` | `push_events` outbox |
| `20260719_0067` | `push_reviews`, `push_security` |
| `20260719_0068` | `push_message_previews` |

## Tests

Backend: `tests/test_push_checklist.py`, `test_notifications_push.py`, `test_push_privacy.py`, `test_push_templates.py`, `test_push_worker_cli.py`, `test_notification_triggers.py`, `test_notification_center.py`.

Frontend smoke: `npm run test:pwa` (permission UX, SW push/click, toast, center, theme).

## Real-device manual checks (production)

Automated tests cover API, privacy, worker, SW source, and UI wiring. **Real phone/browser delivery must be tested after deploying** with:

- HTTPS
- production service worker (`/sw.js` registered — not `next dev`)
- admin **web_push** enabled (`/admin/push/settings`)
- VAPID public + private configured (private encrypted at rest)
- user permission granted via **Enable notifications** on `/dashboard/settings/notifications`

Suggested smoke on a real device after deploy:

1. Super admin opens Push settings → provider `web_push` → VAPID set → push enabled.
2. On the device browser/PWA, sign in → Enable notifications → grant permission.
3. Admin **Send test push** → notification appears; tap opens `/dashboard/notifications` (or safe `action_url`).
4. Confirm in-app toast + notification center still work with push disabled on another account.
5. Confirm denied / unsupported browsers show guidance and do not prompt on load.
