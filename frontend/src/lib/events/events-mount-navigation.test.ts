import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

/**
 * Regression: anonymous /events must not mount-navigate into default facets.
 * (No Playwright in this package — source + pure URL builder cover the contract.)
 */
describe("/events mount navigation guards", () => {
  const client = readFileSync(
    path.join(
      process.cwd(),
      "src/components/events/marketplace/EventsMarketplaceClient.tsx",
    ),
    "utf8",
  );

  it("uses parseLatLngSearchParams instead of Number(null) lat/lng seed", () => {
    expect(client).toMatch(/parseLatLngSearchParams/);
    expect(client).not.toMatch(
      /const lat = Number\(searchParams\.get\("lat"\)\)/,
    );
  });

  it("gates price/location URL writes behind intentional sync refs", () => {
    expect(client).toMatch(/syncPriceToUrl/);
    expect(client).toMatch(/syncLocationToUrl/);
    expect(client).toMatch(/buildEventsListingHref/);
  });

  it("does not unconditionally write price_max from rangeMax < priceBoundMax", () => {
    // Old mount storm: if (rangeMax < priceBoundMax) params.set("price_max"...
    expect(client).not.toMatch(
      /if \(rangeMax < priceBoundMax\) params\.set\("price_max"/,
    );
  });
});
