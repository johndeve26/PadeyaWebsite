/**
 * Hub indexability thresholds + eligibility (Phase 1B).
 * Tunable in one place — do not scatter magic numbers in pages/sitemap.
 */

export const HUB_ELIGIBILITY = {
  /** Minimum listed public events for country/state/city hubs. */
  locationMinEvents: 2,
  /** Areas are finer-grained; slightly lower bar. */
  areaMinEvents: 1,
  /** City × category combinations — stricter thin-content risk. */
  cityCategoryMinEvents: 2,
} as const;

/** Curated override on Location.seo_index_mode */
export type SeoIndexMode = "auto" | "force_index" | "force_noindex";

export function normalizeSeoIndexMode(
  value: string | null | undefined,
): SeoIndexMode {
  const v = (value || "auto").trim().toLowerCase();
  if (v === "force_index" || v === "force_noindex") return v;
  return "auto";
}

export type LocationHubEligibilityInput = {
  exists: boolean;
  isActive?: boolean | null;
  kind?: string | null;
  eventCount: number;
  seoIndexMode?: string | null;
};

export type HubEligibilityResult = {
  indexable: boolean;
  reason:
    | "missing"
    | "inactive"
    | "force_noindex"
    | "force_index"
    | "below_threshold"
    | "ok";
  minRequired: number;
};

export function minEventsForLocationKind(kind: string | null | undefined): number {
  const k = (kind || "").trim().toLowerCase();
  if (k === "area") return HUB_ELIGIBILITY.areaMinEvents;
  return HUB_ELIGIBILITY.locationMinEvents;
}

export function evaluateLocationHubEligibility(
  input: LocationHubEligibilityInput,
): HubEligibilityResult {
  if (!input.exists) {
    return {
      indexable: false,
      reason: "missing",
      minRequired: minEventsForLocationKind(input.kind),
    };
  }
  if (input.isActive === false) {
    return {
      indexable: false,
      reason: "inactive",
      minRequired: minEventsForLocationKind(input.kind),
    };
  }

  const mode = normalizeSeoIndexMode(input.seoIndexMode);
  const minRequired = minEventsForLocationKind(input.kind);

  if (mode === "force_noindex") {
    return { indexable: false, reason: "force_noindex", minRequired };
  }
  if (mode === "force_index") {
    return { indexable: true, reason: "force_index", minRequired };
  }

  if (input.eventCount < minRequired) {
    return { indexable: false, reason: "below_threshold", minRequired };
  }
  return { indexable: true, reason: "ok", minRequired };
}

export type CityCategoryHubEligibilityInput = {
  cityExists: boolean;
  cityActive?: boolean | null;
  categoryExists: boolean;
  categoryActive?: boolean | null;
  eventCount: number;
  /** Optional city-level force_noindex blocks combinations too. */
  citySeoIndexMode?: string | null;
};

export function evaluateCityCategoryHubEligibility(
  input: CityCategoryHubEligibilityInput,
): HubEligibilityResult {
  const minRequired = HUB_ELIGIBILITY.cityCategoryMinEvents;
  if (!input.cityExists || !input.categoryExists) {
    return { indexable: false, reason: "missing", minRequired };
  }
  if (input.cityActive === false || input.categoryActive === false) {
    return { indexable: false, reason: "inactive", minRequired };
  }
  if (normalizeSeoIndexMode(input.citySeoIndexMode) === "force_noindex") {
    return { indexable: false, reason: "force_noindex", minRequired };
  }
  if (input.eventCount < minRequired) {
    return { indexable: false, reason: "below_threshold", minRequired };
  }
  return { indexable: true, reason: "ok", minRequired };
}

/** Natural, non-spammy fallback title/description for location hubs. */
export function locationHubFallbackCopy(opts: {
  locationName: string;
  kind?: string | null;
  parentName?: string | null;
  categoryName?: string | null;
}): { title: string; description: string } {
  const name = opts.locationName.trim() || "this place";
  const parent = opts.parentName?.trim();
  const cat = opts.categoryName?.trim();
  const kind = (opts.kind || "").toLowerCase();

  if (cat) {
    return {
      title: `${cat} events in ${name}`,
      description: `Find ${cat.toLowerCase()} events in ${name} on Pàdéyá — verified tickets and trusted hosts.`,
    };
  }

  const place =
    kind === "area" && parent ? `${name}, ${parent}` : name;

  return {
    title: `Events in ${place}`,
    description: `Discover concerts, parties, and community events in ${place} on Pàdéyá.`,
  };
}

/** Short inventory intro — no fabricated editorial claims. */
export function locationHubIntroParagraph(opts: {
  locationName: string;
  parentName?: string | null;
  eventCount: number;
  categoryNames?: string[];
  curatedIntro?: string | null;
}): string {
  const curated = opts.curatedIntro?.trim();
  if (curated) return curated.slice(0, 400);

  const name = opts.locationName.trim();
  const parentBit = opts.parentName?.trim()
    ? ` in ${opts.parentName.trim()}`
    : "";
  const count = Math.max(0, opts.eventCount);
  const cats = (opts.categoryNames || []).filter(Boolean).slice(0, 4);
  const catBit =
    cats.length > 0
      ? ` Popular scenes include ${cats.join(", ")}.`
      : "";

  if (count === 0) {
    return `Browse events in ${name}${parentBit} on Pàdéyá. New listings appear here as hosts publish.${catBit}`;
  }
  if (count === 1) {
    return `Explore 1 public event in ${name}${parentBit} on Pàdéyá — verified tickets and trusted hosts.${catBit}`;
  }
  return `Explore ${count} public events in ${name}${parentBit} on Pàdéyá — verified tickets and trusted hosts.${catBit}`;
}

export type SitemapLocationLike = {
  kind: string;
  slug: string;
  is_active?: boolean;
  seo_index_mode?: string | null;
};

export type SitemapEventForHubs = {
  city?: string | null;
  category?: { slug?: string | null } | null;
  location?: {
    kind?: string | null;
    slug?: string | null;
    ancestors?: Array<{ kind?: string | null; slug?: string | null }> | null;
  } | null;
};

function slugifyCity(s: string): string {
  return s
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

/** Count listed events per `kind::slug` and city×category for sitemap gates. */
export function buildHubInventoryFromEvents(events: SitemapEventForHubs[]): {
  locationCounts: Map<string, number>;
  cityCategoryCounts: Map<string, number>;
} {
  const locationCounts = new Map<string, number>();
  const cityCategoryCounts = new Map<string, number>();

  const bump = (map: Map<string, number>, key: string) => {
    map.set(key, (map.get(key) || 0) + 1);
  };

  for (const event of events) {
    const loc = event.location;
    if (loc?.kind && loc?.slug) {
      bump(locationCounts, `${loc.kind}::${loc.slug}`);
      for (const a of loc.ancestors ?? []) {
        if (a.kind && a.slug) bump(locationCounts, `${a.kind}::${a.slug}`);
      }
    } else if (event.city) {
      const citySlug = slugifyCity(event.city);
      if (citySlug) bump(locationCounts, `city::${citySlug}`);
    }

    const cat = event.category?.slug?.trim();
    const citySlug =
      loc?.kind === "city" && loc.slug
        ? loc.slug
        : loc?.ancestors?.find((a) => a.kind === "city")?.slug ||
          (event.city ? slugifyCity(event.city) : "");
    if (cat && citySlug) {
      bump(cityCategoryCounts, `${citySlug}::${cat}`);
    }
  }

  return { locationCounts, cityCategoryCounts };
}

export function isLocationInSitemap(
  loc: SitemapLocationLike,
  locationCounts: Map<string, number>,
): boolean {
  const count = locationCounts.get(`${loc.kind}::${loc.slug}`) || 0;
  return evaluateLocationHubEligibility({
    exists: true,
    isActive: loc.is_active,
    kind: loc.kind,
    eventCount: count,
    seoIndexMode: loc.seo_index_mode,
  }).indexable;
}

export function isCityCategoryInSitemap(
  citySlug: string,
  categorySlug: string,
  cityCategoryCounts: Map<string, number>,
  cityLoc?: SitemapLocationLike | null,
): boolean {
  const count =
    cityCategoryCounts.get(`${citySlug}::${categorySlug}`) || 0;
  return evaluateCityCategoryHubEligibility({
    cityExists: true,
    cityActive: cityLoc?.is_active !== false,
    categoryExists: true,
    categoryActive: true,
    eventCount: count,
    citySeoIndexMode: cityLoc?.seo_index_mode,
  }).indexable;
}
