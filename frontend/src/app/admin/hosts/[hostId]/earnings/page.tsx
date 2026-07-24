"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { EarningsReportPanel } from "@/components/finance/EarningsReportPanel";
import { useAuth } from "@/components/auth/AuthProvider";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { Alert, Button, SkeletonLoader } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { userHasPermission } from "@/lib/auth/permissions";
import {
  exportAdminEarningsCsv,
  fetchAdminHostEarnings,
} from "@/lib/finance-api";
import type { HostEarningsReport } from "@/lib/types/finance";

export default function AdminHostEarningsPage() {
  const params = useParams<{ hostId: string }>();
  const hostId = params.hostId;
  const { user } = useAuth();
  const canView = userHasPermission(
    user,
    "payments.view",
    "payouts.review",
    "admin.finance.view_fees",
    "admin.full_access",
  );
  const [report, setReport] = useState<HostEarningsReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    if (!canView || !hostId) return;
    let active = true;
    void (async () => {
      try {
        const data = await fetchAdminHostEarnings(hostId);
        if (active) {
          setReport(data);
          setError(null);
        }
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load host earnings",
          );
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [canView, hostId]);

  async function onExport() {
    setExporting(true);
    try {
      await exportAdminEarningsCsv({ hostId });
    } catch {
      setError("CSV export failed");
    } finally {
      setExporting(false);
    }
  }

  if (!canView) {
    return (
      <DashboardShell tone="soft" eyebrow="Admin" title="Host earnings">
        <Alert tone="warning">Finance view permission required.</Alert>
      </DashboardShell>
    );
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title={
        report?.summary.host_display_name
          ? `Earnings · ${report.summary.host_display_name}`
          : "Host earnings"
      }
      description="Gross, Pàdéyá deductions, and net for this host."
      actions={
        <div className="flex flex-wrap gap-2">
          <Link href="/admin/finance/earnings">
            <Button size="sm" variant="secondary">
              All earnings
            </Button>
          </Link>
          <Link href={`/admin/hosts/${hostId}/fees`}>
            <Button size="sm" variant="ghost">
              Fee overrides
            </Button>
          </Link>
        </div>
      }
    >
      {error ? <Alert tone="danger">{error}</Alert> : null}
      {!report && !error ? <SkeletonLoader lines={8} /> : null}
      {report ? (
        <EarningsReportPanel
          report={report}
          showHostLinks={false}
          onExport={() => void onExport()}
          exporting={exporting}
        />
      ) : null}
    </DashboardShell>
  );
}
