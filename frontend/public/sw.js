/* Pàdéyá service worker — cache shell assets only; never Vault/API/auth.
 *
 * Push: receive → show safe title/body → click opens action_url in-app.
 * Never trust or surface sensitive fields from the payload.
 */

const VERSION = "padeya-pwa-v24";
const PRECACHE = [
  "/offline",
  "/manifest.webmanifest",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
  "/icons/apple-touch-icon.png",
  "/brand/padeya-logo-dark-v3.png",
  "/brand/padeya-logo-light-v3.png",
];

const NEVER_CACHE_PATH =
  /\/(api|vault|checkout|login|register|admin|support|finance)(\/|$)/i;

const DEFAULT_ACTION = "/dashboard/notifications";
const DEFAULT_ICON = "/icons/icon-192.png";
const DEFAULT_BADGE = "/icons/icon-192.png";

/** Only these keys may appear on a push notification. */
const ALLOWED_PUSH_KEYS = new Set([
  "title",
  "body",
  "action_url",
  "url",
  "notification_id",
  "tag",
  "timestamp",
  "icon",
  "badge",
  "kind",
]);

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(VERSION).then((cache) => cache.addAll(PRECACHE)).then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== VERSION).map((k) => caches.delete(k))),
    ).then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  if (NEVER_CACHE_PATH.test(url.pathname)) return;
  if (url.pathname.startsWith("/api/")) return;

  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((response) => response)
        .catch(() => caches.match("/offline")),
    );
    return;
  }

  if (
    url.pathname.startsWith("/icons/") ||
    url.pathname.startsWith("/brand/") ||
    url.pathname === "/manifest.webmanifest"
  ) {
    event.respondWith(
      caches.match(request).then((cached) => {
        if (cached) return cached;
        return fetch(request).then((response) => {
          const copy = response.clone();
          void caches.open(VERSION).then((cache) => cache.put(request, copy));
          return response;
        });
      }),
    );
  }
});

/**
 * Normalize push JSON into the allowed public fields only.
 * Accepts legacy `url` as alias for `action_url`.
 */
function scrubCopy(text) {
  return String(text || "")
    .replace(/https?:\/\/\S+|www\.\S+/gi, "")
    .replace(/\b[\w.+-]+@[\w.-]+\.\w+\b/g, "")
    .replace(/\b(?:\+?\d[\d\s().-]{7,}\d)\b/g, "")
    .replace(/\/(?:vault|api|messages\/attachments|media)\/\S+/gi, "")
    .replace(/\b(?:order|pay|txn|ref|pickup|entry)[_-]?[A-Z0-9]{6,}\b/gi, "")
    .replace(/\b(?:code|pin|otp)[:\s#-]*[A-Z0-9]{4,}\b/gi, "")
    .replace(/\b(?=[A-Z0-9]*\d)[A-Z0-9]{6,12}\b/gi, "")
    .replace(/\s{2,}/g, " ")
    .trim()
    .slice(0, 240);
}

function sanitizePushPayload(raw) {
  const src = raw && typeof raw === "object" ? raw : {};
  const cleaned = {};
  for (const key of Object.keys(src)) {
    if (!ALLOWED_PUSH_KEYS.has(key)) continue;
    cleaned[key] = src[key];
  }

  const title = scrubCopy(cleaned.title || "Pàdéyá").slice(0, 120) || "Pàdéyá";
  let body = scrubCopy(
    cleaned.body || "You have a new notification on Pàdéyá.",
  );

  const action_url = safeActionUrl(
    cleaned.action_url || cleaned.url || DEFAULT_ACTION,
  );
  const notification_id = cleaned.notification_id
    ? String(cleaned.notification_id).slice(0, 80)
    : null;
  const tag = String(
    cleaned.tag || notification_id || cleaned.kind || "padeya-notification",
  ).slice(0, 80);
  const timestamp = Number(cleaned.timestamp) || Date.now();
  const icon = safeAssetUrl(cleaned.icon, DEFAULT_ICON);
  const badge = safeAssetUrl(cleaned.badge, DEFAULT_BADGE);

  return {
    title,
    body: body || "You have a new notification on Pàdéyá.",
    action_url,
    notification_id,
    tag,
    timestamp,
    icon,
    badge,
  };
}

/** Only same-origin relative paths inside Pàdéyá (never external / javascript:). */
function safeActionUrl(value) {
  try {
    const raw = String(value || DEFAULT_ACTION).trim();
    if (!raw || raw.startsWith("javascript:") || raw.startsWith("data:")) {
      return DEFAULT_ACTION;
    }
    const url = new URL(raw, self.location.origin);
    if (url.origin !== self.location.origin) return DEFAULT_ACTION;
    // Never deep-link push into Vault or checkout.
    if (/\/(vault|checkout)(\/|$)/i.test(url.pathname)) return DEFAULT_ACTION;
    const path = `${url.pathname}${url.search}${url.hash}`;
    return path || DEFAULT_ACTION;
  } catch {
    return DEFAULT_ACTION;
  }
}

function safeAssetUrl(value, fallback) {
  try {
    const raw = String(value || fallback).trim();
    const url = new URL(raw, self.location.origin);
    if (url.origin !== self.location.origin) return fallback;
    if (!(url.pathname.startsWith("/icons/") || url.pathname.startsWith("/brand/"))) {
      return fallback;
    }
    return url.pathname;
  } catch {
    return fallback;
  }
}

function parsePushEventData(event) {
  if (!event.data) {
    return sanitizePushPayload({});
  }
  try {
    return sanitizePushPayload(event.data.json());
  } catch {
    try {
      const text = event.data.text();
      return sanitizePushPayload({
        title: "Pàdéyá",
        body: String(text || "").slice(0, 240),
      });
    } catch {
      return sanitizePushPayload({});
    }
  }
}

self.addEventListener("push", (event) => {
  const data = parsePushEventData(event);
  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: data.icon,
      badge: data.badge,
      tag: data.tag,
      timestamp: data.timestamp,
      renotify: false,
      data: {
        action_url: data.action_url,
        notification_id: data.notification_id,
        tag: data.tag,
        timestamp: data.timestamp,
      },
    }),
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const raw =
    (event.notification.data && event.notification.data.action_url) ||
    DEFAULT_ACTION;
  const path = safeActionUrl(raw);
  const target = new URL(path, self.location.origin).href;

  event.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true }).then((list) => {
      // Prefer an existing Pàdéyá tab; navigate it, then focus.
      for (const client of list) {
        if (!client.url || !client.url.startsWith(self.location.origin)) continue;
        if ("focus" in client) {
          if ("navigate" in client && typeof client.navigate === "function") {
            return client
              .navigate(target)
              .then((navigated) => {
                const c = navigated || client;
                return c.focus ? c.focus() : client.focus();
              })
              .catch(() => client.focus());
          }
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(target);
      }
      return undefined;
    }),
  );
});

self.addEventListener("notificationclose", () => {
  /* no-op — do not ping APIs with private context */
});
