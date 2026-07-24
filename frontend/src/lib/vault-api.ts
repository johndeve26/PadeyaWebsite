import { apiRequest } from "@/lib/api";
import type {
  AdminVaultFilters,
  VaultAdminItem,
  VaultCatalogCard,
  VaultCheckout,
  VaultEarnings,
  VaultItem,
  VaultLibrarySummary,
  VaultPurchase,
  VaultStudioSummary,
} from "@/lib/types/vault";

export async function fetchPublicVault(username: string): Promise<VaultCatalogCard[]> {
  return apiRequest<VaultCatalogCard[]>(
    `/vault/public/${encodeURIComponent(username)}`,
    { auth: false },
  );
}

export async function fetchVaultRelatedToEvent(
  eventId: string,
): Promise<VaultCatalogCard[]> {
  return apiRequest<VaultCatalogCard[]>(
    `/vault/related/event/${encodeURIComponent(eventId)}`,
    { auth: false },
  );
}

export async function fetchVaultRelatedToMemory(
  memoryId: string,
): Promise<VaultCatalogCard[]> {
  return apiRequest<VaultCatalogCard[]>(
    `/vault/related/memory/${encodeURIComponent(memoryId)}`,
    { auth: false },
  );
}

export async function fetchPublicVaultItem(
  username: string,
  itemSlug: string,
): Promise<VaultItem> {
  return apiRequest<VaultItem>(
    `/vault/public/${encodeURIComponent(username)}/${encodeURIComponent(itemSlug)}`,
  );
}

export async function unlockVaultItem(itemId: string): Promise<VaultCheckout> {
  return apiRequest<VaultCheckout>(`/vault/unlock/${itemId}`, { method: "POST" });
}

export async function redeemVaultInvite(
  itemId: string,
  accessCode: string,
): Promise<VaultItem> {
  return apiRequest<VaultItem>(`/vault/redeem/${itemId}`, {
    method: "POST",
    body: { access_code: accessCode },
  });
}

export async function fetchMyVaultPurchases(): Promise<VaultPurchase[]> {
  return apiRequest<VaultPurchase[]>("/vault/me/purchases");
}

export async function fetchMyVaultPurchase(purchaseId: string): Promise<VaultPurchase> {
  return apiRequest<VaultPurchase>(
    `/vault/me/purchases/${encodeURIComponent(purchaseId)}`,
  );
}

export async function fetchMyVaultItems(): Promise<VaultItem[]> {
  return apiRequest<VaultItem[]>("/vault/me/items");
}

export async function fetchMyVaultLibrary(): Promise<VaultLibrarySummary> {
  return apiRequest<VaultLibrarySummary>("/vault/me/library");
}

export async function fetchVaultStudio(): Promise<VaultStudioSummary> {
  return apiRequest<VaultStudioSummary>("/vault/host/studio");
}

export async function fetchHostVaultItems(): Promise<VaultItem[]> {
  return apiRequest<VaultItem[]>("/vault/host/items");
}

export async function fetchHostVaultItem(id: string): Promise<VaultItem> {
  return apiRequest<VaultItem>(`/vault/host/items/${id}`);
}

export async function previewHostVaultItemAsFan(id: string): Promise<VaultItem> {
  return apiRequest<VaultItem>(`/vault/host/items/${id}/preview`);
}

export async function createHostVaultItem(
  input: Record<string, unknown>,
): Promise<VaultItem> {
  return apiRequest<VaultItem>("/vault/host/items", { method: "POST", body: input });
}

export async function updateHostVaultItem(
  id: string,
  input: Record<string, unknown>,
): Promise<VaultItem> {
  return apiRequest<VaultItem>(`/vault/host/items/${id}`, {
    method: "PATCH",
    body: input,
  });
}

export async function publishHostVaultItem(id: string): Promise<VaultItem> {
  return apiRequest<VaultItem>(`/vault/host/items/${id}/publish`, { method: "POST" });
}

export async function unpublishHostVaultItem(id: string): Promise<VaultItem> {
  return apiRequest<VaultItem>(`/vault/host/items/${id}/unpublish`, {
    method: "POST",
  });
}

export async function scheduleHostVaultItem(
  id: string,
  startsAt?: string | null,
): Promise<VaultItem> {
  return apiRequest<VaultItem>(`/vault/host/items/${id}/schedule`, {
    method: "POST",
    body: { starts_at: startsAt || null },
  });
}

export async function archiveHostVaultItem(id: string): Promise<VaultItem> {
  return apiRequest<VaultItem>(`/vault/host/items/${id}/archive`, { method: "POST" });
}

export async function restoreHostVaultItem(id: string): Promise<VaultItem> {
  return apiRequest<VaultItem>(`/vault/host/items/${id}/restore`, { method: "POST" });
}

export async function deleteHostVaultItem(id: string): Promise<void> {
  await apiRequest<{ message: string }>(`/vault/host/items/${id}`, {
    method: "DELETE",
  });
}

export async function fetchHostVaultEarnings(): Promise<VaultEarnings> {
  return apiRequest<VaultEarnings>("/vault/host/earnings");
}

export async function fetchAdminVaultItems(
  filters: AdminVaultFilters = {},
): Promise<VaultAdminItem[]> {
  const params = new URLSearchParams();
  if (filters.status) params.set("status", filters.status);
  if (filters.moderation_status) {
    params.set("moderation_status", filters.moderation_status);
  }
  if (filters.access_type) params.set("access_type", filters.access_type);
  if (filters.host_username) params.set("host_username", filters.host_username);
  if (filters.q) params.set("q", filters.q);
  if (filters.limit != null) params.set("limit", String(filters.limit));
  if (filters.offset != null) params.set("offset", String(filters.offset));
  const qs = params.toString();
  return apiRequest<VaultAdminItem[]>(
    `/vault/admin/items${qs ? `?${qs}` : ""}`,
  );
}

export async function moderateVaultItem(
  id: string,
  action: string,
  note?: string,
): Promise<VaultAdminItem> {
  return apiRequest<VaultAdminItem>(`/vault/admin/items/${id}/moderate`, {
    method: "POST",
    body: { action, note },
  });
}
