import { apiRequest } from "@/lib/api";
import type { EventTemplate } from "@/lib/types/lifecycle";

export async function fetchEventTemplates(
  includeArchived = false,
): Promise<EventTemplate[]> {
  const q = includeArchived ? "?include_archived=true" : "";
  return apiRequest<EventTemplate[]>(`/events/templates${q}`);
}

export async function fetchEventTemplate(id: string): Promise<EventTemplate> {
  return apiRequest<EventTemplate>(`/events/templates/${id}`);
}

export async function createEventTemplate(body: {
  name: string;
  description?: string | null;
  payload?: Record<string, unknown>;
}): Promise<EventTemplate> {
  return apiRequest<EventTemplate>("/events/templates", {
    method: "POST",
    body,
  });
}

export async function updateEventTemplate(
  id: string,
  body: {
    name?: string;
    description?: string | null;
    payload?: Record<string, unknown>;
  },
): Promise<EventTemplate> {
  return apiRequest<EventTemplate>(`/events/templates/${id}`, {
    method: "PATCH",
    body,
  });
}

export async function archiveEventTemplate(id: string): Promise<EventTemplate> {
  return apiRequest<EventTemplate>(`/events/templates/${id}/archive`, {
    method: "POST",
  });
}

export async function restoreEventTemplate(id: string): Promise<EventTemplate> {
  return apiRequest<EventTemplate>(`/events/templates/${id}/restore`, {
    method: "POST",
  });
}
