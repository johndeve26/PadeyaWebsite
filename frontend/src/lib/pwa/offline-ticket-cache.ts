/**
 * Buyer ticket display cache for offline viewing.
 * Validation still happens server-side when scanned — this is display-only.
 * Never use this for Vault content.
 */

import type { Ticket } from "@/lib/types/commerce";

const TICKET_PREFIX = "padeya.ticket.cache.v1.";
const LIST_KEY = "padeya.tickets.list.v1";

function canUseStorage(): boolean {
  return typeof window !== "undefined" && typeof localStorage !== "undefined";
}

export function cacheTicketForOffline(ticket: Ticket): void {
  if (!canUseStorage() || !ticket?.id) return;
  try {
    const payload = {
      cached_at: new Date().toISOString(),
      ticket,
    };
    localStorage.setItem(`${TICKET_PREFIX}${ticket.id}`, JSON.stringify(payload));

    const listRaw = localStorage.getItem(LIST_KEY);
    const list: string[] = listRaw ? (JSON.parse(listRaw) as string[]) : [];
    if (!list.includes(ticket.id)) {
      list.unshift(ticket.id);
      localStorage.setItem(LIST_KEY, JSON.stringify(list.slice(0, 40)));
    }
  } catch {
    // Quota / private mode — ignore
  }
}

export function cacheTicketListForOffline(tickets: Ticket[]): void {
  if (!canUseStorage()) return;
  try {
    localStorage.setItem(
      LIST_KEY,
      JSON.stringify(tickets.map((t) => t.id).slice(0, 40)),
    );
    for (const ticket of tickets) {
      // List endpoint may omit QR — keep existing QR if present
      const existing = readCachedTicket(ticket.id);
      const merged = {
        ...ticket,
        qr_payload: ticket.qr_payload ?? existing?.qr_payload ?? null,
      };
      cacheTicketForOffline(merged);
    }
  } catch {
    // ignore
  }
}

export function readCachedTicket(ticketId: string): Ticket | null {
  if (!canUseStorage()) return null;
  try {
    const raw = localStorage.getItem(`${TICKET_PREFIX}${ticketId}`);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { ticket?: Ticket };
    return parsed.ticket ?? null;
  } catch {
    return null;
  }
}

export function readCachedTicketList(): Ticket[] {
  if (!canUseStorage()) return [];
  try {
    const listRaw = localStorage.getItem(LIST_KEY);
    const ids: string[] = listRaw ? (JSON.parse(listRaw) as string[]) : [];
    return ids
      .map((id) => readCachedTicket(id))
      .filter((t): t is Ticket => Boolean(t));
  } catch {
    return [];
  }
}
