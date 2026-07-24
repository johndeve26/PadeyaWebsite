import { apiRequest, apiUpload } from "@/lib/api";
import type {
  EventRecommendationImpressionInput,
  EventRecommendationsResponse,
} from "@/lib/types/event-recommendations";
import type {
  EventCategory,
  EventItem,
  TicketType,
} from "@/lib/types/events";

export type MediaUploadResult = {
  url: string;
  key: string;
  media_type: string;
  event_id?: string | null;
};

export async function fetchCategories(): Promise<EventCategory[]> {
  return apiRequest<EventCategory[]>("/events/categories", { auth: false });
}

export async function fetchPublicEvents(filters?: {
  q?: string;
  category?: string;
  city?: string;
  location_kind?: string;
  location_slug?: string;
  weekend?: boolean;
  paid?: string;
  sort?: string;
}): Promise<EventItem[]> {
  const params = new URLSearchParams();
  if (filters?.q) params.set("q", filters.q);
  if (filters?.category) params.set("category", filters.category);
  if (filters?.city) params.set("city", filters.city);
  if (filters?.location_kind) params.set("location_kind", filters.location_kind);
  if (filters?.location_slug) params.set("location_slug", filters.location_slug);
  if (filters?.weekend) params.set("weekend", "true");
  if (filters?.paid) params.set("paid", filters.paid);
  if (filters?.sort) params.set("sort", filters.sort);
  const qs = params.toString();
  return apiRequest<EventItem[]>(`/events${qs ? `?${qs}` : ""}`, { auth: false });
}

export async function fetchEventRecommendations(opts?: {
  limit?: number;
  cursor?: string;
  city?: string;
  area?: string;
  category?: string;
  mode?: string;
  excludeEventId?: string;
  contextEventId?: string;
  hostId?: string;
}): Promise<EventRecommendationsResponse> {
  const params = new URLSearchParams();
  if (opts?.limit) params.set("limit", String(opts.limit));
  if (opts?.cursor) params.set("cursor", opts.cursor);
  if (opts?.city) params.set("city", opts.city);
  if (opts?.area) params.set("area", opts.area);
  if (opts?.category) params.set("category", opts.category);
  if (opts?.mode) params.set("mode", opts.mode);
  if (opts?.excludeEventId) params.set("exclude_event_id", opts.excludeEventId);
  if (opts?.contextEventId) params.set("context_event_id", opts.contextEventId);
  if (opts?.hostId) params.set("host_id", opts.hostId);
  const q = params.toString();
  return apiRequest<EventRecommendationsResponse>(
    `/events/recommendations${q ? `?${q}` : ""}`,
  );
}

export async function eventRecommendationFeedback(
  eventId: string,
  action: string,
  categorySlug?: string,
): Promise<void> {
  await apiRequest(`/events/recommendations/${eventId}/feedback`, {
    method: "POST",
    body: { action, category_slug: categorySlug ?? null },
  });
}

export async function recordEventRecommendationImpressions(
  items: EventRecommendationImpressionInput[],
): Promise<void> {
  if (items.length === 0) return;
  await apiRequest("/events/recommendations/impressions", {
    method: "POST",
    body: { items },
  });
}

export type NearbyEventsResponse = {
  items: EventItem[];
  total: number;
  page: number;
  limit: number;
  radius_km: number;
  lat: number;
  lng: number;
  location_label?: string | null;
};

export type CalendarEventCompact = {
  id: string;
  slug: string;
  title: string;
  start_datetime: string;
  end_datetime?: string | null;
  banner_url?: string | null;
  city?: string | null;
  public_location_label?: string | null;
  featured: boolean;
  host_display_name?: string | null;
  host_id?: string | null;
  category_name?: string | null;
  category_slug?: string | null;
  min_price?: number | null;
  is_free: boolean;
};

export type CalendarDay = {
  date: string;
  event_count: number;
  events: CalendarEventCompact[];
};

export type CalendarMonthResponse = {
  month: string;
  days: CalendarDay[];
  featured_event: CalendarEventCompact | null;
  total_events: number;
};

export async function fetchNearbyEvents(params: {
  lat: number;
  lng: number;
  radius_km?: number;
  category?: string;
  date?: string;
  limit?: number;
  page?: number;
  location_label?: string;
}): Promise<NearbyEventsResponse> {
  const qs = new URLSearchParams();
  qs.set("lat", String(params.lat));
  qs.set("lng", String(params.lng));
  qs.set("radius_km", String(params.radius_km ?? 25));
  if (params.category) qs.set("category", params.category);
  if (params.date) qs.set("date", params.date);
  if (params.limit) qs.set("limit", String(params.limit));
  if (params.page) qs.set("page", String(params.page));
  if (params.location_label) qs.set("location_label", params.location_label);
  return apiRequest<NearbyEventsResponse>(`/events/nearby?${qs}`, {
    auth: false,
  });
}

export type MapEventCompact = {
  id: string;
  slug: string;
  title: string;
  banner_url?: string | null;
  start_datetime: string;
  end_datetime?: string | null;
  price_label: string;
  min_price?: number | null;
  is_free?: boolean;
  category_name?: string | null;
  category_slug?: string | null;
  host_display_name?: string | null;
  public_location_label?: string | null;
  city?: string | null;
  area?: string | null;
  latitude: string | null;
  longitude: string | null;
  location_visibility?: string;
  location_map_mode?: string;
  location_privacy_message?: string | null;
  distance_km?: number | null;
  distance_label?: string | null;
  distance_is_approximate?: boolean;
};

export type MapEventsResponse = {
  items: MapEventCompact[];
  total: number;
  north: number;
  south: number;
  east: number;
  west: number;
  lat?: number | null;
  lng?: number | null;
  radius_km?: number | null;
};

export async function fetchMapEvents(params: {
  north: number;
  south: number;
  east: number;
  west: number;
  lat?: number;
  lng?: number;
  radius_km?: number;
  city?: string;
  area?: string;
  category?: string;
  date?: string;
  price?: "any" | "free" | "paid";
  host?: string;
  limit?: number;
}): Promise<MapEventsResponse> {
  const qs = new URLSearchParams();
  qs.set("north", String(params.north));
  qs.set("south", String(params.south));
  qs.set("east", String(params.east));
  qs.set("west", String(params.west));
  if (params.lat != null) qs.set("lat", String(params.lat));
  if (params.lng != null) qs.set("lng", String(params.lng));
  if (params.radius_km != null) qs.set("radius_km", String(params.radius_km));
  if (params.city) qs.set("city", params.city);
  if (params.area) qs.set("area", params.area);
  if (params.category) qs.set("category", params.category);
  if (params.date) qs.set("date", params.date);
  if (params.price && params.price !== "any") qs.set("price", params.price);
  if (params.host) qs.set("host", params.host);
  if (params.limit) qs.set("limit", String(params.limit));
  return apiRequest<MapEventsResponse>(`/events/map?${qs}`, { auth: false });
}

export async function fetchEventsCalendar(params: {
  month: string;
  category?: string;
  city?: string;
  location_kind?: string;
  location_slug?: string;
  paid?: string;
  host?: string;
  include_featured?: boolean;
}): Promise<CalendarMonthResponse> {
  const qs = new URLSearchParams();
  qs.set("month", params.month);
  if (params.category) qs.set("category", params.category);
  if (params.city) qs.set("city", params.city);
  if (params.location_kind) qs.set("location_kind", params.location_kind);
  if (params.location_slug) qs.set("location_slug", params.location_slug);
  if (params.paid) qs.set("paid", params.paid);
  if (params.host) qs.set("host", params.host);
  if (params.include_featured === false) qs.set("include_featured", "false");
  return apiRequest<CalendarMonthResponse>(`/events/calendar?${qs}`, {
    auth: false,
  });
}

export async function regeocodeAdminEvent(eventId: string): Promise<EventItem> {
  return apiRequest<EventItem>(`/events/admin/${eventId}/regeocode`, {
    method: "POST",
  });
}

export {
  fetchPadeyaPicks,
  buildPadeyaPicksTitle,
  type PadeyaPicksQuery,
} from "@/lib/placements-api";

export async function fetchPublicEvent(slug: string): Promise<EventItem> {
  return apiRequest<EventItem>(`/events/${slug}`, { auth: false });
}

export async function fetchMyEvents(): Promise<EventItem[]> {
  return apiRequest<EventItem[]>("/events/mine");
}

export async function fetchEventById(id: string): Promise<EventItem> {
  return apiRequest<EventItem>(`/events/by-id/${id}`);
}

export async function createEvent(body: Record<string, unknown>): Promise<EventItem> {
  return apiRequest<EventItem>("/events", { method: "POST", body });
}

export async function updateEvent(
  id: string,
  body: Record<string, unknown>,
): Promise<EventItem> {
  return apiRequest<EventItem>(`/events/by-id/${id}`, { method: "PATCH", body });
}

export async function submitEvent(id: string): Promise<EventItem> {
  return apiRequest<EventItem>(`/events/by-id/${id}/submit`, { method: "POST" });
}

export async function completeEvent(id: string): Promise<EventItem> {
  return apiRequest<EventItem>(`/events/by-id/${id}/complete`, { method: "POST" });
}

export async function pauseEvent(id: string): Promise<EventItem> {
  return apiRequest<EventItem>(`/events/by-id/${id}/pause`, { method: "POST" });
}

export async function resumeEvent(id: string): Promise<EventItem> {
  return apiRequest<EventItem>(`/events/by-id/${id}/resume`, { method: "POST" });
}

export async function postponeEvent(
  id: string,
  body: { start_datetime: string; end_datetime: string },
): Promise<EventItem> {
  return apiRequest<EventItem>(`/events/by-id/${id}/postpone`, {
    method: "POST",
    body,
  });
}

export async function cancelEvent(id: string): Promise<EventItem> {
  return apiRequest<EventItem>(`/events/by-id/${id}/cancel`, { method: "POST" });
}

export async function discardEvent(id: string): Promise<void> {
  await apiRequest<{ message: string }>(`/events/by-id/${id}`, { method: "DELETE" });
}

export async function archiveEvent(id: string): Promise<EventItem> {
  return apiRequest<EventItem>(`/events/by-id/${id}/archive`, { method: "POST" });
}

export async function restoreArchivedEvent(id: string): Promise<EventItem> {
  return apiRequest<EventItem>(`/events/by-id/${id}/restore`, { method: "POST" });
}

export async function deleteEventMedia(
  eventId: string,
  mediaId: string,
): Promise<EventItem> {
  return apiRequest<EventItem>(`/events/by-id/${eventId}/media/${mediaId}`, {
    method: "DELETE",
  });
}

export async function approveEvent(id: string): Promise<EventItem> {
  return apiRequest<EventItem>(`/events/by-id/${id}/approve`, { method: "POST" });
}

export async function rejectEvent(id: string, reason: string): Promise<EventItem> {
  return apiRequest<EventItem>(`/events/by-id/${id}/reject`, {
    method: "POST",
    body: { reason },
  });
}

export async function flagEvent(id: string, reason: string): Promise<EventItem> {
  return apiRequest<EventItem>(`/events/by-id/${id}/flag`, {
    method: "POST",
    body: { reason },
  });
}

export async function clearEventFlag(
  id: string,
  reason?: string,
): Promise<EventItem> {
  return apiRequest<EventItem>(`/events/by-id/${id}/clear-flag`, {
    method: "POST",
    body: reason?.trim() ? { reason: reason.trim() } : {},
  });
}

export async function fetchPendingEvents(): Promise<EventItem[]> {
  return apiRequest<EventItem[]>("/events/admin/pending");
}

export async function fetchAdminEvents(): Promise<EventItem[]> {
  return apiRequest<EventItem[]>("/events/admin/all");
}

export async function addEventMedia(
  id: string,
  body: Record<string, unknown>,
): Promise<EventItem> {
  return apiRequest<EventItem>(`/events/by-id/${id}/media`, {
    method: "POST",
    body,
  });
}

export async function uploadHostMediaFile(
  file: File,
  mediaType: string = "gallery",
): Promise<MediaUploadResult> {
  const form = new FormData();
  form.append("file", file);
  form.append("media_type", mediaType);
  return apiUpload<MediaUploadResult>("/events/media/upload", form);
}

export async function uploadEventMediaFile(
  eventId: string,
  file: File,
  options: {
    mediaType?: string;
    setAsBanner?: boolean;
    altText?: string;
  } = {},
): Promise<EventItem> {
  const form = new FormData();
  form.append("file", file);
  form.append("media_type", options.mediaType ?? "gallery");
  if (options.setAsBanner) form.append("set_as_banner", "true");
  if (options.altText) form.append("alt_text", options.altText);
  return apiUpload<EventItem>(`/events/by-id/${eventId}/media/upload`, form);
}

export async function fetchTicketTypes(eventId: string): Promise<TicketType[]> {
  return apiRequest<TicketType[]>(`/events/by-id/${eventId}/ticket-types`);
}

export async function createTicketType(
  eventId: string,
  body: Record<string, unknown>,
): Promise<TicketType> {
  return apiRequest<TicketType>(`/events/by-id/${eventId}/ticket-types`, {
    method: "POST",
    body,
  });
}

export async function updateTicketType(
  eventId: string,
  ticketTypeId: string,
  body: Record<string, unknown>,
): Promise<TicketType> {
  return apiRequest<TicketType>(
    `/events/by-id/${eventId}/ticket-types/${ticketTypeId}`,
    { method: "PATCH", body },
  );
}

export async function deactivateTicketType(
  eventId: string,
  ticketTypeId: string,
): Promise<TicketType> {
  return apiRequest<TicketType>(
    `/events/by-id/${eventId}/ticket-types/${ticketTypeId}/deactivate`,
    { method: "POST" },
  );
}

export async function deleteTicketType(
  eventId: string,
  ticketTypeId: string,
): Promise<void> {
  await apiRequest<{ message: string }>(
    `/events/by-id/${eventId}/ticket-types/${ticketTypeId}`,
    { method: "DELETE" },
  );
}
