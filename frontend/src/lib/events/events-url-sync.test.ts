import { describe, expect, it } from "vitest";

import {
  buildEventsListingHref,
  parseLatLngSearchParams,
} from "./events-url-sync";
import { DEFAULT_PRICE_BOUND_MAX } from "./marketplace-listing";

function params(record: Record<string, string>) {
  return {
    get(name: string) {
      return record[name] ?? null;
    },
  };
}

describe("parseLatLngSearchParams", () => {
  it("does not treat missing lat/lng as 0 (Number(null) trap)", () => {
    expect(parseLatLngSearchParams(params({}))).toBeNull();
    expect(parseLatLngSearchParams(params({ lat: "6.5" }))).toBeNull();
  });

  it("rejects Null Island 0,0 placeholders", () => {
    expect(parseLatLngSearchParams(params({ lat: "0", lng: "0" }))).toBeNull();
  });

  it("accepts real coordinates", () => {
    expect(
      parseLatLngSearchParams(params({ lat: "6.5244", lng: "3.3792" })),
    ).toEqual({ lat: 6.5244, lng: 3.3792 });
  });
});

describe("buildEventsListingHref mount defaults", () => {
  const defaults = {
    city: "all" as const,
    date: "any" as const,
    priceMin: 0,
    priceMax: DEFAULT_PRICE_BOUND_MAX,
    priceBoundMax: 50_000,
    syncPriceToUrl: false,
    sort: "recommended" as const,
    view: "grid" as const,
    proximityActive: true,
    syncLocationToUrl: false,
    location: {
      lat: 6.5,
      lng: 3.3,
      radiusKm: 25 as const,
      label: "Near you",
    },
  };

  it("keeps bare /events when defaults are not user/deep-link intent", () => {
    expect(buildEventsListingHref("/events", defaults)).toBe("/events");
  });

  it("does not inject price_max when syncPriceToUrl is false", () => {
    const href = buildEventsListingHref("/events", {
      ...defaults,
      proximityActive: false,
      location: null,
      priceMax: DEFAULT_PRICE_BOUND_MAX,
      priceBoundMax: 50_000,
      syncPriceToUrl: false,
    });
    expect(href).toBe("/events");
    expect(href).not.toContain("price_max");
  });

  it("writes price_max only when intentionally synced", () => {
    const href = buildEventsListingHref("/events", {
      ...defaults,
      proximityActive: false,
      location: null,
      syncPriceToUrl: true,
      priceMax: 500,
      priceBoundMax: 50_000,
    });
    expect(href).toContain("price_max=500");
  });

  it("writes lat/lng only when syncLocationToUrl is true", () => {
    const silent = buildEventsListingHref("/events", defaults);
    expect(silent).not.toContain("lat=");
    const pinned = buildEventsListingHref("/events", {
      ...defaults,
      syncLocationToUrl: true,
    });
    expect(pinned).toContain("lat=6.5");
    expect(pinned).toContain("lng=3.3");
  });
});
