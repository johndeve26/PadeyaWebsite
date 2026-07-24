import { apiRequest } from "@/lib/api";

export type SponsorshipDealInvoice = {
  id: string;
  invoice_number: string;
  amount: string;
  currency: string;
  status: string;
  due_at: string | null;
  paid_at: string | null;
  payment_url: string | null;
};

export type SponsorshipDeal = {
  id: string;
  sponsor_id: string;
  host_id: string;
  event_id: string | null;
  campaign_id: string | null;
  inquiry_id: string | null;
  slot_id: string | null;
  placement_id: string | null;
  title: string;
  description: string | null;
  package_type: string;
  deliverables: string[] | null;
  amount: string;
  currency: string;
  status: string;
  accepted_at: string | null;
  starts_at: string | null;
  ends_at: string | null;
  created_at: string;
  updated_at: string;
  host_display_name: string | null;
  sponsor_display_name: string | null;
  invoice: SponsorshipDealInvoice | null;
  can_edit: boolean;
  can_accept: boolean;
  can_pay: boolean;
};

export type HostSponsorshipRevenueReport = {
  revenue_pending_ngn: string | null;
  revenue_paid_ngn: string | null;
  active_placements: number;
  active_deals: number;
  pending_deliverables: number;
  overdue_deliverables: number;
  completed_deliverables: number;
  deliverables_completion_rate: number | null;
};

export type SponsorshipDeliverable = {
  id: string;
  deal_id: string;
  placement_id: string | null;
  title: string;
  description: string | null;
  deliverable_type: string;
  due_at: string | null;
  status: string;
  proof_url: string | null;
  proof_notes: string | null;
  submitted_at: string | null;
  approved_at: string | null;
  rejection_reason: string | null;
  created_at: string;
  updated_at: string;
  can_host_edit: boolean;
  can_host_submit: boolean;
  can_sponsor_review: boolean;
};

export async function fetchHostDeliverables(dealId: string): Promise<SponsorshipDeliverable[]> {
  return apiRequest(`/api/v1/host/sponsorship-deals/${dealId}/deliverables`);
}

export async function hostPatchDeliverable(
  dealId: string,
  deliverableId: string,
  body: { status?: string; proof_notes?: string; description?: string },
): Promise<SponsorshipDeliverable> {
  return apiRequest(
    `/api/v1/host/sponsorship-deals/${dealId}/deliverables/${deliverableId}`,
    { method: "PATCH", body: JSON.stringify(body) },
  );
}

export async function hostSubmitDeliverable(
  dealId: string,
  deliverableId: string,
  body: { proof_url: string; proof_notes?: string },
): Promise<SponsorshipDeliverable> {
  return apiRequest(
    `/api/v1/host/sponsorship-deals/${dealId}/deliverables/${deliverableId}/submit`,
    { method: "POST", body: JSON.stringify(body) },
  );
}

export async function fetchSponsorDeliverables(
  sponsorId: string,
  dealId: string,
): Promise<SponsorshipDeliverable[]> {
  return apiRequest(
    `/api/v1/sponsors/workspaces/${sponsorId}/deals/${dealId}/deliverables`,
  );
}

export async function approveSponsorDeliverable(
  sponsorId: string,
  dealId: string,
  deliverableId: string,
): Promise<SponsorshipDeliverable> {
  return apiRequest(
    `/api/v1/sponsors/workspaces/${sponsorId}/deals/${dealId}/deliverables/${deliverableId}/approve`,
    { method: "POST" },
  );
}

export async function rejectSponsorDeliverable(
  sponsorId: string,
  dealId: string,
  deliverableId: string,
  body: { rejection_reason: string },
): Promise<SponsorshipDeliverable> {
  return apiRequest(
    `/api/v1/sponsors/workspaces/${sponsorId}/deals/${dealId}/deliverables/${deliverableId}/reject`,
    { method: "POST", body: JSON.stringify(body) },
  );
}

export async function fetchAdminDeliverables(dealId: string): Promise<SponsorshipDeliverable[]> {
  return apiRequest(`/api/v1/admin/sponsorship-deals/${dealId}/deliverables`);
}

export async function fetchSponsorDeals(sponsorId: string): Promise<SponsorshipDeal[]> {
  return apiRequest<SponsorshipDeal[]>(
    `/api/v1/sponsors/workspaces/${sponsorId}/deals`,
  );
}

export async function fetchSponsorDeal(
  sponsorId: string,
  dealId: string,
): Promise<SponsorshipDeal> {
  return apiRequest<SponsorshipDeal>(
    `/api/v1/sponsors/workspaces/${sponsorId}/deals/${dealId}`,
  );
}

export async function acceptSponsorDeal(
  sponsorId: string,
  dealId: string,
): Promise<SponsorshipDeal> {
  return apiRequest<SponsorshipDeal>(
    `/api/v1/sponsors/workspaces/${sponsorId}/deals/${dealId}/accept`,
    { method: "POST" },
  );
}

export async function rejectSponsorDeal(
  sponsorId: string,
  dealId: string,
): Promise<SponsorshipDeal> {
  return apiRequest<SponsorshipDeal>(
    `/api/v1/sponsors/workspaces/${sponsorId}/deals/${dealId}/reject`,
    { method: "POST" },
  );
}

export async function paySponsorDeal(
  sponsorId: string,
  dealId: string,
): Promise<{ payment_url: string; invoice_id: string; message: string }> {
  return apiRequest(`/api/v1/sponsors/workspaces/${sponsorId}/deals/${dealId}/pay`, {
    method: "POST",
  });
}

export async function fetchHostSponsorshipDeals(): Promise<SponsorshipDeal[]> {
  return apiRequest<SponsorshipDeal[]>("/api/v1/host/sponsorship-deals");
}

export async function fetchHostSponsorshipDeal(dealId: string): Promise<SponsorshipDeal> {
  return apiRequest<SponsorshipDeal>(`/api/v1/host/sponsorship-deals/${dealId}`);
}

export async function createHostSponsorshipDeal(body: {
  sponsor_id: string;
  inquiry_id?: string;
  slot_id?: string;
  title: string;
  package_type: string;
  amount: string;
  description?: string;
  deliverables?: string[];
}): Promise<SponsorshipDeal> {
  return apiRequest<SponsorshipDeal>("/api/v1/host/sponsorship-deals", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function sendHostSponsorshipDeal(dealId: string): Promise<SponsorshipDeal> {
  return apiRequest<SponsorshipDeal>(
    `/api/v1/host/sponsorship-deals/${dealId}/send`,
    { method: "POST" },
  );
}

export async function cancelHostSponsorshipDeal(dealId: string): Promise<SponsorshipDeal> {
  return apiRequest<SponsorshipDeal>(
    `/api/v1/host/sponsorship-deals/${dealId}/cancel`,
    { method: "POST" },
  );
}

export async function fetchHostSponsorshipRevenue(): Promise<HostSponsorshipRevenueReport> {
  return apiRequest<HostSponsorshipRevenueReport>(
    "/api/v1/host/sponsorship-deals/reports/summary",
  );
}

export async function fetchAdminSponsorshipDeals(): Promise<SponsorshipDeal[]> {
  return apiRequest<SponsorshipDeal[]>("/api/v1/admin/sponsorship-deals");
}

export async function fetchAdminSponsorshipDeal(dealId: string): Promise<SponsorshipDeal> {
  return apiRequest<SponsorshipDeal>(`/api/v1/admin/sponsorship-deals/${dealId}`);
}

export async function adminCancelSponsorshipDeal(dealId: string): Promise<SponsorshipDeal> {
  return apiRequest<SponsorshipDeal>(
    `/api/v1/admin/sponsorship-deals/${dealId}/cancel`,
    { method: "POST" },
  );
}

export async function adminVoidSponsorshipInvoice(invoiceId: string): Promise<SponsorshipDeal> {
  return apiRequest<SponsorshipDeal>(
    `/api/v1/admin/sponsorship-invoices/${invoiceId}/void`,
    { method: "POST" },
  );
}
