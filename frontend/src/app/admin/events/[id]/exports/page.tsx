"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { AdminEventBuyersNav } from "@/components/admin/AdminEventBuyersNav";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  Card,
  EmptyState,
  SectionHeader,
  SkeletonLoader,
} from "@/components/ui";
import {
  fetchAdminEventBuyerExports,
  type AdminEventBuyerExportLog,
} from "@/lib/admin-event-buyers-api";
import { ApiError } from "@/lib/api";
import { fetchEventById } from "@/lib/events-api";
import { formatDateTime } from "@/lib/format";
import type { EventItem } from "@/lib/types/events";

export default function AdminEventExportsPage() {
  const params = useParams<{ id: string }>();
  const [event, setEvent] = useState<EventItem | null>(null);
  const [logs, setLogs] = useState<AdminEventBuyerExportLog[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadLogs = useCallback(async () => {
    const rows = await fetchAdminEventBuyerExports(params.id);
    setLogs(rows);
  }, [params.id]);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const [row] = await Promise.all([
          fetchEventById(params.id),
          loadLogs(),
        ]);
        if (active) setEvent(row);
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load exports",
          );
          setLogs([]);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [params.id, loadLogs]);

  return (
    <DashboardShell
      tone="soft"
      compact
      eyebrow="Admin"
      title={event ? `${event.title} · Exports` : "Event exports"}
      description="Audit history for buyer exports. Start a new export from Buyers or Attendees (modes, reason, and filters)."
      actions={
        <Link href={`/admin/events/${params.id}/buyers`}>
          <Button size="sm">Open buyers</Button>
        </Link>
      }
    >
      <AdminEventBuyersNav eventId={params.id} />

      {error ? (
        <Alert tone="danger" title="Something went wrong">
          {error}
        </Alert>
      ) : null}

      <Card className="space-y-4">
        <SectionHeader
          title="Export history"
          description="Every successful download is audited with mode, format, filters, row count, and reason when required."
        />
        {logs === null ? (
          <SkeletonLoader lines={4} />
        ) : logs.length === 0 ? (
          <EmptyState
            title="No exports yet"
            description="Downloads appear here after an admin exports buyers."
          />
        ) : (
          <ul className="m-0 divide-y divide-border rounded-[var(--radius-md)] border border-border p-0">
            {logs.map((log) => (
              <li
                key={log.id}
                className="flex flex-wrap items-start justify-between gap-3 px-4 py-3"
              >
                <div className="min-w-0 space-y-1">
                  <p className="font-semibold text-foreground">
                    {log.actor_name || "Admin"}
                    {log.actor_email ? (
                      <span className="font-normal text-muted-foreground">
                        {" "}
                        · {log.actor_email}
                      </span>
                    ) : null}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {log.action}
                    {" · "}
                    {(log.export_mode ||
                      log.details?.export_mode ||
                      "operations")}
                    {" · "}
                    {(
                      log.format ||
                      log.details?.format ||
                      "csv"
                    ).toUpperCase()}
                    {(log.row_count ?? log.details?.row_count) != null
                      ? ` · ${log.row_count ?? log.details?.row_count} rows`
                      : ""}
                    {log.reason || log.details?.reason
                      ? ` · reason: ${log.reason || log.details?.reason}`
                      : ""}
                  </p>
                </div>
                <p className="shrink-0 text-xs tabular-nums text-muted-foreground">
                  {log.created_at ? formatDateTime(log.created_at) : "—"}
                </p>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </DashboardShell>
  );
}
