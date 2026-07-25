import { afterEach, describe, expect, it, vi } from "vitest";

const getAccessToken = vi.fn();

vi.mock("@/lib/auth/storage", () => ({
  getAccessToken: () => getAccessToken(),
}));

describe("unread poll guard (401 storm regression)", () => {
  afterEach(() => {
    getAccessToken.mockReset();
    vi.resetModules();
  });

  it("blocks chrome polls when access token is missing", async () => {
    getAccessToken.mockReturnValue(null);
    const { canPollAuthenticatedChrome } = await import(
      "@/lib/auth/unread-poll-guard"
    );
    expect(canPollAuthenticatedChrome()).toBe(false);
  });

  it("allows chrome polls when access token is present", async () => {
    getAccessToken.mockReturnValue("token");
    const { canPollAuthenticatedChrome } = await import(
      "@/lib/auth/unread-poll-guard"
    );
    expect(canPollAuthenticatedChrome()).toBe(true);
  });
});
