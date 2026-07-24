# Buyer / Personal dashboard audit — Pàdéyá

**Status:** Audit complete (§1–§15). Phase 1–2 done. **Phase 3 (Personal Command Center on `/dashboard`) implemented.** Phases 4–7 remain future work.  
**Date:** July 2026  
**Brand:** Pàdéyá  

**Scope:** Private personal / buyer workspace (`/dashboard/*`) only. Host workspace stays at `/host/*`.

**Related:** [DASHBOARD_HOST_UNIFICATION_AUDIT.md](./DASHBOARD_HOST_UNIFICATION_AUDIT.md) · [HOST_AREA_AUDIT.md](./HOST_AREA_AUDIT.md) · [FRONTEND_ROUTES.md](./FRONTEND_ROUTES.md) · [PRODUCTION_SMOKE_TEST.md](./PRODUCTION_SMOKE_TEST.md) · [CRUD_MATRIX.md](./CRUD_MATRIX.md) · [AMBASSADORS.md](./AMBASSADORS.md) · [PRIVACY.md](./PRIVACY.md) · [FAN_PASSPORT.md](./FAN_PASSPORT.md) · [VAULT.md](./VAULT.md) · [MESSAGING.md](./MESSAGING.md) · [SECURITY.md](./SECURITY.md) · [EXECUTION_TRACKER.md](./EXECUTION_TRACKER.md)

## Table of contents

1. [Current route audit](#1-current-route-audit)
2. [Current `/dashboard` home audit](#2-current-dashboard-home-audit)
3. [Proposed Personal sidebar / navigation](#3-proposed-personal-sidebar--navigation)
4. [Buyer naming audit](#4-buyer-naming-audit)
5. [Tickets audit](#5-tickets-audit)
6. [Orders, merch, cart, refunds audit](#6-orders-merch-cart-refunds-audit)
7. [Messages, Connect, Following audit](#7-messages-connect-following-audit)
8. [Passport, badges, Vault, reviews audit](#8-passport-badges-vault-reviews-audit)
9. [Ambassador buyer-side audit](#9-ambassador-buyer-side-audit)
10. [Workspace switcher and top nav audit](#10-workspace-switcher-and-top-nav-audit)
11. [Proposed `/dashboard` Personal Command Center](#11-proposed-dashboard-personal-command-center)
12. [Privacy and safety boundaries](#12-privacy-and-safety-boundaries)
13. [Migration / redirect plan](#13-migration--redirect-plan)
14. [Implementation roadmap](#14-implementation-roadmap)
15. [Final audit summary](#15-final-audit-summary)

---

## Legend

| Field | Meaning |
| --- | --- |
| **Purpose** | What the page is for |
| **Component / file** | Primary `page.tsx` (and notable child components) |
| **Data shown** | Concrete UI data / APIs the page loads |
| **User type** | Product role (not platform admin) |
| **Sidebar / layout** | Personal `WorkspaceShell` unless noted; primary nav group if linked |
| **Permissions** | FE gates; APIs remain source of truth for ownership |
| **Overlaps (buyer)** | Conceptual overlap with other `/dashboard` (or `/connect`) personal pages |
| **Overlaps (host)** | Label or product overlap with `/host/*` — not a merge recommendation |
| **Recommendation** | `stay` · `redirect` · `alias` · `rename in UI only` · `move later` |

**Recommendation policy**

| Value | Meaning |
| --- | --- |
| **stay** | Keep URL and ownership in Personal workspace |
| **redirect** | Legacy path; send users to a canonical URL (may already be 308 + client) |
| **alias** | Thin redirect kept for bookmarks / old links; canonical lives elsewhere |
| **rename in UI only** | Keep URL; change nav label, eyebrow, or page title later |
| **move later** | Possible future URL or nav-group restructure — **not** recommended now |

---

## Shared shell facts

| Surface | Detail |
| --- | --- |
| Layout | `frontend/src/app/dashboard/layout.tsx` |
| Auth | `RequireAuth` — authenticated user; **no** host membership required |
| Shell | `HostWorkspaceProvider` → `WorkspaceShell` with `buyerNav` / `buyerNavGroups` |
| Sidebar title | **Personal** (`PERSONAL_WORKSPACE_TITLE`) |
| Toolbar | `WorkspaceSwitcher` (Personal account ↔ Host workspaces) |
| Page chrome | Many pages wrap content in `DashboardShell` (in-column header only — not a second app shell) |
| Nav source | `frontend/src/lib/nav/workspace.ts` — groups: **Home · Activity · Community · Identity · Earn · Account** (Phase 2; was Growth → Earn, Team → Workspaces) |
| Team nested layout | `frontend/src/app/dashboard/team/layout.tsx` — pass-through only |
| Fan Connect canonical | `/connect/*` uses the **same** Personal shell (`frontend/src/app/connect/layout.tsx`) |

**Server redirects** (`frontend/next.config.ts`):

| From | To | HTTP |
| --- | --- | --- |
| `/dashboard/merch` | `/dashboard/merchandise` | 308 |
| `/dashboard/merch/:path*` | `/dashboard/merchandise/:path*` | 308 |
| `/host/settings/notifications` | `/dashboard/settings/notifications` | 308 |

**Route count:** 41 `page.tsx` files under `frontend/src/app/dashboard/**` (34 functional + 6 Connect aliases + 1 merch legacy redirect page).

---

## 1. Current route audit

### 1.1 Home & alerts

| Route | Purpose | Component / file | Data shown | User type | Sidebar / layout | Permissions | Overlaps (buyer) | Overlaps (host) | Recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `/dashboard` | **Personal Command Center** home — Next up, activity, messages, identity, Vault, Ambassadors, quick actions | `frontend/src/app/dashboard/page.tsx` → `PersonalCommandCenter` | P0: tickets, orders, merch, cart + unread hook; deferred Passport/Vault/Ambassador/Connect/Following | Authenticated personal user | Personal shell; nav **Home → Overview** | Auth; own-data APIs only (§12) | Soft overlap with tickets, orders, passport (deep links only) | Parallel to Host Command Center at `/host` — **not** a data merge | **stay** — Phase 3 **shipped** (URL unchanged) |
| `/dashboard/notifications` | In-app Alerts inbox (filters, mark read) | `…/notifications/page.tsx` | `fetchNotifications`; `markNotificationRead` / `markAllNotificationsRead` — title, body, kind, unread, `link_path` | Authenticated | Personal shell; nav **Home → Alerts** | Auth | Overlaps account prefs at `/dashboard/settings/notifications` (prefs vs inbox) | Account-level; host shell may deep-link here | **stay** |

### 1.2 Tickets

| Route | Purpose | Component / file | Data shown | User type | Sidebar / layout | Permissions | Overlaps (buyer) | Overlaps (host) | Recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `/dashboard/tickets` | Buyer ticket wallet (list + offline cache) | `…/tickets/page.tsx` (`BuyerTicketsDashboard`) | `fetchMyTickets`; offline ticket list cache | Ticket holder | Personal shell; nav **Activity → Tickets** | Auth; API returns own tickets | Links to orders, ticket detail | Label vs Host **Tickets & Entry** (`/host/desk`) — desk scans host events, not this wallet | **stay** |
| `/dashboard/tickets/[id]` | Digital ticket detail — QR, PDF, cancel, QR mode, device bind, linked merch | `…/tickets/[id]/page.tsx` (`TicketQrPanel`, `CancelTicketButton`) | `fetchTicket`; `downloadTicketPdf`; `setTicketQrMode`; `bindTicketDevice`; merch status | Ticket holder (own ticket) | Personal shell; deep link from list | Auth + own ticket (API) | Orders, merchandise, transfer | Host check-in / desk scan the same ticket QR from host tools | **stay** |
| `/dashboard/tickets/[id]/transfer` | Transfer ticket ownership + history | `…/tickets/[id]/transfer/page.tsx` | `fetchTicket`; `fetchTicketTransfers`; `transferTicket({ to_email, note })` | Ticket holder (active ticket) | Personal shell; deep link | Auth + own ticket (API) | Ticket detail | — | **stay** |

### 1.3 Orders & cart

| Route | Purpose | Component / file | Data shown | User type | Sidebar / layout | Permissions | Overlaps (buyer) | Overlaps (host) | Recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `/dashboard/orders` | Purchase / receipt history list | `…/orders/page.tsx` (`DataTable`) | `fetchMyOrders` — event, reference, date, ticket/merch qty, total, status | Buyer | Personal shell; nav **Activity → Orders** | Auth | Tickets, merchandise, refunds (same purchase lifecycle) | Host sees sales / fulfillment, not this buyer list | **stay** |
| `/dashboard/orders/[id]` | Order receipt — lines, payments, checkout answers; polls pending payment | `…/orders/[id]/page.tsx` (`StartMessageButton` on merch) | `fetchOrder` (poll ~4s) — items, totals, discounts, payments, answers | Buyer (own order) | Personal shell; deep link | Auth + own order (API) | Tickets, merchandise, messages (message host) | Host merch order / fulfillment views are separate | **stay** |
| `/dashboard/cart` | Active / abandoned merch cart; resume checkout | `…/cart/page.tsx` | `fetchBuyerCart`; `removeBuyerCartItem` — lines, resume path | Buyer | Personal shell; **not** in primary nav (linked from merch) | Auth | Merchandise wallet; checkout under `/events/...` | — | **stay** |

### 1.4 Merchandise

| Route | Purpose | Component / file | Data shown | User type | Sidebar / layout | Permissions | Overlaps (buyer) | Overlaps (host) | Recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `/dashboard/merchandise` | Buyer merch wallet — pickups / purchases + post-event drops | `…/merchandise/page.tsx` (`BuyerMerchDashboard`) | `fetchMyMerch`; `fetchMyEligiblePostEventDrops`; offline pickup cache | Buyer / merch holder | Personal shell; nav **Activity → Merch** (href merchandise) | Auth | Orders, cart, tickets, merch item detail | Host `/host/merchandise` = studio / fulfillment | **stay** — canonical buyer merch |
| `/dashboard/merchandise/[orderItemId]` | Merch item detail — pickup QR / shipping + verified review CRUD | `…/merchandise/[orderItemId]/page.tsx` (`MerchPickupQr`) | `fetchMyMerchItem`; merch review fetch/create/update/remove; offline fallback | Buyer (own item) | Personal shell; deep link | Auth + own item (API) | Merchandise list; Reviews page (event reviews vs merch reviews) | Host fulfillment desk / product review inbox | **stay** |
| `/dashboard/merch` | Legacy path → merchandise wallet | `…/merch/page.tsx` (client `router.replace`) + next.config **308** | None (redirect skeleton) | Buyer | Brief Personal shell while redirecting | Auth | Canonical `/dashboard/merchandise` | — | **redirect** → `/dashboard/merchandise` (already 308 + client; keep until bookmarks die) |

### 1.5 Refunds

| Route | Purpose | Component / file | Data shown | User type | Sidebar / layout | Permissions | Overlaps (buyer) | Overlaps (host) | Recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `/dashboard/refunds` | My refund requests list | `…/refunds/page.tsx` (`RefundCard`) | `fetchMyRefunds` | Buyer | Personal shell; nav **Activity → Refunds** | Auth | Orders (source of refundable purchases) | Support `/support/refunds`, admin refunds — ops, not buyer wallet | **stay** |
| `/dashboard/refunds/new` | Request full refund for a paid order | `…/refunds/new/page.tsx` | `fetchMyOrders` (paid); `createRefundRequest` | Buyer | Personal shell; deep link from refunds list | Auth | Orders, refunds list | — | **stay** |

### 1.6 Messages

| Route | Purpose | Component / file | Data shown | User type | Sidebar / layout | Permissions | Overlaps (buyer) | Overlaps (host) | Recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `/dashboard/messages` | Fan messaging inbox (thread list) | `…/messages/page.tsx` (`MessagesInbox` `mode="fan"`) | Fan threads via messaging-api (`fetchFanThreads` / related) | Fan / attendee | Personal shell; nav **Community → Messages** | Auth; messaging permissions on actions | Message settings / notifications prefs; Connect (social vs DM) | Label vs `/host/messages` (host inbox) — same model, different role | **stay** |
| `/dashboard/messages/[threadId]` | Fan inbox focused on one thread | `…/messages/[threadId]/page.tsx` (`MessagesInbox` fan mode) | Same as inbox + selected thread | Fan / attendee | Personal shell; deep link | Auth + thread access (messaging perms) | Messages list | Host thread view of same conversation when host-side | **stay** |
| `/dashboard/messages/settings` | Fan messaging privacy / who-can-message | `…/messages/settings/page.tsx` (`MessageSettingsForm` fan) | Message settings fetch/update | Fan / attendee | Personal shell; off primary nav | Auth | Messages inbox; account notification settings | Host message settings under host area | **stay** |
| `/dashboard/messages/notifications` | Message notification summaries panel | `…/messages/notifications/page.tsx` (`MessageNotificationsPanel`) | `fetchMessageNotifications` (via panel) | Fan / attendee | Personal shell; off primary nav | Auth | Alerts inbox; settings/notifications | — | **stay** |

### 1.7 Team / workspaces (host bridge)

| Route | Purpose | Component / file | Data shown | User type | Sidebar / layout | Permissions | Overlaps (buyer) | Overlaps (host) | Recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `/dashboard/team` | List owned + joined host workspaces; open host desk | `…/team/page.tsx` | `fetchHostWorkspaces` — owned vs joined (role, scope, slug) | User who owns or joined a host team | Personal shell; nav **Community → Workspaces** (Phase 2 UI rename; URL unchanged) | Auth (page lists empty if none) | `/dashboard/team/workspaces`, `/workspaces`, `WorkspaceSwitcher` | Bridges into `/host`; disambiguated from Host **Host Team** | **stay**; UI label **Workspaces** shipped |
| `/dashboard/team/workspaces` | Set active host workspace and open host desk | `…/team/workspaces/page.tsx` | `fetchHostWorkspaces`; `setActiveHostWorkspace` | Same | Personal shell; deep link from Team | Auth | Team list, `/workspaces`, switcher | Same host bridge | **stay** for now; prefer switcher as primary entry (**move later** / chrome merge candidate) |

### 1.8 Fan Connect aliases

Canonical UI lives at `/connect/*` (Personal shell). These dashboard paths are server `redirect()` only.

| Route | Purpose | Component / file | Data shown | User type | Sidebar / layout | Permissions | Overlaps (buyer) | Overlaps (host) | Recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `/dashboard/connect` | Alias → `/connect` | `…/connect/page.tsx` | None | Fan | Redirect (nav **Community → Connect** still points here) | Auth | Canonical `/connect`; Following (hosts vs peers) | Admin Fan Connect ops | **alias** → `/connect` |
| `/dashboard/connect/connections` | Alias → `/connect/connections` | `…/connect/connections/page.tsx` | None | Fan | Redirect | Auth | Canonical connect connections | — | **alias** |
| `/dashboard/connect/requests` | Alias → `/connect/requests` | `…/connect/requests/page.tsx` | None | Fan | Redirect | Auth | Canonical connect requests | — | **alias** |
| `/dashboard/connect/suggestions` | Alias → `/connect/suggestions` | `…/connect/suggestions/page.tsx` | None | Fan | Redirect | Auth | Canonical connect suggestions | — | **alias** |
| `/dashboard/connect/events` | Alias → `/connect/events` | `…/connect/events/page.tsx` | None | Fan | Redirect | Auth | Canonical connect events | — | **alias** |
| `/dashboard/connect/settings` | Alias → `/connect/settings` | `…/connect/settings/page.tsx` | None | Fan | Redirect | Auth | Canonical connect settings | — | **alias** |

### 1.9 Following

| Route | Purpose | Component / file | Data shown | User type | Sidebar / layout | Permissions | Overlaps (buyer) | Overlaps (host) | Recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `/dashboard/following` | Hosts I follow + marketing email opt-in / unfollow | `…/following/page.tsx` | `fetchMyFollowing`; `updateMarketingOptIn`; `unfollowHost` | Fan / attendee | Personal shell; nav **Community → Following** | Auth | Passport (followed hosts); Vault / Connect (related social graph) | Inverse of `/host/followers` | **stay** |

### 1.10 Passport & badges

| Route | Purpose | Component / file | Data shown | User type | Sidebar / layout | Permissions | Overlaps (buyer) | Overlaps (host) | Recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `/dashboard/passport` | Fan Passport hub — stamps, loyalty, attendance, vault/badge stats | `…/passport/page.tsx` (`PassportStampGrid`, `MerchProofSection`) | `fetchMyPassport` — attended/upcoming, loyalty, badges count, reviews, vault unlocks, followed hosts, favorites, cities, VIP | Fan / attendee | Personal shell; nav **Identity → Passport** | Auth | Badges, tickets, vault, following, passport settings | — | **stay**; **rename in UI only** if framing as Personal identity hub |
| `/dashboard/passport/settings` | Passport visibility, directory opt-in, public profile fields | `…/passport/settings/page.tsx` (`ImageUrlOrUploadField`) | `fetchPassportSettings` / `updatePassportSettings` — username, display name, avatar, tagline, bio, visibility toggles | Fan / attendee | Personal shell; off primary nav | Auth | Passport hub; account settings (name/theme) | — | **stay** |
| `/dashboard/badges` | Full badge catalog with earned / locked state | `…/badges/page.tsx` | `fetchMyBadges` — name, description, earned, awarded_at | Fan / attendee | Personal shell; nav **Identity → Badges** | Auth | Passport (already surfaces badge progress) | — | **stay**; **rename in UI only** / nest under Passport in nav later (keep URL) |

### 1.11 Vault

| Route | Purpose | Component / file | Data shown | User type | Sidebar / layout | Permissions | Overlaps (buyer) | Overlaps (host) | Recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `/dashboard/vault` | Fan Vault library — unlocked / follower / ticket / unlockable sections + activity | `…/vault/page.tsx` (`BuyerVaultLibraryCard`) | `fetchMyVaultLibrary`; optional purchase poll after `?purchase=` | Fan / attendee | Personal shell; nav **Identity → Vault** | Auth | Following, vault item, subscriptions | Host `/host/vault` = studio (create/publish) | **stay** |
| `/dashboard/vault/[itemId]` | Unlocked Vault item detail (body/media if accessible) | `…/vault/[itemId]/page.tsx` | `fetchMyVaultItems` + `fetchMyVaultPurchases` — resolve by `itemId` | Fan with access | Personal shell; deep link | Auth + access rules (empty if locked) | Vault library | Host edit/preview studio for same content | **stay** |
| `/dashboard/vault/subscriptions` | Manage Vault host subscriptions (cancel / archive / restore) | `…/vault/subscriptions/page.tsx` | `fetchMyVaultSubscriptions`; cancel / archive / restore | Subscriber | Personal shell; off primary nav | Auth | Vault library | Host `/host/vault/subscriptions` = subscriber list for host | **stay** |

### 1.12 Reviews

| Route | Purpose | Component / file | Data shown | User type | Sidebar / layout | Permissions | Overlaps (buyer) | Overlaps (host) | Recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `/dashboard/reviews` | Create / edit / withdraw own verified event reviews (from checked-in tickets) | `…/reviews/page.tsx` (`ReviewCard`) | `fetchMyReviews`; `fetchMyTickets` (checked_in); eligibility; submit / update / withdraw | Verified attendee | Personal shell; nav **Identity → Reviews** | Auth; eligibility API | Passport (review counts); merch item reviews are separate on merch detail | Host `/host/reviews` = reply inbox (hosts **cannot** delete reviews) | **stay** |

### 1.13 Ambassadors (promote & earn)

| Route | Purpose | Component / file | Data shown | User type | Sidebar / layout | Permissions | Overlaps (buyer) | Overlaps (host) | Recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `/dashboard/ambassador` | Ambassador overview — promotions + earnings snapshot | `…/ambassador/page.tsx` (`AmbassadorDashNav`, `StatCard`) | `fetchAmbassadorEarningsSummary`; optional domain earnings — enrollments, clicks, sales, payable/paid | Ambassador / fan promoter | Personal shell; nav **Earn → Ambassadors** (Phase 2; plural label, singular path) | Auth; backend gates ambassador data | Sibling ambassador pages | Host `/host/ambassadors*` = campaign owner tools | **stay**; path pluralization later if needed |
| `/dashboard/ambassador/events` | Active campaign enrollments per event | `…/ambassador/events/page.tsx` | `fetchMyAmbassadorEnrollments` — clicks, tickets, merch, revenue, commission, referral code | Same | Personal shell + `AmbassadorDashNav` | Auth | Ambassador overview / links | Host per-event ambassadors | **stay** |
| `/dashboard/ambassador/links` | Referral codes / links / share cards | `…/ambassador/links/page.tsx` (`AmbassadorShareCard`) | Active enrollments from `fetchMyAmbassadorEnrollments` | Same | Personal shell + subnav | Auth | Ambassador events | — | **stay** |
| `/dashboard/ambassador/earnings` | Earnings summary + confirmed sales ledger | `…/ambassador/earnings/page.tsx` | Earnings summary + enrollments flattened to `sales[]` | Same | Personal shell + subnav | Auth | Payouts page | Host conversion ledger (host-owned) | **stay** |
| `/dashboard/ambassador/leaderboard` | Personal ranking of own campaigns (not global) | `…/ambassador/leaderboard/page.tsx` | Enrollments sorted client-side by revenue/clicks | Same | Personal shell + subnav | Auth | Earnings | Host campaign leaderboard | **stay** |
| `/dashboard/ambassador/payouts` | Payout / reward status snapshot | `…/ambassador/payouts/page.tsx` | `fetchAmbassadorEarningsSummary` — payable / approved / paid | Same | Personal shell + subnav | Auth | Earnings | Host ambassador payouts summary | **stay** |

### 1.14 Settings

| Route | Purpose | Component / file | Data shown | User type | Sidebar / layout | Permissions | Overlaps (buyer) | Overlaps (host) | Recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `/dashboard/settings` | Account profile — display name + theme appearance | `…/settings/page.tsx` (`ThemeAppearanceCard`) | `updateMyProfile({ full_name })`; email read-only; theme | Authenticated | Personal shell; nav **Account → Settings** | Auth | Passport settings (public fan profile vs account name) | Host `/host/settings` = host org profile | **stay** |
| `/dashboard/settings/notifications` | Account email + browser push preferences | `…/settings/notifications/page.tsx` (`PushSettingsPanel`) | Email + push preference fetch/update (ticket, merch, messages, fan_connect, sponsor, host, marketing, …) | Authenticated (shared account prefs) | Personal shell; off primary nav (linked from settings / alerts) | Auth | Alerts inbox; message notification prefs | **Canonical** target of `/host/settings/notifications` (308) | **stay** — shared account prefs (chrome merge already via redirect) |

---

## Route count summary

| Category | Count | Notes |
| --- | --- | --- |
| Functional Personal pages | 34 | Including deep links and subnav |
| Connect aliases | 6 | Server redirect → `/connect/*` |
| Merch legacy | 1 | Client + 308 → merchandise |
| **Total `page.tsx`** | **41** | Under `frontend/src/app/dashboard/**` |

---

## Recommendation tally (§1 routes)

| Recommendation | Routes (approx.) |
| --- | --- |
| **stay** | Vast majority of functional Personal routes |
| **redirect** | `/dashboard/merch` (+ `:path*` in next.config) |
| **alias** | All six `/dashboard/connect/*` paths |
| **rename in UI only** | Team → Workspaces (nav); Ambassadors plural/singular polish; optional Passport hub framing; Badges nest under Passport in nav |
| **move later** | Team / team/workspaces consolidation with switcher + `/workspaces` (chrome only; no URL migration required yet) |

---

## 2. Current `/dashboard` home audit

**File:** `frontend/src/app/dashboard/page.tsx` → `PersonalCommandCenter`  
**URL:** `/dashboard` (canonical Personal home; Option A — keep prefix)  
**Shell:** Personal `WorkspaceShell` + in-page `DashboardShell` (`tone="soft"`, compact, eyebrow **Personal Command Center**)

**Principle:** Personal Command Center — actionable and scannable for the next ticket, pickup, message, or reward. Parallel to Host Command Center at `/host`, **not** a merge and **not** a 14-tile feature dump of every sidebar link.

> **Phase 3 shipped (20 July 2026):** `/dashboard` is the Personal Command Center. Routes unchanged. Privacy §12 preserved. Sections below through §2.7 describe the **pre-Phase-3** home for audit history; §2.13 and §11 / §14 Phase 3 document what shipped.

### 2.1 What it showed (pre–Phase 3)

| Block | Content |
| --- | --- |
| **Page header** | Eyebrow `Personal`; title `Hello, {full_name}`; description mentioning tickets, passport stamps, Vault unlocks, refunds |
| **Header CTA** | Single primary: **Browse events** → `/events` |
| **Metric row** | Three `MetricCard`s — Tickets, Orders, Passport |
| **Account card** | Email, roles string, role-gated workspace CTAs, footnote about Alerts / push prefs |

**Data sources today**

| Source | Used for |
| --- | --- |
| `useAuth().user` | Greeting name, email, roles, CTA visibility |
| `fetchMyTickets()` | **Count only** (`tickets.length`) — no next event, status, or QR |
| `fetchMyOrders()` | **Count only** (`orders.length`) — no pending payment, merch lines, or refunds |

No other Personal modules are loaded on home (messages, merch, passport payload, vault, connect, ambassador, following, refunds, cart, alerts).

### 2.2 Current cards / metrics

| Card | Value | Description | Action |
| --- | --- | --- | --- |
| **Tickets** | Total ticket count (all statuses lumped) | “Ready for door entry” (often inaccurate — includes past/cancelled) | Open tickets → `/dashboard/tickets` |
| **Orders** | Total order count | “Receipts & payments” | View orders → `/dashboard/orders` |
| **Passport** | Static string **`Open`** (not a metric) | “Badges, loyalty, check-ins” | Open Passport → `/dashboard/passport` |

### 2.3 Current CTAs

| CTA | Target | Who sees it |
| --- | --- | --- |
| Browse events | `/events` | Everyone (header) |
| Open tickets | `/dashboard/tickets` | Everyone (metric card) |
| View orders | `/dashboard/orders` | Everyone (metric card) |
| Open Passport | `/dashboard/passport` | Everyone (metric card) |
| Host workspace | `/host` | `host` or `host_staff` role |
| Become a host | `/host/onboarding` | Users without host roles |
| Support | `/support` | `support_agent` |
| Admin | `/admin` | `super_admin` or `finance_admin` |

**Not present as CTAs today:** open next ticket QR, cart, merch pickups, refunds, messages, Connect, Vault, Ambassadors, Following, Alerts, Settings, notification prefs (mentioned only in footnote).

### 2.4 What feels useful

| Signal | Why it works |
| --- | --- |
| Personal eyebrow + greeting | Correct mode language vs Host; warm entry |
| Tickets + Orders as first cards | Matches buyer jobs (wallet / receipts) |
| Browse events | Clear empty-state / discovery path when the wallet is empty |
| Host / Become a host on dual-role or prospect users | Legitimate mode bridge (should stay secondary to switcher) |
| Short page | Not a Host-style 14-link feature dump |

### 2.5 What feels weak

| Weakness | Detail |
| --- | --- |
| **Counts ≠ command** | Lifetime totals do not answer “what do I do next?” |
| **Misleading ticket copy** | “Ready for door entry” on an all-time count |
| **Passport is a button disguised as a metric** | Value `Open` teaches nothing about progress |
| **Description overpromises** | Mentions Vault unlocks and refunds; home never shows them |
| **No time axis** | No next event date, no upcoming vs past split |
| **No ops urgency** | Unread messages, pending pickups, open refunds, cart, alerts absent |
| **Account card is admin-shaped** | Email + raw `roles` string feels like a debug panel for most fans |
| **Role escape hatches compete with chrome** | Host/Support/Admin CTAs sit in the primary personal narrative; switcher / SiteHeader already cover mode |
| **Zero empty-state craft** | New user with 0 tickets sees `0` / `0` / `Open` — not guidance |
| **Mobile bottom nav already has Home** | Home must earn the tap; today it mostly repeats sidebar links |

### 2.6 What should move out

| Current element | Recommendation |
| --- | --- |
| Raw **Roles:** list on Account card | **Move out** of home — Settings / debug only |
| Primary **Host workspace / Become a host** block | **Demote** — rely on `WorkspaceSwitcher` + optional single secondary link; not a peer to tickets |
| **Support** / **Admin** CTAs | **Move out** of Personal home — role tools already have their shells |
| Lifetime **order count** as a hero metric | **Demote** — keep deep link via Orders; prefer “needs attention” (pending payment / recent) if shown |
| Static Passport **`Open`** card | **Replace** with progress snapshot or drop card and use quick action |
| Long product laundry-list description | **Shorten** — one line on “next ticket / next action” |
| Footnote about Alerts / push | **Move** into Alerts empty state or Settings; home should link Alerts if unread |

**Do not put on Personal home (anti-dump):** full ticket wallet, full order table, Vault studio, host desk, team staff management, analytics charts, duplicate sidebar grid of all `buyerNav` items.

### 2.7 What should be added

Priority model mirrors Host Command Center (§5 in [HOST_AREA_AUDIT.md](./HOST_AREA_AUDIT.md)): **actionable strips first**, hide sections when empty, deep-link into existing `/dashboard/*` pages.

| Priority | Add | Why |
| --- | --- | --- |
| **P0** | Next event / next ticket (date, venue, Open QR) | Core personal job |
| **P0** | Active / upcoming tickets strip (≤3) | Wallet without leaving home |
| **P0** | Quick actions row | Browse events, tickets, messages, passport |
| **P1** | Merch pickups / cart needing action | Pre-door and post-event urgency |
| **P1** | Unread messages (+ optional Alerts badge) | Already in sidebar/mobile; home should surface count |
| **P1** | Refund status (open requests only) | Description already promises refunds |
| **P2** | Passport progress (stamps / next badge) | Replace fake metric |
| **P2** | Vault unlocks (recent or pending) | Match description promise |
| **P2** | Fan Connect activity (requests) | Social urgency; hide if none |
| **P2** | Ambassador earnings / links (enrolled only) | Hide if not an ambassador |
| **P3** | Following / host updates | Nice-to-have; avoid competing with tickets |

### 2.8 Should `/dashboard` become Personal Command Center?

| Option | Summary | Verdict |
| --- | --- | --- |
| **A** | `/dashboard` = **Personal Command Center** home; keep URL; remodel body into actionable sections (§2.9) | **Recommended** |
| B | Keep soft greeting + metric cards; put “command” content only in sidebar | Rejected — home wastes the highest-traffic Personal entry |
| C | Add `/dashboard/home` or `/dashboard/command` as a second home | Rejected — same class of confusion Host avoided by canonical `/host` |
| D | Redirect `/dashboard` → `/dashboard/tickets` | Rejected — loses multi-module snapshot (messages, merch, passport) |

**Rationale**

1. Option A already chose `/dashboard` = Personal account and `/host` = Host Command Center — Personal deserves a matching **home job**, not a weaker cousin.
2. The route inventory (§1) already has the deep pages; home should **compose signals**, not duplicate full UIs.
3. Code already labels the shell **Personal** and the page eyebrow **Personal** — “Personal Command Center” is the product name for this home, parallel to Host — not a new route prefix.
4. SiteHeader workspace entry is **Personal** → `/dashboard` (Phase 2); Command Center home framing comes in Phase 3.

**Verdict:** Yes — **`/dashboard` should become the Personal Command Center.** Keep the path. Remodel content. Do not invent a second home route.

### 2.9 Recommended Personal Command Center sections

Evaluate each proposed section against today’s APIs / pages. **Hide when empty** unless noted.

| Section | Purpose | Suggested data (known / nearby) | Empty state | Priority | On home? |
| --- | --- | --- | --- | --- | --- |
| **Next event / next ticket** | Single primary “what’s next” with Open QR / ticket detail | Derive soonest upcoming from `fetchMyTickets()` or passport `upcoming_tickets` | “No upcoming tickets” + Browse events | **P0** | **Yes — hero** |
| **Active tickets** | Up to 3 upcoming / transferable tickets | Same ticket list, filtered | Collapse section; rely on hero empty | **P0** | **Yes** |
| **Upcoming orders / merch pickups** | Orders awaiting payment + merch ready for pickup / ship | `fetchMyOrders` (attention subset); `fetchMyMerch` (pending pickup); optional cart via `fetchBuyerCart` | Hide if none; link Merch / Cart when cart has lines | **P1** | **Yes** |
| **Refund status** | Open refund requests only | `fetchMyRefunds` filtered to non-terminal | Hide if none | **P1** | **Yes** (compact) |
| **Unread messages** | Count + jump to inbox | Existing unread messages hook / messaging-api | “Inbox clear” or hide | **P1** | **Yes** |
| **Fan Connect activity** | Pending requests / suggestions count | Connect APIs under `/connect` | Hide if none | **P2** | **Yes** (compact) |
| **Passport progress** | Stamps toward next badge / loyalty snapshot | `fetchMyPassport` / `fetchMyBadges` summary | “Start stamping — browse events” | **P2** | **Yes** (replace static card) |
| **Vault unlocks** | Recent unlock or pending purchase | `fetchMyVaultLibrary` stats / activity head | Hide if none | **P2** | **Yes** (compact) |
| **Ambassador earnings / links** | Payable snapshot + copy-link affordance | `fetchAmbassadorEarningsSummary` / enrollments | **Hide** if not enrolled | **P2** | **Yes** (conditional) |
| **Following / host updates** | Hosts followed + soft “what’s new” | `fetchMyFollowing`; richer updates may need API later | Link Following / Hosts | **P3** | **Optional** — defer if home feels crowded |
| **Quick actions** | Short button row, not a nav grid | — | Always show small set | **P0** | **Yes** |

#### Quick actions (target)

| Label | Target | Who |
| --- | --- | --- |
| Browse events | `/events` | Everyone |
| My tickets | `/dashboard/tickets` | Everyone |
| Messages | `/dashboard/messages` | Everyone |
| Passport | `/dashboard/passport` | Everyone |
| Merch / Cart | `/dashboard/merchandise` or `/dashboard/cart` | Everyone (prefer cart if lines > 0) |
| Ambassadors | `/dashboard/ambassador` | Only if enrolled / active promotions |
| Switch to Host | `/host` via switcher semantics | Dual-role only — secondary |

### 2.10 Map from current `/dashboard` → Personal Command Center

| Current block | Proposal |
| --- | --- |
| Eyebrow Personal + Hello | **Keep** — optionally title/subtitle → “Personal Command Center” / next-action line |
| Browse events (header) | **Keep** as primary discovery CTA; also in Quick actions |
| Tickets count metric | **Replace** with Next ticket hero + Active tickets strip |
| Orders count metric | **Replace** with attention strip (pending payment / recent) or fold into merch/orders section |
| Passport `Open` metric | **Replace** with Passport progress snapshot |
| Account card (email + roles + Host/Support/Admin) | **Remove or shrink** — email optional; roles out; Host demoted; Support/Admin out |
| Alerts footnote | **Remove** — surface unread Alerts in messages/alerts strip or quick action |

### 2.11 Success criteria

A signed-in fan should answer in under two seconds on `/dashboard`:

1. What is my **next event / ticket**?
2. Do I have **anything urgent** (pickup, refund, unread message, cart)?
3. Where do I go for **wallet vs identity vs earn**? → deep links / quick actions, not a second sidebar.

If those three are obvious, Personal Command Center has succeeded — without mixing Host ops data.

### 2.12 Implementation note

Implemented in Phase 3: small section components under `components/personal/command-center/`, existing fetchers, hide-when-empty optional strips, P0 then deferred loads (`Promise.allSettled`). See §14 Phase 3.

### 2.13 What `/dashboard` shows now (Phase 3 shipped)

| Block | Content |
| --- | --- |
| **Header** | Eyebrow **Personal Command Center**; Hello {name}; short description; Browse events — **no** roles dump, **no** in-body WorkspaceSwitcher |
| **Welcome** (quiet / new user) | Browse events · Set up Passport · Promote an event · Become a host (secondary) — no zero-card wall |
| **Next up** | Active ticket (Open QR via `TicketQrModal`) · merch pickup · cart resume · empty browse |
| **My activity** | Attention chips only (hide when all quiet) |
| **Messages & community** | Unread / Connect pending / Following — hide section when empty |
| **Identity** | Passport progress · badges · review prompt when eligible |
| **Vault / Ambassadors** | Conditional; hide when empty |
| **Quick actions** | Short wrap row (not a feature grid) |

**Privacy:** Own-data only (§12). No host finance, scanner, admin, raw QR text, or payment provider refs on home.

---

## 3. Proposed Personal sidebar / navigation

**Source of truth today:** `buyerNav` / `buyerNavGroups` in `frontend/src/lib/nav/workspace.ts`  
**Shell title:** Personal (`PERSONAL_WORKSPACE_TITLE`)  
**Surfaces:** Desktop sidebar + mobile drawer (`WorkspaceShell`); mobile bottom nav is a **subset** (Home, Alerts, Messages, Events) — see §3.5  
**Connect:** Canonical product is `/connect/*` with the same Personal shell; sidebar may keep the `/dashboard/connect` alias href (active-state already treats `/connect` as Connect)

### 3.1 Current sidebar (audit)

| Group | Label | Route | Badge | Notes |
| --- | --- | --- | --- | --- |
| Home | Overview | `/dashboard` | — | Exact-match active only |
| Home | Alerts | `/dashboard/notifications` | `notifications` | In-app inbox |
| Activity | Tickets | `/dashboard/tickets` | — | Buyer wallet |
| Activity | Orders | `/dashboard/orders` | — | Receipts |
| Activity | Merch | `/dashboard/merchandise` | — | Label short; URL long form |
| Activity | Refunds | `/dashboard/refunds` | — | Buyer requests |
| Community | Messages | `/dashboard/messages` | `messages` | Fan inbox |
| Community | Team | `/dashboard/team` | — | Host-workspace bridge; collides with Host **Team** |
| Community | Connect | `/dashboard/connect` | — | Alias → `/connect` |
| Community | Following | `/dashboard/following` | — | Hosts followed |
| Identity | Passport | `/dashboard/passport` | — | Loyalty hub |
| Identity | Badges | `/dashboard/badges` | — | Also linked from Passport |
| Identity | Vault | `/dashboard/vault` | — | Fan library |
| Identity | Reviews | `/dashboard/reviews` | — | Own verified reviews |
| Growth | Ambassadors | `/dashboard/ambassador` | — | Plural label; singular path |
| Account | Settings | `/dashboard/settings` | — | Profile + appearance |

**Not in sidebar today (intentional deep links):** cart, ticket/order/merch detail, refunds/new, message settings/notifications, passport settings, vault subscriptions / item, team/workspaces, ambassador subpages, settings/notifications, `/dashboard/merch` legacy.

**Gap vs recommended structure:** Group names and item set already match. Only material nav change needed is **Team → Workspaces** (label). Optional polish: Ambassadors path pluralization later (not sidebar-blocking).

### 3.2 Final grouped sidebar (proposed)

**Decision:** Adopt the recommended six-group Personal sidebar. Keep routes. Change one primary label (Team → Workspaces). Keep Cart and other deep links off primary nav.

Legend for columns below:

| Column | Meaning |
| --- | --- |
| **Sidebar** | `Yes` = primary Personal sidebar + mobile drawer; `No` = deep link / subnav / redirect only |
| **Label change** | Relative to today’s `buyerNav` label |
| **Priority** | `P0` always in nav · `P1` standard · `P2` keep but lower emphasis / conditional later |

#### Home

| Item | Route | Purpose | Sidebar | Label change | Priority |
| --- | --- | --- | --- | --- | --- |
| Overview | `/dashboard` | Personal Command Center home (§2) | **Yes** | No — keep **Overview** (page may say Personal Command Center in body) | **P0** |
| Alerts | `/dashboard/notifications` | In-app notification inbox | **Yes** | No | **P0** |

#### Activity

| Item | Route | Purpose | Sidebar | Label change | Priority |
| --- | --- | --- | --- | --- | --- |
| Tickets | `/dashboard/tickets` | Ticket wallet, QR, transfer entry | **Yes** | No | **P0** |
| Orders | `/dashboard/orders` | Purchase history / receipts | **Yes** | No | **P0** |
| Merch | `/dashboard/merchandise` | Merch pickup wallet / purchases | **Yes** | No — keep short label **Merch**; URL stays `merchandise` | **P0** |
| Refunds | `/dashboard/refunds` | Buyer refund requests | **Yes** | No | **P1** |

#### Community

| Item | Route | Purpose | Sidebar | Label change | Priority |
| --- | --- | --- | --- | --- | --- |
| Messages | `/dashboard/messages` | Fan inbox (fan↔host / Connect rules) | **Yes** | No | **P0** |
| Workspaces | `/dashboard/team` | Host workspaces I own or joined; jump into Host | **Yes** | **Yes** — **Team → Workspaces** (disambiguate Host Team staff) | **P1** |
| Connect | `/dashboard/connect` | Fan Connect entry (alias → `/connect`) | **Yes** | No | **P1** |
| Following | `/dashboard/following` | Hosts I follow + marketing opt-in | **Yes** | No | **P1** |

#### Identity

| Item | Route | Purpose | Sidebar | Label change | Priority |
| --- | --- | --- | --- | --- | --- |
| Passport | `/dashboard/passport` | Fan Passport / loyalty hub | **Yes** | No | **P0** |
| Badges | `/dashboard/badges` | Badge catalog + earned state | **Yes** | No — keep top-level (also linked from Passport) | **P1** |
| Vault | `/dashboard/vault` | Unlocked Vault library | **Yes** | No | **P1** |
| Reviews | `/dashboard/reviews` | Own verified event reviews | **Yes** | No | **P1** |

#### Growth

| Item | Route | Purpose | Sidebar | Label change | Priority |
| --- | --- | --- | --- | --- | --- |
| Ambassadors | `/dashboard/ambassador` | Promote events & earn | **Yes** | No for now — label **Ambassadors** stays; path singular until a later redirect | **P1** |

#### Account

| Item | Route | Purpose | Sidebar | Label change | Priority |
| --- | --- | --- | --- | --- | --- |
| Settings | `/dashboard/settings` | Profile name + appearance; gateway to notification prefs | **Yes** | No | **P0** |

### 3.3 Off-sidebar items (confirm stay deep-linked)

| Item | Route | Purpose | Sidebar | Label change | Priority |
| --- | --- | --- | --- | --- | --- |
| Cart | `/dashboard/cart` | Active / abandoned merch cart | **No** — link from Merch + Command Center | — | P1 deep |
| Merch item | `/dashboard/merchandise/[orderItemId]` | Pickup QR + merch review | **No** | — | P0 deep |
| Ticket detail / transfer | `/dashboard/tickets/[id]`(+`/transfer`) | QR, PDF, transfer | **No** | — | P0 deep |
| Order receipt | `/dashboard/orders/[id]` | Receipt detail | **No** | — | P0 deep |
| New refund | `/dashboard/refunds/new` | Submit refund request | **No** | — | P1 deep |
| Message settings / notifications | `/dashboard/messages/settings`, `…/notifications` | Messaging prefs | **No** | — | P2 deep |
| Passport settings | `/dashboard/passport/settings` | Visibility / directory | **No** | — | P1 deep |
| Vault item / subscriptions | `/dashboard/vault/[itemId]`, `…/subscriptions` | Item + subscription manage | **No** | — | P1 deep |
| Team workspaces picker | `/dashboard/team/workspaces` | Set active host workspace | **No** — reachable from Workspaces | Optional page title polish | P1 deep |
| Ambassador subpages | `/dashboard/ambassador/*` | Events, links, earnings, leaderboard, payouts | **No** — `AmbassadorDashNav` | — | P1 deep |
| Notification prefs | `/dashboard/settings/notifications` | Email + push | **No** — from Settings / Alerts | — | P0 deep (shared account) |
| Legacy merch | `/dashboard/merch` | Redirect → merchandise | **No** | — | redirect only |
| Connect aliases | `/dashboard/connect/*` | Redirect → `/connect/*` | **No** (parent Connect in sidebar) | — | alias only |

### 3.4 Label & collision notes (Personal vs Host)

| Personal sidebar | Host sidebar (same word) | Personal intent | Host intent | Personal label fix |
| --- | --- | --- | --- | --- |
| Tickets | Tickets & Entry | My wallet / QR | Desk / scan | Keep **Tickets** (Host already disambiguated) |
| Merch | Merch | My pickups | Studio / catalog | Keep **Merch** — mode chrome must carry context |
| Messages | Messages | Fan inbox | Host inbox | Keep **Messages** |
| Vault | Vault | My library | Studio | Keep **Vault** |
| Ambassadors | Ambassadors | Earn / promote | Manage campaigns | Keep **Ambassadors** |
| Settings | Settings | Account | Host org | Keep **Settings** |
| Team → **Workspaces** | Team | My host memberships | Staff & invites | **Required** label change |

### 3.5 Mobile bottom nav (related, not sidebar)

Today (`MobileBottomNav`): **Home** · **Alerts** · **Messages** · **Events** (public `/events`).

| Item | Keep on bottom nav? | Notes |
| --- | --- | --- |
| Home → `/dashboard` | **Yes** | Personal Command Center |
| Alerts | **Yes** | Matches sidebar P0 |
| Messages | **Yes** | Matches sidebar P0 |
| Events | **Yes** | Discovery; not in Personal sidebar (correct — public browse) |
| Tickets | Optional later | Only if Command Center + wallet need a fourth utility slot; do not bloat to 5+ |

Bottom nav must stay a **subset** of Personal jobs + discovery — not a second full sidebar.

### 3.6 Implementation checklist (deferred)

| Change | Effort | Routes |
| --- | --- | --- |
| Rename nav label Team → **Workspaces** in `buyerNav` | Tiny | No URL change (`/dashboard/team` stays) |
| Optional: page titles / breadcrumbs “Team” → “Workspaces” | Tiny | Same |
| Point Connect nav `href` at `/connect` instead of alias | Optional | Alias routes remain |
| Ambassadors path `/dashboard/ambassadors` + redirect | Later | Not required for sidebar ship |
| Personal Command Center home body (§2) | Separate | `/dashboard` |

**Do not:** mix Host nav into Personal sidebar; add Cart/Refunds/new as primary peers without need; delete Connect aliases or merch redirects in this phase.

### 3.7 Sidebar verdict

| Question | Answer |
| --- | --- |
| Is the recommended structure right? | **Yes** — it already matches shipped `buyerNav` groups |
| Biggest nav fix? | **Team → Workspaces** (label only) |
| Cart in sidebar? | **No** — deep link |
| Badges in sidebar? | **Yes** — keep Identity peer (Passport remains hub) |
| Overview label vs Personal Command Center? | Sidebar **Overview**; home page carries Command Center framing |

---

## 4. Buyer naming audit

**Goal:** One stable chrome vocabulary for the `/dashboard` mode, without erasing role words (fan, buyer, ticket holder, attendee) where they are contextually correct in page copy.

**Preferred direction (locked for this audit)**

| Layer | Final language |
| --- | --- |
| Workspace **mode** label (sidebar title, breadcrumb root) | **Personal** |
| Workspace **switcher** option | **Personal account** |
| Host counterpart | **Host: {display_name}** (or “Host workspace: …” — keep switcher/Host audit alignment) |
| Home product framing | **Personal Command Center** |
| URL prefix | `/dashboard` (unchanged; not user-facing brand) |
| Code / API identifiers | May keep `buyer*`, `fan*`, `attendee` — not user chrome |

### 4.1 Where names appear today

| Surface | Current language | File / source |
| --- | --- | --- |
| Sidebar / shell title | **Personal** | `PERSONAL_WORKSPACE_TITLE` in `host-access.ts`; `dashboard/layout.tsx` |
| Breadcrumb root | **Personal** | `breadcrumbs.ts` (`dashboard: "Personal"`) |
| Workspace switcher | **Personal account** | `WorkspaceSwitcher.tsx` |
| `/workspaces` chooser | **Personal account** | `workspaces/page.tsx` |
| Site header (logged in) | **Personal** → `/dashboard` | `SiteHeader.tsx` |
| Site footer | **Personal** | `SiteFooter.tsx` |
| Home eyebrow | **Personal** | `dashboard/page.tsx` |
| Home description | “Your personal account on **Pàdéyá**…” | `dashboard/page.tsx` |
| Mobile bottom nav aria | “Personal mobile navigation” | `MobileBottomNav.tsx` |
| Nav code | `buyerNav`, `BuyerNavGroupId`, `onBuyerSurface` | `workspace.ts`, layout helpers |
| Nav prefs storage scope | Internal key `"buyer"` (maps Personal/Buyer titles) | `nav-preferences.ts` |
| Page copy examples | Fan Passport, Ambassadors, My merch (legacy redirect), Vault, Your teams | Various `dashboard/**/page.tsx` |
| Unification doc (stale) | Still says sidebar title **Buyer** in places | `DASHBOARD_HOST_UNIFICATION_AUDIT.md` § shared shell — **doc drift**; code is Personal |

**Drift summary:** User-facing workspace chrome is **Personal** (shell, switcher option **Personal account**, SiteHeader/Footer). Code may still say `buyerNav` / storage scope `"buyer"`. Page bodies correctly mix **fan / buyer / ticket / attendee** language where those words mean purchaser, Fan products, or check-in.

### 4.2 Name inventory — keep, retire, or contextual

| Name | Role | Recommendation |
| --- | --- | --- |
| **Personal** | Workspace mode | **Keep** — canonical chrome label |
| **Personal account** | Switcher / chooser | **Keep** — canonical switch label |
| **Personal Command Center** | `/dashboard` home product name | **Adopt** in home title/eyebrow framing (§2, §4.4) |
| **Dashboard** | SiteHeader / footer entry | **Demote** — prefer entry that opens Personal (or last-used workspace per Option A); do not use as sidebar title |
| **Buyer** | Code, commerce, admin “buyers” | **Retire from chrome**; keep in code/API/admin where it means purchaser |
| **Attendee** | Event attendance / check-in context | **Contextual page copy only** — not mode label |
| **Fan** | Passport, Connect, messaging, public `/fans` | **Contextual + product names** (Fan Passport, Fan Connect) — not mode label |
| **Ticket holder** | Tickets, transfers, QR | **Contextual page copy only** |
| **Pàdéyá** | Brand | Always accented in user-facing prose |

### 4.3 Decision answers

#### Should sidebar title be Personal instead of Buyer?

**Yes — and it already is.**  
`PERSONAL_WORKSPACE_TITLE = "Personal"`. Do **not** revert to Buyer. Update stale docs that still say Buyer sidebar. Code may keep `buyerNav`.

#### Should `/dashboard` home say “Personal Command Center” or “Your Pàdéyá dashboard”?

**Prefer Personal Command Center** (aligned with Host Command Center).

| Option | Verdict |
| --- | --- |
| **Personal Command Center** | **Recommended** — pairs with `/host` Host Command Center; reinforces mode |
| Your Pàdéyá dashboard | Rejected as primary — reintroduces “dashboard” as product name and weakens Personal ↔ Host symmetry |
| Hello, {name} only | Keep as greeting **title**; put Command Center in eyebrow or subtitle |

**Target framing (copy later, no route change):**

- Eyebrow: `Personal Command Center` (or keep `Personal` + subtitle)
- Title: `Hello, {name}`
- Description: one line on next ticket / next action — not a feature laundry list

#### Should “Team” be renamed to “Workspaces” or “My teams”?

**Workspaces** (not “My teams”).

| Option | Verdict |
| --- | --- |
| **Workspaces** | **Recommended** — matches page content (host workspaces), `/workspaces` chooser, and switcher mental model |
| My teams | Rejected — still collides with Host **Team** (staff) and sounds like people-management |
| Team (current) | Rejected for sidebar — highest Personal↔Host label collision |

Keep URL `/dashboard/team` for now (**rename in UI only**). Update page eyebrow/title from “Team” / “Your teams” toward Workspaces in the same pass.

#### Should “Merch” be “My merch”?

**No — keep Merch** in the sidebar.

| Option | Verdict |
| --- | --- |
| **Merch** | **Recommended** — short; Host also says Merch; mode chrome (Personal vs Host) disambiguates |
| My merch | Optional **page title** only (“My merch” / “Merchandise wallet”); do not lengthen every sidebar row |

Same pattern as Host: short nav labels; possessive “My …” in page headers when helpful.

#### Should “Vault” be “My Vault”?

**No — keep Vault** in the sidebar.

| Option | Verdict |
| --- | --- |
| **Vault** | **Recommended** — product name; Host Vault = studio, Personal Vault = library |
| My Vault | Optional page title / empty states only |

Avoid “My …” inflation across Identity (My Passport, My Badges, My Vault, My Reviews) — noisy and still doesn’t fix Host collisions.

#### Should “Ambassadors” be “My Ambassador links” or stay Ambassadors?

**Stay Ambassadors** in the sidebar.

| Option | Verdict |
| --- | --- |
| **Ambassadors** | **Recommended** — product program name; matches Host Ambassadors (different job, same brand word) |
| My Ambassador links | Rejected for nav — too narrow (overview is earnings + events + links + payouts) |

Page subnav can say “Links”, “Earnings”, etc. Optional later: URL `/dashboard/ambassador` → `/dashboard/ambassadors` (**redirect**), label unchanged.

### 4.4 Final language matrix (chrome vs page)

| Surface | Final user-facing language |
| --- | --- |
| Sidebar title | **Personal** |
| Breadcrumb root | **Personal** |
| Switcher | **Personal account** |
| `/workspaces` card | **Personal account** |
| Sidebar nav groups | Home · Activity · Community · Identity · **Earn** · Account (Phase 2; was Growth) |
| Sidebar items | Overview, Alerts, Tickets, Orders, Merch, Refunds, Messages, **Workspaces**, Connect, Following, Passport, Badges, Vault, Reviews, Ambassadors, Settings |
| Home product name | **Personal Command Center** |
| Site header entry | **Personal** → `/dashboard` (Phase 2 shipped); private Host peer removed; public Hosts kept |
| Page body roles | fan · buyer · ticket holder · attendee · ambassador — **context OK** |
| Brand | **Pàdéyá** |

### 4.5 Contextual role words (when to use which)

| Word | Use when | Avoid when |
| --- | --- | --- |
| **fan** | Social/identity: Passport, Connect, Following, fan↔host messages | Naming the whole workspace mode |
| **buyer** | Commerce: orders, cart, refunds, receipts, admin buyer lists | Sidebar title |
| **ticket holder** | Door entry, QR, transfer, check-in eligibility | Mode label |
| **attendee** | Post-check-in, reviews eligibility, attendance stats | Mode label |
| **ambassador** | Growth program pages | Replacing Ambassadors product name with “links” only |
| **Personal** | Mode, shell, switcher, Command Center | Replacing “Fan Passport” product name |

### 4.6 Naming verdict

| Question | Answer |
| --- | --- |
| Sidebar title Personal vs Buyer? | **Personal** (already shipped) |
| Home: Command Center vs “Your Pàdéyá dashboard”? | **Personal Command Center** |
| Team → ? | **Workspaces** |
| Merch → My merch? | **No** (page title optional) |
| Vault → My Vault? | **No** (page title optional) |
| Ambassadors → My Ambassador links? | **No** — stay **Ambassadors** |

**Net:** Lock chrome on **Personal / Personal account / Personal Command Center**. Keep short sidebar labels. Use fan/buyer/attendee/ticket holder only in situational copy. Fix the one collision: **Team → Workspaces**.

---

## 5. Tickets audit

**Routes**

| Route | File | Primary UI |
| --- | --- | --- |
| `/dashboard/tickets` | `frontend/src/app/dashboard/tickets/page.tsx` | `BuyerTicketsDashboard` |
| `/dashboard/tickets/[id]` | `…/tickets/[id]/page.tsx` | Digital pass + `TicketQrPanel` |
| `/dashboard/tickets/[id]/transfer` | `…/tickets/[id]/transfer/page.tsx` | Transfer form + history |

**Supporting modules:** `components/tickets/*`, `lib/tickets/buyer-ticket-groups.ts`, `lib/pwa/offline-ticket-cache.ts`, `lib/commerce-api` (`fetchMyTickets`, `fetchTicket`, `downloadTicketPdf`), `lib/advanced-tickets-api` (transfer, QR mode, cancel, device bind).

**Disposition:** All three routes **stay**. Improvements are UX / security hardening — no URL moves.

### 5.1 `/dashboard/tickets` — wallet list

#### Current UI

| Block | Behavior |
| --- | --- |
| Page chrome | `DashboardShell` — title **My tickets**; CTAs View orders / Browse events |
| Offline / cache alerts | Warning when offline; info while refreshing from cache |
| Summary | `TicketSummaryCards` — counts for upcoming / past / cancelled / all (tap switches tab) |
| Tabs | `TicketStatusTabs` — **upcoming** (default), past, cancelled, all |
| Grouping | Tickets grouped by event (`TicketEventGroupCard`) — cover, date/time, location, host message, calendar, download-all PDFs |
| Pass rows | `TicketPassCard` — type, status/readiness badges, holder, shortened entry code, offline badge, **View QR** / details |
| QR | `TicketQrModal` — fetch/cache ticket, show QR when allowed, copy `public_code`, download PDF |
| Empty | Page-level empty if zero tickets; per-tab `TicketEmptyState` otherwise |

#### Upcoming / past / cancelled grouping

Logic in `buyer-ticket-groups.ts` (mutually exclusive buckets):

| Bucket | Rule |
| --- | --- |
| **cancelled** | Status in `cancelled`, `refunded`, `voided`, `invalid` |
| **past** | Checked in **or** event ended / completed / cancelled / archived |
| **upcoming** | Everything else (typically `active` for a future event) |

Event groups sort: ready-for-QR first, then soonest `starts_at`. Within a group, `active` tickets first.

#### Empty states

| Case | Copy |
| --- | --- |
| Zero tickets (page) | “No active tickets” + Browse events |
| Upcoming tab empty | “No active tickets” + Browse events |
| Past tab empty | “No past tickets” |
| Cancelled tab empty | “No cancelled or refunded tickets” |
| All tab empty | “No tickets yet” |

**Gap:** Page-level empty title says “No **active** tickets” even when the user has never purchased — prefer “No tickets yet” at page level (tab copy can stay nuanced).

#### Mobile behavior

| Signal | Assessment |
| --- | --- |
| Layout | `max-w-3xl/4xl` column; pass cards stack (`flex-col` → `sm:flex-row`) |
| QR | Modal path avoids forcing full detail navigation — good for door |
| Dense chrome | Summary cards + tabs + collapsible groups — workable; first upcoming group auto-opens |
| Bottom nav | No direct Tickets tab (Home / Alerts / Messages / Events) — wallet reached via sidebar or home |

### 5.2 `/dashboard/tickets/[id]` — digital pass

#### Current UI

| Block | Behavior |
| --- | --- |
| Header | Event title; subtitle = ticket type · **full** `public_code` |
| Pass card | Dark “Pàdéyá ticket” stub + status; **always-on** QR (`TicketQrPanel`); full entry code; door tip (screenshots ≠ entry; rotating needs network) |
| Meta | Holder name, **masked** email, check-in state, QR mode, device-bound flag, table/seat, issued time |
| Linked merch | Optional card with pickup status → order / merchandise |
| Actions (online) | Download PDF; if **active**: Transfer, toggle static/rotating QR, Bind device, Cancel (password modal) |
| Offline | Cached ticket + alert; QR from cache when present |

#### QR access

| Path | How QR is shown |
| --- | --- |
| List → View QR | `TicketQrModal` — gated by `ticketStatusPresentation.showQr` |
| Detail page | Inline `TicketQrPanel` if `ticket.qr_payload` present — **not** status-gated the same way (cancelled may still show payload if API returns it; UI copy warns invalid at door) |
| Rendering | `QRCodeSVG` with `value={qr_payload}` only — **payload string is not rendered as visible text** |
| Modes | `static` vs `rotating` via `setTicketQrMode`; PDF download notes static QR for print |

#### Ticket PDF / pass download

| Capability | Status |
| --- | --- |
| PDF download | **Yes** — `downloadTicketPdf(ticket.id)` on detail, modal, group “download all”, actions menu |
| Analytics | `trackTicketDownloaded` |
| Apple Wallet / Google Wallet / `.pkpass` | **Not present** — PDF only |
| Offline PDF | Download requires online (`canDownloadPdf && online` on detail) |

#### Transfer / cancel / refund actions on detail

| Action | Present? | Notes |
| --- | --- | --- |
| Transfer | **Yes** — link to `/transfer` when `active` | Not in list `TicketActionsMenu` |
| Cancel ticket | **Yes** — `CancelTicketButton` (password + irreversible warning) | Destructive; good |
| Request refund | **No** on ticket surfaces | Lives under `/dashboard/refunds` — easy to miss from pass |
| View order | List menu when inactive; merch card links order on detail | Partial |

### 5.3 `/dashboard/tickets/[id]/transfer`

| Aspect | Current behavior |
| --- | --- |
| UI | Event summary card (`public_code`, type, status); recipient email + optional note; Transfer ownership CTA; transfer history `DataTable` |
| Rules (FE) | CTA disabled unless `ticket.status === "active"` and email non-empty |
| Product copy | Previous owner loses access; transfers audited; recipient email should already have a Pàdéyá account |
| Success | `router.push("/dashboard/tickets")` — no success toast on wallet |
| History | `from_email → to_email`, date, note — full emails visible to current holder |
| Empty history | “No transfers yet” |
| Offline | No offline transfer (network required) — correct |

**Gaps:** No confirmation step beyond single button; no explicit “you will lose QR access” checklist; list/actions menu does not surface Transfer; no link to refunds if user meant money-back instead of ownership change.

### 5.4 Offline-safe pass

| Mechanism | Behavior |
| --- | --- |
| Cache | `localStorage` keys `padeya.ticket.cache.v1.{id}` + list id index (max 40) |
| List hydrate | Initial state from `readCachedTicketList()`; merge keeps prior `qr_payload` if list API omits it |
| Detail / modal | Prefer network; fall back to cache with user-visible offline/cached alerts |
| Validation | Copy correctly states door validation is **server-side when online** — cache is display-only |
| Rotating QR | Detail warns rotating mode needs connection to refresh — offline rotating may be stale |

**Strengths:** Real offline wallet path already shipped.  
**Risks:** Full `Ticket` including `qr_payload` in `localStorage` (XSS / shared-device exposure); no TTL / purge on logout documented in FE helper; list empty-title mismatch.

### 5.5 Privacy / security

| Topic | Finding | Severity | Recommendation |
| --- | --- | --- | --- |
| Raw QR token in UI text | **Not shown** as plaintext — only encoded in SVG | OK | **Keep** — never print `qr_payload` in DOM text, toasts, or copy buttons |
| Copy actions | Copy **`public_code` only** (modal + menu) | OK | Do not add “Copy QR payload” |
| `public_code` on detail | Full code in header + pass body | Medium (shoulder surf) | Acceptable for door; keep list shortened via `shortenPublicCode` |
| Offline cache | Stores `qr_payload` in `localStorage` | Medium | Prefer session-aware purge on logout; consider encrypt-at-rest or shorter TTL; document threat model |
| Transfer history emails | Full `from_email` / `to_email` in table | Low–Med | Mask like holder email on detail, or show local-part only |
| Holder email on detail | `maskEmail` | OK | Keep |
| Cancel | Password re-auth | OK | Keep |
| Screenshot warning | Present on detail | OK | Keep; reinforce in QR modal |
| Pending tickets | Presentation hides QR (`showQr: false`) | OK | Ensure API also omits/forbids payload for unpaid |
| Authz | Own-ticket APIs; FE has no extra gate beyond `RequireAuth` | OK | Backend remains source of truth |
| Device bind | UA + screen fingerprint string | Low | Fine as soft preference; not a security boundary |

### 5.6 What should appear on Personal Command Center home

From §2 — tickets are **P0**. Home should compose signals, not the full wallet.

| Home element | Source | Notes |
| --- | --- | --- |
| **Next event / next ticket** hero | Soonest `upcoming` active ticket (same bucket rules) | Event title, when/where, status, primary **Open QR** (modal or detail) |
| **Active tickets** strip (≤3) | Upcoming groups / ready count | Deep link “All tickets” |
| Quick action **My tickets** | `/dashboard/tickets` | Always |
| Do **not** on home | Full tabbed wallet, transfer form, PDF bulk, cancel, QR mode toggles | Stay on tickets routes |
| Optional badge | Upcoming count | Replace today’s lifetime total metric |

### 5.7 Recommended improvements

| Improvement | Priority | Detail |
| --- | --- | --- |
| **Ticket wallet layout** | P1 | Keep event-group wallet; ensure first upcoming group is the visual hero; tighten summary so it doesn’t dominate mobile |
| **Next event pass card** | P0 | Shared component for home + top of `/dashboard/tickets` (event, time, Open QR, offline badge) |
| **QR modal** | P0 (polish) | Already exists — make list primary CTA open modal; add screenshot warning; link “Full pass” → detail; hide QR when `showQr` false consistently |
| **Detail QR consistency** | P1 | Gate inline QR with same `ticketStatusPresentation.showQr` as modal (don’t show scannable QR for cancelled if API still returns payload) |
| **Offline-safe pass** | P1 | Keep cache; purge on logout; surface “Cached for offline” on next-pass card; document rotating-QR offline limits |
| **Clear transfer / refund actions** | P1 | Add Transfer to active pass actions menu; on detail, pair Transfer with **Request refund** → `/dashboard/refunds/new?order_id=` when eligible; clarify cancel ≠ refund |
| **No raw QR token exposure** | P0 (guard) | Lint/review: never render or clipboard `qr_payload`; copy entry code only; avoid logging payload |
| **Empty copy** | P2 | Page-level “No tickets yet”; keep tab-specific empties |
| **Transfer UX** | P2 | Confirm step (“You will lose access”); success toast; optional mask emails in history |
| **Wallet passes** | P3 | Apple/Google Wallet — out of scope until product asks; PDF remains canonical download |

### 5.8 Map: current → target

| Area | Today | Target |
| --- | --- | --- |
| List | Strong grouped wallet + QR modal | Add next-pass hero; expose Transfer in menu |
| Detail | Full pass + PDF + transfer + cancel | Align QR gating; add refund path; demote power tools (QR mode / bind) under “Advanced” |
| Transfer page | Functional form + audit history | Confirmation + clearer loss-of-access copy |
| Home | Lifetime ticket **count** only | Next ticket + Open QR + count of upcoming |
| Security | No plaintext payload in UI | Keep + cache hygiene + no payload copy |

### 5.9 Tickets verdict

| Question | Answer |
| --- | --- |
| Are ticket routes solid? | **Yes** — substantial wallet, modal QR, PDF, offline cache, transfer, cancel |
| Biggest product gap vs Personal Command Center? | Home does not reuse next-pass / QR; refund path disconnected |
| Biggest security watchpoint? | `qr_payload` in `localStorage`; keep payload out of visible UI/clipboard |
| Apple Wallet? | Not required for this phase — PDF + live QR sufficient |
| Route changes? | **None** — stay on current URLs |

---

## 6. Orders, merch, cart, refunds audit

**Routes in scope**

| Route | File | Role |
| --- | --- | --- |
| `/dashboard/orders` | `frontend/src/app/dashboard/orders/page.tsx` | Order history / receipts list |
| `/dashboard/orders/[id]` | `…/orders/[id]/page.tsx` | Receipt detail + payment timeline |
| `/dashboard/merchandise` | `…/merchandise/page.tsx` | Buyer merch wallet (`BuyerMerchDashboard`) |
| `/dashboard/merchandise/[orderItemId]` | `…/merchandise/[orderItemId]/page.tsx` | Pickup QR / shipping + review |
| `/dashboard/cart` | `…/cart/page.tsx` | Saved merch cart (off primary nav) |
| `/dashboard/refunds` | `…/refunds/page.tsx` | Refund request list |
| `/dashboard/refunds/new` | `…/refunds/new/page.tsx` | Create full refund request |
| `/dashboard/merch` *(legacy)* | `…/merch/page.tsx` + `next.config.ts` **308** | Redirect → merchandise |

**Supporting modules:** `lib/commerce-api`, `lib/merch-api`, `lib/finance-api`, `lib/merch-buyer-status.ts`, `lib/merch/buyer-merch-wallet.ts`, `components/merch/buyer/*`, `MerchPickupQr`, offline merch cache.

**Disposition:** Functional routes **stay**. Legacy merch **redirect** (already formalized). No merge of Tickets into Orders.

### 6.1 Orders — history & receipt

#### `/dashboard/orders` — clarity

| Aspect | Today |
| --- | --- |
| UI | `DataTable`: Event, Reference, Date (`paid_at` \|\| `created_at`), Items (ticket qty · merch qty), Total, Status, Receipt CTA |
| Cross-links | Header → Merch, Browse events |
| Empty | “No orders yet” + Browse events — clear |
| Filters / tabs | **None** — flat list of all statuses |
| Grouping | None by event or attention |

**What works:** Receipt mental model; ticket vs merch counts in Items column; money + status visible.  
**Weak:** No “needs attention” (pending payment) surfacing; no Refund CTA; table-dense on mobile; pending vs paid mixed without sort affordance.

#### `/dashboard/orders/[id]` — receipt

| Aspect | Today |
| --- | --- |
| Pending UX | Polls every **4s**; warning that tickets/merch wait for webhook (correct — no FE ticket mint) |
| Paid UX | Success alert; CTAs View tickets / View merch (if merch lines) |
| Content | Total card (buyer name/email), event & host links, line items, subtotal/discount/total, **Payment timeline**, checkout answers |
| Merch on receipt | Fulfillment `StatusBadge`, pickup code badge, instructions, Message host |
| Tickets on receipt | Line items only — no deep link per ticket id |
| Refund | **Not linked** |

**Gap:** Receipt is the natural place for **Request refund** and per-line “Open ticket” / “Open pickup” — currently users must navigate sideways.

### 6.2 Merch — wallet, pickup QR, shipping

#### `/dashboard/merchandise` — wallet

| Aspect | Today |
| --- | --- |
| Page title | **My merch** (sidebar label remains **Merch**) |
| Data | `fetchMyMerch` + `fetchMyEligiblePostEventDrops`; offline list cache |
| UI | `BuyerMerchDashboard` — summary cards + tabs mirroring tickets pattern |
| Tabs | **Ready** · **Shipping / Delivery** · **Completed** · **Cancelled** · All |
| Bucket rules | `ready_for_pickup` → ready; cancelled/refunded → cancelled; picked_up/delivered → completed; else → shipping (includes confirmed / awaiting shipment / shipped / pending) |
| Pass cards | `BuyerMerchPassCard` — status, method (Pickup / Delivery / POD), shortened codes, Open QR / details |
| QR | `MerchPickupQrModal` (list) |
| Empty | “No merch orders yet” (+ drops can populate without paid rows) |
| Cross-links | Orders, Cart, Tickets, Browse events |

#### Pickup status (buyer-safe labels)

From `merch-buyer-status.ts` / wallet helpers:

| Display status | Buyer label | Typical meaning |
| --- | --- | --- |
| `pending_payment` | Pending payment | Not paid — no pickup QR |
| `confirmed` | Confirmed | Paid; waiting for stand readiness |
| `ready_for_pickup` | Ready for pickup | Show QR at merch desk |
| `picked_up` | Picked up | Done (pickup path) |
| `awaiting_shipment` | Preparing shipment | Shipping / POD pack |
| `shipped` | Shipped | In transit (+ tracking when present) |
| `delivered` | Delivered | Done (ship path) |
| `cancelled` / `refunded` | Cancelled / Refunded | Invalid |

#### Pickup QR behavior

| Rule | Implementation |
| --- | --- |
| QR type | `padeya.merch.pickup` — explicitly **not** ticket entry (`MerchPickupQr` footnote) |
| Enabled when | Not `pending_payment`, `picked_up`, `cancelled`, `refunded` |
| Token | `qr_token` passed to `QRCodeSVG` only — not shown as raw text; pickup **code** shown as badge |
| Offline | Merch pickup cache; shipping address **never** cached (detail copy) |
| Desk validation | Server-side when online — same model as tickets |

#### Delivery / shipping status

| Supported? | Yes |
| --- | --- |
| Method labels | Pickup · Delivery (`shipping`) · Print on demand |
| Detail (non-pickup) | Method + `tracking_number` when present; list cards mention tracking after ship |
| Wallet tab | “Shipping / Delivery” buckets in-progress + ship-path items |
| Gap | No rich buyer timeline (ordered → packed → shipped → delivered); detail for ship is a short paragraph vs pickup QR pass |

#### `/dashboard/merchandise/[orderItemId]`

| Aspect | Today |
| --- | --- |
| Pickup | `MerchPickupQr` with status gating + offline hint |
| Shipping | Method + tracking string (minimal) |
| Reviews | Create / edit / remove verified merch review when `order_status === paid` and online |
| Host reply | Shown when present |

### 6.3 Cart — abandoned / active usefulness

| Aspect | Today |
| --- | --- |
| Scope | **Merch cart only** (not ticket checkout basket) |
| Nav | Off sidebar — linked from Merch page (+ proposed Command Center) |
| Actions | List lines (product, variant, qty, price); Remove; **Resume checkout** via `resume_path` or `/events/{slug}/checkout` |
| Empty | “Cart is empty” — **no** Browse events CTA |
| Copy | Correctly states nothing is purchased until payment succeeds |

**Usefulness:** **High** for resume-after-abandon; **low discoverability** without Merch/home entry. Worth keeping as deep link, not primary nav.

### 6.4 Refunds — request flow

| Route | Behavior |
| --- | --- |
| `/dashboard/refunds` | List `RefundCard`s; info alert (policy / support); Request refund + My orders CTAs |
| `/dashboard/refunds/new` | Paid orders only (`status === "paid"`); select order + reason (≥5 chars); `createRefundRequest`; redirect to list |
| Product rules (FE copy) | **Full refunds only**; approved refunds invalidate related tickets |
| Empty list | “No refund requests yet” + Request refund |
| Empty eligible orders | “No paid orders to refund” → View orders |

**Gaps**

| Gap | Detail |
| --- | --- |
| No deep link from order receipt / ticket | Users must know Refunds exists in Activity nav |
| Prefill | `refunds/new` ignores `?order_id=` (not implemented) |
| Selected-order summary | Says “N ticket(s)” even when order is merch-heavy — misleading |
| Partial refunds | Explicitly unavailable — keep honest |
| Status timeline | List cards only — no shared buyer timeline component with orders/merch |

### 6.5 `/dashboard/merch` redirect

| Layer | Status |
| --- | --- |
| `next.config.ts` | **308** `/dashboard/merch` → `/dashboard/merchandise` (+ `:path*`) |
| Client page | `router.replace("/dashboard/merchandise")` + skeleton |
| Nav | Already points at `/dashboard/merchandise` |

**Recommendation:** **Keep formal redirect** (already done). Do **not** delete the alias page/config until analytics show zero hits. Treat as **redirect**, not a second product surface.

### 6.6 Concept: unified “Purchases” vs separate nav

| Option | Summary | Verdict |
| --- | --- | --- |
| **A — Keep separate Tickets / Orders / Merch / Refunds** | Different jobs: entry pass · money receipt · fulfillment wallet · money-back | **Recommended** for sidebar (§3) |
| B — Single sidebar “Purchases” hub | One nav item → tabs for orders/merch/refunds | Rejected — buries Tickets (P0 door job) and Merch QR urgency |
| C — Soft “Purchases” on Command Center only | Home strip: pending payment, ready pickups, open refunds; deep links to existing pages | **Recommended** as home composition, not nav merge |

**Mental model to teach**

| Surface | Job |
| --- | --- |
| **Tickets** | Door entry (QR / PDF / transfer) |
| **Orders** | What I paid (receipt / payment status) |
| **Merch** | What I collect or receive (pickup QR / shipping) |
| **Cart** | What I have not paid yet (merch) |
| **Refunds** | Money-back requests on paid orders |

Orders is the **spine** connecting tickets + merch lines; it should not replace wallets.

### 6.7 Buyer-safe status timeline (recommended)

One shared pattern (visual language) across receipt, merch detail, refund card — **buyer words only**, no host/ops jargon.

#### Order / payment

`Pending` → `Paid` → (`Refund requested` → `Refunded`) · or `Failed` / `Cancelled`

#### Merch fulfillment (pickup)

`Pending payment` → `Confirmed` → `Ready for pickup` → `Picked up`  
(Branch: `Cancelled` / `Refunded`)

#### Merch fulfillment (delivery)

`Pending payment` → `Confirmed` → `Preparing shipment` → `Shipped` → `Delivered`  
(Branch: `Cancelled` / `Refunded`)

#### Refund

`Submitted` → `In review` → `Approved` / `Rejected` → (`Paid out` if shown)

**Rules:** Hide host-internal states; map raw fulfillment enums through `buyerMerchStatusLabel`; never show desk queue IDs; QR only in Ready (and Confirmed if product allows — today Confirmed can still show QR unless disabled list is expanded).

### 6.8 Empty states — gaps & targets

| Surface | Today | Target |
| --- | --- | --- |
| Orders | Good + Browse events | Add “Pending payments” empty nuance if filtered later |
| Merch | Good + Browse events | If cart has lines, CTA **Resume cart** |
| Cart | Empty, **no CTA** | Add Browse events / continue shopping |
| Refunds list | Good | Secondary: link Orders |
| Refunds new (no paid) | Good → Orders | Prefill from order when linked |
| Merch shipping tab | Tab-specific empty exists | Keep |

### 6.9 Personal Command Center — commerce strips

| Home section (§2) | Source | CTA |
| --- | --- | --- |
| Upcoming orders / merch pickups | Pending orders + `ready_for_pickup` / shipped needing attention | Open receipt / Open pickup QR |
| Refund status | Open refund requests | `/dashboard/refunds` |
| Cart (if lines > 0) | `fetchBuyerCart` | Resume checkout |
| Quick actions | Orders · Merch · (Cart if non-empty) | Existing routes |

### 6.10 Recommended improvements

| Improvement | Priority | Detail |
| --- | --- | --- |
| Keep Tickets / Orders / Merch / Refunds separate in sidebar | P0 | Do not unify into one Purchases nav item |
| Soft Purchases on Command Center | P0 | Attention strip only |
| Order → Refund + wallet deep links | P1 | Receipt: Request refund; per ticket/merch line → pass pages |
| `refunds/new?order_id=` prefill | P1 | From receipt / ticket |
| Fix refund order summary copy | P2 | “tickets + merch” not “N ticket(s)” only |
| Buyer-safe timeline component | P1 | Shared on receipt, merch detail, refund card |
| Cart empty CTA + home discoverability | P1 | Browse / resume; Command Center when non-empty |
| Merch shipping detail richness | P2 | Tracking link, carrier, last update — still buyer-safe |
| Align QR gating | P1 | Confirmed vs ready — product decision; document in MERCHANDISE.md |
| Keep `/dashboard/merch` 308 | P0 | Already formal — monitor, then deprecate client page later |
| Merch offline cache hygiene | P2 | Same class as tickets (purge on logout) |

### 6.11 Map & verdict

| Question | Answer |
| --- | --- |
| Order history clear? | **Mostly** — improve attention sorting + refund/ticket/merch exits from receipt |
| Merch pickup status? | **Strong** label map + wallet tabs |
| Pickup QR? | **Solid** — typed merch QR, gated, offline-aware, not ticket QR |
| Shipping? | **Supported** but thinner than pickup UX |
| Refund flow? | **Clear** full-only policy; poorly connected from orders/tickets |
| Abandoned cart useful? | **Yes** — keep off-nav; improve empty + discovery |
| Formal merch redirect? | **Already yes** (308 + client) — keep |
| Unified Purchases nav? | **No** — separate Tickets vs Orders vs Merch; Purchases only as home concept |

---

## 7. Messages, Connect, Following audit

**Routes in scope**

| Route | Role | Shell |
| --- | --- | --- |
| `/dashboard/messages` | Fan inbox (list) | Personal + `MessagesInbox mode="fan"` |
| `/dashboard/messages/[threadId]` | Fan inbox focused on thread | Same |
| `/dashboard/messages/settings` | Who can message + blocked users | Personal (off sidebar) |
| `/dashboard/messages/notifications` | Message notification summaries | Personal (off sidebar) |
| `/dashboard/connect` · `/dashboard/connect/*` | **Alias** → `/connect` · `/connect/*` | Server `redirect()` |
| `/connect` | Fan Connect hub (“Circle”) | Personal shell + `ConnectShell` subnav |
| `/connect/suggestions` | Shared-energy suggestions | Same |
| `/connect/events` | Same public events | Same |
| `/connect/requests` | Incoming / outgoing Connect requests | Same |
| `/connect/connections` | Accepted peer connections | Same |
| `/connect/settings` | Fan Connect privacy (opt-in, off by default) | Same |
| `/dashboard/following` | Hosts I follow + email Notify toggle | Personal |

**Docs of record:** [MESSAGING.md](./MESSAGING.md) · [FAN_CONNECT.md](./FAN_CONNECT.md).

### 7.1 Do Messages and Connect feel duplicated?

**No — different jobs that meet at chat unlock.**

| Product | Job | Who | Chat? |
| --- | --- | --- | --- |
| **Messages** | Private inbox | Fan ↔ **host** (always own gates); fan ↔ **fan** only after Connect accept | **Yes** — bubbles, requests, pins, stars |
| **Fan Connect** | Opt-in peer discovery graph | Fan ↔ fan matching on **safe public** context | **Not until** mutual accept → then thread appears in Messages with **Fan Connect** badge |
| **Following** | Host relationship + marketing email opt-in | Fan → **host** | No peer graph; message host via separate Start Message / inbox |

**Overlap users may feel**

| Symptom | Reality |
| --- | --- |
| Both under Community sidebar | Correct — social cluster; not the same feature |
| Fan↔fan threads live in Messages | Intentional — Connect unlocks chat; Messages is the inbox |
| “Requests” in both | Different: Messages **message requests** (host gate) vs Connect **connection requests** (peer graph) |

**Verdict:** Keep both. Clarify copy (Connect = meet fans; Messages = conversations). Do **not** merge Connect UI into the messages inbox.

### 7.2 Should Connect stay its own product section?

**Yes.**

| Reason | Detail |
| --- | --- |
| Product brand | Fan Connect is a named surface with its own privacy defaults (all off) |
| IA | Own subnav: Circle · Shared energy · Same events · Requests · Connections · Privacy |
| Safety | Separate admin: `/admin/fan-connect/*` vs `/admin/message-reports` |
| Canonical URL | `/connect/*` — not nested under `/dashboard/messages` |
| Shell | Same Personal chrome as `/dashboard` (Option A) — already unified |

Sidebar label stays **Connect** (short); page eyebrow **Fan Connect**.

### 7.3 Messages audit (fan inbox)

| Aspect | Today |
| --- | --- |
| UI | Full `MessagesInbox`: filters (all / unread / requests / event / starred / archived), thread list, composer, pins, stars, search, related-event card |
| Unread | Sidebar + mobile badge via `useUnreadMessages` / realtime + poll (`badge: "messages"` on nav) |
| Fan↔host | Own relationship gates — never Fan Connect rules |
| Fan↔fan | Connection-only; badge + safe context string; no VIP/spend/private venue |
| Block / report | `MessageActionMenu` → block + `ReportMessageDialog`; settings lists blocked users + unblock |
| Settings | `/dashboard/messages/settings` — who can message; blocked list |
| Host parallel | `/host/messages` — separate inbox, same component `mode="host"` |
| Empty | `EmptyMessagesState` inside inbox |

**Strengths:** Substantial; permission model documented and enforced server-side.  
**Gaps for Personal home:** Home does not surface unread count today (§2).

### 7.4 Fan Connect audit (`/connect/*` + aliases)

| Aspect | Today |
| --- | --- |
| Canonical | `/connect/*` under Personal `WorkspaceShell` + `ConnectShell` |
| Aliases | Six `/dashboard/connect*` pages — immediate server redirect |
| Nav href | `buyerNav` still points at `/dashboard/connect` (alias) — active state also matches `/connect` |
| Privacy defaults | Connect **off** until user enables (`fan_connect_enabled` etc.) |
| Matching | Public shared events/hosts/scenes only — see FAN_CONNECT.md |
| Reports / blocks | Connection-level reports & blocks (admin Fan Connect); also honor messaging blocks |
| Unread / pending | `pending_requests` exists in Connect APIs/types — **not** wired as sidebar badge today |

### 7.5 Following audit

| Aspect | Today |
| --- | --- |
| Data | `fetchMyFollowing` — host id, name, username, `marketing_opt_in`, `followed_at` |
| UI | List rows → Legacy `/@username`; **Notify me by email** / Mute; Unfollow |
| Updates feed | **None** — no announcements, upcoming events, or activity stream on this page |
| Empty | Clear + Browse hosts |
| Relation to Connect | Following hosts ≠ Fan Connect peers; shared-host is only a **matching signal** inside Connect when both opted in |

### 7.6 Unread counts

| Signal | Wired today? | Where |
| --- | --- | --- |
| Message unread | **Yes** | Sidebar Messages, mobile bottom nav, realtime hook |
| Alerts / notifications | **Yes** | Sidebar Alerts (`badge: "notifications"`) |
| Connect pending requests | **Data exists, no nav badge** | Could surface on Connect nav or home strip |
| Following “new from hosts” | **No** | Would need announcements / digest API — not on Following page |

### 7.7 Blocked / reported user handling

| Layer | Mechanism | Surface |
| --- | --- | --- |
| Messaging block | Block from thread; listed in message settings; disables send | Fan + host inboxes |
| Messaging report | Report thread → admin `/admin/message-reports` | Participants report; admins moderate reported threads only |
| Fan Connect block | Connection / user blocks (`fan_connection_blocks` + messaging blocks) | Connect eligibility denies `blocked` |
| Fan Connect report | Connection reports → `/admin/fan-connect/reports` | Safe connection context — **not** a chat browser |
| Privacy invariant | Admins do not browse private chats without a report | Documented in MESSAGING.md |

**Buyer UX gap:** No single “Safety” page — blocks live under Messages settings; Connect privacy under `/connect/settings`. Acceptable if cross-linked; optional later “Safety & privacy” under Account.

### 7.8 Privacy boundaries (must not blur)

| Boundary | Rule |
| --- | --- |
| Fan ↔ host messaging | Independent of Fan Connect opt-in |
| Fan ↔ fan messaging | **Only** after accepted Connect; removed/blocked kills send |
| Connect discovery | Safe **public** reasons only — never private venues, VIP, spend, hidden events |
| Notifications | Prefer kinds/counts — not full message bodies by default |
| Following | Host marketing email is **explicit opt-in** per host (page copy already says follow ≠ email) |
| Host mass-DM of Connect graph | **Out of product** (EXECUTION_TRACKER / FAN_CONNECT non-goals) |

### 7.9 What should appear on `/dashboard` home

| Section | Priority | Content | Hide when |
| --- | --- | --- | --- |
| **Unread messages** | **P1** | Count + Open inbox | Zero unread (or show “Inbox clear” once) |
| **Fan Connect activity** | **P2** | Pending requests count → `/connect/requests` | Connect off or zero pending |
| **Following / host updates** | **P3** | Optional: “N hosts · email on for K” or 1–2 upcoming from followed hosts **if** a safe public API exists | No follows — or defer entirely |
| Quick action Messages | **P0** | Always in quick actions | — |
| Quick action Connect | **P2** | Only if Connect enabled or pending | — |

Do **not** embed full inbox or Connect suggestion grid on home.

### 7.10 Recommendations

#### Where Fan Connect belongs in sidebar

| Decision | Detail |
| --- | --- |
| **Keep under Community** | Messages · Workspaces · **Connect** · Following |
| Label | **Connect** (nav) / Fan Connect (page) |
| Order | Messages (P0) before Connect (P1) — inbox urgency first |
| Do not nest under Messages | Discovery ≠ inbox |

#### Should `/dashboard/connect` aliases remain?

| Decision | **Yes — keep aliases** |
| --- | --- |
| Why | Bookmarks, old docs, nav href already uses alias; zero UI cost (server redirect) |
| Optional polish | Point `buyerNav` `href` directly at `/connect` (active aliases already treat `/connect` as active) — aliases still stay |
| Do not delete | Until traffic is proven zero |

#### Should Following show host updates or only followed hosts?

| Option | Verdict |
| --- | --- |
| **List + Notify toggle only (today)** | **Recommended for v1** — clear job; email is the update channel when opted in |
| Full in-app host activity feed on Following | **Defer** — needs productized announcements/digest; risk of becoming a second Alerts |
| Light enhancement | **P3:** per-row “Upcoming” public event chip from followed hosts (public data only) — still not a social feed |

**Home:** Prefer Alerts + email for host broadcasts; Following page remains the **relationship manager**.

### 7.11 Copy / IA clarifiers (no route moves)

| Surface | Suggested framing |
| --- | --- |
| Messages description | “Chat with hosts — and with fans you’ve connected with.” |
| Connect description | Keep “Meet fans going where you’re going.” |
| Following description | Keep “Follow ≠ email; Notify turns on updates.” |
| Requests naming | In UI, prefer **Message requests** vs **Connect requests** where both appear nearby |

### 7.12 Verdict

| Question | Answer |
| --- | --- |
| Messages ≈ Connect? | **No** — inbox vs peer graph; chat unlock bridges them |
| Connect own section? | **Yes** — Community → Connect; canonical `/connect/*` |
| Keep `/dashboard/connect` aliases? | **Yes** |
| Following = updates feed? | **No for now** — list + email Notify; optional public upcoming chips later |
| Home? | Unread messages (P1); Connect pending (P2); Following light/defer (P3) |
| Route deletes? | **None** |

---

## 8. Passport, badges, Vault, reviews audit

**Routes in scope**

| Route | File / UI | Role |
| --- | --- | --- |
| `/dashboard/passport` | `passport/page.tsx` + stamp/loyalty/vault sections | Private Fan Passport hub |
| `/dashboard/passport/settings` | `passport/settings/page.tsx` | Visibility, directory, public fields, section toggles |
| `/dashboard/badges` | `badges/page.tsx` | Full badge catalog + earned progress |
| `/dashboard/vault` | `vault/page.tsx` + `BuyerVaultLibraryCard` | Fan Vault library |
| `/dashboard/vault/[itemId]` | `vault/[itemId]/page.tsx` | Unlocked item detail (body only if accessible) |
| `/dashboard/vault/subscriptions` | `vault/subscriptions/page.tsx` | Cancel / archive / restore subscriptions |
| `/dashboard/reviews` | `reviews/page.tsx` | Create / edit / withdraw verified event reviews |

**Sidebar (§3):** Identity → Passport, Badges, Vault, Reviews (all **stay**). Settings / subscriptions / item detail stay deep-linked.

**Docs of record:** [FAN_PASSPORT.md](./FAN_PASSPORT.md) · [VAULT.md](./VAULT.md).

### 8.1 Passport — identity & profile readiness

#### `/dashboard/passport` today

| Block | Content |
| --- | --- |
| Hero | Display name, `@username` or “Set a username”, visibility, Superfan badge, **completion_score %**, public share link when not private |
| Stats | Events attended, hosts followed, badges, reviews, Vault unlocks, VIP nights, cities, tickets bought |
| Stamps | `PassportStampGrid` + `MerchProofSection` → Badges |
| Host loyalty | Per-host check-ins / tickets / Following badge |
| Vault access summary | Paid / pending unlock counts + unlocked titles → Vault library |
| Attended / upcoming | Checked-in attendance (refunds don’t count); upcoming tickets |
| CTAs | Passport settings, Badges, Tickets, Find events |

**Identity readiness checklist (implied by product)**

| Ready signal | Today |
| --- | --- |
| Username set | Shown; empty nudges settings |
| Display name | From passport |
| Visibility chosen | Shown as raw enum string (`private` / `unlisted` / `public`) |
| Completion score | Badge `% complete` |
| Directory opt-in | **Not** summarized on hub — only in settings |
| Avatar / tagline / bio | Settings only |

**Gap:** Hub shows technical `Visibility: private` rather than plain-language privacy status; no single “Profile readiness” strip (username + public/private + directory).

#### `/dashboard/passport/settings` — public / private controls

| Control | Behavior |
| --- | --- |
| Profile visibility | Private (only you) · Unlisted (link) · Public (shareable) |
| Directory | `appear_in_directory` — requires Public; never lists private/unlisted |
| Public fields | Username, display name, avatar, tagline, bio |
| Section toggles | Attended events, badges, followed hosts, reviews, Vault unlock **titles**, city/category stats |
| Always hide private events | `hide_private_events_always` — recommended on |
| Defaults copy | “Private by default. Public directory listing is opt-in only.” |

**Strengths:** Aligns with FAN_PASSPORT.md; directory ≠ Connect; unsaved-changes guard.  
**Gaps:** Long toggle list without a one-line “Who can see what” summary; Connect privacy lives separately under `/connect/settings` (correct separation, easy to confuse).

### 8.2 Badges — progress

| Aspect | Today |
| --- | --- |
| Data | `fetchMyBadges` — catalog with `earned` / `awarded_at` |
| UI | Progress card (`earned / total` + bar); grid of earned vs locked cards |
| Rules copy | “Deterministic from tickets and check-ins” |
| Linkage | Passport stamps + sidebar Badges; Back to Passport |
| Empty | “No badges in catalog yet” |

**Gap vs home:** Passport hub already has badge count; Personal Command Center still shows fake Passport metric `Open` (§2) — should use completion or badges earned / next stamp.

### 8.3 Vault — unlocked items & subscriptions

#### `/dashboard/vault` library

| Aspect | Today |
| --- | --- |
| Access model | Server re-checks; locked bodies never for inaccessible items |
| Sections | Unlocked · Followed-host drops · Ticket-holder · Unlockable · Activity / purchases |
| Stats | Unlocked, followed, ticket-holder, may unlock, paid unlocks |
| Post-purchase | `?purchase=` polls webhook confirmation (correct — no FE mint) |
| Empty | Strong CTAs → hosts / following |
| Cross-links | Subscriptions, Following, Find hosts |

#### `/dashboard/vault/[itemId]`

| Aspect | Today |
| --- | --- |
| Content | Title/media/body only when found in accessible items |
| Empty / locked | Empty state if no access — does not leak locked body |
| Public link | Optional `/@{host}/vault/{slug}` |

#### `/dashboard/vault/subscriptions`

| Aspect | Today |
| --- | --- |
| Lifecycle | Cancel, archive, restore (+ include archived filter) |
| UI | `DataTable` + `ConfirmAction` |
| Nav | Off sidebar — linked from Vault library |
| Host overlap | Host `/host/vault/subscriptions` = subscriber list (different data) |

**Gaps:** Subscriptions easy to miss; no Command Center unlock summary today; Passport hub already lists unlock titles (good internal consistency).

### 8.4 Reviews — verified attendance

| Aspect | Today |
| --- | --- |
| Eligibility | Checked-in tickets only; `fetchReviewEligibility` per ticket |
| CRUD | Submit, edit, withdraw; edit can restore withdrawn |
| Host rule | Copy: hosts **cannot** delete fan reviews (product invariant) |
| Public | Verified reviews appear on host Legacy Page (privacy-safe) |
| Empty | Explains check-in + event ended |
| Prompts | **None** outside this page — no post-check-in CTA from tickets/home/Alerts |

**Gap:** Biggest identity/commerce bridge miss — attended fans must discover Reviews in Identity nav.

### 8.5 Privacy controls (cross-cutting)

| Concern | Where controlled | Rule |
| --- | --- | --- |
| Passport visibility | Passport settings | private / unlisted / public |
| `/fans` directory | `appear_in_directory` + public | Opt-in only |
| What public Passport shows | Section toggles | Titles/stats only where allowed |
| Private / secret events | `hide_private_events_always` | Keep off public views |
| Vault on public Passport | `show_vault_unlocks` | **Titles only** — never locked content |
| Reviews on public Passport | `show_reviews` | Verified, no private event details |
| Fan Connect | `/connect/settings` | Separate opt-in (off by default) |
| Account name/theme | `/dashboard/settings` | Not the public Passport profile |

**Never expose (public):** email, phone, orders/payments, private venues, locked Vault bodies — enforced in public serializers (docs); FE settings copy should keep saying so plainly.

### 8.6 What should appear on Personal Command Center (`/dashboard`)

| Section | Priority | Content | Source |
| --- | --- | --- | --- |
| **Passport progress card** | **P2** | Completion % or stamps; next badge hint; visibility plain language (“Private” / “Public on /fans”) | `fetchMyPassport` / badges summary |
| **Vault unlock summary** | **P2** | Unlocked count + 1 recent title; link library | Vault library stats or passport `vault_summary` |
| **Review prompts** | **P1–P2** | “Review {event}” after checked-in + eligible | Eligibility API / attended without review |
| Quick action Passport | P0 row | Always | `/dashboard/passport` |

Hide empty Vault/review strips. Do not dump full stamp grid or Vault library on home.

### 8.7 Recommended improvements

| Improvement | Priority | Detail |
| --- | --- | --- |
| **Passport progress card on `/dashboard`** | **P2** | Replace static `Open` metric; show completion / badges / “Set username” readiness |
| **Vault unlock summary on home** | **P2** | Compact count + Open library; hide if zero |
| **Review prompts after attended events** | **P1** | Ticket detail + Alerts + home strip when eligible; deep link `/dashboard/reviews` with ticket preselected if added later |
| **Clearer privacy language** | **P1** | Hub: plain “Only you can see this” / “Shareable link” / “Listed on Fan Directory”; settings: short “Who can see what” summary above toggles |
| Identity readiness strip on Passport hub | P2 | Username · visibility · directory · completion |
| Badges “next badge” hint | P2 | One locked badge with progress copy on Passport + home |
| Vault subscriptions discoverability | P2 | Keep off-nav; pin under Vault page actions (already) + optional Account deep link |
| Cross-link Connect privacy | P3 | From Passport settings: “Peer discovery is Fan Connect (separate)” |
| Prefill review form `?ticket_id=` | P2 | From prompt CTAs |

### 8.8 Keep separate vs nest Badges

| Option | Verdict |
| --- | --- |
| Badges stay Identity sidebar peer | **Keep** (§3) — catalog is browsable |
| Badges only under Passport | Rejected for nav — keep URL `/dashboard/badges`; Passport remains hub with stamp embed |

### 8.9 Map current → target

| Surface | Today | Target |
| --- | --- | --- |
| `/dashboard` Passport card | Value `Open` | Progress + privacy one-liner |
| Passport hub | Rich private dashboard | + readiness strip + plain visibility |
| Badges | Full catalog | + next-badge on hub/home |
| Vault | Strong library | + home unlock summary |
| Reviews | Self-serve page only | + post-attendance prompts |
| Privacy copy | Good in settings; raw on hub | Plain language everywhere |

### 8.10 Verdict

| Question | Answer |
| --- | --- |
| Identity/profile readiness? | **Partial** — completion score exists; username/directory not summarized on hub/home |
| Public/private controls? | **Strong** in settings; hub language needs plain words |
| Vault unlocks + subscriptions? | **Substantial** library; subscriptions lifecycle OK; home summary missing |
| Verified reviews? | **Solid** CRUD; **weak** prompting after check-in |
| Badge progress? | **Good** on Badges page; underused on Command Center |
| Route changes? | **None** — stay; nest only via UX (prompts, cards), not URL moves |

---

## 9. Ambassador buyer-side audit

**Product invariant ([AMBASSADORS.md](./AMBASSADORS.md)):** Ambassador = promoter/referrer. **Never** grants Host workspace, scanner, merch desk, attendee lists, or buyer PII. Host Team ≠ Ambassadors.

**Routes in scope (Personal)**

| Route | File | Role |
| --- | --- | --- |
| `/dashboard/ambassador` | `ambassador/page.tsx` | Overview — promotions + earnings snapshot |
| `/dashboard/ambassador/events` | `…/events/page.tsx` | My active campaign enrollments (“Campaigns” in subnav) |
| `/dashboard/ambassador/links` | `…/links/page.tsx` | Codes, links, share cards, copy |
| `/dashboard/ambassador/earnings` | `…/earnings/page.tsx` | Earnings waterfall + confirmed sales ledger |
| `/dashboard/ambassador/leaderboard` | `…/leaderboard/page.tsx` | **Own** campaigns ranked (not global) |
| `/dashboard/ambassador/payouts` | `…/payouts/page.tsx` | Payout/reward status snapshot |

**Chrome:** Personal shell + `AmbassadorDashNav` (Overview · Campaigns · Links & QR · Earnings · Leaderboard · Payouts).  
**Sidebar (§3):** Growth → **Ambassadors** → `/dashboard/ambassador` (plural label, singular path — **stay** URL for now).  
**Public join funnel (outside `/dashboard`):** `/ambassadors`, `/ambassadors/events`, `/ambassadors/how-it-works` — “Promote this event” → Personal dashboard after join.

### 9.1 How an ambassador sees campaigns

| Surface | What they see |
| --- | --- |
| Overview | `enrollments_active`, aggregate clicks, ticket/merch sales; links to earnings/links/payouts; CTA **Find events to promote** → `/ambassadors/events` |
| Campaigns (`/events`) | Active enrollments only (`ambassador.status === "active"`); per campaign: title, `?ref=` code badge, Open vs Host partner, clicks/tickets/merch/revenue/est. earnings, Open event page with ref |
| Discovery | Not inside dashboard — browse eligible events on public Ambassadors pages |
| Empty | “No events yet” → Browse eligible events |

**Program kinds shown:** Open event Ambassadors vs host partner badge. Campaign types include tickets vs merch (`event_merch` affects link builder).

### 9.2 Referral link / code visibility

| Aspect | Today |
| --- | --- |
| Uniqueness | Unique code **per campaign** (copy on Links page) |
| Display | `referral_code_display` or formatted code; Campaigns page shows `?ref={code}` badge |
| Links | `buildAmbassadorEventLink(slug, code, { merch })`; merch campaigns also show event-page link |
| Actions | Copy link, copy code, `AmbassadorShareCard` (share/QR affordances) |
| Attribution copy | “Referral cookies last 30 days (last click wins)” |
| Checkout | Explicit code at checkout can win over cookie (product rule — not re-shown on every dash page) |

**Clarity:** Strong on Links page. Campaigns page surfaces code but primary share UX is Links & QR.

### 9.3 Earnings clarity

| Bucket | Meaning (FE copy) |
| --- | --- |
| Estimated | From confirmed paid sales (may use domain `pending_amount` when available) |
| Approved | Past payout review |
| Payable | Ready for payout/reward |
| Paid | Already paid out |

| Strength | Gap |
| --- | --- |
| Four-step waterfall on Overview + Earnings | Dual sources (`fetchAmbassadorEarningsSummary` + optional `fetchDomainEarnings`) — cutover complexity |
| Confirmed sales list (event, ticket/merch qty, revenue, commission, status, date) | Sale `status` shown raw — could use buyer-safe labels |
| “Only after verified payment” messaging | Good — aligns with webhook invariant |

### 9.4 Payout / reward status

| Aspect | Today |
| --- | --- |
| Status | `payout_status` badge + `payout_status_label` prose |
| Amounts | Payable now · Approved · Paid out |
| History | **Placeholder** — “No Ambassador payouts have been issued yet… when payouts are enabled…” |
| Rails | Copy: payout rails rolling out; estimated balances update from confirmed sales |

**Verdict:** Status snapshot is useful; history/rails still immature — set expectations on home (“Payable ₦X · payouts rolling out”) rather than over-promising.

### 9.5 Leaderboard

| Aspect | Today |
| --- | --- |
| Scope | **Personal only** — ranks the user’s own enrollments by revenue, then clicks |
| Columns | Rank, campaign/event, clicks, sales, conversion %, revenue, est. earnings |
| Copy | Explicitly: hosts see the **full public** campaign leaderboard on host tools |
| Empty | “No campaigns yet” |

**Do not confuse** with Host `/host/ambassadors/campaigns/[id]` public leaderboard among all promoters.

### 9.6 Privacy boundaries

| Rule | Buyer Ambassadors dashboard |
| --- | --- |
| See own codes, links, clicks, aggregate sales, commission | **Yes** |
| See buyer PII, emails, phones, payment refs, order IDs | **No** (allowlisted sale rows — AMBASSADORS.md / privacy tests) |
| See attendee lists, ticket/merch QRs, shipping, Fan Connect graph | **No** |
| Gain Host workspace / desk / team | **Never** |
| Host sees ambassador as participant + conversions (no buyer private data on host DTOs) | Separate `/host/ambassadors*` |

FE should keep avoiding any “who bought” identity fields if APIs ever expand.

### 9.7 Relationship with Host Ambassadors pages

| Personal (`/dashboard/ambassador*`) | Host (`/host/ambassadors*`) |
| --- | --- |
| Join / promote / share / track **my** earnings | Create campaigns, manage participants, conversions ledger, approve rewards |
| My links & codes | Campaign analytics across ambassadors |
| My payout/reward **status** as earner | Host payout summary / mark paid (host-owned) |
| Personal campaign ranking | Event/campaign leaderboard among promoters |
| Same product word **Ambassadors** | Disambiguated by Personal vs Host chrome |

**Never merge** these trees. Dual-role users switch via WorkspaceSwitcher.

### 9.8 What should appear on `/dashboard` home

| Section | Priority | When to show | Content |
| --- | --- | --- | --- |
| **Ambassador strip** | **P2** | `enrollments_active > 0` (or payable/estimated > 0) | Active promotions count · Estimated/Payable ₦ · CTA **Copy links** → `/dashboard/ambassador/links` · secondary Overview |
| Quick action Ambassadors | **P2** | Same condition (or always if ever enrolled) | `/dashboard/ambassador` |
| Non-ambassadors | — | Never enrolled | **Hide** strip; discovery stays on `/ambassadors` / event Promote CTA — do not push Growth on every fan |

Aligns with §2 (conditional Earn section).

### 9.9 Stronger shortcut for active ambassadors?

| Option | Verdict |
| --- | --- |
| **Conditional home strip + quick action** | **Recommended** — strongest shortcut without cluttering non-promoters |
| Always-visible sidebar Ambassadors | **Keep** (already) — fine for discoverability of the program |
| Hide Growth group until first enrollment | Optional later — may bury “how do I promote?”; public `/ambassadors` already recruits |
| Mobile bottom nav Ambassadors | **No** — keep bottom nav to Home/Alerts/Messages/Events |
| SiteHeader Ambassadors | Public marketing nav already points at Ambassadors program — OK; Personal shortcut is home/sidebar |

### 9.10 Is “Growth” the right sidebar group?

| Option | Verdict |
| --- | --- |
| **Growth** (current) | Acceptable — matches Host Grow cluster linguistically; a bit vague for earners |
| **Earn** | **Preferred rename** — clearer job (promote → earn); pairs with Personal Command Center §2 “Earn” |
| Move under Activity | Rejected — not wallet/tickets |
| Move under Account | Rejected — not settings |

**Recommendation:** Rename sidebar group **Growth → Earn**; keep item label **Ambassadors**. No route change. Host sidebar can keep **Grow** (different mode).

### 9.11 Recommended improvements

| Improvement | Priority | Detail |
| --- | --- | --- |
| Conditional Command Center ambassador strip | P2 | Active enrollments / payable snapshot + Copy links |
| Sidebar group Earn | P2 | Rename Growth → Earn (§3 update when implementing) |
| Plain earnings labels on sales rows | P2 | Map raw `sale.status` to buyer-safe words |
| Payout history when rails ship | P1 (later) | Replace placeholder; keep immutable evidence rules on host/admin side |
| Clarify leaderboard title | P3 | “Your campaigns” vs implying global rank |
| Path pluralization `/dashboard/ambassadors` | Later | Optional redirect; label already plural |
| Empty Overview for never-enrolled | P2 | Friendlier “Become an Ambassador” → `/ambassadors/events` (not only error/skeleton) |

### 9.12 Verdict

| Question | Answer |
| --- | --- |
| Campaign visibility? | **Clear** for active enrollments; join funnel is public `/ambassadors*` |
| Links/codes? | **Strong** on Links & QR |
| Earnings? | **Clear waterfall**; sales ledger OK; dual API cutover is the main smell |
| Payouts? | **Status OK**; history/rails still placeholder |
| Leaderboard? | **Personal campaign rank only** — keep copy explicit |
| Privacy vs Host? | **Well bounded** in product docs — keep FE sparse |
| Home shortcut? | **Yes, conditional** for active ambassadors |
| Growth group? | Rename to **Earn**; keep Ambassadors item |
| Route deletes? | **None** |

---

## 10. Workspace switcher and top nav audit

**Buyer-side focus:** Behavior while on Personal surfaces (`/dashboard/*`, `/connect/*`) and how global chrome treats Personal vs Host.  
**Sources:** `WorkspaceSwitcher.tsx`, `SiteHeader.tsx`, `CreateEventCta.tsx`, `NotificationBell.tsx`, `DashboardTopbar.tsx`, `DashboardSidebar.tsx`, `MobileBottomNav.tsx`, `dashboard/layout.tsx`, `host-access.ts` (`PERSONAL_WORKSPACE_TITLE`, `hostWorkspaceChromeTitle`).

**Option A reminder:** Unified shell; private Host tools live in the switcher — not as a peer SiteHeader product link. Public **Hosts** marketplace stays.

### 10.1 Workspace switcher (Personal shell)

| Aspect | Behavior today |
| --- | --- |
| Mount | Personal layout toolbar: `WorkspaceShell` → `toolbar={<WorkspaceSwitcher />}` (sidebar desktop + top strip mobile) |
| Label | Field label **Workspace** |
| Personal option | **Personal account** (`value=personal`) → `writeWorkspaceMode("personal")` + `router.push("/dashboard")` |
| Host options | **`Host: {display_name}`** via `workspaceOptionLabel` → `hostWorkspaceChromeTitle`; suffix ` (Owner)` or ` · {role_label}` |
| Landing on Host | `hostHomePathForWorkspace(match)` — role-aware (not hardcoded `/host/events`) |
| Persist | `setActiveHostId` + `POST /me/active-workspace` + local mode |
| Zero workspaces | Select still shows **Personal account**; below: **Become a host** → `/host/onboarding` |
| Selected value on Personal routes | Always **Personal account** when not on `/host/*` |
| Loading | Skeleton placeholder — switcher does **not** disappear when `workspaces.length === 0` |

**Shell title beside switcher:** Sidebar/topbar title **Personal** (`PERSONAL_WORKSPACE_TITLE`) — not “Buyer”.

### 10.2 Site header — top nav (buyer-relevant)

| Item | href | Buyer-side role |
| --- | --- | --- |
| Events | `/events` | Public discovery |
| Ambassadors | `/ambassadors` | Public Ambassadors program |
| **Hosts** | `/hosts` | **Public marketplace** — discover hosts / Legacy |
| Fans | `/fans` | Public Fan Passport directory |
| Sponsors | `/sponsors` | Public |
| **Dashboard** (logged in) | `/dashboard` | Personal entry; active for `/dashboard/*` **and** `/connect/*` |
| Support / Admin | role-gated | Separate shells — not switcher options |

**Explicitly absent from SiteHeader:** private **Host** workspace link (e.g. `/host` or `/host/events`). Comment in code: *“Private Host tools live in WorkspaceSwitcher — not here.”*

### 10.3 Public Hosts vs private Host — duplication check

| Link | Destination | Product meaning | Duplicates private Host? |
| --- | --- | --- | --- |
| SiteHeader **Hosts** | `/hosts` | Marketplace / discovery | **No** |
| Switcher **Host: {name}** | Role-aware `/host…` | Private Host workspace | Canonical private entry |
| Become a host | `/host/onboarding` | First-time host signup | Growth path — not a second Host nav peer |

**Confirmed:** Private Host is **not** duplicated as a peer top-nav product link. Public **Hosts** remains.

### 10.4 Create event CTA

| Aspect | Behavior |
| --- | --- |
| Placement | SiteHeader (desktop when logged in; always in mobile drawer; guests see CTA too) |
| Zero workspaces / guest | → `/host/onboarding` |
| Can create on a workspace | → `/host/events/new` + sets active host |
| Staff without create | Hidden (`status: "hidden"`) |
| Intent | Growth entry — **not** a workspace switcher substitute |

**Buyer impact:** Personal-only users still see **Create event**, which sends them to onboarding — aligned with Become a host, but can feel host-pushy on Personal surfaces. Acceptable for growth; do not treat as private Host nav duplication.

### 10.5 Notifications

| Surface | Behavior |
| --- | --- |
| Header bell | `NotificationBell` → `/dashboard/notifications` (account Alerts inbox) |
| Unread | Realtime + HTTP; badge on bell |
| Sidebar | **Alerts** with `badge: "notifications"` |
| Mobile bottom nav | Alerts with unread badge |
| Prefs | `/dashboard/settings/notifications` (canonical; host settings 308 here) |

Account-level alerts correctly live under Personal even when the user also hosts.

### 10.6 Mobile chrome (buyer)

| Piece | Behavior |
| --- | --- |
| SiteHeader hamburger | Same links as desktop (public + Personal); Create event; theme; login |
| Workspace topbar (`md:hidden`) | Switcher strip + **Menu** opens drawer with **grouped `buyerNav`** (same as desktop sidebar); title **Personal** |
| Mobile bottom nav | Home · Alerts · Messages · Events — Personal surfaces only; hidden on `/host` |
| Connect | Uses Personal shell → same switcher + drawer pattern |

### 10.7 Confirmation checklist

| Requirement | Status | Evidence |
| --- | --- | --- |
| **Personal account is clear** | **Yes** | Switcher option **Personal account**; shell title **Personal**; mode write `"personal"` |
| **Switching to Host uses Host: {name}** | **Yes** | `hostWorkspaceChromeTitle` → `Host: ${displayName}` (+ Owner/role suffix) |
| **Buyer-only users see Become a host** | **Yes** | Shown when `workspaces.length === 0` under switcher |
| **Private Host link is not duplicated** | **Yes** | No SiteHeader Host → `/host`; private entry is switcher only |
| **Public Hosts marketplace remains** | **Yes** | `publicNav` includes Hosts → `/hosts` |

### 10.8 Remaining friction (buyer chrome)

| Issue | Severity | Note |
| --- | --- | --- |
| SiteHeader label **Dashboard** vs shell **Personal** | Done | Renamed to **Personal** → `/dashboard` (Phase 2) |
| Create event always visible for personal-only | Low | Growth CTA; overlaps Become a host psychologically |
| Dashboard nav active on `/connect` | OK | Correct — Connect is Personal mode |
| Dual mobile menus (SiteHeader + workspace Menu) | Low | Different jobs (marketing vs workspace nav); acceptable |

### 10.9 Recommendations (chrome only — no route deletes)

| Change | Priority | Detail |
| --- | --- | --- |
| Rename SiteHeader **Dashboard** → **Personal** (or Workspace) | Done | Href stays `/dashboard` this phase |
| Keep Hosts marketplace + switcher Host: {name} split | P0 | Already correct — do not re-add private Host peer link |
| Keep Become a host for zero-workspace users | P0 | Already correct |
| Optional: soften Create event on Personal-only | P3 | e.g. label “Host an event” or rely on Become a host — product choice |

### 10.10 Verdict

Buyer-side chrome **matches Option A** for switching: Personal account ↔ Host: {name}, Become a host for non-hosts, public Hosts kept, private Host not duplicated in top nav. SiteHeader workspace entry is **Personal** → `/dashboard`.

---

## 11. Proposed `/dashboard` Personal Command Center

**Canonical route:** `/dashboard` (no second home).  
**Product name:** Personal Command Center (§2, §4).  
**Principle:** Actionable and scannable — compose signals from existing `/dashboard/*` pages. **Hide empty optional sections.** Not a 14-tile nav dump. Parallel to Host Command Center at `/host`, never mixed data.

**Chrome vs page body**

| Concern | Where it lives |
| --- | --- |
| Workspace switcher | **Shell only** (`WorkspaceSwitcher` in sidebar / mobile topbar) — do **not** duplicate in page header |
| Sidebar title **Personal** | Shell |
| Page header | `DashboardShell` eyebrow/title/description + optional account status line |
| SiteHeader Dashboard → Personal | Global chrome (§10) — separate from this page |

### 11.1 Final section order

```
[Shell: Personal + WorkspaceSwitcher]
┌─────────────────────────────────────────────┐
│ 1. Header — Personal Command Center         │
│ 2. Next up                         (P0)     │
│ 3. My activity                     (P0–P1)  │
│ 4. Messages and community          (P1–P2)  │
│ 5. Identity                        (P2)     │
│ 6. Vault                           (P2)     │
│ 7. Ambassador summary              (P2)*    │
│ 8. Quick actions                   (P0)     │
└─────────────────────────────────────────────┘
* Hide unless active enrollments / earnings signal
```

On mobile: Header → Next up → Quick actions → My activity → then 4–7. Promote Quick actions above the fold after Next up so primary CTAs are reachable without scroll.

### 11.2 Section specs

#### 1. Header

| Element | Content |
| --- | --- |
| Eyebrow | **Personal** or **Personal Command Center** |
| Title | `Hello, {full_name}` |
| Supporting line | One sentence: next-action oriented (e.g. “Your next ticket, pickups, and messages — in one place.”) — not a feature laundry list |
| Account status | Plain privacy/account cue: e.g. email (optional) · Passport visibility one-liner (“Private” / “Public on /fans”) — **no raw roles list** |
| Workspace switcher | **Not in page** — already in shell (§10) |
| Primary CTA (optional) | Browse events — or omit if Quick actions includes it |

**Remove from today’s home:** Account card with Roles + Support/Admin CTAs; Host workspace as peer hero (§2.6).

#### 2. Next up (P0 — hero)

| Row | Show when | Content | Primary CTA |
| --- | --- | --- | --- |
| Next ticket / event | Upcoming active ticket exists | Event title, date/time, venue/city if safe, ticket type | **Open QR** (modal) · Full pass → ticket detail |
| QR shortcut | Event starts within ~48h (or “today”) and ticket `showQr` | Emphasize Open QR; offline badge if cached | Same |
| Merch pickup reminder | Any `ready_for_pickup` (or cart with lines) | Product + event · “Ready for pickup” | Open pickup QR / Merch · Resume cart if cart only |
| Empty | No upcoming ticket and no pickup/cart | “No upcoming tickets” + Browse events | Browse events |

**Do not:** lifetime ticket counts; full wallet; transfer/cancel controls.

**Data:** `fetchMyTickets` (upcoming bucket §5) · `fetchMyMerch` / cart · reuse pass-card / QR modal patterns.

#### 3. My activity (P0–P1)

Compact link row or four attention chips — not four giant metric cards of lifetime totals.

| Chip | Default value | Prefer attention signal | Href |
| --- | --- | --- | --- |
| Tickets | Upcoming count | “N ready for entry” | `/dashboard/tickets` |
| Orders | Recent / pending payment count | “Payment pending” if any | `/dashboard/orders` |
| Merch | Ready + in-progress counts | “N ready for pickup” | `/dashboard/merchandise` |
| Refunds | Open request count | Hide chip if zero open | `/dashboard/refunds` |

Optional fifth: **Cart** only if lines > 0 → `/dashboard/cart`.

#### 4. Messages and community (P1–P2)

| Row | Show when | Content | CTA |
| --- | --- | --- | --- |
| Unread messages | Always compact; emphasize if count > 0 | Unread count | Open Messages |
| Fan Connect | Connect enabled or pending > 0 | Pending requests (and optional suggestions count) | `/connect/requests` or `/connect` |
| Following | Has follows; updates only if safe public signal exists | “Following N hosts” · optional 1 upcoming public event | `/dashboard/following` |
| Hide whole section? | Never entirely if Messages exists — Messages row stays | Connect / Following rows hide when empty | — |

**Privacy:** Connect row never shows peer PII beyond counts; Following never shows private venues (§7).

#### 5. Identity (P2)

| Row | Content | CTA |
| --- | --- | --- |
| Passport progress | Completion % or stamps · plain visibility | Open Passport |
| Badges | Earned / total or “Next: {badge}” | `/dashboard/badges` |
| Reviews prompt | Only if eligible checked-in event without review | Write review → `/dashboard/reviews` (+ `?ticket_id=` later) |

Hide reviews row when nothing to prompt. Replace today’s Passport value **`Open`**.

#### 6. Vault (P2)

| Row | Show when | Content | CTA |
| --- | --- | --- | --- |
| Recent unlocks | `unlocked_count > 0` or recent titles | Count + up to 2 titles | Open Vault library |
| Subscriptions | Active subscription count > 0 | “N active” | `/dashboard/vault/subscriptions` |
| Empty | No unlocks and no subs | **Hide section** (or single line “No Vault unlocks yet” linking hosts) | — |

Never preview locked bodies.

#### 7. Ambassador summary (P2 — conditional)

| Show when | `enrollments_active > 0` OR payable/estimated > 0 |
| --- | --- |
| Content | Active campaigns · clicks · sales · Estimated/Payable ₦ · `payout_status_label` short |
| CTAs | **Copy link** → `/dashboard/ambassador/links` · Overview → `/dashboard/ambassador` |
| Hide when | Never enrolled / inactive — discovery stays on `/ambassadors` and Promote CTAs (§9) |

#### 8. Quick actions (P0)

Short button row — max ~6 visible; conditional items last.

| Action | Target | Who |
| --- | --- | --- |
| Browse events | `/events` | Everyone |
| View tickets | `/dashboard/tickets` | Everyone |
| Open messages | `/dashboard/messages` | Everyone |
| Open Passport | `/dashboard/passport` | Everyone |
| Promote an event | `/ambassadors/events` | Everyone (recruit) **or** only if Ambassadors program relevant |
| Become a host | `/host/onboarding` | Zero host workspaces |
| Switch to Host | Rely on **shell switcher**; optional secondary “Open Host: {name}” if dual-role | Dual-role only |

**Do not** put Support / Admin here.

### 11.3 Layout wireframe (desktop)

```
Personal Command Center          [Browse events]
Hello, Ada
Private Passport · ada@…

┌─ Next up ──────────────────────────────────┐
│  DJ Maze Night · Sat 8pm · GA              │
│  [Open QR]  [Ticket details]               │
│  Merch: Hoodie ready for pickup [Open]     │
└────────────────────────────────────────────┘

My activity
[ Tickets 2 ] [ Orders 1 ] [ Merch 1 ready ] [ Refunds — ]

Messages and community
Unread 3 · Connect 1 request · Following 4 hosts

Identity          Vault              Ambassadors*
62% · 3 badges    2 unlocks          1 campaign · ₦…
[Passport]        [Library]          [Copy link]

Quick actions
Browse events · Tickets · Messages · Passport · Promote · Become a host
```

### 11.4 Empty / first-run state

When the user has no tickets, orders, merch, messages, or unlocks:

1. Header greeting  
2. Next up empty → Browse events  
3. Quick actions (full)  
4. Soft Identity nudge (“Set up Fan Passport”) if username missing  
5. Hide Vault, Ambassador, review prompt, refunds  

Avoid a wall of zeroed StatCards.

### 11.5 Loading & performance

| Rule | Detail |
| --- | --- |
| P0 first | Header skeleton → Next up (tickets + merch attention) → Quick actions |
| Deferred | Connect pending, Passport, Vault, Ambassador — progressive sections OK |
| Reuse | Existing fetchers; ticket/merch offline cache for Next up when offline |
| Cap | No N+1 per-ticket QR fetch on home — Open QR opens modal that loads one ticket |

### 11.6 Map from current `/dashboard` page

| Current | Proposed |
| --- | --- |
| Eyebrow Personal + Hello | **Keep** — add Command Center framing |
| Browse events header CTA | Keep or move into Quick actions |
| Tickets / Orders counts + Passport `Open` | **Replace** with Next up + My activity + Identity progress |
| Account card (email, roles, Host/Support/Admin) | **Remove** — status line lite; Host via switcher / conditional quick action |
| Alerts footnote | **Remove** — Alerts in sidebar/bell |

### 11.7 Success criteria (home)

A fan answers in under two seconds:

1. What is **next** (ticket / pickup)?  
2. Anything **urgent** (unread, refund, Connect request, cart)?  
3. Where for wallet vs identity vs earn? → section CTAs / Quick actions  

### 11.8 Implementation phases

Phase 3 home remodel is **shipped** — see §14 Phase 3. Phases 4–7 remain future work.

| Phase | Ship | Status |
| --- | --- | --- |
| **H1** | Header cleanup + Next up + Quick actions + My activity chips | **Shipped** |
| **H2** | Messages unread + review prompts + Passport progress (replace `Open`) | **Shipped** |
| **H3** | Vault summary + conditional Ambassador strip + Connect pending | **Shipped** |
| **H4** | Polish empty states, deferred loading, offline next-pass | Empty + deferred **shipped**; offline next-pass → Phase 4+ |

Routes stay. Sidebar stays (§3). Naming: Personal / Personal Command Center (§4). Privacy §12 smoke-locked.

### 11.9 Verdict

**Shipped:** `/dashboard` is the Personal Command Center (Phase 3). Workspace switcher remains shell chrome. Sections hide when empty. Tickets stay the hero job; commerce, community, identity, Vault, and Ambassadors are summary strips with deep links — never full feature dumps. Deep wallet polish remains Phases 4–6.

---

## 12. Privacy and safety boundaries

**Invariant:** `/dashboard/*` (and Personal-shell `/connect/*`) is **account-scoped self-service** only. Host ops, finance, desk, team, and admin live in other shells. APIs remain source of truth; the FE must never present forbidden surfaces or render forbidden fields even if a buggy response includes them.

**Related:** [PRIVACY.md](./PRIVACY.md) · [MESSAGING.md](./MESSAGING.md) · [FAN_CONNECT.md](./FAN_CONNECT.md) · [AMBASSADORS.md](./AMBASSADORS.md) · [SECURITY.md](./SECURITY.md).

### 12.1 Must not show (Personal / buyer dashboard)

| Forbidden | Why | Belongs instead |
| --- | --- | --- |
| **Host private financial data** | Balances, payouts, bank accounts, host revenue, settlement ledgers | `/host/payouts`, finance APIs, admin finance |
| **Host team management tools** | Invite/remove staff, roles, permissions, audit of team | `/host/team*` |
| **Host attendee lists** | Searchable guest/buyer lists for an event | `/host/events/[id]/attendees`, admin buyers |
| **Scanner tools** | Door QR scan, offline check-in buffer, desk queue ops | `/host/desk`, `/host/events/[id]/check-in*`, staff routes |
| **Hidden venue details before eligible** | Secret/private street addresses before ticket/check-in rules allow | Public event page reveals only when policy allows; never on Connect/Passport public |
| **Other users’ private Fan Connect info** | Others’ pending intros, private Passport fields, connection graph beyond safe public context | Own Connect UI only; admin Fan Connect reports (safe context) |
| **Raw QR secrets** | Ticket `qr_payload` / merch `qr_token` as plaintext, logs, copy-to-clipboard, exports | Encode in QR SVG only; copy **public_code** / pickup code (§5, §6) |
| **Raw payment provider refs** | Paystack (or other) full references, raw webhook payloads, secret keys | Host/admin finance & gateway; buyer sees order status/amounts/timeline without raw provider secrets |
| **Admin tools** | Platform admin, finance admin, CMS, audit browsers, message-report queues | `/admin/*` (role shells — not Personal nav) |

**Also never on Personal (supporting list)**

| Forbidden | Notes |
| --- | --- |
| Host merch studio / fulfillment desk | `/host/merchandise*` — buyer sees **own** pickup wallet only |
| Host Vault studio / subscriber PII lists | `/host/vault*` — buyer sees **own** library + **own** subscriptions |
| Host Ambassadors conversion ledger with buyer PII | Host tools may see ambassadors; still no buyer contact — Personal sees **own** promo metrics only (§9) |
| Support agent case queues as Personal nav | `/support` is a separate shell; optional role CTA — not buyer Activity |
| Other fans’ emails, phones, exact spend, VIP tables, locked Vault bodies | Passport/Connect/Vault public rules |

### 12.2 May show (own data only)

| Allowed | Personal surfaces | Notes |
| --- | --- | --- |
| **Own tickets** | `/dashboard/tickets*` · Command Center Next up | QR encoded, not raw secret text; offline cache display-only |
| **Own orders** | `/dashboard/orders*` | Receipt, line items, payment **status** timeline — not raw provider secrets |
| **Own merch purchases** | `/dashboard/merchandise*` · cart | Pickup QR encoded; shipping city-level as product allows — not others’ ship-to |
| **Own refunds** | `/dashboard/refunds*` | Own requests/status only |
| **Own messages** | `/dashboard/messages*` | Fan↔host per gates; fan↔fan only after Connect accept; block/report own threads |
| **Own Passport / badges / Vault / reviews** | Identity routes | Private hub full; public share only per visibility toggles; Vault body only if unlocked |
| **Own Ambassador activity** | `/dashboard/ambassador*` | Own codes, clicks, aggregate sales, earnings — **no** buyer PII of referred purchasers |
| **Own Following + marketing opt-in** | `/dashboard/following` | Hosts the user follows — not host CRM internals |
| **Own Alerts / notification prefs** | `/dashboard/notifications`, settings | Account-scoped |
| **Own Fan Connect graph** | `/connect*` | Own requests/connections/suggestions under opt-in + safe public reasons |

### 12.3 Boundary matrix (shell → data)

| Shell | Data scope |
| --- | --- |
| **Personal** `/dashboard`, `/connect` | Self: tickets, orders, merch, refunds, messages, Passport, Vault, reviews, Ambassadors-as-earner, Connect-as-peer |
| **Host** `/host` | Workspace: events, desk, merch studio, host inbox, team, host finance (permissioned) |
| **Support** `/support` | Assigned cases / refunds ops — not Personal Activity |
| **Admin** `/admin` | Platform — never mixed into `buyerNav` |

WorkspaceSwitcher may **navigate** into Host; it must not **embed** host finance/attendees/scanner inside Personal pages.

### 12.4 FE safety checklist (Personal Command Center + wallets)

| Check | Rule |
| --- | --- |
| Nav purity | `buyerNav` never links to `/host/desk`, `/host/team`, `/host/payouts`, `/admin` |
| Role CTAs | Support/Admin only as rare escape hatches — **out of** Command Center body (§2, §11) |
| QR UI | Never render or clipboard `qr_payload` / `qr_token`; copy public/pickup codes only |
| Connect cards | Safe reason chips only — no private events, hidden venues, spend, locked Vault |
| Ambassador sales rows | Allowlisted fields only — no buyer email/order/payment refs |
| Order receipt | Amounts + status OK; strip/hide raw gateway references if API ever returns them |
| Home strips | Counts and own titles only — no other users’ private activity |

### 12.5 Confirmation

| Statement | Confirmed |
| --- | --- |
| Buyer dashboard must **not** show host private financial data | **Yes** |
| … host team management tools | **Yes** |
| … host attendee lists | **Yes** |
| … scanner tools | **Yes** |
| … hidden venue details before eligible | **Yes** |
| … other users’ private Fan Connect info | **Yes** |
| … raw QR secrets | **Yes** |
| … raw payment provider refs | **Yes** |
| … admin tools | **Yes** |
| Buyer dashboard **can** show own tickets, orders, merch, refunds, messages, Passport/Vault/reviews, Ambassador activity | **Yes** |

### 12.6 Verdict

Personal `/dashboard` is a **self-data vault + Command Center**, not a host ops console. Keep Option A route split so URL prefixes reinforce the boundary: `/dashboard` = mine; `/host` = workspace; `/admin` = platform.

---

## 13. Migration / redirect plan

**Policy:** Safe handling only — **no Option B/C URL tree moves**, no mass deletes, no nesting Host under `/dashboard`. Prefer **keep** + **rename in UI only** + thin **redirect/alias** for legacy bookmarks.

**Disposition legend** (same as §1)

| Value | Meaning |
| --- | --- |
| **keep** | Canonical Personal URL — stay |
| **redirect** | Permanent (308) or defensive client replace → canonical |
| **alias** | Thin server `redirect()` kept for old links; canonical elsewhere |
| **rename in UI only** | Labels/copy/nav text change; path unchanged |

### 13.1 Specific decisions

| Question | Decision | Status today | Action |
| --- | --- | --- | --- |
| Should `/dashboard/merch` become a **308** to `/dashboard/merchandise`? | **Yes** | **Already shipped** in `frontend/next.config.ts` (`/dashboard/merch`, `/dashboard/merch/:path*` → merchandise) + client `router.replace` page | **Keep 308.** Optionally remove client-only page later once traffic is zero — not required now |
| Keep `/dashboard/connect` aliases if `/connect` is canonical? | **Yes — keep aliases** | Six server `redirect()` pages under `dashboard/connect/**` | Keep indefinitely for bookmarks/docs; optional: point `buyerNav` href at `/connect` directly (aliases remain) |
| Keep `/dashboard/settings/notifications` canonical for account notifications? | **Yes** | Canonical Personal prefs; `/host/settings/notifications` → here (**308**) | **Keep.** Do not move prefs under `/host` again |

**Also already redirected (host-side, for completeness):** `/host/dashboard` → `/host` (308). Not a Personal route.

### 13.2 Routes to keep (canonical)

All functional Personal product URLs remain. No path migration in this phase.

| Area | Keep |
| --- | --- |
| Home | `/dashboard` |
| Alerts | `/dashboard/notifications` |
| Tickets | `/dashboard/tickets`, `/dashboard/tickets/[id]`, `…/transfer` |
| Orders | `/dashboard/orders`, `/dashboard/orders/[id]` |
| Merch | `/dashboard/merchandise`, `/dashboard/merchandise/[orderItemId]` |
| Cart | `/dashboard/cart` |
| Refunds | `/dashboard/refunds`, `/dashboard/refunds/new` |
| Messages | `/dashboard/messages`, `/dashboard/messages/[threadId]`, `…/settings`, `…/notifications` |
| Workspaces bridge | `/dashboard/team`, `/dashboard/team/workspaces` |
| Following | `/dashboard/following` |
| Passport | `/dashboard/passport`, `/dashboard/passport/settings` |
| Badges | `/dashboard/badges` |
| Vault | `/dashboard/vault`, `/dashboard/vault/[itemId]`, `/dashboard/vault/subscriptions` |
| Reviews | `/dashboard/reviews` |
| Ambassadors | `/dashboard/ambassador` + subroutes (`events`, `links`, `earnings`, `leaderboard`, `payouts`) |
| Settings | `/dashboard/settings`, `/dashboard/settings/notifications` |
| Fan Connect (canonical) | `/connect`, `/connect/suggestions`, `/connect/events`, `/connect/requests`, `/connect/connections`, `/connect/settings` |

### 13.3 Routes to redirect (308 / permanent)

| From | To | Status |
| --- | --- | --- |
| `/dashboard/merch` | `/dashboard/merchandise` | **Done** (308) |
| `/dashboard/merch/:path*` | `/dashboard/merchandise/:path*` | **Done** (308) |
| `/host/settings/notifications` | `/dashboard/settings/notifications` | **Done** (308) — keeps account prefs canonical on Personal |

**Optional later (not now)**

| From | To | When |
| --- | --- | --- |
| `/dashboard/ambassador` | `/dashboard/ambassadors` | Only if plural path desired; add 308 + dual support period — **defer** |
| `/dashboard/team` | `/dashboard/workspaces` | Only if URL rename after UI “Workspaces” settles — **defer** |

Do **not** redirect `/dashboard` → anything else. Do **not** add `/dashboard/host/*`.

### 13.4 Routes to alias (thin redirects — keep)

| Alias | Canonical | Keep? |
| --- | --- | --- |
| `/dashboard/connect` | `/connect` | **Yes** |
| `/dashboard/connect/connections` | `/connect/connections` | **Yes** |
| `/dashboard/connect/requests` | `/connect/requests` | **Yes** |
| `/dashboard/connect/suggestions` | `/connect/suggestions` | **Yes** |
| `/dashboard/connect/events` | `/connect/events` | **Yes** |
| `/dashboard/connect/settings` | `/connect/settings` | **Yes** |
| Legacy public `/ambassador`, `/ambassador/earnings` (if still present) | `/dashboard/ambassador*` | Keep per FRONTEND_ROUTES — outside this tree but related |

### 13.5 Rename in UI only (no URL change)

| Current UI | Target UI | Path unchanged |
| --- | --- | --- |
| Sidebar **Team** | **Workspaces** | `/dashboard/team` |
| SiteHeader **Dashboard** | **Personal** (or workspace entry) | `/dashboard` |
| Sidebar group **Growth** | **Earn** (§9) | Ambassadors href unchanged |
| Page titles “Your teams” / eyebrow Team | Workspaces language | `/dashboard/team*` |
| Home Passport metric `Open` | Progress / privacy copy | `/dashboard` body only |
| Raw `Visibility: private` on Passport hub | Plain “Only you can see this” | `/dashboard/passport` |

### 13.6 Explicitly do not migrate

| Idea | Why reject now |
| --- | --- |
| `/dashboard` → `/personal` | High link breakage; Option A keeps prefix |
| Nest Host under `/dashboard/host` | Option B rejected |
| Delete Connect aliases or merch redirect page immediately | Breaks bookmarks; zero upside |
| Merge Tickets into Orders URL | Different jobs (§6) |
| Move account notification prefs to `/host/settings/notifications` | Inverse of shipped 308 |

### 13.7 Docs to update

| Doc | Update |
| --- | --- |
| **This file** | Source of truth for Personal IA (§1–§13) |
| [FRONTEND_ROUTES.md](./FRONTEND_ROUTES.md) | Confirm merch 308, Connect aliases, notifications canonical, Personal Command Center home job |
| [DASHBOARD_HOST_UNIFICATION_AUDIT.md](./DASHBOARD_HOST_UNIFICATION_AUDIT.md) | Fix stale **Buyer** sidebar title → **Personal**; note Phases shipped + Personal CC proposal |
| [EXECUTION_TRACKER.md](./EXECUTION_TRACKER.md) | Checklist: merch 308 done; Team→Workspaces; SiteHeader Personal; Command Center H1–H4 |
| [CRUD_MATRIX.md](./CRUD_MATRIX.md) | Paths already mostly `/dashboard/*` — note cart/refunds/notifications canonical homes |
| [MERCHANDISE.md](./MERCHANDISE.md) / [MERCH.md](./MERCH.md) | Canonical buyer URL `merchandise`; `merch` = redirect only |
| [FAN_CONNECT.md](./FAN_CONNECT.md) | Canonical `/connect/*`; `/dashboard/connect/*` = aliases |
| [MESSAGING.md](./MESSAGING.md) | Unchanged paths; home unread strip when CC ships |
| [AMBASSADORS.md](./AMBASSADORS.md) | Personal vs Host paths; optional Earn group note |
| [FAN_PASSPORT.md](./FAN_PASSPORT.md) / [VAULT.md](./VAULT.md) | No path changes; privacy language polish |
| [PRIVACY.md](./PRIVACY.md) | Point at §12 boundaries for Personal shell |
| [HOST_AREA_AUDIT.md](./HOST_AREA_AUDIT.md) | Cross-link Personal CC vs Host CC; notifications 308 |

### 13.8 Tests needed

| Test | Purpose |
| --- | --- |
| `npm run test:buyer-dashboard-nav` | Extend/assert sidebar labels (Workspaces, Earn) + hrefs still resolve |
| Redirect smoke | Assert 308: `/dashboard/merch` → merchandise; `/dashboard/merch/x` → merchandise/x; `/host/settings/notifications` → dashboard settings notifications |
| Connect alias smoke | `/dashboard/connect` and each subpath → matching `/connect*` (status redirect) |
| `npm run test:fan-connect` | Still passes with Personal shell on `/connect` |
| Nav active-state unit | `isNavItemActive` for Connect alias + `/connect` (already in `workspace.ts`) |
| Breadcrumbs | Root label **Personal** on `/dashboard` (`breadcrumbs.test.ts`) |
| Workspace switcher | Personal account → `/dashboard`; Host: {name} → `hostHomePathForWorkspace`; zero hosts → Become a host visible |
| Privacy / ambassador | Existing backend privacy tests remain green — no buyer PII on ambassador sale rows |
| Command Center (when H1 ships) | Smoke: `/dashboard` renders Next up / empty browse CTA; no `/host/desk` links in page body |
| Playwright / production smoke | Update any “Buyer dashboard” / “Attendee” copy expectations to Personal |

**Do not** require full E2E of every deep link for rename-only label changes — unit + nav smoke is enough.

### 13.9 Rollout sequence (safe)

| Step | Work | Risk |
| --- | --- | --- |
| 0 | Confirm redirects already in `next.config.ts` (merch, host notification prefs) | None — verify in CI |
| 1 | UI renames: Team→Workspaces, Growth→Earn, SiteHeader Dashboard→Personal | Low |
| 2 | Optional: `buyerNav` Connect href → `/connect` | Low |
| 3 | Personal Command Center H1–H4 (§11) | Medium (UX only) |
| 4 | Docs sync (§13.7) | None |
| 5 | Later: consider plural ambassador path / team→workspaces URL only with 308 + metrics | Higher — defer |

### 13.10 Verdict

| Item | Recommendation |
| --- | --- |
| `/dashboard/merch` | **308 keep** (already done) |
| `/dashboard/connect*` | **Alias keep**; canonical `/connect*` |
| `/dashboard/settings/notifications` | **Canonical keep**; host 308 inbound |
| Almost all `/dashboard/*` | **Keep** |
| Team / Growth / Dashboard labels | **Rename in UI only** |
| Big URL renames | **Defer** |

No route deletions in this phase. Migration is chrome + home remodel + docs/tests — not a redirect matrix rewrite.

---

## 14. Implementation roadmap

**Rules for all phases**

- Keep `/dashboard` = Personal, `/host` = Host (Option A).
- No route deletes; redirects/aliases per §13.
- Privacy boundaries §12 — never embed host ops / admin / raw QR secrets.
- Prefer small PRs; update [EXECUTION_TRACKER.md](./EXECUTION_TRACKER.md) as phases close.

```
Phase 1  Audit & docs          ✅ (this document)
Phase 2  Workspace chrome      → labels, vertical sidebar, Personal, switcher
Phase 3  Personal Command Center home
Phase 4  Tickets / Orders / Merch / Refunds pages
Phase 5  Passport / Vault / Reviews / Connect summaries
Phase 6  Buyer Ambassador summaries
Phase 7  Aliases, docs sync, smoke tests
```

### Phase 1 — Audit and docs only

| Status | **Complete** |
| --- | --- |
| Deliverable | `docs/BUYER_DASHBOARD_AUDIT.md` (§1–§14) |
| Includes | Route inventory, home audit, sidebar, naming, tickets/commerce/community/identity/ambassador audits, chrome, Command Center proposal, privacy, migration, roadmap |
| Out of scope | Code, redesign, route deletes |
| Exit criteria | Doc reviewed; product agrees Personal Command Center + Option A |

### Phase 2 — Workspace chrome

| Status | **Complete** (implemented 20 July 2026) |
| --- | --- |

**Goal:** Personal mode feels like one Pàdéyá workspace with clear Personal ↔ Host: {name} switching — before remodeling page bodies.

#### Implementation notes (shipped)

| Fact | Behavior |
| --- | --- |
| `/dashboard` | Remains **Personal** workspace (shell title `PERSONAL_WORKSPACE_TITLE`) |
| `/host` | Remains **Host: {display_name}** (`hostWorkspaceChromeTitle`) |
| SiteHeader workspace entry | **Personal** → `/dashboard` (was Dashboard); **not** last-used / not `/host` |
| Private Host top-nav | **Removed** — Host mode only via in-shell `WorkspaceSwitcher` |
| Public Hosts marketplace | **Kept** — `/hosts` |
| Personal sidebar item | **Team** → **Workspaces** (href still `/dashboard/team`) |
| Personal sidebar group | **Growth** → **Earn** (Ambassadors unchanged at `/dashboard/ambassador`) |
| Connect nav | Canonical `/connect`; `/dashboard/connect*` aliases remain |
| Host sidebar | Disambiguated labels unchanged (Merch Studio, Host Inbox, Host Team, …) |
| Breadcrumbs | e.g. Personal / Overview · Personal / Workspaces · Host: {name} / Host Team |
| Permissions | UI/chrome only — no backend permission changes; privacy smoke locked |

| Work | Detail | Refs |
| --- | --- | --- |
| Fix workspace chrome labels | SiteHeader **Dashboard** → **Personal**; sidebar **Team** → **Workspaces**; group **Growth** → **Earn**; retire any remaining Buyer/Attendee chrome strings | §3, §4, §10 |
| Sidebar vertical layout | Keep / polish Personal **vertical** grouped sidebar (`buyerNavGroups`: Home · Activity · Community · Identity · Earn · Account) in `WorkspaceShell` + mobile drawer — same structure as today, correct labels | §3 |
| Personal title | Shell + breadcrumbs stay **Personal** (`PERSONAL_WORKSPACE_TITLE`); align any stale docs/UI saying Buyer | §4, §10 |
| Switcher clarity | Confirm always-on switcher: **Personal account** · **Host: {name}**; Become a host when zero workspaces; no private Host peer in SiteHeader; public **Hosts** marketplace unchanged | §10 |
| Optional | Point Connect nav `href` at `/connect` (aliases remain) | §7, §13 |

| Exit criteria | Dual-role user can answer: Am I in Personal or Host: {name}? How do I switch? |
| Out of scope (at Phase 2) | Command Center body redesign → done in Phase 3; deep page UX (4–6) |
| Shipped | Labels/groups above; SiteHeader/Footer; breadcrumbs; switcher clarity; vertical sidebar; smokes (`test:buyer-dashboard-nav`, `test:host-command-center`, `test:workspace-privacy`); lint/build/pwa/theme verified |

### Phase 3 — Redesign `/dashboard` as Personal Command Center

| Status | **Complete** (implemented 20 July 2026) |
| --- | --- |

**Goal:** Ship §11 layout on `/dashboard` only.

#### Implementation notes (shipped)

| Fact | Behavior |
| --- | --- |
| Route | Still `/dashboard` — no move, no `/personal`, no `/dashboard/host` |
| Page | `PersonalCommandCenter` + sections under `components/personal/command-center/` |
| Header | Eyebrow **Personal Command Center**; Hello {name}; compact shell — **no** roles / Support / Admin CTAs |
| Switcher | Shell only — not remounted on home (Phase 2 chrome intact) |
| Next up | Priority: active ticket → merch pickup → cart → Browse; Open QR via `TicketQrModal`; `location_label` only |
| My activity | Attention chips; **hidden** when no signals (no zero wall) |
| Community | Unread / Connect pending / Following — **hide section** when empty |
| Identity / Vault / Ambassadors | Progressive; Vault/Ambassador hide when empty; review prompt when eligible |
| Welcome | Quiet new-user card: Browse · Set up Passport · Promote · Become a host (secondary) |
| Quick actions | Wrap row — not a feature grid; Host via sidebar switcher |
| Loading | P0 tickets/orders/merch/cart + unread hook; soft P1 refunds; deferred Passport/Vault/Ambassador/Connect/Following |
| Design | Brand tokens; compact; dark/light; `min-w-0` / no horizontal overflow |
| Privacy | §12 own-data only — smoke-locked (`test:personal-command-center`) |
| Phase 2 | Unbroken: Personal top-nav, public Hosts, switcher labels, Workspaces/Earn, role-aware host landing |

| Exit criteria | §11.7 success criteria (next / urgent / where to go) — met for home |
| Maps to | §11 H1–H4 |
| Out of scope | Full tickets/merch page rewrites (Phase 4) |
| Verify | `npm run test:personal-command-center` · unit helpers · lint/build/pwa/theme · Phase 2 smokes |

### Phase 4 — Improve Tickets, Orders, Merch, Refunds pages

**Goal:** Wallet/receipt UX matches Command Center deep links.

| Area | Improvements | Refs |
| --- | --- | --- |
| Tickets | Next-pass hero on list; QR modal polish; `showQr` gating on detail; Transfer in actions menu; refund link; empty copy; cache purge on logout | §5 |
| Orders | Attention sorting; receipt → tickets/merch/refund; buyer-safe payment timeline; no raw provider refs | §6, §12 |
| Merch | Shipping detail richness; QR gating alignment; cart empty CTA; offline hygiene | §6 |
| Refunds | Prefill `?order_id=`; fix “N ticket(s)” summary; link from receipt/ticket | §6 |
| Shared | Buyer-safe status timeline component | §6.7 |

| Exit criteria | From home Next up / activity chips, user reaches QR, receipt, pickup, or refund without dead ends |
| Out of scope | Apple Wallet; host fulfillment desk |

### Phase 5 — Passport / Vault / Reviews / Connect summaries

**Goal:** Identity + community strips and hubs use plain privacy language and prompts.

| Area | Improvements | Refs |
| --- | --- | --- |
| Passport | Hub readiness strip; plain visibility language; home progress card (done in P3 — deepen hub) | §8 |
| Badges | Next-badge hint on Passport / home | §8 |
| Vault | Unlock summary quality; subscriptions discoverability | §8 |
| Reviews | Post-check-in prompts (ticket detail, Alerts, home); optional `?ticket_id=` | §8 |
| Connect | Pending count on home (P3); copy clarifiers Message requests vs Connect requests; keep `/connect` canonical | §7 |
| Privacy copy | “Who can see what” summary on Passport settings | §8, §12 |

| Exit criteria | Eligible fan is prompted to review; Passport privacy is understandable without reading docs |
| Out of scope | Fan Connect matching algorithm changes; Vault studio |

### Phase 6 — Buyer-side Ambassador dashboard summaries

**Goal:** Active promoters get a clearer earn loop; non-promoters stay uncluttered.

| Work | Detail | Refs |
| --- | --- | --- |
| Overview empty / active states | Clear Become an Ambassador vs active snapshot | §9 |
| Earnings labels | Buyer-safe sale status words; waterfall clarity | §9 |
| Links shortcut | Emphasize Copy link from overview + home strip (P3) | §9 |
| Leaderboard copy | “Your campaigns” — not global | §9 |
| Payouts | Honest placeholder until rails; then history | §9 |
| Sidebar | Earn group already from Phase 2 | §3, §9 |

| Exit criteria | Active ambassador can copy a link and see Estimated/Payable in &lt;2 taps from Personal home |
| Out of scope | Host Ambassadors campaign admin; payout rail backend |

### Phase 7 — Route aliases, docs, smoke tests

**Goal:** Lock the migration story and prevent regressions. Much of the redirect matrix is **already shipped** (§13) — this phase verifies and documents.

| Work | Detail |
| --- | --- |
| Verify 308s | `/dashboard/merch` → merchandise; `/host/settings/notifications` → dashboard settings notifications |
| Keep Connect aliases | `/dashboard/connect*` → `/connect*`; optional nav href → `/connect` |
| Keep notifications canonical | `/dashboard/settings/notifications` |
| Docs sync | FRONTEND_ROUTES, EXECUTION_TRACKER, unification audit (Buyer→Personal), MERCH/FAN_CONNECT/PRIVACY cross-links (§13.7) |
| Smoke / unit tests | `test:buyer-dashboard-nav`, redirect smoke, Connect alias smoke, breadcrumbs Personal, switcher behavior, Command Center smoke (§13.8) |
| Tracker | Mark Phases 2–7 done in EXECUTION_TRACKER |

| Exit criteria | CI green; docs match code; no broken bookmark for merch/connect/notifications |
| Out of scope | Deferred URL renames (`/dashboard/ambassadors`, `/dashboard/workspaces`) unless explicitly opened |

### 14.1 Dependency graph

```
Phase 1 (docs) ──✔
       │
       ▼
Phase 2 (chrome) ─────────────────────────────┐
       │                                        │
       ▼                                        │
Phase 3 (Command Center home) ──┬──► Phase 5 (identity/community polish)
       │                        └──► Phase 6 (ambassador polish)
       ▼
Phase 4 (commerce pages)  (can parallelize with 5–6 after 3 starts)
       │
       ▼
Phase 7 (aliases / docs / tests)  ← also run lightweight checks after 2 & 3
```

Phases **4, 5, 6** may run in parallel after Phase 3 H1 (header + Next up + quick actions) lands. Phase **7** should run a **lite** pass after Phase 2 (label smoke) and a **full** pass at the end.

### 14.2 Already done (do not redo)

| Item | Where |
| --- | --- |
| Shared `WorkspaceShell` + Personal title | Option A / current layouts |
| `Host: {name}` switcher labels | `hostWorkspaceChromeTitle` |
| Become a host when zero workspaces | `WorkspaceSwitcher` |
| No private Host peer in SiteHeader | `SiteHeader.tsx` |
| Merch 308 + notifications 308 | `next.config.ts` |
| Connect aliases | `dashboard/connect/**` |
| This audit | Phase 1 |

### 14.3 Success criteria (end state)

1. Chrome language is **Personal** / **Personal account** / **Host: {name}** end-to-end.  
2. `/dashboard` is a Personal Command Center (Next up + urgency), not lifetime metric cards.  
3. Tickets → Orders → Merch → Refunds deep links work with buyer-safe statuses.  
4. Identity/community/ambassador summaries respect §12.  
5. Redirects/aliases documented and smoke-tested; no unnecessary URL churn.

---

## 15. Final audit summary

**Verdict:** Keep `/dashboard` as the Personal account workspace and remodel its home into a **Personal Command Center**. Keep `/host` as Host Command Center. Unify through shared chrome — never mix data. No route deletions required; merch 308 and Connect aliases already exist.

### 15.1 Current buyer routes found

**41** `page.tsx` under `frontend/src/app/dashboard/**` (34 functional + 6 Connect aliases + 1 merch legacy redirect).

| Group | Routes |
| --- | --- |
| Home / account | `/dashboard`, `/notifications`, `/settings`, `/settings/notifications` |
| Commerce | `/tickets(+/*)`, `/orders(+/*)`, `/merchandise(+/*)`, `/merch`→redirect, `/cart`, `/refunds(+/*)` |
| Community | `/messages(+/*)`, `/team(+/*)`, `/connect*`→`/connect*`, `/following` |
| Identity | `/passport(+/*)`, `/badges`, `/vault(+/*)`, `/reviews` |
| Growth | `/ambassador(+/*)` |
| Canonical Connect (Personal shell) | `/connect/*` |

### 15.2 What `/dashboard` shows today

**Personal Command Center (Phase 3 shipped):** Next up (ticket QR / merch / cart) · My activity (attention only) · Messages & community · Identity · Vault · Ambassadors (conditional) · Quick actions · quiet welcome for new users. Routes unchanged. Own-data privacy §12 preserved. No host finance/scanner/admin on home.

### 15.3 Main buyer-side navigation problems

1. ~~Naming drift: SiteHeader Dashboard vs Personal~~ → **Fixed** (Phase 2: Personal)  
2. ~~Team collides with Host Team~~ → **Fixed** (Workspaces)  
3. ~~Home is soft metrics~~ → **Fixed** (Phase 3 Command Center)  
4. Identity/Growth dense; Ambassadors path singular vs plural label — Growth → **Earn** done; path pluralization later  
5. Cart / vault subscriptions / refunds discoverability — home strips help; deep pages Phase 4  


### 15.4 Recommended Personal sidebar

| Group | Items |
| --- | --- |
| Home | Overview, Alerts |
| Activity | Tickets, Orders, Merch, Refunds |
| Community | Messages, **Workspaces**, Connect, Following |
| Identity | Passport, Badges, Vault, Reviews |
| **Earn** (rename Growth) | Ambassadors |
| Account | Settings |

Cart and deep links stay off primary nav. URLs unchanged except optional Connect nav → `/connect`.

### 15.5 Recommended `/dashboard` home layout

Personal Command Center: Header → **Next up** (ticket/QR, merch pickup) → My activity chips → Messages & community → Identity → Vault → Ambassador (conditional) → Quick actions. Switcher stays in **shell only**. Hide empty optional sections.

### 15.6 Tickets / orders / merch / refund findings

| Area | Finding |
| --- | --- |
| Tickets | Strong wallet + QR modal + PDF + offline + transfer; home unused; refund path missing from pass |
| Orders | Clear receipts; weak attention + no refund/wallet exits |
| Merch | Strong pickup wallet; shipping thinner; merch 308 done |
| Cart | Useful resume; off-nav OK; empty needs CTA |
| Refunds | Clear full-only flow; disconnected from orders/tickets |
| Concept | Keep Tickets / Orders / Merch separate; “Purchases” only as home strip |

### 15.7 Messages / Connect / Following findings

Not duplicates: Messages = inbox; Connect = peer graph (`/connect`); Following = host list + email Notify. Keep Connect aliases. Following stays list-first (no feed yet). Home: unread P1, Connect pending P2.

### 15.8 Passport / Vault / review findings

Strong private hubs and privacy settings; weak Command Center surfacing. Replace Passport `Open`; add Vault unlock summary; add post-check-in review prompts; plain-language visibility on hub.

### 15.9 Ambassador buyer-side findings

Solid promote-and-earn mini-app; separate from Host Ambassadors. Conditional home strip for active promoters. Rename sidebar group Growth → **Earn**. Leaderboard = own campaigns only. Payout history still placeholder.

### 15.10 Workspace switcher / top-nav findings

Option A mostly met: Personal account · Host: {name} · Become a host · no private Host peer · public Hosts kept. Fix SiteHeader **Dashboard** → **Personal**.

### 15.11 Privacy boundaries

Personal shows **own** tickets, orders, merch, refunds, messages, Passport/Vault/reviews, Ambassador activity only. Must never show host finance/team/attendees/scanners, hidden venues early, others’ private Connect data, raw QR secrets, raw payment refs, or admin tools.

### 15.12 Redirect / alias recommendations

| Item | Action |
| --- | --- |
| `/dashboard/merch` → merchandise | **Keep 308** (done) |
| `/dashboard/connect*` → `/connect*` | **Keep aliases** |
| `/dashboard/settings/notifications` | **Canonical keep** (+ host 308 in) |
| Team / Growth / Dashboard labels | **UI rename only** |
| `/dashboard` → `/personal` etc. | **Defer** |

### 15.13 Implementation phases

| Phase | Focus | Status |
| --- | --- | --- |
| 1 | Audit & docs | **Done** |
| 2 | Chrome labels, vertical sidebar, Personal, switcher | **Done** |
| 3 | Personal Command Center home | **Done** |
| 4 | Tickets / Orders / Merch / Refunds pages | Next |
| 5 | Passport / Vault / Reviews / Connect | — |
| 6 | Buyer Ambassador summaries | — |
| 7 | Aliases verify, docs sync, smoke tests | Partial (Phase 3 docs + smokes) |

### 15.14 Open questions / risks

| # | Question / risk | Suggestion |
| --- | --- | --- |
| 1 | SiteHeader: “Personal” vs “Workspace” entry? | Prefer **Personal** |
| 2 | Create event CTA intensity for personal-only users? | Keep growth CTA; don’t treat as Host nav |
| 3 | QR for `confirmed` vs only `ready_for_pickup`? | Product call; document in MERCHANDISE.md |
| 4 | Following in-app updates vs email-only? | Stay list + Notify for v1 |
| 5 | Hide Earn nav until first Ambassador enrollment? | Keep visible; hide home strip only |
| 6 | `localStorage` QR cache XSS / shared-device risk | Purge on logout; never clipboard payload |
| 7 | Dual ambassador earnings APIs (cutover) | Consolidate when domain API stable |
| 8 | Payout rails still immature | Honest copy; don’t over-promise on home |
| 9 | Doc drift (unification audit still says Buyer) | Fix in Phase 7 docs sync |
| 10 | Parallel Host chrome work | Coordinate labels so Personal/Host stay symmetric |

### 15.15 Final recommendation

1. **Keep** `/dashboard` + `/host` (Option A) — **confirmed**.  
2. **Personal Command Center on `/dashboard`** — **shipped** (Phase 3); routes and permissions unchanged.  
3. **Do not** delete routes or merge buyer/host data — **preserved**.  
4. **Continue** Phases 4–7 for deep page polish; privacy §12 remains invariant.

---

## Explicit non-goals (for this audit)

| Non-goal | Reason |
| --- | --- |
| Delete `/dashboard` routes | Out of scope; aliases/redirects only where already legacy (§13) |
| Merge buyer + host data tables | Product invariant — Personal vs Host Command Center (§12) |
| Rename URL prefix `/dashboard` → `/personal` | Deferred; Option A keeps prefixes (§13.6) |
| Implement Phases 4–7 in this audit pass | Phases 2–3 shipped; 4–7 remain (§14) |
| Build a second home at `/dashboard/command` | Rejected in §2.8 |
| Duplicate WorkspaceSwitcher in page header | Lives in shell only (§10, §11) |
