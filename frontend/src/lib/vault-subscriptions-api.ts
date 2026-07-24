import { apiRequest } from "@/lib/api";
import type { VaultSubscription } from "@/lib/types/lifecycle";

export async function createVaultSubscription(body: {
  host_id: string;
  plan_label?: string;
  price?: number;
  currency?: string;
}): Promise<VaultSubscription> {
  return apiRequest<VaultSubscription>("/vault/subscriptions", {
    method: "POST",
    body,
  });
}

export async function fetchMyVaultSubscriptions(
  includeArchived = false,
): Promise<VaultSubscription[]> {
  const q = includeArchived ? "?include_archived=true" : "";
  return apiRequest<VaultSubscription[]>(`/vault/subscriptions/mine${q}`);
}

export async function fetchHostVaultSubscriptions(
  includeArchived = false,
): Promise<VaultSubscription[]> {
  const q = includeArchived ? "?include_archived=true" : "";
  return apiRequest<VaultSubscription[]>(`/vault/host/subscriptions${q}`);
}

export async function cancelVaultSubscription(
  id: string,
): Promise<VaultSubscription> {
  return apiRequest<VaultSubscription>(`/vault/subscriptions/${id}/cancel`, {
    method: "POST",
  });
}

export async function archiveVaultSubscription(
  id: string,
): Promise<VaultSubscription> {
  return apiRequest<VaultSubscription>(`/vault/subscriptions/${id}/archive`, {
    method: "POST",
  });
}

export async function restoreVaultSubscription(
  id: string,
): Promise<VaultSubscription> {
  return apiRequest<VaultSubscription>(`/vault/subscriptions/${id}/restore`, {
    method: "POST",
  });
}
