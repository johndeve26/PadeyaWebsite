"use client";

import { Button } from "@/components/ui";
import { formatNgn } from "@/lib/format";
import type { TicketType } from "@/lib/types/events";

type Props = {
  tickets: TicketType[];
  quantities: Record<string, number>;
  onQuantityChange: (ticketId: string, quantity: number, ticket: TicketType) => void;
};

function availableLabel(ticket: TicketType): string | null {
  const qty = Number(ticket.quantity ?? 0);
  const sold = Number(ticket.quantity_sold ?? 0);
  const reserved = Number(ticket.quantity_reserved ?? 0);
  const left = Math.max(0, qty - sold - reserved);
  if (left <= 0) return "Sold out";
  if (left <= 5) return `Only ${left} left`;
  return null;
}

export function CheckoutTicketSelector({
  tickets,
  quantities,
  onQuantityChange,
}: Props) {
  if (tickets.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No tickets on sale. You can still add event merch if available.
      </p>
    );
  }

  return (
    <ul className="divide-y divide-border">
      {tickets.map((ticket) => {
        const qty = quantities[ticket.id] ?? 0;
        const max = Number(ticket.max_per_order ?? 10);
        const price = Number(ticket.price);
        const free = price <= 0;
        const inventory = availableLabel(ticket);
        const soldOut = inventory === "Sold out";
        const typeLabel = String(ticket.type || "regular").replace(/_/g, " ");
        const vipHint =
          /vip|table|group/i.test(ticket.name) ||
          /vip|table|group/i.test(typeLabel)
            ? typeLabel
            : null;

        return (
          <li
            key={ticket.id}
            className="flex flex-col gap-3 py-4 first:pt-0 last:pb-0 sm:flex-row sm:items-center sm:justify-between"
          >
            <div className="min-w-0 space-y-1">
              <p className="font-bold text-foreground">{ticket.name}</p>
              <p className="text-sm text-muted-foreground">
                {free ? "Free" : formatNgn(ticket.price)}
                {vipHint ? ` · ${vipHint}` : ""}
              </p>
              {ticket.description ? (
                <p className="text-xs leading-relaxed text-muted-foreground">
                  {ticket.description}
                </p>
              ) : null}
              {inventory ? (
                <p
                  className={
                    soldOut
                      ? "text-xs font-medium text-destructive"
                      : "text-xs font-medium text-muted-foreground"
                  }
                >
                  {inventory}
                </p>
              ) : null}
            </div>
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                className="h-11 w-11 shrink-0 px-0 text-lg"
                disabled={soldOut || qty <= 0}
                aria-label={`Decrease ${ticket.name}`}
                onClick={() =>
                  onQuantityChange(ticket.id, Math.max(0, qty - 1), ticket)
                }
              >
                −
              </Button>
              <span className="min-w-[2.5rem] text-center text-base font-extrabold tabular-nums text-foreground">
                {qty}
              </span>
              <Button
                type="button"
                variant="secondary"
                size="sm"
                className="h-11 w-11 shrink-0 px-0 text-lg"
                disabled={soldOut || qty >= max}
                aria-label={`Increase ${ticket.name}`}
                onClick={() =>
                  onQuantityChange(ticket.id, Math.min(max, qty + 1), ticket)
                }
              >
                +
              </Button>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
