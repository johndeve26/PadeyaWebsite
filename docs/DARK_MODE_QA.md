# Dark mode QA

Premium **light / dark / system** theming for the Pàdéyá frontend.  
**Scope:** entire frontend — public, buyer, host, admin, support, PWA chrome. Not homepage-only and not a crude invert.

**Invariants**
- Semantic tokens only for themed chrome (no gray-scale Tailwind, no `bg-white` page cards)
- Every new component must support light / dark / system
- Fixed `--ink` / `--paper` for brand heroes, footer, QR plate — never theme-flipped
- Primary CTAs: lime + ink foreground (never light text on lime)

**Companions:** [BRAND_GUIDE.md](./BRAND_GUIDE.md) · [UI_PREMIUM_AUDIT.md](./UI_PREMIUM_AUDIT.md) · [FRONTEND_ROUTES.md](./FRONTEND_ROUTES.md)

---

## Theme architecture

| Piece | Path | Role |
| --- | --- | --- |
| Preference store | `frontend/src/lib/theme.ts` | `light` \| `dark` \| `system`; `padeya-theme` localStorage; resolve + apply |
| FOUC script | `ThemeScript` + `themeInitScript` | Pre-paint `<html class="dark">` + `theme-color` |
| Provider | `ThemeProvider` | Hydrate store, OS `prefers-color-scheme`, cross-tab storage |
| Hook | `useTheme()` | Preference + resolved theme + setters |
| Toggle | `ThemeToggle` | Cycle (nav/topbar) or segmented Light/Dark/System |
| Settings UI | `ThemeAppearanceCard` | Account appearance block |
| Tokens | `frontend/src/styles/globals.css` | `:root` / `.dark` semantic CSS variables |
| Tailwind | `frontend/src/styles/tailwind-theme.css` | `@theme inline` + `@custom-variant dark (&:where(.dark, .dark *))` |

**Single approach:** class-based dark on `<html class="dark">` only.  
Do **not** use `data-theme`, Tailwind `media` darkMode, or competing color configs in `tailwind.config.ts`.

**Preference → resolve:**

- `light` → light tokens  
- `dark` → dark tokens  
- `system` → follows `prefers-color-scheme`

**Controls:**

| Surface | Control |
| --- | --- |
| Site header / mobile menu | Compact / full cycle toggle |
| Buyer / host / admin / support topbar | Compact cycle toggle |
| `/dashboard/settings` | `ThemeAppearanceCard` (Light / Dark / System) |
| `/host/settings` | Same |
| `/demo` | `DemoThemePanel` segmented control |

---

## Token strategy

### Rules (required for all new UI)

1. Use **semantic** utilities: `bg-background`, `bg-surface`, `bg-surface-elevated`, `bg-surface-inset`, `bg-card`, `bg-muted`, `text-foreground`, `text-heading`, `text-body`, `text-muted-foreground`, `border-border`, `ring-focus-ring`, etc.
2. Avoid hardcoded `bg-white` / `bg-black` / gray scales / random hex in components.
3. Prefer brand tokens / CSS variables over one-off colors.
4. Every new component must support **light**, **dark**, and **system**.
5. **QR code area** must stay high-contrast for scanning: fixed white plate + black modules (`TicketQrPanel`), even when surrounding UI is dark.
6. On intentional ink heroes/footers, use fixed `--ink` / `--paper` (or `bg-ink` / `text-paper`), not theme-flipped grays.

### Layering recipe (dark)

1. **Page:** `bg-background` (`#0a0a0a`)  
2. **Soft shell / section:** `bg-surface` or `bg-muted`  
3. **Cards / elevated chrome:** `bg-card` / `dark:bg-surface-elevated` (`#1a1a1a`)  
4. **Nested cells / tiers / chips:** `bg-surface-inset` or `bg-surface-muted` — never another flat `bg-card` on `bg-card`  
5. **Body copy:** `text-foreground` / `text-body`; reserve `text-muted-foreground` for meta  
6. **Primary CTA:** lime (`--primary`) with **ink** foreground — never white text on lime  

### Fixed vs themeable

| Token | Behavior |
| --- | --- |
| `--ink` / `--paper` | Never theme-flipped — heroes, footer, true-black CTAs, QR plate context |
| `--background`, `--surface`, `--card`, `--border`, text tokens | Flip under `.dark` |
| `--brand-green` / `--primary` | Same lime accent both themes; `--primary-foreground` = ink |
| `--brand-black` / `--brand-white` | Themeable chrome aliases (legacy utilities) |

### Key files

- Semantic variables: `frontend/src/styles/globals.css` (`:root` + `.dark`)  
- Tailwind mapping: `frontend/src/styles/tailwind-theme.css`  
- Form chrome: `frontend/src/lib/ui/field.ts`  
- Shared Card/Button/Badge/Alert/DataTable: `frontend/src/components/ui/*`  

---

## Pages audited

### Public

| Route | Notes |
| --- | --- |
| `/` | Ink hero kept; content bands + marketplace cards layered; final CTA light before footer |
| `/events` (+ discovery landings, category/location/chips) | Filters elevated; EventCard / Pàdéyá Picks elevated |
| `/events/[slug]` | Panels, tiers (inset), map/privacy, trust sidebar, sticky bar |
| `/events/[slug]/checkout` | Soft shell + forms |
| `/hosts`, `/sponsors`, `/sponsors/hosts` | Marketplace cards + lookup/forms |
| `/u/[username]`, `/@[username]` | Legacy public renderer |
| `/u/.../vault`, vault item, memories | Locked blur + badges; unlock CTA contrast |
| `/f/[username]` | Fan Passport public |
| `/login`, `/register` | Ink auth shell + elevated form card |
| `/demo` | Theme panel |
| `/offline` | Theme-aware card on `bg-background` |

Legal / help / blog public routes: **blog shipped** (`/blog`, category/tag/author hubs, post detail). Legal/help still absent.

### Buyer

`/dashboard`, tickets (+ QR detail + transfer), orders, passport (+ settings privacy), badges, vault, reviews, refunds (+ new), following, **`/dashboard/settings` (Appearance)**.

### Host

`/host` hub, onboarding, events + Event Studio, check-in / offline / analytics, Legacy Studio, Vault Studio, audience, followers, announcements, promos, ambassadors, payouts, sponsorships, reviews, **`/host/settings` (Appearance)**.

### Admin / support / staff

Admin hubs (events, tickets, orders, payments, refunds, payouts, ledger, reviews, vault, memories, legacy, analytics, taxonomy, featured placements, sponsorships, AI, CMS), `/support/*`, `/staff/check-in/[eventId]`.

---

## Components audited

| Area | Components / notes |
| --- | --- |
| Theme | `ThemeProvider`, `ThemeScript`, `ThemeToggle`, `ThemeAppearanceCard`, `DemoThemePanel` |
| Layout | `SiteHeader`, `SiteFooter`, `WorkspaceShell`, `DashboardShell`, `DashboardSidebar`, `DashboardTopbar`, `WorkspaceBreadcrumbs` |
| UI primitives | `Card`, `Button`, `Badge`, `StatusBadge`, `Alert`, `Toast`, `Modal`, `Dropdown`, `Tabs`, `Input`/`Select`/`Textarea`, `DataTable`, `FilterBar`, `EmptyState`, `Skeleton*`, `ConfirmAction` |
| Discovery | `EventDiscoveryView`, `FacetedFilterBar`, `HeroDiscoverySearch`, `PadeyaPicksSection`, `FeaturedPlacementCard`, `LocationChips`, `TaxonomyChips`, `EventCard` |
| Event detail | `EventPublicView`, `EventDetailPanel`, `TicketTierList`, `MapPreviewCard`, `EventLocationMapCard`, `EventLocationPrivacyNotice`, `RelatedDiscovery*` |
| Legacy / Vault | `LegacyPublicPageRenderer`, studio editors, `PublicVaultItemCard`, `VaultItemLockedPanel`, `VaultCard`, `TicketQrPanel` |
| Check-in | `CheckInWorkspace`, `ScanResultCard`, `QrScanner` |
| Analytics | `MultiMetricTrend`, `AnalyticsFunnel`, `TrendPanel`, `StatCard` sparklines |
| PWA | Manifest `theme_color` / `background_color`, `THEME_COLOR` metas, SW precache offline shell |

---

## Remaining known issues

1. **Google Maps embeds** stay light (third-party iframe). Labels/overlays are themed; map tiles are not.
2. **Installed PWA** `manifest.theme_color` is a single value (`#0a0a0a`). Runtime browser chrome follows resolved theme via `theme-color` metas.
3. **Some brand-green washes** still use `rgb(142_240_18/…)` inline — visually fine; prefer `color-mix` with `var(--primary)` when touching those lines.
4. **SERP mock** in Event Studio SEO preview intentionally uses Google-like hex on a fixed `bg-paper` plate.
5. **Dense admin nav** on tablet remains scrollable topbar IA (not a theme bug).
6. Future routes must reuse shells + semantic tokens from day one.

---

## Manual QA checklist

### Preference & chrome

- [ ] System preference: OS light → site light; OS dark → site dark  
- [ ] Explicit Light / Dark override OS; System returns to OS  
- [ ] Setting persists after refresh (`localStorage` key `padeya-theme`)  
- [ ] Cross-tab: change theme in one tab → other tab follows  
- [ ] No FOUC flash of wrong theme on hard reload  
- [ ] Mobile browser bar / `theme-color` matches resolved theme  
- [ ] Focus ring visible on ThemeToggle (keyboard Tab)  
- [ ] Appearance on `/dashboard/settings` and `/host/settings` shows Light / Dark / System labels  

### Visual (both themes)

- [ ] Text readable (body + muted meta; no tiny faint captions for critical info)  
- [ ] Cards layered (not flat mush on soft shells)  
- [ ] Borders / table separators visible  
- [ ] Inputs: visible border, readable label + placeholder, clear disabled state  
- [ ] Buttons: hover / focus / active; primary = lime + **black** text  
- [ ] Danger / warning / success alerts readable (not color-only)  
- [ ] Modals / dropdowns use popover surfaces  
- [ ] Empty + loading states readable  

### Special surfaces

- [ ] Ticket QR: white plate, black modules, scannable in dark mode (`TicketQrPanel`)  
- [ ] Check-in scanner: high contrast; scan count / status badges readable on ink header  
- [ ] Maps: exact / approximate labels readable; placeholders not broken  
- [ ] Charts: bars/labels use chart tokens; no invisible labels in dark  
- [ ] Ink heroes/footer: paper/primary text, not faint theme gray  
- [ ] Offline page (`/offline`) readable in light and dark  
- [ ] Logo: light mark on light chrome, dark mark on ink / dark surfaces (`Logo variant="auto"`)  

### Smoke

- [ ] `cd frontend && npm run lint`  
- [ ] `cd frontend && npm run build`  
- [ ] `cd frontend && npm run test:theme`  
- [ ] `cd frontend && npm run test:pwa`  

---

## Document rules (summary)

| Do | Don’t |
| --- | --- |
| Semantic tokens | Hardcoded gray/white/black utilities |
| Support light / dark / system | Assume light-only cards |
| Ink + paper for brand heroes | Theme-flip true black/white brand blocks |
| White QR plate + black modules | Theme-colored QR modules |
| `text-primary-foreground` (ink) on lime | White text on lime |
| Visible borders + focus rings | Faint borders / missing focus |
