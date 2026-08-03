/**
 * Ambassador frontend alignment — public /ambassadors + admin Overview.
 * Requires PLAYWRIGHT_PASSWORD (see docs/DEMO_DATA.md). Fails setup if absent.
 */
import { expect, test } from "@playwright/test";

import {
  apiBaseUrl,
  apiPrefix,
  getPersonaCreds,
  loginAs,
} from "./helpers/auth";

function requirePassword(): void {
  const pw =
    process.env.PLAYWRIGHT_PASSWORD?.trim() ||
    process.env.PLAYWRIGHT_DEMO_PASSWORD?.trim() ||
    "";
  if (!pw) {
    throw new Error(
      "AMBFRONT: PLAYWRIGHT_PASSWORD required. See docs/DEMO_DATA.md.",
    );
  }
}

test.describe("ambassador frontend alignment", () => {
  test.beforeAll(() => {
    requirePassword();
  });

  test("public /ambassadors signed-out hero and FAQ", async ({ page }) => {
    await page.goto("/ambassadors", { waitUntil: "domcontentloaded" });
    await expect(
      page.getByRole("heading", {
        name: /Share experiences people will love/i,
      }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Pàdéyá-wide programs" }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Host event campaigns" }),
    ).toBeVisible();
    await expect(page.getByText(/enrollment-controlled/i).first()).toBeVisible();
    await expect(page.getByText(/No host opt-in required/i).first()).toBeVisible();
    await expect(
      page.getByText(/Host must enable \(tick\) per event/i).first(),
    ).toBeVisible();
    await page.getByText("Do hosts need to enable Pàdéyá-wide programs?").click();
    await expect(
      page.getByText(/Hosts only enable Ambassadors when they want their own/i),
    ).toBeVisible();
    await page
      .getByText("What happens if a host campaign and Pàdéyá-wide both apply?")
      .click();
    await expect(
      page.getByText(/Both can pay on the same item/i),
    ).toBeVisible();
    await page.getByText("What happens after a refund?").click();
    await expect(
      page.getByText(/original earning and any later adjustment/i),
    ).toBeVisible();
    await page.getByRole("link", { name: /Sign in to continue/i }).first().click();
    await expect(page).toHaveURL(/login/);
  });

  test("admin Overview ledger cards and navigation", async ({
    page,
    request,
  }) => {
    // Warm API
    const health = await request.post(
      `${apiBaseUrl()}${apiPrefix()}/auth/login`,
      {
        data: {
          login: getPersonaCreds("super_admin")!.email,
          password: getPersonaCreds("super_admin")!.password,
        },
        timeout: 60_000,
      },
    );
    expect(health.ok(), await health.text()).toBeTruthy();

    await loginAs(page, request, "super_admin");
    await page.goto("/admin/ambassadors", { waitUntil: "domcontentloaded" });
    await expect(
      page.getByRole("heading", { name: "Ambassadors", exact: true }),
    ).toBeVisible({ timeout: 60_000 });
    await expect(page.getByText("Active programs & campaigns")).toBeVisible({
      timeout: 60_000,
    });
    await expect(page.getByText("Converted orders")).toBeVisible();
    await expect(page.getByText("Commission owed")).toBeVisible({
      timeout: 30_000,
    });
    // Workspaces always render even if summary is slow
    await expect(page.getByText("Workspaces")).toBeVisible();
    await expect(
      page.getByText(/Pàdéyá-funded|host-funded|Global referral switch/i).first(),
    ).toBeVisible();

    await page.getByRole("link", { name: /^Programs$/ }).first().click();
    await expect(page).toHaveURL(/\/admin\/ambassadors\/programs/);

    await page.goto("/admin/ambassadors");
    await expect(page.getByText("Workspaces")).toBeVisible({ timeout: 60_000 });
    await page.getByRole("link", { name: /^Liabilities$/ }).first().click();
    await expect(page).toHaveURL(/\/admin\/ambassadors\/liabilities/);
    await expect(
      page.getByText(/Referral liabilities|Platform-funded|Host-funded/i).first(),
    ).toBeVisible({ timeout: 60_000 });

    await page.goto("/admin/ambassadors");
    await expect(page.getByText("Workspaces")).toBeVisible({ timeout: 60_000 });
    await page.getByRole("link", { name: /^Campaigns$/ }).first().click();
    await expect(page).toHaveURL(/\/admin\/ambassadors\/campaigns/);
  });

  test("admin API overview summary shape", async ({ request }) => {
    const admin = getPersonaCreds("super_admin")!;
    const login = await request.post(`${apiBaseUrl()}${apiPrefix()}/auth/login`, {
      data: { login: admin.email, password: admin.password },
    });
    expect(login.ok()).toBeTruthy();
    const token = (await login.json()).access_token as string;
    const summary = await request.get(
      `${apiBaseUrl()}${apiPrefix()}/admin/referrals/summary`,
      { headers: { Authorization: `Bearer ${token}` } },
    );
    expect(summary.ok()).toBeTruthy();
    const body = await summary.json();
    for (const key of [
      "active_arrangements",
      "unique_active_ambassadors",
      "converted_orders",
      "commission_owed_total",
      "host_funded_owed",
      "platform_funded_owed",
      "active_platform_programs",
      "active_host_campaigns",
    ]) {
      expect(body).toHaveProperty(key);
    }
  });
});
