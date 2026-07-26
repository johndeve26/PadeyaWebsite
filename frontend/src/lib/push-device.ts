/**
 * Device / capability helpers for Pàdéyá browser push UX guidance.
 *
 * Detection is UX-only — never use these checks for authorization or security.
 * Safe browser feature detection only; no permission prompts.
 */

/** Browser Notification.permission values when the API exists. */
export type PushNotificationPermission = "default" | "granted" | "denied";

export type PushDeviceContext = {
  /** Coarse platform label for subscription metadata (not for access control) */
  platformGuess: string | undefined;
  /** 1. iPhone / iPad / iPod (incl. iPadOS desktop-UA spoof) */
  isAppleMobile: boolean;
  /** 2. Installed Home Screen app / PWA (standalone display) */
  isStandalone: boolean;
  /** 3. Web Push APIs present (Notification + serviceWorker + PushManager) */
  pushSupported: boolean;
  /** Individual API presence (for clearer unsupported copy) */
  hasNotification: boolean;
  hasServiceWorker: boolean;
  hasPushManager: boolean;
  /**
   * 4. Notification permission when Notification API exists.
   * null when `'Notification' in window` is false — there is no permission state.
   */
  permission: PushNotificationPermission | null;
  /**
   * Apple mobile browsers often need the Home Screen app before Web Push
   * works reliably — Chrome, Firefox, Edge, and Safari included.
   */
  needsHomeScreenForPush: boolean;
};

export function isAppleMobileDevice(
  userAgent: string = typeof navigator !== "undefined" ? navigator.userAgent : "",
  opts?: { platform?: string; maxTouchPoints?: number },
): boolean {
  if (/iPhone|iPod|iPad/i.test(userAgent)) return true;
  // iPadOS 13+ may report as Macintosh with touch
  const platform =
    opts?.platform ??
    (typeof navigator !== "undefined" ? navigator.platform : "");
  const maxTouch =
    opts?.maxTouchPoints ??
    (typeof navigator !== "undefined" ? navigator.maxTouchPoints : 0);
  if (/Mac/i.test(platform) && maxTouch > 1) return true;
  return false;
}

/** Home Screen / installed PWA via display-mode + legacy iOS navigator.standalone. */
export function isStandaloneDisplay(): boolean {
  if (typeof window === "undefined") return false;
  try {
    if (window.matchMedia("(display-mode: standalone)").matches) return true;
    // Some installed PWAs report fullscreen
    if (window.matchMedia("(display-mode: fullscreen)").matches) return true;
  } catch {
    /* ignore */
  }
  const nav = navigator as Navigator & { standalone?: boolean };
  return nav.standalone === true;
}

/** UX check only — Web Push needs all three APIs. */
export function isPushApiSupported(): boolean {
  if (typeof window === "undefined") return false;
  return (
    "Notification" in window &&
    "serviceWorker" in navigator &&
    "PushManager" in window
  );
}

/**
 * Read Notification.permission without requesting it.
 * Returns null when the Notification API is missing.
 */
export function readNotificationPermission(): PushNotificationPermission | null {
  if (typeof window === "undefined" || !("Notification" in window)) {
    return null;
  }
  const value = Notification.permission;
  if (value === "default" || value === "granted" || value === "denied") {
    return value;
  }
  return null;
}

export function guessPushPlatform(
  userAgent: string = typeof navigator !== "undefined" ? navigator.userAgent : "",
): string | undefined {
  if (typeof navigator === "undefined" && !userAgent) return undefined;
  const ua = userAgent.toLowerCase();
  if (isAppleMobileDevice(userAgent)) return "ios";
  if (/android/.test(ua)) return "android";
  if (/mac os|macintosh/.test(ua)) return "macos";
  if (/windows/.test(ua)) return "windows";
  if (/linux/.test(ua)) return "linux";
  return "web";
}

/**
 * Snapshot of device + capability signals for push UX copy.
 * Does not call Notification.requestPermission.
 */
export function detectPushDeviceContext(): PushDeviceContext {
  if (typeof window === "undefined") {
    return {
      platformGuess: undefined,
      isAppleMobile: false,
      isStandalone: false,
      pushSupported: false,
      hasNotification: false,
      hasServiceWorker: false,
      hasPushManager: false,
      permission: null,
      needsHomeScreenForPush: false,
    };
  }

  const hasNotification = "Notification" in window;
  const hasServiceWorker = "serviceWorker" in navigator;
  const hasPushManager = "PushManager" in window;
  const isAppleMobile = isAppleMobileDevice();
  const isStandalone = isStandaloneDisplay();
  const pushSupported = hasNotification && hasServiceWorker && hasPushManager;

  return {
    platformGuess: guessPushPlatform(),
    isAppleMobile,
    isStandalone,
    pushSupported,
    hasNotification,
    hasServiceWorker,
    hasPushManager,
    permission: readNotificationPermission(),
    needsHomeScreenForPush: isAppleMobile && !isStandalone,
  };
}

/** iPhone/iPad push helper copy — UX only; not Safari-only framing. */
export const IOS_PUSH_HELPER = {
  title: "Install Pàdéyá to enable push notifications",
  body: "On iPhone or iPad, push notifications work from the installed Pàdéyá app. Add Pàdéyá to your Home Screen, open it from the Home Screen icon, then enable notifications.",
  steps: [
    "Open Pàdéyá in your browser",
    "Tap Share or the browser menu",
    "Tap Add to Home Screen",
    "Open Pàdéyá from the Home Screen icon",
    "Go to Notification settings and tap Enable notifications",
  ] as const,
  browsersNote:
    "Chrome, Firefox, Edge, and Safari on iPhone may all require the Home Screen app flow.",
  whyNote:
    "Apple only allows web push for installed Home Screen web apps on iPhone/iPad.",
} as const;

/** Compact one-line reminder (errors / install banner). */
export const IOS_HOME_SCREEN_STEPS = [
  IOS_PUSH_HELPER.body,
  IOS_PUSH_HELPER.browsersNote,
].join(" ");

/** Shown when Notification.permission is denied (after Enable or already blocked). */
export const PUSH_DENIED_COPY =
  "Notifications are blocked for this browser. You can enable them later in your browser or device settings.";

/** Shown when this device has an active browser push subscription. */
export const PUSH_ENABLED_COPY =
  "You’ll get system notifications on this device even when Pàdéyá is closed.";

/** Unsupported browser push UX — never prompt for Notification permission. */
export const UNSUPPORTED_PUSH_HELPER = {
  title: "Push notifications are not available in this browser",
  body: "You can still receive in-app notifications while using Pàdéyá. Try installing Pàdéyá to your Home Screen or use a supported desktop/Android browser for system push alerts.",
  openCenterLabel: "Open notification center",
  learnInstallLabel: "How to install",
  centerHref: "/dashboard/notifications",
} as const;

/**
 * Real push pipeline state — never treat Notification.permission alone as subscribed.
 *
 * A device is push-enabled only when permission is granted, a service worker is
 * active, pushManager.getSubscription() returns a subscription, and that
 * subscription is active on the backend for the current user.
 */
export type PushPipelineState =
  | "unsupported"
  | "permission_required"
  | "permission_denied"
  | "permission_granted_not_subscribed"
  | "subscribed"
  | "subscription_stale"
  | "install_required"
  | "admin_disabled"
  | "error";

/** Compact status labels for the settings push card. */
export type PushUiStatus =
  | "enabled"
  | "not_enabled"
  | "denied"
  | "unsupported"
  | "install_required"
  | "admin_disabled"
  | "no_active_device"
  | "permission_granted_not_subscribed"
  | "subscription_stale";

export const PUSH_UI_STATUS: Record<
  PushUiStatus,
  { label: string; body: string; tone: "success" | "warning" | "danger" | "neutral" | "accent" }
> = {
  enabled: {
    label: "Enabled",
    body: PUSH_ENABLED_COPY,
    tone: "success",
  },
  not_enabled: {
    label: "Not enabled",
    body: "System push is off on this device. Tap Enable — you’ll get alerts even when the app is closed.",
    tone: "neutral",
  },
  denied: {
    label: "Permission denied",
    body: PUSH_DENIED_COPY,
    tone: "warning",
  },
  unsupported: {
    label: "Unsupported browser",
    body: UNSUPPORTED_PUSH_HELPER.body,
    tone: "neutral",
  },
  install_required: {
    label: "Install required",
    body: IOS_PUSH_HELPER.body,
    tone: "accent",
  },
  admin_disabled: {
    label: "Admin disabled",
    body: "Push is off until a Pàdéyá admin enables it.",
    tone: "neutral",
  },
  no_active_device: {
    label: "No active device",
    body: "No active push device on this browser. Enable notifications to add one.",
    tone: "neutral",
  },
  permission_granted_not_subscribed: {
    label: "Not subscribed",
    body: "Browser permission is allowed, but this device is not subscribed for Web Push. Tap Repair to finish setup.",
    tone: "warning",
  },
  subscription_stale: {
    label: "Needs repair",
    body: "This browser’s push subscription is out of sync with Pàdéyá. Tap Repair push notifications.",
    tone: "warning",
  },
};

export type PushDiagnosticLines = {
  permission: string;
  serviceWorker: string;
  thisDevice: string;
  serverRegistration: string;
};

export function resolvePushPipelineState(input: {
  supported: boolean;
  adminEnabled: boolean;
  permission: string;
  /** Local PushManager subscription present */
  subscribed: boolean;
  /** Local subscription also active on backend for this user */
  serverRegisteredHere: boolean;
  activeDeviceCount: number;
  needsHomeScreenForPush: boolean;
  isStandalone: boolean;
  serviceWorkerActive: boolean;
  error?: string | null;
}): PushPipelineState {
  const {
    supported,
    adminEnabled,
    permission,
    subscribed,
    serverRegisteredHere,
    needsHomeScreenForPush,
    isStandalone,
    error,
  } = input;

  if (error) return "error";
  if (needsHomeScreenForPush && !isStandalone) return "install_required";
  if (!supported) return "unsupported";
  if (!adminEnabled) return "admin_disabled";
  if (permission === "denied") return "permission_denied";

  if (subscribed && serverRegisteredHere) return "subscribed";
  if (subscribed && !serverRegisteredHere) return "subscription_stale";
  if (permission === "granted" && !subscribed) {
    return "permission_granted_not_subscribed";
  }
  if (permission === "default" || permission === "unknown") {
    return "permission_required";
  }
  return "permission_required";
}

export function resolvePushUiStatus(input: {
  supported: boolean;
  adminEnabled: boolean;
  permission: string;
  subscribed: boolean;
  serverRegisteredHere?: boolean;
  activeDeviceCount: number;
  deviceCount: number;
  needsHomeScreenForPush: boolean;
  isStandalone: boolean;
  serviceWorkerActive?: boolean;
  error?: string | null;
}): PushUiStatus {
  const pipeline = resolvePushPipelineState({
    supported: input.supported,
    adminEnabled: input.adminEnabled,
    permission: input.permission,
    subscribed: input.subscribed,
    serverRegisteredHere: Boolean(input.serverRegisteredHere),
    activeDeviceCount: input.activeDeviceCount,
    needsHomeScreenForPush: input.needsHomeScreenForPush,
    isStandalone: input.isStandalone,
    serviceWorkerActive: Boolean(input.serviceWorkerActive),
    error: input.error,
  });

  if (pipeline === "subscribed") return "enabled";
  if (pipeline === "subscription_stale") return "subscription_stale";
  if (pipeline === "permission_granted_not_subscribed") {
    return "permission_granted_not_subscribed";
  }
  if (pipeline === "permission_denied") return "denied";
  if (pipeline === "install_required") return "install_required";
  if (pipeline === "unsupported" || pipeline === "error") return "unsupported";
  if (pipeline === "admin_disabled") return "admin_disabled";

  if (
    input.activeDeviceCount === 0 &&
    (input.permission === "granted" || input.deviceCount > 0)
  ) {
    return "no_active_device";
  }
  return "not_enabled";
}

export function buildPushDiagnosticLines(input: {
  permission: string | null;
  serviceWorkerActive: boolean;
  subscribed: boolean;
  serverRegisteredHere: boolean;
}): PushDiagnosticLines {
  const perm =
    input.permission === "granted"
      ? "Allowed"
      : input.permission === "denied"
        ? "Blocked"
        : input.permission === "default"
          ? "Not asked"
          : "Unavailable";
  return {
    permission: perm,
    serviceWorker: input.serviceWorkerActive ? "Active" : "Missing",
    thisDevice: input.subscribed ? "Subscribed" : "Not subscribed",
    serverRegistration: input.serverRegisteredHere ? "Active" : "Missing",
  };
}
