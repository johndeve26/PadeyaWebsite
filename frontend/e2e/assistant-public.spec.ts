import { test, expect } from "@playwright/test";

/**
 * Public Ask Pàdéyá widget smoke.
 * Mocks /assistant/status so the suite does not require live flags.
 */
const STATUS_ENABLED = {
  assistant_enabled: true,
  public_enabled: true,
  authenticated_enabled: false,
  actions_enabled: false,
  event_search_enabled: true,
  product_public: "Ask Pàdéyá",
  product_authenticated: "Pàdéyá Copilot",
};

async function mockAssistantStatus(page: import("@playwright/test").Page) {
  await page.route("**/api/v1/assistant/status", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(STATUS_ENABLED),
    });
  });
}

test.describe("Ask Pàdéyá public widget", () => {
  test("launcher opens welcome with public prompts", async ({ page }) => {
    await mockAssistantStatus(page);
    await page.goto("/", { waitUntil: "domcontentloaded", timeout: 45_000 });

    const launcher = page.getByRole("button", { name: /open ask pàdéyá/i });
    await expect(launcher).toBeVisible({ timeout: 15_000 });
    await launcher.click();

    await expect(page.getByRole("heading", { name: "Ask Pàdéyá" })).toBeVisible();
    await expect(
      page.getByText(/find events, pages and answers/i).first(),
    ).toBeVisible();
    await expect(
      page.getByRole("button", {
        name: /events in ibadan|free events|ambassadors|become a host|contact support/i,
      }).first(),
    ).toBeVisible();
  });

  test("widget hidden on checkout paths", async ({ page }) => {
    await mockAssistantStatus(page);
    await page.goto("/checkout/success", {
      waitUntil: "domcontentloaded",
      timeout: 45_000,
    });
    await expect(
      page.getByRole("button", { name: /open ask pàdéyá|open pàdéyá copilot/i }),
    ).toHaveCount(0);
  });

  test("disabled status hides launcher", async ({ page }) => {
    await page.route("**/api/v1/assistant/status", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          ...STATUS_ENABLED,
          assistant_enabled: false,
          public_enabled: false,
        }),
      });
    });
    await page.goto("/", { waitUntil: "domcontentloaded", timeout: 45_000 });
    await page.waitForTimeout(800);
    await expect(
      page.getByRole("button", { name: /open ask pàdéyá|open pàdéyá copilot/i }),
    ).toHaveCount(0);
  });
});
