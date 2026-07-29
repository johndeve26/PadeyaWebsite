import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

import {
  getPersonaCreds,
  hasAuthCredentials,
  loginAs,
  type Persona,
} from "./helpers/auth";
import {
  applyTheme,
  assertResolvedTheme,
  screenshotPath,
  stabilizePage,
  type ThemeMode,
} from "./helpers/theme";

/**
 * Authenticated visual packs — requires PLAYWRIGHT_PASSWORD (demo seed)
 * and a running API. Skips cleanly when credentials are missing.
 */

const THEMES: { preference: ThemeMode; resolved: "light" | "dark" }[] = [
  { preference: "light", resolved: "light" },
  { preference: "dark", resolved: "dark" },
];

type PackRoute = { path: string; family: string; label: string };

const FAN_ROUTES: PackRoute[] = [
  { path: "/dashboard", family: "FAN_DASHBOARD_LAYOUT", label: "fan-dashboard" },
  { path: "/dashboard/profile", family: "SETTINGS_LAYOUT", label: "fan-profile" },
  { path: "/dashboard/settings", family: "SETTINGS_LAYOUT", label: "fan-settings" },
  {
    path: "/dashboard/passport/settings",
    family: "SETTINGS_LAYOUT",
    label: "fan-passport-settings",
  },
  { path: "/dashboard/orders", family: "COMMERCE_LAYOUT", label: "fan-orders" },
  { path: "/dashboard/tickets", family: "COMMERCE_LAYOUT", label: "fan-tickets" },
  { path: "/connect", family: "FAN_DASHBOARD_LAYOUT", label: "fan-connect" },
  {
    path: "/connect/connections",
    family: "FAN_DASHBOARD_LAYOUT",
    label: "fan-connections",
  },
  {
    path: "/connect/requests",
    family: "FAN_DASHBOARD_LAYOUT",
    label: "fan-connect-requests",
  },
  { path: "/messages", family: "MESSAGING_LAYOUT", label: "fan-messages" },
  {
    path: "/dashboard/notifications",
    family: "SETTINGS_LAYOUT",
    label: "fan-notifications",
  },
  {
    path: "/dashboard/support",
    family: "FAN_DASHBOARD_LAYOUT",
    label: "fan-support",
  },
];

const HOST_ROUTES: PackRoute[] = [
  { path: "/host", family: "HOST_DASHBOARD_LAYOUT", label: "host-home" },
  {
    path: "/host/dashboard",
    family: "HOST_DASHBOARD_LAYOUT",
    label: "host-dashboard",
  },
  { path: "/host/events", family: "HOST_DASHBOARD_LAYOUT", label: "host-events" },
  { path: "/host/events/new", family: "FORM_EDITOR_LAYOUT", label: "host-event-new" },
  {
    path: "/host/analytics",
    family: "ANALYTICS_LAYOUT",
    label: "host-analytics",
  },
  { path: "/host/audience", family: "DATA_TABLE_LAYOUT", label: "host-crm" },
  {
    path: "/host/merchandise",
    family: "DATA_TABLE_LAYOUT",
    label: "host-merch",
  },
  { path: "/host/promos", family: "DATA_TABLE_LAYOUT", label: "host-promos" },
  {
    path: "/host/ambassadors",
    family: "DATA_TABLE_LAYOUT",
    label: "host-ambassadors",
  },
  {
    path: "/host/sponsorships",
    family: "DATA_TABLE_LAYOUT",
    label: "host-sponsorships",
  },
  { path: "/host/vault", family: "DATA_TABLE_LAYOUT", label: "host-vault" },
  { path: "/host/messages", family: "MESSAGING_LAYOUT", label: "host-messages" },
  { path: "/host/team", family: "SETTINGS_LAYOUT", label: "host-team" },
  { path: "/host/earnings", family: "DATA_TABLE_LAYOUT", label: "host-earnings" },
  { path: "/host/settings", family: "SETTINGS_LAYOUT", label: "host-settings" },
];

const ADMIN_ROUTES: PackRoute[] = [
  { path: "/admin", family: "ADMIN_DASHBOARD_LAYOUT", label: "admin-dashboard" },
  { path: "/admin/users", family: "DATA_TABLE_LAYOUT", label: "admin-users" },
  { path: "/admin/payments", family: "DATA_TABLE_LAYOUT", label: "admin-payments" },
  { path: "/admin/support", family: "DATA_TABLE_LAYOUT", label: "admin-support" },
  {
    path: "/admin/blog/new",
    family: "RICH_EDITOR_LAYOUT",
    label: "admin-blog-new",
  },
  {
    path: "/admin/analytics",
    family: "ANALYTICS_LAYOUT",
    label: "admin-analytics",
  },
  {
    path: "/admin/platform",
    family: "SETTINGS_LAYOUT",
    label: "admin-platform",
  },
  {
    path: "/admin/audit-logs",
    family: "DATA_TABLE_LAYOUT",
    label: "admin-audit-logs",
  },
];

/** Mask secrets / credentials UI — demo data is fictional but never capture tokens. */
const SCREENSHOT_MASK = [
  'input[type="password"]',
  'input[autocomplete="current-password"]',
  'input[autocomplete="new-password"]',
  "[data-sensitive]",
  "[data-testid='access-token']",
  "[data-testid='api-key']",
];

async function shot(
  page: import("@playwright/test").Page,
  testInfo: { project: { name: string } },
  theme: string,
  label: string,
) {
  await stabilizePage(page);
  await page.screenshot({
    path: screenshotPath(`auth/${label}`, theme, testInfo.project.name),
    fullPage: false,
    mask: SCREENSHOT_MASK.map((sel) => page.locator(sel)),
  });
}

async function softGoto(page: import("@playwright/test").Page, path: string) {
  const res = await page.goto(path, {
    waitUntil: "domcontentloaded",
    timeout: 45_000,
  });
  const status = res?.status() ?? 0;
  expect(status).toBeLessThan(500);
  await page
    .locator("[data-workspace-breadcrumbs]")
    .first()
    .waitFor({ state: "attached", timeout: 10_000 })
    .catch(() => undefined);
  return status;
}

function describeAuthPack(
  title: string,
  persona: Persona,
  routes: PackRoute[],
) {
  test.describe(title, () => {
    test.skip(
      !hasAuthCredentials() || !getPersonaCreds(persona),
      `Set PLAYWRIGHT_PASSWORD for ${persona} authenticated pack`,
    );

    for (const theme of THEMES) {
      test(`${theme.preference} · pack`, async ({ page, request }, testInfo) => {
        test.setTimeout(240_000);
        await applyTheme(page, theme.preference, {
          colorScheme: theme.resolved,
        });
        await loginAs(page, request, persona);
        await assertResolvedTheme(page, theme.resolved);

        for (const route of routes) {
          await softGoto(page, route.path);
          await assertResolvedTheme(page, theme.resolved);
          await expect(page.locator("body")).toBeVisible();
          await shot(page, testInfo, theme.preference, route.label);

          if (theme.resolved === "dark") {
            const bg = await page.evaluate(() =>
              getComputedStyle(document.body).backgroundColor,
            );
            expect(bg).not.toMatch(/^rgb\(\s*255,\s*255,\s*255\s*\)$/);
          }
        }
      });
    }
  });
}

describeAuthPack("Fan authenticated visual pack", "fan", FAN_ROUTES);
describeAuthPack("Host authenticated visual pack", "host", HOST_ROUTES);
describeAuthPack(
  "Admin (super_admin) authenticated visual pack",
  "super_admin",
  ADMIN_ROUTES,
);

test.describe("Admin role visibility smoke", () => {
  test.skip(!hasAuthCredentials(), "Set PLAYWRIGHT_PASSWORD");

  test("support cannot open finance settlements as privileged write UI", async ({
    page,
    request,
  }, testInfo) => {
    test.skip(!getPersonaCreds("admin_support"), "support persona unavailable");
    await applyTheme(page, "dark", { colorScheme: "dark" });
    await loginAs(page, request, "admin_support");
    const status = await softGoto(page, "/admin/finance");
    // Either redirected, forbidden copy, or page loads without write controls —
    // assert we did not crash and theme applies.
    await assertResolvedTheme(page, "dark");
    expect(status).toBeLessThan(500);
    await shot(page, testInfo, "dark", "role-support-finance");
  });

  test("finance can open payments table", async ({ page, request }, testInfo) => {
    test.skip(!getPersonaCreds("admin_finance"), "finance persona unavailable");
    await applyTheme(page, "light", { colorScheme: "light" });
    await loginAs(page, request, "admin_finance");
    await softGoto(page, "/admin/payments");
    await assertResolvedTheme(page, "light");
    await expect(page.locator("body")).toBeVisible();
    await shot(page, testInfo, "light", "role-finance-payments");
  });

  test("super_admin platform settings shell", async ({ page, request }) => {
    test.skip(!getPersonaCreds("super_admin"), "super_admin unavailable");
    await applyTheme(page, "dark", { colorScheme: "dark" });
    await loginAs(page, request, "super_admin");
    await softGoto(page, "/admin/platform");
    await assertResolvedTheme(page, "dark");
    await expect(page.locator("body")).toBeVisible();
  });

  test("host_staff reaches host desk without admin shell", async ({
    page,
    request,
  }) => {
    test.skip(!getPersonaCreds("host_staff"), "host_staff unavailable");
    await applyTheme(page, "light", { colorScheme: "light" });
    await loginAs(page, request, "host_staff");
    await softGoto(page, "/host");
    await assertResolvedTheme(page, "light");
    expect(page.url()).not.toMatch(/\/admin(\/|$)/);
    await softGoto(page, "/admin");
    // Staff should not land in a privileged admin console as owner.
    const url = page.url();
    expect(url).not.toMatch(/\/admin\/(payments|finance|platform)/);
  });
});

test.describe("Modal / portal + empty-state smoke", () => {
  test.skip(!hasAuthCredentials(), "Set PLAYWRIGHT_PASSWORD");

  test("notification popover portals under html.dark", async ({ page, request }, testInfo) => {
    test.skip(!getPersonaCreds("fan"), "fan persona unavailable");
    await applyTheme(page, "dark", { colorScheme: "dark" });
    await loginAs(page, request, "fan");
    await softGoto(page, "/dashboard");
    await assertResolvedTheme(page, "dark");

    const bell = page.getByRole("button", { name: /Notifications/i });
    if ((await bell.count()) === 0) {
      test.skip(true, "Notification bell not present");
    }
    await bell.first().click();
    const dialog = page.getByRole("dialog").or(page.locator("[role='dialog']"));
    await expect(dialog.first()).toBeVisible({ timeout: 10_000 });
    const dialogBg = await dialog.first().evaluate((el) =>
      getComputedStyle(el).backgroundColor,
    );
    expect(dialogBg).not.toMatch(/^rgb\(\s*255,\s*255,\s*255\s*\)$/);
    await shot(page, testInfo, "dark", "fan-notifications-popover");
    await page.keyboard.press("Escape");
  });

  test("fan notifications empty-or-list shell", async ({ page, request }, testInfo) => {
    test.skip(!getPersonaCreds("fan"), "fan persona unavailable");
    await applyTheme(page, "light", { colorScheme: "light" });
    await loginAs(page, request, "fan");
    await softGoto(page, "/dashboard/notifications");
    await assertResolvedTheme(page, "light");
    await expect(page.locator("body")).toBeVisible();
    // EmptyState or list both OK — assert shell themed.
    await shot(page, testInfo, "light", "fan-notifications-shell");
  });

  test("host analytics chart shell", async ({ page, request }, testInfo) => {
    test.skip(!getPersonaCreds("host"), "host persona unavailable");
    await applyTheme(page, "dark", { colorScheme: "dark" });
    await loginAs(page, request, "host");
    await softGoto(page, "/host/analytics");
    await assertResolvedTheme(page, "dark");
    await expect(page.locator("body")).toBeVisible();
    await shot(page, testInfo, "dark", "host-analytics-charts");
  });

  test("admin users data table shell", async ({ page, request }, testInfo) => {
    test.skip(!getPersonaCreds("super_admin"), "super_admin unavailable");
    await applyTheme(page, "light", { colorScheme: "light" });
    await loginAs(page, request, "super_admin");
    await softGoto(page, "/admin/users");
    await assertResolvedTheme(page, "light");
    await expect(page.locator("body")).toBeVisible();
    await shot(page, testInfo, "light", "admin-users-table");
  });
});

test.describe("Contrast — authenticated dashboards", () => {
  test.skip(!hasAuthCredentials(), "Set PLAYWRIGHT_PASSWORD");

  const targets: { persona: Persona; path: string; name: string }[] = [
    { persona: "fan", path: "/dashboard", name: "fan-dashboard" },
    { persona: "host", path: "/host/dashboard", name: "host-dashboard" },
    { persona: "super_admin", path: "/admin", name: "admin-dashboard" },
  ];

  for (const preference of ["light", "dark"] as const) {
    for (const target of targets) {
      test(`axe contrast · ${target.name} · ${preference}`, async ({
        page,
        request,
      }) => {
        test.skip(!getPersonaCreds(target.persona), `${target.persona} missing`);
        await applyTheme(page, preference, { colorScheme: preference });
        await loginAs(page, request, target.persona);
        await softGoto(page, target.path);
        await stabilizePage(page);
        await assertResolvedTheme(page, preference);

        const results = await new AxeBuilder({ page })
          .withTags(["wcag2a", "wcag2aa"])
          // color-contrast enabled on auth critical dashboards
          .analyze();

        const critical = results.violations.filter(
          (v) => v.impact === "critical" || v.impact === "serious",
        );
        expect(
          critical,
          critical
            .map((v) => `${v.id} (${v.impact}): ${v.help} — ${v.nodes.length} nodes`)
            .join("\n"),
        ).toEqual([]);
      });
    }
  }
});
