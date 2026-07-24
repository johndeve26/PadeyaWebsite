/** Human-readable Vault lock reasons and CTAs for public UI. */

import { formatNgn } from "@/lib/format";

export function formatAccessType(accessType: string | null | undefined): string {
  if (!accessType) return "Exclusive";
  return accessType.replace(/_/g, " ");
}

export function vaultCtaLabel(item: {
  locked?: boolean;
  expired?: boolean;
  cta_label?: string | null;
  access_type?: string | null;
  access?: { access_type?: string | null } | null;
}): string {
  if (item.cta_label) return item.cta_label;
  if (item.expired) return "Expired";
  if (!item.locked) return "Open";
  const type = item.access_type || item.access?.access_type;
  if (type === "one_time_unlock") return "Unlock";
  if (type === "invite_only") return "Enter code";
  if (type === "followers_only") return "Follow to unlock";
  if (
    type === "ticket_holder_only" ||
    type === "checked_in_attendee_only" ||
    type === "vip_ticket_holder_only"
  ) {
    return "Unlock with ticket";
  }
  return "View";
}

/** Canonical locked-state messages for the public item page. */
export function vaultLockMessage(item: {
  locked?: boolean;
  expired?: boolean;
  lock_reason?: string | null;
  access_reason?: string | null;
  price?: string | number | null;
  access?: {
    access_type?: string | null;
    price?: string | number | null;
  } | null;
}): string {
  if (item.expired) return "This drop has expired.";

  const type = item.access?.access_type;
  const price = item.access?.price ?? item.price;

  switch (type) {
    case "followers_only":
      return "Follow this host to unlock.";
    case "ticket_holder_only":
      return "Buy a ticket to this event to unlock.";
    case "checked_in_attendee_only":
      return "Checked-in attendees only.";
    case "vip_ticket_holder_only":
      return "VIP ticket holders only.";
    case "one_time_unlock":
      return `Unlock this drop for ${formatNgn(price)}.`;
    case "invite_only":
      return "Invite-only drop.";
    default:
      break;
  }

  if (item.lock_reason) return item.lock_reason;
  if (item.access_reason) {
    const reason = item.access_reason;
    if (reason === "followers_only") return "Follow this host to unlock.";
    if (reason === "ticket_required") {
      return "Buy a ticket to this event to unlock.";
    }
    if (reason === "check_in_required") return "Checked-in attendees only.";
    if (reason === "vip_ticket_required") return "VIP ticket holders only.";
    if (reason === "purchase_required") {
      return `Unlock this drop for ${formatNgn(price)}.`;
    }
    if (reason === "invite_only") return "Invite-only drop.";
    return reason.replace(/_/g, " ");
  }
  return "Access required to view full content.";
}
