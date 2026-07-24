import { apiRequest } from "@/lib/api";
import { getAccessToken } from "@/lib/auth/storage";
import { getApiBaseUrl, getApiPrefix } from "@/lib/api-base";

const API_URL = getApiBaseUrl();
const API_PREFIX = getApiPrefix();

export type AdminExportMode = "public_summary" | "operations" | "finance";
export type AdminExportFormat = "csv" | "json" | "xlsx";

export type AdminEventBuyerRow = {
  event_id: string;
  event_title: string;
  event_slug?: string;
  event_date?: string | null;
  host_name?: string | null;
  host_id?: string | null;
  ticket_id: string;
  public_code: string;
  safe_ticket_code?: string;
  safe_order_code?: string;
  ticket_type_name: string;
  ticket_type?: string;
  ticket_status: string;
  purchase_status?: string;
  checked_in_at: string | null;
  ticket_created_at?: string | null;
  purchase_date?: string | null;
  seat_label: string | null;
  table_label: string | null;
  attendee_index?: number | null;
  quantity?: number | null;
  order_id: string;
  order_status: string | null;
  payment_status?: string | null;
  refund_status?: string | null;
  order_paid_at?: string | null;
  order_currency?: string | null;
  order_total_amount?: string | null;
  amount_paid?: string | null;
  currency?: string | null;
  discount_amount?: string | null;
  promo_code?: string | null;
  promo_code_used?: string | null;
  ambassador_code?: string | null;
  referral_source?: string | null;
  holder_name?: string;
  holder_email?: string | null;
  buyer_user_id: string;
  buyer_full_name?: string | null;
  buyer_account_email?: string | null;
  buyer_email?: string | null;
  display_name?: string | null;
  username?: string | null;
  passport_username: string | null;
  passport_display_name: string | null;
  attendee_name?: string | null;
  is_checked_in: boolean;
  checked_in?: boolean;
  check_in_method?: string | null;
};

export type AdminEventBuyersResponse = {
  event_id: string;
  event_title: string;
  event_slug?: string;
  event_date?: string | null;
  host_name?: string | null;
  host_id?: string | null;
  total: number;
  limit: number;
  offset: number;
  items: AdminEventBuyerRow[];
};

export type AdminEventBuyerExportLog = {
  id: string;
  action: string;
  actor_user_id: string | null;
  admin_user_id?: string | null;
  actor_name: string | null;
  actor_email: string | null;
  event_id?: string | null;
  host_profile_id?: string | null;
  export_mode?: string | null;
  format?: string | null;
  filters_json?: Record<string, string | null | undefined> | null;
  row_count?: number | null;
  reason?: string | null;
  ip_address?: string | null;
  user_agent?: string | null;
  details: {
    row_count?: number;
    format?: string;
    export_mode?: string;
    reason?: string | null;
    filters?: Record<string, string | null | undefined>;
    filters_json?: Record<string, string | null | undefined>;
  } | null;
  created_at: string | null;
};

export type AdminBuyerFilters = {
  q?: string;
  ticket_status?: string;
  purchase_status?: string;
  payment_status?: string;
  refund_status?: string;
  checked_in?: string;
  ticket_type?: string;
  purchased_from?: string;
  purchased_to?: string;
  promo_code?: string;
  ambassador_code?: string;
  limit?: number;
  offset?: number;
};

function applyFilters(qs: URLSearchParams, filters: AdminBuyerFilters) {
  if (filters.q) qs.set("q", filters.q);
  if (filters.ticket_status) qs.set("ticket_status", filters.ticket_status);
  if (filters.purchase_status) qs.set("purchase_status", filters.purchase_status);
  if (filters.payment_status) qs.set("payment_status", filters.payment_status);
  if (filters.refund_status) qs.set("refund_status", filters.refund_status);
  if (filters.checked_in) qs.set("checked_in", filters.checked_in);
  if (filters.ticket_type) qs.set("ticket_type", filters.ticket_type);
  if (filters.purchased_from) qs.set("purchased_from", filters.purchased_from);
  if (filters.purchased_to) qs.set("purchased_to", filters.purchased_to);
  if (filters.promo_code) qs.set("promo_code", filters.promo_code);
  if (filters.ambassador_code) qs.set("ambassador_code", filters.ambassador_code);
  if (filters.limit != null) qs.set("limit", String(filters.limit));
  if (filters.offset != null) qs.set("offset", String(filters.offset));
}

function toQuery(filters: AdminBuyerFilters): string {
  const qs = new URLSearchParams();
  applyFilters(qs, filters);
  const query = qs.toString();
  return query ? `?${query}` : "";
}

export async function fetchAdminEventBuyers(
  eventId: string,
  filters: AdminBuyerFilters = {},
): Promise<AdminEventBuyersResponse> {
  return apiRequest<AdminEventBuyersResponse>(
    `/admin/events/${eventId}/buyers${toQuery(filters)}`,
  );
}

export async function fetchAdminEventBuyerExports(
  eventId: string,
): Promise<AdminEventBuyerExportLog[]> {
  return apiRequest<AdminEventBuyerExportLog[]>(
    `/admin/events/${eventId}/buyers/exports`,
  );
}

export async function exportAdminEventBuyers(
  eventId: string,
  opts: AdminBuyerFilters & {
    format?: AdminExportFormat;
    mode?: AdminExportMode;
    reason?: string;
    include_private_contact?: boolean;
  } = {},
): Promise<void> {
  const {
    format = "csv",
    mode = "operations",
    reason,
    include_private_contact,
    ...filters
  } = opts;
  const qs = new URLSearchParams();
  qs.set("format", format);
  qs.set("mode", mode);
  if (reason) qs.set("reason", reason);
  if (include_private_contact) qs.set("include_private_contact", "true");
  applyFilters(qs, filters);

  const token = getAccessToken();
  const res = await fetch(
    `${API_URL}${API_PREFIX}/admin/events/${eventId}/buyers/export?${qs}`,
    {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    },
  );
  if (!res.ok) {
    let detail = "Export failed";
    try {
      const data = (await res.json()) as { detail?: string };
      if (typeof data.detail === "string") detail = data.detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  const blob = await res.blob();
  const disposition = res.headers.get("Content-Disposition") || "";
  const match = /filename="?([^";]+)"?/i.exec(disposition);
  const filename =
    match?.[1]?.trim() ||
    `padeya-event-buyers-${eventId}.${format === "json" ? "json" : "csv"}`;
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
