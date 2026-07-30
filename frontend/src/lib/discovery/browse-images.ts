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
export function cityBrowseImage(
  slug: string,
  adminImageUrl?: string | null,
): string {
  if (adminImageUrl?.trim()) return adminImageUrl.trim();
  const key = slug.trim().toLowerCase();
  return (
    CITY_IMAGES[key] ||
    CITY_FROM_DEFAULTS.get(key) ||
    brand.heroImage
  );
}

/** Resolve art for a category / interest slug. */
export function categoryBrowseImage(
  slug: string,
  adminImageUrl?: string | null,
): string {
  if (adminImageUrl?.trim()) return adminImageUrl.trim();
  const key = slug.trim().toLowerCase();
  return (
    CATEGORY_IMAGES[key] ||
    CATEGORY_FROM_DEFAULTS.get(key) ||
    brand.heroImage
  );
}

export type BrowseCardVisuals = {
  imageUrl: string;
  imageAlt: string;
  focalX: number;
  focalY: number;
};

type TaxonomyImageFields = {
  primary_image_url?: string | null;
  image_url?: string | null;
  primary_image_alt?: string | null;
  image_alt?: string | null;
  primary_image_focal_x?: number | null;
  primary_image_focal_y?: number | null;
  image_focal_x?: number | null;
  image_focal_y?: number | null;
  hero_image_url?: string | null;
  hero_image_alt?: string | null;
  hero_image_focal_x?: number | null;
  hero_image_focal_y?: number | null;
};

/** Card art + accessibility from taxonomy category fields. */
export function categoryBrowseVisuals(
  slug: string,
  name: string,
  term?: TaxonomyImageFields | null,
): BrowseCardVisuals {
  // Cards prefer primary; if only a hero was uploaded, still show it.
  const adminUrl =
    term?.image_url ??
    term?.primary_image_url ??
    term?.hero_image_url ??
    null;
  return {
    imageUrl: categoryBrowseImage(slug, adminUrl),
    imageAlt:
      term?.image_alt ??
      term?.primary_image_alt ??
      term?.hero_image_alt ??
      name,
    focalX:
      term?.image_focal_x ??
      term?.primary_image_focal_x ??
      term?.hero_image_focal_x ??
      0.5,
    focalY:
      term?.image_focal_y ??
      term?.primary_image_focal_y ??
      term?.hero_image_focal_y ??
      0.5,
  };
}

/** Card art + accessibility from taxonomy location fields. */
export function cityBrowseVisuals(
  slug: string,
  name: string,
  loc?: TaxonomyImageFields | null,
): BrowseCardVisuals {
  const adminUrl =
    loc?.image_url ??
    loc?.primary_image_url ??
    loc?.hero_image_url ??
    null;
  return {
    imageUrl: cityBrowseImage(slug, adminUrl),
    imageAlt:
      loc?.image_alt ??
      loc?.primary_image_alt ??
      loc?.hero_image_alt ??
      name,
    focalX:
      loc?.image_focal_x ??
      loc?.primary_image_focal_x ??
      loc?.hero_image_focal_x ??
      0.5,
    focalY:
      loc?.image_focal_y ??
      loc?.primary_image_focal_y ??
      loc?.hero_image_focal_y ??
      0.5,
  };
}

/** Card art for any image-capable location kind (city/state/area). */
export function locationBrowseVisuals(
  slug: string,
  name: string,
  kind: string,
  loc?: TaxonomyImageFields | null,
): BrowseCardVisuals {
  if (kind === "city") return cityBrowseVisuals(slug, name, loc);
  const adminUrl = loc?.image_url ?? loc?.primary_image_url;
  return {
    imageUrl: adminUrl?.trim() || brand.heroImage,
    imageAlt: loc?.image_alt ?? loc?.primary_image_alt ?? name,
    focalX: loc?.image_focal_x ?? loc?.primary_image_focal_x ?? 0.5,
    focalY: loc?.image_focal_y ?? loc?.primary_image_focal_y ?? 0.5,
  };
}

/** Prefer hero, then primary, then fallback resolver. */
export function taxonomyHeroImage(
  slug: string,
  kind: "category" | "city",
  opts?: {
    heroUrl?: string | null;
    primaryUrl?: string | null;
  },
): string {
  if (opts?.heroUrl?.trim()) return opts.heroUrl.trim();
  if (opts?.primaryUrl?.trim()) return opts.primaryUrl.trim();
  return kind === "city" ? cityBrowseImage(slug) : categoryBrowseImage(slug);
}

/** Hero focal: hero image focal when set, else primary/card focal. */
export function taxonomyHeroFocal(
  term?: TaxonomyImageFields | null,
): { focalX: number; focalY: number } {
  if (term?.hero_image_url?.trim()) {
    return {
      focalX: term.hero_image_focal_x ?? 0.5,
      focalY: term.hero_image_focal_y ?? 0.5,
    };
  }
  return {
    focalX: term?.image_focal_x ?? term?.primary_image_focal_x ?? 0.5,
    focalY: term?.image_focal_y ?? term?.primary_image_focal_y ?? 0.5,
  };
}

/** Hero alt: hero alt when hero image set, else primary alt chain. */
export function taxonomyHeroAlt(
  term: TaxonomyImageFields | null | undefined,
  fallbackName: string,
): string {
  if (term?.hero_image_url?.trim()) {
    return term.hero_image_alt?.trim() || fallbackName;
  }
  return (
    term?.primary_image_alt?.trim() ||
    term?.image_alt?.trim() ||
    fallbackName
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
