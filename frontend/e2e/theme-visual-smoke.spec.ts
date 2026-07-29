import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

import {
  applyTheme,
  assertResolvedTheme,
  screenshotPath,
  stabilizePage,
  type ThemeMode,
} from "./helpers/theme";

/** Public / unauthenticated smoke set (no login required). */
const PUBLIC_SMOKE: { path: string; priority: "P0" | "P1" }[] = [
  { path: "/", priority: "P0" },
  { path: "/login", priority: "P0" },
  { path: "/register", priority: "P0" },
  { path: "/forgot-password", priority: "P1" },
  { path: "/events", priority: "P0" },
  { path: "/blog", priority: "P1" },
  { path: "/merch", priority: "P1" },
  { path: "/about", priority: "P1" },
  { path: "/help", priority: "P1" },
  { path: "/faq", priority: "P1" },
  { path: "/pricing", priority: "P1" },
  { path: "/offline", priority: "P1" },
  { path: "/terms", priority: "P1" },
  { path: "/hosts", priority: "P1" },
];

const THEMES: { preference: ThemeMode; resolved: "light" | "dark"; colorScheme?: "light" | "dark" }[] = [
  { preference: "light", resolved: "light" },
  { preference: "dark", resolved: "dark" },
];

async function gotoSoft(page: import("@playwright/test").Page, path: string) {
  return page.goto(path, {
    waitUntil: "domcontentloaded",
    timeout: 45_000,
  });
}

test.describe("Theme visual smoke (public)", () => {
  for (const theme of THEMES) {
    for (const route of PUBLIC_SMOKE) {
      test(`${theme.preference} · ${route.path}`, async ({ page }, testInfo) => {
        await applyTheme(page, theme.preference, {
          colorScheme: theme.resolved,
        });
        const response = await gotoSoft(page, route.path);
        const status = response?.status() ?? 0;
        expect(status).toBeLessThan(500);

        await stabilizePage(page);
        await assertResolvedTheme(page, theme.resolved);

        const body = page.locator("body");
        await expect(body).toBeVisible();

        const project = testInfo.project.name;
        await page.screenshot({
          path: screenshotPath(route.path, theme.preference, project),
          fullPage: false,
        });

        // No blank white flash on dark: background should not be pure white when dark.
        if (theme.resolved === "dark") {
          const bg = await page.evaluate(() =>
            getComputedStyle(document.body).backgroundColor,
          );
          expect(bg).not.toMatch(/^rgb\(\s*255,\s*255,\s*255\s*\)$/);
        }
      });
    }
  }
});

test.describe("System theme resolution", () => {
  test("system + OS dark → html.dark", async ({ page }) => {
    await applyTheme(page, "system", { colorScheme: "dark" });
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await stabilizePage(page);
    await assertResolvedTheme(page, "dark");
  });

  test("system + OS light → no html.dark", async ({ page }) => {
    await applyTheme(page, "system", { colorScheme: "light" });
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await stabilizePage(page);
    await assertResolvedTheme(page, "light");
  });

  test("theme persists across reload", async ({ page }) => {
    await applyTheme(page, "dark", { colorScheme: "dark" });
    await page.goto("/events", { waitUntil: "domcontentloaded" });
    await assertResolvedTheme(page, "dark");
    await page.reload({ waitUntil: "domcontentloaded" });
    await assertResolvedTheme(page, "dark");
    const stored = await page.evaluate(
      (key) => localStorage.getItem(key),
      "padeya-theme",
    );
    expect(stored).toBe("dark");
  });
});

test.describe("Accessibility smoke (critical public)", () => {
  for (const preference of ["light", "dark"] as const) {
    test(`axe · home · ${preference}`, async ({ page }) => {
      await applyTheme(page, preference, { colorScheme: preference });
      await page.goto("/", { waitUntil: "domcontentloaded" });
      await stabilizePage(page);
      await assertResolvedTheme(page, preference);

      const results = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa"])
        .disableRules(["color-contrast"]) // sampled separately; charts/marketing can noise
        .analyze();

      const critical = results.violations.filter(
        (v) => v.impact === "critical" || v.impact === "serious",
      );
      expect(
        critical,
        critical.map((v) => `${v.id}: ${v.help}`).join("\n"),
      ).toEqual([]);
    });

    test(`axe · login · ${preference}`, async ({ page }) => {
      await applyTheme(page, preference, { colorScheme: preference });
      await page.goto("/login", { waitUntil: "domcontentloaded" });
      await stabilizePage(page);
      await assertResolvedTheme(page, preference);

      const results = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa"])
        .disableRules(["color-contrast"])
        .analyze();

      const critical = results.violations.filter(
        (v) => v.impact === "critical" || v.impact === "serious",
      );
      expect(critical).toEqual([]);
    });
  }
});

test.describe("Authenticated routes", () => {
  test.skip(
    !process.env.PLAYWRIGHT_FAN_EMAIL || !process.env.PLAYWRIGHT_FAN_PASSWORD,
    "Set PLAYWRIGHT_FAN_EMAIL / PLAYWRIGHT_FAN_PASSWORD for authenticated visual pack",
  );

  test("fan dashboard theme (skipped without credentials)", async ({ page }) => {
    // Placeholder — enabled when env credentials exist.
    await applyTheme(page, "dark", { colorScheme: "dark" });
    await page.goto("/login");
    await page.getByLabel(/email/i).fill(process.env.PLAYWRIGHT_FAN_EMAIL!);
    await page.getByLabel(/password/i).fill(process.env.PLAYWRIGHT_FAN_PASSWORD!);
    await page.getByRole("button", { name: /sign in|log in/i }).click();
    await page.waitForURL(/dashboard/, { timeout: 30_000 });
    await assertResolvedTheme(page, "dark");
  });
});
