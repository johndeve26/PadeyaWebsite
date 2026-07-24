"use client";

import { useCallback, useEffect, useState, useTransition } from "react";

import { ApiError } from "@/lib/api";
import {
  fetchPushSubscriptions,
  fetchVapidPublicKey,
  removePushSubscription,
  subscribePush,
  testMyPush,
  unsubscribePush,
  urlBase64ToUint8Array,
  type PushSubscriptionDevice,
} from "@/lib/notifications-api";
import {
  detectPushDeviceContext,
  guessPushPlatform,
  IOS_PUSH_HELPER,
  isPushApiSupported,
  PUSH_ENABLED_COPY,
  type PushDeviceContext,
} from "@/lib/push-device";

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

/**
 * Browser push registration for Pàdéyá.
 *
 * Permission flow (Android / desktop unchanged):
 * 1. Settings show current state — no Notification.requestPermission on load
 * 2. User clicks Enable notifications
 * 3. Browser permission prompt
 * 4. On grant → subscribe → POST /push/subscriptions → success
 * 5. On deny → helpful denied state (no subscription)
 */
export function usePushNotifications() {
  const [supported, setSupported] = useState(false);
  const [adminEnabled, setAdminEnabled] = useState(false);
  const [permission, setPermission] = useState<PushPermissionState>("unknown");
  const [subscribed, setSubscribed] = useState(false);
  const [devices, setDevices] = useState<PushSubscriptionDevice[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [device, setDevice] = useState<PushDeviceContext>(() =>
    detectPushDeviceContext(),
  );
  const [, startTransition] = useTransition();

  const refresh = useCallback(async () => {
    // UX detection only — not used for security/authorization.
    const deviceCtx = detectPushDeviceContext();
    const apiSupported = deviceCtx.pushSupported;
    let vapidOn = false;
    let isSubscribed = false;
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
        const sub = await reg.pushManager.getSubscription();
        isSubscribed = Boolean(sub);
      } catch {
        isSubscribed = false;
      }
    }

    let deviceRows: PushSubscriptionDevice[] = [];
    try {
      const data = await fetchPushSubscriptions(true);
      deviceRows = data.items;
    } catch {
      deviceRows = [];
    }

    startTransition(() => {
      setSupported(apiSupported);
      setAdminEnabled(vapidOn);
      setPermission(perm);
      setSubscribed(isSubscribed);
      setDevices(deviceRows);
      setDevice(deviceCtx);
    });
  }, [startTransition]);

  useEffect(() => {
    let cancelled = false;
    queueMicrotask(() => {
      void (async () => {
        if (cancelled) return;
        await refresh();
      })();
    });
    return () => {
      cancelled = true;
    };
  }, [refresh]);

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
        // Helpful denied state — do not treat as a hard error toast.
        setError(null);
        setNote(null);
        return;
      }
      if (next !== "granted") {
        throw new Error(
          "Notification permission was dismissed. Tap Enable notifications to try again.",
        );
      }
      const reg = await Promise.race([
        navigator.serviceWorker.ready,
        new Promise<never>((_, reject) => {
          window.setTimeout(() => {
            reject(
              new Error(
                "Service worker did not become ready. Reload this page (or reopen the installed app), then try Enable again.",
              ),
            );
          }, 12_000);
        }),
      ]);
      const sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(
          vapid.public_key,
        ) as BufferSource,
      });
      const json = sub.toJSON();
      const p256dh = json.keys?.p256dh;
      const auth = json.keys?.auth;
      if (!json.endpoint || !p256dh || !auth) {
        throw new Error("Browser did not return a complete push subscription.");
      }
      const platform = guessPushPlatform();
      await subscribePush({
        endpoint: json.endpoint,
        p256dh,
        auth,
        platform,
        device_label: platform
          ? `${platform.charAt(0).toUpperCase()}${platform.slice(1)} browser`
          : "This browser",
      });
      clearPushPromptDismissed();
      setSubscribed(true);
      setNote(PUSH_ENABLED_COPY);
      await refresh();
      try {
        await testMyPush();
        setNote(
          "Push is enabled on this device. Check for a test notification from Pàdéyá.",
        );
      } catch {
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
  }, [refresh]);

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
        await removePushSubscription(subscriptionId);
        const reg = await navigator.serviceWorker.ready;
        const sub = await reg.pushManager.getSubscription();
        if (sub) {
          const listed = await fetchPushSubscriptions(true);
          const stillActiveHere = listed.items.some(
            (d) =>
              d.is_active &&
              d.endpoint_hint &&
              sub.endpoint.endsWith(d.endpoint_hint.replace(/^…/, "")),
          );
          if (!stillActiveHere) {
            try {
              await unsubscribePush(sub.endpoint);
            } catch {
              /* already revoked */
            }
            await sub.unsubscribe();
            setSubscribed(false);
          }
        }
        setNote("Device removed. It will no longer receive Pàdéyá push alerts.");
        await refresh();
      } catch (err) {
        setError(err instanceof ApiError ? err.detail : "Could not remove device");
      } finally {
        setBusy(false);
      }
    },
    [refresh],
  );

  const sendTest = useCallback(async () => {
    setBusy(true);
    setError(null);
    setNote(null);
    try {
      await testMyPush();
      setNote(
        "Test notification sent. Check your system tray or notification center.",
      );
    } catch (err) {
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
  }, []);

  const canOfferOptIn =
    supported &&
    adminEnabled &&
    !subscribed &&
    permission !== "denied" &&
    permission !== "unsupported";

  return {
    supported,
    adminEnabled,
    permission,
    subscribed,
    devices,
    busy,
    error,
    note,
    canOfferOptIn,
    /** iPhone/iPad Home Screen context for helper copy */
    device,
    refresh,
    enable,
    disableThisDevice,
    removeDevice,
    sendTest,
    setError,
    setNote,
  };
}
