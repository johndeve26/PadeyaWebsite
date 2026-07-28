import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

describe("getApiBaseUrl", () => {
  const originalWindow = global.window;
  const originalEnv = { ...process.env };

  beforeEach(() => {
    vi.resetModules();
    process.env = { ...originalEnv };
    delete process.env.NEXT_PUBLIC_API_URL;
    delete process.env.NEXT_PUBLIC_LIVE_API_URL;
    delete process.env.API_PROXY_TARGET;
  });

  afterEach(() => {
    process.env = originalEnv;
    global.window = originalWindow;
  });

  it("prefers NEXT_PUBLIC_API_URL when set", async () => {
    process.env.NEXT_PUBLIC_API_URL = "https://api.example.test/";
    const { getApiBaseUrl } = await import("@/lib/api-base");
    expect(getApiBaseUrl()).toBe("https://api.example.test");
  });

  it("uses same-origin rewrites for non-production browser hosts", async () => {
    process.env.API_PROXY_TARGET = "http://127.0.0.1:8000";
    global.window = {
      location: { hostname: "mesic-lera-indigestive.ngrok-free.dev" },
    } as Window & typeof globalThis;
    const { getApiBaseUrl } = await import("@/lib/api-base");
    expect(getApiBaseUrl()).toBe("");
  });

  it("falls back to the live API origin on padeya.com when env is unset", async () => {
    global.window = {
      location: { hostname: "padeya.com" },
    } as Window & typeof globalThis;
    const { getApiBaseUrl, LIVE_API_ORIGIN } = await import("@/lib/api-base");
    expect(getApiBaseUrl()).toBe(LIVE_API_ORIGIN);
    expect(getApiBaseUrl()).toBe("https://padeyawebsite.onrender.com");
  });

  it("falls back to the live API origin on www.padeya.com", async () => {
    global.window = {
      location: { hostname: "www.padeya.com" },
    } as Window & typeof globalThis;
    const { getApiBaseUrl } = await import("@/lib/api-base");
    expect(getApiBaseUrl()).toBe("https://padeyawebsite.onrender.com");
  });

  it("uses API_PROXY_TARGET on the server when env is unset", async () => {
    process.env.API_PROXY_TARGET = "http://127.0.0.1:8000";
    // @ts-expect-error simulate server bundle
    delete global.window;
    const { getApiBaseUrl } = await import("@/lib/api-base");
    expect(getApiBaseUrl()).toBe("http://127.0.0.1:8000");
  });
});
