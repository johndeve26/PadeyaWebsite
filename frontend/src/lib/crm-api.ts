import { apiRequest } from "@/lib/api";
import type {
  Announcement,
  AnnouncementDispatchResult,
  AudienceMember,
  AudienceSegment,
  AudienceStats,
  FollowingHost,
  SegmentKey,
} from "@/lib/types/crm";

export async function followHost(input: {
  host_id?: string;
  host_slug?: string;
}): Promise<FollowingHost> {
  return apiRequest<FollowingHost>("/crm/follow", {
    method: "POST",
    body: input,
  });
}

export async function unfollowHost(hostId: string): Promise<void> {
  return apiRequest<void>(`/crm/follow/${hostId}`, { method: "DELETE" });
}

export async function fetchMyFollowing(): Promise<FollowingHost[]> {
  return apiRequest<FollowingHost[]>("/crm/me/following");
}

export async function updateMarketingOptIn(
  hostId: string,
  marketing_opt_in: boolean,
): Promise<FollowingHost> {
  return apiRequest<FollowingHost>(`/crm/me/following/${hostId}`, {
    method: "PATCH",
    body: { marketing_opt_in },
  });
}

export async function fetchAudienceStats(): Promise<AudienceStats> {
  return apiRequest<AudienceStats>("/crm/host/audience");
}

export async function fetchHostFollowers(): Promise<AudienceMember[]> {
  return apiRequest<AudienceMember[]>("/crm/host/followers");
}

export async function fetchAudienceMembers(params: {
  segment_key?: string;
  segment_id?: string;
  event_id?: string;
  ticket_type_id?: string;
  check_in_status?: string;
}): Promise<AudienceMember[]> {
  const qs = new URLSearchParams();
  if (params.segment_key) qs.set("segment_key", params.segment_key);
  if (params.segment_id) qs.set("segment_id", params.segment_id);
  if (params.event_id) qs.set("event_id", params.event_id);
  if (params.ticket_type_id) qs.set("ticket_type_id", params.ticket_type_id);
  if (params.check_in_status) qs.set("check_in_status", params.check_in_status);
  const query = qs.toString();
  return apiRequest<AudienceMember[]>(
    `/crm/host/audience/members${query ? `?${query}` : ""}`,
  );
}

export async function fetchSegments(): Promise<AudienceSegment[]> {
  return apiRequest<AudienceSegment[]>("/crm/host/segments");
}

export async function createSegment(input: {
  name: string;
  segment_key: SegmentKey | string;
  description?: string | null;
  filters?: Record<string, unknown> | null;
}): Promise<AudienceSegment> {
  return apiRequest<AudienceSegment>("/crm/host/segments", {
    method: "POST",
    body: input,
  });
}

export async function deleteSegment(segmentId: string): Promise<void> {
  await apiRequest<{ message: string }>(`/crm/host/segments/${segmentId}`, {
    method: "DELETE",
  });
}

export async function fetchAnnouncements(): Promise<Announcement[]> {
  return apiRequest<Announcement[]>("/crm/host/announcements");
}

export async function fetchAnnouncement(id: string): Promise<Announcement> {
  return apiRequest<Announcement>(`/crm/host/announcements/${id}`);
}

export async function createAnnouncement(input: {
  title: string;
  body_email: string;
  body_whatsapp?: string | null;
  channel?: string;
  segment_id?: string | null;
  segment_key?: string | null;
  filters?: Record<string, unknown> | null;
}): Promise<Announcement> {
  return apiRequest<Announcement>("/crm/host/announcements", {
    method: "POST",
    body: input,
    timeout: "long",
  });
}

export async function dispatchAnnouncementEmail(
  id: string,
): Promise<AnnouncementDispatchResult> {
  return apiRequest<AnnouncementDispatchResult>(
    `/crm/host/announcements/${id}/dispatch-email`,
    { method: "POST", timeout: "long" },
  );
}

export async function cancelAnnouncement(id: string): Promise<Announcement> {
  return apiRequest<Announcement>(`/crm/host/announcements/${id}/cancel`, {
    method: "POST",
  });
}
