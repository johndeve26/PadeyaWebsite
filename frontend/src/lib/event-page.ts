import type { EventItem, TicketType } from "@/lib/types/events";

export function ticketAvailability(ticket: TicketType): {
  label: string;
  closed: boolean;
} {
  const now = Date.now();
  const status = (ticket.status || "").toLowerCase();
  if (status === "sold_out" || status === "closed") {
    return { label: status === "sold_out" ? "Sold out" : "Closed", closed: true };
  }
  if (ticket.sale_end) {
    const end = new Date(ticket.sale_end).getTime();
    if (Number.isFinite(end) && end < now) {
      return { label: "Online booking closed", closed: true };
    }
  }
  if (ticket.sale_start) {
    const start = new Date(ticket.sale_start).getTime();
    if (Number.isFinite(start) && start > now) {
      return { label: "Sales open soon", closed: true };
    }
  }
  const sold = ticket.quantity_sold ?? 0;
  if (ticket.quantity > 0 && sold >= ticket.quantity) {
    return { label: "Sold out", closed: true };
  }
  return { label: "Available", closed: false };
}

function icsDate(value: string): string {
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "";
  return d
    .toISOString()
    .replace(/[-:]/g, "")
    .replace(/\.\d{3}/, "");
}

export function buildEventIcs(event: EventItem, location: string): string {
  const start = icsDate(event.start_datetime);
  const end = icsDate(event.end_datetime || event.start_datetime);
  const stamp = icsDate(new Date().toISOString());
  const lines = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//Padeya//Event//EN",
    "CALSCALE:GREGORIAN",
    "METHOD:PUBLISH",
    "BEGIN:VEVENT",
    `UID:${event.id}@padeya`,
    `DTSTAMP:${stamp}`,
    `DTSTART:${start}`,
    `DTEND:${end}`,
    `SUMMARY:${escapeIcs(event.title)}`,
    `DESCRIPTION:${escapeIcs(event.short_tagline || event.description.slice(0, 280))}`,
    `LOCATION:${escapeIcs(location)}`,
    "END:VEVENT",
    "END:VCALENDAR",
  ];
  return lines.join("\r\n");
}

function escapeIcs(value: string): string {
  return value
    .replace(/\\/g, "\\\\")
    .replace(/\n/g, "\\n")
    .replace(/,/g, "\\,")
    .replace(/;/g, "\\;");
}

export function downloadEventIcs(event: EventItem, location: string) {
  const blob = new Blob([buildEventIcs(event, location)], {
    type: "text/calendar;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${event.slug || "event"}.ics`;
  a.click();
  URL.revokeObjectURL(url);
}

export async function shareEventPage(event: EventItem): Promise<"shared" | "copied"> {
  const url = typeof window !== "undefined" ? window.location.href : "";
  const title = event.social_share_title || event.title;
  const text = event.social_share_description || event.short_tagline || event.title;
  if (typeof navigator !== "undefined" && navigator.share) {
    await navigator.share({ title, text, url });
    return "shared";
  }
  if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(url);
    return "copied";
  }
  throw new Error("Sharing is not available in this browser.");
}

export function mapsSearchUrl(query: string): string {
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`;
}
