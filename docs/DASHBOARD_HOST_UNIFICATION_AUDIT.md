# Dashboard ↔ Host unification audit — Pàdéyá

**Status:** Audit complete; **Option A chrome Phases 2–5 implemented**; **Personal Command Center (buyer Phase 3) shipped** on `/dashboard` (20 July 2026).  
**Date:** July 2026  
**Brand:** Pàdéyá  

**Goal:** Document how `/dashboard` (personal / buyer tools) and `/host` (host workspace tools) differ today, so navigation and workspace switching can feel like one product **without mixing buyer data and host data**.

**Related:** [HOST_AREA_AUDIT.md](./HOST_AREA_AUDIT.md) · [BUYER_DASHBOARD_AUDIT.md](./BUYER_DASHBOARD_AUDIT.md) · [FRONTEND_ROUTES.md](./FRONTEND_ROUTES.md) · [TEAMS.md](./TEAMS.md) · [HOST_PERMISSIONS.md](./HOST_PERMISSIONS.md) · [EXECUTION_TRACKER.md](./EXECUTION_TRACKER.md) · [PRODUCTION_SMOKE_TEST.md](./PRODUCTION_SMOKE_TEST.md)

---

## Implementation notes (shipped — Option A)

UI/chrome unification only. **Do not** treat this as a data merge or Option B (`/dashboard/host`).

| Fact | Current behavior |
| --- | --- |
| **Personal tree** | `/dashboard/*` — buyer/fan tools; shell title **Personal** |
| **Host tree** | `/host/*` — host org tools; shell title **Host: {display_name}** |
| **Shared chrome** | One `WorkspaceShell` renderer; mode-specific nav configs (`buyerNav*` vs `hostNav*` / `navGroupsForWorkspace`) |
| **Site header** | Public **Hosts** marketplace (`/hosts`); logged-in **Personal** → `/dashboard` only; **no** private peer **Host** top-nav link |
| **Workspace entry** | **Personal** is the single top-nav workspace entry; in-shell switcher changes Personal ↔ Host |
| **Switcher labels** | **Personal account** · **Host: {name}** (+ Owner / role suffix); zero hosts → Personal + **Become a host** |
| **Personal sidebar (Phase 2)** | **Team** → **Workspaces** (`/dashboard/team`); group **Growth** → **Earn**; Connect → `/connect` (aliases kept) |
| **Host sidebar** | Disambiguated labels (Merch Studio, Host Inbox, Host Team, …); routes under `/host/*` unchanged |
| **Admin / Support** | Separate shells (`/admin/*`, `/support/*`); **not** workspace-switcher options |
| **Role-aware Host landing** | Switcher uses `hostHomePathForWorkspace` (owner → `/host`, desk → `/host/desk`, sponsor mgr → `/host/sponsorships`, …) — never hardcoded `/host/events` |
| **Redirects unchanged** | `/host/dashboard` → `/host`; merch alias; host notification prefs → personal settings |
| **Personal home (buyer Phase 3)** | `/dashboard` = **Personal Command Center** body remodel — routes unchanged; own-data only; **not** a buyer/host data merge |
| **Still out of scope** | No `/dashboard/host` alias or Option B tree; no merging Personal and Host data |

**Verification:** `npm run test:buyer-dashboard-nav` · `npm run test:host-command-center` · `npm run test:workspace-privacy` · `npm run test:personal-command-center` · `npm run lint` · `npm run build` · `npm run test:pwa` · `npm run test:theme`.

---

## Legend

| Column | Meaning |
| --- | --- |
| **User type** | Who the page is for (product role, not platform admin) |
| **Layout** | Shell wrapping the page |
| **Permissions** | Auth / host-team gates (FE + product intent; APIs remain source of truth) |
| **Overlap** | Conceptual or label overlap with the *other* workspace — not a recommendation to merge data |
| **Disposition** | `Stay` · `Redirect` · `Alias` · `Merge (chrome only)` · `Move (defer)` |

**Disposition policy for this audit**

| Value | Meaning |
| --- | --- |
| **Stay** | Keep URL and ownership in current workspace |
| **Redirect** | Legacy or duplicate path; send users to a canonical URL |
| **Alias** | Keep path as a thin redirect/alias for bookmarks/docs |
| **Merge (chrome only)** | Same *product concept* appears in both shells (e.g. account notifications); unify labels/entry, not data tables |
| **Move (defer)** | Possible future URL restructure — **not** recommended now |

---

## Shared shell facts

| Surface | Layout file | Shell | Sidebar title | Toolbar |
| --- | --- | --- | --- | --- |
| `/dashboard/*` | `frontend/src/app/dashboard/layout.tsx` | `RequireAuth` → `HostWorkspaceProvider` → `WorkspaceShell` (`buyerNav` / `buyerNavGroups`) | **Personal** | `WorkspaceSwitcher` |
| `/host/*` | `frontend/src/app/host/layout.tsx` | `RequireAuth` → `HostWorkspaceProvider` → `HostShell` (`navForWorkspace` + `HostAccessGuard`) | **Host: {display_name}** | `WorkspaceSwitcher` |
| Host exceptions | same layout | **No** `WorkspaceShell` for `/host/onboarding` and `/host/events/[id]/preview` | — | — |
| Fan Connect (canonical) | `frontend/src/app/connect/layout.tsx` | `RequireAuth` → `HostWorkspaceProvider` → `WorkspaceShell` with **personal** nav | **Personal** | `WorkspaceSwitcher` |
| Admin | `frontend/src/app/admin/layout.tsx` | `RequireAuth` (admin roles) → `WorkspaceShell` (`adminNav`) | **Admin** | none (not Personal/Host switcher) |
| Support | `frontend/src/app/support/layout.tsx` | `RequireAuth` (support roles) → `WorkspaceShell` (`supportNav`) | **Support** | none |

Page bodies commonly wrap content in `DashboardShell` (page header chrome inside the workspace main column). That is **not** a second app shell.

**Server redirects** (`frontend/next.config.ts`) — unchanged this phase; **no** `/dashboard/host`:

| From | To | HTTP |
| --- | --- | --- |
| `/host/dashboard`, `/host/dashboard/:path*` | `/host` | 308 |
| `/host/events/:id/merch` | `/host/events/:id/merchandise` | 308 |
| `/host/settings/notifications` | `/dashboard/settings/notifications` | 308 |
| `/dashboard/merch`, `/dashboard/merch/:path*` | `/dashboard/merchandise…` | 308 |

**Related (outside shells):** `/workspaces` post-login chooser. SiteHeader: public **Hosts** → `/hosts`; logged-in **Personal** → `/dashboard` (single workspace entry). Private Host tools only via in-shell switcher + role-aware `hostHomePathForWorkspace`.

---

## 1. Current route audit

### 1.1 Personal / buyer workspace — `/dashboard/*`

**Default permissions:** authenticated user (`RequireAuth`). No host membership required.  
**Default layout:** Personal `WorkspaceShell` (sidebar groups: Home · Activity · Community · Identity · Earn · Account; item **Workspaces** → `/dashboard/team`).

| Route | Purpose | User type | Component / file | Sidebar / layout | Permissions | Overlap with host | Disposition |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `/dashboard` | **Personal Command Center** — Next up, activity, messages, identity, Vault, Ambassadors | Attendee / buyer | `frontend/src/app/dashboard/page.tsx` → `PersonalCommandCenter` | Buyer shell + `DashboardShell` | Auth; own-data only | Parallel to Host Command Center; different data | **Stay** — Phase 3 shipped (URL unchanged) |
| `/dashboard/notifications` | In-app notification inbox (Alerts) | Attendee | `…/notifications/page.tsx` | Buyer shell | Auth | Account-level; host may deep-link here | **Stay** |
| `/dashboard/tickets` | My tickets list (upcoming/past/cancelled) | Ticket holder | `…/tickets/page.tsx` | Buyer shell | Auth | Label vs host “Tickets & Entry” desk | **Stay** |
| `/dashboard/tickets/[id]` | Ticket detail + QR / PDF | Ticket holder | `…/tickets/[id]/page.tsx` | Buyer shell | Auth (own ticket) | Host check-in scans *their* ticket | **Stay** |
| `/dashboard/tickets/[id]/transfer` | Transfer ticket ownership | Ticket holder | `…/tickets/[id]/transfer/page.tsx` | Buyer shell | Auth (own ticket) | — | **Stay** |
| `/dashboard/orders` | My order history | Buyer | `…/orders/page.tsx` | Buyer shell | Auth | Host sees sales, not this list | **Stay** |
| `/dashboard/orders/[id]` | Order receipt (ticket + merch lines) | Buyer | `…/orders/[id]/page.tsx` | Buyer shell | Auth (own order) | Host merch fulfillment is separate | **Stay** |
| `/dashboard/merch` | Legacy client redirect → merchandise | Buyer | `…/merch/page.tsx` | Buyer shell (brief) | Auth | — | **Redirect** → `/dashboard/merchandise` (formalize 308 later) |
| `/dashboard/merchandise` | My merch pickups / purchases | Buyer | `…/merchandise/page.tsx` | Buyer shell (nav label “Merch”) | Auth | Host `/host/merchandise` is studio | **Stay** — canonical buyer merch |
| `/dashboard/merchandise/[orderItemId]` | Merch item detail + pickup QR + review | Buyer | `…/merchandise/[orderItemId]/page.tsx` | Buyer shell | Auth (own item) | Host fulfillment desk | **Stay** |
| `/dashboard/cart` | Abandoned / active merch cart | Buyer | `…/cart/page.tsx` | Buyer shell (not primary nav) | Auth | — | **Stay** |
| `/dashboard/refunds` | My refund requests | Buyer | `…/refunds/page.tsx` | Buyer shell | Auth | Host/support refund ops elsewhere | **Stay** |
| `/dashboard/refunds/new` | Request full refund | Buyer | `…/refunds/new/page.tsx` | Buyer shell | Auth | — | **Stay** |
| `/dashboard/messages` | Fan inbox (fan↔host / connect rules) | Attendee | `…/messages/page.tsx` | Buyer shell | Auth | Label vs `/host/messages` (host inbox) | **Stay** — separate inbox |
| `/dashboard/messages/[threadId]` | Thread detail | Attendee | `…/messages/[threadId]/page.tsx` | Buyer shell | Auth + messaging perms | Same thread model, different role | **Stay** |
| `/dashboard/messages/settings` | Personal messaging prefs | Attendee | `…/messages/settings/page.tsx` | Buyer shell | Auth | Host has own message settings | **Stay** |
| `/dashboard/messages/notifications` | Message notification prefs | Attendee | `…/messages/notifications/page.tsx` | Buyer shell | Auth | — | **Stay** |
| `/dashboard/team` | List owned/joined host workspaces; jump into host | Attendee who is owner/staff | `…/team/page.tsx` | Buyer shell | Auth | Bridges to `/host`; overlaps `/workspaces` + switcher | **Stay** for now; later **Merge (chrome only)** with switcher/`/workspaces` |
| `/dashboard/team/workspaces` | Set / open active host workspace | Same | `…/team/workspaces/page.tsx` | Buyer shell | Auth | Duplicates `/workspaces` chooser | **Stay** for now; prefer switcher as primary |
| `/dashboard/connect` | Alias → `/connect` | Attendee | `…/connect/page.tsx` | Redirect out of layout | Auth | — | **Alias** → `/connect` |
| `/dashboard/connect/connections` | Alias → `/connect/connections` | Attendee | `…/connect/connections/page.tsx` | Redirect | Auth | — | **Alias** |
| `/dashboard/connect/requests` | Alias → `/connect/requests` | Attendee | `…/connect/requests/page.tsx` | Redirect | Auth | — | **Alias** |
| `/dashboard/connect/suggestions` | Alias → `/connect/suggestions` | Attendee | `…/connect/suggestions/page.tsx` | Redirect | Auth | — | **Alias** |
| `/dashboard/connect/events` | Alias → `/connect/events` | Attendee | `…/connect/events/page.tsx` | Redirect | Auth | — | **Alias** |
| `/dashboard/connect/settings` | Alias → `/connect/settings` | Attendee | `…/connect/settings/page.tsx` | Redirect | Auth | — | **Alias** |
| `/dashboard/following` | Hosts I follow + marketing opt-in | Attendee | `…/following/page.tsx` | Buyer shell | Auth | Inverse of host `/host/followers` | **Stay** |
| `/dashboard/passport` | Fan Passport hub | Attendee | `…/passport/page.tsx` | Buyer shell | Auth | — | **Stay** |
| `/dashboard/passport/settings` | Passport visibility / prefs | Attendee | `…/passport/settings/page.tsx` | Buyer shell | Auth | — | **Stay** |
| `/dashboard/badges` | Badge collection | Attendee | `…/badges/page.tsx` | Buyer shell | Auth | — | **Stay** |
| `/dashboard/vault` | My Vault library (unlocked / discover) | Attendee | `…/vault/page.tsx` | Buyer shell | Auth | Host `/host/vault` = studio | **Stay** |
| `/dashboard/vault/[itemId]` | Unlocked Vault item | Attendee | `…/vault/[itemId]/page.tsx` | Buyer shell | Auth (access rules) | Host edit/preview studio | **Stay** |
| `/dashboard/vault/subscriptions` | My Vault subscriptions | Attendee | `…/vault/subscriptions/page.tsx` | Buyer shell | Auth | Host `/host/vault/subscriptions` = subscriber list | **Stay** |
| `/dashboard/reviews` | My verified reviews (edit/remove own) | Attendee | `…/reviews/page.tsx` | Buyer shell | Auth | Host `/host/reviews` = reply inbox (cannot delete) | **Stay** |
| `/dashboard/ambassador` | Ambassadors overview (promote & earn) | Ambassador / fan promoter | `…/ambassador/page.tsx` | Buyer shell | Auth | Host `/host/ambassadors` = campaign owner tools | **Stay** |
| `/dashboard/ambassador/events` | My promoted events | Same | `…/ambassador/events/page.tsx` | Buyer shell | Auth | — | **Stay** |
| `/dashboard/ambassador/links` | Referral links / codes / QR | Same | `…/ambassador/links/page.tsx` | Buyer shell | Auth | — | **Stay** |
| `/dashboard/ambassador/earnings` | Earnings breakdown | Same | `…/ambassador/earnings/page.tsx` | Buyer shell | Auth | Host conversion ledger is host-owned | **Stay** |
| `/dashboard/ambassador/leaderboard` | Personal campaign ranking | Same | `…/ambassador/leaderboard/page.tsx` | Buyer shell | Auth | Host campaign leaderboard | **Stay** |
| `/dashboard/ambassador/payouts` | Ambassador payout / reward status | Same | `…/ambassador/payouts/page.tsx` | Buyer shell | Auth | Host ambassador payouts summary | **Stay** |
| `/dashboard/settings` | Account profile settings | Attendee | `…/settings/page.tsx` | Buyer shell | Auth | Host `/host/settings` = host profile | **Stay** |
| `/dashboard/settings/notifications` | Account email + push prefs | Attendee (shared account prefs) | `…/settings/notifications/page.tsx` | Buyer shell | Auth | **Canonical** for `/host/settings/notifications` redirect | **Stay** — shared account prefs (**Merge chrome only**) |

**Buyer route count:** 41 `page.tsx` files under `frontend/src/app/dashboard/**`.

---

### 1.2 Host workspace — `/host/*`

**Default permissions:** authenticated + active host workspace (`RequireHost` on most pages) + `HostAccessGuard` / `canAccessHostPath` for non-owners.  
**Default layout:** Host `WorkspaceShell` (groups: Home · Operate · Grow · Manage), permission-filtered via `navGroupsForWorkspace()`.

#### 1.2.1 Workspace root, access, onboarding

| Route | Purpose | User type | Component / file | Sidebar / layout | Permissions | Overlap with dashboard | Disposition |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `/host` | Host Command Center (owner) or member desk overview | Host owner / team | `frontend/src/app/host/page.tsx` | Host shell | Active workspace; members always allowed home | Personal `/dashboard` home (different data) | **Stay** — canonical host home |
| `/host/dashboard` | Alias → `/host` | — | `…/dashboard/page.tsx` + next.config 308 | N/A | — | Naming confusion with `/dashboard` | **Alias** → `/host` |
| `/host/access-denied` | Permission denied | Team member | `…/access-denied/page.tsx` | Host shell | Workspace member | Links back to personal | **Stay** |
| `/host/onboarding` | Become-a-host signup | Prospective host | `…/onboarding/page.tsx` | **No** workspace sidebar | Auth; redirects if already host | Dashboard “Become a host” CTA | **Stay** — first-time only |
| `/host/roadmap` | Launch checklist | Owner / editors | `…/roadmap/page.tsx` | Host shell | `events.edit` / `events.create` / `team.invite`; hidden for desk/read-only | — | **Stay** |
| `/host/desk` | Host-wide scanner / pickup queue | Desk staff / owner | `…/desk/page.tsx` | Host shell | Workspace member; useful with scan perms | Not buyer tickets | **Stay** — desk landing |
| `/host/support` | CTA into platform `/support` inbox | Host / messaging staff | `…/support/page.tsx` | Host shell (nav → `/support`) | Workspace member | Account support is separate | **Stay** |

#### 1.2.2 Events (`/host/events/*`)

| Route | Purpose | User type | Component / file | Sidebar / layout | Permissions | Overlap with dashboard | Disposition |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `/host/events` | Event list (table/list/grid) | Host / team with event view | `…/events/page.tsx` | Host shell | `canViewEvents` (view/edit/create or desk) | Buyer browses public `/events` | **Stay** |
| `/host/events/new` | Create event (Event Studio) | Host editor | `…/events/new/page.tsx` | Host shell | `events.create` / `events.edit` | — | **Stay** |
| `/host/events/[id]` | Event ops hub | Host / assigned staff | `…/events/[id]/page.tsx` | Host shell | Event view (+ per-tool gates) | — | **Stay** |
| `/host/events/[id]/edit` | Event Studio edit (`?step=`) | Host editor | `…/events/[id]/edit/page.tsx` | Host shell | `events.edit` / create | — | **Stay** |
| `/host/events/[id]/preview` | Host preview of public page | Host | `…/events/[id]/preview/page.tsx` | **No** workspace sidebar | Active workspace | Public `/events/[slug]` | **Stay** |
| `/host/events/[id]/tickets` | Ticket tier builder | Host editor | `…/tickets/page.tsx` | Host shell | Event edit / ticket manage | Buyer `/dashboard/tickets` | **Stay** |
| `/host/events/[id]/check-in` | Door QR scanner | Scanner / owner | `…/check-in/page.tsx` | Host shell | `tickets.scan_qr` / `tickets.check_in` | Buyer shows QR | **Stay** |
| `/host/events/[id]/check-in/analytics` | Check-in stats | Host / scanner analytics | `…/check-in/analytics/page.tsx` | Host shell | Scan or event analytics | — | **Stay** |
| `/host/events/[id]/offline-check-in` | Offline scan buffer | Scanner | `…/offline-check-in/page.tsx` | Host shell | Scan perms | — | **Stay** |
| `/host/events/[id]/attendees` | Attendee search + staff assign | Host / desk | `…/attendees/page.tsx` | Host shell | Event view / desk | Buyer ticket list | **Stay** |
| `/host/events/[id]/analytics` | Per-event analytics | Host analyst | `…/analytics/page.tsx` | Host shell | Analytics / event view | — | **Stay** |
| `/host/events/[id]/ai` | Event-scoped AI drafts | Host | `…/ai/page.tsx` | Host shell | Studio-style grants (`events.edit` / create / …) | — | **Stay** |
| `/host/events/[id]/ambassadors` | Per-event Ambassadors enable | Host | `…/ambassadors/page.tsx` | Host shell | Ambassadors / events.edit | Fan `/dashboard/ambassador` | **Stay** |
| `/host/events/[id]/tables` | Table / seat assignment | Host editor | `…/tables/page.tsx` | Host shell | Event edit | — | **Stay** |
| `/host/events/[id]/bundles` | Ticket + merch bundles | Host | `…/bundles/page.tsx` | Host shell | Merch / event edit | Buyer cart/checkout | **Stay** |
| `/host/events/[id]/post-event-drops` | Post-event merch drops | Host | `…/post-event-drops/page.tsx` | Host shell | Merch grants | — | **Stay** |
| `/host/events/[id]/memory` | Event Memory overview | Host | `…/memory/page.tsx` | Host shell | Studio-style grants | Public memories | **Stay** |
| `/host/events/[id]/memory/edit` | Edit recap + gallery | Host | `…/memory/edit/page.tsx` | Host shell | Studio-style grants | — | **Stay** |
| `/host/events/[id]/merch` | Legacy → merchandise | — | `…/merch/page.tsx` + next.config 308 | N/A | — | — | **Redirect** → `…/merchandise` |
| `/host/events/[id]/merchandise` | Merch Studio for event | Host / merch staff | `…/merchandise/page.tsx` | Host shell | Merch view/create/edit or scan | Buyer merch wallet | **Stay** |
| `/host/events/[id]/merchandise/new` | Create product | Host | `…/merchandise/new/page.tsx` | Host shell | Merch create/edit | — | **Stay** |
| `/host/events/[id]/merchandise/[merchId]/edit` | Edit product | Host | `…/merchandise/[merchId]/edit/page.tsx` | Host shell | Merch edit | — | **Stay** |
| `/host/events/[id]/merchandise/orders` | Event merch orders | Host / staff | `…/merchandise/orders/page.tsx` | Host shell | Merch view / desk | Buyer orders | **Stay** |
| `/host/events/[id]/merchandise/fulfillment` | Pickup desk | Merch desk | `…/merchandise/fulfillment/page.tsx` | Host shell | Merch scan / `merch.view` | Buyer pickup QR | **Stay** |

#### 1.2.3 Merchandise (host-global)

| Route | Purpose | User type | Component / file | Sidebar / layout | Permissions | Overlap with dashboard | Disposition |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `/host/merchandise` | Merch across all events | Host / merch staff | `…/merchandise/page.tsx` | Host shell | Merch view/create/edit or scan | Buyer `/dashboard/merchandise` | **Stay** |
| `/host/merchandise/new` | Create merch (pick event) | Host | `…/merchandise/new/page.tsx` | Host shell | Merch create/edit | — | **Stay** |
| `/host/merchandise/[id]/edit` | Edit product | Host | `…/merchandise/[id]/edit/page.tsx` | Host shell | Merch edit | — | **Stay** |
| `/host/merchandise/discounts` | Merch discount codes | Host | `…/discounts/page.tsx` | Host shell | Merch manage | — | **Stay** |
| `/host/merchandise/size-charts` | Size chart library | Host | `…/size-charts/page.tsx` | Host shell | Merch | — | **Stay** |
| `/host/merchandise/shipping-zones` | Flat shipping zones | Host | `…/shipping-zones/page.tsx` | Host shell | Merch | — | **Stay** |
| `/host/merchandise/revenue` | Merch revenue splits | Host | `…/revenue/page.tsx` | Host shell | Merch / finance view | — | **Stay** |
| `/host/merchandise/stock-alerts` | Stock alert inbox | Host | `…/stock-alerts/page.tsx` | Host shell | Merch | — | **Stay** |
| `/host/merchandise/reviews` | Product review reply inbox | Host | `…/reviews/page.tsx` | Host shell | Merch; hosts **cannot** delete reviews | Buyer write reviews | **Stay** |
| `/host/merchandise/print-on-demand` | POD jobs / integrations | Host | `…/print-on-demand/page.tsx` | Host shell | Merch | — | **Stay** |

#### 1.2.4 Growth — Ambassadors, sponsorships, audience, promos

| Route | Purpose | User type | Component / file | Sidebar / layout | Permissions | Overlap with dashboard | Disposition |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `/host/ambassadors` | Ambassador partners overview | Host | `…/ambassadors/page.tsx` | Host shell | Ambassadors view/create/edit or events.edit | Fan Ambassadors area | **Stay** |
| `/host/ambassadors/[id]` | Partner performance | Host | `…/ambassadors/[id]/page.tsx` | Host shell | Same | — | **Stay** |
| `/host/ambassadors/campaigns` | Campaign list | Host | `…/campaigns/page.tsx` | Host shell | Same | Fan enrollments | **Stay** |
| `/host/ambassadors/campaigns/new` | Create campaign | Host | `…/campaigns/new/page.tsx` | Host shell | `create_campaigns` / events.edit | — | **Stay** |
| `/host/ambassadors/campaigns/[id]` | Campaign detail + leaderboard | Host | `…/campaigns/[id]/page.tsx` | Host shell | Ambassadors view+ | Fan leaderboard | **Stay** |
| `/host/ambassadors/conversions` | Conversion ledger + reward actions | Host / reward perms | `…/conversions/page.tsx` | Host shell | view_conversions + reward flags | Fan earnings (buyer view) | **Stay** |
| `/host/ambassadors/payouts` | Ambassador payout summary (host-owned) | Host | `…/ambassadors/payouts/page.tsx` | Host shell | `view_payouts` / mark paid / finance | Fan `/dashboard/ambassador/payouts` | **Stay** |
| `/host/sponsorships` | Sponsor slots + inquiries | Host / sponsor mgr | `…/sponsorships/page.tsx` | Host shell | `sponsors.view` / `manage_slots` | Public `/sponsors` | **Stay** |
| `/host/sponsorships/new` | Create slot | Host | `…/sponsorships/new/page.tsx` | Host shell | manage_slots | — | **Stay** |
| `/host/sponsorships/[id]/edit` | Edit slot | Host | `…/sponsorships/[id]/edit/page.tsx` | Host shell | manage_slots | — | **Stay** |
| `/host/audience` | Audience CRM + segments | Host | `…/audience/page.tsx` | Host shell | `events.view` / `analytics.view_events` | Buyer following | **Stay** |
| `/host/followers` | Follower list | Host | `…/followers/page.tsx` | Host shell | Same as audience | `/dashboard/following` | **Stay** |
| `/host/announcements` | Announcement history | Host | `…/announcements/page.tsx` | Host shell | Studio-style grants | Messages | **Stay** |
| `/host/announcements/new` | Create announcement | Host | `…/announcements/new/page.tsx` | Host shell | Same | — | **Stay** |
| `/host/promos` | Ticket promo codes | Host | `…/promos/page.tsx` | Host shell (deep link) | Studio-style grants | Merch discounts separate | **Stay** |
| `/host/reviews` | Host review reply / report inbox | Host | `…/reviews/page.tsx` | Host shell (deep link) | Studio-style grants | Buyer `/dashboard/reviews` | **Stay** |

#### 1.2.5 Legacy Page + Vault studio

| Route | Purpose | User type | Component / file | Sidebar / layout | Permissions | Overlap with dashboard | Disposition |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `/host/legacy` | Legacy Studio overview | Host | `…/legacy/page.tsx` | Host shell | Studio-style grants | Public `/@username` | **Stay** |
| `/host/legacy/edit` | Identity / CTAs / contact | Host | `…/legacy/edit/page.tsx` | Host shell | Same | Host settings fields | **Stay** |
| `/host/legacy/content` | Content blocks + vault preview config | Host | `…/legacy/content/page.tsx` | Host shell | Same | Vault | **Stay** |
| `/host/legacy/preview` | Full public preview | Host | `…/legacy/preview/page.tsx` | Host shell | Same | Public Legacy | **Stay** |
| `/host/legacy/tier` | Tier progress | Host | `…/legacy/tier/page.tsx` | Host shell | Same | — | **Stay** |
| `/host/vault` | Vault Studio dashboard | Host | `…/vault/page.tsx` | Host shell | Studio-style grants | Buyer Vault library | **Stay** |
| `/host/vault/new` | Create drop | Host | `…/vault/new/page.tsx` | Host shell | Same | — | **Stay** |
| `/host/vault/[id]` | Drop detail hub | Host | `…/vault/[id]/page.tsx` | Host shell | Same | Buyer item view | **Stay** |
| `/host/vault/[id]/edit` | Edit drop + access rules | Host | `…/vault/[id]/edit/page.tsx` | Host shell | Same | — | **Stay** |
| `/host/vault/[id]/preview` | Locked vs owner preview | Host | `…/vault/[id]/preview/page.tsx` | Host shell | Same | Public vault item | **Stay** |
| `/host/vault/preview` | Studio catalog preview | Host | `…/vault/preview/page.tsx` | Host shell | Same | Public catalog | **Stay** |
| `/host/vault/earnings` | Vault unlock earnings | Host | `…/vault/earnings/page.tsx` | Host shell | Same / finance view | Host payouts | **Stay** |
| `/host/vault/subscriptions` | Subscriber list (host) | Host | `…/vault/subscriptions/page.tsx` | Host shell | Same | Buyer my subscriptions | **Stay** |

#### 1.2.6 Team, messages, analytics, finance, settings, AI, templates

| Route | Purpose | User type | Component / file | Sidebar / layout | Permissions | Overlap with dashboard | Disposition |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `/host/team` | Team overview | Host owner / team mgr | `…/team/page.tsx` | Host shell | `RequireHostTeamManage` (`team.view` / invite / edit / remove) | Buyer `/dashboard/team` (workspace picker) | **Stay** — different “Team” meaning |
| `/host/team/members` | Accepted members | Same | `…/team/members/page.tsx` | Host shell | Team manage | — | **Stay** |
| `/host/team/invites` | Pending invites | Same | `…/team/invites/page.tsx` | Host shell | Team manage | Invite accept at `/team/invite/[token]` | **Stay** |
| `/host/team/audit-log` | Team + desk audit | Same | `…/team/audit-log/page.tsx` | Host shell | Team manage | — | **Stay** |
| `/host/team/[id]` | Member role / scope / perms | Same | `…/team/[id]/page.tsx` | Host shell | Team manage | — | **Stay** |
| `/host/messages` | Host inbox | Host / messaging staff | `…/messages/page.tsx` | Host shell | `messages.view` / `reply` | Buyer inbox | **Stay** |
| `/host/messages/[threadId]` | Thread detail | Same | `…/messages/[threadId]/page.tsx` | Host shell | Same | Buyer thread | **Stay** |
| `/host/messages/settings` | Host messaging prefs / auto-reply | Same | `…/messages/settings/page.tsx` | Host shell | Same | Buyer message settings | **Stay** |
| `/host/messages/notifications` | Host message notifications | Same | `…/messages/notifications/page.tsx` | Host shell | Same | Account notification settings | **Stay** |
| `/host/analytics` | Portfolio analytics | Host analyst | `…/analytics/page.tsx` | Host shell | `analytics.view_*` | — | **Stay** |
| `/host/payouts` | Host balance + payout requests | **Owner only** | `…/payouts/page.tsx` | Host shell (deep link) | `RequireHostOwner` | Fan ambassador payouts | **Stay** |
| `/host/bank-accounts` | Saved payout accounts | **Owner only** | `…/bank-accounts/page.tsx` | Host shell (deep link) | `RequireHostOwner` | — | **Stay** |
| `/host/bank-accounts/[id]` | Bank account detail | **Owner only** | `…/bank-accounts/[id]/page.tsx` | Host shell | `RequireHostOwner` | — | **Stay** |
| `/host/settings` | Host profile, taxonomy, appearance | Host / team.view | `…/settings/page.tsx` | Host shell | `team.view` / `team.edit_permissions` | Account `/dashboard/settings` | **Stay** |
| `/host/settings/notifications` | Alias → account notification prefs | — | `…/settings/notifications/page.tsx` + next.config 308 | N/A | — | Canonical on dashboard | **Redirect** / **Alias** → `/dashboard/settings/notifications` |
| `/host/templates` | Event template library | Host | `…/templates/page.tsx` | Host shell (deep link) | Studio-style grants | — | **Stay** |
| `/host/templates/[id]` | Template detail | Host | `…/templates/[id]/page.tsx` | Host shell | Same | — | **Stay** |
| `/host/ai` | Host AI Copilot | Host | `…/ai/page.tsx` | Host shell (deep link) | Studio-style / `ai.use_own` | Event AI | **Stay** |

**Host route count:** 88 `page.tsx` files under `frontend/src/app/host/**` (including aliases/redirects).

---

### 1.3 Cross-workspace overlap map (labels / concepts — not data merge)

| Concept | Personal (`/dashboard`) | Host (`/host`) | Unification note |
| --- | --- | --- | --- |
| Home | `/dashboard` | `/host` | Two mode homes; switch via workspace chrome |
| Tickets | My tickets + QR | Desk / check-in / tiers | Rename chrome: “My tickets” vs “Tickets & Entry” |
| Merch | My merch / cart | Merch studio / fulfillment | Keep separate; clarify labels |
| Messages | Fan inbox | Host inbox | Keep separate; same thread rules by role |
| Team | Joined/owned workspaces picker | Host staff management | Highest naming collision — disambiguate |
| Vault | Unlocks / subscriptions | Vault Studio | Keep separate |
| Ambassadors | Promote & earn | Campaigns / conversions | Keep separate |
| Reviews | My reviews | Reply inbox | Keep separate (hosts cannot delete) |
| Settings | Account profile + notifications | Host profile | Notifications already shared (redirect) |
| Following / Followers | Following hosts | Follower CRM | Inverse views — keep |

---

### 1.4 Disposition summary

| Disposition | Count (approx.) | Examples |
| --- | --- | --- |
| **Stay** | Vast majority | All primary personal tools; all host ops tools |
| **Alias** | Few | `/host/dashboard` → `/host`; `/dashboard/connect/*` → `/connect/*` |
| **Redirect** | Few | `/dashboard/merch` → merchandise; `/host/events/[id]/merch`; `/host/settings/notifications` |
| **Merge (chrome only)** | Entry points | Workspace switcher vs `/dashboard/team` vs `/workspaces`; shared notification settings |
| **Move (defer)** | None recommended now | Do **not** nest `/host` under `/dashboard` or invent `/app/*` yet |

---

### 1.5 Unification recommendation (navigation only)

1. **Keep route prefixes:** `/dashboard` = Personal mode, `/host` = Host workspace mode.  
2. **Unify chrome:** one persistent workspace switcher (Personal ↔ Host: {name}); stop treating Dashboard/Host as peer marketing nav items inside workspace paths.  
3. **Align Host landings** to `hostHomePathForWorkspace()` (not hardcoded `/host/events`).  
4. **Rename colliding labels** in nav copy; do not merge datasets.  
5. **Do not move or delete routes** in the next implementation phase — only chrome, naming, and entry alignment.

---

## 2. Compare `/dashboard` vs `/host`

Side-by-side product comparison. **Do not merge buyer data into host views (or vice versa).** The gap is navigation, layout identity, and workspace switching.

### 2.1 `/dashboard` — Personal / buyer workspace

| Question | Answer today |
| --- | --- |
| **What it is for** | The authenticated **personal account** surface: attend events, hold tickets, buy merch, manage refunds, Fan Passport / Vault unlocks, Fan Connect, promote as an Ambassador, and edit account settings. |
| **What it shows today (home)** | `frontend/src/app/dashboard/page.tsx` — eyebrow **Attendee**; greeting by name; copy “fan workspace”; metric cards for Tickets / Orders / Passport; account card with email + roles; CTAs: Browse events, Host workspace / Become a host, optional Support / Admin. |
| **Navigation / sidebar** | `buyerNav` / `buyerNavGroups` in `frontend/src/lib/nav/workspace.ts`. Sidebar title: **Personal**. Groups: **Home** (Overview, Alerts) · **Activity** (Tickets, Orders, Merch, Refunds) · **Community** (Messages, **Workspaces**, Connect, Following) · **Identity** (Passport, Badges, Vault, Reviews) · **Earn** (Ambassadors) · **Account** (Settings). Mobile: `DashboardTopbar` drawer (same groups). Toolbar: always-on `WorkspaceSwitcher`. |
| **Layout shell** | `RequireAuth` → `HostWorkspaceProvider` → `WorkspaceShell` (`frontend/src/app/dashboard/layout.tsx`). Page bodies use `DashboardShell` for in-page headers. |
| **User types** | Any signed-in user: **buyer / attendee / fan** by default. Also dual-role users who are also host owners, host staff, or Ambassadors — they still use `/dashboard` for *personal* tools. |
| **Buyer / fan / account features** | Tickets + transfer + QR · Orders + receipts · Merch wallet + cart · Refunds · Messages (fan side) · Fan Connect (via `/dashboard/connect` → `/connect/*`) · Following · Passport + badges · Vault library + subscriptions · Own reviews · Ambassador promote & earn · Account settings + notification prefs · Alerts inbox · Team = *list of host workspaces I own/joined* (bridge out to `/host`). |

### 2.2 `/host` — Host / team / business workspace

| Question | Answer today |
| --- | --- |
| **What it is for** | The authenticated **host business** surface for a selected host org: create and run events, door/merch desk, merch studio, Ambassadors campaigns, sponsorships, audience CRM, Legacy Page + Vault studio, analytics, team, payouts. |
| **What it shows today (home)** | `frontend/src/app/host/page.tsx` — **Owner:** `OwnerCommandCenter` (readiness, today’s ops, sales snapshot, upcoming events, pending tasks, quick actions). **Team member:** `MemberDeskOverview` (desk/scanner/pickup or read-only workspace card). Canonical path `/host`; `/host/dashboard` is a 308 alias. |
| **Navigation / sidebar** | `hostNav` filtered by `navGroupsForWorkspace()` / `navForWorkspace()` (`frontend/src/lib/nav/host-nav.ts`). Sidebar title: **Host: {display_name}**. Groups: **Home** (Overview, Roadmap) · **Operate** (Events, Tickets & Entry, Merch Studio, Host Inbox) · **Grow** (Ambassador Campaigns, Sponsorships, Audience CRM, Legacy Page, Vault Studio) · **Manage** (Analytics, Host Team, Host Settings, Support → `/support`). Paths unchanged. Desk-focused staff get a minimal Operate set. Deep links off-sidebar: payouts, bank accounts, promos, templates, AI, announcements, followers, etc. Toolbar: always-on `WorkspaceSwitcher`. |
| **Layout shell** | Same `WorkspaceShell` component as dashboard, via `HostShell` in `frontend/src/app/host/layout.tsx`, plus `HostAccessGuard`. **Exceptions (no sidebar):** `/host/onboarding`, `/host/events/[id]/preview`. |
| **User types** | **Host owner**; **host team** roles (admin, event manager, scanner, merch staff, sponsor manager, viewer, etc.); event-scoped staff. Not for pure buyers until they onboard or accept an invite. Landing path is role-aware (`hostHomePathForWorkspace`: owner → `/host`, desk → `/host/desk`, sponsor mgr → `/host/sponsorships`, …). |
| **Host / team / business features** | Events + Event Studio · Desk / check-in / fulfillment · Merch studio + shipping/discounts/revenue · Host messages · Ambassadors campaigns + conversions · Sponsorships · Audience + followers + announcements · Legacy studio · Vault studio + earnings · Analytics · Team members/invites/audit · Host settings · Owner payouts + bank accounts · Promos, templates, AI · Support entry. |

### 2.3 Side-by-side snapshot

| Dimension | `/dashboard` | `/host` |
| --- | --- | --- |
| Product job | “My stuff as a fan / buyer” | “Run my event business / help a host” |
| Home tone | Soft attendee greeting + personal metrics | Operational Command Center or desk |
| Sidebar title | **Buyer** | **Host** |
| Switcher option label | **Personal account** | **Host workspace: {name}** |
| SiteHeader link label | **Dashboard** | **Host** |
| Home page eyebrow | **Attendee** | Owner/team operational chrome |
| Data scope | Current user as consumer | Active `host_id` as producer |
| Gate | `RequireAuth` | `RequireAuth` + workspace + `RequireHost` / path perms |

### 2.4 Same layout shell?

**Yes — same shell component, different config.**

| Shared | Differs by mode |
| --- | --- |
| `WorkspaceShell` | `nav` / `navGroups` (buyer vs host) |
| `DashboardSidebar` + `DashboardTopbar` | `title` (“Buyer” vs “Host”) |
| `WorkspaceBreadcrumbs` | `homeHref` (`/dashboard` vs role-aware `/host`…) |
| `HostWorkspaceProvider` on both | Host adds `HostAccessGuard`; onboarding/preview skip shell |
| `WorkspaceSwitcher` on both (when workspaces exist) | Select value: Personal vs active host |

They look like one design system. They feel like two products because of **labels, SiteHeader, and entry points**, not because the chrome components are different.

### 2.5 Duplicated UI (same patterns / parallel screens)

Not the same data — parallel *UI jobs* that read as twins:

| Pattern | Personal | Host |
| --- | --- | --- |
| Overview home | Metric cards + CTAs | Command Center / desk overview |
| Inbox | `/dashboard/messages*` | `/host/messages*` |
| Vault | Library / unlocks | Studio / drops / earnings |
| Merch | Wallet / pickup QR | Catalog / fulfillment desk |
| Ambassadors | Promote & earn | Campaigns / conversions / host payouts |
| Reviews | My reviews | Reply inbox |
| Settings | Account profile | Host profile |
| Notifications | Account prefs (canonical) | Redirects into personal prefs |
| Workspace chooser UI | `/dashboard/team`, `/dashboard/team/workspaces` | Switcher + `/workspaces` |

**Also duplicated chrome:** `WorkspaceSwitcher` appears in the sidebar *and* again inside `CommandCenterHeader` on the host owner home.

### 2.6 Duplicated nav item labels

Exact or near-exact sidebar labels on **both** sides (different hrefs):

| Label | Personal href | Host href |
| --- | --- | --- |
| Overview | `/dashboard` | `/host` |
| Merch | `/dashboard/merch` → merchandise | `/host/merchandise` |
| Messages | `/dashboard/messages` | `/host/messages` |
| Team | `/dashboard/team` | `/host/team` |
| Vault | `/dashboard/vault` | `/host/vault` |
| Ambassadors | `/dashboard/ambassador` | `/host/ambassadors` |
| Settings | `/dashboard/settings` | `/host/settings` |

Near-duplicates:

| Personal | Host |
| --- | --- |
| Tickets | Tickets & Entry |
| Reviews | (host reviews mostly deep-linked) |
| Following | Audience / Followers |

### 2.7 Confusing top nav labels (`SiteHeader`)

Logged-in header (`frontend/src/components/layout/SiteHeader.tsx`) adds peer links next to public marketing nav:

| Label | Destination | Confusion |
| --- | --- | --- |
| **Dashboard** | `/dashboard` | Sounds like “the app,” not “Personal.” Conflicts with product language “Personal account” / sidebar “Buyer” / home “Attendee.” |
| **Host** | `/host/events` (if host/staff) or `/host/onboarding` | Sounds like a second product. Lands on **Events list**, not role-aware home (`/host` or `/host/desk`). Competes with switcher and with public **Hosts** marketplace link (`/hosts`). |
| **Create event** | Always prominent CTA | Host-biased while user may be in Personal mode. |

Public **Hosts** (`/hosts`) vs private **Host** workspace is an easy mis-click for new users.

### 2.8 Confusing sidebar labels

| Issue | Detail |
| --- | --- |
| Sidebar title **Buyer** | Technical commerce term; home says Attendee/fan; switcher says Personal account. |
| Sidebar title **Host** | Correct domain, but doesn’t show *which* host org until you read the switcher. |
| **Team** | Personal = “workspaces I belong to”; Host = “staff I manage.” Highest collision. |
| **Merch / Vault / Messages / Ambassadors / Settings** | Same words, opposite ownership (consume vs operate). |
| **Tickets** vs **Tickets & Entry** | Better than identical, but still ticket-adjacent without mode chrome. |
| Breadcrumb root | Uses shell `title` (“Buyer” / “Host”), not “Personal” or host display name. |

### 2.9 Where “Dashboard” and “Host” compete

| Touchpoint | How they compete |
| --- | --- |
| SiteHeader | Two equal destination links → two apps |
| URL language | `/dashboard` vs `/host`; docs also say “host dashboard” meaning `/host` |
| Alias `/host/dashboard` | Reinforces “dashboard” as a host word too |
| Home CTAs | Personal home offers “Host workspace”; host errors offer “Back to dashboard” |
| Login → `/workspaces` | Chooser says Personal vs Host workspace — good — then header reverts to Dashboard vs Host |
| Create event CTA | Global header always pushes host creation even on personal routes |

**Net effect:** Users are asked to pick a *product* (Dashboard vs Host), not a *mode* of one Pàdéyá workspace.

### 2.10 Is Personal ↔ Host switching clear?

| Signal | Status |
| --- | --- |
| Mental model in `/workspaces` | **Clear** — “Personal account” vs “Host workspace: {Name}” |
| `WorkspaceSwitcher` copy | **Clear** when visible — same Personal / Host workspace labels |
| Switcher visibility | **Weak** — returns `null` if `workspaces.length === 0`; personal-only users never see the model |
| Switcher placement | **Weak** — buried in sidebar (desktop) / top strip (mobile); easy to miss vs SiteHeader |
| SiteHeader | **Undermines** switcher — parallel Dashboard/Host links with different destinations |
| Landing consistency | **Unclear** — switcher → `hostHomePathForWorkspace`; header Host → `/host/events` |
| Dual-role users | **Overloaded** — switcher + `/dashboard/team` + `/workspaces` + header + in-page CTAs |
| Active host shown in chrome | **Partial** — only inside the select; sidebar title stays generic “Host” |

**Verdict:** Switching is **implemented but not clear**. The switcher is the right control; the header and naming make Personal and Host feel like competing products instead of one workspace with two modes.

### 2.11 Comparison verdict

| Finding | Verdict |
| --- | --- |
| Same layout shell? | **Yes** (`WorkspaceShell` + shared sidebar/topbar) |
| Same product job? | **No** — consumer vs producer; keep data separate |
| Feel like one workspace today? | **No** — peer “Dashboard” / “Host” nav + inconsistent naming |
| Highest-friction duplicates | Team, Merch, Messages, Vault, Ambassadors, Settings labels; SiteHeader peer links |
| Clearest existing language to standardize on | **Personal account** ↔ **Host workspace: {name}** (from switcher / `/workspaces`) |

---

## 3. Recommend unification strategy

**Constraint (this phase):** Improve navigation, layout identity, workspace switching, and route *strategy* — without mixing buyer and host data, and without requiring a large URL migration.

### 3.1 Options evaluated

#### Option A — Unified shell, keep routes

| Piece | Proposal |
| --- | --- |
| Routes | Keep `/dashboard` = Personal account; keep `/host` = Host workspace |
| Shell | One shared `WorkspaceShell` (already shipped) |
| Switcher | Persistent control: **Personal account** · **Host: {display_name}** (e.g. Host: DJ Maze) |
| Top nav “Dashboard” | Opens last-used workspace **or** `/workspaces` chooser — not a second product |
| Top nav “Host” | Becomes “Switch to Host” **or** is removed when the switcher is always visible |

**Pros**

- Matches code that already exists (`WorkspaceShell`, `WorkspaceSwitcher`, `HostWorkspaceProvider`, `/workspaces`, `POST /me/active-workspace`).
- Zero deep-link / bookmark / email / invite URL breakage for host ops and buyer tickets.
- Keeps permission model obvious: `/host/*` remains host-gated; `/dashboard/*` remains account-scoped.
- Fixes the *feeling* of two products (chrome + naming + entry points) without pretending data should merge.
- Aligns with [HOST_AREA_AUDIT.md](./HOST_AREA_AUDIT.md) canonical `/host` Command Center.

**Cons**

- URLs still say `/dashboard` and `/host` (not `/workspace/...`) — fine if chrome language is consistent.
- Requires discipline: SiteHeader must stop competing with the switcher.
- Dual-role users still have two trees — intentional; must be labeled clearly.

**Risk:** Low. **Migration:** Chrome/copy/entry only.

---

#### Option B — `/dashboard` becomes root for all workspaces

| Piece | Proposal |
| --- | --- |
| Routes | `/dashboard` = Personal; `/dashboard/host` = Command Center; `/dashboard/host/events`, … |
| Redirects | `/host` → `/dashboard/host` (and subtree) |

**Pros**

- Single URL prefix can feel “one app.”
- Personal remains the linguistic root.

**Cons**

- High migration: 88 host pages, docs, emails, QR deep links, team invites, smoke tests, API “host area” mental model.
- Nesting host under “dashboard” reintroduces the word that already confuses Personal vs Host Command Center.
- Blurs permission boundaries in the URL (`/dashboard/...` no longer means “buyer-safe”).
- Reworks `canAccessHostPath`, breadcrumbs, nav hrefs, and every hard-coded `/host/...` link.

**Risk:** High. **Migration:** Large redirect matrix + long dual-URL period. **Not justified** when Option A already shares the shell.

---

#### Option C — One `/workspace` route family

| Piece | Proposal |
| --- | --- |
| Routes | `/workspace/personal`, `/workspace/host/[hostId]`, … |
| Redirects | `/dashboard` and `/host` → new tree |

**Pros**

- Cleanest long-term IA vocabulary (“workspace” everywhere).
- Host id in the path can make multi-host switching explicit.

**Cons**

- Highest migration cost (buyer + host + Connect aliases + docs).
- `hostId` in every path complicates sharing, caching, and “active workspace” already persisted server-side.
- Overlaps `/workspaces` chooser naming.
- Does not buy more product clarity than a good switcher if shell is already unified.

**Risk:** Highest. **Defer** until after Option A ships and still feels insufficient.

---

#### Option D — Keep separate, improve only top navigation

| Piece | Proposal |
| --- | --- |
| Routes / sidebars | Unchanged |
| Change | Tweak SiteHeader labels/links only |

**Pros**

- Lowest engineering cost; tiny PR surface.

**Cons**

- Leaves sidebar titles (Buyer vs Host), breadcrumb roots, buried/hidden switcher, colliding Team/Merch/Vault labels, and disagreeing landings (`/host/events` vs role home).
- Header-only fix still lets two sidebars feel like two products once you click in.
- Does not establish “Personal ↔ Host: {name}” as the durable model.

**Risk:** Lowest. **Upside:** Insufficient against the audit findings in §2.

---

### 3.2 Decision matrix

| Criterion | A | B | C | D |
| --- | --- | --- | --- | --- |
| Fixes “two products” feeling | Strong | Strong | Strong | Weak |
| Keeps buyer/host data separate | Yes | Yes | Yes | Yes |
| Reuses existing shell/switcher | Full | Partial | Rewrite | Partial |
| URL / deep-link risk | Low | High | Highest | None |
| Permission clarity in URL | High (`/host` gated) | Weaker | Medium | High |
| Aligns with shipped Command Center | Yes | Conflict | Conflict | Yes |
| Fits “no route moves yet” phase | Yes | No | No | Yes |
| Effort to first user-visible win | Small | Large | Very large | Tiny |

### 3.3 Recommendation: **Option A**

**Pick Option A — unified shell, keep `/dashboard` and `/host`.**

**Why (for Pàdéyá specifically)**

1. **The hard part is already built.** Both trees use `WorkspaceShell` + `HostWorkspaceProvider` + `WorkspaceSwitcher`. The product gap is identity and entry competition, not missing architecture.
2. **Route prefixes already encode the right split.** Personal consumer tools vs host business tools should not share one nested path; `/dashboard` vs `/host` is a feature for permissions and mental models, not a bug.
3. **B and C buy cosmetics with migration tax.** Nesting under `/dashboard/host` or inventing `/workspace/*` does not improve desk check-in, tickets, or payouts — it burns cycles on redirects while dual-role users still need a mode switcher.
4. **D is a bandage.** Top-nav-only changes cannot fix Buyer/Attendee/Personal naming drift or sidebar label collisions that make the two modes feel like different apps after entry.
5. **Option A matches the intended vocabulary already on `/workspaces`:** Personal account ↔ Host workspace: {Name}. Standardize the whole chrome on that pair; demote the word “Dashboard” from peer-product status.

### 3.4 Option A — target experience (no route moves)

| Surface | Target behavior |
| --- | --- |
| Workspace switcher | Always visible in workspace chrome when authenticated. Options: **Personal account**; each membership as **Host: {display_name}** (owner/role suffix ok). If no host workspaces: show Personal + **Become a host**. |
| Sidebar title / breadcrumb root | **Personal** on `/dashboard/*`; **Host: {display_name}** (or short host name) on `/host/*` — retire sidebar title **Buyer**. |
| SiteHeader on workspace paths | Do **not** show peer **Dashboard** + **Host** product links. Show current mode chip + switcher (or a single **Workspace** control). |
| SiteHeader “Dashboard” (if kept outside shells) | Prefer: open **last-used mode** (personal vs active host home via `hostHomePathForWorkspace`) **or** `/workspaces` when ambiguous / first login. Avoid implying a third destination. |
| SiteHeader “Host” | **Remove** when switcher is present; else label **Switch to Host** and land on `hostHomePathForWorkspace`, never hardcode `/host/events`. |
| Public nav | Keep **Hosts** (`/hosts` marketplace) distinct from private Host workspace. |
| Sidebars | Stay mode-pure (buyer nav vs host nav). Disambiguate colliding labels (Team → “My teams” vs “Host team”, etc.) in a follow-on polish pass. |
| Data | Never merge personal tickets/orders with host attendees/sales into one list. |

### 3.5 What we explicitly reject (for now)

| Reject | Reason |
| --- | --- |
| Option B (`/dashboard/host/...`) | High redirect cost; weakens “dashboard = personal” signal; unnecessary given shared shell |
| Option C (`/workspace/...`) | Highest migration; revisit only if A ships and IA still fails |
| Option D alone | Insufficient against §2 friction |
| One mega-sidebar mixing buyer + host tools | Mixes data domains; violates product constraint |
| Deleting `/dashboard` or `/host` | Out of scope; aliases/redirects only where already legacy |

### 3.6 Phased delivery under Option A

| Phase | Work | Routes |
| --- | --- | --- |
| **A1 — Vocabulary + landings** | Rename Buyer → Personal in shell titles/breadcrumbs; align all Host entries to `hostHomePathForWorkspace` | No moves |
| **A2 — Chrome switcher** | Elevate switcher; remove redundant Dashboard/Host peer links on workspace paths; always show Personal | No moves |
| **A3 — Label polish** | Disambiguate Team / Merch / Vault / Messages / Ambassadors / Settings nav copy | No moves |
| **A4 — Entry consolidation** | Soft-prefer switcher + `/workspaces`; demote duplicate CTAs (`/dashboard/team` as secondary) | Redirects only if needed later |

### 3.7 Success criteria

A user who is both a ticket holder and a host owner should be able to answer in under two seconds:

1. Am I in **Personal** or **Host: {name}**?
2. How do I switch?
3. Why are these sidebars different? → “Different tools for different jobs — same Pàdéyá account.”

If those three are obvious, Option A has succeeded without Option B/C migration.

---

## 4. Preferred product direction — codebase evaluation

### 4.1 Stated direction

**Option A — unified shell, keep routes.**

| Principle | Intent |
| --- | --- |
| Technical separation | `/dashboard` and `/host` stay separate for safety |
| User experience | One workspace via shared layout + workspace switcher |
| Risk | Lower than moving every route (Options B/C) |
| Compatibility | Old links remain safe |
| Permissions | Stay clean (`/host` gated; `/dashboard` account-scoped) |

**Target UX (product sketch)**

| Layer | Behavior |
| --- | --- |
| Top nav (public + entry) | Events · Ambassadors · Hosts · Fans · Sponsors · **Dashboard** |
| Top nav “Host” | Remove or reduce if it duplicates Dashboard / switcher |
| Inside workspace chrome | Switcher: **Personal account** · **Host: DJ Maze** |
| Personal selected | Buyer/fan sidebar + `/dashboard/*` tools |
| Host selected | Host/team sidebar + `/host/*` tools |
| Routes | Remain `/dashboard/*` and `/host/*` — feel like one workspace |

### 4.2 Codebase verdict: **Option A is best and already half-built**

Evaluated against current frontend structure. **Confirm Option A.**

| Preferred claim | Codebase evidence | Fit |
| --- | --- | --- |
| Keep `/dashboard` and `/host` separate for safety | Distinct app trees; host pages use `RequireHost` / `HostAccessGuard` / `canAccessHostPath`; buyer tree is `RequireAuth` only | **Strong** — do not nest host under `/dashboard` |
| One shared layout | Both layouts render `WorkspaceShell` (`dashboard/layout.tsx`, `host/layout.tsx`) with the same sidebar/topbar/breadcrumb components | **Strong** — already shared |
| Workspace switcher Personal ↔ Host | `WorkspaceSwitcher` already switches `router.push("/dashboard")` vs `hostHomePathForWorkspace` + `setActiveHostId`; labels close to target (“Personal account” / `Host workspace: {name}`) | **Strong** — needs polish + always-on visibility |
| Lower risk than route moves | No need to rewrite 41 + 88 pages, nav hrefs, emails, invites, or `canAccessHostPath` prefixes | **Strong** |
| Old links stay safe | URLs unchanged; existing 308 aliases (`/host/dashboard`, merch, notification prefs) remain valid | **Strong** |
| Permissions stay clean | Path-prefix gating + owner-only payouts/banks stay on `/host` | **Strong** |
| Top nav: single **Dashboard** entry | Today SiteHeader adds **both** `Dashboard` → `/dashboard` **and** `Host` → `/host/events` (or onboarding) | **Gap** — Host peer link is the main competitor |
| Switcher drives sidebar mode | Switching navigates between trees; each layout supplies `buyerNav` vs `navForWorkspace(active)` | **Strong** — mode = route prefix + nav config, not a fake single URL |

**Conclusion:** The preferred UX matches what the codebase was designed to do. Gaps are mostly **SiteHeader competition**, **switcher visibility/copy**, and **shell titles** — not missing route architecture. Options B/C would fight the existing permission and deep-link design.

### 4.3 Map preferred UX → current code

```
Preferred                          Today
─────────                          ─────
Top: Events…Sponsors               SiteHeader publicNav ✓
Top: Dashboard (workspace entry)   Label exists → always /dashboard
Top: (no Host peer)                Extra “Host” → /host/events ✗
Shell: WorkspaceShell              Shared component ✓
Switcher: Personal / Host: Name    Exists; “Host workspace: Name”; hidden if 0 hosts ✗
Personal → buyer sidebar           buyerNav + title “Buyer” ✓/rename
Host → host sidebar                navForWorkspace + title “Host” ✓
Routes /dashboard/* /host/*        Unchanged ✓
```

**Important clarification:** “Inside Dashboard shell” in the product sketch means **inside the authenticated workspace chrome** (`WorkspaceShell`), not “all host URLs live under `/dashboard`.” When Host is selected, the user is on `/host/*` with the **same shell component** and host nav — that is Option A, not Option B.

### 4.4 What already supports the preferred UX

| Building block | Location | Role in Option A |
| --- | --- | --- |
| `WorkspaceShell` | `frontend/src/components/layout/WorkspaceShell.tsx` | Single chrome for both modes |
| Buyer nav | `buyerNav` / `buyerNavGroups` in `lib/nav/workspace.ts` | Personal sidebar |
| Host nav | `hostNav` + `navGroupsForWorkspace` in `lib/nav/host-nav.ts` | Host sidebar (permission-filtered) |
| `WorkspaceSwitcher` | `components/hosts/WorkspaceSwitcher.tsx` | Mode switch + navigation |
| Active host persistence | `HostWorkspaceProvider`, `POST /me/active-workspace`, localStorage | Last host org remembered |
| Role-aware host home | `hostHomePathForWorkspace()` | Correct landing when switching to Host |
| Post-login chooser | `/workspaces` | First-time / multi-workspace pick |
| Workspace path helper | `isWorkspacePath` / `WORKSPACE_PREFIXES` | Header can treat `/dashboard` + `/host` as one chrome class |

### 4.5 Gaps vs preferred final UX (implementation checklist — not done yet)

| Gap | Current behavior | Preferred fix |
| --- | --- | --- |
| Peer **Host** top nav | Competes with Dashboard; lands on `/host/events` | **Remove** for users who can use the switcher; or demote to onboarding-only CTA for non-hosts |
| **Dashboard** top nav meaning | Always `/dashboard` | Workspace **entry**: last-used mode (Personal home or `hostHomePathForWorkspace`) and/or `/workspaces` when ambiguous |
| Switcher hidden | `if (workspaces.length === 0) return null` | Always show **Personal account**; empty host list → Become a host |
| Switcher label | `Host workspace: {name}` via `workspaceOptionLabel` | Prefer shorter **Host: {name}** (e.g. Host: DJ Maze) to match product sketch |
| Shell title | `"Buyer"` / `"Host"` | **Personal** / **Host: {name}** (breadcrumb root too) |
| Duplicate switcher on host home | Also in `CommandCenterHeader` | Keep one primary switcher in shell chrome |
| Public **Hosts** vs private Host | Both use “Host(s)” | Keep marketplace as **Hosts**; never reintroduce private peer **Host** next to it |
| Colliding sidebar labels | Team, Merch, Vault, … | Follow-on copy polish (Phase A3); not a reason to reject A |

### 4.6 Recommended top-nav policy (codebase-aligned)

| User state | Top nav after public links | Rationale |
| --- | --- | --- |
| Logged out | Events · Ambassadors · Hosts · Fans · Sponsors (+ Log in / Create event) | Unchanged marketing |
| Logged in, any role | … · **Dashboard** | Single entry into workspace chrome |
| Logged in, no host workspace | No **Host** peer; Dashboard → Personal; in-shell Become a host | Avoids fake second product |
| Logged in, has host workspace(s) | No **Host** peer; Dashboard → last-used Personal or Host home; switcher inside shell | Matches preferred sketch |
| Support / Admin | Keep Support / Admin as today | Separate privileged shells |

**Create event:** Keep as a primary CTA where product wants growth, but it should not replace workspace switching. Prefer it not fighting Personal mode (optional: only emphasize on host mode or marketing pages — product call later).

### 4.7 Safety check: why keeping routes matters in *this* repo

| Risk if we chose B/C instead | Why A wins here |
| --- | --- |
| `canAccessHostPath` and host-nav hrefs are `/host`-prefixed | Prefix rename = wide FE blast radius |
| Team invites, desk links, event ops, smoke docs point at `/host/...` | A leaves them valid |
| Buyer Connect aliases already bounce `/dashboard/connect` → `/connect` | A doesn’t reopen that migration |
| Notification prefs already canonicalize on `/dashboard/settings/notifications` | Shared account prefs stay on personal tree — correct under A |
| Owner-only finance stays off member sidebars via `/host/payouts` path rules | Nesting under `/dashboard/host` would muddy “dashboard = safe personal” |

### 4.8 Final evaluation answer

| Question | Answer |
| --- | --- |
| Is Option A best based on the codebase? | **Yes.** |
| Does the preferred UX match Option A? | **Yes** — with the clarification that host tools stay on `/host/*` inside the shared shell. |
| Should top nav keep both Dashboard and Host? | **No.** Keep **Dashboard** as workspace entry; **remove/reduce Host** so it doesn’t duplicate the switcher. |
| Is anything blocking A? | No architectural blocker. Work is chrome: header, switcher visibility/copy, shell titles, landings. |
| Should we move routes now? | **No.** |

**Product one-liner for Pàdéyá:** One account, one workspace chrome, two safe route trees — **Personal** tools on `/dashboard`, **Host: {name}** tools on `/host`, switched in-shell.

---

## 5. Workspace switcher audit

**Primary file:** `frontend/src/components/hosts/WorkspaceSwitcher.tsx`  
**Context:** `frontend/src/components/hosts/HostWorkspaceProvider.tsx`  
**Mounted in:** `dashboard/layout.tsx` and `host/layout.tsx` (toolbar); also duplicated in `CommandCenterHeader` on host owner home.

### 5.1 Where Personal account is defined

| Layer | Definition | Notes |
| --- | --- | --- |
| Switcher constant | `const PERSONAL = "personal"` in `WorkspaceSwitcher.tsx` | Client-only sentinel value for the `<select>` |
| UI label | Hard-coded option text: **Personal account** | Not loaded from API |
| Server model | **None** | Personal is not a row in `user_active_workspaces` |
| Selection rule | `value = PERSONAL` when `!pathname.startsWith("/host")` (or no active host on host surface) | Mode is inferred from **URL**, not from a stored “personal” flag |
| Destination | `router.push("/dashboard")` | Always personal home, not last personal deep link |

Personal account = “I am on the buyer/account route tree,” not a persisted workspace entity.

### 5.2 Where Host workspaces are defined

| Layer | Definition | Notes |
| --- | --- | --- |
| API | `GET /api/v1/me/team-workspaces` via `fetchHostWorkspaces()` | Owned + team + event-staff hosts |
| Type | `HostWorkspace` in `frontend/src/lib/types/host-workspace.ts` | `host_id`, `display_name`, `role`, `permissions`, `is_owner`, `is_active`, … |
| Backend list | `workspace_service.list_user_workspaces` + `is_active` from `user_active_workspaces` | `backend/app/teams/me_router.py` |
| Option label | `workspaceOptionLabel(w)` → `Host workspace: ${display_name}` | `frontend/src/lib/host-access.ts` |
| Extra suffix in switcher | ` (Owner)` or ` · {role_label}` | Appended in `WorkspaceSwitcher` JSX |
| Active host pick | `pickActive(workspaces, readActiveHostId())` | localStorage preferred → server `is_active` → owned → first |

### 5.3 Capability answers

| Question | Answer | Evidence |
| --- | --- | --- |
| Can `/dashboard` already show host workspaces in the switcher? | **Yes** | Dashboard layout wraps `HostWorkspaceProvider` + `toolbar={<WorkspaceSwitcher />}`; options map `workspaces` |
| Can `/host` already show Personal account in the switcher? | **Yes** | Same component; first `<option value="personal">Personal account</option>` |
| Can the switcher switch between `/dashboard` and `/host`? | **Yes** | Personal → `router.push("/dashboard")`; host → `setActiveHostId` + `router.push(hostHomePathForWorkspace(match))` |
| Does active **host** workspace persist? | **Yes** | `localStorage` key `padeya-active-host-id` + `POST /me/active-workspace` → table `user_active_workspaces` |
| Is **last-used mode** (Personal vs Host) stored? | **No** | Only last **host_id** is stored. Personal mode is purely “current path is not `/host/*`” |
| Is switching Personal → Host clear? | **Partially** | Works when switcher is visible; undermined by SiteHeader **Host** link, hidden switcher when `workspaces.length === 0`, and label/title drift (Buyer / Dashboard / Personal) |

### 5.4 Persistence detail

```
Selecting a Host workspace
  → setActiveHostId(hostId)
  → writeActiveHostId(hostId)          // localStorage: padeya-active-host-id
  → POST /me/active-workspace {host_id} // DB: user_active_workspaces
  → navigate to hostHomePathForWorkspace()

Selecting Personal account
  → router.push("/dashboard")
  → does NOT clear padeya-active-host-id
  → does NOT POST a “personal” active workspace
  → active host remains in provider memory for next Host switch (good)
```

| Stored | Key / table | Cleared on Personal? |
| --- | --- | --- |
| Active host id (client) | `padeya-active-host-id` | No — retained for return trip |
| Active host id (server) | `user_active_workspaces.host_id` | No — still last host org |
| Last surface mode | — | **Not implemented** |
| Last personal deep link | — | **Not implemented** (always `/dashboard`) |
| Last host deep link | — | **Not implemented** (always role home, not previous `/host/events/...`) |

`pickActive` order on load: localStorage host id (if still a member) → server `is_active` → owned host → first workspace.

### 5.5 Visibility & clarity issues

| Issue | Current behavior | Impact |
| --- | --- | --- |
| Hidden when no hosts | `if (loading \|\| workspaces.length === 0) return null` | Personal-only users never see the workspace model |
| Loading flash | Returns null while loading | Switcher pops in late |
| Duplicate control | Shell toolbar + `CommandCenterHeader` | Two switchers on owner `/host` |
| Competing top nav | SiteHeader **Host** → `/host/events` | Bypasses switcher + role-aware home |
| Select UI | Native `<select>` in sidebar | Easy to miss; weak on mobile vs peer header links |
| Value while on Personal | Shows Personal even if `active` host is still set in context | Correct UX; host preference quietly retained |
| Personal redirect | Always `/dashboard` overview | Loses deep personal page (e.g. tickets) — acceptable for v1 |

### 5.6 Related entry points (same data, parallel UI)

| Surface | Behavior |
| --- | --- |
| `/workspaces` | Card list: Personal account → `/dashboard`; each host → set active + role home |
| `/dashboard/team` | Lists owned/joined workspaces; opens host |
| `/dashboard/team/workspaces` | Explicit active-host picker |
| Login (no `next`) | If `workspaces.length > 0` → `/workspaces`; else → `/dashboard` |

These duplicate the switcher’s job and should stay secondary once the in-shell switcher is always clear.

### 5.7 Recommended switcher behavior (Option A)

Exact product rules for implementation later:

#### Behavior

1. **Mount** the switcher once in `WorkspaceShell` chrome (sidebar + mobile). Remove duplicate from `CommandCenterHeader` (or make header read-only current-mode chip).
2. **Always render** when authenticated inside `/dashboard` or `/host` (except onboarding/preview without shell).
3. **Options**
   - Always: **Personal account**
   - Then: one option per `HostWorkspace` from `/me/team-workspaces`
   - If zero hosts: still show Personal; below or as helper link **Become a host** → `/host/onboarding`
4. **Current value**
   - Path starts with `/host` and `active` set → that `host_id`
   - Else → Personal
5. **On change → Personal:** navigate to `/dashboard` (overview). Keep stored active `host_id` unchanged.
6. **On change → Host X:** `setActiveHostId(X)` (localStorage + `POST /me/active-workspace`), then navigate to `hostHomePathForWorkspace(X)` (owner `/host`, desk `/host/desk`, etc. — **not** hardcoded `/host/events`).
7. **Do not** merge personal and host sidebars; navigation swap happens because the route tree (and layout nav config) changes.

#### Exact labels

| Element | Label |
| --- | --- |
| Control group | **Workspace** (existing) |
| Personal option | **Personal account** |
| Host option | **Host: {display_name}** (e.g. `Host: DJ Maze`) |
| Owner suffix | optional ` (Owner)` |
| Member suffix | optional ` · {role_label}` |
| Empty-host helper | **Become a host** |
| Shell title / breadcrumb root (Personal) | **Personal** |
| Shell title / breadcrumb root (Host) | **Host: {display_name}** |

Deprecate chrome use of **Buyer** and long form **Host workspace:** in the switcher (keep “Host workspace” in long-form docs/chooser copy if useful).

#### Exact redirect behavior

| Action | Redirect |
| --- | --- |
| Switcher → Personal account | `/dashboard` |
| Switcher → Host: {name} | `hostHomePathForWorkspace(workspace)` |
| Become a host | `/host/onboarding` |
| Blocked host path | `/host/access-denied?from=…` (unchanged) |
| `/workspaces` → Personal | `/dashboard` |
| `/workspaces` → Host | same as switcher host redirect |

Optional later (not required for A1): remember last personal path / last host path per mode — out of scope until basic switcher clarity ships.

#### Top nav **Dashboard** → last-used workspace?

| Recommendation | Detail |
| --- | --- |
| **Yes — with a small addition** | Today only last **host** is stored, not last **mode**. To honor “Dashboard opens last-used workspace,” persist a client mode flag. |
| Proposed storage | e.g. `localStorage` `padeya-workspace-mode` = `"personal"` \| `"host"` updated whenever the switcher navigates (and when user lands deep via links). |
| Dashboard click algorithm | (1) If mode is `host` and user still has that host (or any host + stored host id valid) → `hostHomePathForWorkspace(active)`. (2) Else → `/dashboard`. (3) If never set and user has host workspaces → prefer `/workspaces` once, or default Personal — product choice; recommend **default Personal** after first login chooser. |
| If mode persistence deferred | Dashboard → `/dashboard` is acceptable for A1; remove peer **Host** link so Dashboard isn’t competing. Last-used host still applies when user opens switcher → Host. |
| Do **not** | Send Dashboard to `/host/events` unconditionally. |

**Phased recommendation**

| Phase | Top nav Dashboard | Mode persistence |
| --- | --- | --- |
| A1 | `/dashboard` + remove Host peer | Host id only (as today) |
| A2 | Last-used mode (personal vs host home) | Add `padeya-workspace-mode` |
| A3 | Optional: restore last deep link per mode | Extra keys if needed |

### 5.8 Switcher audit verdict

| Finding | Verdict |
| --- | --- |
| Personal defined? | Yes — client sentinel + URL inference; not a DB workspace |
| Hosts defined? | Yes — `/me/team-workspaces` + active host pref |
| Cross-show on both trees? | Yes — same switcher on `/dashboard` and `/host` |
| Cross-route switch? | Yes — already navigates both trees |
| Host persistence? | Yes — localStorage + server |
| Last-used **mode**? | No — needed for ideal top-nav Dashboard behavior |
| Clear enough today? | No — hidden empty state, header competition, label drift |
| Option A fit? | Excellent — finish the switcher; don’t move routes |

---

## 6. Proposed unified navigation

**Goal:** One sidebar chrome that **swaps config** when the workspace switcher changes mode — not one mega-menu mixing buyer and host tools.

### 6.1 Recommended Personal workspace sidebar

Mode: **Personal account** · Routes: `/dashboard/*` (Connect canonical under `/connect/*` via aliases)

| Group | Items | Canonical hrefs (today) |
| --- | --- | --- |
| **Home** | Overview · Alerts | `/dashboard` · `/dashboard/notifications` |
| **Activity** | Tickets · Orders · Merch · Refunds | `/dashboard/tickets` · `/dashboard/orders` · `/dashboard/merchandise` (nav may still say `/dashboard/merch` → redirect) · `/dashboard/refunds` |
| **Community** | Messages · Team · Connect · Following | `/dashboard/messages` · `/dashboard/team` · `/dashboard/connect` → `/connect` · `/dashboard/following` |
| **Identity** | Passport · Badges · Vault · Reviews | `/dashboard/passport` · `/dashboard/badges` · `/dashboard/vault` · `/dashboard/reviews` |
| **Growth** | Ambassadors | `/dashboard/ambassador` |
| **Account** | Settings | `/dashboard/settings` |

### 6.2 Recommended Host workspace sidebar

Mode: **Host: {display_name}** · Routes: `/host/*` (Support → `/support`)

| Group | Items | Canonical hrefs (today) |
| --- | --- | --- |
| **Home** | Overview · Roadmap | `/host` · `/host/roadmap` |
| **Operate** | Events · Tickets & Entry · Merch Studio · Host Inbox | `/host/events` · `/host/desk` · `/host/merchandise` · `/host/messages` |
| **Grow** | Ambassador Campaigns · Sponsorships · Audience CRM · Legacy Page · Vault Studio | `/host/ambassadors` · `/host/sponsorships` · `/host/audience` · `/host/legacy` · `/host/vault` |
| **Manage** | Analytics · Host Team · Host Settings · Support | `/host/analytics` · `/host/team` · `/host/settings` · `/support` |

**Off-sidebar (keep as deep links / Command Center):** payouts, bank accounts, promos, templates, AI, announcements, followers, per-event ops — unchanged from [HOST_AREA_AUDIT.md](./HOST_AREA_AUDIT.md).

**Host members:** continue filtering via `navGroupsForWorkspace()` / `canSeeNavHref` (desk staff = minimal Operate, etc.). Proposed structure is the **owner / full** tree; filtered subsets are derived, not a second IA.

### 6.3 Match to current codebase

| Proposed structure | Already in `lib/nav/workspace.ts`? |
| --- | --- |
| Personal groups + items (§6.1) | **Exact match** to `buyerNav` / `buyerNavGroups` |
| Host groups + items (§6.2) | **Exact match** to `hostNav` / `hostNavGroups` |

**No IA redesign required** for Option A navigation. Work is chrome identity (Personal vs Host: {name}), switcher, and top nav — not reinventing sidebar groups.

Minor hygiene (optional, same structure):

| Item | Note |
| --- | --- |
| Personal Merch nav href | Point primary nav at `/dashboard/merchandise` instead of legacy `/dashboard/merch` |
| Colliding labels | Structure can stay; optional copy polish later (e.g. Personal Team → “My teams”) without new groups |
| Support | Correctly leaves `/host` tree — keep as Manage item linking `/support` |

### 6.4 Same shared component with different nav config?

**Yes — recommend (and already implemented).**

| Layer | Shared? | Config that changes |
| --- | --- | --- |
| `WorkspaceShell` | Shared | `nav`, `navGroups`, `title`, `homeHref`, `toolbar` |
| `DashboardSidebar` | Shared | Renders whatever groups/items it receives |
| `DashboardTopbar` + drawer | Shared | Same |
| `WorkspaceNavSections` | Shared | Active state, favorites/collapse prefs scoped by workspace title |
| `buyerNav` / `hostNav` | **Separate configs** | Different hrefs + group ids |
| `navGroupsForWorkspace` | Host-only filter | Permissions / desk focus |
| Page routes / data | **Not shared** | Personal vs host trees stay separate |

```
WorkspaceShell(navConfig)
        │
        ├─ mode Personal → buyerNavGroups + title "Personal" + homeHref /dashboard
        │
        └─ mode Host     → navGroupsForWorkspace(active) + title "Host: {name}" + role homeHref
```

**Do not** build a second sidebar component for host. **Do not** concatenate personal + host items into one list. **Do** keep two nav configs and one renderer — that is the unified navigation model.

### 6.5 How the switcher drives the sidebar

| User selects | Navigation | Shell result |
| --- | --- | --- |
| Personal account | → `/dashboard` | Dashboard layout supplies `buyerNav*` |
| Host: DJ Maze | → `hostHomePathForWorkspace` | Host layout supplies filtered `hostNav*` |

The sidebar “changes based on selected workspace” because **layout + route prefix change**, not because a single page re-binds items in place. That keeps permissions (`HostAccessGuard`) and URL safety intact under Option A.

### 6.6 Label collision policy (structure unchanged)

Keep the proposed item names for parity with shipped nav. Disambiguation is **optional copy**, not structural:

| Both modes say | Personal clarification (optional) | Host clarification (optional) |
| --- | --- | --- |
| Merch | My merch | Merch (studio) — or keep Merch |
| Messages | Messages | Messages (host inbox) — or keep Messages |
| Team | My teams | Host team |
| Vault | My Vault | Vault studio — or keep Vault |
| Ambassadors | Ambassadors | Ambassadors |
| Settings | Settings | Host settings — or keep Settings |

Mode chrome (**Personal** vs **Host: DJ Maze**) does most of the disambiguation; rename only where user testing still confuses Team.

### 6.7 Unified navigation verdict

| Question | Answer |
| --- | --- |
| Adopt the proposed Personal / Host sidebars? | **Yes** — they are the current shipped IA |
| One shared sidebar component? | **Yes** — `WorkspaceShell` + `DashboardSidebar` / `WorkspaceNavSections` |
| Different nav config per workspace? | **Yes** — `buyerNav*` vs `hostNav*` (+ host permission filter) |
| Merge into one combined sidebar? | **No** |
| Move routes to make nav unified? | **No** — config + switcher + titles are enough |

**Product one-liner:** Same sidebar machine, two menus — Personal account gets fan tools; Host: {name} gets business tools.

---

## 7. Top navigation recommendation

**Source today:** `frontend/src/components/layout/SiteHeader.tsx`  
**Public links:** Events · Ambassadors · Hosts · Fans · Sponsors  
**Logged-in extras:** Dashboard · Host · (Support/Admin by role) · Theme · NotificationBell · Create event · user name · Log out

### 7.1 Current top-nav audit

| Control | Current behavior | Problem for Option A |
| --- | --- | --- |
| **Dashboard** | Always → `/dashboard` | Fine as Personal entry; competes with Host as a second “app” |
| **Host** | Role host/staff/admin → `/host/events`; else → `/host/onboarding` | Peer product link; skips role-aware home (`/host` / `/host/desk`); confusable with public **Hosts** |
| **Create event** | Global primary button → `/host/events/new` or onboarding | Host-biased while user may be in Personal mode; always visible when logged in (and for logged-out as CTA) |
| **User name** | Truncated `full_name` (xl+) | Display only — OK |
| **Log out** | Clears session → `/` | OK |
| **Notifications** | `NotificationBell` when logged in | Account-level — OK; deep links into personal/host targets as payloads dictate |
| **Theme** | Toggle | OK — out of scope for workspace IA |

Workspace paths widen the header container via `isWorkspacePath` (`/dashboard`, `/host`, `/admin`, …) but **do not** change which links are shown.

### 7.2 Answers to product questions

#### 1. Should top nav have both Dashboard and Host?

**No.** Keep a single workspace entry (**Dashboard**). Remove the peer **Host** link for users who can use the in-shell workspace switcher.

| Keep both? | Verdict |
| --- | --- |
| Today | Causes “two products” |
| Option A | One entry + in-shell mode switch |

Exception: pure marketing/header for users **without** any host workspace may show a softer **Become a host** (not labeled bare “Host”) — preferably inside shell or as secondary text, not a peer nav item next to Dashboard.

#### 2. Should Host be removed when the user already has a workspace switcher?

**Yes.** If `workspaces.length > 0` (or switcher is mounted), **Host** top-nav is redundant and harmful.

| User state | Top nav Host peer |
| --- | --- |
| Has ≥1 host workspace | **Remove** — switcher owns Host: {name} |
| Has 0 host workspaces | **Remove** bare “Host”; optional **Become a host** → `/host/onboarding` (secondary) |
| On `/host/onboarding` or preview | N/A — limited chrome |

#### 3. Should “Create event” stay globally visible?

**Mostly yes, with nuance — do not remove the growth CTA, but stop letting it define IA.**

| Context | Recommendation |
| --- | --- |
| Marketing / public pages | **Keep** Create event (drives host acquisition) |
| Inside Personal workspace (`/dashboard/*`) | **Keep allowed** but treat as secondary to workspace switcher; still OK as growth CTA → `/host/events/new` or onboarding |
| Inside Host workspace (`/host/*`) | **Keep / emphasize** — natural here; prefer `/host/events/new` when user can create |
| Logged out | **Keep** as today |

Optional polish (later): on Personal mode, use quieter styling or “Create event” that switches to host mode then opens studio — not required for A1.

**Do not** replace Dashboard/Host switching with Create event.

#### 4. Should clicking Dashboard open `/dashboard`, `/host`, last-used workspace, or chooser?

**Phased answer (aligned with §5.7):**

| Phase | Dashboard click | Why |
| --- | --- | --- |
| **A1 (ship first)** | → **`/dashboard`** | Zero new persistence; remove Host peer so this is enough |
| **A2 (preferred final)** | → **last-used mode** | If `padeya-workspace-mode === "host"` and user still has that host → `hostHomePathForWorkspace(active)`; else → `/dashboard` |
| Chooser `/workspaces` | **Not** every Dashboard click | Use after login when `workspaces.length > 0` and no `next` (already), or when mode/host is ambiguous |
| Always `/host` | **No** | Punishes fans and dual-role users in Personal |

**Never** send Dashboard → `/host/events` (today’s Host link anti-pattern).

#### 5. Should host users see “Switch workspace” instead of a separate Host link?

**Prefer in-shell switcher; optional compact header control on workspace paths.**

| Approach | Recommendation |
| --- | --- |
| Replace Host link with “Switch workspace” **and** keep Dashboard | Better than today, but two controls still compete |
| **Best:** Remove Host; keep Dashboard as entry; **Workspace** switcher inside shell (Personal / Host: {name}) | Matches Option A |
| On workspace paths only | Optional header chip showing current mode that opens the same switcher (not a second destination link) |

Label if a header control is needed: **Workspace** or current mode (**Personal** / **Host: DJ Maze**), not “Host”.

### 7.3 Recommended final top-nav behavior

#### Logged out

`Logo · Events · Ambassadors · Hosts · Fans · Sponsors · Log in · Create event`

#### Logged in — outside workspace paths (marketing pages)

`…public… · **Dashboard** · [Support?] · [Admin?] · Theme · Bell · Create event · Name · Log out`

- **No** peer **Host**
- Dashboard → A1 `/dashboard` · A2 last-used mode home

#### Logged in — on `/dashboard/*` or `/host/*`

Same as above for public + Dashboard entry, **plus** in-shell:

- Persistent **Workspace** switcher: Personal account · Host: {name}…
- Sidebar from §6
- **No** peer Host in SiteHeader
- Optional: header shows current mode chip (not a second nav destination)

#### Role-gated (unchanged)

| Role | Extra top link |
| --- | --- |
| Support agent | Support → `/support` |
| Super/finance admin (etc.) | Admin → `/admin` |

### 7.4 Decision summary

| Question | Recommendation |
| --- | --- |
| Both Dashboard and Host? | **No** — Dashboard only as workspace entry |
| Remove Host when switcher exists? | **Yes** |
| Create event globally visible? | **Yes** (growth CTA); don’t use it as mode switch |
| Dashboard click target? | **A1:** `/dashboard` · **A2:** last-used mode home · chooser only when ambiguous / post-login |
| Switch workspace instead of Host link? | **Yes in spirit** — in-shell (or header chip), not a peer “Host” route link |

### 7.5 What not to do

| Anti-pattern | Why |
| --- | --- |
| Keep Dashboard + Host peers | Recreates two-product feel |
| Host → `/host/events` | Wrong landing for desk/sponsor roles |
| Dashboard always → `/host` for anyone with host role | Traps fans who also host |
| Drop Create event entirely | Unrelated to IA; hurts acquisition |
| Rename public **Hosts** marketplace | Different product surface; keep |

---

## 8. Role and permission behavior

Two layers matter:

| Layer | What it is | Where enforced |
| --- | --- | --- |
| **Platform roles** | `buyer`, `host`, `host_staff`, `support_agent`, `finance_admin`, `super_admin` | Auth / shell access ([ROLES_AND_PERMISSIONS.md](./ROLES_AND_PERMISSIONS.md)) |
| **Host workspace membership** | Owner or team preset (`scanner`, `merch_staff`, `viewer`, `sponsor_manager`, …) + permission toggles | `HostWorkspace`, `canAccessHostPath`, `navGroupsForWorkspace`, `hostHomePathForWorkspace` |

Ambassadors are **not** a platform role — they are buyers using `/dashboard/ambassador*`. Platform admin uses a **separate** `/admin` shell and must not be mixed into Personal/Host workspace chrome.

### 8.1 Persona audit (current → recommended)

#### Normal buyer / fan (no host profile)

| | Current | Recommended (Option A) |
| --- | --- | --- |
| Platform role | `buyer` (typical) | Same |
| Host workspaces | None | None |
| Switcher | Hidden (`workspaces.length === 0`) | Show **Personal account** + **Become a host** |
| Top nav | Dashboard + Host→onboarding | Dashboard only; optional Become a host secondary |
| Login (no `next`) | → `/dashboard` | → `/dashboard` |
| Sidebar | Full personal nav | §6 Personal |
| Host routes | Onboarding CTA / RequireHost empty state | `/host/onboarding` only until they create/join |

**Landing:** `/dashboard`

---

#### Personal account + host owner

| | Current | Recommended |
| --- | --- | --- |
| Platform roles | `buyer` + `host` | Same |
| Workspaces | Owned host in `/me/team-workspaces` | Same |
| Switcher | Personal ↔ Host workspace: {name} (Owner) | Personal ↔ **Host: {name}** (Owner) |
| Login (no `next`) | → `/workspaces` | Keep chooser **or** last-used mode (A2) |
| Switch to Host | `hostHomePathForWorkspace` → `/host` | Same — Command Center |
| Top nav Host | → `/host/events` (wrong) | **Remove**; use switcher |
| Personal tools | Full `/dashboard/*` | Unchanged — tickets/orders still personal |

**Landing:**

| Entry | Destination |
| --- | --- |
| Login / first choice | `/workspaces` or last-used mode (A2) |
| Switcher / Dashboard→Host mode | `/host` |
| Switcher → Personal | `/dashboard` |
| Do **not** | Force always `/host` on login |

---

#### Personal account + host team member (non-desk)

| | Current | Recommended |
| --- | --- | --- |
| Platform roles | Often `buyer` + `host_staff` | Same |
| Workspaces | Team/event_staff row; permissions drive nav | Same |
| Switch to Host | Usually → `/host` (member overview) | Same unless sponsor_manager → `/host/sponsorships` |
| Sidebar | Filtered `navGroupsForWorkspace` | Same |
| Blocked paths | `HostAccessGuard` → `/host/access-denied` | Same |
| Payouts / banks | Owner-only; members denied | Same |

**Landing when selecting that host:** `hostHomePathForWorkspace` (typically `/host`; sponsor_manager → `/host/sponsorships`).

---

#### Scanner staff

| | Current | Recommended |
| --- | --- | --- |
| Workspace role | `scanner` and/or desk-focused ticket perms | Same |
| Home path | `hostHomePathForWorkspace` → **`/host/desk`** | **Keep** |
| Sidebar | Minimal Operate (desk + events; merch if granted) | Keep desk-focused filter |
| Roadmap / Grow / Manage | Hidden for desk-focused | Keep |
| Personal account | Still available via switcher | Keep — scanners may also hold tickets |

**Landing when selecting host:** `/host/desk`  
**Personal landing:** `/dashboard`

---

#### Merch staff

| | Current | Recommended |
| --- | --- | --- |
| Workspace role | `merch_staff` and/or merch desk perms | Same |
| Home path | Desk-focused → **`/host/desk`** | **Keep** |
| Sidebar | Operate with Merch when granted | Keep |
| Fulfillment | Per-event `/host/events/[id]/merchandise/fulfillment` | Deep links from desk |

**Landing when selecting host:** `/host/desk`  
**Personal landing:** `/dashboard`

---

#### Viewer role

| | Current | Recommended |
| --- | --- | --- |
| Workspace role | `viewer` / read-only member | Same |
| Home path | `/host` (member read-only overview) | **Keep** `/host` — not desk |
| Roadmap | Hidden (`isHostReadOnlyMember`) | Keep |
| Mutations | Blocked by perms / UI | Keep |
| Personal | Full personal sidebar | Keep |

**Landing when selecting host:** `/host` (read-only overview)  
**Not** `/host/desk` unless they also have scan grants.

---

#### Ambassador-only user

| | Current | Recommended |
| --- | --- | --- |
| Platform role | Usually `buyer` only | Same — no `ambassador` platform role |
| Host workspace | None (unless also staff/owner) | None |
| Tools | `/dashboard/ambassador*` | Same under Personal → Growth |
| Login | → `/dashboard` | Prefer **`/dashboard/ambassador`** only when product flags them as active promoter **or** they last used that area; default safe landing remains `/dashboard` with Ambassadors in sidebar |
| Host top nav | Misleading onboarding | Remove peer Host; Become a host optional |

**Landing:**

| Entry | Destination |
| --- | --- |
| Default login | `/dashboard` (Overview) — Ambassadors visible in sidebar |
| Deep link / “go promote” CTA | `/dashboard/ambassador` |
| Optional smart landing | If enrollments active and no host workspaces → `/dashboard/ambassador` (nice-to-have, not required for A1) |

Do **not** put Ambassador campaigns under `/host` for this user.

---

#### Platform admin (`super_admin` / `finance_admin`)

| | Current | Recommended |
| --- | --- | --- |
| Shell | Separate `/admin` via SiteHeader | **Keep separate** |
| Personal / Host | May also use `/dashboard` and `/host` (impersonation/ops) | Allowed, but **Admin is not a workspace mode** |
| Switcher | Host workspaces if they own/join hosts | Do not add “Admin” into Personal/Host switcher |
| Login | Often `next` or → chooser/dashboard | Prefer `/admin` when primary job is platform ops **and** no `next` — product choice; otherwise `/workspaces` / `/dashboard` is OK if they also host |

**Landing (recommended default for pure platform admins):** `/admin`  
**Do not** mix admin nav into Personal or Host sidebars.  
Support agents: `/support` shell — same separation rule.

### 8.2 Recommended landing matrix

| Persona | Post-login (no `next`) | Top nav Dashboard (A1) | Top nav Dashboard (A2 last-used) | Switcher → Personal | Switcher → that Host |
| --- | --- | --- | --- | --- | --- |
| Buyer only | `/dashboard` | `/dashboard` | `/dashboard` | `/dashboard` | — |
| Host owner (+ personal) | `/workspaces` | `/dashboard` | last mode home | `/dashboard` | `/host` |
| Host team (general) | `/workspaces` | `/dashboard` | last mode home | `/dashboard` | `/host` (or sponsorships) |
| Scanner staff | `/workspaces` | `/dashboard` | last mode home | `/dashboard` | **`/host/desk`** |
| Merch staff | `/workspaces` | `/dashboard` | last mode home | `/dashboard` | **`/host/desk`** |
| Viewer | `/workspaces` | `/dashboard` | last mode home | `/dashboard` | `/host` |
| Ambassador-only | `/dashboard` | `/dashboard` | `/dashboard` or ambassador if smart | `/dashboard` | — |
| Platform admin | `/admin` (preferred) or chooser if also host | `/dashboard` if used | last personal/host mode; Admin via Admin link | `/dashboard` | role home if they have host seat |
| Support agent | `/support` (preferred) | `/dashboard` if used | same pattern | `/dashboard` | if team seat |

Always honor `?next=` over the matrix (`LoginForm` already does).

### 8.3 Permission rules that stay invariant

| Rule | Behavior |
| --- | --- |
| Personal data | Only on `/dashboard/*` (and `/connect/*`) — never require host membership |
| Host mutations | Active `host_id` + `canAccessHostPath` / API perms |
| Desk staff | Minimal sidebar; land on `/host/desk` |
| Owner finance | `/host/payouts`, `/host/bank-accounts` — owner only |
| Hosts cannot delete reviews | Product invariant |
| Admin / support | Own shells; not workspace switcher options |
| Multi-host users | Switcher lists every workspace; each has its own role home |

### 8.4 Clarity vs today’s bugs

| Bug / smell | Fix under Option A |
| --- | --- |
| SiteHeader Host → `/host/events` for all host/staff | Remove link; use `hostHomePathForWorkspace` |
| Scanner opening “Host” lands on events list | Desk home via switcher |
| Admin link beside Dashboard/Host feels like third workspace | Keep Admin separate; remove Host peer so Admin isn’t a fourth twin |
| Ambassador sees Host→onboarding as peer product | Remove Host peer; Growth → Ambassadors in Personal sidebar |

### 8.5 Role behavior verdict

| Principle | Decision |
| --- | --- |
| Buyer only | Personal only → `/dashboard` |
| Dual-role owner/team | Personal + Host: {name} via switcher; role-aware host home |
| Scanner / merch | Host mode → `/host/desk` |
| Viewer | Host mode → `/host` read-only overview |
| Ambassador-only | Personal → `/dashboard` (ambassador section); not a host mode |
| Platform admin / support | Separate shells; not mixed into workspace switcher |
| Implementation | Mostly **already** in `hostHomePathForWorkspace` + login chooser — finish chrome (§5–§7), don’t re-architect roles |

---

## 9. Privacy and safety boundaries

**Hard rule for this unification:** UI/navigation only. Shared shell and workspace switcher must **never** merge datasets, weaken gates, or imply that Personal and Host are the same data plane.

### 9.1 What must not be mixed

| Forbidden mix | Why | How Option A stays safe | Code / product anchors today |
| --- | --- | --- | --- |
| **Buyer private tickets in host workspace** | Ticket QR / transfers are attendee PII and ownership | Host desk scans **event** tickets via host APIs; never list `/dashboard/tickets` data in `/host` nav or Command Center | Personal: `/dashboard/tickets*`. Host: check-in / desk / attendees APIs scoped to host+event |
| **Host financial data in personal dashboard** | Balances, payouts, bank accounts are business-sensitive | No host finance routes under `/dashboard`; personal Ambassadors payouts ≠ host balance | `/host/payouts`, `/host/bank-accounts` owner-only (`RequireHostOwner` / `canAccessHostPath` deny members). Personal: orders/refunds/ambassador earnings only |
| **Team member access without permission** | Staff see only granted tools | Keep `HostAccessGuard` + `canAccessHostPath` + API enforcement; switcher does not grant access | `frontend/src/lib/host-access.ts`, `HostAccessGuard` → `/host/access-denied` |
| **Scanner staff seeing full host dashboard** | Desk roles are operationally narrow | Desk-focused nav filter + land on `/host/desk`; no Grow/Manage dump | `isDeskFocusedStaff`, `navGroupsForWorkspace`, `hostHomePathForWorkspace` → `/host/desk` |
| **Ambassadors seeing host/team tools** | Promoters are buyers unless also invited as staff | Ambassador IA stays under Personal (`/dashboard/ambassador*`); no host sidebar for ambassador-only users | No platform `ambassador` role; host Ambassadors = campaign **owner** tools on `/host/ambassadors*` |
| **Public Legacy pages as private dashboard routes** | Public profile ≠ private studio | Public `/@username` (rewrite → `/u/...`) stays outside workspace shells; private edit stays `/host/legacy*` | `WORKSPACE_PREFIXES` does **not** include `/u` or `/@`; Legacy studio is host-gated |
| **Admin tools mixed into normal dashboard** | Platform ops ≠ fan/host workspace | `/admin` and `/support` remain separate shells and switcher options | SiteHeader role links; not in `buyerNav` / `hostNav` |

### 9.2 Boundary model (keep)

```
┌─────────────────────────────────────────────────────────┐
│  SiteHeader (marketing + single Dashboard entry)        │
└─────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────┐
│  WorkspaceShell (shared CHROME only)                    │
│  Switcher: Personal account | Host: {name}              │
└─────────────┬───────────────────────────┬───────────────┘
              │                           │
              ▼                           ▼
┌─────────────────────────┐   ┌─────────────────────────────┐
│  PERSONAL data plane    │   │  HOST data plane            │
│  /dashboard/*           │   │  /host/*                    │
│  /connect/*             │   │  active host_id + perms     │
│  account-scoped APIs    │   │  HostAccessGuard            │
└─────────────────────────┘   └─────────────────────────────┘

Separate (never workspace modes):
  /admin/*   /support/*   public /events /hosts /@username …
```

Shared: layout components, brand tokens, switcher chrome.  
**Not shared:** nav item lists as one merged menu, React query caches across modes without scoping, API clients that drop `host_id` / authz checks.

### 9.3 Explicit allow vs deny for unification work

| Change type | Allowed? |
| --- | --- |
| Shared `WorkspaceShell`, sidebar renderer, breadcrumbs chrome | **Yes** |
| Workspace switcher labels / visibility / top-nav cleanup | **Yes** |
| Rename shell title Buyer → Personal | **Yes** |
| Point Host landings at `hostHomePathForWorkspace` | **Yes** |
| One sidebar listing both personal tickets and host payouts | **No** |
| “Universal inbox” mixing fan and host threads without role context | **No** (separate inboxes OK) |
| Showing host balance widgets on `/dashboard` | **No** |
| Showing my ticket QR on `/host` overview | **No** |
| Softening `canAccessHostPath` to “simplify nav” | **No** |
| Putting Legacy public page inside buyer/host shell | **No** |
| Adding Admin to Personal/Host switcher options | **No** |
| Moving host finance under `/dashboard` for “one URL tree” | **No** |

### 9.4 Overlapping *labels* vs overlapping *data*

Same words in both sidebars (Merch, Messages, Vault, Team, Ambassadors, Settings) are **allowed** only when:

1. Mode chrome makes ownership obvious (**Personal** vs **Host: {name}**), and  
2. Each href hits a **different** API/data scope, and  
3. Permissions still apply on the host side.

Label polish (§6.6) is cosmetic. **Data merge is not.**

### 9.5 Related product invariants (unchanged)

From project rules / [ROLES_AND_PERMISSIONS.md](./ROLES_AND_PERMISSIONS.md) — still enforced after unification:

1. Hosts cannot delete reviews.  
2. Support cannot modify financial records.  
3. Manual payouts require immutable evidence.  
4. Tickets issue only after verified payment webhooks.  
5. Check-in uses signed QR payloads.  
6. Messaging fan↔host rules stay permission-checked (`app.messaging.permissions`).

### 9.6 Safety verdict

| Statement | Status |
| --- | --- |
| Unification is UI/navigation only | **Confirmed** — Option A |
| Data and permissions remain separate | **Confirmed** — dual route trees + existing guards |
| Listed forbidden mixes | **Must remain forbidden**; chrome work must not regress them |
| Public Legacy / Admin / Support | **Outside** Personal/Host workspace modes |

**Test mindset for any future PR:** switching Personal ↔ Host changes chrome and route prefix; it must not change what a `buyer`-only token can fetch, or what a scanner can see beyond desk grants.

---

## 10. Migration plan

**Strategy:** Option A — unify chrome and switching; **keep** `/dashboard/*` and `/host/*` as canonical trees. Do not require Option B/C URL moves. Respect §9 privacy boundaries in every phase.

### 10.1 Phase overview

| Phase | Scope | Routes moved? | Ship when |
| --- | --- | --- | --- |
| **1** | Audit + docs only | No | This document complete |
| **2** | Shared shell/switcher polish + sidebar layout fix | No | Chrome feels one product inside both trees |
| **3** | Top nav cleanup + Dashboard landing + Host peer removed | No | Header no longer competes with switcher |
| **4** | Optional aliases only | Aliases/redirects only | Old links + optional convenience paths |
| **5** | Tests, docs, smoke | No | Regression-safe |

### 10.2 Phase 1 — Audit and docs only

**Status:** In progress / largely complete via this file.

| Deliverable | Notes |
| --- | --- |
| Route audit (§1) | Done |
| `/dashboard` vs `/host` compare (§2) | Done |
| Strategy Option A (§3–§4) | Done |
| Switcher / nav / top nav / roles / safety (§5–§9) | Done |
| Migration plan (§10) | This section |
| No product code changes | Required |

**Exit criteria:** Stakeholders agree Option A + phase gates; no route renames approved for Phases 2–3.

---

### 10.3 Phase 2 — Shared shell, switcher, sidebar layout (routes unchanged)

**Already partially shipped:** both layouts use `WorkspaceShell` + `WorkspaceSwitcher`. Phase 2 finishes the product model, not a greenfield shell.

| Work item | Detail |
| --- | --- |
| Shared `WorkspaceShell` | Confirm single chrome path; no second host-only sidebar component |
| Shared workspace switcher | Always visible when authenticated in workspace paths; Personal always listed; hosts from `/me/team-workspaces`; labels **Personal account** / **Host: {name}**; remove duplicate in `CommandCenterHeader` (or demote to chip) |
| Shell titles | Buyer → **Personal**; Host → **Host: {display_name}** (breadcrumb roots too) |
| Fix dashboard sidebar vertical layout | Layout/CSS only — sticky/overflow/scroll behavior in `DashboardSidebar` / shell; **no** IA change |
| Nav configs | Keep §6 `buyerNav` / `hostNav` (optional: Merch href → `/dashboard/merchandise`) |
| Routes | **Unchanged** |

**Exit criteria:** On `/dashboard` and `/host`, user sees one workspace chrome + clear switcher; sidebar layout correct on desktop/mobile; §9 boundaries untouched.

---

### 10.4 Phase 3 — Top nav cleanup + Dashboard landing

| Work item | Detail |
| --- | --- |
| Remove peer **Host** from `SiteHeader` | When user can use switcher (or always for logged-in); optional secondary **Become a host** if zero workspaces |
| Keep **Dashboard** as workspace entry | Public nav unchanged (Events · Ambassadors · Hosts · Fans · Sponsors) |
| Dashboard click | **A3a:** `/dashboard` · **A3b (preferred):** last-used mode via `padeya-workspace-mode` → Personal `/dashboard` or `hostHomePathForWorkspace` · chooser `/workspaces` only when ambiguous / post-login (already) |
| Host link | Becomes **removed** (preferred) or a non-route “Workspace” control that opens the same switcher — **not** `/host/events` |
| Create event | Remains global growth CTA (§7) |
| Routes | **Unchanged** |

**Exit criteria:** Logged-in header has one workspace entry; dual-role users switch only via Workspace control; scanner/owner landings still role-aware when entering Host mode.

---

### 10.5 Phase 4 — Optional route aliases (keep `/host`)

**Canonical trees stay `/dashboard/*` and `/host/*`.** Aliases are convenience/defensive only — not a migration to Option B.

| Kind | Path | Target | When |
| --- | --- | --- | --- |
| **Keep** | All primary `/dashboard/*` and `/host/*` tools (§1) | Canonical | Always |
| **Already redirect/alias** | `/host/dashboard` → `/host` | Keep | Already in `next.config` |
| **Already redirect** | `/host/events/:id/merch` → `…/merchandise` | Keep | Already |
| **Already redirect** | `/host/settings/notifications` → `/dashboard/settings/notifications` | Keep | Account prefs |
| **Already alias** | `/dashboard/connect/*` → `/connect/*` | Keep | Fan Connect shell |
| **Formalize** | `/dashboard/merch` → `/dashboard/merchandise` | 308 in `next.config` | Phase 4 |
| **Optional alias** | `/dashboard/host` → `/host` (or role home) | Only if product wants a “under Dashboard” bookmark **without** moving the tree | **Optional — default skip** |
| **Optional alias** | `/dashboard/host/*` → `/host/*` | High maintenance; **not recommended** unless strongly requested | Prefer skip |
| **Do not** | Make `/dashboard/host` the canonical Command Center | That is Option B | Rejected for now |

**Keep `/host` for all old links** (emails, invites, QR ops, docs, bookmarks). Never delete `/host` in Phase 4.

**Exit criteria:** Aliases are 308/permanentRedirect only; no host page files moved under `/dashboard`.

---

### 10.6 Phase 5 — Tests, docs, smoke checks

| Work | Detail |
| --- | --- |
| Unit / component | Switcher: Personal → `/dashboard`; Host → `hostHomePathForWorkspace`; hidden→always-visible behavior; mode persistence (if A3b) |
| Nav | Snapshot/filter: desk staff minimal Operate; owner full §6 host nav |
| Access | Member denied path → `/host/access-denied`; owner payouts still owner-only |
| Redirects | `/host/dashboard`, merch aliases, notification prefs |
| Smoke | [PRODUCTION_SMOKE_TEST.md](./PRODUCTION_SMOKE_TEST.md) — login chooser, Personal home, Host Command Center, desk landing, Create event, Admin separate |
| Privacy regression | No personal tickets on host home; no host balance on `/dashboard` (§9) |

**Exit criteria:** CI green for host-command-center / host-team related suites; smoke checklist updated and run.

---

### 10.7 Routes to keep / redirect / alias

#### Keep (canonical — do not move)

| Tree | Examples |
| --- | --- |
| Personal | `/dashboard`, tickets, orders, merchandise, messages, passport, vault, ambassador, settings, team (picker) |
| Host | `/host`, roadmap, desk, events/*, merchandise/*, ambassadors/*, sponsorships, audience, legacy/*, vault/*, analytics, team/*, messages/*, settings, payouts, bank-accounts |
| Related | `/workspaces`, `/connect/*`, `/support`, `/admin`, public `/hosts`, `/@username` |

#### Redirect (legacy → canonical)

| From | To | Phase |
| --- | --- | --- |
| `/host/dashboard`, `/host/dashboard/:path*` | `/host` | Done — keep |
| `/host/events/:id/merch` | `/host/events/:id/merchandise` | Done — keep |
| `/host/settings/notifications` | `/dashboard/settings/notifications` | Done — keep |
| `/dashboard/merch` | `/dashboard/merchandise` | Phase 4 (formalize 308) |
| `/dashboard/connect/*` | `/connect/*` | Done — keep |

#### Alias (optional)

| From | To | Phase | Default |
| --- | --- | --- | --- |
| `/dashboard/host` | `/host` or role-aware home | 4 | **Skip** unless requested |
| `/dashboard/host/:path*` | `/host/:path*` | 4 | **Skip** (maintenance cost) |

### 10.8 Docs to update

| Doc | Phase | Update |
| --- | --- | --- |
| [DASHBOARD_HOST_UNIFICATION_AUDIT.md](./DASHBOARD_HOST_UNIFICATION_AUDIT.md) | 1 | Source of truth for decision (this file) |
| [FRONTEND_ROUTES.md](./FRONTEND_ROUTES.md) | 3–5 | Top nav behavior; Dashboard entry; no peer Host; switcher labels |
| [HOST_AREA_AUDIT.md](./HOST_AREA_AUDIT.md) | 3–5 | Cross-link Option A; SiteHeader notes |
| [TEAMS.md](./TEAMS.md) / [HOST_TEAM.md](./HOST_TEAM.md) | 2–5 | Switcher always-on; Personal vs Host: {name}; mode persistence if added |
| [ROLES_AND_PERMISSIONS.md](./ROLES_AND_PERMISSIONS.md) | 5 | Landing matrix pointer to §8 |
| [PRODUCTION_SMOKE_TEST.md](./PRODUCTION_SMOKE_TEST.md) | 5 | Unified chrome flows; remove “open Host top nav → events” if present |
| [EXECUTION_TRACKER.md](./EXECUTION_TRACKER.md) | 2–5 | Track phase completion |
| [CRUD_MATRIX.md](./CRUD_MATRIX.md) | 4–5 | Only if aliases/`padeya-workspace-mode` affect active workspace story |
| AGENTS / project rules | Optional | One line: workspace chrome vs data planes |

### 10.9 Risks

| Risk | Likelihood | Mitigation |
| --- | --- | --- |
| Users bookmark SiteHeader **Host** → `/host/events` | Med | Phase 3 remove link; desk staff use switcher → `/host/desk` |
| Hiding switcher when `workspaces.length === 0` leaves Personal-only users confused | Med | Phase 2 always show Personal + Become a host |
| Last-used mode sends fans to host unexpectedly | Med | Default Personal; only restore host mode if flag set; honor `?next=` |
| Optional `/dashboard/host` alias implies Option B | Med | Skip by default; document as non-canonical |
| Duplicate switchers (shell + Command Center) | Low | Phase 2 single control |
| Sidebar layout fix regresses mobile drawer | Med | Visual QA desktop + mobile in Phase 2 |
| Permission regression while “simplifying nav” | High impact | §9 checklist on every PR; no `canAccessHostPath` weakening |
| Doc drift (“host dashboard” vs `/dashboard`) | Med | Phase 5 glossary: host home = `/host`; personal = `/dashboard` |
| Create event CTA still feels host-biased on Personal | Low | Accept for growth; optional quieter style later |

### 10.10 Phase gates (do not skip)

1. **No Phase 3** until Phase 2 switcher is always understandable.  
2. **No Phase 4 aliases** that make `/dashboard/host` canonical.  
3. **No route file moves** without a new explicit decision to revisit Option B/C.  
4. **No Phase 5 complete** without privacy smoke (§9).

### 10.11 Migration verdict

| Question | Answer |
| --- | --- |
| Safe path for Pàdéyá? | Phases 1 → 2 → 3 → 5; Phase 4 optional and minimal |
| Move `/host` under `/dashboard`? | **No** (not in this plan) |
| Keep old `/host` links? | **Yes** forever in this plan |
| Biggest user-facing win? | Phase 2 switcher + Phase 3 remove peer Host |

---

## 11. Final audit response

**Status:** Audit complete. **Do not implement yet** — this document is the decision record.  
**Brand:** Pàdéyá  
**Decision:** **Option A** — unified workspace chrome; keep `/dashboard` and `/host` routes.

### 1. What `/dashboard` is today

The authenticated **Personal account** surface for buyers/fans/attendees: tickets, orders, merch wallet, refunds, messages, Fan Connect, following, Passport/badges, Vault unlocks, own reviews, Ambassadors (promote & earn), and account settings.

- **Home:** soft “Attendee” greeting + personal metrics (`frontend/src/app/dashboard/page.tsx`).
- **Shell:** `WorkspaceShell` with `buyerNav` (sidebar title today: **Buyer**).
- **Gate:** `RequireAuth` only — no host membership required.

### 2. What `/host` is today

The authenticated **Host workspace** surface for a selected host org: Command Center (or member desk overview), roadmap, events/ops, desk (tickets & merch entry), merch studio, host messages, Ambassadors campaigns, sponsorships, audience, Legacy + Vault studios, analytics, team, host settings, owner payouts.

- **Home:** owner `OwnerCommandCenter` or member desk/read-only overview (`/host`; `/host/dashboard` aliases here).
- **Shell:** same `WorkspaceShell` with permission-filtered `hostNav` (title: **Host**).
- **Gate:** active workspace + `RequireHost` / `HostAccessGuard` / `canAccessHostPath`.

### 3. Main overlaps / confusions

| Confusion | Detail |
| --- | --- |
| Peer top nav | SiteHeader **Dashboard** + **Host** feel like two products |
| Naming drift | Buyer / Attendee / Personal account / Dashboard vs Host |
| Host landing | Header Host → `/host/events`, not role-aware home |
| Label twins | Team, Merch, Messages, Vault, Ambassadors, Settings on both sidebars |
| Switcher gaps | Hidden when zero hosts; last **host** persists, not last **mode** |
| “Host dashboard” language | Means `/host`, easy to confuse with `/dashboard` |

**Not a confusion to “fix” by merging data:** consumer tools vs producer tools are correctly separate.

### 4. Recommended unification option

**Option A — Unified shell, keep routes.**

- One shared `WorkspaceShell` + workspace switcher.
- Users experience one Pàdéyá workspace with two modes.
- Reject Option B (`/dashboard/host/...`) and Option C (`/workspace/...`) for now (migration cost).
- Reject Option D (top-nav-only) as insufficient.

### 5. Should routes stay separate internally?

**Yes.** Keep canonical trees:

- Personal → `/dashboard/*` (and `/connect/*`)
- Host → `/host/*`

Safety, permissions, deep links, and emails stay clean. Unification is chrome/IA, not URL surgery.

### 6. Proposed workspace switcher behavior

| Rule | Behavior |
| --- | --- |
| Labels | **Personal account** · **Host: {display_name}** (+ Owner / role suffix) |
| Always show | Personal; if no hosts → Become a host → `/host/onboarding` |
| → Personal | Navigate `/dashboard` (keep stored active `host_id`) |
| → Host | `setActiveHostId` + `POST /me/active-workspace` + `hostHomePathForWorkspace` |
| Persist | Active **host** already (localStorage + DB); add last **mode** in a later phase |
| Placement | Once in shell chrome; don’t compete with SiteHeader Host link |

### 7. Proposed top nav behavior

| Item | Recommendation |
| --- | --- |
| Public | Events · Ambassadors · Hosts · Fans · Sponsors |
| Workspace entry | **Dashboard** only (remove peer **Host**) |
| Dashboard click | Phase 3a → `/dashboard`; later → last-used mode home |
| Create event | Keep as growth CTA |
| Bell / name / logout | Keep |
| Admin / Support | Separate shells — not workspace modes |

### 8. Proposed personal sidebar

**Home:** Overview · Alerts  
**Activity:** Tickets · Orders · Merch · Refunds  
**Community:** Messages · Team · Connect · Following  
**Identity:** Passport · Badges · Vault · Reviews  
**Growth:** Ambassadors  
**Account:** Settings  

(= current `buyerNav` / §6.1)

### 9. Proposed host sidebar

**Home:** Overview · Roadmap  
**Operate:** Events · Tickets & Entry · Merch Studio · Host Inbox  
**Grow:** Ambassador Campaigns · Sponsorships · Audience CRM · Legacy Page · Vault Studio  
**Manage:** Analytics · Host Team · Host Settings · Support  

(= current `hostNav` labels; paths unchanged; filtered by permissions / §6.2)

Same shared sidebar **component**; different **nav config** per mode — not one merged menu.

### 10. Role-aware landing behavior

| Persona | Landing |
| --- | --- |
| Buyer only | `/dashboard` |
| Host owner (Host mode) | `/host` |
| Scanner / merch staff (Host mode) | `/host/desk` |
| Viewer (Host mode) | `/host` (read-only overview) |
| Sponsor manager (typical) | `/host/sponsorships` |
| Dual-role login | `/workspaces` or later last-used mode |
| Ambassador-only | `/dashboard` (Ambassadors in sidebar); CTA may go `/dashboard/ambassador` |
| Platform admin | `/admin` — not mixed into Personal/Host switcher |
| Support | `/support` — separate |

Always honor `?next=`. Use `hostHomePathForWorkspace` — never hardcode `/host/events` as the universal Host entry.

### 11. Privacy / permission boundaries

Unification is **UI/navigation only**. Must not mix:

- Buyer tickets into host workspace  
- Host finance into personal dashboard  
- Team access without permission  
- Full host IA for desk-only staff  
- Host/team tools for ambassador-only users  
- Public Legacy into private shells  
- Admin into normal workspace switcher  

Data planes and gates stay separate (§9).

### 12. Migration phases

| Phase | Work | Status |
| --- | --- | --- |
| **1** | Audit + docs | **Done** |
| **2** | Switcher/shell polish, titles Personal / Host: {name}, sidebar layout; routes unchanged | **Done** |
| **3** | Top nav cleanup; remove Host peer; Dashboard = single workspace entry → `/dashboard` | **Done** |
| **4** | Optional aliases; keep `/host` canonical; **skip** `/dashboard/host` | **Done (skipped alias)** |
| **5** | Tests, docs, smoke + privacy regression (`test:workspace-privacy`) | **Done** |

### 13. Open questions / risks

| Open question | Note |
| --- | --- |
| Dashboard → last-used mode? | **Deferred** — top nav stays simple `/dashboard`; mode stored as `padeya-workspace-mode` for future use |
| Optional `/dashboard/host` alias? | **Skipped** this phase — do not make canonical |
| Disambiguate Team / Merch labels? | **Done** on Host sidebar (Merch Studio, Host Inbox, …) — see [HOST_COMMAND_CENTER_POLISH.md](./HOST_COMMAND_CENTER_POLISH.md) |
| Create event styling on Personal? | Keep CTA; quieter style later? |
| Smart ambassador login landing? | Nice-to-have → `/dashboard/ambassador` |

| Risk | Mitigation |
| --- | --- |
| Header Host bookmarks to `/host/events` | Peer link removed; role-aware switcher |
| Mode restore sends fans to host | Top nav defaults Personal (`/dashboard`); honor `next` |
| “Simplifying” nav weakens perms | §9 + `test:workspace-privacy` |
| Doc language “host dashboard” | Always mean `/host` |

---

### Final one-liner

**One Pàdéyá account, one shared workspace chrome, two safe route trees — Personal on `/dashboard`, Host: {name} on `/host`, switched in-shell. Admin and Support stay separate. No `/dashboard/host`.**

---

## Appendix A — Layout & nav source files

| Concern | File |
| --- | --- |
| Personal layout | `frontend/src/app/dashboard/layout.tsx` |
| Host layout | `frontend/src/app/host/layout.tsx` |
| Shared shell | `frontend/src/components/layout/WorkspaceShell.tsx` |
| Sidebar / mobile drawer | `DashboardSidebar.tsx` · `DashboardTopbar.tsx` · `WorkspaceNavSections.tsx` |
| Personal + host nav definitions | `frontend/src/lib/nav/workspace.ts` |
| Host permission-filtered nav | `frontend/src/lib/nav/host-nav.ts` |
| Path access + role landings + chrome titles | `frontend/src/lib/host-access.ts` |
| Workspace switcher | `frontend/src/components/hosts/WorkspaceSwitcher.tsx` |
| Site header (Dashboard entry; no private Host peer) | `frontend/src/components/layout/SiteHeader.tsx` |
| Create event CTA (not a switcher) | `frontend/src/components/layout/CreateEventCta.tsx` |
| Post-login chooser | `frontend/src/app/workspaces/page.tsx` |
| Server redirects | `frontend/next.config.ts` |
| Privacy smoke | `frontend/scripts/workspace-privacy-smoke.mjs` |

## Appendix B — Method

- Globbed `frontend/src/app/dashboard/**/page.tsx` (41) and `frontend/src/app/host/**/page.tsx` (88).  
- Read layouts, `WorkspaceSwitcher`, `HostAccessGuard`, `canAccessHostPath`, `next.config.ts` redirects.  
- Cross-checked [FRONTEND_ROUTES.md](./FRONTEND_ROUTES.md) and [HOST_AREA_AUDIT.md](./HOST_AREA_AUDIT.md).  
- Product intent: unify **navigation / layout / workspace switching / route strategy**, not buyer↔host data.
