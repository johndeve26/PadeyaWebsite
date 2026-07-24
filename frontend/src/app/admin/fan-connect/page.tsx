"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  Card,
  SkeletonLoader,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { fetchAdminFanConnectOverview } from "@/lib/fan-connect-api";
import type { FanConnectAdminOverview } from "@/lib/types/fan-connect";

export default function AdminFanConnectPage() {
  const [data, setData] = useState<FanConnectAdminOverview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const overview = await fetchAdminFanConnectOverview();
        if (!active) return;
        setData(overview);
      } catch (err) {
        if (!active) return;
        setError(
          err instanceof ApiError ? err.detail : "Could not load overview.",
        );
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
      title="Fan Connect"
      description="Moderation for opt-in fan↔fan Connect. Private attendance, orders, and payments are never shown. Moderate fan↔fan chat only when a message report exists."
      actions={
        <>
          <Link href="/admin/fan-connect/settings">
            <Button variant="secondary">Settings</Button>
          </Link>
          <Link href="/admin/fan-connect/reports">
            <Button variant="secondary">Reports</Button>
          </Link>
          <Link href="/admin/fan-connect/blocks">
            <Button variant="secondary">Blocks</Button>
          </Link>
          <Link href="/admin/message-reports">
            <Button variant="secondary">Message reports</Button>
          </Link>
        </>
      }
    >
      {loading ? <SkeletonLoader className="h-32" /> : null}
      {error ? <Alert tone="danger">{error}</Alert> : null}
      {data ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {(
            [
              ["Connect enabled", data.connect_enabled_users],
              ["Open reports", data.open_reports ?? 0],
              ["Pending requests", data.pending_requests],
              ["Accepted connections", data.accepted_connections],
              ["Blocked connections", data.blocked_connections],
              ["Fan↔fan threads", data.fan_fan_threads],
              ["Fan Connect reports", data.fan_fan_reports],
              ["Connect blocks", data.message_blocks],
            ] as const
          ).map(([label, value]) => (
            <Card key={label} className="space-y-1 p-5">
              <p className="text-xs font-extrabold uppercase tracking-wide text-muted">
                {label}
              </p>
              <p className="text-2xl font-extrabold text-ink">{value}</p>
            </Card>
          ))}
        </div>
      ) : null}
    </DashboardShell>
  );
}
