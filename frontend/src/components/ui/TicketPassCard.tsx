import Link from "next/link";

import { cn } from "@/lib/cn";
import {
  shortenPublicCode,
  ticketPrimaryAction,
  ticketStatusPresentation,
} from "@/lib/tickets/buyer-ticket-groups";
import type { Ticket } from "@/lib/types/commerce";

import { Badge } from "./Badge";
import { Button } from "./Button";

/** Compact pass link card (shared UI). Prefer dashboard TicketPassCard for wallet rows. */
export function TicketPassCard({
  ticket,
  className = "",
}: {
  ticket: Ticket;
  className?: string;
}) {
  const action = ticketPrimaryAction(ticket);
  const presentation = ticketStatusPresentation(ticket);
  const inactive = action.emphasis === "inactive";
  const ready = action.emphasis === "ready";

  return (
    <Link href={action.href} className={cn("group block", className)}>
      <article className="padeya-card-hover overflow-hidden rounded-[var(--radius-xl)] border border-border bg-card shadow-[var(--shadow-soft)] dark:bg-surface-elevated">
        <div className="flex flex-col sm:flex-row">
          <div
            className={cn(
              "relative flex min-h-[132px] flex-1 flex-col justify-between px-5 py-5 sm:max-w-[58%]",
              ready && "bg-ink text-paper",
              inactive && "bg-muted text-foreground",
              !ready && !inactive && "bg-muted text-foreground",
            )}
          >
            <div className="space-y-2.5">
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone={presentation.statusTone} size="sm">
                  {presentation.statusLabel}
                </Badge>
                <Badge
                  tone="outline"
                  className={ready ? "border-paper/25 text-paper/80" : undefined}
                >
                  {ticket.ticket_type_name || "Ticket"}
                </Badge>
              </div>
              <h3 className="text-xl font-extrabold tracking-tight sm:text-2xl">
                {ticket.event_title ?? "Event"}
              </h3>
              <p
                className={cn(
                  "font-mono text-sm tracking-wide",
                  ready ? "text-primary" : "text-muted-foreground",
                )}
              >
                {shortenPublicCode(ticket.public_code)}
              </p>
            </div>
            <p
              className={cn(
                "mt-4 text-xs font-bold uppercase tracking-[0.12em]",
                ready ? "text-paper/65" : "text-muted-foreground",
              )}
            >
              Pàdéyá ticket
            </p>
          </div>
          <div className="flex flex-1 flex-col justify-between gap-4 border-t border-border px-5 py-5 sm:border-l sm:border-t-0">
            <p className="text-sm leading-relaxed text-muted-foreground">
              {presentation.entryNote}
            </p>
            <Button
              size="lg"
              variant={action.variant}
              className="w-full pointer-events-none sm:w-auto"
            >
              {action.label}
            </Button>
          </div>
        </div>
      </article>
    </Link>
  );
}
