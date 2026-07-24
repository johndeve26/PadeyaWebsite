import { apiRequest } from "@/lib/api";
import type { Ticket } from "@/lib/types/commerce";
import type {
  OfflineSyncResult,
  TableReservation,
  TicketTransfer,
  TicketTransferActivity,
} from "@/lib/types/advanced-tickets";

export async function transferTicket(
  ticketId: string,
  body: { to_email: string; to_name: string; note?: string },
): Promise<TicketTransfer> {
  return apiRequest<TicketTransfer>(`/tickets/${ticketId}/transfer`, {
    method: "POST",
    body,
  });
}

export async function claimTransferredTicket(token: string): Promise<Ticket> {
  return apiRequest<Ticket>("/tickets/claim", {
    method: "POST",
    body: { token },
  });
}

/** Claim a pending transfer while logged in as the recipient (no email token needed). */
export async function claimTicketTransferById(transferId: string): Promise<Ticket> {
  return apiRequest<Ticket>(`/tickets/transfers/${transferId}/claim`, {
    method: "POST",
    body: {},
  });
}

export async function cancelTicket(
  ticketId: string,
  body: { password: string; reason?: string },
): Promise<Ticket> {
  return apiRequest<Ticket>(`/tickets/${ticketId}/cancel`, {
    method: "POST",
    body,
  });
}

export async function setTicketQrMode(
  ticketId: string,
  qr_mode: "static" | "rotating",
): Promise<Ticket> {
  return apiRequest<Ticket>(`/tickets/${ticketId}/qr-mode`, {
    method: "POST",
    body: { qr_mode },
  });
}

export async function bindTicketDevice(
  ticketId: string,
  device_fingerprint: string,
): Promise<Ticket> {
  return apiRequest<Ticket>(`/tickets/${ticketId}/bind-device`, {
    method: "POST",
    body: { device_fingerprint },
  });
}

export async function fetchTicketTransfers(ticketId: string): Promise<TicketTransfer[]> {
  return apiRequest<TicketTransfer[]>(`/tickets/${ticketId}/transfers`);
}

export async function fetchMyTicketTransfers(): Promise<TicketTransferActivity[]> {
  return apiRequest<TicketTransferActivity[]>("/tickets/transfers/mine");
}

export async function revokeTicketTransfer(
  transferId: string,
): Promise<TicketTransferActivity> {
  return apiRequest<TicketTransferActivity>(`/tickets/transfers/${transferId}/revoke`, {
    method: "POST",
    body: {},
  });
}

export async function declineTicketTransfer(
  transferId: string,
): Promise<TicketTransferActivity> {
  return apiRequest<TicketTransferActivity>(
    `/tickets/transfers/${transferId}/decline`,
    { method: "POST", body: {} },
  );
}

export async function resendTicketTransferInvite(
  transferId: string,
): Promise<TicketTransferActivity> {
  return apiRequest<TicketTransferActivity>(
    `/tickets/transfers/${transferId}/resend-invite`,
    { method: "POST", body: {} },
  );
}

/** Fresh claim URL for a pending transfer (does not send email). */
export async function fetchTicketTransferClaimLink(
  transferId: string,
): Promise<TicketTransferActivity> {
  return apiRequest<TicketTransferActivity>(
    `/tickets/transfers/${transferId}/claim-link`,
    { method: "POST", body: {} },
  );
}

export async function fetchEventTransfers(eventId: string): Promise<TicketTransfer[]> {
  return apiRequest<TicketTransfer[]>(`/tickets/events/${eventId}/transfers`);
}

export async function fetchEventTables(eventId: string): Promise<TableReservation[]> {
  return apiRequest<TableReservation[]>(`/tickets/events/${eventId}/tables`);
}

export async function createEventTable(
  eventId: string,
  body: { table_label: string; capacity: number; seat_label?: string },
): Promise<TableReservation> {
  return apiRequest<TableReservation>(`/tickets/events/${eventId}/tables`, {
    method: "POST",
    body,
  });
}

export async function assignEventTable(
  reservationId: string,
  body: { ticket_id?: string; seat_label?: string },
): Promise<TableReservation> {
  return apiRequest<TableReservation>(`/tickets/tables/${reservationId}/assign`, {
    method: "PATCH",
    body,
  });
}

export async function cancelEventTable(
  reservationId: string,
): Promise<TableReservation> {
  return apiRequest<TableReservation>(
    `/tickets/tables/${reservationId}/cancel`,
    { method: "POST" },
  );
}

export async function fetchAdminTickets(): Promise<Ticket[]> {
  return apiRequest<Ticket[]>("/tickets/admin/list");
}

export async function fetchAdminTransfers(): Promise<TicketTransfer[]> {
  return apiRequest<TicketTransfer[]>("/tickets/admin/transfers");
}

/** @deprecated Prefer `exportAdminEventBuyers` from `@/lib/admin-event-buyers-api`. */
export async function exportAdminEventBuyersCsv(eventId: string): Promise<void> {
  const { exportAdminEventBuyers } = await import("@/lib/admin-event-buyers-api");
  await exportAdminEventBuyers(eventId, { format: "csv" });
}

export async function syncOfflineScans(body: {
  event_id: string;
  client_batch_id: string;
  device_label?: string;
  scans: {
    client_scan_id: string;
    qr_payload?: string;
    public_code?: string;
    scanned_at?: string;
  }[];
}): Promise<OfflineSyncResult> {
  return apiRequest<OfflineSyncResult>("/checkins/offline/sync", {
    method: "POST",
    body,
  });
}
