import type { Order, Ticket } from "./types/commerce";
import type { RefundRequest } from "./types/finance";
import type { MerchFulfillment } from "./types/merch";
import type { PassportVisibility } from "./types/passport";
import type { AmbassadorEarningsSummary } from "./types/promos";

type CartLike = {
  items?: Array<{ quantity?: number }> | null;
} | null;

const CLOSED_REFUND = new Set([
  "approved",
  "rejected",
  "paid",
  "closed",
  "cancelled",
  "completed",
  "denied",
]);

/** Tickets that must never appear as Next up. */
const EXCLUDED_NEXT_UP_TICKET = new Set([
  "cancelled",
  "refunded",
  "voided",
  "invalid",
  "expired",
  "transferred",
]);

/** Soon window for emphasizing Open QR on Next up (~48h). */
export const NEXT_UP_QR_SOON_MS = 48 * 60 * 60 * 1000;

function isExcludedNextUpTicket(ticket: Ticket): boolean {
  return EXCLUDED_NEXT_UP_TICKET.has((ticket.status || "").toLowerCase());
}

function isCheckedIn(ticket: Ticket): boolean {
  return (
    (ticket.status || "").toLowerCase() === "checked_in" ||
    Boolean(ticket.checked_in_at)
  );
}

function isEventPast(ticket: Ticket, now: Date): boolean {
  const status = (ticket.event_status || "").toLowerCase();
  if (status === "completed" || status === "cancelled" || status === "archived") {
    return true;
  }
  const end = ticket.event_ends_at || ticket.event_starts_at;
  if (!end) return false;
  const t = new Date(end).getTime();
  return Number.isFinite(t) && t < now.getTime();
}

/** Upcoming active only — not pending, cancelled, refunded, invalid, or past. */
function isUpcomingActive(ticket: Ticket, now: Date): boolean {
  if (
    isExcludedNextUpTicket(ticket) ||
    isCheckedIn(ticket) ||
    isEventPast(ticket, now)
  ) {
    return false;
  }
  return (ticket.status || "").toLowerCase() === "active";
}

/** Soft upcoming for activity chips (excludes cancelled/refunded/invalid/past). */
function isUpcomingSoft(ticket: Ticket, now: Date): boolean {
  if (
    isExcludedNextUpTicket(ticket) ||
    isCheckedIn(ticket) ||
    isEventPast(ticket, now)
  ) {
    return false;
  }
  return true;
}

function compareTicketStarts(a: Ticket, b: Ticket): number {
  const ta = a.event_starts_at ? new Date(a.event_starts_at).getTime() : Infinity;
  const tb = b.event_starts_at ? new Date(b.event_starts_at).getTime() : Infinity;
  return ta - tb;
}

/**
 * Soonest upcoming active ticket.
 * Never returns cancelled / refunded / invalid / expired / transferred / past.
 */
export function pickNextTicket(
  tickets: Ticket[],
  now = new Date(),
): Ticket | null {
  const upcoming = tickets.filter((t) => isUpcomingActive(t, now));
  if (upcoming.length === 0) return null;
  return [...upcoming].sort(compareTicketStarts)[0] ?? null;
}

export function isTicketQrSoon(ticket: Ticket, now = new Date()): boolean {
  if (!isUpcomingActive(ticket, now)) return false;
  const start = ticket.event_starts_at
    ? new Date(ticket.event_starts_at).getTime()
    : NaN;
  if (!Number.isFinite(start)) return true;
  return start - now.getTime() <= NEXT_UP_QR_SOON_MS;
}

/**
 * Location line for Next up — only the API-provided ticket `location_label`.
 * Do not invent street/venue from other fields. Hidden private addresses stay
 * with the ticket/event API; if the label is absent, show nothing.
 */
export function safeTicketLocationLabel(
  ticket: Pick<Ticket, "location_label">,
): string | null {
  const label = (ticket.location_label || "").trim();
  return label || null;
}

function merchDisplayStatus(row: MerchFulfillment): string {
  return (
    (row.display_status || row.status || "").toLowerCase() || "pending_payment"
  );
}

export function pickReadyMerch(
  rows: MerchFulfillment[],
): MerchFulfillment | null {
  return rows.find((row) => merchDisplayStatus(row) === "ready_for_pickup") ?? null;
}

export type NextUpResolution = {
  /** 1 ticket → 2 merch → 3 cart → 4 empty (browse). */
  primary:
    | { kind: "ticket"; ticket: Ticket }
    | { kind: "merch"; merch: MerchFulfillment }
    | { kind: "cart"; cartLines: number; resumePath: string }
    | { kind: "empty" };
  /** Merch pickup reminder when ticket is already the primary next-up. */
  merchReminder: MerchFulfillment | null;
};

type CartResumeLike = CartLike & {
  resume_path?: string | null;
  event_slug?: string | null;
  host_slug?: string | null;
};

/** Prefer event or host checkout over the cart page when resuming a purchase. */
export function resolveCartCheckoutPath(
  cart: CartResumeLike | null | undefined,
): string | null {
  if (!cart) return null;
  const eventSlug = (cart.event_slug || "").trim();
  if (eventSlug) return `/events/${eventSlug}/checkout`;
  const hostSlug = (cart.host_slug || "").trim();
  if (hostSlug) return `/merch/hosts/${hostSlug}/checkout`;
  const explicit = (cart.resume_path || "").trim();
  if (explicit && explicit !== "/dashboard/cart") return explicit;
  return null;
}

/**
 * Next up priority:
 * 1. Upcoming active ticket (soonest)
 * 2. Merch ready for pickup
 * 3. Pending cart / resume checkout
 * 4. Empty → Browse events
 */
export function resolveNextUp(input: {
  tickets: Ticket[];
  merch: MerchFulfillment[];
  cart: CartResumeLike | null | undefined;
  now?: Date;
}): NextUpResolution {
  const now = input.now ?? new Date();
  const ticket = pickNextTicket(input.tickets, now);
  const readyMerch = pickReadyMerch(input.merch);
  const lines = cartLineCount(input.cart);
  const resumePath =
    resolveCartCheckoutPath(input.cart) || "/dashboard/cart";

  if (ticket) {
    return {
      primary: { kind: "ticket", ticket },
      merchReminder: readyMerch,
    };
  }
  if (readyMerch) {
    return {
      primary: { kind: "merch", merch: readyMerch },
      merchReminder: null,
    };
  }
  if (lines > 0) {
    return {
      primary: { kind: "cart", cartLines: lines, resumePath },
      merchReminder: null,
    };
  }
  return { primary: { kind: "empty" }, merchReminder: null };
}

function isMerchInProgress(row: MerchFulfillment): boolean {
  const s = merchDisplayStatus(row);
  if (
    s === "ready_for_pickup" ||
    s === "picked_up" ||
    s === "delivered" ||
    s === "cancelled" ||
    s === "refunded"
  ) {
    return false;
  }
  return [
    "pending_payment",
    "confirmed",
    "awaiting_shipment",
    "shipped",
    "awaiting_pickup",
    "packed",
  ].includes(s);
}

export function cartLineCount(cart: CartLike | undefined): number {
  if (!cart?.items?.length) return 0;
  return cart.items.reduce((sum, line) => sum + (line.quantity || 0), 0);
}

/**
 * Brand-new / no-history home — show welcome CTAs, not a wall of zero cards.
 */
export function isQuietPersonalHome(input: {
  tickets: Ticket[];
  orders: Order[];
  merch: MerchFulfillment[];
  cart: CartLike | null | undefined;
}): boolean {
  return (
    input.tickets.length === 0 &&
    input.orders.length === 0 &&
    input.merch.length === 0 &&
    cartLineCount(input.cart) === 0
  );
}

/** True when My activity has something worth surfacing (not all zeros). */
export function hasAttentionSignals(input: {
  tickets: Ticket[];
  orders: Order[];
  merch: MerchFulfillment[];
  refunds: RefundRequest[];
  cartLines: number;
  now?: Date;
}): boolean {
  const now = input.now ?? new Date();
  if (input.cartLines > 0) return true;
  if (openRefundCount(input.refunds) > 0) return true;
  if (pendingPaymentOrderCount(input.orders) > 0) return true;
  if (input.tickets.some((t) => isUpcomingSoft(t, now))) return true;
  if (
    input.merch.some(
      (row) =>
        merchDisplayStatus(row) === "ready_for_pickup" || isMerchInProgress(row),
    )
  ) {
    return true;
  }
  return false;
}

/** Messages / Connect / Following strip — hide when nothing to show. */
export function shouldShowCommunityStrip(input: {
  unreadMessages: number | null;
  connectPending: number | null;
  followingCount: number | null;
}): boolean {
  if ((input.unreadMessages ?? 0) > 0) return true;
  if ((input.connectPending ?? 0) > 0) return true;
  if ((input.followingCount ?? 0) > 0) return true;
  return false;
}

export function pendingPaymentOrderCount(orders: Order[]): number {
  return orders.filter((order) => {
    const status = (order.status || "").toLowerCase();
    if (status === "pending" || status === "awaiting_payment") return true;
    return (order.payments || []).some((p) =>
      ["pending", "initialized", "abandoned"].includes(
        (p.status || "").toLowerCase(),
      ),
    );
  }).length;
}

export function openRefundCount(refunds: RefundRequest[]): number {
  return refunds.filter(
    (r) => !CLOSED_REFUND.has((r.status || "").toLowerCase()),
  ).length;
}

export function passportVisibilityLabel(
  visibility: PassportVisibility | string | null | undefined,
): string {
  const v = (visibility || "private").toLowerCase();
  if (v === "public") return "Public on /fans";
  if (v === "unlisted") return "Unlisted Passport";
  return "Private Passport";
}

export function shouldShowAmbassadorStrip(
  summary: AmbassadorEarningsSummary | null | undefined,
): boolean {
  if (!summary) return false;
  if ((summary.enrollments_active ?? 0) > 0) return true;
  const payable = Number(summary.payable_earnings ?? 0);
  const estimated = Number(summary.estimated_earnings ?? 0);
  return (
    (Number.isFinite(payable) && payable > 0) ||
    (Number.isFinite(estimated) && estimated > 0)
  );
}

export type ActivityChip = {
  key: string;
  label: string;
  value: string;
  href: string;
  emphasize?: boolean;
};

function plural(count: number, singular: string, pluralForm?: string): string {
  return count === 1 ? singular : pluralForm || `${singular}s`;
}

/** Attention-focused chips — not lifetime totals. Always includes Refunds. */
export function buildActivityChips(input: {
  tickets: Ticket[];
  orders: Order[];
  merch: MerchFulfillment[];
  refunds: RefundRequest[];
  cartLines: number;
  now?: Date;
}): ActivityChip[] {
  const now = input.now ?? new Date();
  const upcoming = input.tickets.filter((t) => isUpcomingSoft(t, now)).length;
  const readyEntry = input.tickets.filter((t) => isUpcomingActive(t, now)).length;
  const readyMerch = input.merch.filter(
    (row) => merchDisplayStatus(row) === "ready_for_pickup",
  ).length;
  const inProgressMerch = input.merch.filter((row) => isMerchInProgress(row)).length;
  const pendingOrders = pendingPaymentOrderCount(input.orders);
  const openRefunds = openRefundCount(input.refunds);

  const ticketValue =
    readyEntry > 0
      ? `${readyEntry} ready for entry`
      : `${upcoming} upcoming ${plural(upcoming, "ticket")}`;

  const orderValue =
    pendingOrders > 0
      ? `${pendingOrders} pending ${plural(pendingOrders, "order")}`
      : "0 pending orders";

  const merchValue =
    readyMerch > 0
      ? `${readyMerch} merch pickup${readyMerch === 1 ? "" : "s"} ready`
      : inProgressMerch > 0
        ? `${inProgressMerch} in progress`
        : "0 pickups ready";

  const chips: ActivityChip[] = [
    {
      key: "tickets",
      label: "Tickets",
      value: ticketValue,
      href: "/dashboard/tickets",
      emphasize: readyEntry > 0 || upcoming > 0,
    },
    {
      key: "orders",
      label: "Orders",
      value: orderValue,
      href: "/dashboard/orders",
      emphasize: pendingOrders > 0,
    },
    {
      key: "merch",
      label: "Merch",
      value: merchValue,
      href: "/dashboard/merchandise",
      emphasize: readyMerch > 0,
    },
    {
      key: "refunds",
      label: "Refunds",
      value: `${openRefunds} open ${plural(openRefunds, "refund")}`,
      href: "/dashboard/refunds",
      emphasize: openRefunds > 0,
    },
  ];

  if (input.cartLines > 0) {
    chips.push({
      key: "cart",
      label: "Cart",
      value: `${input.cartLines} item${input.cartLines === 1 ? "" : "s"} waiting`,
      href: "/dashboard/cart",
      emphasize: true,
    });
  }

  return chips;
}

type ReviewLike = {
  ticket_id: string;
  event_id?: string | null;
  status?: string | null;
};

/**
 * Best checked-in past-event ticket that is not already reviewed.
 * Skips tickets for hosts the viewer **owns** (not team/staff)
 * so owner self-attendance never drives public review prompts.
 * Caller should confirm with `/reviews/eligibility` before prompting.
 */
export function pickReviewPromptTicket(
  tickets: Ticket[],
  reviews: ReviewLike[],
  now = new Date(),
  options?: { excludeHostIds?: Iterable<string> | null },
): Ticket | null {
  const activeReviews = reviews.filter(
    (r) => (r.status || "").toLowerCase() !== "withdrawn",
  );
  const reviewedTickets = new Set(activeReviews.map((r) => r.ticket_id));
  const reviewedEvents = new Set(
    activeReviews.map((r) => r.event_id).filter(Boolean) as string[],
  );
  const excludeHosts = new Set(
    Array.from(options?.excludeHostIds ?? []).filter(Boolean),
  );

  const candidates = tickets.filter((ticket) => {
    if (!isCheckedIn(ticket)) return false;
    if (!isEventPast(ticket, now)) return false;
    if (reviewedTickets.has(ticket.id)) return false;
    if (reviewedEvents.has(ticket.event_id)) return false;
    if (ticket.host_id && excludeHosts.has(ticket.host_id)) return false;
    return true;
  });

  if (candidates.length === 0) return null;
  return [...candidates].sort((a, b) => {
    const ea = a.event_ends_at || a.event_starts_at || "";
    const eb = b.event_ends_at || b.event_starts_at || "";
    return eb.localeCompare(ea);
  })[0] ?? null;
}
