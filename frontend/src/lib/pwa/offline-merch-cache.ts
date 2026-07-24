/**
 * Buyer merch pickup QR display cache for offline viewing.
 * Validation still happens server-side when scanned — this is display-only.
 * Never cache shipping addresses with the QR payload. Never use for Vault.
 */

import type { MerchFulfillment } from "@/lib/types/merch";
import {
  buyerMerchStatusLabel,
  resolveBuyerMerchDisplayStatus,
} from "@/lib/merch-buyer-status";

const MERCH_PREFIX = "padeya.merch.pickup.cache.v1.";
const LIST_KEY = "padeya.merch.pickup.list.v1";

/** Minimal offline payload — QR bitmap token + desk code only. */
export type CachedMerchPickup = {
  id: string;
  order_item_id: string;
  pickup_code: string;
  qr_token: string;
  qr_typ: string;
  product_name_snapshot: string;
  variant_label_snapshot: string;
  quantity: number;
  status: string;
  display_status?: string | null;
  order_status?: string | null;
  fulfillment_method?: string | null;
  event_title?: string | null;
  cached_at: string;
};

function canUseStorage(): boolean {
  return typeof window !== "undefined" && typeof localStorage !== "undefined";
}

function cacheKey(orderItemId: string): string {
  return `${MERCH_PREFIX}${orderItemId}`;
}

function isEligibleForOfflineCache(row: MerchFulfillment): boolean {
  const method = (row.fulfillment_method || "pickup").toLowerCase();
  if (method !== "pickup") return false;
  if (!row.qr_token || !row.pickup_code) return false;
  const display = resolveBuyerMerchDisplayStatus({
    displayStatus: row.display_status,
    fulfillmentStatus: row.status,
    orderStatus: row.order_status,
  });
  if (
    display === "pending_payment" ||
    display === "picked_up" ||
    display === "cancelled" ||
    display === "refunded"
  ) {
    return false;
  }
  const order = (row.order_status || "").toLowerCase();
  if (order && order !== "paid") return false;
  return true;
}

function toCached(row: MerchFulfillment): CachedMerchPickup | null {
  if (!isEligibleForOfflineCache(row) || !row.qr_token) return null;
  return {
    id: row.id,
    order_item_id: row.order_item_id,
    pickup_code: row.pickup_code,
    qr_token: row.qr_token,
    qr_typ: row.qr_typ || "padeya.merch.pickup",
    product_name_snapshot: row.product_name_snapshot,
    variant_label_snapshot: row.variant_label_snapshot,
    quantity: row.quantity,
    status: row.status,
    display_status: row.display_status,
    order_status: row.order_status,
    fulfillment_method: row.fulfillment_method || "pickup",
    event_title: row.event_title,
    cached_at: new Date().toISOString(),
  };
}

export function cacheMerchPickupForOffline(row: MerchFulfillment): void {
  if (!canUseStorage() || !row?.order_item_id) return;
  try {
    const key = cacheKey(row.order_item_id);
    if (!isEligibleForOfflineCache(row)) {
      localStorage.removeItem(key);
      const listRaw = localStorage.getItem(LIST_KEY);
      const list: string[] = listRaw ? (JSON.parse(listRaw) as string[]) : [];
      localStorage.setItem(
        LIST_KEY,
        JSON.stringify(list.filter((id) => id !== row.order_item_id)),
      );
      return;
    }
    const payload = toCached(row);
    if (!payload) return;
    // Explicitly omit shipping_address and any contact fields.
    localStorage.setItem(key, JSON.stringify(payload));

    const listRaw = localStorage.getItem(LIST_KEY);
    const list: string[] = listRaw ? (JSON.parse(listRaw) as string[]) : [];
    if (!list.includes(row.order_item_id)) {
      list.unshift(row.order_item_id);
      localStorage.setItem(LIST_KEY, JSON.stringify(list.slice(0, 40)));
    }
  } catch {
    // Quota / private mode — ignore
  }
}

export function cacheMerchPickupListForOffline(rows: MerchFulfillment[]): void {
  if (!canUseStorage()) return;
  try {
    const eligible = rows.filter(isEligibleForOfflineCache);
    localStorage.setItem(
      LIST_KEY,
      JSON.stringify(eligible.map((r) => r.order_item_id).slice(0, 40)),
    );
    for (const row of rows) {
      cacheMerchPickupForOffline(row);
    }
  } catch {
    // ignore
  }
}

export function readCachedMerchPickup(
  orderItemId: string,
): CachedMerchPickup | null {
  if (!canUseStorage()) return null;
  try {
    const raw = localStorage.getItem(cacheKey(orderItemId));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as CachedMerchPickup;
    if (!parsed?.qr_token || !parsed?.pickup_code) return null;
    // Never treat a payload that somehow included address fields as valid cache.
    if ("shipping_address" in (parsed as object)) {
      localStorage.removeItem(cacheKey(orderItemId));
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

export function cachedMerchAsFulfillment(
  cached: CachedMerchPickup,
): MerchFulfillment {
  return {
    id: cached.id,
    order_id: "",
    order_item_id: cached.order_item_id,
    host_id: "",
    buyer_user_id: "",
    merch_variant_id: "",
    quantity: cached.quantity,
    status: cached.status,
    display_status: cached.display_status,
    order_status: cached.order_status,
    fulfillment_method: cached.fulfillment_method || "pickup",
    pickup_code: cached.pickup_code,
    product_name_snapshot: cached.product_name_snapshot,
    variant_label_snapshot: cached.variant_label_snapshot,
    qr_token: cached.qr_token,
    qr_typ: cached.qr_typ,
    event_title: cached.event_title,
    created_at: cached.cached_at,
    shipping_address: null,
  };
}

export function offlineMerchStatusLabel(cached: CachedMerchPickup): string {
  return buyerMerchStatusLabel(
    resolveBuyerMerchDisplayStatus({
      displayStatus: cached.display_status,
      fulfillmentStatus: cached.status,
      orderStatus: cached.order_status,
    }),
  );
}
