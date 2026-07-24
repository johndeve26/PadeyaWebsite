import Link from "next/link";

import { cn } from "@/lib/cn";
import { formatDateTime } from "@/lib/format";

import type { RecentScanRow } from "./scan-result-utils";

function outcomeDot(outcome: string) {
  if (outcome === "success" || outcome === "valid") return "bg-accent";
  if (outcome === "duplicate") return "bg-warning";
  if (outcome === "invalid") return "bg-danger";
  if (outcome === "queued") return "bg-info";
  return "bg-muted-foreground";
}

export function RecentScansStrip({
  rows,
  attendeesHref,
}: {
  rows: RecentScanRow[];
  attendeesHref?: string;
}) {
  if (rows.length === 0) return null;

  return (
    <section className="space-y-2" aria-label="Recent scans">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
          Recent scans
        </h3>
        {attendeesHref ? (
          <Link
            href={attendeesHref}
            className="text-xs font-bold text-accent underline-offset-2 hover:underline"
          >
            Full list
          </Link>
        ) : null}
      </div>
      <ul className="divide-y divide-border overflow-hidden rounded-[var(--radius-md)] border border-border bg-surface-elevated">
        {rows.slice(0, 5).map((row) => (
          <li
            key={row.key}
            className="flex items-center gap-3 px-3 py-2.5 text-sm"
          >
            <span
              className={cn("h-2.5 w-2.5 shrink-0 rounded-full", outcomeDot(row.outcome))}
              aria-hidden
            />
            <div className="min-w-0 flex-1">
              <p className="truncate font-semibold text-foreground">{row.holderName}</p>
              <p className="truncate text-xs text-muted-foreground">
                {row.ticketType} · {formatDateTime(row.at)}
              </p>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
