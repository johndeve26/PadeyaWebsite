import type { Config } from "tailwindcss";

/**
 * Pàdéyá — Tailwind CSS v4
 *
 * Theme colors and dark mode are NOT configured here.
 * They live in CSS (single source of truth):
 *
 *   src/styles/globals.css        → :root / .dark CSS variables
 *   src/styles/tailwind-theme.css → @theme inline + @custom-variant dark
 *
 * Dark mode approach (only one — do not mix):
 *   Class-based: <html class="dark"> via ThemeProvider / ThemeScript
 *
 * Do not add:
 *   - theme.extend.colors (conflicts with @theme CSS variables)
 *   - darkMode: "media" (conflicts with ThemeProvider)
 *   - data-theme selectors (we use class="dark" only)
 */
const config = {
  // Content paths are auto-detected by Tailwind v4 + @tailwindcss/postcss.
  // Keep this file as documentation / editor tooling anchor only.
} satisfies Config;

export default config;
