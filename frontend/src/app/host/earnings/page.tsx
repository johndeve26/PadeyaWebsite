"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { EarningsReportPanel } from "@/components/finance/EarningsReportPanel";
import { RequireHost } from "@/components/hosts/RequireHost";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { Alert, Button, SkeletonLoader } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { exportHostEarningsCsv, fetchHostEarnings } from "@/lib/finance-api";
import type { HostEarningsReport } from "@/lib/types/finance";

export default function HostEarningsPage() {
  const [report, setReport] = useState<HostEarningsReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const data = await fetchHostEarnings();
        if (active) {
          setReport(data);
          setError(null);
        }
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load earnings",
          );
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  async function onExport() {
    setExporting(true);
    try {
      await exportHostEarningsCsv();
    } catch {
      setError("CSV export failed");
    } finally {
      setExporting(false);
    }
  }

  return (
    <RequireHost>
      <DashboardShell
        tone="soft"
        eyebrow="Finance"
        title="Earnings"
        description="See what you make after Pàdéyá deductions, refunds, and other host-paid charges."
        actions={
          <div className="flex flex-wrap gap-2">
            <Link href="/host/payouts">
              <Button size="sm" variant="secondary">
                Payouts
              </Button>
            </Link>
            <Link href="/host/analytics">
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
            onExport={() => void onExport()}
            exporting={exporting}
          />
        ) : null}
      </DashboardShell>
    </RequireHost>
  );
}
