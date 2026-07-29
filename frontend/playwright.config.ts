import { defineConfig, devices } from "@playwright/test";

// Always use 127.0.0.1 (not localhost) so browser, server, and CORS origins match exactly.
const FE_PORT = process.env.PLAYWRIGHT_FE_PORT ?? "3000";
const API_PORT = process.env.PLAYWRIGHT_API_PORT ?? "8000";
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? `http://127.0.0.1:${FE_PORT}`;
const apiURL = process.env.PLAYWRIGHT_API_URL ?? `http://localhost:${API_PORT}`;

// Whether to let Playwright start the dev server itself.
// Set PLAYWRIGHT_SKIP_WEBSERVER=1 when the server is already running (e.g. this session).
const skipWebServer = Boolean(process.env.PLAYWRIGHT_SKIP_WEBSERVER);

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 2 : 2,
  reporter: [
    ["list"],
    ["json", { outputFile: "artifacts/ui-audit/playwright-report.json" }],
  ],
  outputDir: "artifacts/ui-audit/test-output",
  timeout: 180_000,
  expect: { timeout: 20_000 },
  use: {
    baseURL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "off",
    colorScheme: "light",
  },
  // Playwright will start the Next.js dev server before running tests.
  // The server is started with NEXT_PUBLIC_API_URL so the browser bundle
  // sends API requests directly (no proxy needed, no CORS mismatch).
  // API_PROXY_TARGET is still set for SSR rewrites.
  webServer: skipWebServer ? undefined : {
    command: `NEXT_PUBLIC_API_URL=${apiURL} API_PROXY_TARGET=${apiURL} npm run dev -- --port ${FE_PORT}`,
    url: `http://127.0.0.1:${FE_PORT}`,
    reuseExistingServer: false,
    timeout: 120_000,
    env: {
      NEXT_PUBLIC_API_URL: apiURL,
      API_PROXY_TARGET: apiURL,
    },
  },
  projects: [
    {
      name: "chromium-desktop",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1440, height: 900 },
      },
    },
    {
      name: "chromium-mobile",
      use: {
        browserName: "chromium",
        viewport: { width: 375, height: 812 },
        isMobile: true,
        hasTouch: true,
        userAgent:
          "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
      },
    },
    {
      name: "firefox-critical",
      testMatch: /theme-visual-smoke\.spec\.ts/,
      grep: /System theme|light · \/($|login)|dark · \/($|login)/,
      use: { ...devices["Desktop Firefox"], viewport: { width: 1440, height: 900 } },
    },
    {
      name: "webkit-critical",
      testMatch: /theme-visual-smoke\.spec\.ts/,
      grep: /System theme|light · \/($|login)|dark · \/($|login)/,
      use: { ...devices["Desktop Safari"], viewport: { width: 1440, height: 900 } },
    },
  ],
});
