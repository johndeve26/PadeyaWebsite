/**
 * Public Event Memories masonry gallery flow.
 * Uses demo completed event island-comedy-night (Sunday Comedy Room).
 */

import { test, expect } from "@playwright/test";

const MEMORIES_PATH = "/events/island-comedy-night/memories";

test.describe("Event memories masonry gallery", () => {
  test("host and community galleries preserve natural ratios", async ({
    page,
  }) => {
    await page.goto(MEMORIES_PATH, {
      waitUntil: "domcontentloaded",
      timeout: 60_000,
    });

    await expect(
      page.getByRole("heading", { name: /Sunday Comedy Room/i }),
    ).toBeVisible({ timeout: 30_000 });

    const hostGallery = page.getByRole("list", {
      name: /host memories gallery/i,
    });
    await expect(hostGallery).toBeVisible();
    const hostTiles = hostGallery.getByRole("listitem");
    await expect(hostTiles.first()).toBeVisible();

    const communityGallery = page.getByRole("list", {
      name: /community memories gallery/i,
    });
    await expect(communityGallery).toBeVisible();

    const hostHeights = await hostTiles.evaluateAll((items) =>
      items.map((el) => el.getBoundingClientRect().height),
    );
    if (hostHeights.length >= 2) {
      const uniqueHeights = new Set(hostHeights.map((h) => Math.round(h)));
      expect(uniqueHeights.size).toBeGreaterThan(1);
    }
  });

  test("lightbox open, navigate, close with focus return", async ({ page }) => {
    await page.goto(MEMORIES_PATH, {
      waitUntil: "domcontentloaded",
      timeout: 60_000,
    });

    const hostGallery = page.getByRole("list", {
      name: /host memories gallery/i,
    });
    await expect(hostGallery).toBeVisible({ timeout: 30_000 });

    const firstTile = hostGallery.getByRole("button").first();
    await firstTile.focus();
    await firstTile.click();

    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();

    const nextBtn = dialog.getByRole("button", { name: /^next$/i });
    if (await nextBtn.isEnabled()) {
      await nextBtn.click();
      await expect(dialog).toContainText(/of/i);
    }

    await page.keyboard.press("Escape");
    await expect(dialog).not.toBeVisible();
    await expect(firstTile).toBeFocused();
  });

  test("footer remains reachable", async ({ page }) => {
    await page.goto(MEMORIES_PATH, {
      waitUntil: "domcontentloaded",
      timeout: 60_000,
    });

    await expect(
      page.getByRole("link", { name: /all memories/i }),
    ).toBeVisible({ timeout: 30_000 });
    await page.getByRole("link", { name: /all memories/i }).scrollIntoViewIfNeeded();
    await expect(page.getByRole("link", { name: /all memories/i })).toBeVisible();
  });

  test("mobile layout has no horizontal overflow", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto(MEMORIES_PATH, {
      waitUntil: "domcontentloaded",
      timeout: 60_000,
    });

    await expect(
      page.getByRole("heading", { name: /community memories/i }),
    ).toBeVisible({ timeout: 30_000 });

    const overflow = await page.evaluate(() => {
      return document.documentElement.scrollWidth > window.innerWidth + 1;
    });
    expect(overflow).toBe(false);
  });

  test("private fan identity is not exposed in community section", async ({
    page,
  }) => {
    await page.goto(MEMORIES_PATH, {
      waitUntil: "domcontentloaded",
      timeout: 60_000,
    });

    const communitySection = page.locator("section", {
      has: page.getByRole("heading", { name: /community memories/i }),
    });
    await expect(communitySection).toBeVisible({ timeout: 30_000 });

    const bodyText = await communitySection.innerText();
    expect(bodyText).not.toMatch(/@/);
    expect(bodyText.toLowerCase()).not.toContain("email");
  });
});
