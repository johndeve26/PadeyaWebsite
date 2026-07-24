# Cookies and browser storage

**Brand:** Pàdéyá  
**Audience:** engineering, support, legal alignment  
**Public policy:** frontend route `/cookies` — `frontend/src/lib/legal/cookies-content.tsx`

This document inventories first-party browser storage. It matches current frontend behavior. Do not change auth architecture here—see [Future hardening](#future-hardening) for token storage notes.

Related: [AUTH.md](./AUTH.md) · [AMBASSADORS.md](./AMBASSADORS.md) · [ANALYTICS_PRIVACY.md](./ANALYTICS_PRIVACY.md) · [CHECKOUT.md](./CHECKOUT.md) · [SECURITY.md](./SECURITY.md)

---

## Terminology

| Type | Mechanism | Examples on Pàdéyá |
| --- | --- | --- |
| HTTP cookie | `document.cookie` | Ambassador referral only (first-party) |
| localStorage | `window.localStorage` | Auth tokens, theme, host workspace, analytics ids, PWA cache |
| sessionStorage | `window.sessionStorage` | Merch draft cart, checkout email hint, geo decline flag |

Third parties (notably **Paystack** at checkout) may set their own cookies or storage; Pàdéyá does not control those.

---

## HTTP cookies

| Name | Purpose | Lifetime | Required | Preference-gated | Code |
| --- | --- | --- | --- | --- | --- |
| `padeya_amb_ref_v1` | JSON map of event key → `{ code, at }` for ambassador attribution; last-click per event | 30 days (`max-age`); client also ignores entries older than 30 days | No (referral program) | No | `frontend/src/lib/ambassador-referral.ts` |

**Checkout attribution order:** explicit code → URL `ref` / `amb` → cookie (`resolveCheckoutReferral`).

**Attributes:** `path=/`, `SameSite=Lax` (no `HttpOnly`; readable by page JS).

Captured on event/merch landings and checkout when URL carries `ref` or `amb` (see `EventDetailClient.tsx`, `merch/page.tsx`, `checkout/page.tsx`).

---

## Authentication (localStorage)

Normal and admin impersonation sessions use **Bearer JWTs** in localStorage, not auth cookies. Backend: `backend/app/auth/session.py`.

| Key | Purpose | Lifetime | Required | Preference-gated | Code |
| --- | --- | --- | --- | --- | --- |
| `padeya.access_token` | User access JWT | Until expiry / silent refresh / logout / clear site data | Yes when signed in | No | `frontend/src/lib/auth/storage.ts` |
| `padeya.refresh_token` | Refresh token (rotated server-side, ~180d default) | Until logout / revoke / expiry / clear | Yes when signed in | No | same |
| `padeya.auth.device_id` | Opaque device id for session metadata | Persistent | No | Yes | `frontend/src/lib/auth/session-meta.ts` |
| `padeya.auth.last_login_at` | Last successful login timestamp | Persistent | No | Yes | same |
| `padeya.auth.last_refreshed_at` | Last token refresh timestamp | Persistent | No | Yes | same |
| `padeya.admin_access_token` | Stashed admin token during impersonation | Session of impersonation flow | Impersonation only | No | same |
| `padeya.admin_refresh_token` | Stashed admin refresh | Same | Impersonation only | No | same |
| `padeya.impersonating` | Flag that admin tokens are stashed | Same | Impersonation only | No | same |

One-time migration may copy legacy sessionStorage auth keys into localStorage on load.

---

## Preferences and UX (localStorage / sessionStorage)

| Key / pattern | Storage | Purpose | Lifetime | Required | Preference-gated | Code |
| --- | --- | --- | --- | --- | --- | --- |
| `padeya-theme` | localStorage | Light / dark / system theme | Persistent | No | Yes (user choice) | `frontend/src/lib/theme.ts` |
| `padeya-active-host-id` | localStorage | Active host workspace | Persistent | No | Yes | `frontend/src/lib/host-workspace.ts` |
| `padeya-workspace-mode` | localStorage | Host workspace mode | Persistent | No | Yes | same |
| `padeya.ui-sounds.v1` | localStorage | UI sound prefs | Persistent | No | Yes | `frontend/src/lib/ui-sounds.ts` |
| `padeya.discovery.location` | localStorage | Saved discovery location (when user sets it) | Persistent | No | Yes (location opt-in) | `frontend/src/lib/discovery/geo-location.ts` |
| `padeya.discovery.recentSearches` | localStorage | Recent discovery searches | Persistent | No | Yes | `frontend/src/components/discovery/HeroDiscoverySearch.tsx` |
| `padeya.events.view` | localStorage | Events marketplace list/grid view | Persistent | No | Yes | `frontend/src/lib/events/marketplace-listing.ts` |
| `padeya:host-events:view-mode` | localStorage | Host events list view mode | Persistent | No | Yes | `frontend/src/components/host/events/event-list-types.ts` |
| `padeya.host.last_scanner_event` | localStorage | Last scanner event shortcut | Persistent | No | Yes | `frontend/src/lib/host-scanner-entry.ts` |
| `padeya.host.last_pickup_event` | localStorage | Last merch pickup event shortcut | Persistent | No | Yes | same |
| `padeya-push-prompt-dismissed` | localStorage | Push prompt dismiss state | Persistent | No | Yes | `frontend/src/hooks/usePushNotifications.ts` |
| `padeya.pwa.install.dismissed` | localStorage | PWA install prompt dismiss | Persistent | No | Yes | `frontend/src/components/pwa/InstallPrompt.tsx` |
| `padeya.register.location` | sessionStorage | Register flow location hint | Tab session | No | Yes | `frontend/src/lib/auth/register-location.ts` |
| `padeya_checkout_buyer_email` | sessionStorage | Buyer email for logged-out PDF download on success | Tab session | Checkout success UX | No | `frontend/src/lib/commerce-api.ts`, checkout/success |
| `padeya.discovery.geo_declined` | sessionStorage | User declined browser geolocation for discovery | Tab session | No | Yes | `frontend/src/lib/discovery/geo-session.ts` |
| `padeya.merch.draft.{eventId}` | sessionStorage | Merch draft cart lines per event | Tab session | No | Yes | `frontend/src/lib/merch-draft-cart.ts` |
| Event studio preview flag | sessionStorage | Per-event studio preview checkbox | Tab session | No | Yes | `frontend/src/components/events/studio/EventStudio.tsx` |

---

## PWA offline display cache (localStorage)

Display-only; door validation remains server-side. See [SECURITY.md](./SECURITY.md).

| Key / pattern | Purpose | Lifetime | Code |
| --- | --- | --- | --- |
| `padeya.ticket.cache.v1.{ticketId}` | Cached ticket payload for offline viewing | Until cleared; list capped (~40) | `frontend/src/lib/pwa/offline-ticket-cache.ts` |
| `padeya.tickets.list.v1` | Index of cached ticket ids | Same | same |
| `padeya.merch.pickup.cache.v1.{orderItemId}` | Merch pickup display cache | Same pattern | `frontend/src/lib/pwa/offline-merch-cache.ts` |
| `padeya.merch.pickup.list.v1` | Index of cached merch pickup ids | Same | same |

---

## First-party analytics (localStorage)

First-party product analytics only—no GA/Meta/etc. in current phase ([ANALYTICS_PRIVACY.md](./ANALYTICS_PRIVACY.md)).

| Key | Purpose | Lifetime | Required | Preference-gated | Code |
| --- | --- | --- | --- | --- | --- |
| `padeya_anonymous_id` | Anonymous visitor id; also sent on ambassador referral click tracking for **unique click** estimation (hashed server-side; not exposed to hosts) | Persistent | No | Non-essential where consent applies | `frontend/src/lib/analytics-client.ts`, `frontend/src/lib/referral-click-track.ts` |
| `padeya_session_id` | Analytics session id | ~30 min idle | No | Same | same |
| `padeya_session_ts` | Last activity for session idle | Same | No | Same | same |
| `padeya_utm_attribution` | Captured UTM params | Persistent | No | Same | `frontend/src/lib/analytics.ts` |
| `padeya_analytics_queue` | Offline event queue (cap 200) | Persistent | No | Same | same |
| `padeya_analytics_dedupe` | Client dedupe map | Persistent | No | Same | same |

---

## Third parties

| Provider | When | Pàdéyá control |
| --- | --- | --- |
| Paystack | Card / payment checkout | None over their cookies/storage; governed by Paystack policies |

---

## Public vs internal

- **Public Cookie Policy** describes categories and the ambassador cookie name; it does not list auth token key names.
- **This doc** lists keys for developers and support.

---

## Future hardening

Consider moving auth tokens from **localStorage** to **httpOnly**, **Secure**, **SameSite** cookies (or equivalent BFF pattern) to reduce token exposure risk from XSS. That is a behavior and security architecture change—plan separately from legal copy updates; do not imply it is live on public legal pages.

---

## Changelog

| Date | Change |
| --- | --- |
| 2026-07-22 | Initial inventory aligned with Cookie Policy rewrite |
