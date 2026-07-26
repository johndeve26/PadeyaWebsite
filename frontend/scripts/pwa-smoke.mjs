/**
 * Phase 18 PWA smoke checks — no browser required.
 * Run: node scripts/pwa-smoke.mjs
 */

import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");
const publicDir = path.join(root, "public");

function read(rel) {
  return fs.readFileSync(path.join(root, rel), "utf8");
}

function exists(rel) {
  return fs.existsSync(path.join(root, rel));
}

// --- Manifest valid ---
const manifestPath = path.join(publicDir, "manifest.webmanifest");
assert.ok(fs.existsSync(manifestPath), "manifest.webmanifest missing");
const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
assert.equal(manifest.name, "Pàdéyá");
assert.equal(manifest.display, "standalone");
assert.ok(manifest.start_url);
assert.ok(manifest.theme_color, "manifest.theme_color required");
assert.ok(manifest.background_color, "manifest.background_color required");
assert.match(manifest.theme_color, /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/);
assert.match(manifest.background_color, /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/);
assert.ok(Array.isArray(manifest.icons) && manifest.icons.length >= 2);
for (const icon of manifest.icons) {
  const iconFile = path.join(publicDir, icon.src.replace(/^\//, ""));
  assert.ok(fs.existsSync(iconFile), `icon missing: ${icon.src}`);
  assert.ok(fs.statSync(iconFile).size > 100, `icon too small: ${icon.src}`);
}

// --- Service worker present & safe ---
const sw = read("public/sw.js");
assert.match(sw, /padeya-pwa-v25/);
assert.match(sw, /addEventListener\("push"/);
assert.match(sw, /addEventListener\("notificationclick"/);
assert.match(sw, /push_received_service_worker/);
assert.match(sw, /action_url/);
assert.match(sw, /sanitizePushPayload/);
assert.match(sw, /ALLOWED_PUSH_KEYS/);
assert.match(sw, /safeActionUrl/);
assert.match(sw, /clients\.matchAll/);
assert.match(sw, /NEVER_CACHE_PATH/);
assert.match(sw, /vault/i);
assert.match(sw, /checkout/i);
assert.doesNotMatch(sw, /\/api\/v1\/vault/);

// --- Offline ticket + merch QR cache helpers ---
assert.ok(exists("src/lib/pwa/offline-ticket-cache.ts"));
assert.ok(exists("src/lib/pwa/offline-merch-cache.ts"));
assert.ok(exists("src/lib/pwa/offline-scanner-queue.ts"));
const ticketCache = read("src/lib/pwa/offline-ticket-cache.ts");
assert.match(ticketCache, /cacheTicketForOffline/);
assert.match(ticketCache, /Never use this for Vault/i);
const merchCache = read("src/lib/pwa/offline-merch-cache.ts");
assert.match(merchCache, /cacheMerchPickupForOffline/);
assert.match(merchCache, /padeya\.merch\.pickup/);
assert.match(merchCache, /Never cache shipping/i);
assert.doesNotMatch(merchCache, /shipping_address:\s*row/);

// --- Mobile layout building blocks ---
assert.ok(exists("src/components/layout/MobileBottomNav.tsx"));
assert.ok(exists("src/components/layout/HostScannerDock.tsx"));
assert.ok(exists("src/components/pwa/InstallPrompt.tsx"));
assert.ok(exists("src/app/offline/page.tsx"));

const ticketPage = read("src/app/dashboard/tickets/[id]/page.tsx");
assert.match(ticketPage, /TicketQrPanel|QRCodeSVG/);
assert.match(ticketPage, /readCachedTicket/);
assert.ok(
  exists("src/components/tickets/TicketQrPanel.tsx"),
  "TicketQrPanel missing",
);
const merchDetailPage = read(
  "src/app/dashboard/merchandise/[orderItemId]/page.tsx",
);
assert.match(merchDetailPage, /MerchPickupQr/);
assert.match(merchDetailPage, /readCachedMerchPickup/);
assert.match(merchDetailPage, /cacheMerchPickupForOffline/);
assert.ok(
  exists("src/components/merch/MerchPickupQr.tsx"),
  "MerchPickupQr missing",
);
const merchQr = read("src/components/merch/MerchPickupQr.tsx");
assert.match(merchQr, /padeya\.merch\.pickup/);
assert.match(merchQr, /bgColor="#ffffff"/);
assert.match(merchQr, /fgColor="#000000"/);
assert.ok(
  exists("src/components/merch/host/HostMerchPickupDesk.tsx"),
  "HostMerchPickupDesk missing",
);
const merchDesk = read("src/components/merch/host/HostMerchPickupDesk.tsx");
assert.match(merchDesk, /scanMerchPickup/);
assert.match(merchDesk, /padeya\.merch\.pickup/);
const qrPanel = read("src/components/tickets/TicketQrPanel.tsx");
assert.match(qrPanel, /bgColor="#ffffff"/);
assert.match(qrPanel, /fgColor="#000000"/);
assert.match(qrPanel, /bg-paper|bg-\[#ffffff\]/);

const themeLib = read("src/lib/theme.ts");
assert.match(themeLib, /THEME_COLOR/);
assert.match(themeLib, /applyThemeColor|theme-color/);

const layout = read("src/app/layout.tsx");
assert.match(layout, /THEME_COLOR/);
assert.match(layout, /prefers-color-scheme/);
assert.match(layout, /manifest\.webmanifest/);
assert.match(layout, /PwaProvider/);
assert.match(layout, /MobileBottomNav/);
const pwaProvider = read("src/components/pwa/PwaProvider.tsx");
assert.match(pwaProvider, /shouldRegisterServiceWorker|register\("\/sw\.js"\)/);
assert.match(pwaProvider, /localhost|isSecureContext/);
assert.match(
  pwaProvider,
  /unregister/,
  "localhost next dev still unregisters SW for HMR",
);

const offlinePage = read("src/app/offline/page.tsx");
assert.match(offlinePage, /bg-background|dark:/);

const scanner = read("src/components/checkin/CheckInWorkspace.tsx");
assert.match(scanner, /enqueueScannerScan/);
assert.match(scanner, /flushScannerQueue/);
assert.match(scanner, /Offline/);

const checkout = read("src/app/events/[slug]/checkout/page.tsx");
assert.match(checkout, /Mobile sticky checkout|fixed inset-x-0 bottom-0/);

// --- Notification settings + push UX ---
assert.ok(exists("src/app/dashboard/settings/notifications/page.tsx"));
assert.ok(exists("src/app/dashboard/settings/page.tsx"));
assert.ok(exists("src/components/notifications/PushSettingsPanel.tsx"));
assert.ok(
  exists("src/components/notifications/NotificationPreferencesSections.tsx"),
);
assert.ok(exists("src/hooks/usePushNotifications.ts"));
const settingsPage = read("src/app/dashboard/settings/page.tsx");
assert.match(settingsPage, /NotificationPreferencesSections/);
assert.doesNotMatch(
  settingsPage,
  /Email notifications<\/Button>/,
  "email + push are inline on settings — no hop button required",
);
const notifSettings = read("src/app/dashboard/settings/notifications/page.tsx");
assert.match(notifSettings, /NotificationPreferencesSections/);
const notifSections = read(
  "src/components/notifications/NotificationPreferencesSections.tsx",
);
assert.match(notifSections, /PushSettingsPanel/);
assert.match(notifSections, /fetchPushPreferences|updatePushPreferences/);
assert.match(notifSections, /push_enabled/);
assert.match(notifSections, /Email notifications/);
assert.match(notifSections, /min-w-0/);
assert.doesNotMatch(
  notifSections,
  /PushPermissionPrompt/,
  "settings page uses PushSettingsPanel as the single push card",
);
const pushPanel = read("src/components/notifications/PushSettingsPanel.tsx");
assert.match(pushPanel, /Enable notifications/);
assert.match(pushPanel, /Repair push notifications/);
assert.match(pushPanel, /resolvePushUiStatus|PUSH_UI_STATUS/);
assert.match(pushPanel, /Push notifications/);
assert.match(pushPanel, /Permission|Service worker|This device|Server registration/);
assert.match(pushPanel, /PushInstallDetails|How to install/);
assert.match(pushPanel, /w-full sm:w-auto/);
assert.match(pushPanel, /overflow-hidden|min-w-0/);
assert.match(pushPanel, /usePushNotifications/);
assert.match(pushPanel, /isStandalone|needsHomeScreenForPush/);
assert.match(pushPanel, /Last active|deviceLastActive/);
assert.match(pushPanel, /Disable on this device/);
assert.match(pushPanel, /Remove/);
assert.match(
  pushPanel,
  /install_required|unsupported|admin_disabled|no_active_device|permission_granted_not_subscribed|subscription_stale/,
);

const installDetails = read("src/components/notifications/PushInstallDetails.tsx");
assert.match(installDetails, /<details/);
assert.match(installDetails, /How to install/);
assert.match(installDetails, /IOS_PUSH_HELPER/);

const unsupportedUi = read("src/components/notifications/PushUnsupportedState.tsx");
assert.match(
  unsupportedUi,
  /Push notifications are not available in this browser|UNSUPPORTED_PUSH_HELPER/,
);
assert.match(unsupportedUi, /Open notification center|openCenterLabel/);
assert.match(unsupportedUi, /PushInstallDetails|How to install/);
assert.doesNotMatch(
  unsupportedUi,
  /requestPermission|push\.enable|Notification\.request/,
  "unsupported state must not request browser permission",
);

const pushDevice = read("src/lib/push-device.ts");
assert.match(pushDevice, /needsHomeScreenForPush/);
assert.match(pushDevice, /isAppleMobileDevice|iPhone|iPad/);
assert.match(pushDevice, /display-mode: standalone/);
assert.match(pushDevice, /navigator\.standalone|standalone\?:/);
assert.match(pushDevice, /PushManager/);
assert.match(pushDevice, /serviceWorker/);
assert.match(pushDevice, /Notification\.permission|readNotificationPermission/);
assert.match(pushDevice, /default.*granted.*denied|PushNotificationPermission/);
assert.match(pushDevice, /UX-only|UX guidance|not for security|authorization/i);
assert.match(pushDevice, /PUSH_DENIED_COPY/);
assert.match(
  pushDevice,
  /Notifications are blocked for this browser\. You can enable them later/,
);
assert.match(pushDevice, /PUSH_ENABLED_COPY/);
assert.match(
  pushDevice,
  /You’ll get system notifications on this device even when Pàdéyá is closed/,
);
assert.match(pushDevice, /resolvePushUiStatus/);
assert.match(pushDevice, /resolvePushPipelineState|permission_granted_not_subscribed/);
assert.match(pushDevice, /subscription_stale/);
assert.match(pushDevice, /install_required/);
assert.match(pushDevice, /admin_disabled/);
assert.match(pushDevice, /no_active_device/);
assert.match(pushDevice, /buildPushDiagnosticLines/);
const pushSub = read("src/lib/push-subscription.ts");
assert.match(pushSub, /ensurePushSubscription|userVisibleOnly/);
assert.match(pushSub, /urlBase64ToUint8Array/);
assert.match(pushSub, /Missing VAPID public key/);
assert.doesNotMatch(pushSub, /VAPID_PRIVATE|private_key/);
const pushHook = read("src/hooks/usePushNotifications.ts");
assert.match(pushHook, /repair/);
assert.match(pushHook, /ensurePushSubscription/);
assert.match(pushHook, /persistSubscription/);
assert.match(pushHook, /requestPermission/);
assert.match(pushHook, /never prompts again|reuses an already-granted permission/);
assert.match(pushDevice, /IOS_PUSH_HELPER/);
assert.match(
  pushDevice,
  /Install Pàdéyá to enable push notifications/,
);
assert.match(
  pushDevice,
  /Chrome, Firefox, Edge, and Safari on iPhone may all require the Home Screen app flow/,
);
assert.match(
  pushDevice,
  /Apple only allows web push for installed Home Screen web apps/,
);
assert.doesNotMatch(pushDevice, /Safari only|Safari is broken/i);
assert.doesNotMatch(
  pushDevice,
  /Chrome will definitely work in a normal tab/i,
);
const homeHint = read("src/components/notifications/PushHomeScreenHint.tsx");
assert.match(homeHint, /IOS_PUSH_HELPER/);
assert.match(homeHint, /Install Pàdéyá to enable push notifications|IOS_PUSH_HELPER\.title/);
assert.doesNotMatch(homeHint, /only works in Safari|Safari is broken/i);
const installPrompt = read("src/components/pwa/InstallPrompt.tsx");
assert.match(installPrompt, /needsHomeScreenForPush|IOS_PUSH_HELPER/);
assert.match(installPrompt, /IOS_PUSH_HELPER/);

const adminPush = read("src/app/admin/push/settings/page.tsx");
assert.match(adminPush, /RequireAuth/);
assert.match(adminPush, /roles=\{\["super_admin"\]\}/);
const adminPushAlias = read("src/app/admin/settings/push/page.tsx");
assert.match(adminPushAlias, /\/admin\/push\/settings/);
assert.match(adminPushAlias, /roles=\{\["super_admin"\]\}/);

const toastLib = read("src/lib/notifications-toast.ts");
assert.match(toastLib, /safeToastActionHref/);
assert.match(toastLib, /vault|checkout/);
const toastBridge = read("src/components/notifications/NotificationPopupBridge.tsx");
assert.match(toastBridge, /safeToastActionHref/);
assert.match(pushHook, /Notification\.requestPermission/);
assert.match(pushHook, /isPushApiSupported|pushSupported/);
assert.match(pushHook, /unsupported/);
assert.match(
  pushHook,
  /Only after Enable notifications|never on page load/,
);
assert.match(pushHook, /async function enable|const enable = /);
assert.match(pushHook, /detectPushDeviceContext|needsHomeScreenForPush/);
assert.match(pushHook, /Home Screen/);
assert.match(pushHook, /UX detection only|not used for security/i);
assert.match(
  pushHook,
  /next === "denied"/,
  "denied after Enable shows denied state without hard error",
);
// requestPermission must only appear inside enable(), not refresh()
const refreshIdx = pushHook.indexOf("const refresh");
const enableIdx = pushHook.indexOf("const enable");
const requestInRefresh = pushHook
  .slice(refreshIdx, enableIdx)
  .includes("requestPermission");
assert.equal(
  requestInRefresh,
  false,
  "refresh() must not call Notification.requestPermission",
);

const pushPrompt = read("src/components/notifications/PushPermissionPrompt.tsx");
assert.match(
  pushPrompt,
  /Never show the Enable|when push is unsupported/,
);
assert.match(pushDevice, /UNSUPPORTED_PUSH_HELPER/);
assert.match(
  pushDevice,
  /Push notifications are not available in this browser/,
);

// --- Service worker push + click opens action_url ---
assert.match(sw, /self\.addEventListener\("push"/);
assert.match(sw, /showNotification/);
assert.match(sw, /self\.addEventListener\("notificationclick"/);
assert.match(sw, /action_url/);
assert.match(sw, /clients\.openWindow|client\.navigate|clients\.matchAll/);
assert.doesNotMatch(sw, /pickup_code|shipping_address|message_body/);

// --- In-app toast + notification center ---
assert.ok(exists("src/components/notifications/NotificationToastProvider.tsx"));
assert.ok(exists("src/components/notifications/NotificationPopupBridge.tsx"));
assert.ok(exists("src/app/dashboard/notifications/page.tsx"));
const toastProvider = read(
  "src/components/notifications/NotificationToastProvider.tsx",
);
assert.match(toastProvider, /NotificationPopupBridge/);
assert.match(toastProvider, /ToastProvider/);
const popupBridge = read(
  "src/components/notifications/NotificationPopupBridge.tsx",
);
assert.match(popupBridge, /toast\.push/);
assert.match(popupBridge, /safeToastCopy/);
assert.match(popupBridge, /notification\.created|fetchPopupNotifications/);
const notifCenterPage = read("src/app/dashboard/notifications/page.tsx");
assert.match(notifCenterPage, /AccountNotificationsPanel/);
assert.match(notifCenterPage, /dashboard\/settings\/notifications/);
const notifCenter = read(
  "src/components/notifications/AccountNotificationsPanel.tsx",
);
assert.match(notifCenter, /fetchNotifications/);
assert.match(notifCenter, /markNotificationRead/);
assert.match(notifCenter, /markAllNotificationsRead/);
assert.match(notifCenter, /Mark read/);
assert.match(notifCenter, /Mark all read/);
assert.match(notifCenter, /Fan Connect/);
const layoutSrc = read("src/app/layout.tsx");
assert.match(layoutSrc, /NotificationToastProvider/);

// --- Mobile alerts + dark/light ---
const mobileNav = read("src/components/layout/MobileBottomNav.tsx");
assert.match(mobileNav, /dashboard\/notifications/);
assert.match(mobileNav, /Alerts/);
assert.match(mobileNav, /md:hidden/);
assert.match(mobileNav, /useUnreadNotifications/);
assert.match(themeLib, /light|dark/);
assert.match(layoutSrc, /ThemeProvider|ThemeScript/);

console.log("PWA smoke checks passed:");
console.log("  ✓ manifest valid + icons present");
console.log("  ✓ theme-color light/dark + ThemeScript sync");
console.log("  ✓ mobile layout components present");
console.log("  ✓ ticket page offline + high-contrast QR panel");
console.log("  ✓ merch pickup QR offline cache (no shipping)");
console.log("  ✓ scanner offline queue foundation");
console.log("  ✓ offline fallback page (theme-aware)");
console.log("  ✓ notification settings + push enable/denied/unsupported");
console.log("  ✓ SW push receive + notificationclick → action_url");
console.log("  ✓ in-app toast + notification center mark-read");
console.log("  ✓ mobile alerts nav + theme wiring");
