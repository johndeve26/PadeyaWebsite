import { cn } from "@/lib/cn";

export function CheckInCompactHeader({
  eventTitle,
  scannerLine,
  online,
  cameraReady,
  showCameraStatus = true,
  queued,
  scanCount,
  className,
}: {
  eventTitle?: string;
  scannerLine: string;
  online: boolean;
  cameraReady: boolean;
  showCameraStatus?: boolean;
  queued: number;
  scanCount: number;
  className?: string;
}) {
  return (
    <header
      className={cn(
        "space-y-2 rounded-[var(--radius-lg)] border border-border bg-surface-elevated px-3 py-2.5 sm:px-4",
        className,
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-accent">
            Check-in
          </p>
          <h1 className="truncate text-base font-extrabold tracking-tight text-foreground sm:text-lg">
            {eventTitle ?? "Event scanner"}
          </h1>
          <p className="truncate text-xs text-muted-foreground">{scannerLine}</p>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1 text-right">
          <span
            className={cn(
              "inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide",
              online ? "bg-accent/15 text-accent" : "bg-warning-surface text-warning-foreground",
            )}
          >
            <span
              className={cn(
                "h-1.5 w-1.5 rounded-full",
                online ? "bg-accent animate-pulse" : "bg-warning",
              )}
              aria-hidden
            />
            {online ? "Live" : "Offline"}
          </span>
          <span className="text-xs font-bold text-foreground">{scanCount} scanned</span>
        </div>
      </div>
      <div className="flex flex-wrap gap-x-3 gap-y-1 text-[11px] font-semibold text-muted-foreground">
        <span>{online ? "Online" : "Offline · scans queue locally"}</span>
        {showCameraStatus ? (
          <>
            <span aria-hidden>·</span>
            <span>{cameraReady ? "Camera ready" : "Camera starting…"}</span>
          </>
        ) : null}
        {queued > 0 ? (
          <>
            <span aria-hidden>·</span>
            <span className="text-warning-foreground">{queued} in buffer</span>
          </>
        ) : null}
      </div>
    </header>
  );
}
