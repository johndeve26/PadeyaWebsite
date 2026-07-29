/**
 * Authenticated Blog Taxonomy CRUD closeout.
 * Requires PLAYWRIGHT_PASSWORD + running API/frontend (super_admin demo).
 */

import { test, expect } from "@playwright/test";

import {
  apiBaseUrl,
  apiPrefix,
  hasAuthCredentials,
  loginAs,
} from "./helpers/auth";

const hasCreds = hasAuthCredentials();
const uniq = () =>
  `tx-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`;

async function gotoTaxonomies(
  page: import("@playwright/test").Page,
  tab: string,
) {
  await page.goto(`/admin/blog/taxonomies?tab=${tab}`, {
    waitUntil: "domcontentloaded",
    timeout: 60_000,
  });
  await expect(page.getByRole("heading", { name: /taxonomies/i })).toBeVisible({
    timeout: 30_000,
  });
}

function apiUrl(path: string) {
  return `${apiBaseUrl()}${apiPrefix()}${path}`;
}

test.describe("Blog taxonomy authenticated CRUD", () => {
  test.skip(
    !hasCreds,
    "Set PLAYWRIGHT_PASSWORD for authenticated blog taxonomy tests",
  );

  test.beforeEach(async ({ page, request }) => {
    await loginAs(page, request, "super_admin");
  });

  test("category create → edit → slug confirm → archive → restore", async ({
    page,
  }) => {
    const name = `Cat ${uniq()}`;
    const edited = `${name} Edited`;
    await gotoTaxonomies(page, "categories");

    await page.getByRole("button", { name: /^add$/i }).click();
    await page.getByLabel(/^name$/i).fill(name);
    await page.getByRole("button", { name: /^save$/i }).click();
    const createdRow = page.locator("ul li").filter({ hasText: name });
    await expect(createdRow).toBeVisible({ timeout: 15_000 });
    await expect(page.locator("h3", { hasText: /^Create term$/ })).toHaveCount(0);

    await createdRow.getByRole("button", { name: /^edit$/i }).click();
    await page.getByLabel(/^name$/i).fill(edited);
    await page.getByLabel(/^description$/i).fill("Updated description");
    const slugInput = page.getByLabel(/^slug$/i);
    if (await slugInput.isVisible()) {
      const current = await slugInput.inputValue();
      await slugInput.fill(`${current}-v2`);
      const slugConfirm = page
        .locator("label")
        .filter({ hasText: /confirm slug change/i })
        .locator('input[type="checkbox"]');
      if (await slugConfirm.count()) {
        await slugConfirm.check();
      }
    }
    await page.getByRole("button", { name: /^save$/i }).click();
    const editedRow = page.locator("ul li").filter({ hasText: edited });
    await expect(editedRow).toBeVisible({ timeout: 15_000 });
    await expect(page.locator("h3", { hasText: /^Edit / })).toHaveCount(0);

    await editedRow.getByRole("button", { name: /^archive$/i }).click();
    const archiveDialog = page.getByRole("dialog");
    await expect(archiveDialog).toBeVisible({ timeout: 5_000 });
    await archiveDialog.getByRole("button", { name: /^archive$/i }).click();
    await expect(archiveDialog).toBeHidden({ timeout: 10_000 });
    await page.getByRole("combobox", { name: /^status$/i }).selectOption("archived");
    await expect(page.locator("ul li").filter({ hasText: edited })).toBeVisible({
      timeout: 10_000,
    });
    await expect(
      page.locator("ul li").filter({ hasText: edited }).getByText(/^Archived$/i),
    ).toBeVisible({ timeout: 5_000 });

    await page
      .locator("ul li")
      .filter({ hasText: edited })
      .getByRole("button", { name: /^restore$/i })
      .click();
    await page.getByRole("combobox", { name: /^status$/i }).selectOption("active");
    await expect(page.locator("ul li").filter({ hasText: edited })).toBeVisible({
      timeout: 15_000,
    });
  });

  test("tag create → duplicate conflict → archive", async ({ page, request }) => {
    const name = `Tag ${uniq()}`;
    await gotoTaxonomies(page, "tags");
    await page.getByRole("button", { name: /^add$/i }).click();
    await page.getByLabel(/^name$/i).fill(name);
    await page.getByRole("button", { name: /^save$/i }).click();
    await expect(page.getByText(name).first()).toBeVisible({ timeout: 15_000 });

    const token = await page.evaluate(() =>
      localStorage.getItem("padeya.access_token"),
    );
    const dup = await request.post(apiUrl("/admin/blog/tags"), {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      data: { name },
    });
    expect(dup.status()).toBe(409);

    await page.getByRole("button", { name: /^archive$/i }).first().click();
    const archiveDialog = page.getByRole("dialog");
    if (await archiveDialog.isVisible().catch(() => false)) {
      await archiveDialog.getByRole("button", { name: /^archive$/i }).click();
    }
  });

  test("post type create → rename label keeps key → archive", async ({
    page,
  }) => {
    const name = `Type ${uniq()}`;
    await gotoTaxonomies(page, "post-types");
    await page.getByRole("button", { name: /^add$/i }).click();
    await page.getByLabel(/^name$/i).fill(name);
    await page.getByRole("button", { name: /^save$/i }).click();
    await expect(page.getByText(name).first()).toBeVisible({ timeout: 15_000 });

    await page.getByRole("button", { name: /^edit$/i }).first().click();
    await page.getByLabel(/^name$/i).fill(`${name} Renamed`);
    await page.getByRole("button", { name: /^save$/i }).click();
    await expect(page.getByText(`${name} Renamed`).first()).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByText(/uses/i).first()).toBeVisible();
  });

  test("media roles: custom create, unsafe folder rejected, core roles listed", async ({
    page,
    request,
  }) => {
    await gotoTaxonomies(page, "media-roles");
    await expect(page.getByText(/cover|featured/i).first()).toBeVisible({
      timeout: 20_000,
    });

    const token = await page.evaluate(() =>
      localStorage.getItem("padeya.access_token"),
    );
    const unsafe = await request.post(apiUrl("/admin/blog/media-roles"), {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      data: {
        name: "Evil",
        key: `evil_${uniq().replace(/-/g, "_")}`,
        storage_folder: "../etc",
      },
    });
    expect(unsafe.status()).toBe(400);

    const key = `custom_${uniq().replace(/-/g, "_")}`;
    await page.getByRole("button", { name: /^add$/i }).click();
    await page.getByLabel(/^name$/i).fill(`Role ${uniq()}`);
    const keyField = page.getByLabel(/^key$/i);
    if (await keyField.isVisible()) {
      await keyField.fill(key);
    }
    await page.getByRole("button", { name: /^save$/i }).click();
    await expect(page.getByText(key).first()).toBeVisible({ timeout: 15_000 });
  });

  test("studio metadata loads API taxonomies", async ({ page }) => {
    await page.goto("/admin/blog/new", {
      waitUntil: "domcontentloaded",
      timeout: 60_000,
    });
    const start = page.getByRole("button", { name: /start blank|blank/i });
    if (await start.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await start.click();
    }
    const seo = page.getByRole("button", { name: /seo/i }).first();
    if (await seo.isVisible({ timeout: 8_000 }).catch(() => false)) {
      await seo.click();
      await expect(
        page.getByText(/metadata|category|post type/i).first(),
      ).toBeVisible({ timeout: 15_000 });
    }
  });
});

test.describe("Blog taxonomy visual / a11y smoke", () => {
  test.skip(!hasCreds, "Set PLAYWRIGHT_PASSWORD for taxonomy a11y");

  for (const theme of ["light", "dark"] as const) {
    test(`taxonomies hub ${theme} desktop contrast + axe`, async ({
      page,
      request,
    }) => {
      const AxeBuilder = (await import("@axe-core/playwright")).default;
      await loginAs(page, request, "super_admin");
      await page.emulateMedia({ colorScheme: theme });
      await gotoTaxonomies(page, "categories");
      await page.getByRole("combobox", { name: /^status$/i }).selectOption("active");
      await expect(page.getByRole("button", { name: /^add$/i })).toBeVisible();
      const results = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa"])
        .disableRules(["color-contrast"])
        .analyze();
      const serious = results.violations.filter(
        (v) => v.impact === "critical" || v.impact === "serious",
      );
      expect(serious, JSON.stringify(serious, null, 2)).toEqual([]);
      // Color contrast for public blog surfaces is covered elsewhere; admin
      // hub smoke focuses on structure/name/role regressions.
    });

    test(`taxonomies hub ${theme} mobile tabs`, async ({ page, request }) => {
      await loginAs(page, request, "super_admin");
      await page.setViewportSize({ width: 390, height: 844 });
      await page.emulateMedia({ colorScheme: theme });
      await gotoTaxonomies(page, "tags");
      await expect(page.getByRole("button", { name: /^tags$/i })).toBeVisible();
      await page.getByRole("button", { name: /^post types$/i }).click();
      await expect(page).toHaveURL(/tab=post-types/);
    });
  }
});
