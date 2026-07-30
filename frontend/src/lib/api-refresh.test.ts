import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const storage = vi.hoisted(() => ({
  access: null as string | null,
  refresh: null as string | null,
}));

const markSessionExpired = vi.hoisted(() => vi.fn());

vi.mock("@/lib/auth/storage", () => ({
  clearTokens: vi.fn(() => {
    storage.access = null;
    storage.refresh = null;
  }),
  getAccessToken: vi.fn(() => storage.access),
  getRefreshToken: vi.fn(() => storage.refresh),
  isImpersonationSession: vi.fn(() => false),
  setTokens: vi.fn((tokens: { access_token: string; refresh_token: string }) => {
    storage.access = tokens.access_token;
    storage.refresh = tokens.refresh_token;
  }),
}));

vi.mock("@/lib/auth/session-expired", () => ({
  DEFAULT_SESSION_EXPIRED_MESSAGE: "Session expired",
  markSessionExpired,
}));

vi.mock("@/lib/api-base", () => ({
  getApiBaseUrl: () => "http://api.test",
  getApiPrefix: () => "/api/v1",
}));

vi.mock("@/lib/auth/jwt", () => ({
  shouldRefreshAccessToken: vi.fn(() => true),
}));

describe("refreshTokens persistence", () => {
  beforeEach(() => {
    storage.access = "access-old";
    storage.refresh = "refresh-old";
    markSessionExpired.mockClear();
    vi.stubGlobal("fetch", vi.fn());
    Reflect.deleteProperty(globalThis as object, "__padeyaRefreshInFlight");
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.resetModules();
    vi.clearAllMocks();
    Reflect.deleteProperty(globalThis as object, "__padeyaRefreshInFlight");
  });

  it("does not clear a rotated session when a stale refresh loses the race", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockImplementation(async () => {
      // Simulate another tab/flight writing the winner's tokens first.
      storage.access = "access-new";
      storage.refresh = "refresh-new";
      return new Response(JSON.stringify({ detail: "Invalid refresh token" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      });
    });

    const { refreshTokens } = await import("@/lib/api");
    const tokens = await refreshTokens();

    expect(tokens).toEqual({
      access_token: "access-new",
      refresh_token: "refresh-new",
      token_type: "bearer",
    });
    expect(storage.refresh).toBe("refresh-new");
    expect(markSessionExpired).not.toHaveBeenCalled();
  });

  it("clears tokens only when the failed refresh is still current", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "Invalid refresh token" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const { refreshTokens } = await import("@/lib/api");
    const tokens = await refreshTokens();

    expect(tokens).toBeNull();
    expect(storage.refresh).toBeNull();
    expect(markSessionExpired).toHaveBeenCalledOnce();
  });

  it("does not mark session expired on network refresh failure", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockRejectedValueOnce(new TypeError("Failed to fetch"));

    const { refreshTokens } = await import("@/lib/api");
    const tokens = await refreshTokens();

    expect(tokens).toBeNull();
    expect(storage.refresh).toBe("refresh-old");
    expect(markSessionExpired).not.toHaveBeenCalled();
  });
});
