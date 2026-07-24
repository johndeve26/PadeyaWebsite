"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AdminAISummaryPanel } from "@/components/admin/AdminAISummaryPanel";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Card,
  EmptyState,
  SkeletonLoader,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { fetchAdminMessageReports } from "@/lib/messaging-api";
import type { AdminMessageReport } from "@/lib/types/messaging";
import { formatDate } from "@/lib/format";

function statusTone(
  status: string,
): "warning" | "accent" | "success" | "neutral" {
  if (status === "open") return "warning";
  if (status === "reviewing") return "accent";
  if (status === "resolved") return "success";
  return "neutral";
}

export default function AdminMessageReportsPage() {
  const [items, setItems] = useState<AdminMessageReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const res = await fetchAdminMessageReports();
        if (!active) return;
        setItems(res.items);
      } catch (err) {
        if (!active) return;
        setError(err instanceof ApiError ? err.detail : "Failed to load reports");
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title="Message reports"
      description="Moderate reported conversations. Emails, phones, and payment data are never shown."
    >
      {error ? (
        <Alert tone="danger" title="Could not load">
          {error}
        </Alert>
      ) : null}

      <AdminAISummaryPanel
        feature="admin.reports.summary"
        title="Reports AI summary"
        generateLabel="Summarize reports"
        links={[
          { href: "/admin/reviews", label: "Review reports" },
          { href: "/admin/fan-connect/reports", label: "Fan Connect reports" },
        ]}
      />

      {loading ? <SkeletonLoader lines={5} /> : null}
      {!loading && items.length === 0 ? (
        <EmptyState
          title="No message reports"
          description="Reported conversations will appear here for review."
        />
      ) : null}
      <ul className="space-y-3">
        {items.map((r) => (
          <li key={r.id}>
            <Card className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div className="space-y-1">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="font-extrabold text-foreground">{r.reason}</p>
                  <Badge tone={statusTone(r.status)} size="sm">
                    {r.status}
                  </Badge>
                  {r.thread_type === "fan_fan" ? (
                    <Badge tone="accent" size="sm">
                      Fan Connect
                    </Badge>
                  ) : null}
                </div>
                <p className="text-sm text-muted-foreground">
                  {r.reporter_display_name} → {r.reported_display_name}
                  {r.host_display_name ? ` · Host: ${r.host_display_name}` : ""}
                </p>
                <p className="line-clamp-1 text-sm text-body">
                  {r.message_preview || "No preview"}
                </p>
                <p className="text-xs text-muted-foreground">
                  {formatDate(r.created_at)}
                </p>
              </div>
              <Link
                href={`/admin/message-reports/${r.id}`}
                className="text-sm font-bold text-foreground underline-offset-2 hover:underline"
              >
                Review
              </Link>
            </Card>
          </li>
        ))}
      </ul>
    </DashboardShell>
  );
}
