import {
  buyerMerchStatusLabel,
  fulfillmentMethodLabel,
  resolveBuyerMerchDisplayStatus,
} from "@/lib/merch-buyer-status";
import type { MerchFulfillment } from "@/lib/types/merch";

export type MerchWalletTab =
  | "ready"
  | "shipping"
  | "completed"
  | "cancelled"
  | "all";

export type MerchBadgeTone =
  | "accent"
  | "neutral"
  | "warning"
  | "danger"
  | "outline"
  | "success";

/** Short code for list rows — full code only in QR modal. */
export function shortenMerchCode(
  code: string | null | undefined,
  opts?: { head?: number; tail?: number },
): string {
  const raw = (code || "").trim();
  if (!raw) return "—";
  const head = opts?.head ?? 8;
  const tail = opts?.tail ?? 4;
  if (raw.length <= head + tail + 1) return raw;
  return `${raw.slice(0, head)}…${raw.slice(-tail)}`;
}

export function merchDisplayStatus(row: MerchFulfillment): string {
  return resolveBuyerMerchDisplayStatus({
    displayStatus: row.display_status,
    fulfillmentStatus: row.status,
    orderStatus: row.order_status,
  });
}

export function isMerchCancelledLike(row: MerchFulfillment): boolean {
  const s = merchDisplayStatus(row);
  return s === "cancelled" || s === "refunded";
}

export function isMerchReadyPickup(row: MerchFulfillment): boolean {
  return merchDisplayStatus(row) === "ready_for_pickup";
}

export function isMerchCompleted(row: MerchFulfillment): boolean {
  const s = merchDisplayStatus(row);
  return s === "picked_up" || s === "delivered";
}

export function isMerchShippingLike(row: MerchFulfillment): boolean {
  const method = (row.fulfillment_method || "pickup").toLowerCase();
  return (
    method === "shipping" ||
    method === "delivery" ||
    method === "print_on_demand"
  );
}

/** Active non-ready items: shipping in flight + confirmed/pending pickup. */
export function isMerchInProgress(row: MerchFulfillment): boolean {
  if (isMerchCancelledLike(row) || isMerchCompleted(row) || isMerchReadyPickup(row)) {
    return false;
  }
  const s = merchDisplayStatus(row);
  return (
    s === "pending_payment" ||
    s === "confirmed" ||
    s === "awaiting_shipment" ||
    s === "shipped" ||
    s === "awaiting_pickup" ||
    s === "packed"
  );
}

export function merchWalletBucket(
  row: MerchFulfillment,
): Exclude<MerchWalletTab, "all"> {
  if (isMerchCancelledLike(row)) return "cancelled";
  if (isMerchReadyPickup(row)) return "ready";
  if (isMerchCompleted(row)) return "completed";
  return "shipping";
}

export function summarizeMerchWallet(rows: MerchFulfillment[]) {
  let ready = 0;
  let inProgress = 0;
  let completed = 0;
  let cancelled = 0;
  for (const row of rows) {
    const bucket = merchWalletBucket(row);
    if (bucket === "ready") ready += 1;
    else if (bucket === "shipping") inProgress += 1;
    else if (bucket === "completed") completed += 1;
    else cancelled += 1;
  }
  return {
    ready,
    inProgress,
    completed,
    cancelled,
    total: rows.length,
  };
}

export function filterMerchForTab(
  rows: MerchFulfillment[],
  tab: MerchWalletTab,
): MerchFulfillment[] {
  if (tab === "all") return rows;
  return rows.filter((r) => merchWalletBucket(r) === tab);
}

export type MerchPrimaryAction = {
  label: string;
  kind: "pickup_qr" | "track" | "order" | "pay";
  emphasis: "ready" | "neutral" | "inactive";
};

export function merchPrimaryAction(row: MerchFulfillment): MerchPrimaryAction {
  const status = merchDisplayStatus(row);
  if (status === "pending_payment") {
    return { label: "View order", kind: "pay", emphasis: "neutral" };
  }
  if (isMerchCancelledLike(row)) {
    return { label: "View order", kind: "order", emphasis: "inactive" };
  }
  if (isMerchReadyPickup(row)) {
    return { label: "View pickup QR", kind: "pickup_qr", emphasis: "ready" };
  }
  if (isMerchShippingLike(row) && !isMerchCompleted(row)) {
    return { label: "Track delivery", kind: "track", emphasis: "neutral" };
  }
  if (
    (row.fulfillment_method || "pickup").toLowerCase() === "pickup" &&
    !isMerchCompleted(row) &&
    status !== "pending_payment"
  ) {
    // Confirmed / awaiting — still allow opening pass
    return { label: "View pickup QR", kind: "pickup_qr", emphasis: "neutral" };
  }
  return { label: "View order", kind: "order", emphasis: "neutral" };
}

export type MerchStatusPresentation = {
  fulfillmentLabel: string;
  fulfillmentTone: MerchBadgeTone;
  paymentLabel: string | null;
  paymentTone: MerchBadgeTone | null;
  invalidCopy: string | null;
  showPickupQr: boolean;
};

export function merchStatusPresentation(
  row: MerchFulfillment,
): MerchStatusPresentation {
  const status = merchDisplayStatus(row);
  const order = (row.order_status || "").toLowerCase();
  const paid = order === "paid";

  if (status === "refunded") {
    return {
      fulfillmentLabel: "Refunded",
      fulfillmentTone: "neutral",
      paymentLabel: "Refunded",
      paymentTone: "neutral",
      invalidCopy: "This item is no longer available for pickup.",
      showPickupQr: false,
    };
  }
  if (status === "cancelled") {
    return {
      fulfillmentLabel: "Cancelled",
      fulfillmentTone: "neutral",
      paymentLabel: paid ? "Order paid" : null,
      paymentTone: paid ? "success" : null,
      invalidCopy: "This item is no longer available for pickup.",
      showPickupQr: false,
    };
  }
  if (status === "pending_payment") {
    return {
      fulfillmentLabel: "Payment pending",
      fulfillmentTone: "warning",
      paymentLabel: "Payment pending",
      paymentTone: "warning",
      invalidCopy: null,
      showPickupQr: false,
    };
  }
  if (status === "ready_for_pickup") {
    return {
      fulfillmentLabel: "Ready for pickup",
      fulfillmentTone: "success",
      paymentLabel: paid ? "Order paid" : null,
      paymentTone: paid ? "success" : null,
      invalidCopy: null,
      showPickupQr: true,
    };
  }
  if (status === "picked_up") {
    return {
      fulfillmentLabel: "Picked up",
      fulfillmentTone: "neutral",
      paymentLabel: paid ? "Order paid" : null,
      paymentTone: paid ? "success" : null,
      invalidCopy: null,
      showPickupQr: false,
    };
  }
  if (status === "delivered") {
    return {
      fulfillmentLabel: "Delivered",
      fulfillmentTone: "neutral",
      paymentLabel: paid ? "Order paid" : null,
      paymentTone: paid ? "success" : null,
      invalidCopy: null,
      showPickupQr: false,
    };
  }
  if (status === "shipped") {
    return {
      fulfillmentLabel: "Shipped",
      fulfillmentTone: "outline",
      paymentLabel: paid ? "Order paid" : null,
      paymentTone: paid ? "success" : null,
      invalidCopy: null,
      showPickupQr: false,
    };
  }
  if (status === "awaiting_shipment" || status === "packed") {
    return {
      fulfillmentLabel: "Processing",
      fulfillmentTone: "outline",
      paymentLabel: paid ? "Order paid" : null,
      paymentTone: paid ? "success" : null,
      invalidCopy: null,
      showPickupQr: false,
    };
  }

  return {
    fulfillmentLabel: buyerMerchStatusLabel(status),
    fulfillmentTone: "outline",
    paymentLabel: paid ? "Order paid" : order ? "Payment pending" : null,
    paymentTone: paid ? "success" : order ? "warning" : null,
    invalidCopy: null,
    showPickupQr:
      (row.fulfillment_method || "pickup").toLowerCase() === "pickup" &&
      Boolean(row.pickup_code) &&
      paid,
  };
}

export type TimelineStep = {
  id: string;
  label: string;
  done: boolean;
  current: boolean;
};

export function merchOrderTimeline(row: MerchFulfillment): TimelineStep[] {
  const status = merchDisplayStatus(row);
  const paid =
    (row.order_status || "").toLowerCase() === "paid" ||
    !["pending", "failed", "pending_payment"].includes(
      (row.order_status || "").toLowerCase(),
    );
  const method = (row.fulfillment_method || "pickup").toLowerCase();
  const shipping = method === "shipping" || method === "delivery" || method === "print_on_demand";

  if (isMerchCancelledLike(row)) {
    return [
      { id: "paid", label: "Order paid", done: paid, current: false },
      {
        id: "end",
        label: status === "refunded" ? "Refunded" : "Cancelled",
        done: true,
        current: true,
      },
    ];
  }

  if (shipping) {
    const steps = [
      { id: "paid", label: "Order paid" },
      { id: "processing", label: "Processing" },
      { id: "shipped", label: "Shipped" },
      { id: "delivered", label: "Delivered" },
    ];
    let idx = 0;
    if (status === "delivered") idx = 3;
    else if (status === "shipped") idx = 2;
    else if (
      status === "awaiting_shipment" ||
      status === "packed" ||
      status === "confirmed"
    ) {
      idx = 1;
    } else if (paid) idx = 0;
    return steps.map((s, i) => ({
      id: s.id,
      label: s.label,
      done: i <= idx,
      current: i === idx,
    }));
  }

  // Pickup
  const steps = [
    { id: "paid", label: "Order paid" },
    { id: "code", label: "Pickup code generated" },
    { id: "ready", label: "Ready for pickup" },
    { id: "picked", label: "Picked up" },
  ];
  let idx = 0;
  if (status === "picked_up") idx = 3;
  else if (status === "ready_for_pickup") idx = 2;
  else if (paid && row.pickup_code) idx = 1;
  else if (paid) idx = 0;
  return steps.map((s, i) => ({
    id: s.id,
    label: s.label,
    done: i <= idx,
    current: i === idx,
  }));
}

export { fulfillmentMethodLabel, buyerMerchStatusLabel };
