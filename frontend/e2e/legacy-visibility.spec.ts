import { expect, test } from "@playwright/test";

import { apiBaseUrl, apiPrefix } from "./helpers/auth";

const LEGACY_HOSTS = {
  established: "legacy-established",
  provisional: "legacy-provisional",
  gateBlocked: "legacy-gated",
  topTier: "legacy-legend",
  noHistory: "legacy-empty",
} as const;

const API_TIMEOUT_MS = 120_000;

async function requireApi(request: import("@playwright/test").APIRequestContext) {
  const health = await request.get(`${apiBaseUrl()}/health`, {
    timeout: API_TIMEOUT_MS,
  });
  expect(
    health.ok(),
    `API unavailable at ${apiBaseUrl()}/health — start backend and run demo seed`,
  ).toBeTruthy();
}

async function assertLegacyPage(
  request: import("@playwright/test").APIRequestContext,
  username: string,
  expectations?: {
    minDisplayScore?: number;
    minReviews?: number;
    isProvisional?: boolean;
    isTopTier?: boolean;
    nextTierState?: string;
  },
) {
  const res = await request.get(
    `${apiBaseUrl()}${apiPrefix()}/u/${username}/legacy`,
    { timeout: API_TIMEOUT_MS },
  );
  expect(res.ok(), `Missing Legacy page for @${username}`).toBeTruthy();
  const body = await res.json();
  expect(body.legacy_trust, `legacy_trust missing for @${username}`).toBeTruthy();
  const trust = body.legacy_trust;
  if (expectations?.minDisplayScore != null) {
    expect(
      trust.display_score,
      `@${username} display_score too low (seed incomplete?)`,
    ).toBeGreaterThanOrEqual(expectations.minDisplayScore);
  }
  if (expectations?.minReviews != null) {
    expect(body.stats.review_count).toBeGreaterThanOrEqual(expectations.minReviews);
  }
  if (expectations?.isProvisional != null) {
    expect(trust.is_provisional).toBe(expectations.isProvisional);
  }
  if (expectations?.isTopTier != null) {
    expect(trust.is_top_tier).toBe(expectations.isTopTier);
  }
  if (expectations?.nextTierState) {
    expect(trust.next_tier?.state).toBe(expectations.nextTierState);
  }
  return body;
}

test.describe("Legacy public host flows", () => {
  test.describe.configure({ timeout: 300_000, retries: 1 });

  test.beforeEach(async ({ request }) => {
    await requireApi(request);
  });

  test("established host profile shows Legacy trust summary", async ({
    page,
    request,
  }) => {
    await assertLegacyPage(request, LEGACY_HOSTS.established, {
      isProvisional: false,
      minDisplayScore: 40,
      minReviews: 5,
    });
    await page.goto(`/u/${LEGACY_HOSTS.established}`, {
      waitUntil: "domcontentloaded",
    });
    await expect(page.getByRole("heading", { name: "Page not found" })).toHaveCount(
      0,
    );
    const summary = page.getByLabel(/Legacy Score:/i);
    await expect(summary).toBeVisible();
    await expect(page.getByText(/\/ 100/).first()).toBeVisible();
    // Verified star rating remains separate from Legacy Score (evidence + host stats).
    await expect(page.getByText(/Supporting proof/i).first()).toBeVisible();
    await expect(page.getByText(/Verified rating/i).first()).toBeVisible();

    await page.getByRole("button", { name: /What shapes this score\?/i }).click();
    await expect(
      page.getByText(/Guest satisfaction|Event experience/i).first(),
    ).toBeVisible();

    await page.getByRole("link", { name: /How Legacy works/i }).first().click();
    await expect(page).toHaveURL(/\/legacy/);
  });

  test("provisional host shows limited-history explanation", async ({
    page,
    request,
  }) => {
    await assertLegacyPage(request, LEGACY_HOSTS.provisional, {
      isProvisional: true,
      minDisplayScore: 1,
    });
    await page.goto(`/u/${LEGACY_HOSTS.provisional}`, {
      waitUntil: "domcontentloaded",
    });
    await expect(page.getByRole("heading", { name: "Page not found" })).toHaveCount(0);
    await expect(page.getByText(/Provisional/i).first()).toBeVisible();
    await expect(page.getByText(/\/ 100/).first()).toBeVisible();
    await expect(
      page.getByText(/verified history|verified activity/i).first(),
    ).toBeVisible();
  });

  test("score-met gate-blocked host explains remaining gates", async ({
    page,
    request,
  }) => {
    await assertLegacyPage(request, LEGACY_HOSTS.gateBlocked, {
      nextTierState: "score_met_gates_remaining",
    });
    await page.goto(`/u/${LEGACY_HOSTS.gateBlocked}`, {
      waitUntil: "domcontentloaded",
    });
    await expect(page.getByRole("heading", { name: "Page not found" })).toHaveCount(0);
    await expect(page.getByText(/Score requirement met/i).first()).toBeVisible();
    await expect(page.getByText(/remaining verified activity/i)).toBeVisible();
    await expect(page.getByText(/\d+ points to/i)).toHaveCount(0);
  });

  test("top-tier host shows highest tier without fake next tier", async ({
    page,
    request,
  }) => {
    await assertLegacyPage(request, LEGACY_HOSTS.topTier, {
      isTopTier: true,
      minDisplayScore: 80,
    });
    await page.goto(`/u/${LEGACY_HOSTS.topTier}`, {
      waitUntil: "domcontentloaded",
    });
    await expect(page.getByRole("heading", { name: "Page not found" })).toHaveCount(0);
    await expect(page.getByText(/Highest Legacy tier/i).first()).toBeVisible();
    await expect(page.getByText(/Next-tier progress/i)).toHaveCount(0);
  });

  test("mobile layout has no horizontal overflow on Legacy summary", async ({
    page,
    request,
  }) => {
    await assertLegacyPage(request, LEGACY_HOSTS.established, {
      isProvisional: false,
      minDisplayScore: 40,
    });
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto(`/u/${LEGACY_HOSTS.established}`);
    await expect(page.getByLabel(/Legacy Score:/i)).toBeVisible();

    const scrollWidth = await page.evaluate(
      () => document.documentElement.scrollWidth,
    );
    const clientWidth = await page.evaluate(
      () => document.documentElement.clientWidth,
    );
    expect(scrollWidth).toBeLessThanOrEqual(clientWidth + 1);
  });
});

test.describe("Legacy transparency page", () => {
  test("how Legacy works page explains score vs tier", async ({ page, request }) => {
    await requireApi(request);
    await page.goto("/legacy");
    await expect(
      page.getByRole("heading", { name: "How Legacy works" }),
    ).toBeVisible();
    await expect(page.getByText("Score versus tier")).toBeVisible();
    await expect(page.getByText("30%", { exact: true }).first()).toBeVisible();
  });
});
