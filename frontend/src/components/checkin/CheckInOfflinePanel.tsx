"use client";

import Link from "next/link";

import { Alert, Button } from "@/components/ui";
import { loadScannerQueue } from "@/lib/pwa/offline-scanner-queue";
import { formatDateTime } from "@/lib/format";

export function CheckInOfflinePanel({
  eventId,
  variant,
  online,
  queued,
  lastSyncAt,
  busy,
  onSync,
}: {
  eventId: string;
  variant: "host" | "staff";
  online: boolean;
  queued: number;
  lastSyncAt: string | null;
  busy: boolean;
  onSync: () => void;
}) {
  const queue = loadScannerQueue(eventId);
  const hostBase = `/host/events/${eventId}`;

  return (
    <div className="space-y-4">
      <Alert tone={online ? "info" : "warning"} title={online ? "Online" : "Offline mode"}>
        {online
          ? "Scans validate with the server in real time."
          : "Scans will be saved and synced when connection returns."}
      </Alert>

      <div className="rounded-[var(--radius-lg)] border border-border bg-surface-elevated p-4">
        <p className="text-sm font-bold text-foreground">{queued} scan(s) in buffer</p>
        {lastSyncAt ? (
          <p className="mt-1 text-xs text-muted-foreground">
            Last sync {formatDateTime(lastSyncAt)}
          </p>
        ) : (
          <p className="mt-1 text-xs text-muted-foreground">Not synced this session yet</p>
        )}
        {online && queued > 0 ? (
          <Button className="mt-3" disabled={busy} onClick={onSync}>
            Sync now
          </Button>
        ) : null}
      </div>

      {queue.length > 0 ? (
        <ul className="space-y-2 text-sm text-muted-foreground">
          {queue.slice(0, 8).map((item) => (
            <li key={item.client_scan_id} className="font-mono text-xs">
              {item.public_code ?? "QR scan"} · {formatDateTime(item.scanned_at)}
            </li>
          ))}
        </ul>
      ) : null}

      {variant === "host" ? (
        <Link href={`${hostBase}/offline-check-in`}>
          <Button variant="secondary" size="sm">
            Open full offline buffer
          </Button>
        </Link>
      ) : null}
    </div>
  );
}
