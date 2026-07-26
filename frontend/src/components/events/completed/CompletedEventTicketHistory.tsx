"use client";

import { useState } from "react";

import { Button } from "@/components/ui";
import { formatNgn } from "@/lib/format";
import { historicalTicketsWereLabel } from "@/lib/events/completed-event";
import type { EventItem } from "@/lib/types/events";

import { EventDetailPanel } from "../EventDetailPanel";

type CompletedEventTicketHistoryProps = {
  event: EventItem;
};

/** Informational historical tiers — no selectors or purchase controls. */
export function CompletedEventTicketHistory({
  event,
}: CompletedEventTicketHistoryProps) {
  const tickets = event.ticket_types ?? [];
  const [open, setOpen] = useState(false);
  const were = historicalTicketsWereLabel(tickets.map((t) => t.price));

  if (!tickets.length) return null;

  return (
    <EventDetailPanel title="Original ticket options">
      {were ? (
        <p className="mb-3 text-sm text-muted-foreground">{were}.</p>
      ) : null}
      <p className="text-sm text-muted-foreground">
        Ticket sales for this event have ended. These are historical prices only.
      </p>
      {!open ? (
        <div className="mt-4">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => setOpen(true)}
            aria-expanded={false}
          >
            View original ticket options
          </Button>
        </div>
      ) : (
        <ul className="mt-4 divide-y divide-border rounded-xl border border-border">
          {tickets.map((ticket) => {
            const amount = Number(ticket.price);
            const priceLabel =
              Number.isFinite(amount) && amount === 0
                ? "Free"
                : formatNgn(ticket.price);
            return (
              <li
                key={ticket.id}
                className="flex items-center justify-between gap-4 px-4 py-3"
              >
                <div className="min-w-0">
                  <p className="font-extrabold text-foreground">{ticket.name}</p>
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">
                    {String(ticket.type).replaceAll("_", " ")}
                  </p>
                </div>
                <p className="shrink-0 text-lg font-extrabold text-foreground">
                  {priceLabel}
                </p>
              </li>
            );
          })}
        </ul>
      )}
      {open ? (
        <button
          type="button"
          className="mt-3 text-xs font-semibold text-muted-foreground underline-offset-2 hover:underline"
          onClick={() => setOpen(false)}
          aria-expanded={true}
        >
          Hide ticket options
        </button>
      ) : null}
    </EventDetailPanel>
  );
}
