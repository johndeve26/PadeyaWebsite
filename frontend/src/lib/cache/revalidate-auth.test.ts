import { afterEach, describe, expect, it, vi } from "vitest";

describe("revalidate-auth", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it("rejects when secret is unset", async () => {
    vi.stubEnv("REVALIDATE_SECRET", "");
    const mod = await import("./revalidate-auth");
    const req = new Request("http://localhost/api/revalidate/fan", {
      method: "POST",
      headers: { Authorization: "Bearer anything" },
    });
    expect(mod.authorizeRevalidateRequest(req)).toBe(false);
  });

  it("rejects wrong bearer token", async () => {
    vi.stubEnv("REVALIDATE_SECRET", "correct-secret-value");
    const mod = await import("./revalidate-auth");
    const req = new Request("http://localhost/api/revalidate/fan", {
      method: "POST",
      headers: { Authorization: "Bearer wrong-secret-value" },
    });
    expect(mod.authorizeRevalidateRequest(req)).toBe(false);
  });

  it("accepts matching bearer token", async () => {
    vi.stubEnv("REVALIDATE_SECRET", "correct-secret-value");
    const mod = await import("./revalidate-auth");
    const req = new Request("http://localhost/api/revalidate/fan", {
      method: "POST",
      headers: { Authorization: "Bearer correct-secret-value" },
    });
    expect(mod.authorizeRevalidateRequest(req)).toBe(true);
  });

  it("accepts x-revalidate-secret header", async () => {
    vi.stubEnv("REVALIDATE_SECRET", "correct-secret-value");
    const mod = await import("./revalidate-auth");
    const req = new Request("http://localhost/api/revalidate/fan", {
      method: "POST",
      headers: { "x-revalidate-secret": "correct-secret-value" },
    });
    expect(mod.authorizeRevalidateRequest(req)).toBe(true);
  });
});
