# Host area audit — Pàdéyá

**Status: audit + implementation reference.** Sections §1–§10 record the July 2026 audit and proposals. **Implementation notes** (below) reflect what shipped in the Host Command Center — use those for current behavior; treat unlisted audit items as still proposed.

**Audit date:** July 2026  
**Scope:** Private host workspace (`/host/*`), public Legacy surfaces, navigation, Command Center home, roadmap, events listing, role behavior, and safe migration planning.

## Implementation notes (July 2026)

Host Command Center is **live** in the frontend. Canonical home: **`/host`**. Product copy may say “host dashboard” — that means `/host`, not a separate route and **not** `/dashboard/host`.

Personal account tools remain on **`/dashboard/*`** (shell title **Personal**). Shared chrome + switcher: [DASHBOARD_HOST_UNIFICATION_AUDIT.md](./DASHBOARD_HOST_UNIFICATION_AUDIT.md).

| Area | Shipped | Still proposed / partial |
| --- | --- | --- |
| **Canonical home** | `/host` — `OwnerCommandCenter` (owner) or `MemberDeskOverview` (team); **no** `WorkspaceNavGrid` on home | — (platform-admin **user** impersonation shipped; see SECURITY.md) |
| **Workspace chrome** | Shared `WorkspaceShell`; title **Host: {display_name}**; always-on switcher (**Personal account** · **Host: {name}**); SiteHeader has **no** private Host peer (public **Hosts** marketplace only) | Last-used-mode Dashboard click (deferred; top nav → `/dashboard`) |
| **Alias redirect** | `/host/dashboard` → `/host` (**308**) in `next.config.ts` + defensive `page.tsx` | **No** `/dashboard/host` alias |
| **Roadmap** | `/host/roadmap` — launch checklist; statuses **inferred** from workspace APIs (`host-roadmap.ts`) | Persisted skip/opt-out API; “Share event” tracking |
| **Onboarding** | `/host/onboarding` — first-time become-a-host only; existing host → **`/host/roadmap`** (`HostOnboardingRedirectGuard`) | — |
| **Sidebar** | Four groups in `frontend/src/lib/nav/workspace.ts`: **Home** (Overview, Roadmap) · **Operate** (Events, Tickets & Entry, Merch Studio, Host Inbox) · **Grow** (Ambassador Campaigns, Sponsorships, Audience CRM, Legacy Page, Vault Studio) · **Manage** (Analytics, Host Team, Host Settings, Support → `/support`). Paths unchanged. Shell title **Host: {display_name}**. | — |
| **Deep links off sidebar** | Payouts, promos, templates, AI, announcements, followers, bank accounts — reachable from Command Center, settings, or event ops | — |
| **Role landing** | `hostHomePathForWorkspace()` — owner → `/host`; desk-focused scanner/merch → **`/host/desk`**; sponsor manager → `/host/sponsorships` when granted; used by switcher (never hardcode `/host/events`) | — |
| **Role sidebar** | `navGroupsForWorkspace()` — permission-gated items; desk staff get minimal **Operate** only (+ Merch when granted); Roadmap hidden for desk/read-only | — |
| **Event list** | `/host/events` — tabs, search, status/city/visibility/date filters, sort, **Table default** (+ List, Grid); desk staff see assigned events only; desk roles coerced off Grid → Table; grid cards reuse `HostEventRowActions` | Server-side search/sort params |
| **Server redirects (308)** | `/host/events/[id]/merch` → `…/merchandise`; `/host/settings/notifications` → `/dashboard/settings/notifications` | — |
| **Support entry** | `/host/support` — CTA to `/support` inbox; Support shell stays separate from Personal/Host switcher | Host-scoped support ticket API |
| **Docs route** | `/host/events/[id]/studio` — **still no `page.tsx`**; Event Studio lives on `/edit?step=` | Add alias or fix docs only |
| **CC polish (2026-07-20)** | Header Overview framing; member role titles; Today’s ops Scanner/Pickup gated (`canScanTickets` / `canScanMerch`); host-switch refetch; Pending tasks **Needs attention**; event action labels Merch Studio / Ambassador Campaigns; routes + permissions unchanged | See [HOST_COMMAND_CENTER_POLISH.md](./HOST_COMMAND_CENTER_POLISH.md) |

**Verification:** `npm run test:host-command-center` · `npm run test:workspace-privacy` · related: `npm run test:host-team`. See [HOST_COMMAND_CENTER_POLISH.md](./HOST_COMMAND_CENTER_POLISH.md) · [EXECUTION_TRACKER.md](./EXECUTION_TRACKER.md) · [FRONTEND_ROUTES.md](./FRONTEND_ROUTES.md) · [HOST_PERMISSIONS.md](./HOST_PERMISSIONS.md).

## Table of contents

1. [Current route audit](#1-current-route-audit)
2. [`/host` vs `/host/dashboard` comparison](#2-host-vs-hostdashboard-comparison)
3. [Public host pages separation](#3-public-host-pages-separation)
4. [Proposed simplified host navigation](#4-proposed-simplified-host-navigation)
5. [Host dashboard home proposal](#5-host-dashboard-home-proposal)
6. [Roadmap / onboarding proposal](#6-roadmap--onboarding-proposal)
7. [Event listing proposal](#7-event-listing-proposal)
8. [Role-aware behavior](#8-role-aware-behavior)
9. [Migration / redirect plan](#9-migration--redirect-plan)
10. [Final audit summary](#10-final-audit-summary)

---

## 1. Current route audit

**Method:** Globbed `frontend/src/app/host/**/page.tsx` (84 routes). Read `frontend/src/app/host/page.tsx`, `layout.tsx`, `middleware.ts`, `frontend/src/lib/nav/host-nav.ts`, `frontend/src/lib/host-access.ts`, and `docs/FRONTEND_ROUTES.md`.

**Shell behavior** (`frontend/src/app/host/layout.tsx`):

- All routes require auth via `RequireAuth` + `HostWorkspaceProvider`.
- `/host/onboarding` and `/host/events/[id]/preview` render **without** the workspace sidebar (`WorkspaceShell`).
- All other routes use sidebar nav from `navForWorkspace()` / `navGroupsForWorkspace()` with role-aware `homeHref` from `hostHomePathForWorkspace(active)` (owners → `/host`; desk → `/host/desk`; etc.).
- Blocked team members redirect to `/host/access-denied` via `HostAccessGuard`.

**Middleware** (`frontend/src/middleware.ts`): only rewrites public `/@username…` → `/u/[username]…`. No host dashboard redirects.

### 1.1 Workspace root & access

| Route | Purpose | Component | Overlaps with | Recommendation |
| --- | --- | --- | --- | --- |
| `/host` | Host Command Center: owner metrics + nav grid; team member desk overview | `frontend/src/app/host/page.tsx` | Fan `/dashboard` (different product); `/host/desk` (ops landing for staff) | **Stay** — canonical home (Option A) |
| `/host/access-denied` | Permission denied with back link | `…/access-denied/page.tsx` | — | **Stay** |
| `/host/onboarding` | Become-a-host signup form (`onboardHost`); redirects if host exists | `…/onboarding/page.tsx` | `/host/roadmap` (*proposed*) | **Stay** — first-time flow only |
| `/host/desk` | Host-wide ticket scanner / merch pickup queue for assigned events | `…/desk/page.tsx` | Per-event check-in / fulfillment | **Stay** — desk staff landing |
| `/host/ai` | Host AI Copilot (`ai.use_own`) | `…/ai/page.tsx` | `/host/events/[id]/ai` | **Stay** |

### 1.2 Events (`/host/events/*`)

| Route | Purpose | Component | Overlaps with | Recommendation |
| --- | --- | --- | --- | --- |
| `/host/events` | Event list with status pill filters + card UI | `…/events/page.tsx` | Command Center “Upcoming events” on `/host` | **Stay** — improve listing (§7) |
| `/host/events/new` | Create event (Event Studio) | `…/events/new/page.tsx` | `/host/templates` | **Stay** |
| `/host/events/[id]` | Event detail hub + ops subnav | `…/events/[id]/page.tsx` | Event Studio edit | **Stay** |
| `/host/events/[id]/edit` | Event Studio edit (`?step=` deep links) | `…/events/[id]/edit/page.tsx` | `/host/events/new` | **Stay** |
| `/host/events/[id]/preview` | Host preview (no workspace shell) | `…/events/[id]/preview/page.tsx` | Public `/events/[slug]` | **Stay** |
| `/host/events/[id]/tickets` | Ticket tier builder | `…/tickets/page.tsx` | Event Studio tickets step | **Stay** |
| `/host/events/[id]/check-in` | Door QR scanner | `…/check-in/page.tsx` | `/host/desk`, `/staff/check-in/[eventId]` | **Stay** |
| `/host/events/[id]/check-in/analytics` | Check-in stats | `…/check-in/analytics/page.tsx` | `/host/events/[id]/analytics` | **Stay** |
| `/host/events/[id]/offline-check-in` | Offline scan buffer + sync | `…/offline-check-in/page.tsx` | Check-in | **Stay** |
| `/host/events/[id]/attendees` | Attendee search + staff assign | `…/attendees/page.tsx` | Check-in | **Stay** |
| `/host/events/[id]/analytics` | Per-event funnel / sales analytics | `…/analytics/page.tsx` | `/host/analytics` portfolio | **Stay** |
| `/host/events/[id]/ai` | Event-scoped AI drafts | `…/ai/page.tsx` | `/host/ai` | **Stay** |
| `/host/events/[id]/ambassadors` | Per-event Ambassadors enable/manage | `…/ambassadors/page.tsx` | `/host/ambassadors/*` | **Stay** |
| `/host/events/[id]/tables` | Table / seat assignment | `…/tables/page.tsx` | Tickets | **Stay** |
| `/host/events/[id]/bundles` | Ticket + merch bundle builder | `…/bundles/page.tsx` | Merch discounts | **Stay** |
| `/host/events/[id]/post-event-drops` | Post-event merch drops | `…/post-event-drops/page.tsx` | Merch | **Stay** |
| `/host/events/[id]/memory` | Event Memory overview | `…/memory/page.tsx` | Public `/@user/memories/…` | **Stay** |
| `/host/events/[id]/memory/edit` | Edit recap + gallery | `…/memory/edit/page.tsx` | Legacy content | **Stay** |
| `/host/events/[id]/merch` | **Client redirect** → `…/merchandise` | `…/merch/page.tsx` | Merchandise | **Redirect** — already redirects in FE; formalize server redirect later (§9) |
| `/host/events/[id]/merchandise` | Merch Studio (stats + product table) | `…/merchandise/page.tsx` | `/host/merchandise` global | **Stay** |
| `/host/events/[id]/merchandise/new` | Merch Studio create | `…/merchandise/new/page.tsx` | Global merch new | **Stay** |
| `/host/events/[id]/merchandise/[merchId]/edit` | Merch Studio editor | `…/merchandise/[merchId]/edit/page.tsx` | Global edit | **Stay** |
| `/host/events/[id]/merchandise/orders` | Event merch orders | `…/merchandise/orders/page.tsx` | Fulfillment | **Stay** |
| `/host/events/[id]/merchandise/fulfillment` | Pickup desk (QR scan, notes) | `…/merchandise/fulfillment/page.tsx` | `/host/desk` | **Stay** |

**Note:** `docs/FRONTEND_ROUTES.md` references `/host/events/[id]/studio` — **no `page.tsx` exists**; studio lives on `/edit` with `?step=`.

### 1.3 Legacy studio (`/host/legacy/*`)

Private editing for the public Legacy Page. **Not** the public page itself (see §3).

| Route | Purpose | Component | Overlaps with | Recommendation |
| --- | --- | --- | --- | --- |
| `/host/legacy` | Legacy Studio overview + preview links | `…/legacy/page.tsx` | `/host/settings`, public `/@username` | **Stay** |
| `/host/legacy/edit` | Identity, CTAs, contact | `…/legacy/edit/page.tsx` | `/host/settings` (profile fields) | **Stay** — consider cross-link only |
| `/host/legacy/content` | Content blocks, vault preview config | `…/legacy/content/page.tsx` | Vault, reviews | **Stay** |
| `/host/legacy/preview` | Full public preview | `…/legacy/preview/page.tsx` | `/@username` | **Stay** |
| `/host/legacy/tier` | Tier progress + history | `…/legacy/tier/page.tsx` | — | **Stay** |

### 1.4 Vault studio (`/host/vault/*`)

| Route | Purpose | Component | Overlaps with | Recommendation |
| --- | --- | --- | --- | --- |
| `/host/vault` | Vault Studio dashboard | `…/vault/page.tsx` | Public `/@username/vault` | **Stay** |
| `/host/vault/new` | Multi-step drop creator | `…/vault/new/page.tsx` | — | **Stay** |
| `/host/vault/[id]` | Drop detail hub | `…/vault/[id]/page.tsx` | Edit / preview | **Stay** |
| `/host/vault/[id]/edit` | Edit drop + access rules | `…/vault/[id]/edit/page.tsx` | — | **Stay** |
| `/host/vault/[id]/preview` | Locked vs owner preview | `…/vault/[id]/preview/page.tsx` | Public item detail | **Stay** |
| `/host/vault/preview` | Studio catalog / fan-facing preview | `…/vault/preview/page.tsx` | Public catalog | **Stay** |
| `/host/vault/earnings` | Vault unlock earnings | `…/vault/earnings/page.tsx` | `/host/payouts` | **Stay** |
| `/host/vault/subscriptions` | Subscriber list | `…/vault/subscriptions/page.tsx` | — | **Stay** |

### 1.5 Merchandise (global)

| Route | Purpose | Component | Overlaps with | Recommendation |
| --- | --- | --- | --- | --- |
| `/host/merchandise` | Merch across all events | `…/merchandise/page.tsx` | Per-event merchandise | **Stay** |
| `/host/merchandise/new` | Create merch (pick event) | `…/merchandise/new/page.tsx` | Event-scoped new | **Stay** |
| `/host/merchandise/[id]/edit` | Edit product | `…/merchandise/[id]/edit/page.tsx` | Event-scoped edit | **Stay** |
| `/host/merchandise/discounts` | Merch discount codes | `…/discounts/page.tsx` | `/host/promos` (ticket promos) | **Stay** |
| `/host/merchandise/size-charts` | Size chart library | `…/size-charts/page.tsx` | — | **Stay** |
| `/host/merchandise/shipping-zones` | Flat shipping zones | `…/shipping-zones/page.tsx` | — | **Stay** |
| `/host/merchandise/revenue` | Merch revenue splits | `…/revenue/page.tsx` | Analytics | **Stay** |
| `/host/merchandise/stock-alerts` | Stock alert inbox | `…/stock-alerts/page.tsx` | — | **Stay** |
| `/host/merchandise/reviews` | Review reply inbox | `…/reviews/page.tsx` | `/host/reviews` | **Stay** |
| `/host/merchandise/print-on-demand` | POD jobs | `…/print-on-demand/page.tsx` | — | **Stay** |

### 1.6 Growth: Ambassadors, promos, sponsorships, CRM

| Route | Purpose | Component | Overlaps with | Recommendation |
| --- | --- | --- | --- | --- |
| `/host/promos` | Ticket promo codes | `…/promos/page.tsx` | Merch discounts | **Stay** |
| `/host/ambassadors` | Ambassador partners overview | `…/ambassadors/page.tsx` | Fan `/dashboard/ambassador` | **Stay** |
| `/host/ambassadors/[id]` | Partner performance | `…/ambassadors/[id]/page.tsx` | — | **Stay** |
| `/host/ambassadors/campaigns` | Campaign list | `…/campaigns/page.tsx` | Per-event ambassadors | **Stay** |
| `/host/ambassadors/campaigns/new` | Create campaign | `…/campaigns/new/page.tsx` | — | **Stay** |
| `/host/ambassadors/campaigns/[id]` | Campaign detail + leaderboard | `…/campaigns/[id]/page.tsx` | — | **Stay** |
| `/host/ambassadors/conversions` | Conversion ledger + rewards | `…/conversions/page.tsx` | Payouts | **Stay** |
| `/host/ambassadors/payouts` | Ambassador payout summary | `…/payouts/page.tsx` | Owner payouts | **Stay** |
| `/host/sponsorships` | Slots + inquiries | `…/sponsorships/page.tsx` | Public `/sponsors` | **Stay** |
| `/host/sponsorships/new` | Create slot | `…/sponsorships/new/page.tsx` | — | **Stay** |
| `/host/audience` | CRM dashboard + segments | `…/audience/page.tsx` | Followers | **Stay** |
| `/host/followers` | Follower list | `…/followers/page.tsx` | Audience | **Stay** |
| `/host/announcements` | Announcement history | `…/announcements/page.tsx` | Messages | **Stay** |
| `/host/announcements/new` | Create announcement | `…/announcements/new/page.tsx` | — | **Stay** |
| `/host/reviews` | Reply / report reviews | `…/reviews/page.tsx` | Merch reviews | **Stay** |

### 1.7 Team, messages, analytics, finance, settings

| Route | Purpose | Component | Overlaps with | Recommendation |
| --- | --- | --- | --- | --- |
| `/host/team` | Team overview | `…/team/page.tsx` | Settings team link | **Stay** |
| `/host/team/members` | Accepted members | `…/team/members/page.tsx` | Team overview | **Stay** |
| `/host/team/invites` | Pending invites | `…/team/invites/page.tsx` | — | **Stay** |
| `/host/team/audit-log` | Team audit trail | `…/team/audit-log/page.tsx` | — | **Stay** |
| `/host/team/[id]` | Member edit (role, scope, perms) | `…/team/[id]/page.tsx` | — | **Stay** |
| `/host/messages` | Host inbox | `…/messages/page.tsx` | Fan `/dashboard/messages` | **Stay** |
| `/host/messages/[threadId]` | Thread detail | `…/messages/[threadId]/page.tsx` | — | **Stay** |
| `/host/messages/settings` | Messaging prefs + auto-reply | `…/messages/settings/page.tsx` | — | **Stay** |
| `/host/messages/notifications` | Message notifications | `…/messages/notifications/page.tsx` | — | **Stay** |
| `/host/analytics` | Portfolio analytics | `…/analytics/page.tsx` | Per-event analytics | **Stay** |
| `/host/payouts` | Balance + payout requests (**owner only**) | `…/payouts/page.tsx` | Vault earnings | **Stay** |
| `/host/bank-accounts` | Saved payout accounts (**owner only**) | `…/bank-accounts/page.tsx` | Settings | **Stay** |
| `/host/bank-accounts/[id]` | Bank account detail | `…/bank-accounts/[id]/page.tsx` | — | **Stay** |
| `/host/settings` | Host profile, taxonomy, appearance | `…/settings/page.tsx` | Legacy edit | **Stay** |
| `/host/settings/notifications` | **Client redirect** → `/dashboard/settings/notifications` | `…/settings/notifications/page.tsx` | Fan notification prefs | **Redirect** — keep alias (§9) |
| `/host/templates` | Event template library | `…/templates/page.tsx` | Event new | **Stay** |
| `/host/templates/[id]` | Template detail | `…/templates/[id]/page.tsx` | — | **Stay** |

### 1.8 Public host / Legacy routes (outside `/host`)

For cross-reference in §3 — **not** part of the private workspace.

| Route | Purpose | File | Recommendation |
| --- | --- | --- | --- |
| `/@{username}` | Public Legacy Page (rewrite) | Middleware → `frontend/src/app/u/[username]/page.tsx` | **Stay** public |
| `/@{username}/vault`, `/vault/[itemSlug]` | Public Vault catalog / detail | `…/u/[username]/vault/**` | **Stay** public |
| `/@{username}/merch`, `/merch/[productId]` | Host merch storefront | `…/u/[username]/merch/**` | **Stay** public |
| `/@{username}/memories/[eventSlug]` | Public Event Memory | `…/u/[username]/memories/**` | **Stay** public |
| `/hosts` | Host discovery marketplace | `frontend/src/app/hosts/page.tsx` | **Stay** public |
| `/sponsors`, `/sponsors/hosts` | Sponsorship marketplace | `frontend/src/app/sponsors/**` | **Stay** public |
| `/team/invite/[token]` | Accept team invite | `frontend/src/app/team/invite/[token]/page.tsx` | **Stay** — links to `/host` after accept |

---

## 2. `/host` vs `/host/dashboard` comparison

### Update (shipped): `/host/dashboard` is a 308 alias

> Historical audit below described a missing route. **Now shipped:** `/host/dashboard` → `/host` (308 in `next.config.ts` + defensive `page.tsx`). Canonical home remains **`/host`**.

### Historical finding (pre-alias): `/host/dashboard` did not exist

- ~~Zero files under `frontend/src/app/host/dashboard/`.~~ → alias page now present.
- ~~Zero code references to `/host/dashboard`.~~ → redirect + nav active alias.
- Docs and copy sometimes say “host dashboard” generically (`docs/PRODUCTION_SMOKE_TEST.md`, team invite CTA “Open host dashboard”) — they mean **`/host`**, not a separate route.

### What `/host` shows today

**File:** `frontend/src/app/host/page.tsx`

| Audience | Content |
| --- | --- |
| **Owner** (`OwnerHostOverview`) | Profile card, 4 metric cards (published events, followers, past buyers, balance), upcoming events list (top 3), **`WorkspaceNavGrid`** with 14 deep links (events, legacy, vault, audience, analytics, payouts, sponsorships, promos, merchandise, settings, team, bank accounts, templates, vault subscribers) |
| **Team member** (`MemberDeskOverview`) | Role-aware desk card, assigned events with scanner/pickup CTAs, or read-only empty state |

**Data sources (owner):** `fetchMyHost`, `fetchMyEvents`, `fetchAudienceStats`, `fetchHostBalance` — from `frontend/src/lib/hosts-api.ts`, `events-api.ts`, `crm-api.ts`, `finance-api.ts`.

### Real overlaps (not two host dashboards)

| Surface | Path | Product role |
| --- | --- | --- |
| **Host Command Center** | `/host` | Private host workspace home |
| **Fan dashboard** | `/dashboard` | Buyer/attendee home (`frontend/src/app/dashboard/page.tsx`) — tickets, orders, passport, vault unlocks |
| **Host desk** | `/host/desk` | Operational landing for scanner / merch staff (`hostHomePathForWorkspace()` sends desk-capable members here) |
| **Admin** | `/admin/*` | Platform ops — separate shell |

### Duplicated sections (on `/host` today)

- Metric cards overlap with dedicated pages (`/host/events`, `/host/followers`, `/host/audience`, `/host/payouts`).
- **`WorkspaceNavGrid`** duplicates sidebar items in `frontend/src/lib/nav/workspace.ts` **plus** many routes **not** in the sidebar (payouts, promos, bank accounts, templates, vault subscriptions, announcements, etc.) — creates a long “feature dump” on the home page.

### Missing relative to ideal Command Center

- No “next best action” or readiness checklist.
- No today’s ops snapshot (check-ins, pickups, pending messages).
- No ticket sales / merch pickup snapshots.
- No ambassador / sponsor alert strip.
- Team members already get a simplified view — good foundation for role-aware home (§5, §8).

### Option A — **selected**

| Option | Summary | Verdict |
| --- | --- | --- |
| **A** | `/host` = Host Command Center; `/host/dashboard` → redirect alias if it ever appears | **Recommended** — already true in code |
| B | Split overview (`/host`) vs metrics dashboard (`/host/dashboard`) | Rejected — adds confusion; no second home needed |
| C | `/host/dashboard` canonical, `/host` demoted | Rejected — contradicts existing links (`homeHref`, breadcrumbs, `hostHomePathForWorkspace`) |

**Rationale:** Every nav component, breadcrumb root, and post-invite flow already targets `/host`. Option A matches product direction, minimizes migration, and keeps public Legacy separate. If bookmarks or docs reference `/host/dashboard`, add a **308 redirect alias** to `/host` — do **not** build a second home page.

---

## 3. Public host pages separation

| Visibility | Routes | Auth | Purpose |
| --- | --- | --- | --- |
| **Public** | `/@{username}` → `/u/[username]` | None | Legacy Page fans and brands discover |
| **Public** | `/@{username}/vault`, `/merch`, `/memories/…` | None (gated content server-side) | Fan-facing commerce and loyalty |
| **Public** | `/hosts`, `/sponsors`, `/sponsors/hosts` | None | Discovery / marketplace |
| **Private** | `/host/*` | Login + host workspace membership | Studio, ops, finance, team |
| **Private edit → public view** | `/host/legacy/*` edits; preview at `/host/legacy/preview` or `/@username` | Host team | Never mix public URL into workspace sidebar as a nav destination |

**Invariant:** Public Legacy and Vault **must not** appear in the private host sidebar as primary nav targets. Sidebar links to **studio** paths (`/host/legacy`, `/host/vault`); “View public page” opens `/@username` in a new tab.

**SEO:** `robots.ts` disallows `/host/` — workspace is not indexed (`docs/FRONTEND_ROUTES.md`).

---

## 4. Proposed simplified host navigation

Target: sidebar for private Host Command Center (`/host/*`). Event-scoped routes (`/host/events/[id]/*`) use **EventOpsNav** (`frontend/src/components/host/EventOpsNav.tsx`) — not duplicated in the global sidebar.

### 4.1 Sidebar groups

#### Home

| Nav item | Route | Purpose | Who (permission keys) | Priority | Sidebar | Hidden for scanner/merch staff |
| --- | --- | --- | --- | --- | --- | --- |
| Overview | `/host` | Command Center | All workspace members | P0 | Yes | Scanner/merch: **simplified home**, not full owner grid |
| Roadmap | `/host/roadmap` (*proposed*) | Launch checklist | Owner; admin/event_manager read | P1 | Yes | **Hidden** (scanner/merch/viewer) |

#### Operate

| Nav item | Route | Purpose | Who | Priority | Sidebar | Hidden for scanner/merch |
| --- | --- | --- | --- | --- | --- | --- |
| Events | `/host/events` | Operational event list | `events.view` \| `events.edit` \| desk perms | P0 | Yes | Scanner: **assigned events only** (list filtered) |
| Tickets & Entry | `/host/desk` | Scanner + check-in entry | `tickets.scan_qr` \| `tickets.check_in` \| `merch.scan_pickup_qr` | P0 | Yes | **Primary** for scanner/merch staff |
| Merch Studio | `/host/merchandise` | Global merch catalog | `merch.view` \| create/edit \| desk | P1 | Yes | Merch staff: yes; scanner-only: hide |
| Host Inbox | `/host/messages` | Fan/host inbox | `messages.view` \| `messages.reply` | P1 | Yes | Hide unless granted |

**Tickets & Entry mapping:** Sidebar label “Tickets & Entry” → default `/host/desk`; per-event scanner → `/host/events/[id]/check-in`; offline → `…/offline-check-in`; attendees → `…/attendees`; check-in stats → `…/check-in/analytics`; ticket tiers → `…/tickets`.

#### Grow

| Nav item | Route | Purpose | Who | Priority | Sidebar | Hidden for scanner/merch |
| --- | --- | --- | --- | --- | --- | --- |
| Ambassador Campaigns | `/host/ambassadors` | Campaigns + partners | `ambassadors.view` + related | P1 | Yes | **Hidden** |
| Sponsorships | `/host/sponsorships` | Slots + inquiries | `sponsors.view` \| `sponsors.manage_slots` | P2 | Yes | **Hidden** |
| Audience CRM | `/host/audience` | CRM + segments | `events.view` \| `analytics.view_events` | P1 | Yes | **Hidden** |
| Legacy Page | `/host/legacy` | Legacy Studio | Owner; or `events.edit` / `team.edit_permissions` | P1 | Yes | **Hidden** |
| Vault Studio | `/host/vault` | Vault Studio | Same as Legacy studio gates | P1 | Yes | **Hidden** |

#### Manage

| Nav item | Route | Purpose | Who | Priority | Sidebar | Hidden for scanner/merch |
| --- | --- | --- | --- | --- | --- | --- |
| Analytics | `/host/analytics` | Portfolio insights | `analytics.view_*` | P1 | Yes | Hide unless granted |
| Host Team | `/host/team` | Members + invites | `team.view` + related | P1 | Yes | **Hidden** |
| Host Settings | `/host/settings` | Profile + taxonomy + theme | Owner; `team.view` \| `team.edit_permissions` | P1 | Yes | **Hidden** |
| Support | `/host/support` (*proposed*) or link to `/support` | Escalation / help | Owner; support_staff | P2 | Yes | **Hidden** |

**Not in sidebar (deep links / home quick actions):** `/host/payouts`, `/host/bank-accounts`, `/host/promos`, `/host/templates`, `/host/ai`, `/host/announcements`, `/host/reviews`, `/host/followers`, finance sub-pages — reachable from Command Center, settings grid, or event ops nav.

### 4.2 Current sidebar vs proposal

**Today** (`frontend/src/lib/nav/workspace.ts` → `hostNav`): Overview, Roadmap, Events, Tickets & Entry, Merch Studio, Host Inbox, Ambassador Campaigns, Sponsorships, Audience CRM, Legacy Page, Vault Studio, Analytics, Host Team, Host Settings, Support. (Payouts/promos remain deep links.)

**Changes:** Add Roadmap; group visually; move Payouts/Promos out of primary sidebar; rename nothing yet; add Tickets & Entry → `/host/desk`.

---

## 5. Host dashboard home proposal

**Principle:** Command Center — actionable and scannable, **not** a 14-tile feature dump. Align with Option A: canonical `/host`.

### 5.1 Sections

| Section | Purpose | Data source (known) | Empty state | Priority |
| --- | --- | --- | --- | --- |
| **Next best action** | Single primary CTA from readiness gaps | Derived from §6 checklist + `publish_checklist` on events | “You’re launch-ready” + share CTA | P0 |
| **Host readiness / launch checklist** | Top 3 incomplete roadmap items | Host profile, Legacy, first published event | Link to `/host/roadmap` | P0 |
| **Upcoming events** | Next 3 nights | `fetchMyEvents()` — same filter as today | “Create your first event” | P0 |
| **Today’s operations** | Events starting in 24h with door/merch status | `fetchMyEvents()` + desk assignments | “No events today” | P0 |
| **Ticket sales snapshot** | 7-day purchases / revenue | `fetchHostEventAnalyticsOverview` aggregate (*proposed*) or portfolio analytics API | “No sales yet” | P1 |
| **Merch pickup snapshot** | Pending pickups count | Merch fulfillment API (*proposed* summary) | “No pickups queued” | P1 |
| **Pending messages / inquiries** | Unread threads + open sponsor inquiries | Messages + sponsorships APIs | “Inbox clear” | P1 |
| **Ambassador / sponsor alerts** | Pending reward approvals, new inquiries | `/host/ambassadors/conversions`, sponsorships | Hidden when none | P2 |
| **Quick actions** | Short button row | — | — | P0 |

### 5.2 Quick actions

| Label | Target | Who sees it |
| --- | --- | --- |
| Create event | `/host/events/new` | Owner; `events.create` |
| Open scanner | `/host/desk` or assigned event check-in | `tickets.scan_qr` \| `tickets.check_in` |
| Add merch | `/host/merchandise/new` | Owner; `merch.create` |
| Invite team | `/host/team/invites` | Owner; `team.invite` |
| Create ambassador campaign | `/host/ambassadors/campaigns/new` | `ambassadors.create_campaigns` |
| View analytics | `/host/analytics` | `analytics.view_*` |

### 5.3 Map from current `/host`

| Current block | Proposal |
| --- | --- |
| Owner profile card | **Keep** — trim; link to Legacy edit |
| 4 metric cards | **Keep 2** on home (next event + balance); rest move to Manage/Analytics |
| Upcoming events (3) | **Keep** |
| `WorkspaceNavGrid` (14 items) | **Remove from home** — lives in sidebar (§4) |
| Member desk overview | **Keep** — enhance as scanner/merch simplified Command Center |

**Do not put on home:** Vault studio, templates, bank accounts, merch sub-settings, per-event ops, full analytics charts, team audit log.

---

## 6. Roadmap / onboarding proposal

### 6.1 Canonical route choice

| Route | Role | Recommendation |
| --- | --- | --- |
| **`/host/roadmap`** (*proposed*) | Ongoing launch checklist for onboarded hosts | **Canonical** for checklist UI |
| **`/host/onboarding`** (exists) | One-time “become a host” form | **Keep** — first-time signup only |

**Rationale:** “Roadmap” matches product language for post-signup progress; “onboarding” is already wired (`SiteHeader`, `/hosts` marketplace, home page CTAs) for **creating** a host identity. After `onboardHost()`, send users to `/host` or `/host/roadmap`, not a duplicate checklist on onboarding.

**Alias (later):** `/host/onboarding/checklist` → `/host/roadmap` if needed.

### 6.2 Checklist items

**Status model:** `not_started` | `in_progress` | `done` | `skipped` (explicit opt-out, owner only).

| Item | Status inference | CTA | Why it matters | Route |
| --- | --- | --- | --- | --- |
| Complete host profile | `Host.profile.bio` + display_name set | Edit profile | Fans trust a complete identity | `/host/settings` |
| Add logo/cover | `profile.avatar_url` / `cover_url` | Add media | Visual credibility on Legacy | `/host/legacy/edit` |
| Set category/location | `Host.taxonomy` slugs + city | Set taxonomy | Discovery and SEO | `/host/settings` |
| Complete Legacy Page | Legacy publish checklist | Open Legacy Studio | Public reputation surface | `/host/legacy` |
| Create first event | Any `EventItem` exists | Create event | Core revenue path | `/host/events/new` |
| Add ticket types | `ticket_types.length > 0` | Add tickets | Cannot sell without tiers | `/host/events/[id]/tickets` |
| Set location/privacy | `location_visibility` + `visibility` set | Event settings | Trust + compliance | `/host/events/[id]/edit?step=…` |
| Publish event | `status === 'published'` | Publish | Go live on Pàdéyá | `/host/events/[id]/edit` |
| Test checkout | `publish_checklist.preview_checked` or test order flag | Preview checkout | Avoid launch-night payment bugs | `/host/events/[id]/preview` |
| Invite team/scanner | Team member or staff assignment exists | Invite scanner | Door ops without sharing login | `/host/team/invites` |
| Add merch | Merch product exists | Add merch | Incremental revenue at door | `/host/merchandise/new` |
| Enable ambassadors | Campaign or `open_ambassadors_enabled` | Enable Ambassadors | Growth loop | `/host/ambassadors/campaigns/new` |
| Add sponsorship slots | Sponsorship slot exists | Add slot | Brand partnerships | `/host/sponsorships/new` |
| Share event | Manual / share tracking (*proposed*) | Copy link | Drive ticket sales | Public `/events/[slug]` |
| Review analytics | User visited analytics after publish | View analytics | Close the feedback loop | `/host/analytics` |

### 6.3 Relation to Command Center

- **Home** shows top 3 incomplete items + next best action.
- **Full list** on `/host/roadmap` with filters (Launch / Grow / Operate).
- **Role visibility:** Hide Grow items (ambassadors, sponsorships, Legacy, Vault) for scanner-only and merch-only staff; show Operate subset only.

### 6.4 No route deletion

Keep `/host/onboarding` unchanged; add `/host/roadmap` as new page. Redirect `/host/onboarding` → `/host/roadmap` **only** for users who already have a host record (today onboarding already redirects to `/host/events` — refine to `/host/roadmap` in implementation phase).

---

## 7. Event listing proposal

### 7.1 Audit: current `/host/events`

**File:** `frontend/src/app/host/events/page.tsx`  
**Card UI:** `frontend/src/components/host/HostEventListCard.tsx`

| Aspect | Today |
| --- | --- |
| **Data** | `fetchMyEvents()` → `GET /events/mine` |
| **Filters** | Status pills: All, Draft, In review, Published, Paused, Completed, Rejected, Cancelled — client-side only |
| **Search** | None |
| **Sort** | API order only (no user sort) |
| **View** | Large visual cards with banner, metric chips (views/clicks/sales/revenue per event via `fetchHostEventAnalyticsOverview`) |
| **Actions per card** | View (public/preview), Manage, Analytics peek, Edit, Tickets, Check-in, Delete/Cancel |
| **Gaps** | No operational table mode; no date-based tabs (Upcoming/Past); no city/visibility filters; no Merch/Ambassadors quick actions; heavy N+1 analytics fetches per card |

### 7.2 Proposed listing

#### Tabs (date + status logic)

Uses `EventStatus` from `frontend/src/lib/types/events.ts`: `draft`, `published`, `paused`, `completed`, `cancelled`, `rejected`, `archived`.

| Tab | Rule |
| --- | --- |
| **Upcoming** | `end_datetime >= now` AND status ∈ `{published, paused, draft}` |
| **Drafts** | status ∈ `{draft, rejected}` |
| **Published** | status === `published` |
| **Past** | `end_datetime < now` AND status ∈ `{published, completed, paused}` |
| **Cancelled** | status === `cancelled` |
| **All** | No filter |

#### Search

Title, `venue_name`, `city`, `slug` — client-side first; server query param later.

#### Filters

Status (multi), date range (start/end), city (from `EventItem.city`), visibility (`listed` \| `unlisted` \| … from `EventItem.visibility`).

#### Sort

Start date (default asc for Upcoming), created_at, revenue/sales (from analytics overview), title A–Z.

#### View modes

| Mode | Use |
| --- | --- |
| **Compact / table** | **Default** — ops-friendly: date, city, status, sales, row actions |
| **List** | Medium density without hero images |
| **Grid** | Optional marketing-style cards (current card UX) |

#### Quick actions per row

| Action | Route | Permission |
| --- | --- | --- |
| View | `/events/[slug]` or `…/preview` | `events.view` |
| Edit | `/host/events/[id]/edit` | `events.edit` |
| Tickets | `/host/events/[id]/tickets` | `events.edit` or ticket perms |
| Scanner | `/host/events/[id]/check-in` | `tickets.scan_qr` \| `check_in` |
| Merch | `/host/events/[id]/merchandise` | `merch.view` |
| Ambassadors | `/host/events/[id]/ambassadors` | `ambassadors.view` |
| Analytics | `/host/events/[id]/analytics` | `analytics.view_events` |

Scanner-only roles: show **View + Scanner** only on assigned events.

#### Empty states

| Tab | Copy direction |
| --- | --- |
| Upcoming | “No upcoming events” → Create event |
| Drafts | “No drafts” |
| Published | “Nothing live” → Publish checklist |
| Past | “No past events yet” |
| Cancelled | “No cancelled events” |
| All | Same as today |

#### Relation to Command Center

Home “Upcoming events” (3 cards) → **View all** links to `/host/events?tab=upcoming`.

---

## 8. Role-aware behavior

**Sources:** `docs/HOST_PERMISSIONS.md`, `frontend/src/lib/host-team-roles.ts`, `frontend/src/lib/host-access.ts`, `frontend/src/lib/nav/host-nav.ts`, `RequireHostOwner`, `HostAccessGuard`.

### 8.1 Role mapping

| Product label | Codebase preset | Notes |
| --- | --- | --- |
| Host owner | `is_owner` on workspace | Not a team role; full access |
| Host admin / team member | `admin` | Near-full; no desk scan / payout / bank by default |
| Event manager | `event_manager` | Events + ticket ops |
| Scanner staff | `scanner` | Desk via scope + `tickets.scan_qr` / `check_in` |
| Merch staff | `merch_staff` | Desk via scope + `merch.scan_pickup_qr` |
| Sponsor manager | `sponsor_manager` | Sponsorships |
| Viewer | `viewer` | Read-only |
| Support staff | `support_staff` | Messages (*not in user list but exists*) |
| Ambassador manager | `ambassador_manager` | Ambassadors only |
| Finance manager | `finance_manager` | Finance + ambassador mark-paid |
| Platform admin | `super_admin` + `/admin/*` | **Not** host workspace — separate admin shell |

### 8.2 Behavior matrix

#### Host owner

| Aspect | Value |
| --- | --- |
| Default landing | `/host` (`hostHomePathForWorkspace`) |
| Sidebar | Full Home / Operate / Grow / Manage |
| Write access | Full |
| Hidden | — |
| Notes | Payouts/bank use `RequireHostOwner` |

#### Host admin (`admin`)

| Aspect | Value |
| --- | --- |
| Default landing | `/host` |
| Sidebar | Full except finance unless granted |
| Write access | Broad; no payout/bank APIs (owner-only v1) |
| Hidden | `/host/payouts`, `/host/bank-accounts` unless owner |
| Notes | Host-wide desk off by default |

#### Event manager

| Aspect | Value |
| --- | --- |
| Default landing | `/host` |
| Sidebar | Home, Operate (Events, Messages), Manage (Analytics partial) |
| Write access | Events, tickets, attendees |
| Hidden | Grow (Vault, Legacy edit) unless `events.edit`; no payouts |
| Notes | `ambassadors.view` read-only |

#### Scanner staff

| Aspect | Value |
| --- | --- |
| Default landing | **`/host/desk`** when `canScanTickets` |
| Sidebar | **Minimal:** Tickets & Entry (Desk), Events (filtered) |
| Write access | Check-in only on assigned events |
| Hidden | Grow, Manage, payouts, settings, Legacy, Vault |
| Notes | **Simplified Command Center** — not owner home grid |

#### Merch staff

| Aspect | Value |
| --- | --- |
| Default landing | **`/host/desk`** when `canScanMerch` |
| Sidebar | Desk, Events (filtered), Merch |
| Write access | Fulfillment / pickup on assigned events |
| Hidden | Grow, analytics, team, payouts |
| Notes | Pickup → `…/merchandise/fulfillment` |

#### Sponsor manager

| Aspect | Value |
| --- | --- |
| Default landing | `/host` |
| Sidebar | Home, Grow (Sponsorships), Manage (Analytics sponsors) |
| Write access | Sponsor slots + inquiries |
| Hidden | Desk, payouts, ambassadors |

#### Viewer

| Aspect | Value |
| --- | --- |
| Default landing | `/host` |
| Sidebar | Overview + granted read modules only |
| Write access | **Read-only** |
| Hidden | All mutating actions, payouts, bank |
| Notes | Matches `MemberDeskOverview` viewer path today |

#### Platform admin (admin-host mode)

| Aspect | Value |
| --- | --- |
| Default landing | `/admin` — not `/host` |
| Sidebar | `adminNav` — host routes only when impersonating/support (*proposed* explicit mode) |
| Write access | Platform permissions — do not conflate with host team toggles |
| Hidden | — |
| Notes | Event analytics also at `/admin/events/[id]/analytics` |

**Enforcement:** UI gating via `canAccessHostPath()`; API via `has_host_permission` / `has_event_permission` (`docs/HOST_PERMISSIONS.md`). Blocked paths → `/host/access-denied`.

---

## 9. Migration / redirect plan

**Hard rule:** Do not delete old routes without redirects.

### 9.1 Canonical routes

| Canonical | Role |
| --- | --- |
| `/host` | Host Command Center home |
| `/host/roadmap` (*proposed*) | Launch checklist |
| `/host/onboarding` | Become-a-host (first time) |
| `/host/events` | Event list |
| `/host/legacy/*` | Legacy studio (private) |
| `/@username` | Public Legacy (via rewrite) |

### 9.2 Redirects (recommended)

| From | To | HTTP | Phase |
| --- | --- | --- | --- |
| `/host/dashboard` | `/host` | **308** | 1 — alias page even though path unused today |
| `/host/events/[id]/merch` | `/host/events/[id]/merchandise` | 308 | 2 — replace client `router.replace` |
| `/host/settings/notifications` | `/dashboard/settings/notifications` | 308 | 2 — replace client redirect |
| `/host/onboarding` (host already exists) | `/host/roadmap` or `/host` | 302 | 2 — refine today’s `/host/events` redirect |

Prefer **308** for permanent bookmarks; **302** for conditional/auth flows.

### 9.3 Unchanged (keep)

All 84 existing `/host/**/page.tsx` routes except redirects above. Public `/@username`, `/u/*`, `/hosts`, `/sponsors/*` unchanged.

### 9.4 Aliases (temporary dual URL)

| Alias | Canonical | Notes |
| --- | --- | --- |
| `/host/dashboard` | `/host` | Docs/smoke tests saying “host dashboard” |
| `/host/onboarding` (return visits) | `/host/roadmap` | Optional; keep form on first visit |

### 9.5 Nav / breadcrumb / docs updates

| Area | Files to update (implementation phase) |
| --- | --- |
| Sidebar | `frontend/src/lib/nav/workspace.ts`, `host-nav.ts` |
| Home link | `frontend/src/app/host/layout.tsx` (`homeHref`) |
| Breadcrumbs | `frontend/src/lib/breadcrumbs.ts` |
| Workspace switcher | `frontend/src/components/hosts/WorkspaceSwitcher.tsx` |
| Docs | `docs/FRONTEND_ROUTES.md`, `docs/PRODUCTION_SMOKE_TEST.md` (“host dashboard” → `/host`) |
| Emails / CTAs | Team invite copy (`frontend/src/app/team/invite/[token]/page.tsx`) — already links `/host` |
| Site header | `frontend/src/components/layout/SiteHeader.tsx` |

### 9.6 Tests (implementation phase)

| Test | Purpose |
| --- | --- |
| Redirect integration | `/host/dashboard` → `/host` (308); merch legacy path |
| Role landing | Scanner → `/host/desk`; owner → `/host` |
| Permission guard | Blocked path → `/host/access-denied` |
| Smoke | `docs/PRODUCTION_SMOKE_TEST.md` — host home, onboarding, desk |
| Nav snapshot | Sidebar items per role preset |

### 9.7 Phased rollout

| Phase | Work |
| --- | --- |
| **1 — Aliases** | Add `/host/dashboard` redirect; add `/host/roadmap` page; document routes |
| **2 — Redirects** | Server redirects for merch + notifications; refine onboarding redirect |
| **3 — UX** | Command Center home (§5), event table (§7), sidebar groups (§4) |
| **4 — Deprecate** | Remove client-side redirects once server routes stable; monitor 404s |

---

## 10. Final audit summary

Executive summary of the full audit. Brand: **Pàdéyá**.

1. **Current `/host` and `/host/dashboard` difference** — `/host/dashboard` **does not exist** (no route, no code references). `/host` (`frontend/src/app/host/page.tsx`) is the only host home: owner Command Center with metrics + 14-link grid; team members get desk/read-only overview. Confusion is vs fan `/dashboard` or ops `/host/desk`, not two host dashboards.

2. **Recommended canonical route** — **`/host`** = Host Command Center (Option A). Add **`/host/dashboard` → `/host` (308)** only as a defensive alias for docs/bookmarks — never a second home.

3. **Routes to keep** — All **84** existing `/host/**/page.tsx` routes; public `/@username` → `/u/[username]`; `/host/onboarding` for become-a-host; `/host/desk` for scanner/merch landing.

4. **Routes to redirect** — `/host/dashboard` → `/host` (*proposed*); `/host/events/[id]/merch` → `…/merchandise` (formalize existing client redirect); `/host/settings/notifications` → `/dashboard/settings/notifications`; existing hosts hitting `/host/onboarding` → `/host/roadmap` or `/host` (refine current redirect to `/host/events`).

5. **Routes to rename or restructure** — No path renames required. **Restructure in UI only:** drop home `WorkspaceNavGrid` feature dump; add **`/host/roadmap`**; optional **`/host/support`**; group sidebar (§4); event list default **table** view (§7).

6. **Proposed sidebar/navigation** — Four groups: **Home** (Overview, Roadmap); **Operate** (Events, Tickets & Entry/desk, Merch Studio, Host Inbox); **Grow** (Ambassador Campaigns, Sponsorships, Audience CRM, Legacy Page, Vault Studio); **Manage** (Analytics, Host Team, Host Settings, Support). Paths unchanged. Payouts/promos/templates stay as deep links.

7. **Proposed `/host` home layout** — Next best action + top 3 roadmap gaps + upcoming events + today’s ops + sales/pickup snapshots + pending messages/inquiries + quick actions; **remove** 14-tile nav grid; role-aware simplification for scanner/merch staff (§5).

8. **Proposed roadmap/onboarding page** — **`/host/roadmap`** canonical checklist; **`/host/onboarding`** stays for first-time host creation; home shows top gaps, full list on roadmap (§6).

9. **Proposed `/host/events` listing** — Tabs: Upcoming, Drafts, Published, Past, Cancelled, All; search + filters + sort; **default compact/table** ops view; row actions: View, Edit, Tickets, Scanner, Merch, Ambassadors, Analytics (§7).

10. **Role-aware dashboard behavior** — Owner → full Command Center at `/host`; scanner/merch → **`/host/desk`** landing + minimal sidebar; viewer → read-only; admin/event manager/sponsor manager → permission-gated subsets; platform admin stays on `/admin` (§8, `HOST_PERMISSIONS.md`).

11. **Implementation phases** — (1) Redirect aliases + roadmap route, (2) server redirects + onboarding logic, (3) Command Center + event table + sidebar, (4) deprecate client redirects + monitor (§9).

12. **Open questions or risks** — **Studio naming** (Event Studio vs Merch Studio vs Vault Studio — consistent labels in sidebar?); **finance team grants** (payout/bank APIs owner-only in v1 while flags exist); **N+1 analytics** on event list cards; **`/host/events/[id]/studio`** documented but missing; **support entry** (host-scoped vs global `/support`); **roadmap status persistence** (new API vs inferred-only); ensure **no accidental indexing** of workspace (`robots` already disallows `/host/`).

---

## Related docs

- [FRONTEND_ROUTES.md](./FRONTEND_ROUTES.md)
- [HOST_PERMISSIONS.md](./HOST_PERMISSIONS.md)
- [TEAMS.md](./TEAMS.md)
- [LEGACY_PAGE.md](./LEGACY_PAGE.md) (if present)
- [VAULT.md](./VAULT.md)
