import { Badge } from "@/components/ui";
import { cn } from "@/lib/cn";

export function ScannerStatusBar({
  eventTitle,
  subtitle,
  online,
  queued,
  scanCount,
  busy,
  className,
}: {
  eventTitle?: string;
  subtitle: string;
  online: boolean;
  queued: number;
  scanCount: number;
  busy: boolean;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col gap-3 rounded-[var(--radius-lg)] border border-border bg-surface-elevated px-4 py-3 sm:flex-row sm:items-center sm:justify-between",
        className,
      )}
    >
      <div className="min-w-0">
        <p className="text-[11px] font-bold uppercase tracking-[0.12em] text-muted-foreground">
          Door scanner
        </p>
        <p className="truncate text-base font-extrabold tracking-tight text-foreground">
          {eventTitle ?? "Event check-in"}
        </p>
        <p className="mt-0.5 text-sm text-muted-foreground">{subtitle}</p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {online ? (
          <Badge tone="accent">Live</Badge>
        ) : (
          <Badge tone="warning">Offline</Badge>
        )}
        {queued > 0 ? (
          <Badge tone="warning">
            {queued} queued
          </Badge>
        ) : null}
        <Badge tone="neutral">{scanCount} scanned</Badge>
        {busy ? (
          <span className="text-xs font-semibold text-muted-foreground">Processing…</span>
        ) : null}
      </div>
    </div>
  );
}
