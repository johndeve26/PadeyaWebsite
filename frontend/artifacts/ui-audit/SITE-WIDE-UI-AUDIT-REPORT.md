# Pàdéyá Site-Wide UI Audit Report

Generated: 2026-07-29T04:36:32Z

## A. Overall verdict

**NOT COMPLETE — BLOCKED** (authenticated visual pack deferred)

Public + shared-component gate: **met**. No open P0/P1 on smoked public layouts. Authenticated fan/host/admin screenshots skipped (no `PLAYWRIGHT_FAN_*` credentials). Remaining ~418 routes not visually smoked.

## B. Theme architecture

- Storage: `localStorage["padeya-theme"]` (`light` | `dark` | `system`)
- Dark class on `document.documentElement`
- Blocking `ThemeScript` prevents FOUC; SSR snapshot is system→light until hydrate
- Tokens: `globals.css` + `tailwind-theme.css`; brand green `#8EF012`
- Details: `theme-architecture.json`

## C. Route coverage

- Total App Router pages: **432**
- Public smoke set: **14** routes × light/dark × desktop/mobile
- Authenticated smoked: **0**
- Inventory: `site-route-inventory.json`

## D. Shared components audited

Priority set: Button, Input, Select, Textarea, Modal, Drawer, Dropdown, Toast, Card, DataTable, EmptyState, SkeletonLoader, Alert, Tabs, Checkbox, Switch, Radio + layout shells.

Fixes shipped: Modal portal, dark autofill, EmptyState icon well, ConnectHome gradient tokens.

## E. Light-mode result

Pass on smoked public routes (desktop + mobile). See `light-mode-results.json`.

## F. Dark-mode result

Pass on smoked public routes; body background not pure white. See `dark-mode-results.json`.

## G. System-theme result

Pass: system+OS dark → `html.dark`; system+OS light → no dark; preference persists across reload. See `system-theme-results.json`.

## H. Public pages

Smoked: home, login, register, forgot-password, events, blog, merch, about, help, faq, pricing, offline, terms, hosts.

## I. Authentication pages

Login/register/forgot-password covered in light+dark. Password reset token flow not separately smoked.

## J. Fan pages

Not visually smoked this pass (credentials required).

## K. Host pages

Not visually smoked this pass.

## L. Admin pages

Not visually smoked this pass.

## M. Forms and controls

Shared field tokens theme-safe; dark autofill added for default inputs; auth-on-dark path retained.

## N. Tables and analytics

DataTable already uses semantic card/surface tokens. Charts not re-run with live host analytics (auth gap).

## O. Dialogs, menus and toasts

Modal now portals like Drawer; Dropdown/Toast use popover/state tokens.

## P. Loading, empty and error states

Skeleton respects reduced motion; EmptyState themed; offline/unauthorized/system pages exist (unauthorized flaky under prior parallel load; terms used in smoke).

## Q. Responsive result

375×812 and 1440×900 covered for smoke set. No overflow observed. See `responsive-results.json`.

## R. Accessibility result

axe-core on home + login (light/dark): **0** critical/serious (color-contrast rule disabled for noise). See `accessibility-results.json`.

## S. Theme flash/hydration result

ThemeScript + `suppressHydrationWarning` in place; dark smoke asserts non-white body background.

## T. Visual regression result

**57** screenshots under `artifacts/ui-audit/screenshots/` (first-capture baseline; manual review, not auto-approved).

## U. Findings

| ID | Severity | Status |
|----|----------|--------|
| UI-P2-001 Modal portal | P2 | fixed |
| UI-P2-002 Dark autofill | P2 | fixed |
| UI-P3-001 EmptyState icon | P3 | fixed |
| UI-P3-002 ConnectHome gradient | P3 | fixed |
| UI-P2-003 Auth visual pack | P2 | **open** |

### FRONTEND FILES CHANGED

- `frontend/src/components/ui/Modal.tsx`
- `frontend/src/components/ui/EmptyState.tsx`
- `frontend/src/styles/globals.css`
- `frontend/src/components/fan-connect/ConnectHome.tsx`
- `frontend/playwright.config.ts`
- `frontend/e2e/**`
- `frontend/package.json` / lockfile
- `frontend/artifacts/ui-audit/**`
- `frontend/.gitignore`

(Also present from prior work: Fan Connect request-policy defaults — separate from this audit.)

### TESTS ADDED

- Playwright theme visual smoke + system theme + axe
- Scripts: `test:e2e:theme`, `test:e2e:visual`, `test:unit`

### SCREENSHOTS CREATED

57 PNG files in `artifacts/ui-audit/screenshots/`

### FRONTEND TEST RESULT

- `test:theme`: pass
- Vitest: 354 passed, 2 failed (pre-existing `runtime-settings.test.ts`)

### PLAYWRIGHT RESULT

- **70 passed**, 0 failed, **2 skipped** (authenticated), ~25s

### ACCESSIBILITY RESULT

- Home + login light/dark: no critical/serious axe violations (contrast rule off)

### FRONTEND BUILD RESULT

- `npm run build`: **pass**

### P0 OPEN

0

### P1 OPEN

0

### P2 OPEN

1 (authenticated visual pack)

### P3 OPEN

0

### REMAINING LIMITATIONS

- No authenticated fan/host/admin screenshots
- ~418 routes not in visual smoke
- color-contrast axe rule disabled
- Firefox/WebKit not run (Chromium only)
- Pre-existing unit test failures in runtime-settings

### RECOMMENDED DEPLOYMENT STEPS

Do **not** deploy from this audit alone. After review: set `PLAYWRIGHT_FAN_*` (and host/admin) env, expand smoke to authenticated packs, then merge. No production deploy requested.
