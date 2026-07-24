/**
 * Client-only draft cart for public event merch browsing.
 * Hydrates checkout add-on quantities — never invents paid state.
 */

export type MerchDraftCartLine = {
  productId: string;
  variantId: string;
  productName: string;
  variantLabel: string;
  unitPrice: number;
  quantity: number;
  imageUrl?: string | null;
  productType?: string | null;
};

export type MerchDraftCart = {
  eventId: string;
  eventSlug: string;
  lines: MerchDraftCartLine[];
  updatedAt: string;
};

const KEY_PREFIX = "padeya.merch.draft.";

function storageKey(eventId: string) {
  return `${KEY_PREFIX}${eventId}`;
}

function canUseStorage() {
  return typeof window !== "undefined" && typeof sessionStorage !== "undefined";
}

export function readMerchDraftCart(eventId: string): MerchDraftCart | null {
  if (!canUseStorage() || !eventId) return null;
  try {
    const raw = sessionStorage.getItem(storageKey(eventId));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as MerchDraftCart;
    if (!parsed || parsed.eventId !== eventId || !Array.isArray(parsed.lines)) {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

export function writeMerchDraftCart(cart: MerchDraftCart): void {
  if (!canUseStorage()) return;
  try {
    sessionStorage.setItem(
      storageKey(cart.eventId),
      JSON.stringify({ ...cart, updatedAt: new Date().toISOString() }),
    );
  } catch {
    // Ignore quota / private mode.
  }
}

export function clearMerchDraftCart(eventId: string): void {
  if (!canUseStorage() || !eventId) return;
  try {
    sessionStorage.removeItem(storageKey(eventId));
  } catch {
    // ignore
  }
}

export function upsertMerchDraftLine(
  cart: MerchDraftCart,
  line: MerchDraftCartLine,
): MerchDraftCart {
  const next = [...cart.lines];
  const idx = next.findIndex((l) => l.variantId === line.variantId);
  if (line.quantity <= 0) {
    if (idx >= 0) next.splice(idx, 1);
  } else if (idx >= 0) {
    next[idx] = { ...next[idx], ...line };
  } else {
    next.push(line);
  }
  return { ...cart, lines: next, updatedAt: new Date().toISOString() };
}

export function draftCartSubtotal(cart: MerchDraftCart | null): number {
  if (!cart) return 0;
  return cart.lines.reduce(
    (sum, line) => sum + line.unitPrice * line.quantity,
    0,
  );
}

export function draftCartItemCount(cart: MerchDraftCart | null): number {
  if (!cart) return 0;
  return cart.lines.reduce((sum, line) => sum + line.quantity, 0);
}

/** Build checkout URL; first line is URL-prefilled, full cart in sessionStorage. */
export function buildDraftCartCheckoutHref(opts: {
  eventSlug: string;
  cart: MerchDraftCart;
  referralCode?: string;
}): string {
  const qs = new URLSearchParams();
  const first = opts.cart.lines[0];
  if (first) {
    qs.set("merch", first.productId);
    qs.set("variant", first.variantId);
    if (first.quantity > 1) qs.set("qty", String(first.quantity));
  }
  if (opts.referralCode) qs.set("ref", opts.referralCode);
  qs.set("from_merch_cart", "1");
  const q = qs.toString();
  return `/events/${opts.eventSlug}/checkout${q ? `?${q}` : ""}`;
}
