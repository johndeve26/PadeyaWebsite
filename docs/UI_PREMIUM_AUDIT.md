# Pàdéyá UI Premium Audit

Inventory of frontend routes for investor / host / buyer demo readiness.  
**Scope:** frontend UI only. No backend or product-feature changes implied by polish recommendations.

**Brand:** user-facing copy must say **Pàdéyá** (not Padéyá / Pàdéyé / Padeya in sentences).  
**Score:** 1–10 (3–5 scaffold, 6–7 OK, 8–9 strong, 10 exceptional).  
**Polish level:** light / medium / heavy.

**Shared components baseline:** `DashboardShell`, `PageHeader`, `Card`, `Button`, `Badge`, `EmptyState`, `StatCard`, `DataTable`, `Input`/`Select`/`Textarea`, `WorkspaceNavGrid`, `HeroSection` / `SponsorHero`, `LegacyPageView`, `EventCard`, `ReviewCard`.

**Theme:** light / dark / system via `<html class="dark">` — see [DARK_MODE_QA.md](./DARK_MODE_QA.md) · [BRAND_GUIDE.md](./BRAND_GUIDE.md).

---

## Summary (final — 2026-07-17)

| Area | Final avg | Notes |
|------|-----------|-------|
| Public marketing / marketplace / Legacy | **9** | Hero, discovery, sticky CTAs, category demo art |
| Auth / offline / demo | **8** | AuthFormCard, offline brand page, demo hub |
| Buyer dashboard | **8–9** | Wallet tickets, orders, passport, Vault, refunds |
| Host workspace | **8–9** | Ops hub, EventForm, door, Legacy tier, Vault studio, CRM |
| Admin / support / finance | **8** | ConfirmAction, DataTables, case queues, analytics |
| Staff check-in | **8** | Shared CheckInWorkspace + mobile scanner |

**Overall product UI score: 8.5 / 10** (demo-ready; no scaffold queues remaining)

**Rewrite note:** `/@username/*` rewrites to `/u/[username]/*` via middleware.

---

## Public

| Route | Score | Purpose | Type | Main UI problems | Polish | Shared components | Mobile |
|-------|-------|---------|------|------------------|--------|-------------------|--------|
| `/` | 9 | Brand home, discovery CTAs | public | Minor section density only | light | Yes (Hero, SectionHeader, CTAs) | Good |
| `/events` | 8 | Browse published events | public | Filter bar utilitarian | light | Yes (EventCard, hero) | Good |
| `/events/[slug]` | 8 | Event detail + tickets CTA | public | Body over-carded | light | Mostly | Good (sticky CTA) |
| `/events/[slug]/checkout` | 8 | Pay / free checkout | checkout | Trust chips bolted-on | light | Yes | Good (sticky pay) |
| `/hosts` | 7 | Jump to Legacy by username | public | Thin below-fold directory | medium | HostCard OK | OK |
| `/sponsors` | 9 | Sponsorship marketplace landing | sponsor | — | light | Yes (Sponsor*) | Good |
| `/sponsors/hosts` | 9 | Verified host marketplace | sponsor | — | light | Yes | Good |
| `/offline` | 7 | Offline fallback | public | Intentionally minimal | light | Logo/Button | Good |
| `/login` | 7 | Sign in | public | Thin; AuthFormCard carries polish | light | AuthFormCard | Good |
| `/register` | 7 | Create account | public | Same as login | light | AuthFormCard | Good |
| `/demo` | 8 | Local QA control center | demo | Dense link pills (OK for purpose) | light | Custom dark hub | OK |

### Legacy / Vault / Memories (public)

| Route | Score | Purpose | Type | Main UI problems | Polish | Shared components | Mobile |
|-------|-------|---------|------|------------------|--------|-------------------|--------|
| `/@username` → `/u/[username]` | 9 | Public Legacy profile | public | — | light | LegacyPageView | Good |
| `/@username/vault` → `/u/.../vault` | 7 | Public Vault catalog | public | Less rich than Legacy | medium | VaultCard, hero | OK |
| `/@username/vault/[itemSlug]` | 8 | Vault item + unlock | public | — | light | Dark hero + Card | Good |
| `/@username/memories/[eventSlug]` | 8 | Public Event Memory | public | Minor consistency | light | ReviewCard, hero | Good |

---

## Buyer / attendee

| Route | Score | Purpose | Type | Main UI problems | Polish | Shared components | Mobile |
|-------|-------|---------|------|------------------|--------|-------------------|--------|
| `/dashboard` | 8 | Fan workspace hub | buyer | Account card secondary | light | WorkspaceNavGrid | Good |
| `/dashboard/tickets` | 8 | Ticket list + offline cache | ticket | — | light | Ticket pass rows | Good |
| `/dashboard/tickets/[id]` | 8 | Large QR ticket | ticket | Action row ops-dense | light | Strong QR UI | Good |
| `/dashboard/tickets/[id]/transfer` | 5 | Transfer ownership | buyer | Form + rules only | medium | Shell only | OK |
| `/dashboard/orders` | 8 | Order history | buyer | — | light | StatusBadge, EmptyState | Good |
| `/dashboard/orders/[id]` | 8 | Order receipt | buyer | — | light | StatusBadge, receipt Cards | Good |
| `/dashboard/passport` | 8 | Fan Passport | buyer | List sections dense | light | EmptyState, dark hero | Good |
| `/dashboard/badges` | 8 | Badge catalog | buyer | — | light | EmptyState, earned ring | Good |
| `/dashboard/vault` | 8 | Unlocks / purchases | buyer | — | light | VaultCard sections | Good |
| `/dashboard/following` | 5 | Followed hosts | buyer | CRM list | medium | Plain | OK |
| `/dashboard/reviews` | 7 | Submit / view reviews | buyer | Form still heavy | light | ReviewCard, Select | Good |
| `/dashboard/refunds` | 5 | My refund requests | buyer | Generic Cards | medium | Partial EmptyState | OK |
| `/dashboard/refunds/new` | 4 | Request refund | buyer | Plain form | medium | Raw controls risk | OK |

---

## Host

| Route | Score | Purpose | Type | Main UI problems | Polish | Shared components | Mobile |
|-------|-------|---------|------|------------------|--------|-------------------|--------|
| `/host` | 8 | Host workspace hub | host | — | light | WorkspaceNavGrid | Good |
| `/host/onboarding` | 8 | Become a host | host | — | light | Textarea, dark pitch | Good |
| `/host/events` | 8 | Event list | host | — | light | Media rows, EmptyState | Good |
| `/host/events/new` | 7 | Create event | host | Still long form | light | Sectioned EventForm + Select | Better |
| `/host/events/[id]` | 8 | Event ops hub | host | — | light | Grouped actions, banner | Better CTAs |
| `/host/events/[id]/edit` | 7 | Edit event | host | Still long form | light | Sectioned EventForm | Better |
| `/host/events/[id]/tickets` | 5 | Ticket types | host | Config CRUD | medium | Forms | OK |
| `/host/events/[id]/tables` | 5 | Tables / seats | host | Assignment CRUD | medium | Forms | OK |
| `/host/events/[id]/attendees` | 5 | Attendees + staff | host | Admin list | medium | Search raw | OK |
| `/host/events/[id]/check-in` | 6 | Door QR scanner | host | Thin shell; workspace OK | medium | CheckInWorkspace | Good door UX |
| `/host/events/[id]/check-in/analytics` | 5 | Check-in stats | analytics | Sparse | medium | Stats | OK |
| `/host/events/[id]/offline-check-in` | 4 | Offline buffer | host | Foundation UI | medium | Explicit stub feel | OK |
| `/host/events/[id]/analytics` | 6 | Per-event analytics | analytics | Ops look | light | StatCard/Trend | OK |
| `/host/events/[id]/ai` | 4 | Event AI drafts | host | Prompt + pre | medium | Scaffold | OK |
| `/host/events/[id]/memory` | 5 | Memory overview | host | Admin chrome | medium | — | OK |
| `/host/events/[id]/memory/edit` | 5 | Edit memory | host | Editor form | medium | — | OK |
| `/host/legacy` | 8 | Preview Legacy | host | Chrome button row | light | LegacyPageView | Good |
| `/host/legacy/edit` | 5 | Edit Legacy profile | host | URL-field admin form | **medium** | No preview | OK |
| `/host/legacy/tier` | 6 | Tier progress | host | Card stack | light | Progress OK | OK |
| `/host/vault` | 5 | Vault inventory | host | Generic list | medium | EmptyState | OK |
| `/host/vault/new` | 5 | Create Vault item | host | Create form | medium | Forms | OK |
| `/host/vault/[id]/edit` | 5 | Edit Vault item | host | Edit form | medium | Forms | OK |
| `/host/vault/earnings` | 5 | Vault earnings | finance | Four StatCards only | medium | StatCard | OK |
| `/host/audience` | 7 | CRM / segments | host | Still dense stats | light | Select filters, EmptyState | Better |
| `/host/followers` | 7 | Follower list | host | — | light | EmptyState, row layout | Good |
| `/host/payouts` | 7 | Balance + requests | finance | — | light | EmptyState, StatusBadge | Good |
| `/host/promos` | 5 | Promo codes | host | Form-above-list | medium | Raw selects | OK |
| `/host/announcements` | 5 | Announcement history | host | Text empty states | medium | — | OK |
| `/host/announcements/new` | 5 | Compose announcement | host | Compose form | medium | — | OK |
| `/host/sponsorships` | 9 | Slots + inquiries | sponsor | — | light | SponsorSlotCard | Good |
| `/host/sponsorships/new` | 8 | Create slot | sponsor | — | light | Preview column | Good |
| `/host/reviews` | 5 | Reply / report | host | Moderation list | medium | Partial | OK |
| `/host/ambassadors` | 5 | Ambassador mgmt | host | List/CRUD | medium | — | OK |
| `/host/ambassadors/[id]` | 5 | Ambassador detail | host | Metrics detail | medium | — | OK |
| `/host/analytics` | 6 | Host analytics | analytics | Ops dashboard | light | StatCard/DataTable | OK |
| `/host/ai` | 4 | AI Copilot | host | Prompt shell | medium | Scaffold | OK |

---

## Admin / finance / support / staff

| Route | Score | Purpose | Type | Main UI problems | Polish | Shared components | Mobile |
|-------|-------|---------|------|------------------|--------|-------------------|--------|
| `/admin` | 8 | Admin hub | admin | — | light | WorkspaceNavGrid | Good |
| `/admin/events` | 4 | All events | admin | Thin list | medium | Skeleton only | OK |
| `/admin/events/review` | 5 | Approve queue | admin | Queue Cards | medium | — | OK |
| `/admin/orders` | 4 | Order lookup | admin | Bare list | medium | — | OK |
| `/admin/tickets` | 5 | Ticket admin | admin | Ops list | medium | — | OK |
| `/admin/payments` | 4 | Payment lookup | finance | Reference dump | medium | — | OK |
| `/admin/refunds` | 5 | Refund review | finance | Queue Cards | medium | — | OK |
| `/admin/payouts` | 5 | Payout review | finance | Evidence forms | medium | Partial StatCard | OK |
| `/admin/ledger` | 5 | Ledger / settlement | finance | Journal list | medium | — | OK |
| `/admin/reviews` | 5 | Moderate reviews | admin | Moderation list | medium | EmptyState | OK |
| `/admin/vault` | 5 | Moderate Vault | admin | Moderation list | medium | DataTable-ish | OK |
| `/admin/memories` | 5 | Moderate memories | admin | Moderation list | medium | — | OK |
| `/admin/sponsorships` | 7 | Moderate sponsorships | sponsor | Ops table (acceptable) | light | DataTable | Good |
| `/admin/legacy` | 5 | Host tiers admin | admin | List + recalc | medium | — | OK |
| `/admin/legacy/tiers` | 5 | Tier thresholds | admin | Threshold form | medium | — | OK |
| `/admin/analytics` | 6 | Platform analytics | analytics | Not designed | light | StatCard/Trend | OK |
| `/admin/analytics/revenue` | 5 | Revenue | analytics | Thin metrics | medium | — | OK |
| `/admin/analytics/events` | 5 | Event trends | analytics | Thin | medium | — | OK |
| `/admin/analytics/hosts` | 5 | Host rankings | analytics | Thin | medium | — | OK |
| `/admin/analytics/support` | 5 | Support proxies | analytics | Placeholders | medium | — | OK |
| `/admin/ai` | 4 | Admin AI | admin | Prompt tool | medium | Scaffold | OK |
| `/admin/support/ai-summary` | 4 | Support AI summary | support | Summary tool | medium | Scaffold | OK |
| `/support` | 7 | Support hub | support | Sparse vs other hubs | light | WorkspaceNavGrid | Good |
| `/support/refunds` | 5 | Escalate refunds | support | Card queue | medium | EmptyState | OK |
| `/staff/check-in/[eventId]` | 6 | Staff door scanner | host | Thin shell | medium | CheckInWorkspace | Good |

---

## Ambassador

| Route | Score | Purpose | Type | Main UI problems | Polish | Shared components | Mobile |
|-------|-------|---------|------|------------------|--------|-------------------|--------|
| `/ambassador` | 5 | Ambassador dashboard | buyer* | Stat Card hub | medium | StatCard | OK |
| `/ambassador/earnings` | 5 | Commissions | finance | Placeholder list | medium | — | OK |

\*Ambassador is a linked-user workspace adjacent to buyer/host CRM.

---

## Recommended implementation waves

### Wave A — Heavy (demo blockers for host path)
1. `/host/events/[id]` — group actions, banner preview, kill button soup  
2. `/host/events/new` + `/host/events/[id]/edit` — section EventForm  
3. `/host/events` — media/status hierarchy on rows  

### Wave B — Medium (buyer + host trust)
4. `/dashboard/orders` + `/dashboard/orders/[id]`  
5. `/dashboard/vault`  
6. `/dashboard/badges` + `/dashboard/following`  
7. `/u/[username]/vault/[itemSlug]`  
8. `/host/payouts`, `/host/audience`, `/host/followers`  
9. `/host/legacy/edit` (form + optional preview)  
10. `/hosts` directory depth  

### Wave C — Medium (ops consistency)
11. Admin/support queues — EmptyState, StatusBadge, DataTable mobile cards  
12. Host vault/promos/announcements CRUD — FormSection pattern  
13. AI pages — light chrome only  

### Wave D — Light (maintain excellence)
14. Home, sponsors, Legacy, ticket QR, hubs — token/spacing consistency only  

---

## Audit metadata

- **Generated for:** pre-deployment premium UI pass  
- **Route count (App Router `page.tsx`):** ~91  
- **Public alias routes:** `/@*` → `/u/*`  
- **Do not redesign** pages scoring ≥8 unless consistency-only fixes  

---

## Post-audit implementation log

_Updates appended as polish waves land._

| Date | Wave | Routes touched | Notes |
|------|------|----------------|-------|
| 2026-07-16 | A | `/host/events`, `/host/events/[id]`, `EventForm` | Media rows, grouped ops actions, sectioned form |
| 2026-07-16 | B | `/dashboard/orders`, `/dashboard/orders/[id]`, `/dashboard/vault`, `/dashboard/badges`, `/u/.../vault/[itemSlug]`, `/host/followers`, `/host/payouts`, `/host/audience` | Receipt polish, VaultCards, badge passport tone, Vault item hero, CRM/payout EmptyStates |
| 2026-07-17 | Design system | Shared UI/layout/data/product components | Field tokens, Alert/Toast/Tooltip, FilterBar/SearchBar/Pagination/MobileDataCard, EventDetailHero + finance/promo cards |
| 2026-07-17 | Public polish | `/`, `/events`, detail, checkout, hosts, auth, demo, Vault, Memory | Commercial landing, FilterBar discovery, sticky tickets, trust checkout, premium auth, exclusive Vault |
| 2026-07-17 | Buyer polish | All `/dashboard/*` buyer routes | TicketPassCard wallet UI, DataTable orders, collectible badges, exclusive Vault, trustworthy refunds |
| 2026-07-17 | Host polish | All `/host/*` routes | Dashboard KPIs + next actions; EventForm/tickets/ops hub; check-in + offline + analytics; aspirational Legacy tier; Vault studio + earnings; CRM announcements/audience; finance payouts; promos/ambassadors |
| 2026-07-17 | Admin/support polish | All `/admin/*`, `/support/*` (+ staff check-in light) | ConfirmAction for finance/moderation; DataTable + FilterBar queues; RefundCard case layouts; StatCard dashboards; no `/admin/users` or `/admin/hosts` routes (absent) |
| 2026-07-17 | Detail consistency pass | All App Router pages + shared cards | `lib/format` (NGN/dates); `PageToolbar`; DashboardShell body spacing; skeletons/EmptyStates; shared card formatters; readable metadata |
| 2026-07-17 | Demo visuals | `/public/demo/**` SVGs | Category-distinct branded abstract SVGs; `npm run generate:demo-assets`; category-aware `resolveEventImage` |
| 2026-07-17 | Responsive QA | Layout shells + sticky CTAs + tables | overflow-x clip; bottom-nav spacer; DataTable cards→lg; sticky CTA padding; hero/header/modal/filter fixes |
| 2026-07-17 | Final verify | Lint + build + PWA; brand spelling scan | All green; no Padéyá/Pàdéyé; `Padeya` only as `nameAscii` |
| 2026-07-17 | Visual acceptance | Auth/host gates, empty flashes, scaffold copy | Skeleton loaders; Alert rejection; demo seed cards; sponsors/vault/events load states |
| 2026-07-18 | Dark mode / theme | App-wide shells + discovery + dashboards + special UI | Class-based theme (`padeya-theme`); semantic tokens; ThemeToggle + Appearance settings; QR high-contrast panel; PWA `theme-color`; see [DARK_MODE_QA.md](./DARK_MODE_QA.md) |
| 2026-07-18 | Global token harden | Shared Card/Button/Stepper/LegacyTierBadge + atmospheric CSS | Accent cards keep primary wash in dark; lime RGB → `var(--primary)` mixes; steppers use primary/ink; alias `border-gray` → `border` |

---

## Dark mode / theme pass (2026-07-18)

Premium theming landed after the 2026-07-17 closeout. Scores above remain layout/polish scores; theme support is now a baseline requirement for all surfaces.

| Area | Theme notes |
|------|-------------|
| Public marketing / marketplace / Legacy | Soft shells + elevated cards; ink heroes/footer fixed |
| Auth / offline / demo | AuthFormCard paper text; offline theme-aware; demo Appearance panel |
| Buyer / host dashboards | Sidebar/topbar/tables; Appearance on `/dashboard/settings` + `/host/settings` |
| Admin / support / finance | Queue cards, DataTables, featured-placement forms |
| Staff check-in / ticket QR | Scanner badges on ink; `TicketQrPanel` white plate always |

**Rules for future polish:** semantic tokens only; no hardcoded gray/white; light/dark/system required; QR stays scannable.

---

## Final closeout

### Pages improved (all App Router surfaces in scope)

**Public (11):** `/`, `/events`, `/events/[slug]`, `/events/[slug]/checkout`, `/hosts`, `/sponsors`, `/sponsors/hosts`, `/login`, `/register`, `/offline`, `/demo`

**Legacy / Vault / Memory (4):** `/u/[username]`, `/u/[username]/vault`, `/u/[username]/vault/[itemSlug]`, `/u/[username]/memories/[eventSlug]`

**Buyer (12):** `/dashboard`, tickets (+ detail + transfer), orders (+ receipt), passport, badges, vault, reviews, refunds (+ new), following

**Host (37):** overview, onboarding, events list/new/detail/edit/tickets/attendees/check-in(+analytics)/offline/tables/memory(+edit)/analytics/ai, legacy(+edit/tier), vault(+new/edit/earnings), audience, followers, announcements(+new), promos, ambassadors(+id), analytics, payouts, sponsorships(+new), reviews, ai

**Admin (22):** overview, events(+review), tickets, orders, payments, refunds, payouts, ledger, reviews, vault, memories, legacy(+tiers), analytics(+revenue/events/hosts/support), sponsorships, ai, support/ai-summary

**Support / staff / ambassador (5):** `/support`, `/support/refunds`, `/staff/check-in/[eventId]`, `/ambassador`, `/ambassador/earnings`

**Total audited:** ~91 `page.tsx` routes (build lists 69 static/dynamic entries; aliases rewrite to `/u/*`).

### Pages intentionally unchanged / absent

| Item | Reason |
|------|--------|
| `/admin/users`, `/admin/hosts`, `/admin/settings` | Routes do not exist — not invented |
| `/host/support` | Route does not exist |
| Buyer profile / notifications (beyond `/dashboard/settings`) | Not invented |
| Legal / help / blog / contact | Blog public + admin CMS shipped (`/blog*`, `/admin/blog*`); legal/help/contact still absent |
| `/sponsors`, `/sponsors/hosts` (structure) | Already strong (≥9); consistency-only if touched |
| Payment / scanner / ticket issuance logic | UI-only mandate — APIs and flows unchanged |
| Backend / Docker / seed scripts | Not in UI polish scope |

### Components improved

- Design system: `Alert`, `Toast`, `Tooltip`, `FilterBar`, `SearchBar`, `Pagination`, `MobileDataCard`, `ConfirmAction`, `PageToolbar`, field tokens (`lib/ui/field.ts`)
- Product: `EventDetailHero`, `TicketPassCard`, `RefundCard`/`SupportCaseCard`, `PayoutCard`, `PromoCodeCard`, `AmbassadorCard`, `EventCard`, `LegacyTierBadge`
- Layout: `DashboardShell`, `WorkspaceShell`, `SiteHeader`, `SiteFooter`, `MobileBottomNav`, `HostScannerDock`, `Modal`, `DataTable`, `PageHeader`, `HeroSection`
- Forms/ops: `EventForm`, `CheckInWorkspace`, `ScanResultCard`, `QrScanner`, `LegacyPageView`
- Format helpers: `lib/format.ts` (`formatNgn`, `formatDateTime`, `formatDate`, `formatPercent`)

### Assets improved

- Regenerated local SVGs under `frontend/public/demo/{events,hosts,vault,memories,sponsors}/`
- Category-distinct branded compositions (music, comedy, tech, gospel, campus, food, sports, art, vault, memories, sponsorship)
- Generator: `npm run generate:demo-assets`
- Category-aware `resolveEventImage` fallbacks

### Verification (2026-07-17)

| Check | Result |
|-------|--------|
| `npm run lint` | Pass |
| `npm run build` | Pass (TypeScript clean; all routes compile) |
| `npm run test:pwa` | Pass (manifest, mobile layout, ticket QR 280, scanner queue, offline) |
| Backend tests | Skipped — backend not touched |
| Brand: Padéyá / Pàdéyé | None found |
| Brand: Padeya in UI copy | None — only `brand.nameAscii` for code-safe use |
| User-facing brand | **Pàdéyá** |
| Broken routes / missing imports | None (build proves) |

### Remaining non-blocking notes

1. Some accent gradients still use `rgb(142_240_18/…)` inline (brand green) rather than CSS variables — visual OK, token cleanup optional.
2. Admin analytics/support still frames some fraud signals as placeholders (product honesty, not scaffold UI).
3. Ambassador commission “owed” remains labeled placeholder until payouts ship.
4. Dense admin nav is topbar-scrolled on tablet; acceptable for ops IA.
5. Real photography can later replace abstract demo SVGs without route changes.
6. Future routes (`/admin/users`, etc.) should reuse the same shells/tables + semantic theme tokens when added.
7. Theme QA checklist and known issues: [DARK_MODE_QA.md](./DARK_MODE_QA.md).
