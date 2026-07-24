import Link from "next/link";

import { Button, EmptyState } from "@/components/ui";
import type { TicketDashboardTab } from "@/lib/tickets/buyer-ticket-groups";

const COPY: Record<
  TicketDashboardTab,
  { title: string; description: string; cta: string }
> = {
  upcoming: {
    title: "No active tickets",
    description:
      "When you buy tickets for upcoming events, your QR passes will appear here.",
    cta: "Browse events",
  },
  past: {
    title: "No past tickets",
    description: "Checked-in and past tickets will appear here.",
    cta: "Browse events",
  },
  cancelled: {
    title: "No cancelled or refunded tickets",
    description: "No cancelled or refunded tickets.",
    cta: "Browse events",
  },
  all: {
    title: "No tickets yet",
    description:
      "When you book an event on Pàdéyá, your tickets will appear here.",
    cta: "Browse events",
  },
};

export function TicketEmptyState({ tab }: { tab: TicketDashboardTab }) {
  const copy = COPY[tab];
  return (
    <EmptyState
      title={copy.title}
      description={copy.description}
      action={
        <Link href="/events">
          <Button size="lg">{copy.cta}</Button>
        </Link>
      }
    />
  );
}
