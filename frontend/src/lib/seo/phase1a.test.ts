import { describe, expect, it } from "vitest";

import {
  eventJsonLd,
  eventStatusSchemaUrl,
  isPasswordProtectedEvent,
} from "./event-metadata";
import { collectionPageJsonLd } from "./jsonld";
import {
  isMerchProductSchemaEligible,
  merchOfferAvailability,
  merchProductJsonLd,
} from "./merch-metadata";
import {
  configuredOrganizationSameAs,
  EVENTS_SEARCH_ACTION_TEMPLATE,
  ORGANIZATION_ID,
  organizationJsonLd,
  siteGraphJsonLd,
  WEBSITE_ID,
  websiteJsonLd,
} from "./site-graph";
import type { EventItem } from "@/lib/types/events";

function baseEvent(over: Partial<EventItem> = {}): EventItem {
  return {
    id: "e1",
    host_id: "h1",
    title: "Lagos Night",
    slug: "lagos-night",
    description: "A great night out",
    short_tagline: "Night out",
    status: "published",
    visibility: "listed",
    event_type: "in_person",
    start_datetime: "2026-08-01T18:00:00Z",
    end_datetime: "2026-08-01T23:00:00Z",
    featured: false,
    seo_title: null,
    seo_description: null,
    rejection_reason: null,
    published_at: "2026-07-01T00:00:00Z",
    created_at: "2026-06-01T00:00:00Z",
    city: "Lagos",
    location_visibility: "city_only",
    location_address_revealed: false,
    host_display_name: "DJ Ade",
    host_slug: "dj-ade",
    ticket_types: [],
    ...over,
  } as EventItem;
}

describe("sitewide Organization / WebSite graph", () => {
  it("emits Organization once with canonical @id and production URL", () => {
    const org = organizationJsonLd({});
    expect(org["@type"]).toBe("Organization");
    expect(org["@id"]).toBe(ORGANIZATION_ID);
    expect(org["@id"]).toBe("https://padeya.com/#organization");
    expect(org.url).toBe("https://padeya.com");
    expect(org.name).toBe("Pàdéyá");
    expect(org).not.toHaveProperty("address");
    expect(org).not.toHaveProperty("telephone");
    expect(org).not.toHaveProperty("foundingDate");
    expect(org).not.toHaveProperty("aggregateRating");
    expect(org).not.toHaveProperty("sameAs");
  });

  it("only includes sameAs from configured https URLs", () => {
    expect(
      configuredOrganizationSameAs({
        NEXT_PUBLIC_SOCIAL_SAME_AS:
          "https://instagram.com/padeya, http://insecure.example, not-a-url",
      }),
    ).toEqual(["https://instagram.com/padeya"]);
  });

  it("emits WebSite once referencing Organization @id", () => {
    const site = websiteJsonLd();
    expect(site["@type"]).toBe("WebSite");
    expect(site["@id"]).toBe(WEBSITE_ID);
    expect(site.url).toBe("https://padeya.com");
    expect(site.publisher).toEqual({ "@id": ORGANIZATION_ID });
  });

  it("site graph contains exactly one Organization and one WebSite", () => {
    const graph = siteGraphJsonLd()["@graph"] as Record<string, unknown>[];
    expect(graph).toHaveLength(2);
    expect(graph.filter((n) => n["@type"] === "Organization")).toHaveLength(1);
    expect(graph.filter((n) => n["@type"] === "WebSite")).toHaveLength(1);
  });

  it("CollectionPage references WebSite @id instead of embedding a full WebSite", () => {
    const page = collectionPageJsonLd({
      name: "Events",
      description: "Discover events",
      path: "/events",
      origin: "https://padeya.com",
    });
    expect(page.isPartOf).toEqual({ "@id": WEBSITE_ID });
    expect(JSON.stringify(page)).not.toContain('"@type":"WebSite"');
  });
});

describe("SearchAction", () => {
  it("targets working /events?q= template, not /events/search?q=", () => {
    const site = websiteJsonLd({ includeSearchAction: true });
    const action = site.potentialAction as Record<string, unknown>;
    expect(action["@type"]).toBe("SearchAction");
    const target = action.target as Record<string, unknown>;
    expect(target.urlTemplate).toBe(EVENTS_SEARCH_ACTION_TEMPLATE);
    expect(String(target.urlTemplate)).toContain("/events?q=");
    expect(String(target.urlTemplate)).not.toContain("/events/search");
  });

  it("can omit SearchAction when disabled", () => {
    const site = websiteJsonLd({ includeSearchAction: false });
    expect(site).not.toHaveProperty("potentialAction");
  });
});

describe("Product JSON-LD", () => {
  const base = {
    name: "Legacy Tee",
    slug: "legacy-tee",
    short_description: "Soft cotton tee",
    base_price: "8500",
    currency: "NGN",
    availability: "purchasable",
    indexable: true,
    host_name: "DJ Ade",
    host_slug: "dj-ade",
    cover_image_url: "/media/tee.jpg",
  };

  it("emits Product + Offer for public indexable merch", () => {
    const ld = merchProductJsonLd(base);
    expect(ld?.["@type"]).toBe("Product");
    expect(ld?.["@id"]).toBe("https://padeya.com/merch/legacy-tee#product");
    const offer = ld?.offers as Record<string, unknown>;
    expect(offer.price).toBe("8500");
    expect(offer.priceCurrency).toBe("NGN");
    expect(offer.availability).toBe("https://schema.org/InStock");
    const blob = JSON.stringify(ld);
    expect(blob).not.toMatch(/inventory|buyer|order_id|vault_item|moderation/i);
    expect(ld).not.toHaveProperty("aggregateRating");
    expect(ld).not.toHaveProperty("sku");
  });

  it("maps sold out correctly", () => {
    expect(merchOfferAvailability("sold_out")).toBe(
      "https://schema.org/SoldOut",
    );
    const ld = merchProductJsonLd({ ...base, availability: "sold_out" });
    expect((ld?.offers as Record<string, unknown>).availability).toBe(
      "https://schema.org/SoldOut",
    );
  });

  it("does not emit Product for missing / noindex merch", () => {
    expect(merchProductJsonLd(null)).toBeNull();
    expect(isMerchProductSchemaEligible({ ...base, indexable: false })).toBe(
      false,
    );
    expect(merchProductJsonLd({ ...base, indexable: false })).toBeNull();
  });

  it("omits Offer for locked availability without inventing stock state", () => {
    const ld = merchProductJsonLd({ ...base, availability: "locked" });
    expect(ld?.["@type"]).toBe("Product");
    expect(ld).not.toHaveProperty("offers");
  });

  it("uses actual product currency", () => {
    const ld = merchProductJsonLd({ ...base, currency: "usd" });
    expect((ld?.offers as Record<string, unknown>).priceCurrency).toBe("USD");
  });
});

describe("Event eventStatus", () => {
  it("maps published (incl. past) to EventScheduled, not Cancelled", () => {
    expect(eventStatusSchemaUrl({ status: "published" })).toBe(
      "https://schema.org/EventScheduled",
    );
    const past = eventJsonLd(
      baseEvent({
        start_datetime: "2020-01-01T18:00:00Z",
        end_datetime: "2020-01-01T23:00:00Z",
      }),
    );
    expect(past?.eventStatus).toBe("https://schema.org/EventScheduled");
    expect(past?.eventStatus).not.toBe("https://schema.org/EventCancelled");
  });

  it("maps cancelled when modeled", () => {
    expect(eventStatusSchemaUrl({ status: "cancelled" })).toBe(
      "https://schema.org/EventCancelled",
    );
  });

  it("does not invent postponed/rescheduled mappings", () => {
    expect(eventStatusSchemaUrl({ status: "completed" })).toBeUndefined();
    expect(eventStatusSchemaUrl({ status: "draft" })).toBeUndefined();
  });

  it("does not emit Event JSON-LD for password events", () => {
    const ev = baseEvent({ visibility: "password_protected" });
    expect(isPasswordProtectedEvent(ev)).toBe(true);
    expect(eventJsonLd(ev)).toBeNull();
  });
});
