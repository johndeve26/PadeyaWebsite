import { apiRequest } from "@/lib/api";
import type { EventMemory } from "@/lib/types/memories";

export async function fetchPublicMemory(
  username: string,
  eventSlug: string,
): Promise<EventMemory> {
  return apiRequest<EventMemory>(
    `/memories/public/${encodeURIComponent(username)}/${encodeURIComponent(eventSlug)}`,
  );
}

export async function fetchHostMemory(eventId: string): Promise<EventMemory> {
  return apiRequest<EventMemory>(`/memories/host/events/${eventId}`);
}

export async function updateHostMemory(
  eventId: string,
  payload: { host_recap_note: string | null },
): Promise<EventMemory> {
  return apiRequest<EventMemory>(`/memories/host/events/${eventId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function addMemoryMedia(
  eventId: string,
  payload: {
    url: string;
    media_type?: string;
    label?: string | null;
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

export async function moderateMemory(
  memoryId: string,
  payload: { action: "hide" | "unhide" | "flag" | "approve"; note?: string },
): Promise<EventMemory> {
  return apiRequest<EventMemory>(`/memories/admin/${memoryId}/moderate`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
