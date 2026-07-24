/**
 * Pàdéyá brand tokens — product identity + pointers into the CSS theme system.
 *
 * Prefer semantic CSS variables from `src/styles/globals.css`
 * (`--background`, `--card`, `--primary`, …) in UI code.
 * Fixed ink/paper stay true black/white for intentional dark brand blocks.
 */

export const brand = {
  name: "Pàdéyá",
  nameAscii: "Padeya",
  tagline: "Discover events. Sell tickets. Build your legacy.",
  colors: {
    green: "#8EF012",
    greenHover: "#7DDA10",
    /** Fixed true black — heroes, footer, ink CTAs (never theme-flipped). */
    ink: "#000000",
    /** Fixed true white — text/icons on ink surfaces (never theme-flipped). */
    paper: "#FFFFFF",
    /**
     * Themeable chrome (CSS `--brand-*`).
     * Remapped under `.dark` via semantic tokens in globals.css.
     */
    black: "#000000",
    white: "#FFFFFF",
    softGray: "#DDDDDD",
    lightGray: "#F4F4F4",
    surfaceDark: "#111111",
    darkGray: "#1A1A1A",
    mediumGray: "#666666",
    borderGray: "#E5E5E5",
  },
  /** Semantic CSS custom properties (light/dark via ThemeProvider). */
  cssVars: {
    background: "--background",
    foreground: "--foreground",
    surface: "--surface",
    surfaceElevated: "--surface-elevated",
    card: "--card",
    primary: "--primary",
    /** Brand-tinted text safe on light surfaces (`text-primary-text`). */
    primaryText: "--primary-text",
    border: "--border",
    mutedForeground: "--muted-foreground",
  } as const,
  fonts: {
    sans: "Manrope, ui-sans-serif, system-ui, sans-serif",
  },
  logos: {
    /** Green + white mark (transparent PNG) — use on dark surfaces / hero */
    dark: "/brand/padeya-logo-dark-v3.png",
    /** Black mark (transparent PNG) — use on light surfaces / header */
    light: "/brand/padeya-logo-light-v3.png",
  },
  heroImage: "/brand/padeya-hero.jpg",
  personality: [
    "modern",
    "premium",
    "youthful",
    "event-driven",
    "bold",
    "trustworthy",
    "creator-friendly",
  ] as const,
} as const;

export type BrandColor = keyof typeof brand.colors;
export type LogoVariant = keyof typeof brand.logos;
