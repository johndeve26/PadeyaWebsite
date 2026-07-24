import { Card } from "@/components/ui";
import type { ScanResult } from "@/lib/checkin-api";
import { cn } from "@/lib/cn";
import { formatDateTime } from "@/lib/format";

const outcomeMeta: Record<
  string,
  { label: string; hint: string; tone: "success" | "warning" | "danger" | "neutral" }
> = {
  success: {
    label: "Checked in",
    hint: "Guest may enter",
    tone: "success",
  },
  valid: {
    label: "Valid ticket",
    hint: "Ready for entry",
    tone: "success",
  },
  duplicate: {
    label: "Already scanned",
    hint: "This ticket was used before",
    tone: "warning",
  },
  invalid: {
    label: "Not accepted",
    hint: "Do not admit — check with box office",
    tone: "danger",
  },
  queued: {
    label: "Saved offline",
    hint: "Will sync when you reconnect",
    tone: "neutral",
  },
};

function OutcomeIcon({ tone }: { tone: "success" | "warning" | "danger" | "neutral" }) {
  const paths = {
    success: "M5 13l4 4L19 7",
    warning: "M12 9v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
    danger: "M6 18L18 6M6 6l12 12",
    neutral: "M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z",
  };
  return (
    <span
      className={cn(
        "flex h-14 w-14 shrink-0 items-center justify-center rounded-full border-2 sm:h-16 sm:w-16",
        tone === "success" && "border-accent bg-accent/15 text-accent",
        tone === "warning" && "border-warning bg-warning-surface text-warning-foreground",
        tone === "danger" && "border-danger bg-danger-surface text-danger-foreground",
        tone === "neutral" && "border-border bg-muted text-muted-foreground",
      )}
      aria-hidden
    >
      <svg viewBox="0 0 24 24" className="h-7 w-7 sm:h-8 sm:w-8" fill="none" stroke="currentColor" strokeWidth="2.5">
        <path d={paths[tone]} strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </span>
  );
}

export function ScanResultCard({ result }: { result: ScanResult | null }) {
  if (!result) {
    return (
      <Card
        variant="muted"
        className="flex flex-col items-center gap-2 border-dashed py-8 text-center sm:py-10"
      >
        <OutcomeIcon tone="neutral" />
        <p className="text-lg font-extrabold tracking-tight text-foreground">Ready to scan</p>
        <p className="max-w-md text-sm text-muted-foreground">
          Aim the camera at a ticket QR. You will see a large green or red result here for the
          door team.
        </p>
      </Card>
    );
  }

  const meta = outcomeMeta[result.outcome] ?? {
    label: result.outcome,
    hint: "",
    tone: "neutral" as const,
  };

  return (
    <Card
      className={cn(
        "overflow-hidden border-2 p-0",
        meta.tone === "success" &&
          "border-accent bg-[color-mix(in_srgb,var(--brand-green)_12%,var(--surface))]",
        meta.tone === "warning" && "border-warning bg-warning-surface/40",
        meta.tone === "danger" && "border-danger bg-danger-surface/50",
        meta.tone === "neutral" && "border-border bg-muted/40",
      )}
      role="status"
      aria-live="polite"
    >
      <div className="flex flex-col gap-4 p-4 sm:flex-row sm:items-start sm:gap-5 sm:p-6">
        <OutcomeIcon tone={meta.tone} />
        <div className="min-w-0 flex-1 space-y-2">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
              Scan result
            </p>
            <p
              className={cn(
                "text-2xl font-extrabold tracking-tight sm:text-3xl",
                meta.tone === "success" && "text-foreground",
                meta.tone === "warning" && "text-warning-foreground",
                meta.tone === "danger" && "text-danger-foreground",
                meta.tone === "neutral" && "text-foreground",
              )}
            >
              {meta.label}
            </p>
            {meta.hint ? (
              <p className="mt-1 text-sm font-semibold text-muted-foreground">{meta.hint}</p>
            ) : null}
          </div>
          <p className="text-base font-medium leading-snug text-foreground">{result.message}</p>
          {result.scanner_name ? (
            <p className="text-xs text-muted-foreground">Scanner · {result.scanner_name}</p>
          ) : null}
        </div>
      </div>

      {result.ticket ? (
        <div className="grid gap-px border-t border-border bg-border sm:grid-cols-2">
          {[
            { label: "Guest", value: result.ticket.holder_name ?? "—" },
            { label: "Ticket type", value: result.ticket.ticket_type_name ?? "—" },
            { label: "Code", value: result.ticket.public_code ?? "—", mono: true },
            ...(result.checked_in_at || result.ticket.checked_in_at
              ? [
                  {
                    label: "Checked in",
                    value: formatDateTime(
                      result.checked_in_at ?? result.ticket.checked_in_at ?? "",
                    ),
                  },
                ]
              : []),
          ].map((row) => (
            <div key={row.label} className="bg-surface-elevated px-4 py-3">
              <p className="text-[11px] font-bold uppercase tracking-[0.1em] text-muted-foreground">
                {row.label}
              </p>
              <p
                className={cn(
                  "mt-0.5 text-base font-bold text-foreground",
                  "mono" in row && row.mono && "font-mono tracking-wide",
                )}
              >
                {row.value}
              </p>
            </div>
          ))}
        </div>
      ) : null}
    </Card>
  );
}
