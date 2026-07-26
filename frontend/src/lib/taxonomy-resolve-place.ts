/**
 * Resolve Google Places geo hints to a Pàdéyá taxonomy leaf.
 * Used by event studio so Maps picks update location_id + dual-write labels.
 *
 * When a city/area from Maps is missing, optionally suggest/create it under the
 * matched parent (same host APIs as “Other…” in the cascade).
 */

import {
  fetchTaxonomyLocations,
  findTaxonomyLocationByName,
  suggestTaxonomyArea,
  suggestTaxonomyCity,
  type TaxonomyLocation,
} from "@/lib/taxonomy-api";

export type PlaceGeoHints = {
  countryHint?: string | null;
  stateHint?: string | null;
  cityHint?: string | null;
  areaHint?: string | null;
};

export type ResolvedTaxonomyPlace = {
  locationId: string;
  country: string;
  state: string;
  city: string;
  area: string;
  /** Deepest matched taxonomy node (area → city → state → country). */
  leaf: TaxonomyLocation;
  matched: {
    country: TaxonomyLocation | null;
    state: TaxonomyLocation | null;
    city: TaxonomyLocation | null;
    area: TaxonomyLocation | null;
  };
  /** True when a city and/or area was created via suggest APIs. */
  created?: { city?: boolean; area?: boolean };
};

export type TaxonomyPlaceLookup = {
  countries: TaxonomyLocation[];
  statesFor: (countryId: string) => TaxonomyLocation[] | Promise<TaxonomyLocation[]>;
  citiesFor: (stateId: string) => TaxonomyLocation[] | Promise<TaxonomyLocation[]>;
  areasFor: (cityId: string) => TaxonomyLocation[] | Promise<TaxonomyLocation[]>;
};

const COUNTRY_ALIASES: Record<string, string[]> = {
  nigeria: ["ng", "federal republic of nigeria"],
  "united kingdom": ["uk", "gb", "great britain", "britain", "england"],
  "united states": [
    "usa",
    "us",
    "united states of america",
    "america",
  ],
  ghana: ["gh"],
  kenya: ["ke"],
  "south africa": ["za", "rsa"],
  canada: ["ca"],
  ireland: ["ie", "éire", "eire"],
  australia: ["au"],
};

function normalizePlaceName(raw: string | null | undefined): string {
  return (raw || "")
    .trim()
    .toLowerCase()
    .replace(/[’']/g, "'")
    .replace(/\s+/g, " ");
}

/** Strip common admin suffixes so "Lagos State" matches "Lagos". */
function stripAdminSuffix(name: string): string {
  return name
    .replace(
      /\s+(state|province|region|county|territory|emirate|department)$/i,
      "",
    )
    .trim();
}

function findByNameOrAlias(
  locations: TaxonomyLocation[],
  hint: string | null | undefined,
): TaxonomyLocation | null {
  const key = normalizePlaceName(hint);
  if (!key) return null;

  const stripped = stripAdminSuffix(key);
  const candidates = [key, stripped].filter(Boolean);

  for (const candidate of candidates) {
    const hit = findTaxonomyLocationByName(locations, candidate);
    if (hit) return hit;
  }

  // Country aliases / ISO-ish codes stored on rows.
  for (const loc of locations) {
    const nameKey = normalizePlaceName(loc.name);
    const aliases = COUNTRY_ALIASES[nameKey] ?? [];
    if (aliases.includes(key) || aliases.includes(stripped)) return loc;
    const code = (loc.country_code || loc.state_code || "").trim().toLowerCase();
    if (code && (code === key || code === stripped)) return loc;
  }

  // Soft containment: prefer longest taxonomy name contained in the hint
  // (e.g. hint "Lekki Phase 1" → area "Lekki Phase 1"; hint "Foo Lekki" → "Lekki").
  let best: TaxonomyLocation | null = null;
  let bestLen = 0;
  for (const loc of locations) {
    const nameKey = normalizePlaceName(loc.name);
    if (nameKey.length < 3) continue;
    if (key === nameKey || key.includes(nameKey) || nameKey.includes(key)) {
      if (nameKey.length > bestLen) {
        best = loc;
        bestLen = nameKey.length;
      }
    }
  }
  return best;
}

/**
 * Pure cascade match against a lookup. Prefer area, else city/state/country.
 * Returns null when country cannot be matched.
 */
export async function matchTaxonomyFromPlaceHints(
  hints: PlaceGeoHints,
  lookup: TaxonomyPlaceLookup,
): Promise<ResolvedTaxonomyPlace | null> {
  const country = findByNameOrAlias(lookup.countries, hints.countryHint);
  if (!country) return null;

  let state: TaxonomyLocation | null = null;
  let city: TaxonomyLocation | null = null;
  let area: TaxonomyLocation | null = null;

  if (hints.stateHint?.trim()) {
    const states = await Promise.resolve(lookup.statesFor(country.id));
    state = findByNameOrAlias(states, hints.stateHint);
  }

  if (state) {
    const cities = await Promise.resolve(lookup.citiesFor(state.id));
    // 1) Explicit city from Places (locality / admin L2)
    if (hints.cityHint?.trim()) {
      city = findByNameOrAlias(cities, hints.cityHint);
    }
    // 2) Many hubs use a city named like the state (Lagos / Lagos).
    if (!city) {
      city = findByNameOrAlias(cities, state.name);
    }
    // 3) Sometimes Places puts the neighbourhood in locality — try area hint as city.
    if (!city && hints.areaHint?.trim()) {
      city = findByNameOrAlias(cities, hints.areaHint);
    }
  }

  if (city && hints.areaHint?.trim()) {
    const areas = await Promise.resolve(lookup.areasFor(city.id));
    area = findByNameOrAlias(areas, hints.areaHint);
  }

  const leaf = area ?? city ?? state ?? country;
  return {
    locationId: leaf.id,
    country: country.name,
    state: state?.name ?? "",
    city: city?.name ?? "",
    area: area?.name ?? "",
    leaf,
    matched: { country, state, city, area },
  };
}

/** Fetch taxonomy rows and resolve Places hints to a leaf (match only). */
export async function resolveTaxonomyFromPlaceHints(
  hints: PlaceGeoHints,
): Promise<ResolvedTaxonomyPlace | null> {
  if (!hints.countryHint?.trim()) return null;

  const countries = await fetchTaxonomyLocations({ kind: "country" });
  return matchTaxonomyFromPlaceHints(hints, {
    countries,
    statesFor: (countryId) =>
      fetchTaxonomyLocations({ kind: "state", parentId: countryId }),
    citiesFor: (stateId) =>
      fetchTaxonomyLocations({ kind: "city", parentId: stateId }),
    areasFor: (cityId) =>
      fetchTaxonomyLocations({ kind: "area", parentId: cityId }),
  });
}

export type EnsureTaxonomyOptions = {
  /** Create missing city/area via host suggest APIs (requires auth). Default true. */
  createMissing?: boolean;
};

/**
 * Resolve Places hints to taxonomy, creating missing city/area when possible.
 * Does not create countries or states (catalog / admin only).
 */
export async function ensureTaxonomyFromPlaceHints(
  hints: PlaceGeoHints,
  options: EnsureTaxonomyOptions = {},
): Promise<ResolvedTaxonomyPlace | null> {
  const createMissing = options.createMissing !== false;
  if (!hints.countryHint?.trim()) return null;

  const countries = await fetchTaxonomyLocations({ kind: "country" });
  const country = findByNameOrAlias(countries, hints.countryHint);
  if (!country) return null;

  const created = { city: false, area: false };

  let state: TaxonomyLocation | null = null;
  if (hints.stateHint?.trim()) {
    const states = await fetchTaxonomyLocations({
      kind: "state",
      parentId: country.id,
    });
    state = findByNameOrAlias(states, hints.stateHint);
  }

  let city: TaxonomyLocation | null = null;
  if (state) {
    let cities = await fetchTaxonomyLocations({
      kind: "city",
      parentId: state.id,
    });
    if (hints.cityHint?.trim()) {
      city = findByNameOrAlias(cities, hints.cityHint);
    }
    if (!city) {
      city = findByNameOrAlias(cities, state.name);
    }
    if (!city && hints.areaHint?.trim()) {
      city = findByNameOrAlias(cities, hints.areaHint);
    }

    // Create city when Places named one we don't have (not when we only fell
    // back to state-name city — that already covers Lagos/etc.).
    const cityNameToCreate = (hints.cityHint || "").trim();
    if (
      !city &&
      createMissing &&
      cityNameToCreate.length >= 2 &&
      normalizePlaceName(cityNameToCreate) !== normalizePlaceName(state.name)
    ) {
      try {
        city = await suggestTaxonomyCity({
          stateId: state.id,
          name: cityNameToCreate,
        });
        created.city = true;
        cities = await fetchTaxonomyLocations({
          kind: "city",
          parentId: state.id,
        });
        city =
          cities.find((c) => c.id === city!.id) ??
          findByNameOrAlias(cities, cityNameToCreate) ??
          city;
      } catch {
        /* leave unmatched — host can use Other… */
      }
    }

    // Still no city — use state-named city if present after create attempts.
    if (!city) {
      city = findByNameOrAlias(cities, state.name);
    }
  }

  let area: TaxonomyLocation | null = null;
  const areaName = (hints.areaHint || "").trim();
  if (city && areaName.length >= 2) {
    let areas = await fetchTaxonomyLocations({
      kind: "area",
      parentId: city.id,
    });
    area = findByNameOrAlias(areas, areaName);
    if (!area && createMissing) {
      // Don't create an area that duplicates the city name.
      if (normalizePlaceName(areaName) !== normalizePlaceName(city.name)) {
        try {
          area = await suggestTaxonomyArea({
            cityId: city.id,
            name: areaName,
          });
          created.area = true;
          areas = await fetchTaxonomyLocations({
            kind: "area",
            parentId: city.id,
          });
          area =
            areas.find((a) => a.id === area!.id) ??
            findByNameOrAlias(areas, areaName) ??
            area;
        } catch {
          /* leave unmatched */
        }
      }
    }
  }

  const leaf = area ?? city ?? state ?? country;
  return {
    locationId: leaf.id,
    country: country.name,
    state: state?.name ?? "",
    city: city?.name ?? "",
    area: area?.name ?? "",
    leaf,
    matched: { country, state, city, area },
    created,
  };
}

/** Public discovery label from a resolved taxonomy place. */
export function publicLabelFromResolvedPlace(
  resolved: ResolvedTaxonomyPlace,
  fallbackArea?: string | null,
  fallbackCity?: string | null,
): string {
  if (resolved.area) {
    return [resolved.area, resolved.city || resolved.state]
      .filter(Boolean)
      .join(", ");
  }
  if (resolved.city) return resolved.city;
  if (resolved.state) return resolved.state;
  const fallback = [fallbackArea, fallbackCity].filter(Boolean).join(", ");
  return fallback || resolved.country;
}
