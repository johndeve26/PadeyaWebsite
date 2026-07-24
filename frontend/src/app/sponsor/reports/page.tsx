"use client";

import { useEffect, useState } from "react";

import { useSponsorWorkspace } from "@/components/sponsor/SponsorWorkspaceProvider";
import { SponsorReportDashboard } from "@/components/sponsor/SponsorReportDashboard";
import { Alert, Container, SectionHeader, SkeletonCard } from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  fetchSponsorOverviewReport,
  type SponsorOverviewReport,
} from "@/lib/sponsor-reports-api";

export default function SponsorReportsPage() {
  const { active } = useSponsorWorkspace();
  const sponsorId = active?.sponsor_id ?? null;
  const [report, setReport] = useState<SponsorOverviewReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sponsorId) return;
    void (async () => {
      try {
        setReport(await fetchSponsorOverviewReport(sponsorId));
        setError(null);
      } catch (err) {
        setError(err instanceof ApiError ? err.detail : "Failed to load report");
      }
    })();
  }, [sponsorId]);

  if (!sponsorId) return null;

  return (
    <Container className="space-y-6 py-6">
      <SectionHeader
        eyebrow="Analytics"
        title="Reports"
        description="Aggregate sponsor workspace metrics on Pàdéyá — inquiries, campaigns, and saved opportunities. No fan or buyer private data."
      />
      {error ? (
        <Alert tone="danger" title="Error">
          {error}
        </Alert>
      ) : null}
      {report ? (
        <SponsorReportDashboard report={report} />
      ) : !error ? (
        <SkeletonCard />
      ) : null}
    </Container>
  );
}
