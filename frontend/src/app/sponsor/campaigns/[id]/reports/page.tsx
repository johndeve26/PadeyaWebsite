"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { useSponsorWorkspace } from "@/components/sponsor/SponsorWorkspaceProvider";
import { SponsorReportDashboard } from "@/components/sponsor/SponsorReportDashboard";
import { Alert, Container, SectionHeader, SkeletonCard } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatNgn } from "@/lib/format";
import {
  fetchSponsorCampaignReport,
  type CampaignReport,
} from "@/lib/sponsor-reports-api";

export default function SponsorCampaignReportsPage() {
  const params = useParams<{ id: string }>();
  const { active } = useSponsorWorkspace();
  const sponsorId = active?.sponsor_id ?? null;
  const campaignId = params.id;

  const [report, setReport] = useState<CampaignReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sponsorId || !campaignId) return;
    void (async () => {
      try {
        setReport(await fetchSponsorCampaignReport(sponsorId, campaignId));
        setError(null);
      } catch (err) {
        setError(err instanceof ApiError ? err.detail : "Failed to load report");
      }
    })();
  }, [campaignId, sponsorId]);

  if (!sponsorId) return null;

  return (
    <Container className="space-y-6 py-6">
      <SectionHeader
        eyebrow="Campaign"
        title={report ? `${report.campaign.name} — Reports` : "Campaign reports"}
        description="Campaign-level funnel and placement summaries. Budget shown only to your sponsor team."
        action={
          <Link href={`/sponsor/campaigns/${campaignId}`}>
            <span className="text-sm font-semibold text-accent underline">
              Campaign detail
            </span>
          </Link>
        }
      />
      {report ? (
        <div className="rounded-xl border border-border bg-muted/40 p-4 text-sm">
          <p className="capitalize">
            Objective: {report.campaign.objective.replace(/_/g, " ")}
          </p>
          <p>
            Dates: {report.campaign.start_date ?? "—"} →{" "}
            {report.campaign.end_date ?? "—"}
          </p>
          {report.campaign.budget_min != null ||
          report.campaign.budget_max != null ? (
            <p>
              Budget:{" "}
              {report.campaign.budget_min != null
                ? formatNgn(Number(report.campaign.budget_min))
                : "—"}{" "}
              –{" "}
              {report.campaign.budget_max != null
                ? formatNgn(Number(report.campaign.budget_max))
                : "—"}
            </p>
          ) : null}
          {report.campaign.description ? (
            <p className="mt-2 text-muted-foreground">{report.campaign.description}</p>
          ) : null}
        </div>
      ) : null}
      {error ? (
        <Alert tone="danger" title="Error">
          {error}
        </Alert>
      ) : null}
      {report ? (
        <SponsorReportDashboard
          report={report}
          campaignLinkPrefix={`/sponsor/campaigns/${campaignId}`}
        />
      ) : !error ? (
        <SkeletonCard />
      ) : null}
    </Container>
  );
}
