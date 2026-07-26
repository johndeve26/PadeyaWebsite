import { describe, expect, it } from "vitest";

import {
  FAN_PASSPORT_CACHE,
  isPrivateNeverCachePath,
  PUBLIC_CACHE_POLICY,
} from "./public-cache-policy";

describe("public cache policy", () => {
  it("never lists private surfaces as cacheable", () => {
    const never = new Set(PUBLIC_CACHE_POLICY.PRIVATE_NEVER_CACHE);
    for (const key of PUBLIC_CACHE_POLICY.PUBLIC_CACHEABLE) {
      expect(never.has(key as never)).toBe(false);
    }
  });

  it("marks private fan passport as never cache", () => {
    expect(FAN_PASSPORT_CACHE.private.class).toBe("PRIVATE_NEVER_CACHE");
    expect(FAN_PASSPORT_CACHE.public.indexable).toBe(true);
    expect(FAN_PASSPORT_CACHE.unlisted.indexable).toBe(false);
  });

  it("detects private path prefixes and fan HTML paths", () => {
    expect(isPrivateNeverCachePath("/dashboard")).toBe(true);
    expect(isPrivateNeverCachePath("/messages/1")).toBe(true);
    expect(isPrivateNeverCachePath("/events")).toBe(false);
    expect(isPrivateNeverCachePath("/f/pizzlecole")).toBe(true);
  });
});
