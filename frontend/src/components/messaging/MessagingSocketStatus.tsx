"use client";

import type { SocketConnectionStatus } from "@/lib/messaging/socket-types";

/**
 * Subtle live-connection cue — visible but not noisy.
 */
export function MessagingSocketStatus({
  status,
}: {
  status: SocketConnectionStatus;
}) {
  if (status === "connected") {
    return (
      <span
        className="inline-flex items-center gap-1.5 text-[11px] text-muted-foreground"
        title="Live updates on"
      >
        <span className="size-1.5 rounded-full bg-brand-green" aria-hidden />
        <span className="hidden sm:inline">Connected</span>
      </span>
    );
  }

  if (status === "reconnecting") {
    return (
      <span
        className="inline-flex items-center gap-1.5 text-[11px] text-muted-foreground"
        title="Reconnecting"
      >
        <span
          className="size-1.5 animate-pulse rounded-full bg-warning"
          aria-hidden
        />
        Reconnecting…
      </span>
    );
  }

  return (
    <span
      className="inline-flex items-center gap-1.5 text-[11px] text-muted-foreground"
      title="Using periodic sync"
    >
      <span className="size-1.5 rounded-full bg-muted-foreground/50" aria-hidden />
      Offline · syncing
    </span>
  );
}
