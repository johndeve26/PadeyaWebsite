import { apiRequest } from "@/lib/api";

export type SponsorSavedItem = {
  id: string;
  sponsor_id: string;
  item_type: "host" | "event" | "sponsorship_slot";
  item_id: string;
  note: string | null;
  created_at: string;
  updated_at: string;
  available: boolean;
  title: string | null;
  subtitle: string | null;
  href: string | null;
};

export type SponsorSavedList = {
  items: SponsorSavedItem[];
  total: number;
  saved_count: number;
};

export async function fetchSponsorSaved(
  sponsorId: string,
  params?: { item_type?: string; sort?: string },
): Promise<SponsorSavedList> {
  const sp = new URLSearchParams();
  if (params?.item_type) sp.set("item_type", params.item_type);
  if (params?.sort) sp.set("sort", params.sort);
  const qs = sp.toString();
  return apiRequest<SponsorSavedList>(
    `/sponsors/workspaces/${encodeURIComponent(sponsorId)}/saved${qs ? `?${qs}` : ""}`,
  );
}

export async function saveSponsorItem(
  sponsorId: string,
  body: {
    item_type: string;
    item_id: string;
    note?: string | null;
  },
): Promise<SponsorSavedItem> {
  return apiRequest<SponsorSavedItem>(
    `/sponsors/workspaces/${encodeURIComponent(sponsorId)}/saved`,
    { method: "POST", body },
  );
}

export async function updateSponsorSavedNote(
  sponsorId: string,
  savedId: string,
  note: string | null,
): Promise<SponsorSavedItem> {
  return apiRequest<SponsorSavedItem>(
    `/sponsors/workspaces/${encodeURIComponent(sponsorId)}/saved/${encodeURIComponent(savedId)}`,
    { method: "PATCH", body: { note } },
  );
}

export async function unsaveSponsorItem(
  sponsorId: string,
  savedId: string,
): Promise<void> {
  await apiRequest(
    `/sponsors/workspaces/${encodeURIComponent(sponsorId)}/saved/${encodeURIComponent(savedId)}`,
    { method: "DELETE" },
  );
}

export function savedKey(itemType: string, itemId: string): string {
  return `${itemType}:${itemId}`;
}
