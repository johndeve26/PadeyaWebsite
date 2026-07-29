import { apiRequest } from "@/lib/api";
import { getAccessToken } from "@/lib/auth/storage";
import {
  assertClientActionAllowed,
  getOrCreateAnonymousId,
  getOrCreateSessionId,
  isLikelyBot,
  normalizeUtmParams,
} from "@/lib/analytics-client";
import {
  dimensionsToApiBody,
  normalizeTrackedAction,
  type AnalyticsDimensions,
  type TrackedActionName,
} from "@/lib/analytics-taxonomy";
import type {
  AdminChannelPerformance,
  AdminEventAnalyticsBundle,
  AdminEventCompare,
  AdminEventLeaderboard,
  AdminEventsSummary,
  AdminHostsSummary,
  AdminPlatformSummary,
  AdminRevenueSummary,
  AdminSupportSummary,
  AdminBlogAnalyticsSummary,
  AdminBlogPostAnalytics,
  EventAnalyticsAmbassadors,
  EventAnalyticsAudience,
  EventAnalyticsFunnel,
  EventAnalyticsOverview,
  EventAnalyticsPromos,
  EventAnalyticsQuery,
  EventAnalyticsSources,
  EventAnalyticsSummary,
  EventAnalyticsTickets,
  EventAnalyticsTimeseries,
  HostAnalyticsSummary,
} from "@/lib/types/analytics";
import { getApiBaseUrl, getApiPrefix } from "@/lib/api-base";

const API_URL = getApiBaseUrl();
const API_PREFIX = getApiPrefix();

function clientIdentity(dimensions?: AnalyticsDimensions): AnalyticsDimensions {
  const utm = normalizeUtmParams({
    source: dimensions?.source,
    medium: dimensions?.medium,
    campaign: dimensions?.campaign,
    term: dimensions?.term,
    content: dimensions?.content,
    utmSource: dimensions?.utmSource,
    utmMedium: dimensions?.utmMedium,
    utmCampaign: dimensions?.utmCampaign,
    utmTerm: dimensions?.utmTerm,
    utmContent: dimensions?.utmContent,
  });
  return {
    ...dimensions,
    ...utm,
    anonymousId: dimensions?.anonymousId ?? getOrCreateAnonymousId(),
    sessionId: dimensions?.sessionId ?? getOrCreateSessionId(),
    isBot: dimensions?.isBot ?? isLikelyBot(),
    userAgent:
      dimensions?.userAgent ??
      (typeof navigator !== "undefined" ? navigator.userAgent : undefined),
    path:
      dimensions?.path ??
      dimensions?.currentPath ??
      (typeof window !== "undefined" ? window.location.pathname : undefined),
    currentPath:
      dimensions?.currentPath ??
      dimensions?.path ??
      (typeof window !== "undefined" ? window.location.pathname : undefined),
    referrer:
      dimensions?.referrer ??
      (typeof document !== "undefined" ? document.referrer || undefined : undefined),
  };
}

export async function fetchHostAnalytics(): Promise<HostAnalyticsSummary> {
  return apiRequest<HostAnalyticsSummary>("/analytics/host/summary");
}

export async function fetchHostEventAnalytics(
  eventId: string,
): Promise<EventAnalyticsSummary> {
  return apiRequest<EventAnalyticsSummary>(`/analytics/host/events/${eventId}`);
}

function toQuery(params?: EventAnalyticsQuery): string {
  if (!params) return "";
  const qs = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    qs.set(key, String(value));
  }
  const s = qs.toString();
  return s ? `?${s}` : "";
}

export async function fetchHostEventAnalyticsOverview(
  eventId: string,
  params?: EventAnalyticsQuery,
): Promise<EventAnalyticsOverview> {
  return apiRequest<EventAnalyticsOverview>(
    `/host/events/${eventId}/analytics/overview${toQuery(params)}`,
  );
}

export async function fetchHostEventAnalyticsFunnel(
  eventId: string,
  params?: EventAnalyticsQuery,
): Promise<EventAnalyticsFunnel> {
  return apiRequest<EventAnalyticsFunnel>(
    `/host/events/${eventId}/analytics/funnel${toQuery(params)}`,
  );
}

export async function fetchHostEventAnalyticsTimeseries(
  eventId: string,
  params?: EventAnalyticsQuery,
): Promise<EventAnalyticsTimeseries> {
  return apiRequest<EventAnalyticsTimeseries>(
    `/host/events/${eventId}/analytics/timeseries${toQuery(params)}`,
  );
}

export async function fetchHostEventAnalyticsSources(
  eventId: string,
  params?: EventAnalyticsQuery,
): Promise<EventAnalyticsSources> {
  return apiRequest<EventAnalyticsSources>(
    `/host/events/${eventId}/analytics/sources${toQuery(params)}`,
  );
}

export async function fetchHostEventAnalyticsTickets(
  eventId: string,
  params?: EventAnalyticsQuery,
): Promise<EventAnalyticsTickets> {
  return apiRequest<EventAnalyticsTickets>(
    `/host/events/${eventId}/analytics/tickets${toQuery(params)}`,
  );
}

export async function fetchHostEventAnalyticsAudience(
  eventId: string,
  params?: EventAnalyticsQuery,
): Promise<EventAnalyticsAudience> {
  return apiRequest<EventAnalyticsAudience>(
    `/host/events/${eventId}/analytics/audience${toQuery(params)}`,
  );
}

export async function fetchHostEventAnalyticsPromos(
  eventId: string,
  params?: EventAnalyticsQuery,
): Promise<EventAnalyticsPromos> {
  return apiRequest<EventAnalyticsPromos>(
    `/host/events/${eventId}/analytics/promos${toQuery(params)}`,
  );
}

export async function fetchHostEventAnalyticsAmbassadors(
  eventId: string,
  params?: EventAnalyticsQuery,
): Promise<EventAnalyticsAmbassadors> {
  return apiRequest<EventAnalyticsAmbassadors>(
    `/host/events/${eventId}/analytics/ambassadors${toQuery(params)}`,
  );
}

export async function exportHostEventAnalyticsCsv(
  eventId: string,
  params?: EventAnalyticsQuery,
): Promise<void> {
  await downloadCsv(
    `/host/events/${eventId}/analytics/export${toQuery(params)}`,
    `event-${eventId}-analytics.csv`,
  );
}

export async function fetchAdminEventAnalyticsBundle(
  eventId: string,
  params?: EventAnalyticsQuery,
): Promise<AdminEventAnalyticsBundle> {
  return apiRequest<AdminEventAnalyticsBundle>(
    `/admin/events/${eventId}/analytics${toQuery(params)}`,
  );
}

export async function fetchAdminEventAnalyticsTimeseries(
  eventId: string,
  params?: EventAnalyticsQuery,
): Promise<EventAnalyticsTimeseries> {
  return apiRequest<EventAnalyticsTimeseries>(
    `/admin/events/${eventId}/analytics/timeseries${toQuery(params)}`,
  );
}

export async function fetchAdminEventAnalyticsAudience(
  eventId: string,
  params?: EventAnalyticsQuery,
): Promise<EventAnalyticsAudience> {
  return apiRequest<EventAnalyticsAudience>(
    `/admin/events/${eventId}/analytics/audience${toQuery(params)}`,
  );
}

export async function fetchAdminEventAnalyticsPromos(
  eventId: string,
  params?: EventAnalyticsQuery,
): Promise<EventAnalyticsPromos> {
  return apiRequest<EventAnalyticsPromos>(
    `/admin/events/${eventId}/analytics/promos${toQuery(params)}`,
  );
}

export async function fetchAdminEventAnalyticsAmbassadors(
  eventId: string,
  params?: EventAnalyticsQuery,
): Promise<EventAnalyticsAmbassadors> {
  return apiRequest<EventAnalyticsAmbassadors>(
    `/admin/events/${eventId}/analytics/ambassadors${toQuery(params)}`,
  );
}

export async function exportAdminEventAnalyticsCsv(
  eventId: string,
  params?: EventAnalyticsQuery,
): Promise<void> {
  await downloadCsv(
    `/admin/events/${eventId}/analytics/export${toQuery(params)}`,
    `admin-event-${eventId}-analytics.csv`,
  );
}

export async function fetchAdminEventLeaderboard(params?: {
  sort_by?: string;
  limit?: number;
} & EventAnalyticsQuery): Promise<AdminEventLeaderboard> {
  const { sort_by = "revenue", limit = 50, ...filters } = params ?? {};
  const qs = toQuery({
    ...filters,
    // sort/limit passed separately
  } as EventAnalyticsQuery);
  const extra = new URLSearchParams();
  extra.set("sort_by", sort_by);
  extra.set("limit", String(limit));
  const joined = qs
    ? `${qs}&${extra.toString()}`
    : `?${extra.toString()}`;
  return apiRequest<AdminEventLeaderboard>(
    `/admin/analytics/events/leaderboard${joined}`,
  );
}

export async function fetchAdminEventCompare(
  eventIds: string[],
  params?: EventAnalyticsQuery,
): Promise<AdminEventCompare> {
  const qs = new URLSearchParams();
  for (const id of eventIds) qs.append("event_ids", id);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value === undefined || value === null || value === "") continue;
      qs.set(key, String(value));
    }
  }
  return apiRequest<AdminEventCompare>(
    `/admin/analytics/events/compare?${qs.toString()}`,
  );
}

export async function fetchAdminChannelPerformance(
  params?: EventAnalyticsQuery,
): Promise<AdminChannelPerformance> {
  return apiRequest<AdminChannelPerformance>(
    `/admin/analytics/events/channels${toQuery(params)}`,
  );
}

export async function exportAdminEventsLeaderboardCsv(
  params?: { sort_by?: string; limit?: number } & EventAnalyticsQuery,
): Promise<void> {
  const { sort_by = "revenue", limit = 200, ...filters } = params ?? {};
  const qs = new URLSearchParams();
  qs.set("sort_by", sort_by);
  qs.set("limit", String(limit));
  for (const [key, value] of Object.entries(filters)) {
    if (value === undefined || value === null || value === "") continue;
    qs.set(key, String(value));
  }
  await downloadCsv(
    `/admin/analytics/events/export?${qs.toString()}`,
    "admin-events-analytics.csv",
  );
}

export async function fetchAdminAnalytics(): Promise<AdminPlatformSummary> {
  return apiRequest<AdminPlatformSummary>("/analytics/admin/summary");
}

export async function fetchAdminRevenue(): Promise<AdminRevenueSummary> {
  return apiRequest<AdminRevenueSummary>("/analytics/admin/revenue");
}

export async function fetchAdminEventsAnalytics(): Promise<AdminEventsSummary> {
  return apiRequest<AdminEventsSummary>("/analytics/admin/events");
}

export async function fetchAdminHostsAnalytics(): Promise<AdminHostsSummary> {
  return apiRequest<AdminHostsSummary>("/analytics/admin/hosts");
}

export async function fetchAdminSupportAnalytics(): Promise<AdminSupportSummary> {
  return apiRequest<AdminSupportSummary>("/analytics/admin/support");
}

export async function fetchAdminBlogAnalytics(opts?: {
  rangeStart?: string;
  rangeEnd?: string;
  includeInternal?: boolean;
}): Promise<AdminBlogAnalyticsSummary> {
  const params = new URLSearchParams();
  if (opts?.rangeStart) params.set("range_start", opts.rangeStart);
  if (opts?.rangeEnd) params.set("range_end", opts.rangeEnd);
  if (opts?.includeInternal) params.set("include_internal", "true");
  const q = params.toString();
  return apiRequest<AdminBlogAnalyticsSummary>(
    `/analytics/admin/blog${q ? `?${q}` : ""}`,
  );
}

export async function fetchAdminBlogPostAnalytics(
  postId: string,
  opts?: {
    rangeStart?: string;
    rangeEnd?: string;
    includeInternal?: boolean;
  },
): Promise<AdminBlogPostAnalytics> {
  const params = new URLSearchParams();
  if (opts?.rangeStart) params.set("range_start", opts.rangeStart);
  if (opts?.rangeEnd) params.set("range_end", opts.rangeEnd);
  if (opts?.includeInternal) params.set("include_internal", "true");
  const q = params.toString();
  return apiRequest<AdminBlogPostAnalytics>(
    `/analytics/admin/blog/posts/${encodeURIComponent(postId)}${q ? `?${q}` : ""}`,
  );
}

/** Generic taxonomy write — prefer this for new instrumentation. */
export async function trackAction(payload: {
  trackedAction: TrackedActionName | string;
  targetEventId?: string;
  eventListingId?: string;
  hostId?: string;
  sessionId?: string;
  properties?: Record<string, unknown>;
  requireKnownAction?: boolean;
  dimensions?: AnalyticsDimensions;
}): Promise<void> {
  const action = normalizeTrackedAction(payload.trackedAction);
  assertClientActionAllowed(action);
  const dimensions = clientIdentity({
    ...payload.dimensions,
    sessionId: payload.sessionId ?? payload.dimensions?.sessionId,
    metadata: (payload.dimensions?.metadata ??
      payload.properties) as AnalyticsDimensions["metadata"],
  });
  // Never send revenue / trusted conversion fields from the browser.
  if (dimensions.metadata) {
    const meta = { ...dimensions.metadata } as Record<
      string,
      string | number | boolean | undefined
    >;
    delete meta.conversion_value;
    delete meta.amount;
    delete meta.revenue;
    delete meta.tickets_sold;
    dimensions.metadata = meta;
  }

  await apiRequest("/analytics/track", {
    method: "POST",
    body: {
      event_name: action,
      tracked_action: action,
      analytics_event_name: action,
      target_event_id: payload.targetEventId,
      event_listing_id: payload.eventListingId,
      host_id: payload.hostId,
      session_id: dimensions.sessionId,
      properties: payload.properties,
      metadata: dimensions.metadata ?? payload.properties,
      require_known_action: payload.requireKnownAction ?? true,
      ...dimensionsToApiBody(dimensions),
    },
    auth: false,
  });
}

/** Batch client track — same security as trackAction. */
export async function trackBatch(
  events: Array<{
    trackedAction: TrackedActionName | string;
    targetEventId?: string;
    hostId?: string;
    entityType?: string;
    entityId?: string;
    properties?: Record<string, unknown>;
    dimensions?: AnalyticsDimensions;
  }>,
): Promise<{ accepted_count: number; rejected_count: number }> {
  const dimensions = clientIdentity();
  const body = {
    events: events.map((item) => {
      const action = normalizeTrackedAction(item.trackedAction);
      assertClientActionAllowed(action);
      return {
        event_name: action,
        tracked_action: action,
        target_event_id: item.targetEventId,
        host_id: item.hostId,
        entity_type: item.entityType,
        entity_id: item.entityId,
        metadata: item.properties ?? item.dimensions?.metadata,
        require_known_action: true,
        ...dimensionsToApiBody(clientIdentity(item.dimensions ?? dimensions)),
      };
    }),
  };
  return apiRequest("/analytics/track/batch", {
    method: "POST",
    body,
    auth: false,
  });
}

export async function trackPageView(payload: {
  path: string;
  host_id?: string;
  event_id?: string;
  target_event_id?: string;
  session_id?: string;
  referrer?: string;
  tracked_action?: string;
}): Promise<void> {
  if (payload.tracked_action) {
    assertClientActionAllowed(normalizeTrackedAction(payload.tracked_action));
  }
  const dimensions = clientIdentity({
    sessionId: payload.session_id,
    referrer: payload.referrer,
    path: payload.path,
  });
  await apiRequest("/analytics/track/page-view", {
    method: "POST",
    body: {
      path: payload.path,
      host_id: payload.host_id,
      event_id: payload.event_id,
      target_event_id: payload.target_event_id ?? payload.event_id,
      session_id: dimensions.sessionId,
      anonymous_id: dimensions.anonymousId,
      referrer: dimensions.referrer ?? payload.referrer,
      tracked_action: payload.tracked_action,
      user_agent: dimensions.userAgent,
      is_bot: dimensions.isBot,
      ...dimensionsToApiBody(dimensions),
    },
    auth: false,
  });
}

export async function trackEventImpression(payload: {
  event_id: string;
  target_event_id?: string;
  event_listing_id?: string;
  session_id?: string;
  source?: string;
  tracked_action?: string;
  list_context?: string;
}): Promise<void> {
  const action = payload.tracked_action ?? "event_card_impression";
  assertClientActionAllowed(normalizeTrackedAction(action));
  const dimensions = clientIdentity({
    sessionId: payload.session_id,
    source: payload.source,
    metadata: payload.list_context
      ? { list_context: payload.list_context }
      : undefined,
  });
  await apiRequest("/analytics/track/impression", {
    method: "POST",
    body: {
      event_id: payload.event_id,
      target_event_id: payload.target_event_id ?? payload.event_id,
      event_listing_id: payload.event_listing_id,
      session_id: dimensions.sessionId,
      anonymous_id: dimensions.anonymousId,
      source: payload.source,
      tracked_action: action,
      metadata: dimensions.metadata,
      user_agent: dimensions.userAgent,
      is_bot: dimensions.isBot,
      ...dimensionsToApiBody(dimensions),
    },
    auth: false,
  });
}

export async function trackEventClick(payload: {
  event_id: string;
  target_event_id?: string;
  event_listing_id?: string;
  session_id?: string;
  click_target?: string;
  tracked_action?: string;
}): Promise<void> {
  const action = payload.tracked_action ?? "event_card_click";
  assertClientActionAllowed(normalizeTrackedAction(action));
  const dimensions = clientIdentity({ sessionId: payload.session_id });
  await apiRequest("/analytics/track/click", {
    method: "POST",
    body: {
      event_id: payload.event_id,
      target_event_id: payload.target_event_id ?? payload.event_id,
      event_listing_id: payload.event_listing_id,
      session_id: dimensions.sessionId,
      anonymous_id: dimensions.anonymousId,
      click_target: payload.click_target,
      tracked_action: action,
      user_agent: dimensions.userAgent,
      is_bot: dimensions.isBot,
      ...dimensionsToApiBody(dimensions),
    },
    auth: false,
  });
}

export async function trackConversion(payload: {
  stage?: string;
  tracked_action?: string;
  event_id?: string;
  target_event_id?: string;
  session_id?: string;
  order_id?: string;
}): Promise<void> {
  const action = payload.tracked_action
    ? normalizeTrackedAction(payload.tracked_action)
    : payload.stage;
  if (action) assertClientActionAllowed(action);
  if (payload.stage) assertClientActionAllowed(payload.stage);
  const dimensions = clientIdentity({ sessionId: payload.session_id });
  await apiRequest("/analytics/track/conversion", {
    method: "POST",
    body: {
      stage: payload.stage,
      tracked_action: payload.tracked_action
        ? normalizeTrackedAction(payload.tracked_action)
        : undefined,
      event_id: payload.event_id,
      target_event_id: payload.target_event_id ?? payload.event_id,
      session_id: dimensions.sessionId,
      anonymous_id: dimensions.anonymousId,
      order_id: payload.order_id,
      // amount intentionally omitted — server-trusted only
      user_agent: dimensions.userAgent,
      is_bot: dimensions.isBot,
      ...dimensionsToApiBody(dimensions),
    },
    auth: false,
  });
}

async function downloadCsv(path: string, filename: string): Promise<void> {
  const token = getAccessToken();
  const res = await fetch(`${API_URL}${API_PREFIX}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    throw new Error("Export failed");
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export async function exportHostAnalyticsCsv(): Promise<void> {
  await downloadCsv("/analytics/host/export.csv", "host-analytics.csv");
}

export async function exportAdminAnalyticsCsv(): Promise<void> {
  await downloadCsv("/analytics/admin/export.csv", "platform-analytics.csv");
}

export {
  getOrCreateAnonymousId,
  getOrCreateSessionId,
  generateDedupeKey,
  isLikelyBot,
  normalizeUtmParams,
} from "@/lib/analytics-client";
