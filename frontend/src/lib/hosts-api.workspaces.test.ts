import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const storage = vi.hoisted(() => ({
  access: null as string | null,
}));

vi.mock("@/lib/auth/storage", () => ({
  getAccessToken: vi.fn(() => storage.access),
}));

const apiRequest = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api", () => ({
  apiRequest,
}));

describe("fetchHostWorkspaces single-flight", () => {
  beforeEach(() => {
    storage.access = "token-a";
    apiRequest.mockReset();
    vi.resetModules();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("dedupes concurrent calls for the same token", async () => {
    let resolve!: (value: unknown) => void;
    const pending = new Promise((r) => {
      resolve = r;
    });
    apiRequest.mockReturnValueOnce(pending);

    const { fetchHostWorkspaces } = await import("@/lib/hosts-api");
    const p1 = fetchHostWorkspaces();
    const p2 = fetchHostWorkspaces();
    expect(apiRequest).toHaveBeenCalledTimes(1);
    resolve([
      {
        host_id: "h1",
        slug: "lagos",
        is_owner: true,
        kind: "owner",
      },
    ]);
    const [a, b] = await Promise.all([p1, p2]);
    expect(a).toEqual(b);
    expect(a).toHaveLength(1);
  });

  it("reuses resolved result until invalidated", async () => {
    apiRequest.mockResolvedValue([
      { host_id: "h1", slug: "lagos", is_owner: true, kind: "owner" },
    ]);
    const mod = await import("@/lib/hosts-api");
    await mod.fetchHostWorkspaces();
    await mod.fetchHostWorkspaces();
    expect(apiRequest).toHaveBeenCalledTimes(1);

    mod.invalidateHostWorkspacesCache();
    await mod.fetchHostWorkspaces();
    expect(apiRequest).toHaveBeenCalledTimes(2);
  });

  it("does not share cache across access tokens", async () => {
    apiRequest.mockResolvedValue([
      { host_id: "h1", slug: "lagos", is_owner: true, kind: "owner" },
    ]);
    const mod = await import("@/lib/hosts-api");
    await mod.fetchHostWorkspaces();
    storage.access = "token-b";
    await mod.fetchHostWorkspaces();
    expect(apiRequest).toHaveBeenCalledTimes(2);
  });

  it("returns empty and clears cache when logged out", async () => {
    apiRequest.mockResolvedValue([
      { host_id: "h1", slug: "lagos", is_owner: true, kind: "owner" },
    ]);
    const mod = await import("@/lib/hosts-api");
    await mod.fetchHostWorkspaces();
    storage.access = null;
    const empty = await mod.fetchHostWorkspaces();
    expect(empty).toEqual([]);
    expect(apiRequest).toHaveBeenCalledTimes(1);
  });
});
