import { apiRequest } from "@/lib/api";
import type { EventItem } from "@/lib/types/events";

export type PlacementContextType =
  | "homepage"
  | "events_page"
  | "country_page"
  | "state_page"
  | "city_page"
  | "area_page"
  | "category_page"
  | "city_category_page"
  | "global_homepage"
  | "events"
  | "country"
  | "state"
  | "city"
  | "area"
  | "category"
  | "city_category";

export const PLACEMENT_CONTEXT_OPTIONS: {
  value: PlacementContextType;
  label: string;
}[] = [
  { value: "homepage", label: "Global homepage" },
  { value: "events_page", label: "Events page" },
  { value: "country_page", label: "Country page" },
  { value: "state_page", label: "State page" },
  { value: "city_page", label: "City page" },
  { value: "area_page", label: "Area page" },
  { value: "category_page", label: "Category page" },
  { value: "city_category_page", label: "City + category page" },
];

export type PlacementStatus =
  | "draft"
  | "active"
  | "scheduled"
  | "expired"
  | "archived";

export type FeaturedPlacementSlot = {
  id: string;
  placement_key: string;
  context_key?: string;
  placement_type: string;
  context_type: string;
  context_id?: string | null;
  location_id: string | null;
  country_id?: string | null;
  state_id?: string | null;
  city_id?: string | null;
  area_id?: string | null;
  category_id: string | null;
  slot_number: number;
  slot_index?: number;
  slot_label: string;
  event_id: string | null;
  title_override?: string | null;
  subtitle_override?: string | null;
  badge_text?: string | null;
  starts_at?: string | null;
  ends_at?: string | null;
  status: PlacementStatus | string;
  event: EventItem | null;
  created_by?: string | null;
  updated_by?: string | null;
  created_at: string;
  updated_at: string;
};

export type FeaturedPlacementContext = {
  id?: string | null;
  context_key: string;
  placement_key?: string;
  context_type: PlacementContextType | string;
  placement_type?: string;
  context_label: string;
  location_id: string | null;
  country_id?: string | null;
  state_id?: string | null;
  city_id?: string | null;
  area_id?: string | null;
  category_id: string | null;
  location_name: string | null;
  location_slug: string | null;
  location_kind: string | null;
  category_name: string | null;
  category_slug: string | null;
  display_title: string;
  status?: PlacementStatus | string | null;
  starts_at?: string | null;
  ends_at?: string | null;
  title_override?: string | null;
  subtitle_override?: string | null;
  badge_text?: string | null;
  slots: FeaturedPlacementSlot[];
};

export type PadeyaPicksQuery = {
  context?: PlacementContextType | string;
  location_kind?: string;
  location_slug?: string;
  category?: string;
};

export type FeaturedPlacementSetUpsert = {
  context_type: PlacementContextType | string;
  location_id?: string | null;
  category_id?: string | null;
  slot_1: { event_id: string | null };
  slot_2: { event_id: string | null };
  title_override?: string | null;
  subtitle_override?: string | null;
  badge_text?: string | null;
  starts_at?: string | null;
  ends_at?: string | null;
  status?: PlacementStatus | string | null;
};

export function needsLocation(ctx: PlacementContextType | string): boolean {
  return (
    ctx === "country_page" ||
    ctx === "state_page" ||
    ctx === "city_page" ||
    ctx === "area_page" ||
    ctx === "city_category_page" ||
    ctx === "country" ||
    ctx === "state" ||
    ctx === "city" ||
    ctx === "area" ||
    ctx === "city_category"
  );
}

export function needsCategory(ctx: PlacementContextType | string): boolean {
  return (
    ctx === "category_page" ||
    ctx === "city_category_page" ||
    ctx === "category" ||
    ctx === "city_category"
  );
}

export function locationKindForContext(
  ctx: PlacementContextType | string,
): string | null {
  if (ctx === "country_page" || ctx === "country") return "country";
  if (ctx === "state_page" || ctx === "state") return "state";
  if (
    ctx === "city_page" ||
    ctx === "city_category_page" ||
    ctx === "city" ||
    ctx === "city_category"
  ) {
    return "city";
  }
  if (ctx === "area_page" || ctx === "area") return "area";
  return null;
}

export function buildPadeyaPicksTitle(opts: {
  context: PlacementContextType | string;
  locationName?: string | null;
  categoryName?: string | null;
  titleOverride?: string | null;
}): string {
  if (opts.titleOverride?.trim()) return opts.titleOverride.trim();
  const ctx = opts.context;
  if (
    ctx === "homepage" ||
    ctx === "events_page" ||
    ctx === "global_homepage" ||
    ctx === "events"
  ) {
    return "Global Pàdéyá Picks";
  }
  if (
    ctx === "country_page" ||
    ctx === "state_page" ||
    ctx === "city_page" ||
    ctx === "area_page" ||
    ctx === "country" ||
    ctx === "state" ||
    ctx === "city" ||
    ctx === "area"
  ) {
    return `${(opts.locationName || "Location").trim()} Pàdéyá Picks`;
  }
  if (ctx === "category_page" || ctx === "category") {
    return `${(opts.categoryName || "Category").trim()} Pàdéyá Picks`;
  }
  if (ctx === "city_category_page" || ctx === "city_category") {
    const place = (opts.locationName || "City").trim();
    const cat = (opts.categoryName || "Category").trim();
    return `${place} ${cat} Pàdéyá Picks`;
  }
  return "Pàdéyá Picks";
}

export function toDatetimeLocalValue(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function fromDatetimeLocalValue(value: string): string | null {
  if (!value.trim()) return null;
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return null;
  return d.toISOString();
}

export async function fetchFeaturedPlacementContexts(opts?: {
  include_archived?: boolean;
}): Promise<FeaturedPlacementContext[]> {
  const params = new URLSearchParams();
  if (opts?.include_archived) params.set("include_archived", "true");
  const qs = params.toString();
  return apiRequest<FeaturedPlacementContext[]>(
    `/admin/featured-placements/contexts${qs ? `?${qs}` : ""}`,
  );
}

export async function fetchFeaturedPlacementSet(
  setId: string,
): Promise<FeaturedPlacementContext> {
  return apiRequest<FeaturedPlacementContext>(
    `/admin/featured-placements/sets/${setId}`,
  );
}

export async function upsertFeaturedPlacementSet(
  payload: FeaturedPlacementSetUpsert,
): Promise<FeaturedPlacementContext> {
  return apiRequest<FeaturedPlacementContext>(
    "/admin/featured-placements/sets",
    { method: "PUT", body: payload },
  );
}

export async function updateFeaturedPlacementSetStatus(
  setId: string,
  status: "active" | "draft" | "archived",
): Promise<FeaturedPlacementContext> {
  return apiRequest<FeaturedPlacementContext>(
    `/admin/featured-placements/sets/${setId}/status`,
    { method: "POST", body: { status } },
  );
}

export async function fetchFeaturedPlacements(opts?: {
  context_type?: PlacementContextType | string;
  location_id?: string | null;
  category_id?: string | null;
}): Promise<FeaturedPlacementSlot[]> {
  const params = new URLSearchParams();
  params.set("context_type", opts?.context_type || "events_page");
  if (opts?.location_id) params.set("location_id", opts.location_id);
  if (opts?.category_id) params.set("category_id", opts.category_id);
  return apiRequest<FeaturedPlacementSlot[]>(
    `/admin/featured-placements?${params.toString()}`,
  );
}

export async function assignFeaturedPlacement(opts: {
  slotIndex: number;
  context_type: PlacementContextType | string;
  location_id?: string | null;
  category_id?: string | null;
  eventId: string | null;
  title_override?: string | null;
  subtitle_override?: string | null;
  badge_text?: string | null;
  starts_at?: string | null;
  ends_at?: string | null;
  status?: string | null;
}): Promise<FeaturedPlacementSlot> {
  return apiRequest<FeaturedPlacementSlot>(
    `/admin/featured-placements/${opts.slotIndex}`,
    {
      method: "PUT",
      body: {
        context_type: opts.context_type,
        location_id: opts.location_id ?? null,
        category_id: opts.category_id ?? null,
        event_id: opts.eventId,
        title_override: opts.title_override ?? null,
        subtitle_override: opts.subtitle_override ?? null,
        badge_text: opts.badge_text ?? null,
        starts_at: opts.starts_at ?? null,
        ends_at: opts.ends_at ?? null,
        status: opts.status ?? null,
      },
    },
  );
}

export async function setListingPadeyaPick(opts: {
  eventId: string;
  context_type?: PlacementContextType | string;
  slot_number?: 1 | 2;
}): Promise<FeaturedPlacementSlot> {
  return apiRequest<FeaturedPlacementSlot>(
    "/admin/featured-placements/listing-picks",
    {
      method: "POST",
      body: {
        event_id: opts.eventId,
        context_type: opts.context_type ?? "homepage",
        slot_number: opts.slot_number ?? null,
      },
    },
  );
}

export async function clearListingPadeyaPick(opts: {
  eventId: string;
  context_type?: PlacementContextType | string;
}): Promise<FeaturedPlacementSlot[]> {
  return apiRequest<FeaturedPlacementSlot[]>(
    "/admin/featured-placements/listing-picks/clear",
    {
      method: "POST",
      body: {
        event_id: opts.eventId,
        context_type: opts.context_type ?? "homepage",
      },
    },
  );
}

export async function swapListingPadeyaPicks(opts?: {
  context_type?: PlacementContextType | string;
}): Promise<FeaturedPlacementSlot[]> {
  return apiRequest<FeaturedPlacementSlot[]>(
    "/admin/featured-placements/listing-picks/swap",
    {
      method: "POST",
      body: {
        context_type: opts?.context_type ?? "homepage",
      },
    },
  );
}

export async function fetchPadeyaPicks(
  query: PadeyaPicksQuery = {},
): Promise<EventItem[]> {
  const params = new URLSearchParams();
  if (query.context) params.set("context", query.context);
  if (query.location_kind) params.set("location_kind", query.location_kind);
  if (query.location_slug) params.set("location_slug", query.location_slug);
  if (query.category) params.set("category", query.category);
  const qs = params.toString();
  return apiRequest<EventItem[]>(
    `/events/padeya-picks${qs ? `?${qs}` : ""}`,
    { auth: false },
  );
}
