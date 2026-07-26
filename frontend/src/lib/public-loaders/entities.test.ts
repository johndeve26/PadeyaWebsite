import { beforeEach, describe, expect, it, vi } from "vitest";

/**
 * React `cache()` is request-scoped inside RSC. Vitest has no render request
 * boundary, so we stub `cache` with a Map memo for call-count proof.
 */
const memoStore = vi.hoisted(() => new Map<string, Promise<unknown>>());

vi.mock("react", async () => {
  const actual = await vi.importActual<typeof import("react")>("react");
  return {
    ...actual,
    cache: <Args extends unknown[], R>(fn: (...args: Args) => R) => {
      return (...args: Args): R => {
        const key = `${fn.name}:${JSON.stringify(args)}`;
        if (!memoStore.has(key)) {
          memoStore.set(key, Promise.resolve(fn(...args)) as Promise<unknown>);
        }
        return memoStore.get(key) as R;
      };
    },
  };
});

const fetchPublicJson = vi.hoisted(() =>
  vi.fn(async (..._args: unknown[]) => ({
    data: { slug: "demo", title: "Demo" },
    status: 200,
  })),
);

vi.mock("@/lib/seo/public-fetch", () => ({
  fetchPublicJson,
}));

describe("public entity loaders (React cache)", () => {
  beforeEach(() => {
    fetchPublicJson.mockClear();
    memoStore.clear();
    vi.resetModules();
  });

  it("dedupes getPublicEventBySlug for identical slug", async () => {
    const mod = await import("./entities");
    mod.resetPublicLoaderCallCounts();
    const a = await mod.getPublicEventBySlug("demo-afrobeats-night-live");
    const b = await mod.getPublicEventBySlug("demo-afrobeats-night-live");
    expect(a).toEqual(b);
    expect(mod.publicLoaderCallCounts.event).toBe(1);
    expect(fetchPublicJson).toHaveBeenCalledTimes(1);
  });

  it("does not share cache across different slugs", async () => {
    const mod = await import("./entities");
    mod.resetPublicLoaderCallCounts();
    await mod.getPublicEventBySlug("a");
    await mod.getPublicEventBySlug("b");
    expect(mod.publicLoaderCallCounts.event).toBe(2);
    expect(fetchPublicJson).toHaveBeenCalledTimes(2);
  });

  it("fan loader uses no-store (privacy — never CDN-cache HTML data)", async () => {
    fetchPublicJson.mockResolvedValueOnce({
      data: { username: "pizzlecole", visibility: "public", display_name: "P" },
      status: 200,
    });
    const mod = await import("./entities");
    await mod.getPublicFanPassport("pizzlecole");
    expect(fetchPublicJson).toHaveBeenCalledWith(
      "/f/pizzlecole",
      expect.objectContaining({ revalidate: false }),
    );
  });
});
