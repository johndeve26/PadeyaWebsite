/**
 * Browser analytics helpers: visitor ids, UTM, bots, dedupe keys.
 * Trusted actions (payment_success, ticket_issued, etc.) must never be sent from here.
 */

const ANON_KEY = "padeya_anonymous_id";
const SESSION_KEY = "padeya_session_id";
const SESSION_TS_KEY = "padeya_session_ts";

/** Session idle timeout — 30 minutes (matches typical analytics session). */
const SESSION_IDLE_MS = 30 * 60 * 1000;

const BOT_UA =
  /bot|crawl|spider|slurp|facebookexternalhit|preview|headless|wget|curl|python-requests|scrapy|httpclient|monitoring/i;

export function isLikelyBot(userAgent?: string | null): boolean {
  if (typeof userAgent === "string" && userAgent.trim()) {
    return BOT_UA.test(userAgent);
  }
  if (typeof navigator !== "undefined" && navigator.userAgent) {
    return BOT_UA.test(navigator.userAgent);
  }
  return false;
}

export function normalizeUtmParams(
  input?: Record<string, string | null | undefined> | null,
  url?: string,
): {
  source?: string;
  medium?: string;
  campaign?: string;
  term?: string;
  content?: string;
  utmSource?: string;
  utmMedium?: string;
  utmCampaign?: string;
  utmTerm?: string;
  utmContent?: string;
} {
  const fromUrl: Record<string, string> = {};
  const rawUrl =
    url ??
    (typeof window !== "undefined" ? window.location.href : undefined);
  if (rawUrl) {
    try {
      const params = new URL(rawUrl).searchParams;
      for (const key of [
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
      ] as const) {
        const v = params.get(key);
        if (v) fromUrl[key] = v.trim().slice(0, 160).toLowerCase();
      }
    } catch {
      /* ignore */
    }
  }

  const pick = (...vals: Array<string | null | undefined>) => {
    for (const v of vals) {
      if (v && String(v).trim()) return String(v).trim().slice(0, 160).toLowerCase();
    }
    return undefined;
  };

  const source = pick(
    input?.source,
    input?.utm_source,
    input?.utmSource,
    fromUrl.utm_source,
  );
  const medium = pick(
    input?.medium,
    input?.utm_medium,
    input?.utmMedium,
    fromUrl.utm_medium,
  );
  const campaign = pick(
    input?.campaign,
    input?.utm_campaign,
    input?.utmCampaign,
    fromUrl.utm_campaign,
  );
  const term = pick(input?.term, input?.utm_term, input?.utmTerm, fromUrl.utm_term);
  const content = pick(
    input?.content,
    input?.utm_content,
    input?.utmContent,
    fromUrl.utm_content,
  );

  return {
    source,
    medium,
    campaign,
    term,
    content,
    utmSource: source,
    utmMedium: medium,
    utmCampaign: campaign,
    utmTerm: term,
    utmContent: content,
  };
}

function randomId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID().replace(/-/g, "").slice(0, 32);
  }
  return `p${Date.now().toString(36)}${Math.random().toString(36).slice(2, 12)}`;
}

function storage(): Storage | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

function sessionStorageSafe(): Storage | null {
  if (typeof window === "undefined") return null;
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

export function getOrCreateAnonymousId(): string {
  const store = storage();
  if (!store) return randomId();
  const existing = store.getItem(ANON_KEY);
  if (existing) return existing;
  const id = randomId();
  store.setItem(ANON_KEY, id);
  return id;
}

export function getOrCreateSessionId(): string {
  const store = sessionStorageSafe() ?? storage();
  if (!store) return randomId();
  const now = Date.now();
  const existing = store.getItem(SESSION_KEY);
  const tsRaw = store.getItem(SESSION_TS_KEY);
  const ts = tsRaw ? Number(tsRaw) : 0;
  if (existing && ts && now - ts < SESSION_IDLE_MS) {
    store.setItem(SESSION_TS_KEY, String(now));
    return existing;
  }
  const id = randomId();
  store.setItem(SESSION_KEY, id);
  store.setItem(SESSION_TS_KEY, String(now));
  return id;
}

export function generateDedupeKey(
  scope: string,
  parts: {
    requestId?: string;
    targetEventId?: string;
    sessionId?: string;
    anonymousId?: string;
    userId?: string;
    orderId?: string;
    listContext?: string;
    extra?: string;
  } = {},
): string | null {
  const scopeClean = (scope || "").trim().toLowerCase().slice(0, 64);
  if (!scopeClean) return null;
  if (parts.requestId?.trim()) {
    return `${scopeClean}:req:${parts.requestId.trim().slice(0, 128)}`.slice(0, 191);
  }
  const chunks = [scopeClean];
  if (parts.targetEventId) chunks.push(`evt:${parts.targetEventId}`);
  if (parts.orderId) chunks.push(`ord:${parts.orderId}`);
  if (parts.userId) chunks.push(`u:${parts.userId}`);
  else if (parts.anonymousId?.trim()) chunks.push(`a:${parts.anonymousId.trim().slice(0, 64)}`);
  else if (parts.sessionId?.trim()) chunks.push(`s:${parts.sessionId.trim().slice(0, 64)}`);
  else if (!parts.orderId) return null;
  if (parts.listContext?.trim()) chunks.push(`ctx:${parts.listContext.trim().slice(0, 64)}`);
  if (parts.extra?.trim()) chunks.push(parts.extra.trim().slice(0, 64));
  return chunks.join(":").slice(0, 191);
}

/** Trusted actions that the browser must never emit. */
export const SERVER_ONLY_ACTIONS = new Set([
  "payment_success",
  "payment_failed",
  "ticket_issued",
  "checkin_success",
  "review_submitted",
  "checkout_complete",
  "refund_approved",
  "vault_purchase",
  "promo_redemption",
  "ambassador_sale",
  "payout_completed",
  "merch_payment_confirmed",
  "merch_purchase_completed",
  "merch_qr_scanned",
  "merch_picked_up",
  "merch_marked_picked_up",
  "merch_shipped",
  "merch_delivered",
  "merch_review_submitted",
  "merch_abandoned_cart_created",
  "merch_abandoned_cart_recovered",
  "merch_badge_awarded",
  "merch_sold_out",
  "host_merch_product_created",
  "host_merch_product_updated",
  "host_merch_product_paused",
  "admin_merch_hidden",
  "fan_connect_enabled",
  "fan_connect_disabled",
  "fan_connect_request_sent",
  "fan_connect_request_accepted",
  "fan_connect_request_declined",
  "fan_connect_connection_removed",
  "fan_connect_blocked",
  "fan_connect_reported",
  "fan_fan_message_thread_created",
  "fan_fan_message_sent",
]);

export function assertClientActionAllowed(action: string): void {
  const key = action.trim().toLowerCase();
  if (SERVER_ONLY_ACTIONS.has(key)) {
    throw new Error(
      `${key} is a trusted server-side analytics action and cannot be sent from the browser`,
    );
  }
}
