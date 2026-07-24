/** Shared checkout purchase-mode types (buyer ≠ attendee allowed). */

export type PurchaseMode = "self" | "other" | "group";

export type AttendeeDraft = {
  ticket_type_id: string;
  unit_index: number;
  ticket_label: string;
  attendee_name: string;
  attendee_email: string;
  attendee_phone: string;
};

export type GiftDelivery = {
  send_ticket_to_recipient: boolean;
  keep_buyer_copy: boolean;
  gift_message: string;
};

export const CHECKOUT_STEPS = [
  { id: "tickets", label: "Tickets" },
  { id: "attendees", label: "Attendees" },
  { id: "details", label: "Details" },
  { id: "review", label: "Review" },
] as const;

export type CheckoutStepId = (typeof CHECKOUT_STEPS)[number]["id"];

export function emptyAttendee(
  ticketTypeId: string,
  unitIndex: number,
  ticketLabel: string,
  prefill?: { name?: string; email?: string },
): AttendeeDraft {
  return {
    ticket_type_id: ticketTypeId,
    unit_index: unitIndex,
    ticket_label: ticketLabel,
    attendee_name: prefill?.name ?? "",
    attendee_email: prefill?.email ?? "",
    attendee_phone: "",
  };
}

export function buildAttendeeSlots(
  selected: { ticket: { id: string; name: string }; quantity: number }[],
  prefill?: { name?: string; email?: string },
): AttendeeDraft[] {
  const rows: AttendeeDraft[] = [];
  for (const row of selected) {
    for (let i = 0; i < row.quantity; i += 1) {
      rows.push(emptyAttendee(row.ticket.id, i, row.ticket.name, prefill));
    }
  }
  return rows;
}

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function validateAttendeeDrafts(
  mode: PurchaseMode,
  drafts: AttendeeDraft[],
  opts: {
    recipientName: string;
    recipientEmail: string;
    useSameForAll: boolean;
    selfName: string;
    selfEmail: string;
  },
): string | null {
  if (mode === "self") {
    if (!opts.selfName.trim() || opts.selfName.trim().length < 2) {
      return "Enter the attendee name on the ticket.";
    }
    if (!EMAIL_RE.test(opts.selfEmail.trim())) {
      return "Enter a valid email for the ticket holder.";
    }
    return null;
  }
  if (mode === "other") {
    if (!opts.recipientName.trim() || opts.recipientName.trim().length < 2) {
      return "Enter the recipient’s full name.";
    }
    if (!EMAIL_RE.test(opts.recipientEmail.trim())) {
      return "Enter a valid recipient email.";
    }
    return null;
  }
  // group
  if (opts.useSameForAll) {
    if (!opts.selfName.trim() || !EMAIL_RE.test(opts.selfEmail.trim())) {
      return "Enter shared attendee name and email for the group.";
    }
    return null;
  }
  if (drafts.length === 0) {
    return "Select tickets before assigning attendees.";
  }
  for (const d of drafts) {
    if (!d.attendee_name.trim() || d.attendee_name.trim().length < 2) {
      return `Enter a name for ${d.ticket_label} #${d.unit_index + 1}.`;
    }
    if (!EMAIL_RE.test(d.attendee_email.trim())) {
      return `Enter a valid email for ${d.ticket_label} #${d.unit_index + 1}.`;
    }
  }
  return null;
}
