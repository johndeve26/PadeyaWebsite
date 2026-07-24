import { apiDownload, apiRequest } from "@/lib/api";
import { getApiBaseUrl, getApiPrefix } from "@/lib/api-base";
import type {
  BuyerFeeQuote,
  CheckoutResult,
  Order,
  Payment,
  Ticket,
} from "@/lib/types/commerce";

export type { BuyerFeeQuote };

export type OrderLineInput =
  | { item_kind?: "ticket"; ticket_type_id: string; quantity: number }
  | { item_kind: "merch"; merch_variant_id: string; quantity: number }
  | { item_kind: "bundle"; bundle_id: string; quantity: number };

export type ShippingAddressInput = {
  recipient_name: string;
  phone?: string;
  phone_number?: string;
  line1?: string;
  address_line_1?: string;
  line2?: string | null;
  address_line_2?: string | null;
  city: string;
  state: string;
  country: string;
  postal_code?: string | null;
  notes?: string | null;
  delivery_notes?: string | null;
};

export async function createOrder(body: {
  event_id?: string;
  host_id?: string;
  items: OrderLineInput[];
  promo_code?: string;
  merch_discount_code?: string;
  referral_code?: string;
  referral_source?: "explicit" | "link" | "cookie";
  fulfillment_method?: "pickup" | "shipping";
  shipping_address?: ShippingAddressInput;
  checkout_answers?: {
    question_id: string;
    value: string | string[];
  }[];
  purchase_mode?: "self" | "other" | "group";
  attendee_name?: string;
  attendee_email?: string;
  attendee_phone?: string;
  recipient_name?: string;
  recipient_email?: string;
  recipient_phone?: string;
  gift_message?: string;
  send_ticket_to_recipient?: boolean;
  keep_buyer_copy?: boolean;
  use_same_buyer_details_for_all?: boolean;
  attendees?: {
    ticket_type_id: string;
    unit_index: number;
    attendee_name: string;
    attendee_email: string;
    attendee_phone?: string;
    delivery_email?: string;
    delivery_phone?: string;
  }[];
  guest_buyer_name?: string;
  guest_buyer_email?: string;
  guest_buyer_phone?: string;
}): Promise<Order> {
  return apiRequest<Order>("/orders", { method: "POST", body });
}

export type PaystackConfig = {
  mode: "test" | "live";
  public_key: string | null;
  base_url: string;
};

export async function fetchPaystackConfig(): Promise<PaystackConfig> {
  return apiRequest<PaystackConfig>("/payments/paystack/config", { auth: false });
}

export async function checkCheckoutBuyerEmail(body: {
  email: string;
  event_id: string;
  has_tickets?: boolean;
  has_merch?: boolean;
}): Promise<{ status: "ok" | "existing_account" }> {
  return apiRequest("/checkout/buyer-email/check", {
    method: "POST",
    body,
    auth: false,
  });
}

export async function checkoutOrder(
  orderId: string,
  body?: { payment_email?: string },
): Promise<CheckoutResult> {
  return apiRequest<CheckoutResult>(`/payments/checkout/${orderId}`, {
    method: "POST",
    body: body?.payment_email ? { payment_email: body.payment_email } : undefined,
  });
}

/** Server-side Paystack verify + ticket issuance after inline popup success. */
export async function confirmCheckoutPayment(orderId: string): Promise<Order> {
  return apiRequest<Order>(`/payments/checkout/${orderId}/confirm`, {
    method: "POST",
  });
}

export function isPaystackCompatibleEmail(email: string): boolean {
  const normalized = email.trim().toLowerCase();
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalized)) return false;
  const domain = normalized.split("@")[1] ?? "";
  const blocked = [
    ".test",
    ".invalid",
    ".localhost",
    ".local",
    ".example",
    ".internal",
  ];
  return !blocked.some((suffix) => domain.endsWith(suffix));
}

export async function claimGuestOrder(token: string): Promise<{
  order_id: string;
  reference: string;
  claimed: boolean;
  message: string;
}> {
  return apiRequest("/orders/claim", {
    method: "POST",
    body: { token },
  });
}

export async function startGuestOrderClaim(body: {
  order_reference: string;
  email: string;
}): Promise<{
  status: "sent" | "on_account";
  detail: string;
  order_id: string | null;
}> {
  return apiRequest("/orders/claim/start", {
    method: "POST",
    body,
    auth: false,
  });
}

export async function fetchMyOrders(): Promise<Order[]> {
  return apiRequest<Order[]>("/orders/mine");
}

export const CHECKOUT_BUYER_EMAIL_KEY = "padeya_checkout_buyer_email";

export type OrderReferenceSummary = {
  reference: string;
  status: string;
  pdf_available: boolean;
};

export async function fetchOrderSummaryByReference(
  reference: string,
  email: string,
): Promise<OrderReferenceSummary> {
  const qs = new URLSearchParams({ email: email.trim().toLowerCase() });
  return apiRequest<OrderReferenceSummary>(
    `/orders/reference/${encodeURIComponent(reference)}/summary?${qs.toString()}`,
    { auth: false },
  );
}

function triggerBrowserDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  try {
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    anchor.rel = "noopener";
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
  } finally {
    URL.revokeObjectURL(url);
  }
}

export async function downloadOrderPdfByReference(
  reference: string,
  email: string,
): Promise<string> {
  const response = await fetch(
    `${getApiBaseUrl()}${getApiPrefix()}/orders/reference/${encodeURIComponent(reference)}/pdf`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: email.trim().toLowerCase() }),
    },
  );
  if (!response.ok) {
    let detail = response.statusText || "Download failed";
    try {
      const data = (await response.json()) as { detail?: string };
      if (typeof data.detail === "string") detail = data.detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  const blob = await response.blob();
  const cd = response.headers.get("Content-Disposition") ?? "";
  const match = /filename=\"?([^\";]+)\"?/i.exec(cd);
  const filename = match?.[1] ?? `padeya-order-${reference}.pdf`;
  triggerBrowserDownload(blob, filename);
  return filename;
}

export async function downloadOrderPdf(orderId: string): Promise<string> {
  const { blob, filename } = await apiDownload(`/orders/${orderId}/pdf`, {
    fallbackFilename: "padeya-order.pdf",
  });
  triggerBrowserDownload(blob, filename);
  return filename;
}

export async function fetchOrder(orderId: string): Promise<Order> {
  return apiRequest<Order>(`/orders/${orderId}`);
}

export async function resendOrderTicketEmails(
  orderId: string,
): Promise<{ status: string; detail: string }> {
  return apiRequest(`/orders/${orderId}/resend-ticket-emails`, {
    method: "POST",
  });
}

export async function quoteBuyerFees(body: {
  host_id: string;
  ticket_subtotal?: number;
  merch_subtotal?: number;
  ticket_discount?: number;
  merch_discount?: number;
  shipping_amount?: number;
  currency?: string;
}): Promise<BuyerFeeQuote> {
  return apiRequest<BuyerFeeQuote>("/payments/fee-quote", {
    method: "POST",
    body,
    auth: false,
  });
}

export async function fetchMyTickets(): Promise<Ticket[]> {
  return apiRequest<Ticket[]>("/tickets/mine");
}

export async function fetchTicket(ticketId: string): Promise<Ticket> {
  return apiRequest<Ticket>(`/tickets/${ticketId}`);
}

/** Download ticket PDF pass (static QR). Triggers a browser save. */
export async function downloadTicketPdf(ticketId: string): Promise<string> {
  const { blob, filename } = await apiDownload(`/tickets/${ticketId}/pdf`, {
    fallbackFilename: `padeya-ticket-${ticketId}.pdf`,
  });
  const url = URL.createObjectURL(blob);
  try {
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    anchor.rel = "noopener";
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
  } finally {
    URL.revokeObjectURL(url);
  }
  return filename;
}

export async function fetchAdminOrders(): Promise<Order[]> {
  return apiRequest<Order[]>("/admin/orders");
}

export async function fetchAdminPayments(): Promise<Payment[]> {
  return apiRequest<Payment[]>("/admin/payments");
}
