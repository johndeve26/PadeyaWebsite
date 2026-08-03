/**
 * Dual-commission ambassador landing + admin Overview smoke.
 * Requires PLAYWRIGHT_PASSWORD (see docs/DEMO_DATA.md).
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
      "AMBDUAL: PLAYWRIGHT_PASSWORD required. See docs/DEMO_DATA.md.",
    );
  }
}

test.describe("ambassador dual-commission landing", () => {
  test.beforeAll(() => {
    requirePassword();
  });

  test("public /ambassadors signed-out dual copy and FAQ", async ({ page }) => {
    await page.goto("/ambassadors", { waitUntil: "domcontentloaded"});
    await expect(
      page.getByRole("heading", {
        name: /Share experiences people will love/i,
      }),
    ).toBeVisible();
    await expect(
      page.getByText(/host-funded and Pàdéyá-funded earnings/i).first(),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Pàdéyá-wide programs" }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Host event campaigns" }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Your Pàdéyá-wide link" }),
    ).toBeVisible();
    await expect(page.getByText("padeya.com/r/yourusername")).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Fair and transparent earnings" }),
    ).toBeVisible();
    await expect(page.getByText("Illustrative example").first()).toBeVisible();
    await expect(page.getByText("Host-funded").first()).toBeVisible();
    await expect(page.getByText("Funded by Pàdéyá").first()).toBeVisible();
    await expect(
      page.getByText(/does not reduce the host’s settlement/i).first(),
    ).toBeVisible();
    await expect(
      page.getByText(/Two separate earnings/i).first(),
    ).toBeVisible();

    await page
      .getByText("What happens if a host campaign and Pàdéyá-wide program both apply?")
      .click();
    await expect(
      page.getByText(/two separate earnings/i).first(),
    ).toBeVisible();
    await page
      .getByText("Does a live host campaign automatically make me eligible?")
      .click();
    await expect(
      page.getByText(/must be enrolled in that campaign/i),
    ).toBeVisible();
    await page.getByText("What happens after a refund?").click();
    await expect(
      page.getByText(/A full or partial refund may create separate reversal entries/i),
    ).toBeVisible();

    await page.getByRole("link", { name: /Sign in to continue/i }).first().click();
    await expect(page).toHaveURL(/login/);
  });

  test("public /ambassadors mobile dual diagram no overflow", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto("/ambassadors", { waitUntil: "domcontentloaded" });
    const overflow = await page.evaluate(() => {
      const doc = document.documentElement;
      return doc.scrollWidth > doc.clientWidth + 1;
    });
    expect(overflow).toBeFalsy();
    await expect(
      page.getByRole("heading", { name: "Fair and transparent earnings" }),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: /Sign in to continue/i }).first(),
    ).toBeVisible();
  });

  test("admin Overview ledger cards and navigation", async ({
    page,
    request,
  }) => {
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
    await expect(page.getByText("Workspaces")).toBeVisible();
    await page.getByRole("link", { name: /^Programs$/ }).first().click();
    await expect(page).toHaveURL(/\/admin\/ambassadors\/programs/);
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
    ]) {
      expect(body).toHaveProperty(key);
    }
  });
});
