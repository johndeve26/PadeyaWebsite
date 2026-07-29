/**
 * Blog workspace UX closeout — creation flows, tab journey, width regression.
 * Requires PLAYWRIGHT_PASSWORD + running API/frontend.
 */

import { test, expect, type Page, type APIRequestContext } from "@playwright/test";

import { hasAuthCredentials, loginAs, apiBaseUrl, apiPrefix } from "./helpers/auth";

const hasCreds = hasAuthCredentials("super_admin");

async function mockBlogAi(page: Page) {
  await page.route("**/admin/blog/ai/**", async (route) => {
    const url = route.request().url();
    if (url.includes("quality-review") || url.includes("/review")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          summary: "Mock review complete",
          findings: [],
          suggested_changes: [],
        }),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ text: "Mock AI output", sections: [] }),
    });
  });
}

async function countDrafts(page: Page, request: APIRequestContext): Promise<number> {
  const token = await page.evaluate(() => localStorage.getItem("padeya.access_token"));
  const res = await request.get(`${apiBaseUrl()}${apiPrefix()}/admin/blog/posts`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok()) return 0;
  const posts = await res.json();
  return Array.isArray(posts) ? posts.filter((p: { status?: string }) => p.status === "draft").length : 0;
}

async function assertEditorMinWidth(page: Page, testId: string, minPx: number) {
  const box = await page.getByTestId(testId).boundingBox();
  expect(box).not.toBeNull();
  expect(box!.width).toBeGreaterThanOrEqual(minPx);
}

test.describe("Blog workspace closeout", () => {
  test.skip(!hasCreds, "Set PLAYWRIGHT_PASSWORD for authenticated blog workspace tests");

  test.beforeEach(async ({ page, request }) => {
    await loginAs(page, request, "super_admin");
    await mockBlogAi(page);
  });

  test("start screen shows three creation choices only", async ({ page }) => {
    await page.goto("/admin/blog/new");
    await expect(page.getByTestId("blog-creation-start")).toBeVisible();
    await expect(page.getByRole("button", { name: /start blank/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /use a template/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /create with ai/i })).toBeVisible();
    await expect(page.getByRole("tab", { name: /write/i })).toHaveCount(0);
  });

  test("blank journey: write → design → seo → review → publish cancel → reload", async ({
    page,
    request,
  }) => {
    const draftsBefore = await countDrafts(page, request);

    await page.goto("/admin/blog/new");
    await page.getByRole("button", { name: /start blank/i }).click();
    await page.waitForURL(/\/admin\/blog\/[^/]+\/edit\?tab=write/, { timeout: 30_000 });

    const draftsAfterCreate = await countDrafts(page, request);
    expect(draftsAfterCreate).toBe(draftsBefore + 1);

    await expect(page.getByRole("tab", { name: "Write", selected: true })).toBeVisible();

    await page.getByLabel("Title").fill("E2E Workspace Draft");
    const editor = page.getByTestId("blog-editor-canvas").locator("textarea").first();
    await editor.fill("Paragraph A for workspace E2E.");

    await assertEditorMinWidth(page, "blog-editor-canvas", 480);
    await expect(page.getByLabel("Meta title")).toHaveCount(0);
    await expect(page.getByText(/content brief/i)).toHaveCount(0);

    await page.getByRole("tab", { name: "Design" }).click();
    await expect(page.getByTestId("blog-design-workspace")).toBeVisible();
    await assertEditorMinWidth(page, "blog-design-canvas", 480);

    await page.getByRole("button", { name: /\+ two columns/i }).click();
    await page.getByRole("tab", { name: "Write" }).click();
    await expect(editor).toHaveValue(/Paragraph A/i);

    await page.getByRole("tab", { name: /seo & social/i }).click();
    await page.getByLabel("Slug").fill("e2e-workspace-draft");
    await page.getByPlaceholder(/meta title/i).fill(
      "E2E Workspace Draft Title For SEO Meta Tag Field",
    );

    await page.getByRole("tab", { name: "Review" }).click();
    await page.getByRole("button", { name: /run review/i }).click();
    await expect(page.getByText(/mock review complete/i)).toBeVisible({ timeout: 20_000 });

    await page.getByRole("tab", { name: "Publish" }).click();
    await page.getByRole("button", { name: /publish now/i }).click();
    await expect(page.getByText(/publish.*E2E Workspace Draft/i)).toBeVisible();
    await page.getByRole("button", { name: /^cancel$/i }).click();
    await expect(page.getByText(/^draft$/i).first()).toBeVisible();

    const url = page.url();
    await page.reload();
    await expect(page.getByLabel("Title")).toHaveValue("E2E Workspace Draft");
    await expect(page.getByRole("tab", { name: "Publish", selected: true })).toBeVisible();
    expect(page.url()).toContain(new URL(url).pathname);
  });

  test("template journey: one draft, template applied, reload persists", async ({
    page,
    request,
  }) => {
    const draftsBefore = await countDrafts(page, request);

    await page.goto("/admin/blog/new");
    await page.getByRole("button", { name: /use a template/i }).click();
    await expect(page.getByRole("heading", { name: /choose a template/i })).toBeVisible();

    const firstTemplate = page.locator("ul button").first();
    await expect(firstTemplate).toBeVisible({ timeout: 15_000 });
    await firstTemplate.click();

    await page.waitForURL(/\/admin\/blog\/[^/]+\/edit\?tab=write/, { timeout: 30_000 });
    const draftsAfter = await countDrafts(page, request);
    expect(draftsAfter).toBe(draftsBefore + 1);

    await expect(page.getByTestId("blog-write-workspace")).toBeVisible();
    await expect(page.getByTestId("blog-editor-canvas").locator("textarea, input").first()).toBeVisible();

    await page.reload();
    await expect(page.getByTestId("blog-write-workspace")).toBeVisible();
  });

  test("AI journey: one draft, opens plan tab, does not auto-publish", async ({
    page,
    request,
  }) => {
    const draftsBefore = await countDrafts(page, request);

    await page.goto("/admin/blog/new");
    await page.getByRole("button", { name: /create with ai/i }).click();
    await page.waitForURL(/\/admin\/blog\/[^/]+\/edit\?tab=plan/, { timeout: 30_000 });

    expect(await countDrafts(page, request)).toBe(draftsBefore + 1);
    await expect(page.getByRole("tab", { name: "Plan", selected: true })).toBeVisible();
    await expect(page.getByText(/^draft$/i).first()).toBeVisible();
    await expect(page.getByRole("button", { name: /publish now/i })).toHaveCount(0);
  });

  test("mobile: direct ?tab=review scrolls active tab into view", async ({ page }) => {
    await page.goto("/admin/blog/new");
    await page.getByRole("button", { name: /start blank/i }).click();
    await page.waitForURL(/\/admin\/blog\/[^/]+\/edit/, { timeout: 30_000 });

    const postUrl = page.url().replace(/\?.*$/, "");
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto(`${postUrl}?tab=review`);
    await expect(page.getByRole("tab", { name: "Review", selected: true })).toBeVisible();

    const tab = page.locator(".flex.md\\:hidden [role='tablist'] #blog-workspace-tab-review");
    const box = await tab.boundingBox();
    const viewport = page.viewportSize();
    expect(box).not.toBeNull();
    expect(box!.x).toBeGreaterThanOrEqual(0);
    expect(box!.x + box!.width).toBeLessThanOrEqual((viewport?.width ?? 375) + 2);

    const overflow = await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1);
    expect(overflow).toBe(true);
  });

  test("tab accessibility: keyboard navigation between tabs", async ({ page }) => {
    await page.goto("/admin/blog/new");
    await page.getByRole("button", { name: /start blank/i }).click();
    await page.waitForURL(/\/admin\/blog\/[^/]+\/edit\?tab=write/, { timeout: 30_000 });

    await page.getByRole("tab", { name: "Write" }).focus();
    await page.keyboard.press("ArrowRight");
    await expect(page.getByRole("tab", { name: "Design", selected: true })).toBeVisible();
    await page.keyboard.press("End");
    await expect(page.getByRole("tab", { name: "Publish", selected: true })).toBeVisible();
    await page.keyboard.press("Home");
    await expect(page.getByRole("tab", { name: "Plan", selected: true })).toBeVisible();
  });
});

test.describe("Blog workspace width regression", () => {
  test.skip(!hasCreds, "Set PLAYWRIGHT_PASSWORD for authenticated blog workspace tests");

  test.beforeEach(async ({ page, request }) => {
    await loginAs(page, request, "super_admin");
  });

  test("editor canvas minimum width at 1440×900 and 1280×800", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/admin/blog/new");
    await page.getByRole("button", { name: /start blank/i }).click();
    await page.waitForURL(/\/admin\/blog\/[^/]+\/edit\?tab=write/, { timeout: 30_000 });
    await assertEditorMinWidth(page, "blog-editor-canvas", 480);

    await page.getByRole("tab", { name: "Design" }).click();
    await assertEditorMinWidth(page, "blog-design-canvas", 480);

    await page.setViewportSize({ width: 1280, height: 800 });
    await page.getByRole("tab", { name: "Write" }).click();
    await assertEditorMinWidth(page, "blog-editor-canvas", 400);
  });
});
