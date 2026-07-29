import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

import {
  applyTheme,
  assertResolvedTheme,
  stabilizePage,
} from "./helpers/theme";

/** Public critical pages with color-contrast re-enabled. */
const PAGES = [
  "/",
  "/login",
  "/register",
  "/events",
  "/blog",
] as const;

test.describe("Public contrast (axe color-contrast enabled)", () => {
  for (const preference of ["light", "dark"] as const) {
    for (const path of PAGES) {
      test(`${preference} · ${path}`, async ({ page }) => {
        await applyTheme(page, preference, { colorScheme: preference });
        await page.goto(path, { waitUntil: "domcontentloaded", timeout: 45_000 });
        await stabilizePage(page);
        await assertResolvedTheme(page, preference);

        const results = await new AxeBuilder({ page })
          .withTags(["wcag2a", "wcag2aa"])
          .analyze();

        const critical = results.violations.filter(
          (v) => v.impact === "critical" || v.impact === "serious",
        );

        // Record full list in attachment for review; assert empty critical/serious.
        await test.info().attach(`axe-${preference}-${path.replace(/\//g, "_") || "home"}`, {
          body: JSON.stringify(results.violations, null, 2),
          contentType: "application/json",
        });

        expect(
          critical,
          critical
            .map((v) => `${v.id} (${v.impact}): ${v.help}`)
            .join("\n"),
        ).toEqual([]);
      });
    }
  }
});
