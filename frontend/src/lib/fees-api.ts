import { apiRequest } from "@/lib/api";
import type {
  HostFeeOverride,
  HostFeeOverrideCreate,
  HostFeeOverrideUpdate,
  PlatformFeeSetting,
  PlatformFeeSettingCreate,
  PlatformFeeSettingUpdate,
} from "@/lib/types/fees";

export type FeeSettingsQuery = {
  category?: string;
  fee_key?: string;
  include_disabled?: boolean;
};

export async function fetchFeeSettings(
  params?: FeeSettingsQuery,
): Promise<PlatformFeeSetting[]> {
  const qs = new URLSearchParams();
  if (params?.category) qs.set("category", params.category);
  if (params?.fee_key) qs.set("fee_key", params.fee_key);
  if (params?.include_disabled === false) qs.set("include_disabled", "false");
  const q = qs.toString();
  return apiRequest<PlatformFeeSetting[]>(
    `/finance/admin/fees/settings${q ? `?${q}` : ""}`,
  );
}

export async function createFeeSetting(
  body: PlatformFeeSettingCreate,
): Promise<PlatformFeeSetting> {
  return apiRequest<PlatformFeeSetting>("/finance/admin/fees/settings", {
    method: "POST",
    body,
  });
}

export async function updateFeeSetting(
  id: string,
  body: PlatformFeeSettingUpdate,
): Promise<PlatformFeeSetting> {
  return apiRequest<PlatformFeeSetting>(`/finance/admin/fees/settings/${id}`, {
    method: "PATCH",
    body,
  });
}

export type HostFeeOverridesQuery = {
  host_id?: string;
  fee_key?: string;
  include_disabled?: boolean;
};

export async function fetchHostFeeOverrides(
  params?: HostFeeOverridesQuery,
): Promise<HostFeeOverride[]> {
  const qs = new URLSearchParams();
  if (params?.host_id) qs.set("host_id", params.host_id);
  if (params?.fee_key) qs.set("fee_key", params.fee_key);
  if (params?.include_disabled === false) qs.set("include_disabled", "false");
  const q = qs.toString();
  return apiRequest<HostFeeOverride[]>(
    `/finance/admin/fees/overrides${q ? `?${q}` : ""}`,
  );
}

export async function createHostFeeOverride(
  body: HostFeeOverrideCreate,
): Promise<HostFeeOverride> {
  return apiRequest<HostFeeOverride>("/finance/admin/fees/overrides", {
    method: "POST",
    body,
  });
}

export async function updateHostFeeOverride(
  id: string,
  body: HostFeeOverrideUpdate,
): Promise<HostFeeOverride> {
  return apiRequest<HostFeeOverride>(`/finance/admin/fees/overrides/${id}`, {
    method: "PATCH",
    body,
  });
}
