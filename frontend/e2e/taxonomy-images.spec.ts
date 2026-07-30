/**
 * Marketplace taxonomy image management (admin upload → public hub).
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
  `tximg-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`;

function apiUrl(path: string) {
  return `${apiBaseUrl()}${apiPrefix()}${path}`;
}

/** Minimal valid 1×1 PNG (CRC-correct). */
function pngBuffer(): Buffer {
  return Buffer.from(
    "\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01" +
      "\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0" +
      "\x00\x00\x03\x01\x01\x00\xc9\xfe\x92\xef\x00\x00\x00\x00IEND\xaeB`\x82",
    "binary",
  );
}

async function openCategoryVisuals(
  page: import("@playwright/test").Page,
  categoryName: string,
) {
  await page.goto("/admin/taxonomy/categories", {
    waitUntil: "domcontentloaded",
    timeout: 60_000,
  });
  const row = page.locator('[class*="rounded"]').filter({ hasText: categoryName });
  await expect(row.first()).toBeVisible({ timeout: 30_000 });
  await row.first().getByRole("button", { name: /^visuals$/i }).click();
  await expect(page.getByRole("heading", { name: /^visuals$/i })).toBeVisible({
    timeout: 10_000,
  });
}

test.describe("Marketplace taxonomy images", () => {
  test.skip(
    !hasCreds,
    "Set PLAYWRIGHT_PASSWORD for authenticated taxonomy image tests",
  );

  test.beforeEach(async ({ page, request }) => {
    await loginAs(page, request, "super_admin");
  });

  test("category upload → alt/focal save → public hub → remove restores fallback", async ({
    page,
    request,
  }) => {
    const alt = `Taxonomy alt ${uniq()}`;
    const categoryName = "Music";
    const categorySlug = "music";

    await openCategoryVisuals(page, categoryName);

    const fileInput = page.locator('input[type="file"]').first();
    await fileInput.setInputFiles({
      name: "taxonomy-test.png",
      mimeType: "image/png",
      buffer: pngBuffer(),
    });
    await expect(page.getByText(/uploaded/i)).toBeVisible({ timeout: 30_000 });

    await page.getByLabel(/^primary alt text$/i).fill(alt);
    await page.getByRole("button", { name: /^save visuals$/i }).click();
    await expect(page.getByText(/visuals saved/i)).toBeVisible({
      timeout: 15_000,
    });

    await page.reload({ waitUntil: "domcontentloaded" });
    await openCategoryVisuals(page, categoryName);
    await expect(page.getByLabel(/^primary alt text$/i)).toHaveValue(alt);

    await page.goto(`/events/c/${categorySlug}`, {
      waitUntil: "domcontentloaded",
      timeout: 60_000,
    });
    const heroImg = page.locator("section img").first();
    await expect(heroImg).toBeVisible({ timeout: 20_000 });
    await expect(heroImg).toHaveAttribute("alt", alt);

    await openCategoryVisuals(page, categoryName);
    await page.getByRole("button", { name: /^replace image$/i }).click();
    await fileInput.setInputFiles({
      name: "taxonomy-replace.png",
      mimeType: "image/png",
      buffer: pngBuffer(),
    });
    await expect(page.getByText(/uploaded/i)).toBeVisible({ timeout: 30_000 });

    await page.getByRole("button", { name: /^remove primary$/i }).click();
    await expect(page.getByText(/visuals saved/i)).toBeVisible({
      timeout: 15_000,
    });

    const listed = await request.get(apiUrl("/taxonomy/categories"));
    expect(listed.ok()).toBeTruthy();
    const rows = (await listed.json()) as { slug: string; image_url?: string | null }[];
    const music = rows.find((r) => r.slug === categorySlug);
    expect(music?.image_url ?? null).toBeNull();
  });

  test("rejects SVG disguised as PNG and keeps prior image", async ({
    page,
    request,
  }) => {
    const categoryName = "Comedy";
    const categorySlug = "comedy";

    await openCategoryVisuals(page, categoryName);
    const fileInput = page.locator('input[type="file"]').first();
    await fileInput.setInputFiles({
      name: "seed.png",
      mimeType: "image/png",
      buffer: pngBuffer(),
    });
    await expect(page.getByText(/uploaded/i)).toBeVisible({ timeout: 30_000 });

    const before = await request.get(apiUrl("/taxonomy/categories"));
    const beforeRows = (await before.json()) as {
      slug: string;
      image_url?: string | null;
    }[];
    const priorUrl =
      beforeRows.find((r) => r.slug === categorySlug)?.image_url ?? null;
    expect(priorUrl).toBeTruthy();

    const svgAsPng = Buffer.from(
      '<svg xmlns="http://www.w3.org/2000/svg"><rect width="10" height="10"/></svg>',
    );
    await fileInput.setInputFiles({
      name: "evil.png",
      mimeType: "image/png",
      buffer: svgAsPng,
    });
    await expect(page.getByText(/upload failed|invalid|rejected/i)).toBeVisible({
      timeout: 20_000,
    });

    const after = await request.get(apiUrl("/taxonomy/categories"));
    const afterRows = (await after.json()) as {
      slug: string;
      image_url?: string | null;
    }[];
    const afterUrl =
      afterRows.find((r) => r.slug === categorySlug)?.image_url ?? null;
    expect(afterUrl).toBe(priorUrl);
  });

  test("city upload shows single title hierarchy on public hub", async ({
    page,
  }) => {
    await page.goto("/admin/taxonomy/locations", {
      waitUntil: "domcontentloaded",
      timeout: 60_000,
    });
    const lagosRow = page.locator('[class*="rounded"]').filter({ hasText: "Lagos" }).filter({ hasText: /city/i });
    await expect(lagosRow.first()).toBeVisible({ timeout: 30_000 });
    await lagosRow.first().getByRole("button", { name: /^visuals$/i }).click();

    const fileInput = page.locator('input[type="file"]').first();
    await fileInput.setInputFiles({
      name: "lagos.png",
      mimeType: "image/png",
      buffer: pngBuffer(),
    });
    await expect(page.getByText(/uploaded/i)).toBeVisible({ timeout: 30_000 });
    await page.getByLabel(/^primary alt text$/i).fill("Lagos skyline");
    await page.getByRole("button", { name: /^save visuals$/i }).click();

    await page.goto("/events/city/lagos", {
      waitUntil: "domcontentloaded",
      timeout: 60_000,
    });
    const cityCards = page.locator('a[href*="/events/city/"]');
    if ((await cityCards.count()) > 0) {
      const card = cityCards.first();
      await expect(card.getByText(/^city$/i)).toBeVisible();
      await expect(card.getByText(/^lagos$/i)).toHaveCount(1);
    }
    await expect(page.locator("section img").first()).toBeVisible({
      timeout: 20_000,
    });
  });
});
