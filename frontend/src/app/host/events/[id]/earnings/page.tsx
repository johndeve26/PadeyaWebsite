"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { EarningsReportPanel } from "@/components/finance/EarningsReportPanel";
import { RequireHost } from "@/components/hosts/RequireHost";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { Alert, Button, SkeletonLoader } from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  exportHostEarningsCsv,
  fetchHostEventEarnings,
} from "@/lib/finance-api";
import type { HostEarningsReport } from "@/lib/types/finance";

export default function HostEventEarningsPage() {
  const params = useParams<{ id: string }>();
  const eventId = params.id;
  const [report, setReport] = useState<HostEarningsReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    if (!eventId) return;
    let active = true;
    void (async () => {
      try {
        const data = await fetchHostEventEarnings(eventId);
        if (active) {
          setReport(data);
          setError(null);
        }
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load event earnings",
          );
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [eventId]);

  async function onExport() {
    setExporting(true);
    try {
      await exportHostEarningsCsv(eventId);
    } catch {
      setError("CSV export failed");
    } finally {
      setExporting(false);
    }
  }

  const title = report?.summary.event_title
    ? `Earnings · ${report.summary.event_title}`
    : "Event earnings";

  return (
    <RequireHost>
      <DashboardShell
        tone="soft"
        eyebrow="Finance"
        title={title}
        description="Net revenue for this event after Pàdéyá deductions."
        actions={
          <div className="flex flex-wrap gap-2">
            <Link href="/host/earnings">
              <Button size="sm" variant="secondary">
                All earnings
              </Button>
            </Link>
            <Link href={`/host/events/${eventId}`}>
              <Button size="sm" variant="ghost">
                Event
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
