import { apiRequest } from "@/lib/api";
import type {
  HostTierSummary,
  LegacyContentBlock,
  LegacyFeaturedItem,
  LegacyPage,
  LegacyTier,
  ScoreHistory,
  TierProgress,
} from "@/lib/types/legacy";

export async function fetchLegacyPage(username: string): Promise<LegacyPage> {
  return apiRequest<LegacyPage>(`/u/${encodeURIComponent(username)}/legacy`, {
    auth: false,
  });
}

export async function fetchMyLegacyPage(): Promise<LegacyPage> {
  return apiRequest<LegacyPage>("/host/legacy");
}

export async function fetchMyTierProgress(): Promise<TierProgress> {
  return apiRequest<TierProgress>("/legacy/me/tier");
}

export async function updateMyLegacyProfile(
  input: Record<string, unknown>,
): Promise<LegacyPage> {
  return apiRequest<LegacyPage>("/host/legacy", { method: "PATCH", body: input });
}

export async function fetchLegacyContentBlocks(): Promise<LegacyContentBlock[]> {
  return apiRequest<LegacyContentBlock[]>("/host/legacy/content-blocks");
}

export async function createLegacyContentBlock(
  input: Record<string, unknown>,
): Promise<LegacyContentBlock> {
  return apiRequest<LegacyContentBlock>("/host/legacy/content-blocks", {
    method: "POST",
    body: input,
  });
}

export async function updateLegacyContentBlock(
  blockId: string,
  input: Record<string, unknown>,
): Promise<LegacyContentBlock> {
  return apiRequest<LegacyContentBlock>(`/host/legacy/content-blocks/${blockId}`, {
    method: "PATCH",
    body: input,
  });
}

export async function toggleLegacyContentBlock(
  blockId: string,
): Promise<LegacyContentBlock> {
  return apiRequest<LegacyContentBlock>(
    `/host/legacy/content-blocks/${blockId}/toggle`,
    { method: "POST" },
  );
}

export async function reorderLegacyContentBlocks(
  orderedIds: string[],
): Promise<LegacyContentBlock[]> {
  return apiRequest<LegacyContentBlock[]>("/host/legacy/content-blocks/reorder", {
    method: "POST",
    body: { ordered_ids: orderedIds },
  });
}

export async function deleteLegacyContentBlock(blockId: string): Promise<void> {
  await apiRequest<void>(`/host/legacy/content-blocks/${blockId}`, {
    method: "DELETE",
  });
}

export async function fetchLegacyFeaturedItems(): Promise<LegacyFeaturedItem[]> {
  return apiRequest<LegacyFeaturedItem[]>("/host/legacy/featured-items");
}

export async function upsertLegacyFeaturedItem(
  input: Record<string, unknown>,
): Promise<LegacyFeaturedItem> {
  return apiRequest<LegacyFeaturedItem>("/host/legacy/featured-items", {
    method: "POST",
    body: input,
  });
}

export async function clearLegacyFeaturedPlacement(placement: string): Promise<void> {
  await apiRequest<void>(
    `/host/legacy/featured-items/${encodeURIComponent(placement)}`,
    { method: "DELETE" },
  );
}

export async function fetchAdminHostTiers(): Promise<HostTierSummary[]> {
  return apiRequest<HostTierSummary[]>("/legacy/admin/hosts");
}

export async function fetchAdminLegacyTiers(): Promise<LegacyTier[]> {
  return apiRequest<LegacyTier[]>("/legacy/admin/tiers");
}

export async function updateAdminLegacyTier(
  tierId: string,
  input: Record<string, unknown>,
): Promise<LegacyTier> {
  return apiRequest<LegacyTier>(`/legacy/admin/tiers/${tierId}`, {
    method: "PATCH",
    body: input,
  });
}

export async function recalculateHostTier(hostId: string): Promise<HostTierSummary> {
  return apiRequest<HostTierSummary>(`/legacy/admin/hosts/${hostId}/recalculate`, {
    method: "POST",
  });
}

export async function recalculateAllHostTiers(): Promise<{ recalculated: number }> {
  return apiRequest<{ recalculated: number }>("/legacy/admin/recalculate-all", {
    method: "POST",
  });
}

export async function fetchHostTierHistory(hostId: string): Promise<ScoreHistory[]> {
  return apiRequest<ScoreHistory[]>(`/legacy/admin/hosts/${hostId}/history`);
}
