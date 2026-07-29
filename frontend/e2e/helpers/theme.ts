import type { Page } from "@playwright/test";

/** Must match frontend/src/lib/theme.ts THEME_STORAGE_KEY */
export const THEME_STORAGE_KEY = "padeya-theme";

export type ThemeMode = "light" | "dark" | "system";

/**
 * Apply theme through the real localStorage mechanism via init script
 * so ThemeScript + ThemeProvider resolve the same as production.
 * Call before page.goto — does not reload (avoids navigation races).
 */
export async function applyTheme(
  page: Page,
  preference: ThemeMode,
  options?: { colorScheme?: "light" | "dark" },
): Promise<void> {
  if (options?.colorScheme) {
    await page.emulateMedia({ colorScheme: options.colorScheme });
  } else if (preference === "light" || preference === "dark") {
    await page.emulateMedia({ colorScheme: preference });
  }

  await page.addInitScript(
    ({ key, value }) => {
      try {
        localStorage.setItem(key, value);
        const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
        const dark = value === "dark" || (value !== "light" && prefersDark);
        document.documentElement.classList.toggle("dark", dark);
        document.documentElement.style.colorScheme = dark ? "dark" : "light";
      } catch {
        /* ignore */
      }
    },
    { key: THEME_STORAGE_KEY, value: preference },
  );
}

/** Persist preference on an already-loaded page and reload. */
export async function setThemeAndReload(
  page: Page,
  preference: ThemeMode,
  options?: { colorScheme?: "light" | "dark" },
): Promise<void> {
  if (options?.colorScheme) {
    await page.emulateMedia({ colorScheme: options.colorScheme });
  } else if (preference === "light" || preference === "dark") {
    await page.emulateMedia({ colorScheme: preference });
  }
  await page.evaluate(
    ({ key, value }) => {
      localStorage.setItem(key, value);
    },
    { key: THEME_STORAGE_KEY, value: preference },
  );
  await page.reload({ waitUntil: "domcontentloaded" });
}

export async function assertResolvedTheme(
  page: Page,
  expected: "light" | "dark",
): Promise<void> {
  // Re-run ThemeScript-equivalent sync (WebKit can miss the blocking script race).
  await page
    .evaluate((key) => {
      try {
        const t = localStorage.getItem(key);
        const d = window.matchMedia("(prefers-color-scheme: dark)").matches;
        const dark = t === "dark" || (t !== "light" && d);
        document.documentElement.classList.toggle("dark", dark);
        document.documentElement.style.colorScheme = dark ? "dark" : "light";
      } catch {
        /* ignore */
      }
    }, THEME_STORAGE_KEY)
    .catch(() => undefined);

  await page.waitForFunction(
    (exp) => {
      const dark = document.documentElement.classList.contains("dark");
      return exp === "dark" ? dark : !dark;
    },
    expected,
    { timeout: 10_000 },
  );
}

export async function stabilizePage(page: Page): Promise<void> {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.addStyleTag({
    content: `
      *, *::before, *::after {
        animation-duration: 0s !important;
        animation-delay: 0s !important;
        transition-duration: 0s !important;
        caret-color: transparent !important;
      }
      [data-toast], [aria-live="polite"] { opacity: 0 !important; pointer-events: none !important; }
    `,
  });
  await page.waitForLoadState("domcontentloaded");
  await page.evaluate(() => document.fonts?.ready).catch(() => undefined);
}

export function screenshotPath(
  route: string,
  theme: string,
  project: string,
): string {
  const slug =
    route === "/"
      ? "home"
      : route
          .replace(/^\//, "")
          .replace(/\//g, "__")
          .replace(/\[|\]/g, "");
  return `artifacts/ui-audit/screenshots/${project}__${theme}__${slug}.png`;
}
