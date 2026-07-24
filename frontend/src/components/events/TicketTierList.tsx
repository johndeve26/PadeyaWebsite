"use client";

import { TrackImpression } from "@/components/analytics/TrackImpression";
import { EmptyState } from "@/components/ui";
import { cn } from "@/lib/cn";
import { ticketAvailability } from "@/lib/event-page";
import { formatNgn } from "@/lib/format";
import type { EventItem, TicketType } from "@/lib/types/events";
import { trackTicketTypeImpression } from "@/lib/analytics";

function benefitLines(value: string): string[] {
  return value
    .split(/[\n;•]+/)
    .map((line) => line.trim())
    .filter(Boolean);
}

export function TicketTierList({ event }: { event: EventItem }) {
  const tickets = event.ticket_types ?? [];
  if (!tickets.length) {
    return (
      <EmptyState
        title="Tickets coming soon"
        description="This host has not published ticket types yet."
      />
    );
  }

  return (
    <ul className="space-y-3">
      {tickets.map((ticket) => (
        <TicketTierCard
          key={ticket.id}
          ticket={ticket}
          eventId={event.id}
          hostId={event.host_id}
        />
      ))}
    </ul>
  );
}

function TicketTierCard({
  ticket,
  eventId,
  hostId,
}: {
  ticket: TicketType;
  eventId: string;
  hostId: string;
}) {
  const avail = ticketAvailability(ticket);
  const amount = Number(ticket.price);
  const priceLabel =
    Number.isFinite(amount) && amount === 0 ? "Free" : formatNgn(ticket.price);
  const benefits = ticket.benefits ? benefitLines(ticket.benefits) : [];

  return (
    <TrackImpression
      as="li"
      targetEventId={eventId}
      hostId={hostId}
      listContext="event_detail"
      trackCardImpression={false}
      className={cn(
        "rounded-[var(--radius-xl)] border border-border bg-surface-muted p-4 shadow-[var(--shadow-soft)] sm:p-5",
        "dark:border-border-strong/40 dark:bg-surface-inset",
        avail.closed && "opacity-80",
      )}
      onImpression={() => {
        trackTicketTypeImpression({
          targetEventId: eventId,
          hostId,
          ticketTypeId: ticket.id,
          ticketTypeName: ticket.name,
          ticketPrice: ticket.price,
        });
      }}
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 flex-1 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-lg font-extrabold tracking-tight text-foreground">
              {ticket.name}
            </h3>
            <span
              className={cn(
                "rounded-[var(--radius-sm)] px-2 py-0.5 text-[10px] font-extrabold uppercase tracking-wide",
                avail.closed
                  ? "bg-danger/10 text-danger"
                  : "bg-primary/15 text-primary",
              )}
            >
              {avail.label}
            </span>
          </div>
          <p className="text-[11px] font-bold uppercase tracking-[0.12em] text-muted-foreground">
            {String(ticket.type).replaceAll("_", " ")}
          </p>
          {ticket.description ? (
            <p className="text-sm leading-relaxed text-muted-foreground">
              {ticket.description}
            </p>
          ) : null}
          {benefits.length ? (
            <ul className="mt-1 space-y-1 text-sm text-foreground">
              {benefits.slice(0, 4).map((line) => (
                <li key={line} className="flex gap-2">
                  <span className="text-accent" aria-hidden>
                    ✓
                  </span>
                  <span>{line}</span>
                </li>
              ))}
            </ul>
          ) : null}
          {ticket.table_perks ? (
            <p className="text-sm text-muted-foreground">
              <span className="font-semibold text-foreground">Table: </span>
              {ticket.table_perks}
            </p>
          ) : null}
        </div>
        <div className="shrink-0 text-right">
          <p className="text-2xl font-extrabold tracking-tight text-foreground">
            {priceLabel}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            {ticket.seats_per_unit && ticket.seats_per_unit > 1
              ? `${ticket.seats_per_unit} seats / unit`
              : "Per ticket"}
          </p>
        </div>
      </div>
    </TrackImpression>
  );
}
