"use client";

import { TicketActionsMenu } from "@/components/tickets/TicketActionsMenu";
import { TicketOfflineBadge } from "@/components/tickets/TicketOfflineBadge";
import { Badge, Button } from "@/components/ui";
import { cn } from "@/lib/cn";
import { formatDate } from "@/lib/format";
import {
  isCancelledLike,
  shortenPublicCode,
  ticketStatusPresentation,
} from "@/lib/tickets/buyer-ticket-groups";
import type { Ticket } from "@/lib/types/commerce";

export function TicketPassCard({
  ticket,
  hostId,
  hostUsername,
  onViewQr,
  onMessageHost,
  onNotice,
  onError,
}: {
  ticket: Ticket;
  hostId?: string | null;
  hostUsername?: string | null;
  onViewQr: (ticket: Ticket) => void;
  onMessageHost?: () => void;
  onNotice?: (message: string) => void;
  onError?: (message: string) => void;
}) {
  const presentation = ticketStatusPresentation(ticket);
  const ready = presentation.statusLabel === "Active";
  const inactive = isCancelledLike(ticket);

  return (
    <article
      className={cn(
        "flex flex-col gap-3 rounded-[var(--radius-lg)] border px-3.5 py-3.5 sm:flex-row sm:items-center sm:justify-between sm:gap-4",
        ready && "border-border bg-card dark:bg-surface-elevated",
        inactive &&
          "border-border/70 bg-muted/50 opacity-90 dark:bg-surface-inset/50",
        !ready &&
          !inactive &&
          "border-border bg-background dark:bg-surface-inset/60",
      )}
    >
      <div className="min-w-0 flex-1 space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <span
            className={cn(
              "text-base font-extrabold tracking-tight",
              inactive
                ? "text-muted-foreground"
                : "text-foreground",
            )}
          >
            {ticket.ticket_type_name || "Ticket"}
          </span>
          <Badge tone={presentation.statusTone} size="sm">
            {presentation.statusLabel}
          </Badge>
          {presentation.readinessLabel && ready ? (
            <Badge tone="success" size="sm">
              {presentation.readinessLabel}
            </Badge>
          ) : presentation.readinessLabel ? (
            <Badge tone={presentation.readinessTone ?? "neutral"} size="sm">
              {presentation.readinessLabel}
            </Badge>
          ) : null}
        </div>

        <div className="space-y-0.5">
          <p className="truncate text-sm text-muted-foreground">
            {ticket.holder_name}
            {ticket.table_label
              ? ` · ${ticket.table_label}${
                  ticket.seat_label ? ` · ${ticket.seat_label}` : ""
                }`
              : ""}
          </p>
          <p className="font-mono text-xs tracking-wide text-muted-foreground">
            {shortenPublicCode(ticket.public_code)}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
          {!inactive ? (
            <span className="hidden sm:inline">{presentation.entryNote}</span>
          ) : null}
          <span className="hidden sm:inline">
            Bought {formatDate(ticket.created_at)}
          </span>
          <TicketOfflineBadge ticketId={ticket.id} />
        </div>

        {inactive ? (
          <p className="text-sm font-medium text-muted-foreground sm:hidden">
            {presentation.entryNote}
          </p>
        ) : null}
      </div>

      <div className="flex shrink-0 flex-row items-center gap-2 sm:flex-col sm:items-stretch">
        {ready ? (
          <Button
            size="md"
            variant="primary"
            className="min-h-11 flex-1 sm:min-h-0 sm:flex-none"
            onClick={() => onViewQr(ticket)}
          >
            View QR
          </Button>
        ) : (
          <Button
            size="sm"
            variant="secondary"
            className="min-h-11 flex-1 sm:min-h-0 sm:flex-none"
            onClick={() => onViewQr(ticket)}
          >
            {inactive ? "View pass" : "View ticket"}
          </Button>
        )}
        <TicketActionsMenu
          ticket={ticket}
          hostId={hostId}
          hostUsername={hostUsername}
          onMessageHost={onMessageHost}
          onCopied={(label) => onNotice?.(label)}
          onError={onError}
        />
      </div>
    </article>
  );
}
