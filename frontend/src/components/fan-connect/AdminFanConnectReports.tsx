"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  Alert,
  Badge,
  Button,
  EmptyState,
  SkeletonLoader,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  disableAdminFanConnectUser,
  fetchAdminFanConnectReports,
  resolveAdminFanConnectReport,
} from "@/lib/fan-connect-api";
import type { FanConnectAdminReport } from "@/lib/types/fan-connect";
import { formatDate } from "@/lib/format";

function statusTone(
  status: string,
): "warning" | "accent" | "success" | "neutral" {
  if (status === "open") return "warning";
  if (status === "reviewing") return "accent";
  if (status === "resolved") return "success";
  return "neutral";
}

export function AdminFanConnectReports() {
  const [items, setItems] = useState<FanConnectAdminReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const res = await fetchAdminFanConnectReports(
          statusFilter ? { status: statusFilter } : undefined,
        );
        if (!active) return;
        setItems(res.items);
        setError(null);
      } catch (err) {
        if (!active) return;
        setError(
          err instanceof ApiError ? err.detail : "Could not load reports.",
        );
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [tick, statusFilter]);

  async function resolve(
    id: string,
    resolution: "resolved" | "dismissed",
  ) {
    setBusyId(id);
    try {
      await resolveAdminFanConnectReport(id, { resolution });
      setTick((n) => n + 1);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.detail
          : `Could not ${resolution === "resolved" ? "resolve" : "dismiss"}.`,
      );
    } finally {
      setBusyId(null);
    }
  }

  async function disableUser(userId: string, reportId: string) {
    setBusyId(reportId);
    try {
      await disableAdminFanConnectUser(userId, {
        reason: "Disabled from Fan Connect report review",
      });
      setTick((n) => n + 1);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.detail
          : "Could not disable Fan Connect for this user.",
      );
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <label className="text-xs font-bold uppercase tracking-wide text-muted-foreground">
          Status
        </label>
        <select
          className="rounded-[var(--radius-sm)] border border-border bg-surface px-3 py-1.5 text-sm"
          value={statusFilter}
          onChange={(e) => {
            setLoading(true);
            setStatusFilter(e.target.value);
          }}
        >
          <option value="">All</option>
          <option value="open">Open</option>
          <option value="reviewing">Reviewing</option>
          <option value="resolved">Resolved</option>
          <option value="dismissed">Dismissed</option>
        </select>
      </div>

      {loading ? <SkeletonLoader className="h-32" /> : null}
      {error ? <Alert tone="danger">{error}</Alert> : null}
      {!loading && !error && items.length === 0 ? (
        <EmptyState
          title="No Fan Connect reports"
          description="Reports about connections appear here. Thread message moderation stays on Message reports when a fan_fan thread is reported there."
        />
      ) : null}

      {items.length > 0 ? (
        <ul className="divide-y divide-border rounded-[var(--radius-lg)] border border-border bg-card dark:bg-surface-elevated">
          {items.map((row) => {
            const ctx = row.connection_context;
            const open = row.status === "open" || row.status === "reviewing";
            return (
              <li key={row.id} className="space-y-3 px-4 py-4 sm:px-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0 space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-semibold text-heading">{row.reason}</p>
                      <Badge tone={statusTone(row.status)} size="sm">
                        {row.status}
                      </Badge>
                      {row.thread_type === "fan_fan" ? (
                        <Badge tone="accent" size="sm">
                          Fan Connect chat
                        </Badge>
                      ) : null}
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {row.reporter_display_name}
                      {row.reporter_username
                        ? ` (@${row.reporter_username})`
                        : ""}{" "}
                      → {row.reported_display_name}
                      {row.reported_username
                        ? ` (@${row.reported_username})`
                        : ""}
                    </p>
                    {row.details ? (
                      <p className="text-sm text-body">{row.details}</p>
                    ) : null}
                    <p className="text-xs text-muted-foreground">
                      {formatDate(row.created_at)}
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    {open ? (
                      <>
                        <Button
                          size="sm"
                          variant="secondary"
                          disabled={busyId === row.id}
                          onClick={() => void resolve(row.id, "resolved")}
                        >
                          Resolve
                        </Button>
                        <Button
                          size="sm"
                          variant="secondary"
                          disabled={busyId === row.id}
                          onClick={() => void resolve(row.id, "dismissed")}
                        >
                          Dismiss
                        </Button>
                      </>
                    ) : null}
                    {row.reported_connect_enabled ? (
                      <Button
                        size="sm"
                        variant="secondary"
                        disabled={busyId === row.id}
                        onClick={() =>
                          void disableUser(row.reported_user_id, row.id)
                        }
                      >
                        Disable Connect
                      </Button>
                    ) : (
                      <Badge tone="neutral" size="sm">
                        Connect off
                      </Badge>
                    )}
                  </div>
                </div>

                {ctx ? (
                  <div className="rounded-[var(--radius-sm)] border border-border/70 bg-canvas/40 px-3 py-2 text-sm">
                    <p className="text-xs font-extrabold uppercase tracking-wide text-muted-foreground">
                      Connection context
                    </p>
                    <p className="mt-1 text-muted-foreground">
                      Status: {ctx.connection_status || "none"}
                      {ctx.pair_blocked ? " · blocked" : ""}
                    </p>
                    {(ctx.reason_labels || []).length > 0 ? (
                      <ul className="mt-1 list-inside list-disc text-body">
                        {ctx.reason_labels!.map((label) => (
                          <li key={label}>{label}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="mt-1 text-muted-foreground">
                        No safe public reasons on file.
                      </p>
                    )}
                  </div>
                ) : null}

                <div className="flex flex-wrap gap-3 text-sm">
                  {row.message_report_id ? (
                    <Link
                      href={`/admin/message-reports/${row.message_report_id}`}
                      className="font-bold text-foreground underline-offset-2 hover:underline"
                    >
                      Moderate fan↔fan thread
                    </Link>
                  ) : row.thread_id ? (
                    <span className="text-muted-foreground">
                      Thread exists — message moderation opens only after a
                      message report.
                    </span>
                  ) : null}
                  <Link
                    href={`/admin/fan-connect/users/${row.reported_user_id}`}
                    className="font-bold text-foreground underline-offset-2 hover:underline"
                  >
                    Block / report history
                  </Link>
                </div>
              </li>
            );
          })}
        </ul>
      ) : null}
    </div>
  );
}
