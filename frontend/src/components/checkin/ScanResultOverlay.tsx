"use client";

import { Button } from "@/components/ui";
import type { ScanResult } from "@/lib/checkin-api";
import { cn } from "@/lib/cn";
import { formatDateTime } from "@/lib/format";

import { describeScanResult } from "./scan-result-utils";

export function ScanResultOverlay({
  result,
  queuedCount,
  onContinue,
  onManualSearch,
  onViewDetails,
}: {
  result: ScanResult | null;
  queuedCount?: number;
  onContinue: () => void;
  onManualSearch?: () => void;
  onViewDetails?: () => void;
}) {
  if (!result) return null;

  const display = describeScanResult(result);
  const ticket = result.ticket;

  const bg =
    display.tone === "success"
      ? "border-accent bg-[color-mix(in_srgb,var(--brand-green)_18%,var(--surface))]"
      : display.tone === "warning"
        ? "border-warning bg-warning-surface/50"
        : display.tone === "danger"
          ? "border-danger bg-danger-surface/55"
          : display.tone === "info"
            ? "border-info bg-info-surface/40"
            : "border-border bg-muted";

  return (
    <div
      role="alert"
      aria-live="assertive"
      className={cn("overflow-hidden rounded-[var(--radius-lg)] border-2 p-4 sm:p-5", bg)}
    >
      <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-muted-foreground">
        Scan result
      </p>
      <p
        className={cn(
          "mt-1 text-3xl font-black tracking-tight sm:text-4xl",
          display.tone === "success" && "text-accent",
          display.tone === "warning" && "text-warning-foreground",
          display.tone === "danger" && "text-danger-foreground",
          display.tone === "info" && "text-info-foreground",
        )}
      >
        {display.headline}
      </p>
      <p className="mt-1 text-sm font-semibold text-foreground">{display.subline}</p>
      {display.invalidReason ? (
        <p className="mt-2 text-sm text-muted-foreground">Reason: {display.invalidReason}</p>
      ) : null}
      {result.outcome === "queued" && queuedCount != null ? (
        <p className="mt-2 text-sm font-medium text-foreground">
          Buffer: {queuedCount} scan(s) waiting to sync
        </p>
      ) : null}

      {ticket ? (
        <dl className="mt-4 grid gap-2 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
              Guest
            </dt>
            <dd className="font-bold text-foreground">{ticket.holder_name ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
              Ticket type
            </dt>
            <dd className="font-bold text-foreground">{ticket.ticket_type_name ?? "—"}</dd>
          </div>
          {ticket.public_code ? (
            <div>
              <dt className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
                Ticket code
              </dt>
              <dd className="font-mono font-bold tracking-wide text-foreground">
                {ticket.public_code}
              </dd>
            </div>
          ) : null}
          {(result.checked_in_at || ticket.checked_in_at) && (
            <div>
              <dt className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
                {result.outcome === "duplicate" ? "Previous check-in" : "Check-in time"}
              </dt>
              <dd className="font-bold text-foreground">
                {formatDateTime(result.checked_in_at ?? ticket.checked_in_at ?? "")}
              </dd>
            </div>
          )}
        </dl>
      ) : null}

      <div className="mt-4 flex flex-wrap gap-2">
        <Button size="lg" className="min-h-11 flex-1 sm:flex-none" onClick={onContinue}>
          Continue scanning
        </Button>
        {result.outcome === "duplicate" && onViewDetails ? (
          <Button size="lg" variant="secondary" onClick={onViewDetails}>
            View details
          </Button>
        ) : null}
        {(result.outcome === "invalid" || display.tone === "warning") && onManualSearch ? (
          <Button size="lg" variant="secondary" onClick={onManualSearch}>
            Manual search
          </Button>
        ) : null}
      </div>
    </div>
  );
}
