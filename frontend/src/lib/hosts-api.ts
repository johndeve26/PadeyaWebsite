import { apiRequest } from "@/lib/api";
import type { Host } from "@/lib/types/events";
import type {
  HostDiscovery,
  HostRecommendationsResponse,
} from "@/lib/types/hosts-discovery";
import type {
  HostDeskEvent,
  HostWorkspace,
} from "@/lib/types/host-workspace";

export async function fetchDiscoverHosts(): Promise<HostDiscovery[]> {
  return apiRequest<HostDiscovery[]>("/legacy/discover/hosts", { auth: false });
}

export async function fetchHostRecommendations(opts?: {
  limit?: number;
  page?: number;
}): Promise<HostRecommendationsResponse> {
  const params = new URLSearchParams();
  if (opts?.limit) params.set("limit", String(opts.limit));
  if (opts?.page) params.set("page", String(opts.page));
  const q = params.toString();
  return apiRequest<HostRecommendationsResponse>(
    `/hosts/recommendations${q ? `?${q}` : ""}`,
  );
}

export async function dismissHostRecommendation(hostId: string): Promise<void> {
  await apiRequest(`/hosts/recommendations/${hostId}/dismiss`, {
    method: "POST",
    body: {},
  });
}

export async function moreLikeHostRecommendation(hostId: string): Promise<void> {
  await apiRequest(`/hosts/recommendations/${hostId}/more-like-this`, {
    method: "POST",
  });
}

export type HostRecommendationImpressionInput = {
  host_id: string;
  surface: string;
  position?: number;
  recommendation_score?: number;
  reason_codes?: string[];
};

export async function recordHostRecommendationImpressions(
  items: HostRecommendationImpressionInput[],
): Promise<void> {
  if (items.length === 0) return;
  await apiRequest("/hosts/recommendations/impressions", {
    method: "POST",
    body: { items },
  });
}

export async function notInterestedHostRecommendation(hostId: string): Promise<void> {
  await apiRequest(`/hosts/recommendations/${hostId}/not-interested`, {
    method: "POST",
  });
}

export async function recordHostRecommendationClick(hostId: string): Promise<void> {
  await apiRequest(`/hosts/recommendations/${hostId}/click`, {
    method: "POST",
  });
}

export async function recordHostRecommendationFollow(hostId: string): Promise<void> {
  await apiRequest(`/hosts/recommendations/${hostId}/follow`, {
    method: "POST",
  });
}

export async function hideHostRecommendationCategory(
  categorySlug: string,
): Promise<void> {
  await apiRequest("/hosts/recommendations/hide-category", {
    method: "POST",
    body: { category_slug: categorySlug },
  });
}

export async function fetchMyHost(): Promise<Host | null> {
  try {
    return await apiRequest<Host>("/hosts/me");
  } catch (error) {
    if (error && typeof error === "object" && "status" in error && error.status === 404) {
      return null;
    }
    throw error;
  }
}

export async function fetchHostWorkspaces(): Promise<HostWorkspace[]> {
  return apiRequest<HostWorkspace[]>("/me/team-workspaces");
}

export async function setActiveHostWorkspace(
  hostId: string,
): Promise<{ host_id: string }> {
  return apiRequest<{ host_id: string }>("/me/active-workspace", {
    method: "POST",
    body: { host_id: hostId },
  });
}

export async function fetchWorkspaceDeskEvents(
  hostId: string,
): Promise<HostDeskEvent[]> {
  return apiRequest<HostDeskEvent[]>(`/hosts/workspaces/${hostId}/desk-events`);
}

export async function onboardHost(input: {
  display_name: string;
  bio?: string;
  website?: string;
  city?: string;
  state?: string;
  country?: string;
}): Promise<Host> {
  return apiRequest<Host>("/hosts/onboard", { method: "POST", body: input });
}

export async function updateMyHost(input: Record<string, unknown>): Promise<Host> {
  return apiRequest<Host>("/hosts/me", { method: "PATCH", body: input });
}
