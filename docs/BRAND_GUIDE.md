# Brand guide

## Name

**Pàdéyá** (accents matter in product copy). ASCII fallback where systems cannot render diacritics: `Padeya` (`brand.nameAscii` only — not in UI sentences).

## Personality

modern · premium · youthful · event-driven · bold · trustworthy · creator-friendly

## Logo

Use official assets only — do not recreate the mark with text.

| Surface | Asset | When |
| --- | --- | --- |
| Dark / ink | `/brand/padeya-logo-dark-v3.png` | Black heroes, footer, auth ink shell |
| Light | `/brand/padeya-logo-light-v3.png` | White/light headers, elevated cards |

Files live in `frontend/public/brand/`. The React `Logo` component (`variant="auto"`) picks the correct mark from the surface context. Prefer `Logo` over raw `<img>` paths.

## Colors

### Brand primitives

| Token | Hex | Role |
| --- | --- | --- |
| Brand Green | `#8EF012` | Primary accent / CTAs |
| Brand Green Hover | `#7DDA10` | Primary hover |
| Brand Black (ink) | `#000000` | True black — heroes, footer, primary foreground on lime |
| Brand White (paper) | `#FFFFFF` | True white — text on ink, QR plate |

Foundation is black/white. Green is the accent — do not overuse it.  
**Never put white text on lime** — primary buttons use ink (`text-primary-foreground`).

### Semantic UI tokens (required)

Prefer CSS variables / Tailwind semantic utilities over raw hex in components:

| Utility family | Purpose |
| --- | --- |
| `bg-background` / `text-foreground` | Page canvas + default copy |
| `bg-surface` / `bg-surface-elevated` / `bg-surface-inset` | Soft shells, cards, nested cells |
| `bg-card` / `text-card-foreground` | Elevated interactive containers |
| `border-border` / `border-border-strong` | Separators |
| `text-heading` / `text-body` / `text-muted-foreground` | Type hierarchy |
| `bg-primary` / `text-primary-foreground` | Lime CTAs |
| `bg-ink` / `text-paper` | Fixed brand black/white (not theme-flipped) |

Full light/dark maps: `frontend/src/styles/globals.css` and [DARK_MODE_QA.md](./DARK_MODE_QA.md).

Source of truth in code: `frontend/src/lib/brand.ts` + CSS variables (not one-off hex in JSX).

## Typography

- Primary UI font: **Manrope**
- Headings: semibold / bold
- Body: clean and readable
- No serif or decorative fonts

## Theme (light / dark / system)

- Preference: `light` \| `dark` \| `system` (`padeya-theme` localStorage)
- Apply: `<html class="dark">` only (see `frontend/src/lib/theme.ts`)
- Controls: header/topbar `ThemeToggle`; Appearance on `/dashboard/settings` and `/host/settings`
- All future components must support light, dark, and system
- QR codes: always high-contrast white plate + black modules (`TicketQrPanel`)

## UI direction

- Public pages: energetic, bold, clean — brand-first heroes on ink where appropriate
- Dashboards: structured, modern, easy to use — soft shells + elevated cards
- Prefer uncluttered layouts and reusable components
- Colors come from centralized tokens (`brand.ts` + CSS variables), not one-off hex values in components
- Layering: page → soft shell → card → inset — avoid flat same-color stacks in dark mode
