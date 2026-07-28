import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const storage = vi.hoisted(() => ({
  access: "audit-access",
  refresh: "audit-refresh",
}));

vi.mock("@/lib/auth/storage", () => ({
  clearTokens: vi.fn(),
  getAccessToken: vi.fn(() => storage.access),
  getRefreshToken: vi.fn(() => storage.refresh),
  isImpersonationSession: vi.fn(() => false),
  setTokens: vi.fn(),
}));

vi.mock("@/lib/auth/session-expired", () => ({
  DEFAULT_SESSION_EXPIRED_MESSAGE: "Session expired",
  markSessionExpired: vi.fn(),
}));

vi.mock("@/lib/api-base", () => ({
  getApiBaseUrl: () => "https://api.example.test",
  getApiPrefix: () => "/api/v1",
}));

describe("sponsor deals API audit URLs", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ ok: true }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it("builds host deal URLs with a single /api/v1 prefix", async () => {
    const { fetchHostSponsorshipDeals } = await import("@/lib/sponsor-deals-api");

    await fetchHostSponsorshipDeals();

    expect(fetch).toHaveBeenCalledTimes(1);
    expect(vi.mocked(fetch).mock.calls[0]?.[0]).toBe(
      "https://api.example.test/api/v1/host/sponsorship-deals",
    );
  });

  it("builds sponsor workspace URLs with a single /api/v1 prefix", async () => {
    const { fetchSponsorDeals } = await import("@/lib/sponsor-deals-api");

    await fetchSponsorDeals("sponsor-123");

    expect(fetch).toHaveBeenCalledTimes(1);
    expect(vi.mocked(fetch).mock.calls[0]?.[0]).toBe(
      "https://api.example.test/api/v1/sponsors/workspaces/sponsor-123/deals",
    );
  });
});
