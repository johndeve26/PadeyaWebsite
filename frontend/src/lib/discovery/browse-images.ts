import { DEFAULT_BROWSE_TILES } from "@/lib/discovery/default-browse-tiles";
import { brand } from "@/lib/brand";
import { SPONSORSHIP_HOSTS_PATH } from "@/lib/sponsor-marketplace-paths";

/** Known brand browse art under `/public/brand/browse/`. */
const CITY_IMAGES: Record<string, string> = {
  lagos: "/brand/browse/city-lagos.svg",
  abuja: "/brand/browse/city-abuja.svg",
  ibadan: "/brand/browse/city-ibadan.svg",
  akure: "/brand/browse/city-akure.svg",
  "port-harcourt": "/brand/browse/city-port-harcourt.svg",
  enugu: "/brand/browse/city-enugu.svg",
};

const CATEGORY_IMAGES: Record<string, string> = {
  nightlife: "/brand/browse/nightlife.svg",
  music: "/brand/browse/music.svg",
  comedy: "/brand/browse/comedy.svg",
  tech: "/brand/browse/tech.svg",
  gospel: "/brand/browse/gospel.svg",
  campus: "/brand/browse/campus.svg",
  "food-drink": "/brand/browse/food-drink.svg",
  "arts-culture": "/brand/browse/arts-culture.svg",
  lifestyle: "/brand/browse/food-drink.svg",
  business: "/brand/browse/tech.svg",
  community: "/brand/browse/campus.svg",
};

function imagesFromDefaults(rail: "city" | "interest"): Map<string, string> {
  const out = new Map<string, string>();
  for (const tile of DEFAULT_BROWSE_TILES) {
    if (tile.rail !== rail) continue;
    const slug = tile.href.split("/").filter(Boolean).pop();
    if (slug) out.set(slug, tile.image);
  }
  return out;
}

const CITY_FROM_DEFAULTS = imagesFromDefaults("city");
const CATEGORY_FROM_DEFAULTS = imagesFromDefaults("interest");

/** Resolve art for a city hub slug (browse tile art when available). */
export function cityBrowseImage(slug: string): string {
  const key = slug.trim().toLowerCase();
  return (
    CITY_IMAGES[key] ||
    CITY_FROM_DEFAULTS.get(key) ||
    brand.heroImage
  );
}

/** Resolve art for a category / interest slug. */
export function categoryBrowseImage(slug: string): string {
  const key = slug.trim().toLowerCase();
  return (
    CATEGORY_IMAGES[key] ||
    CATEGORY_FROM_DEFAULTS.get(key) ||
    brand.heroImage
  );
}

/** Art for curated collection hubs (weekend / free / VIP / format). */
export function collectionBrowseImage(href: string): string {
  const path = href.split("?")[0].replace(/\/$/, "");
  const byPath: Record<string, string> = {
    "/events/this-weekend": "/brand/browse/when-weekend.svg",
    "/events/free": "/brand/browse/price-free.svg",
    "/events/vip": "/brand/browse/price-vip.svg",
    "/events/near-me": "/brand/browse/city-lagos.svg",
    "/events/in-person": "/brand/browse/when-person.svg",
    "/events/online": "/brand/browse/when-online.svg",
    "/events/hybrid": "/brand/browse/when-hybrid.svg",
    "/events/under/5000": "/brand/browse/price-5k.svg",
    "/events/under/10000": "/brand/browse/price-10k.svg",
    "/events/under/25000": "/brand/browse/price-25k.svg",
    "/hosts": "/brand/browse/campus.svg",
    [SPONSORSHIP_HOSTS_PATH]: "/brand/browse/tech.svg",
  };
  return byPath[path] || brand.heroImage;
}

/**
 * Resolve browse art from any taxonomy / collection href
 * (`/events/c/…`, `/events/city/…`, `/events/under/…`, `/hosts`, …).
 */
export function browseImageForHref(href: string): string {
  try {
    const path = new URL(href, "https://padeya.local").pathname.replace(
      /\/$/,
      "",
    );
    const parts = path.split("/").filter(Boolean);

    if (parts[0] === "hosts" || parts[0] === "sponsors") {
      return collectionBrowseImage(path);
    }

    if (parts[0] !== "events") return collectionBrowseImage(path);

    // /events/c/{category}
    if (parts[1] === "c" && parts[2]) {
      return categoryBrowseImage(parts[2]);
    }

    // /events/city/{city}[/{category}]
    if (parts[1] === "city" && parts[2]) {
      if (parts[3]) return categoryBrowseImage(parts[3]);
      return cityBrowseImage(parts[2]);
    }

    // /events/state|country|area/{slug}[/{category}]
    if (
      (parts[1] === "state" ||
        parts[1] === "country" ||
        parts[1] === "area") &&
      parts[2]
    ) {
      if (parts[3]) return categoryBrowseImage(parts[3]);
      return brand.heroImage;
    }

    return collectionBrowseImage(path);
  } catch {
    return brand.heroImage;
  }
}
