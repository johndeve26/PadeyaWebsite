import { apiRequest } from "@/lib/api";
import type {
  AdminFanRow,
  FanBadge,
  FanDirectoryList,
  FanPassport,
  FanPassportPublicPage,
  PassportEventSafe,
  PassportSettings,
  PassportSettingsUpdate,
} from "@/lib/types/passport";

export async function fetchMyPassport(): Promise<FanPassport> {
  return apiRequest<FanPassport>("/dashboard/passport");
}

export async function fetchMyBadges(): Promise<FanBadge[]> {
  return apiRequest<FanBadge[]>("/passport/me/badges");
}

export async function fetchPassportSettings(): Promise<PassportSettings> {
  return apiRequest<PassportSettings>("/dashboard/passport/settings");
}

export async function updatePassportSettings(
  input: PassportSettingsUpdate,
): Promise<PassportSettings> {
  return apiRequest<PassportSettings>("/dashboard/passport/settings", {
    method: "PATCH",
    body: input,
  });
}

export async function fetchPublicPassport(
  username: string,
): Promise<FanPassportPublicPage> {
  return apiRequest<FanPassportPublicPage>(
    `/f/${encodeURIComponent(username)}`,
    { auth: false },
  );
}

export async function fetchPublicPassportActivity(
  username: string,
): Promise<{ items: PassportEventSafe[] }> {
  return apiRequest<{ items: PassportEventSafe[] }>(
    `/f/${encodeURIComponent(username)}/activity`,
    { auth: false },
  );
}

export async function fetchPublicPassportBadges(
  username: string,
): Promise<FanBadge[]> {
  return apiRequest<FanBadge[]>(
    `/f/${encodeURIComponent(username)}/badges`,
    { auth: false },
  );
}

export async function fetchFanDirectory(params: {
  q?: string;
  city?: string;
  category?: string;
  badge?: string;
  sort?: string;
  page?: number;
  limit?: number;
  has_reviews?: boolean;
  has_vault_unlocks?: boolean;
  min_events?: number;
  max_events?: number;
} = {}): Promise<FanDirectoryList> {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "") continue;
    sp.set(k, String(v));
  }
  const qs = sp.toString();
  return apiRequest<FanDirectoryList>(`/fans${qs ? `?${qs}` : ""}`, {
    auth: false,
  });
}

export async function fetchAdminFans(params: {
  q?: string;
  visibility?: string;
  directory_only?: boolean;
  include_hidden?: boolean;
  page?: number;
  limit?: number;
} = {}): Promise<{ items: AdminFanRow[]; page: number; limit: number; total: number }> {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "") continue;
    sp.set(k, String(v));
  }
  const qs = sp.toString();
  return apiRequest(`/admin/fans${qs ? `?${qs}` : ""}`);
}

export async function adminHideFan(
  userId: string,
  reason: string,
): Promise<void> {
  await apiRequest(`/admin/fans/${encodeURIComponent(userId)}/hide`, {
    method: "PATCH",
    body: { reason },
  });
}

export async function adminRestoreFan(
  userId: string,
  reason = "restored",
): Promise<void> {
  await apiRequest(`/admin/fans/${encodeURIComponent(userId)}/restore`, {
    method: "PATCH",
    body: { reason },
  });
}
