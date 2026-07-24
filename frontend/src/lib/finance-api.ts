import { apiDownload, apiRequest } from "@/lib/api";
import { getApiBaseUrl, getApiPrefix } from "@/lib/api-base";
import { getAccessToken } from "@/lib/auth/storage";
import type {
  AdminHostEarningsOverviewRow,
  HostBalance,
  HostEarningsReport,
  LedgerEntry,
  PayoutRequest,
  PlatformRevenueReport,
  RefundRequest,
  SettlementReport,
} from "@/lib/types/finance";

const API_URL = getApiBaseUrl();
const API_PREFIX = getApiPrefix();

export async function createRefundRequest(input: {
  order_id: string;
  reason: string;
  refund_type?: string;
  amount?: number;
}): Promise<RefundRequest> {
  return apiRequest<RefundRequest>("/finance/refunds/requests", {
    method: "POST",
    body: input,
  });
}

export async function fetchMyRefunds(): Promise<RefundRequest[]> {
  return apiRequest<RefundRequest[]>("/finance/refunds/mine");
}

export async function fetchStaffRefunds(status?: string): Promise<RefundRequest[]> {
  const qs = status ? `?status=${encodeURIComponent(status)}` : "";
  return apiRequest<RefundRequest[]>(`/finance/refunds/requests${qs}`);
}

export async function escalateRefund(
  id: string,
  note: string,
): Promise<RefundRequest> {
  return apiRequest<RefundRequest>(`/finance/refunds/requests/${id}/escalate`, {
    method: "POST",
    body: { note },
  });
}

export async function reviewRefund(
  id: string,
  action: "approve" | "reject",
  note?: string,
): Promise<RefundRequest> {
  return apiRequest<RefundRequest>(`/finance/refunds/requests/${id}/review`, {
    method: "POST",
    body: { action, note },
  });
}

export async function fetchHostBalance(): Promise<HostBalance> {
  return apiRequest<HostBalance>("/finance/host/balance");
}

export async function fetchHostLedger(): Promise<LedgerEntry[]> {
  return apiRequest<LedgerEntry[]>("/finance/host/ledger");
}

export async function fetchHostPayouts(): Promise<PayoutRequest[]> {
  return apiRequest<PayoutRequest[]>("/finance/host/payouts");
}

export async function createHostPayout(input: {
  amount: number;
  bank: { bank_name: string; account_name: string; account_number: string };
  note?: string;
}): Promise<PayoutRequest> {
  return apiRequest<PayoutRequest>("/finance/host/payouts", {
    method: "POST",
    body: input,
  });
}

export async function fetchAdminPayouts(status?: string): Promise<PayoutRequest[]> {
  const qs = status ? `?status=${encodeURIComponent(status)}` : "";
  return apiRequest<PayoutRequest[]>(`/finance/admin/payouts${qs}`);
}

export async function reviewPayout(
  id: string,
  action: "approve" | "reject" | "under_review",
  note?: string,
): Promise<PayoutRequest> {
  return apiRequest<PayoutRequest>(`/finance/admin/payouts/${id}/review`, {
    method: "POST",
    body: { action, note },
  });
}

export async function markPayoutPaid(
  id: string,
  input: {
    bank_transfer_reference: string;
    evidence_file_url: string;
    admin_note?: string;
    paid_at?: string;
  },
): Promise<PayoutRequest> {
  return apiRequest<PayoutRequest>(`/finance/admin/payouts/${id}/mark-paid`, {
    method: "POST",
    body: input,
  });
}

export async function fetchAdminLedger(hostId?: string): Promise<LedgerEntry[]> {
  const qs = hostId ? `?host_id=${encodeURIComponent(hostId)}` : "";
  return apiRequest<LedgerEntry[]>(`/finance/admin/ledger${qs}`);
}

export async function fetchSettlement(hostId?: string): Promise<SettlementReport> {
  const qs = hostId ? `?host_id=${encodeURIComponent(hostId)}` : "";
  return apiRequest<SettlementReport>(`/finance/admin/settlement${qs}`);
}

export async function fetchHostEarnings(eventId?: string): Promise<HostEarningsReport> {
  const qs = eventId ? `?event_id=${encodeURIComponent(eventId)}` : "";
  return apiRequest<HostEarningsReport>(`/finance/host/earnings${qs}`);
}

export async function fetchHostEventEarnings(
  eventId: string,
): Promise<HostEarningsReport> {
  return apiRequest<HostEarningsReport>(
    `/finance/host/events/${encodeURIComponent(eventId)}/earnings`,
  );
}

export async function fetchAdminEarnings(opts?: {
  hostId?: string;
  eventId?: string;
}): Promise<HostEarningsReport> {
  const params = new URLSearchParams();
  if (opts?.hostId) params.set("host_id", opts.hostId);
  if (opts?.eventId) params.set("event_id", opts.eventId);
  const qs = params.toString() ? `?${params}` : "";
  return apiRequest<HostEarningsReport>(`/finance/admin/earnings${qs}`);
}

export async function fetchAdminHostEarnings(
  hostId: string,
): Promise<HostEarningsReport> {
  return apiRequest<HostEarningsReport>(
    `/finance/admin/hosts/${encodeURIComponent(hostId)}/earnings`,
  );
}

export async function fetchAdminEventEarnings(
  eventId: string,
): Promise<HostEarningsReport> {
  return apiRequest<HostEarningsReport>(
    `/finance/admin/events/${encodeURIComponent(eventId)}/earnings`,
  );
}

export async function fetchAdminEarningsHosts(): Promise<
  AdminHostEarningsOverviewRow[]
> {
  return apiRequest<AdminHostEarningsOverviewRow[]>(
    "/finance/admin/earnings/hosts",
  );
}

async function downloadEarningsCsv(path: string, filename: string): Promise<void> {
  try {
    const { blob, filename: serverName } = await apiDownload(path);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = serverName || filename;
    a.click();
    URL.revokeObjectURL(url);
  } catch {
    const token = getAccessToken();
    const res = await fetch(`${API_URL}${API_PREFIX}${path}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) throw new Error("Export failed");
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }
}

export async function exportHostEarningsCsv(eventId?: string): Promise<void> {
  const qs = eventId ? `?event_id=${encodeURIComponent(eventId)}` : "";
  await downloadEarningsCsv(
    `/finance/host/earnings/export.csv${qs}`,
    "padeya-host-earnings.csv",
  );
}

export async function exportAdminEarningsCsv(opts?: {
  hostId?: string;
  eventId?: string;
}): Promise<void> {
  const params = new URLSearchParams();
  if (opts?.hostId) params.set("host_id", opts.hostId);
  if (opts?.eventId) params.set("event_id", opts.eventId);
  const qs = params.toString() ? `?${params}` : "";
  await downloadEarningsCsv(
    `/finance/admin/earnings/export.csv${qs}`,
    "padeya-admin-earnings.csv",
  );
}

export async function fetchPlatformRevenue(opts?: {
  hostId?: string;
  eventId?: string;
  revenueType?: string;
  dateFrom?: string;
  dateTo?: string;
}): Promise<PlatformRevenueReport> {
  const params = new URLSearchParams();
  if (opts?.hostId) params.set("host_id", opts.hostId);
  if (opts?.eventId) params.set("event_id", opts.eventId);
  if (opts?.revenueType) params.set("revenue_type", opts.revenueType);
  if (opts?.dateFrom) params.set("date_from", opts.dateFrom);
  if (opts?.dateTo) params.set("date_to", opts.dateTo);
  const qs = params.toString() ? `?${params}` : "";
  return apiRequest<PlatformRevenueReport>(
    `/finance/admin/platform-revenue${qs}`,
  );
}

export async function exportPlatformRevenueCsv(opts?: {
  hostId?: string;
  eventId?: string;
  revenueType?: string;
  dateFrom?: string;
  dateTo?: string;
}): Promise<void> {
  const params = new URLSearchParams();
  if (opts?.hostId) params.set("host_id", opts.hostId);
  if (opts?.eventId) params.set("event_id", opts.eventId);
  if (opts?.revenueType) params.set("revenue_type", opts.revenueType);
  if (opts?.dateFrom) params.set("date_from", opts.dateFrom);
  if (opts?.dateTo) params.set("date_to", opts.dateTo);
  const qs = params.toString() ? `?${params}` : "";
  await downloadEarningsCsv(
    `/finance/admin/platform-revenue/export.csv${qs}`,
    "padeya-platform-revenue.csv",
  );
}
