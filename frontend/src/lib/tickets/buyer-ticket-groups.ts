import type { Ticket } from "@/lib/types/commerce";

export type TicketDashboardTab =
  | "upcoming"
  | "past"
  | "cancelled"
  | "all";

export type TicketEventGroup = {
  eventId: string;
  eventTitle: string;
  eventSlug: string | null;
  eventCoverUrl: string | null;
  hostId: string | null;
  hostName: string | null;
  hostUsername: string | null;
  startsAt: string | null;
  endsAt: string | null;
  eventStatus: string | null;
  locationLabel: string | null;
  tickets: Ticket[];
};

const CANCELLED_STATUSES = new Set([
  "cancelled",
  "refunded",
  "voided",
  "invalid",
]);

export function isCancelledLike(ticket: Ticket): boolean {
  return CANCELLED_STATUSES.has((ticket.status || "").toLowerCase());
}

export function isEventPast(ticket: Ticket, now = new Date()): boolean {
  const status = (ticket.event_status || "").toLowerCase();
  if (status === "completed" || status === "cancelled" || status === "archived") {
    return true;
  }
  const end = ticket.event_ends_at || ticket.event_starts_at;
  if (!end) return false;
  const t = new Date(end).getTime();
  return Number.isFinite(t) && t < now.getTime();
}

export function isCheckedIn(ticket: Ticket): boolean {
  return (
    (ticket.status || "").toLowerCase() === "checked_in" ||
    Boolean(ticket.checked_in_at)
  );
}

/** Active ticket that can still show QR for an upcoming event. */
export function isActiveQrTicket(ticket: Ticket, now = new Date()): boolean {
  if (isCancelledLike(ticket) || isCheckedIn(ticket) || isEventPast(ticket, now)) {
    return false;
  }
  return (ticket.status || "").toLowerCase() === "active";
}

/** Primary dashboard bucket for a ticket (mutually exclusive). */
export function ticketDashboardBucket(
  ticket: Ticket,
  now = new Date(),
): Exclude<TicketDashboardTab, "all"> {
  if (isCancelledLike(ticket)) return "cancelled";
  if (isCheckedIn(ticket) || isEventPast(ticket, now)) return "past";
  return "upcoming";
}

export function summarizeTickets(tickets: Ticket[], now = new Date()) {
  let upcoming = 0;
  let checkedInOrPast = 0;
  let cancelled = 0;
  for (const ticket of tickets) {
    const bucket = ticketDashboardBucket(ticket, now);
    if (bucket === "upcoming") upcoming += 1;
    else if (bucket === "past") checkedInOrPast += 1;
    else cancelled += 1;
  }
  return {
    upcoming,
    checkedInOrPast,
    cancelled,
    total: tickets.length,
  };
}

export function filterTicketsForTab(
  tickets: Ticket[],
  tab: TicketDashboardTab,
  now = new Date(),
): Ticket[] {
  if (tab === "all") return tickets;
  return tickets.filter((t) => ticketDashboardBucket(t, now) === tab);
}

export function groupTicketsByEvent(tickets: Ticket[]): TicketEventGroup[] {
  const map = new Map<string, TicketEventGroup>();
  for (const ticket of tickets) {
    const key = ticket.event_id;
    let group = map.get(key);
    if (!group) {
      group = {
        eventId: ticket.event_id,
        eventTitle: ticket.event_title || "Event",
        eventSlug: ticket.event_slug ?? null,
        eventCoverUrl: ticket.event_cover_url ?? null,
        hostId: ticket.host_id ?? null,
        hostName: ticket.host_name ?? null,
        hostUsername: ticket.host_username ?? null,
        startsAt: ticket.event_starts_at ?? null,
        endsAt: ticket.event_ends_at ?? null,
        eventStatus: ticket.event_status ?? null,
        locationLabel: ticket.location_label ?? null,
        tickets: [],
      };
      map.set(key, group);
    }
    group.tickets.push(ticket);
  }

  const groups = Array.from(map.values());
  for (const g of groups) {
    g.tickets.sort((a, b) => {
      const aActive = (a.status || "").toLowerCase() === "active" ? 0 : 1;
      const bActive = (b.status || "").toLowerCase() === "active" ? 0 : 1;
      if (aActive !== bActive) return aActive - bActive;
      return (a.ticket_type_name || "").localeCompare(b.ticket_type_name || "");
    });
  }

  groups.sort((a, b) => {
    const aReady = a.tickets.some((t) => isActiveQrTicket(t)) ? 0 : 1;
    const bReady = b.tickets.some((t) => isActiveQrTicket(t)) ? 0 : 1;
    if (aReady !== bReady) return aReady - bReady;
    const aT = a.startsAt ? new Date(a.startsAt).getTime() : 0;
    const bT = b.startsAt ? new Date(b.startsAt).getTime() : 0;
    return aT - bT;
  });

  return groups;
}

export type TicketPrimaryAction = {
  label: string;
  href: string;
  variant: "primary" | "secondary" | "ghost";
  disabled?: boolean;
  /** Visual weight for the row CTA */
  emphasis: "ready" | "neutral" | "inactive";
};

export function ticketPrimaryAction(ticket: Ticket): TicketPrimaryAction {
  const status = (ticket.status || "").toLowerCase();
  const detail = `/dashboard/tickets/${ticket.id}`;

  if (status === "cancelled") {
    return {
      label: "View details",
      href: detail,
      variant: "ghost",
      emphasis: "inactive",
    };
  }
  if (status === "refunded") {
    return {
      label: "View details",
      href: detail,
      variant: "ghost",
      emphasis: "inactive",
    };
  }
  if (status === "voided" || status === "invalid") {
    return {
      label: "QR unavailable",
      href: detail,
      variant: "ghost",
      disabled: true,
      emphasis: "inactive",
    };
  }
  if (status === "checked_in" || ticket.checked_in_at) {
    return {
      label: "View ticket",
      href: detail,
      variant: "secondary",
      emphasis: "neutral",
    };
  }
  if (isEventPast(ticket) && status === "active") {
    return {
      label: "View ticket",
      href: detail,
      variant: "secondary",
      emphasis: "neutral",
    };
  }
  if (status === "active") {
    return {
      label: "View QR",
      href: detail,
      variant: "primary",
      emphasis: "ready",
    };
  }
  return {
    label: "View details",
    href: detail,
    variant: "secondary",
    emphasis: "neutral",
  };
}

export function inactiveStatusLabel(ticket: Ticket): string {
  const status = (ticket.status || "").toLowerCase();
  if (status === "refunded") return "This ticket is no longer valid for entry.";
  if (status === "voided" || status === "invalid") {
    return "This ticket is no longer valid for entry.";
  }
  if (status === "cancelled") return "This ticket is no longer valid for entry.";
  if (isCancelledLike(ticket)) return "This ticket is no longer valid for entry.";
  return "This ticket is no longer valid for entry.";
}

/** Short code for list rows — full code only in QR modal / PDF. */
export function shortenPublicCode(code: string | null | undefined): string {
  const raw = (code || "").trim();
  if (!raw) return "—";
  if (raw.length <= 14) return raw;
  return `${raw.slice(0, 8)}…${raw.slice(-4)}`;
}

export type TicketBadgeTone =
  | "accent"
  | "neutral"
  | "warning"
  | "danger"
  | "outline"
  | "success";

export type TicketStatusPresentation = {
  statusLabel: string;
  readinessLabel: string | null;
  statusTone: TicketBadgeTone;
  readinessTone: TicketBadgeTone | null;
  entryNote: string;
  showQr: boolean;
  canDownloadPdf: boolean;
};

export function ticketStatusPresentation(
  ticket: Ticket,
  now = new Date(),
): TicketStatusPresentation {
  const status = (ticket.status || "").toLowerCase();

  if (status === "refunded") {
    return {
      statusLabel: "Refunded",
      readinessLabel: null,
      statusTone: "neutral",
      readinessTone: null,
      entryNote: "This ticket is no longer valid for entry.",
      showQr: false,
      canDownloadPdf: true,
    };
  }
  if (status === "cancelled" || status === "voided" || status === "invalid") {
    return {
      statusLabel: status === "cancelled" ? "Cancelled" : "Invalid",
      readinessLabel: null,
      statusTone: "neutral",
      readinessTone: null,
      entryNote: "This ticket is no longer valid for entry.",
      showQr: false,
      canDownloadPdf: status === "cancelled",
    };
  }
  if (status === "pending" || status === "reserved") {
    return {
      statusLabel: "Pending confirmation",
      readinessLabel: null,
      statusTone: "warning",
      readinessTone: null,
      entryNote: "Payment not verified — not valid for entry yet.",
      showQr: false,
      canDownloadPdf: true,
    };
  }
  if (isCheckedIn(ticket)) {
    return {
      statusLabel: "Checked in",
      readinessLabel: "Used",
      statusTone: "neutral",
      readinessTone: "outline",
      entryNote: "This ticket has already been used.",
      showQr: true,
      canDownloadPdf: true,
    };
  }
  if (isEventPast(ticket, now)) {
    return {
      statusLabel: "Past event",
      readinessLabel: null,
      statusTone: "neutral",
      readinessTone: null,
      entryNote: "This event has ended.",
      showQr: false,
      canDownloadPdf: true,
    };
  }
  if (status === "active") {
    return {
      statusLabel: "Active",
      readinessLabel: "Ready for entry",
      statusTone: "accent",
      readinessTone: "success",
      entryNote: "QR ready for check-in",
      showQr: true,
      canDownloadPdf: true,
    };
  }
  return {
    statusLabel: status.replace(/_/g, " ") || "Ticket",
    readinessLabel: null,
    statusTone: "neutral",
    readinessTone: null,
    entryNote: "Open ticket details for status.",
    showQr: false,
    canDownloadPdf: true,
  };
}

export function groupCheckedInCount(group: TicketEventGroup): number {
  return group.tickets.filter((t) => isCheckedIn(t)).length;
}

export function groupReadyCount(group: TicketEventGroup): number {
  return group.tickets.filter((t) => isActiveQrTicket(t)).length;
}
