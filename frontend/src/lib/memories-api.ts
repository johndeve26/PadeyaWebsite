import { apiRequest, apiUpload } from "@/lib/api";
import type {
  AdminMemoryPhoto,
  EventMemory,
  MemoryAlbumsResponse,
  MemoryEligibility,
} from "@/lib/types/memories";

export async function fetchPublicMemory(
  username: string,
  eventSlug: string,
): Promise<EventMemory> {
  return apiRequest<EventMemory>(
    `/memories/public/${encodeURIComponent(username)}/${encodeURIComponent(eventSlug)}`,
  );
}

export async function fetchMemoryByEventSlug(
  eventSlug: string,
): Promise<EventMemory> {
  return apiRequest<EventMemory>(
    `/memories/events/${encodeURIComponent(eventSlug)}`,
  );
}

export async function fetchMemoryAlbums(options?: {
  limit?: number;
  cursor?: string | null;
  city?: string | null;
}): Promise<MemoryAlbumsResponse> {
  const params = new URLSearchParams();
  if (options?.limit) params.set("limit", String(options.limit));
  if (options?.cursor) params.set("cursor", options.cursor);
  if (options?.city) params.set("city", options.city);
  const qs = params.toString();
  return apiRequest<MemoryAlbumsResponse>(
    `/memories/albums${qs ? `?${qs}` : ""}`,
  );
}

export async function fetchMemoryEligibility(
  eventSlug: string,
): Promise<MemoryEligibility> {
  return apiRequest<MemoryEligibility>(
    `/memories/events/${encodeURIComponent(eventSlug)}/eligibility`,
  );
}

export async function fetchHostMemory(eventId: string): Promise<EventMemory> {
  return apiRequest<EventMemory>(`/memories/host/events/${eventId}`);
}

export async function updateHostMemory(
  eventId: string,
  payload: {
    host_recap_note?: string | null;
    external_gallery_url?: string | null;
    external_gallery_label?: string | null;
  },
): Promise<EventMemory> {
  return apiRequest<EventMemory>(`/memories/host/events/${eventId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function uploadHostMemoryPhoto(
  eventId: string,
  file: File,
  options?: { caption?: string; is_cover?: boolean },
): Promise<EventMemory> {
  const body = new FormData();
  body.append("file", file);
  if (options?.caption) body.append("caption", options.caption);
  if (options?.is_cover) body.append("is_cover", "true");
  return apiUpload<EventMemory>(
    `/memories/host/events/${eventId}/photos`,
    body,
  );
}

export async function uploadFanMemoryPhoto(
  eventId: string,
  file: File,
  options?: { caption?: string },
): Promise<EventMemory> {
  const body = new FormData();
  body.append("file", file);
  if (options?.caption) body.append("caption", options.caption);
  return apiUpload<EventMemory>(`/memories/events/${eventId}/photos`, body);
}

export async function patchMemoryPhoto(
  eventId: string,
  mediaId: string,
  payload: { caption?: string | null; sort_order?: number; is_cover?: boolean },
  asHost = false,
): Promise<EventMemory> {
  const base = asHost
    ? `/memories/host/events/${eventId}/photos/${mediaId}`
    : `/memories/events/${eventId}/photos/${mediaId}`;
  return apiRequest<EventMemory>(base, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deleteMemoryPhoto(
  eventId: string,
  mediaId: string,
  asHost = false,
): Promise<EventMemory> {
  if (asHost) {
    return apiRequest<EventMemory>(
      `/memories/host/events/${eventId}/media/${mediaId}`,
      { method: "DELETE" },
    );
  }
  return apiRequest<EventMemory>(
    `/memories/events/${eventId}/photos/${mediaId}`,
    { method: "DELETE" },
  );
}

export async function moderateHostAttendeePhoto(
  eventId: string,
  mediaId: string,
  payload: { action: "hide" | "restore" | "remove"; note?: string },
): Promise<EventMemory> {
  return apiRequest<EventMemory>(
    `/memories/host/events/${eventId}/photos/${mediaId}/moderate`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export async function addMemoryMedia(
  eventId: string,
  payload: {
    url: string;
    media_type?: string;
    label?: string | null;
    caption?: string | null;
  },
): Promise<EventMemory> {
  return apiRequest<EventMemory>(`/memories/host/events/${eventId}/media`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function deleteMemoryMedia(
  eventId: string,
  mediaId: string,
): Promise<EventMemory> {
  return apiRequest<EventMemory>(
    `/memories/host/events/${eventId}/media/${mediaId}`,
    { method: "DELETE" },
  );
}

export async function fetchAdminMemories(): Promise<EventMemory[]> {
  return apiRequest<EventMemory[]>("/memories/admin");
}

export async function fetchAdminMemoryPhotos(
  limit = 100,
): Promise<AdminMemoryPhoto[]> {
  return apiRequest<AdminMemoryPhoto[]>(`/memories/admin/photos?limit=${limit}`);
}

export async function moderateMemory(
  memoryId: string,
  payload: { action: "hide" | "unhide" | "flag" | "approve"; note?: string },
): Promise<EventMemory> {
  return apiRequest<EventMemory>(`/memories/admin/${memoryId}/moderate`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function moderateAdminPhoto(
  mediaId: string,
  payload: { action: "hide" | "restore" | "remove"; note?: string },
): Promise<EventMemory> {
  return apiRequest<EventMemory>(`/memories/admin/photos/${mediaId}/moderate`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
