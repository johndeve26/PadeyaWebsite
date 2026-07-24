import { apiRequest } from "@/lib/api";

export type LocationKind = "country" | "state" | "city" | "area";

export type TaxonomyLocation = {
  id: string;
  kind: LocationKind | string;
  name: string;
  slug: string;
  parent_id: string | null;
  state_code?: string | null;
  country_code?: string | null;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
};

export type TaxonomyLocationDetail = {
  location: TaxonomyLocation;
  ancestors: TaxonomyLocation[];
  children: TaxonomyLocation[];
  siblings?: TaxonomyLocation[];
};

export async function fetchTaxonomyLocations(opts?: {
  kind?: LocationKind | string;
  parentId?: string;
}): Promise<TaxonomyLocation[]> {
  const params = new URLSearchParams();
  if (opts?.kind) params.set("kind", opts.kind);
  if (opts?.parentId) params.set("parent_id", opts.parentId);
  const qs = params.toString();
  return apiRequest<TaxonomyLocation[]>(
    `/taxonomy/locations${qs ? `?${qs}` : ""}`,
    { auth: false },
  );
}

export async function fetchTaxonomyLocationDetail(
  kind: LocationKind | string,
  slug: string,
): Promise<TaxonomyLocationDetail> {
  return apiRequest<TaxonomyLocationDetail>(
    `/taxonomy/locations/${encodeURIComponent(kind)}/${encodeURIComponent(slug)}`,
    { auth: false },
  );
}

export type TaxonomyVocabTerm = {
  id: string;
  name: string;
  slug: string;
  description?: string | null;
  is_active?: boolean;
};

export async function fetchVenueTypes(): Promise<TaxonomyVocabTerm[]> {
  return apiRequest<TaxonomyVocabTerm[]>("/taxonomy/venue-types", {
    auth: false,
  });
}

/** Host suggests a new area under a city — saved active for all hosts. */
export async function suggestTaxonomyArea(input: {
  cityId: string;
  name: string;
}): Promise<TaxonomyLocation> {
  return apiRequest<TaxonomyLocation>("/taxonomy/locations/suggest-area", {
    method: "POST",
    body: { city_id: input.cityId, name: input.name },
  });
}

/** Match a taxonomy row by display name or slug (case-insensitive). */
export function findTaxonomyLocationByName(
  locations: TaxonomyLocation[],
  name: string | null | undefined,
): TaxonomyLocation | null {
  const key = (name || "").trim().toLowerCase();
  if (!key) return null;
  const slugish = key.replace(/\s+/g, "-");
  return (
    locations.find((l) => l.name.trim().toLowerCase() === key) ??
    locations.find((l) => l.slug === slugish) ??
    null
  );
}

/** Host suggests a new city under a state — saved active for all hosts. */
export async function suggestTaxonomyCity(input: {
  stateId: string;
  name: string;
}): Promise<TaxonomyLocation> {
  return apiRequest<TaxonomyLocation>("/taxonomy/locations/suggest-city", {
    method: "POST",
    body: { state_id: input.stateId, name: input.name },
  });
}

/** Host suggests a new venue type — saved active for all hosts. */
export async function suggestVenueType(input: {
  name: string;
}): Promise<TaxonomyVocabTerm> {
  return apiRequest<TaxonomyVocabTerm>("/taxonomy/venue-types/suggest", {
    method: "POST",
    body: { name: input.name },
  });
}

export function locationHubPath(
  kind: LocationKind | string,
  slug: string,
): string {
  return `/events/${kind}/${slug}`;
}
