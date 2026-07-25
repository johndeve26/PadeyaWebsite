import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { isTimeoutError } from "@/lib/api-timeouts";

const storage = vi.hoisted(() => ({
  access: null as string | null,
  refresh: null as string | null,
}));

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
  markSessionExpired: vi.fn(),
}));

vi.mock("@/lib/api-base", () => ({
  getApiBaseUrl: () => "http://api.test",
  getApiPrefix: () => "/api/v1",
}));

describe("apiRequest timeouts", () => {
  beforeEach(() => {
    storage.access = "access";
    storage.refresh = "refresh";
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.resetModules();
    vi.clearAllMocks();
  });

  it("maps abort to TimeoutError and does not retry GET", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockRejectedValueOnce(
      Object.assign(new Error("Aborted"), { name: "AbortError" }),
    );

    const { apiRequest } = await import("@/lib/api");
    await expect(
      apiRequest("/events", { auth: false, timeout: 50 }),
    ).rejects.toSatisfy(isTimeoutError);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("does not retry POST on timeout", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockRejectedValueOnce(
      Object.assign(new Error("Aborted"), { name: "AbortError" }),
    );

    const { apiRequest } = await import("@/lib/api");
    await expect(
      apiRequest("/auth/login", {
        method: "POST",
        auth: false,
        body: { email: "a@b.com", password: "x" },
        timeout: 50,
      }),
    ).rejects.toSatisfy(isTimeoutError);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("honors explicit long timeout budget option without auto-retry", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const { apiRequest } = await import("@/lib/api");
    const data = await apiRequest<{ ok: boolean }>("/ai/host/suggest", {
      method: "POST",
      body: { feature: "host.event.title" },
      timeout: "long",
    });
    expect(data.ok).toBe(true);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(init.signal).toBeTruthy();
  });
});
