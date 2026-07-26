/**
 * Pure helpers for Web Push subscription + safe client observability.
 * Never log auth/p256dh/full endpoints/VAPID private keys/tokens.
 */

export type PushClientEvent =
  | "push_subscription_created"
  | "push_subscription_saved"
  | "push_subscription_save_failed"
  | "push_subscription_repaired"
  | "push_subscription_reconcile_skipped"
  | "push_send_attempt"
  | "push_send_success"
  | "push_send_failed"
  | "push_subscription_stale";

export function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const trimmed = base64String.trim();
  if (!trimmed) {
    throw new Error("Missing VAPID public key");
  }
  const padding = "=".repeat((4 - (trimmed.length % 4)) % 4);
  const base64 = (trimmed + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64);
  const output = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i += 1) {
    output[i] = raw.charCodeAt(i);
  }
  return output;
}

/** Match a full endpoint against the short server-side hint (`…` + last 24). */
export function endpointMatchesHint(
  endpoint: string,
  hint: string | null | undefined,
): boolean {
  if (!endpoint || !hint) return false;
  const tail = hint.replace(/^…/, "").trim();
  if (!tail || tail.length < 8) return false;
  return endpoint.endsWith(tail);
}

export function logPushClientEvent(
  event: PushClientEvent,
  meta?: Record<string, string | number | boolean | null | undefined>,
): void {
  if (typeof console === "undefined" || typeof console.info !== "function") return;
  const safe: Record<string, string | number | boolean | null> = {};
  if (meta) {
    for (const [key, value] of Object.entries(meta)) {
      const k = key.toLowerCase();
      if (
        k.includes("auth") ||
        k.includes("p256dh") ||
        k.includes("endpoint") ||
        k.includes("vapid") ||
        k.includes("token") ||
        k.includes("private")
      ) {
        continue;
      }
      if (
        value === undefined ||
        typeof value === "string" ||
        typeof value === "number" ||
        typeof value === "boolean" ||
        value === null
      ) {
        safe[key] = value === undefined ? null : value;
      }
    }
  }
  console.info(`[padeya.push] ${event}`, safe);
}

/**
 * Ensure a PushSubscription exists for the registration.
 * Reuses an existing subscription; never requests Notification permission.
 */
export async function ensurePushSubscription(
  registration: ServiceWorkerRegistration,
  vapidPublicKey: string,
): Promise<{ subscription: PushSubscription; created: boolean }> {
  if (!vapidPublicKey?.trim()) {
    throw new Error("Missing VAPID public key");
  }
  const existing = await registration.pushManager.getSubscription();
  if (existing) {
    return { subscription: existing, created: false };
  }
  const subscription = await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(vapidPublicKey) as BufferSource,
  });
  logPushClientEvent("push_subscription_created", { created: true });
  return { subscription, created: true };
}

export function subscriptionKeysComplete(
  json: PushSubscriptionJSON,
): json is PushSubscriptionJSON & {
  endpoint: string;
  keys: { p256dh: string; auth: string };
} {
  return Boolean(json.endpoint && json.keys?.p256dh && json.keys?.auth);
}
