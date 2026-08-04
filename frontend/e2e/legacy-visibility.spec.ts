import { expect, test } from "@playwright/test";

test.describe("Legacy visibility", () => {
  test("how Legacy works page explains score vs tier", async ({ page }) => {
    await page.goto("/legacy");
    await expect(
      page.getByRole("heading", { name: "How Legacy works" }),
    ).toBeVisible();
    await expect(page.getByText("Score versus tier")).toBeVisible();
    await expect(page.getByText("Verified rating", { exact: true })).toBeVisible();
    await expect(page.getByText("30%", { exact: true }).first()).toBeVisible();
    await expect(
      page.getByText(
        /Legacy reflects verified historical activity on Pàdéyá\. It is not a guarantee/i,
      ),
    ).toBeVisible();
  });

  test("public host Legacy summary shows whole-number score when trust payload present", async ({
    page,
  }) => {
    await page.goto("/hosts");
    const firstHost = page.locator('a[href^="/@"]').first();
    if ((await firstHost.count()) === 0) {
      test.skip(true, "No public hosts available in this environment");
      return;
    }
    await firstHost.click();
    await page.waitForURL(/\/@|\/u\//);
    const summary = page.getByLabel(/Legacy Score:/i);
    if ((await summary.count()) === 0) {
      test.skip(true, "Host page missing legacy_trust summary");
      return;
    }
    await expect(summary).toBeVisible();
    await expect(page.getByText(/\/ 100/).first()).toBeVisible();
    const howLink = page.getByRole("link", { name: /How Legacy works/i }).first();
    await expect(howLink).toBeVisible();
    await howLink.click();
    await expect(page).toHaveURL(/\/legacy/);
  });

  test("legacy summary fits mobile viewport", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto("/legacy");
    await expect(
      page.getByRole("heading", { name: "How Legacy works" }),
    ).toBeVisible();
    const scrollWidth = await page.evaluate(
      () => document.documentElement.scrollWidth,
    );
    const clientWidth = await page.evaluate(
      () => document.documentElement.clientWidth,
    );
    expect(scrollWidth).toBeLessThanOrEqual(clientWidth + 1);
  });
});
