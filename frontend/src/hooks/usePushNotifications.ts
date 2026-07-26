"use client";

import { useCallback, useEffect, useRef, useState, useTransition } from "react";

import { ApiError } from "@/lib/api";
import {
  fetchPushSubscriptions,
  fetchVapidPublicKey,
  removePushSubscription,
  subscribePush,
  testMyPush,
  unsubscribePush,
  type PushSubscriptionDevice,
  type PushTestResult,
} from "@/lib/notifications-api";
import {
  detectPushDeviceContext,
  guessPushPlatform,
  IOS_PUSH_HELPER,
  isPushApiSupported,
  PUSH_ENABLED_COPY,
  type PushDeviceContext,
} from "@/lib/push-device";
import {
  endpointMatchesHint,
  ensurePushSubscription,
  logPushClientEvent,
  subscriptionKeysComplete,
} from "@/lib/push-subscription";

const DISMISS_KEY = "padeya-push-prompt-dismissed";

/** Hook-facing permission: browser values, or unsupported when Notification API is missing. */
export type PushPermissionState =
  | "default"
  | "granted"
  | "denied"
  | "unsupported"
  | "unknown";

export function wasPushPromptDismissed(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return localStorage.getItem(DISMISS_KEY) === "1";
  } catch {
    return false;
  }
}

export function dismissPushPrompt(): void {
  try {
    localStorage.setItem(DISMISS_KEY, "1");
  } catch {
    /* ignore */
  }
}

export function clearPushPromptDismissed(): void {
  try {
    localStorage.removeItem(DISMISS_KEY);
  } catch {
    /* ignore */
  }
}

async function waitForServiceWorkerReady(
  timeoutMs = 12_000,
): Promise<ServiceWorkerRegistration> {
  return Promise.race([
    navigator.serviceWorker.ready,
    new Promise<never>((_, reject) => {
      window.setTimeout(() => {
        reject(
          new Error(
            "Service worker did not become ready. Reload this page (or reopen the installed app), then try again.",
          ),
        );
      }, timeoutMs);
    }),
  ]);
}

function thisDeviceServerRegistered(
  localEndpoint: string | null,
  devices: PushSubscriptionDevice[],
): boolean {
  if (!localEndpoint) return false;
  return devices.some(
    (d) => d.is_active && endpointMatchesHint(localEndpoint, d.endpoint_hint),
  );
}

/**
 * Browser push registration for Pàdéyá.
 *
 * Permission flow (Android / desktop unchanged):
 * 1. Settings show current state — no Notification.requestPermission on load
 * 2. User clicks Enable notifications
 * 3. Browser permission prompt
 * 4. On grant → subscribe → POST /push/subscriptions → success
 * 5. On deny → helpful denied state (no subscription)
 *
 * "Enabled" requires a real PushSubscription + backend registration — not
 * Notification.permission alone.
 */
export function usePushNotifications() {
  const [supported, setSupported] = useState(false);
  const [adminEnabled, setAdminEnabled] = useState(false);
  const [permission, setPermission] = useState<PushPermissionState>("unknown");
  const [subscribed, setSubscribed] = useState(false);
  const [serverRegisteredHere, setServerRegisteredHere] = useState(false);
  const [serviceWorkerActive, setServiceWorkerActive] = useState(false);
  const [localEndpoint, setLocalEndpoint] = useState<string | null>(null);
  const [devices, setDevices] = useState<PushSubscriptionDevice[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [device, setDevice] = useState<PushDeviceContext>(() =>
    detectPushDeviceContext(),
  );
  const [, startTransition] = useTransition();
  const autoRepairRef = useRef(false);

  const persistSubscription = useCallback(
    async (sub: PushSubscription): Promise<PushSubscriptionDevice> => {
      const json = sub.toJSON();
      if (!subscriptionKeysComplete(json)) {
        throw new Error("Browser did not return a complete push subscription.");
      }
      const platform = guessPushPlatform();
      try {
        const saved = await subscribePush({
          endpoint: json.endpoint,
          p256dh: json.keys.p256dh,
          auth: json.keys.auth,
          platform,
          device_label: platform
            ? `${platform.charAt(0).toUpperCase()}${platform.slice(1)} browser`
            : "This browser",
        });
        logPushClientEvent("push_subscription_saved", {
          platform: platform || "web",
        });
        return saved;
      } catch (err) {
        logPushClientEvent("push_subscription_save_failed", {
          reason: err instanceof ApiError ? err.status : "error",
        });
        throw err;
      }
    },
    [],
  );

  const refresh = useCallback(async () => {
    // UX detection only — not used for security/authorization.
    const deviceCtx = detectPushDeviceContext();
    const apiSupported = deviceCtx.pushSupported;
    let vapidOn = false;
    let isSubscribed = false;
    let swActive = false;
    let endpoint: string | null = null;
    const perm: PushPermissionState = deviceCtx.permission ?? "unsupported";

    try {
      const vapid = await fetchVapidPublicKey();
      vapidOn = Boolean(vapid.enabled && vapid.public_key);
    } catch {
      vapidOn = false;
    }

    if (apiSupported) {
      try {
        const reg = await navigator.serviceWorker.ready;
        swActive = Boolean(reg.active || navigator.serviceWorker.controller);
        const sub = await reg.pushManager.getSubscription();
        isSubscribed = Boolean(sub);
        endpoint = sub?.endpoint ?? null;
      } catch {
        isSubscribed = false;
        swActive = false;
        endpoint = null;
      }
    }

    let deviceRows: PushSubscriptionDevice[] = [];
    try {
      const data = await fetchPushSubscriptions(true);
      deviceRows = data.items;
    } catch {
      deviceRows = [];
    }

    const serverHere = thisDeviceServerRegistered(endpoint, deviceRows);

    startTransition(() => {
      setSupported(apiSupported);
      setAdminEnabled(vapidOn);
      setPermission(perm);
      setSubscribed(isSubscribed);
      setServerRegisteredHere(serverHere);
      setServiceWorkerActive(swActive);
      setLocalEndpoint(endpoint);
      setDevices(deviceRows);
      setDevice(deviceCtx);
    });

    return {
      apiSupported,
      vapidOn,
      perm,
      isSubscribed,
      serverHere,
      swActive,
      endpoint,
      deviceRows,
      deviceCtx,
    };
  }, [startTransition]);

  const repair = useCallback(
    async (opts?: { silent?: boolean }) => {
      const silent = Boolean(opts?.silent);
      if (!silent) {
        setBusy(true);
        setError(null);
        setNote(null);
      }
      try {
        const deviceCtx = detectPushDeviceContext();
        setDevice(deviceCtx);
        if (!deviceCtx.pushSupported || !isPushApiSupported()) {
          if (deviceCtx.needsHomeScreenForPush) {
            throw new Error(
              `${IOS_PUSH_HELPER.body} ${IOS_PUSH_HELPER.browsersNote}`,
            );
          }
          throw new Error("Browser push is not supported on this device.");
        }
        if (deviceCtx.permission !== "granted") {
          throw new Error(
            "Notification permission is not allowed. Tap Enable notifications to grant access.",
          );
        }
        const vapid = await fetchVapidPublicKey();
        if (!vapid.enabled || !vapid.public_key) {
          throw new Error("Push is not enabled by Pàdéyá admin yet.");
        }
        // Repair reuses an already-granted permission; it never prompts again.
        const reg = await waitForServiceWorkerReady();
        const { subscription, created } = await ensurePushSubscription(
          reg,
          vapid.public_key,
        );
        await persistSubscription(subscription);
        logPushClientEvent("push_subscription_repaired", { created });
        if (!silent) {
          setNote(
            created
              ? "Push subscription repaired on this device."
              : "Push registration synced with Pàdéyá.",
          );
        }
        await refresh();
        return true;
      } catch (err) {
        if (!silent) {
          setError(
            err instanceof ApiError
              ? err.detail
              : err instanceof Error
                ? err.message
                : "Could not repair push",
          );
        } else {
          logPushClientEvent("push_subscription_reconcile_skipped", {
            reason: err instanceof Error ? err.message.slice(0, 80) : "error",
          });
        }
        return false;
      } finally {
        if (!silent) setBusy(false);
      }
    },
    [persistSubscription, refresh],
  );

  useEffect(() => {
    let cancelled = false;
    queueMicrotask(() => {
      void (async () => {
        if (cancelled) return;
        const snap = await refresh();
        if (cancelled || autoRepairRef.current) return;
        // Lightweight one-shot reconcile: permission granted but missing
        // local subscription and/or backend registration for this device.
        const needsRepair =
          snap.apiSupported &&
          snap.vapidOn &&
          snap.perm === "granted" &&
          (!snap.isSubscribed || !snap.serverHere) &&
          !snap.deviceCtx.needsHomeScreenForPush;
        if (!needsRepair) return;
        autoRepairRef.current = true;
        await repair({ silent: true });
      })();
    });
    return () => {
      cancelled = true;
    };
  }, [refresh, repair]);

  const enable = useCallback(async () => {
    setBusy(true);
    setError(null);
    setNote(null);
    try {
      const deviceCtx = detectPushDeviceContext();
      setDevice(deviceCtx);
      setPermission(deviceCtx.permission ?? "unsupported");
      if (!deviceCtx.pushSupported || !isPushApiSupported()) {
        if (deviceCtx.needsHomeScreenForPush) {
          throw new Error(
            `${IOS_PUSH_HELPER.body} ${IOS_PUSH_HELPER.browsersNote}`,
          );
        }
        throw new Error("Browser push is not supported on this device.");
      }
      const vapid = await fetchVapidPublicKey();
      if (!vapid.enabled || !vapid.public_key) {
        throw new Error("Push is not enabled by Pàdéyá admin yet.");
      }
      // Only after Enable notifications — never on page load / refresh().
      const next = await Notification.requestPermission();
      const nextPerm =
        next === "default" || next === "granted" || next === "denied"
          ? next
          : "unknown";
      setPermission(nextPerm);
      setDevice(detectPushDeviceContext());
      if (next === "denied") {
        setError(null);
        setNote(null);
        return;
      }
      if (next !== "granted") {
        throw new Error(
          "Notification permission was dismissed. Tap Enable notifications to try again.",
        );
      }
      const reg = await waitForServiceWorkerReady();
      const { subscription } = await ensurePushSubscription(
        reg,
        vapid.public_key,
      );
      // Success UI only after backend persistence succeeds.
      await persistSubscription(subscription);
      clearPushPromptDismissed();
      await refresh();
      setNote(PUSH_ENABLED_COPY);
      try {
        logPushClientEvent("push_send_attempt", { kind: "user_test" });
        const result: PushTestResult = await testMyPush();
        if (result.ok === false) {
          logPushClientEvent("push_send_failed", {
            kind: "user_test",
            sent: result.sent ?? 0,
          });
          setNote(
            `${PUSH_ENABLED_COPY} Device registered, but the test push did not deliver. Tap "Send test notification" to retry.`,
          );
        } else if (result.browser_delivery === false) {
          setNote(
            `${PUSH_ENABLED_COPY} Server recorded the test in log mode — browser delivery is off until admin sets provider to web_push.`,
          );
        } else {
          logPushClientEvent("push_send_success", {
            kind: "user_test",
            sent: result.sent ?? 0,
          });
          setNote(
            "Push is enabled on this device. Check for a test notification from Pàdéyá.",
          );
        }
      } catch {
        logPushClientEvent("push_send_failed", { kind: "user_test" });
        setNote(
          `${PUSH_ENABLED_COPY} Tap "Send test notification" below to verify delivery.`,
        );
      }
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.detail
          : err instanceof Error
            ? err.message
            : "Could not enable push",
      );
    } finally {
      setBusy(false);
    }
  }, [persistSubscription, refresh]);

  const disableThisDevice = useCallback(async () => {
    setBusy(true);
    setError(null);
    setNote(null);
    try {
      const reg = await navigator.serviceWorker.ready;
      const sub = await reg.pushManager.getSubscription();
      if (sub) {
        await unsubscribePush(sub.endpoint);
        await sub.unsubscribe();
      }
      setSubscribed(false);
      setServerRegisteredHere(false);
      setLocalEndpoint(null);
      setNote("Browser push disabled on this device.");
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not disable push");
    } finally {
      setBusy(false);
    }
  }, [refresh]);

  const removeDevice = useCallback(
    async (subscriptionId: string) => {
      setBusy(true);
      setError(null);
      setNote(null);
      try {
        const target = devices.find((d) => d.id === subscriptionId) || null;
        await removePushSubscription(subscriptionId);
        try {
          const reg = await navigator.serviceWorker.ready;
          const sub = await reg.pushManager.getSubscription();
          if (
            sub &&
            target &&
            endpointMatchesHint(sub.endpoint, target.endpoint_hint)
          ) {
            try {
              await unsubscribePush(sub.endpoint);
            } catch {
              /* already revoked */
            }
            await sub.unsubscribe();
            setSubscribed(false);
            setServerRegisteredHere(false);
            setLocalEndpoint(null);
          }
        } catch {
          /* SW may be unavailable when removing another device */
        }
        setNote("Device removed. It will no longer receive Pàdéyá push alerts.");
        await refresh();
      } catch (err) {
        setError(err instanceof ApiError ? err.detail : "Could not remove device");
      } finally {
        setBusy(false);
      }
    },
    [devices, refresh],
  );

  const sendTest = useCallback(async () => {
    setBusy(true);
    setError(null);
    setNote(null);
    try {
      logPushClientEvent("push_send_attempt", { kind: "user_test" });
      const result = await testMyPush();
      if (result.ok === false) {
        logPushClientEvent("push_send_failed", {
          kind: "user_test",
          sent: result.sent ?? 0,
          failed: result.failed ?? 0,
        });
        throw new Error(
          result.message ||
            "Test push failed. Try Repair push notifications, then send again.",
        );
      }
      if (result.browser_delivery === false) {
        setNote(
          "Test recorded in log mode. Browser devices will not receive it until admin sets provider to web_push.",
        );
        return;
      }
      logPushClientEvent("push_send_success", {
        kind: "user_test",
        sent: result.sent ?? 0,
      });
      const stale =
        typeof result.removed_stale === "number" && result.removed_stale > 0
          ? ` Removed ${result.removed_stale} stale device registration(s).`
          : "";
      setNote(
        `Test notification sent${
          typeof result.sent === "number" ? ` (${result.sent} device${result.sent === 1 ? "" : "s"})` : ""
        }. Check your system tray or notification center.${stale}`,
      );
      await refresh();
    } catch (err) {
      logPushClientEvent("push_send_failed", { kind: "user_test" });
      setError(
        err instanceof ApiError
          ? err.detail
          : err instanceof Error
            ? err.message
            : "Could not send test notification",
      );
    } finally {
      setBusy(false);
    }
  }, [refresh]);

  const canOfferOptIn =
    supported &&
    adminEnabled &&
    !subscribed &&
    permission !== "denied" &&
    permission !== "unsupported" &&
    permission !== "granted";

  const canRepair =
    supported &&
    adminEnabled &&
    permission === "granted" &&
    (!subscribed || !serverRegisteredHere);

  return {
    supported,
    adminEnabled,
    permission,
    subscribed,
    serverRegisteredHere,
    serviceWorkerActive,
    localEndpoint,
    devices,
    busy,
    error,
    note,
    canOfferOptIn,
    canRepair,
    /** iPhone/iPad Home Screen context for helper copy */
    device,
    refresh,
    enable,
    repair,
    disableThisDevice,
    removeDevice,
    sendTest,
    setError,
    setNote,
  };
}
