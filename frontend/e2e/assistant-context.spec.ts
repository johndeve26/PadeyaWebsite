import { test, expect } from "@playwright/test";

const STATUS_ENABLED = {
  assistant_enabled: true,
  public_enabled: true,
  authenticated_enabled: true,
  actions_enabled: false,
  event_search_enabled: true,
  product_public: "Ask Pàdéyá",
  product_authenticated: "Pàdéyá Copilot",
  ai_provider_ready: true,
};

function sse(events: Array<{ event: string; data: Record<string, unknown> }>): string {
  return events
    .map(
      (e) =>
        `event: ${e.event}\ndata: ${JSON.stringify(e.data)}\n\n`,
    )
    .join("");
}

async function mockAssistant(page: import("@playwright/test").Page) {
  await page.route("**/api/v1/assistant/status", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(STATUS_ENABLED),
    });
  });
}

test.describe("Assistant bounded context follow-ups", () => {
  test("public event search then first-result follow-up uses session", async ({
    page,
  }) => {
    const sessionId = "11111111-1111-1111-1111-111111111111";
    let turn = 0;

    await mockAssistant(page);
    await page.route("**/api/v1/assistant/chat/stream", async (route) => {
      turn += 1;
      if (turn === 1) {
        await route.fulfill({
          status: 200,
          contentType: "text/event-stream",
          body: sse([
            { event: "session", data: { session_id: sessionId } },
            {
              event: "done",
              data: {
                session_id: sessionId,
                text: "Here are events in Ibadan this weekend.",
                citations: [],
                cards: [
                  {
                    type: "result",
                    title: "Ibadan Jazz Night",
                    url: "/events/ibadan-jazz",
                    subtitle: "Ibadan",
                  },
                ],
                actions: [],
              },
            },
          ]),
        });
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body: sse([
          { event: "session", data: { session_id: sessionId } },
          {
            event: "done",
            data: {
              session_id: sessionId,
              text: "Ibadan Jazz Night is on Saturday at The Yard.",
              citations: [],
              cards: [],
              actions: [
                {
                  type: "navigate",
                  label: "Open Ibadan Jazz Night",
                  url: "/events/ibadan-jazz",
                },
              ],
            },
          },
        ]),
      });
    });

    await page.goto("/", { waitUntil: "domcontentloaded", timeout: 45_000 });
    await page.getByRole("button", { name: /open ask pàdéyá/i }).click();
    const composer = page.getByPlaceholder(/ask anything/i);
    await composer.fill("Show events in Ibadan this weekend");
    await composer.press("Enter");
    await expect(page.getByText(/Ibadan Jazz Night/i).first()).toBeVisible({
      timeout: 15_000,
    });

    await composer.fill("Tell me about the first one");
    await composer.press("Enter");
    await expect(page.getByText(/Saturday at The Yard/i)).toBeVisible({
      timeout: 15_000,
    });
  });

  test("session reload continues with session_id on follow-up", async ({ page }) => {
    const sessionId = "22222222-2222-2222-2222-222222222222";
    await mockAssistant(page);

    await page.route("**/api/v1/assistant/chat/stream", async (route) => {
      const body = route.request().postDataJSON() as { session_id?: string };
      expect(body.session_id).toBe(sessionId);
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body: sse([
          { event: "session", data: { session_id: sessionId } },
          {
            event: "done",
            data: {
              session_id: sessionId,
              text: "Continuing your conversation.",
              citations: [],
              cards: [],
              actions: [],
            },
          },
        ]),
      });
    });

    await page.addInitScript((sid) => {
      window.sessionStorage.setItem("padeya-assistant-session-id", sid);
    }, sessionId);

    await page.goto("/", { waitUntil: "domcontentloaded", timeout: 45_000 });
    await page.getByRole("button", { name: /open ask pàdéyá/i }).click();
    const composer = page.getByPlaceholder(/ask anything/i);
    await composer.fill("Same city please");
    await composer.press("Enter");
    await expect(page.getByText(/Continuing your conversation/i)).toBeVisible({
      timeout: 15_000,
    });
  });
});
