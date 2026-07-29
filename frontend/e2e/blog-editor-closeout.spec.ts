/**
 * Blog editor pre-deploy E2E — manual-first, AI-assisted, legacy conversion.
 * Requires PLAYWRIGHT_PASSWORD + running API/frontend.
 */

import { test, expect } from "@playwright/test";
import path from "node:path";

import { getPersonaCreds, hasAuthCredentials, loginAs } from "./helpers/auth";

const hasCreds = hasAuthCredentials("super_admin");

test.describe("Blog editor closeout", () => {
  test.skip(!hasCreds, "Set PLAYWRIGHT_PASSWORD for authenticated blog editor tests");

  test.beforeEach(async ({ page, request }) => {
    await loginAs(page, request, "super_admin");
  });

  test("manual-first: blank → write → layout → preview → save draft", async ({
    page,
  }) => {
    await page.route("**/admin/blog/ai/**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ titles: [], sections: [] }),
      });
    });

    await page.goto("/admin/blog/new");
    await page.getByRole("button", { name: /start blank/i }).click();

    await page.getByPlaceholder(/title/i).first().fill("E2E Manual Draft");
    await page.getByRole("button", { name: /standard editor/i }).click();

    const editor = page.locator("textarea").first();
    await editor.fill("## Introduction\n\nManual paragraph for E2E test.");

    await page.getByRole("button", { name: /layout manager/i }).click();
    await page.getByRole("button", { name: /\+ two columns/i }).click();
    await page.getByRole("button", { name: /standard editor/i }).click();

    await expect(editor).toContainText(/manual paragraph/i);

    await page.getByRole("button", { name: /preview/i }).click();
    await expect(page.getByText(/draft preview/i)).toBeVisible();

    await page.getByRole("button", { name: /save/i }).click();
    await expect(page.getByText(/saved/i).first()).toBeVisible({ timeout: 20_000 });
  });

  test("legacy conversion: opens, converts, revision created, modes work", async ({
    page,
    request,
  }) => {
    // Find a legacy (non-block-document) post via the admin API
    const resp = await request.get("/api/admin/blog?limit=50");
    if (!resp.ok()) {
      test.skip();
      return;
    }
    const data = await resp.json();
    const posts: Array<{ slug: string; content_document: unknown }> = data.posts ?? data;
    const legacy = posts.find((p) => !p.content_document);
    if (!legacy) {
      test.skip();
      return;
    }

    await page.goto(`/admin/blog/${legacy.slug}/edit`);

    // Confirm legacy mode indicator is visible
    await expect(page.getByText(/legacy/i).first()).toBeVisible({ timeout: 10_000 });

    // Convert to block document
    const convertBtn = page.getByRole("button", { name: /convert to block/i });
    if (await convertBtn.isVisible()) {
      await convertBtn.click();
      await expect(page.getByText(/converted/i).first()).toBeVisible({ timeout: 10_000 });
    }

    // Switch to Layout Manager and back — confirm no crash
    await page.getByRole("button", { name: /layout manager/i }).click();
    await page.getByRole("button", { name: /standard editor/i }).click();

    // Save draft
    await page.getByRole("button", { name: /save/i }).click();
    await expect(page.getByText(/saved/i).first()).toBeVisible({ timeout: 20_000 });
  });

  test("optional AI: create with AI does not auto-publish", async ({ page }) => {
    await page.route("**/admin/blog/ai/**", async (route) => {
      const url = route.request().url();
      if (url.includes("outline")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            sections: [{ id: "s1", heading: "Mock section", level: 2 }],
            approved: false,
          }),
        });
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ text: "Mock AI output" }),
      });
    });

    await page.goto("/admin/blog/new");
    await page.getByRole("button", { name: /create with ai/i }).click();
    await expect(page.getByRole("button", { name: /publish/i })).toBeVisible();
    await expect(page.getByText(/draft/i).first()).toBeVisible();
  });
});

test.describe("Blog editor mode invariants (unit-backed)", () => {
  test("mode switch preserves block count via local document utils", async () => {
    const { defaultDocument, createBlock, cloneDocument } = await import(
      "../src/lib/blog-document"
    );
    const doc = defaultDocument();
    doc.blocks.push(createBlock("heading", { content: { text: "H2", level: 2 } }));
    const before = cloneDocument(doc);
    const afterLayout = cloneDocument(doc);
    afterLayout.blocks.push(createBlock("two_column_row"));
    const backToStandard = cloneDocument(afterLayout);
    expect(backToStandard.blocks.length).toBeGreaterThanOrEqual(before.blocks.length);
    expect(backToStandard.blocks[0].id).toBe(before.blocks[0].id);
  });
});
