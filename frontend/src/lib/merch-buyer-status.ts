/** Buyer-facing merch purchase status labels. */

export type BuyerMerchDisplayStatus =
  | "pending_payment"
  | "confirmed"
  | "ready_for_pickup"
  | "picked_up"
  | "awaiting_shipment"
  | "shipped"
  | "delivered"
  | "cancelled"
  | "refunded";

const LABELS: Record<string, string> = {
  pending_payment: "Pending payment",
  confirmed: "Confirmed",
  ready_for_pickup: "Ready for pickup",
  picked_up: "Picked up",
  awaiting_shipment: "Preparing shipment",
  packed: "Preparing shipment",
  shipped: "Shipped",
  delivered: "Delivered",
  cancelled: "Cancelled",
  refunded: "Refunded",
  // Raw fulfillment statuses as fallback
  awaiting_pickup: "Confirmed",
  collect_at_stand: "Ready for pickup",
  fulfilled: "Picked up",
  pending: "Pending payment",
  failed: "Pending payment",
  paid: "Confirmed",
};

export function buyerMerchStatusLabel(status: string | null | undefined): string {
  if (!status) return "Confirmed";
  const key = status.toLowerCase();
  return LABELS[key] ?? status.replace(/_/g, " ");
}

export function resolveBuyerMerchDisplayStatus(opts: {
  displayStatus?: string | null;
  fulfillmentStatus?: string | null;
  orderStatus?: string | null;
}): string {
  if (opts.displayStatus) return opts.displayStatus;
  const order = (opts.orderStatus || "").toLowerCase();
  const fulfillment = (opts.fulfillmentStatus || "").toLowerCase();
  if (order === "refunded" || fulfillment === "refunded") return "refunded";
  if (fulfillment === "cancelled") return "cancelled";
  if (fulfillment === "delivered") return "delivered";
  if (fulfillment === "shipped") return "shipped";
  if (fulfillment === "awaiting_shipment" || fulfillment === "packed") {
    return "awaiting_shipment";
  }
  if (fulfillment === "fulfilled") return "picked_up";
  if (fulfillment === "collect_at_stand") return "ready_for_pickup";
  if (fulfillment === "awaiting_pickup") return "confirmed";
  if (
    fulfillment === "pending_payment" ||
    order === "pending" ||
    order === "failed"
  ) {
    return "pending_payment";
  }
  return fulfillment || "pending_payment";
}

export function fulfillmentMethodLabel(
  method: string | null | undefined,
): string {
  const key = (method || "pickup").toLowerCase();
  if (key === "shipping") return "Delivery";
  if (key === "print_on_demand") return "Print on demand";
  if (key === "pickup") return "Pickup";
  return key.replace(/_/g, " ");
}
