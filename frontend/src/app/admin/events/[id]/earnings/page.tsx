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
  fetchAdminEventEarnings,
} from "@/lib/finance-api";
import type { HostEarningsReport } from "@/lib/types/finance";

export default function AdminEventEarningsPage() {
  const params = useParams<{ id: string }>();
  const eventId = params.id;
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
    if (!canView || !eventId) return;
    let active = true;
    void (async () => {
      try {
        const data = await fetchAdminEventEarnings(eventId);
        if (active) {
          setReport(data);
          setError(null);
        }
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError
              ? err.detail
              : "Failed to load event earnings",
          );
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [canView, eventId]);

  async function onExport() {
    setExporting(true);
    try {
      await exportAdminEarningsCsv({ eventId });
    } catch {
      setError("CSV export failed");
    } finally {
      setExporting(false);
    }
  }

  if (!canView) {
    return (
      <DashboardShell tone="soft" eyebrow="Admin" title="Event earnings">
        <Alert tone="warning">Finance view permission required.</Alert>
      </DashboardShell>
    );
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title={
        report?.summary.event_title
          ? `Earnings · ${report.summary.event_title}`
          : "Event earnings"
      }
      description="Net host revenue for this event after Pàdéyá deductions."
      actions={
        <div className="flex flex-wrap gap-2">
          <Link href="/admin/finance/earnings">
            <Button size="sm" variant="secondary">
              All earnings
            </Button>
          </Link>
          <Link href={`/admin/events/${eventId}/analytics`}>
            <Button size="sm" variant="ghost">
              Analytics
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
