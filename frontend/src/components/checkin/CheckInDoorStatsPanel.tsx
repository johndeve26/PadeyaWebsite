"use client";

import { useEffect, useState } from "react";

import { Alert, SkeletonLoader } from "@/components/ui";
import { fetchCheckInStats, type CheckInStats } from "@/lib/checkin-api";
import { cn } from "@/lib/cn";
import { formatDateTime } from "@/lib/format";

import type { RecentScanRow } from "./scan-result-utils";

function DoorStatTile({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-[var(--radius-md)] border border-border bg-surface-elevated px-3 py-2.5",
        "shadow-[var(--shadow-soft)]",
      )}
    >
      <p className="text-[11px] font-extrabold uppercase tracking-[0.08em] text-foreground">
        {label}
      </p>
      <p className="mt-1 text-2xl font-extrabold tabular-nums leading-none tracking-tight text-foreground">
        {value}
      </p>
      {detail ? (
        <p className="mt-1 text-[10px] font-medium leading-snug text-muted-foreground">
          {detail}
        </p>
      ) : null}
    </div>
  );
}

export function CheckInDoorStatsPanel({
  eventId,
  scanCount,
  queued,
  lastScan,
}: {
  eventId: string;
  scanCount: number;
  queued: number;
  lastScan: RecentScanRow | null;
}) {
  const [stats, setStats] = useState<CheckInStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void fetchCheckInStats(eventId)
      .then((data) => {
        if (active) setStats(data);
      })
      .catch((err) => {
        if (active) setError(err instanceof Error ? err.message : "Could not load stats");
      });
    return () => {
      active = false;
    };
  }, [eventId]);

  if (error) {
    return (
      <Alert tone="danger" title="Door stats">
        {error}
      </Alert>
    );
  }

  if (!stats) {
    return <SkeletonLoader lines={3} />;
  }

  const rate =
    stats.total_tickets > 0
      ? Math.round((stats.checked_in / stats.total_tickets) * 100)
      : 0;

  return (
    <div className="space-y-3">
      <div className="rounded-[var(--radius-lg)] border border-border bg-surface-elevated p-3">
        <p className="text-[11px] font-extrabold uppercase tracking-[0.08em] text-foreground">
          Check-in progress
        </p>
        <div className="mt-2 flex flex-wrap items-end justify-between gap-2">
          <p className="text-3xl font-extrabold tabular-nums text-accent">{rate}%</p>
          <p className="text-sm font-semibold text-foreground">
            {stats.remaining.toLocaleString()} remaining
          </p>
        </div>
        <p className="mt-1 text-xs text-muted-foreground">
          {stats.checked_in.toLocaleString()} checked in of {stats.total_tickets.toLocaleString()}{" "}
          tickets sold
        </p>
        <div
          className="mt-2 h-2 overflow-hidden rounded-full bg-muted"
          role="progressbar"
          aria-valuenow={stats.checked_in}
          aria-valuemin={0}
          aria-valuemax={stats.total_tickets}
          aria-label="Check-in progress"
        >
          <div
            className="h-full rounded-full bg-accent transition-all"
            style={{ width: `${Math.min(100, rate)}%` }}
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <DoorStatTile label="Checked in" value={stats.checked_in.toLocaleString()} />
        <DoorStatTile label="Remaining" value={stats.remaining.toLocaleString()} />
        <DoorStatTile
          label="This session"
          value={scanCount.toLocaleString()}
          detail="Scans on this device"
        />
        <DoorStatTile label="Duplicate scans" value={stats.duplicate_scans.toLocaleString()} />
        <DoorStatTile label="Invalid scans" value={stats.invalid_scans.toLocaleString()} />
        <DoorStatTile label="Offline buffer" value={queued.toLocaleString()} />
      </div>

      {lastScan ? (
        <p className="text-sm text-muted-foreground">
          Last scan:{" "}
          <span className="font-semibold text-foreground">{lastScan.holderName}</span> ·{" "}
          {formatDateTime(lastScan.at)}
        </p>
      ) : null}
    </div>
  );
}
