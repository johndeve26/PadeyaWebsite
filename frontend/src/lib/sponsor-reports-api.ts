import { apiRequest } from "@/lib/api";

export type InquiryCounts = {
  total: number;
  new: number;
  reviewing: number;
  accepted: number;
  declined: number;
  closed: number;
  pending: number;
};

export type LabelCount = { label: string; count: number };

export type SponsorOverviewReport = {
  sponsor_id: string;
  generated_at: string;
  saved_opportunities_count: number;
  inquiries: InquiryCounts;
  response_rate: number | null;
  avg_response_hours: number | null;
  campaigns_by_status: Record<string, number>;
  top_categories: LabelCount[];
  top_locations: LabelCount[];
  recommendation_engagement: {
    clicked: number;
    saved: number;
    dismissed: number;
  };
  linked_placements: {
    count: number;
    spend_committed_ngn: string | null;
  };
  deals: {
    committed_spend_ngn: string | null;
    paid_spend_ngn: string | null;
    pending_invoices: number;
    active_deals: number;
    completed_deals: number;
    proposals_awaiting: number;
    deliverables_pending: number;
    deliverables_completed: number;
    deliverables_overdue: number;
    deliverables_completion_rate: number | null;
  };
  estimated_reach: number | null;
  pending_actions: { kind: string; count: number; label: string }[];
};

export type CampaignReport = {
  campaign: {
    campaign_id: string;
    name: string;
    objective: string;
    status: string;
    start_date: string | null;
    end_date: string | null;
    budget_min: string | null;
    budget_max: string | null;
    currency: string;
    description: string | null;
  };
  generated_at: string;
  saved_opportunities_count: number;
  inquiries: InquiryCounts;
  response_rate: number | null;
  avg_response_hours: number | null;
  recommendation_engagement: SponsorOverviewReport["recommendation_engagement"];
  linked_placements: SponsorOverviewReport["linked_placements"];
  deals: SponsorOverviewReport["deals"];
  estimated_reach: number | null;
  pending_actions: SponsorOverviewReport["pending_actions"];
  top_categories: LabelCount[];
  top_locations: LabelCount[];
};

export async function fetchSponsorOverviewReport(
  sponsorId: string,
): Promise<SponsorOverviewReport> {
  return apiRequest(`/sponsors/workspaces/${sponsorId}/reports/overview`);
}

export async function fetchSponsorCampaignReport(
  sponsorId: string,
  campaignId: string,
): Promise<CampaignReport> {
  return apiRequest(
    `/sponsors/workspaces/${sponsorId}/campaigns/${campaignId}/reports`,
  );
}
