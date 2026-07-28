/**
 * Safe in-app toast copy — never surface private chat/venue/payment bodies.
 */

export type ToastSafeCopy = {
  title: string;
  description?: string;
};

const KIND_FALLBACK: Array<{ match: RegExp; title: string; description?: string }> = [
  {
    match: /^ticket\./i,
    title: "Ticket ready",
    description: "Your tickets are ready on Pàdéyá.",
  },
  {
    match: /^merch\.(ready_for_pickup|confirmed)/i,
    title: "Merch pickup ready",
    description: "Your pickup code is ready at the merch stand.",
  },
  {
    match: /^merch\./i,
    title: "Merch update",
    description: "You have a merch update on Pàdéyá.",
  },
  {
    match: /^fan_connect\.request/i,
    title: "Fan Connect request",
    description: "Someone sent you a Fan Connect request.",
  },
  {
    match: /^fan_connect\./i,
    title: "Fan Connect",
    description: "You have a Fan Connect update.",
  },
  {
    match: /^sponsor\./i,
    title: "Sponsor inquiry received",
    description: "Check sponsorships on Pàdéyá.",
  },
  {
    match: /^review\./i,
    title: "Review update",
    description: "You have a review update on Pàdéyá.",
  },
  {
    match: /^host\./i,
    title: "Host activity",
    description: "Something new happened on your host account.",
  },
  {
    match: /^admin\.user_registered$/i,
    title: "New user registered",
    description: "A new account joined Pàdéyá.",
  },
  {
    match: /^admin\.ticket_sale$/i,
    title: "New ticket sale",
    description: "A verified ticket order was paid.",
  },
  {
    match: /^admin\./i,
    title: "Admin alert",
    description: "Open Pàdéyá admin for details.",
  },
];

const UNSAFE_BODY =
  /https?:\/\/|\b[\w.+-]+@[\w.-]+\.\w+\b|\/media\/|attachment|venue|address|paystack|order[_-]?\w{6,}/i;

function isSafeNotificationText(text: string): boolean {
  const t = text.trim();
  return t.length > 0 && !UNSAFE_BODY.test(t);
}

function kindFallbackCopy(kind: string): ToastSafeCopy | null {
  for (const rule of KIND_FALLBACK) {
    if (rule.match.test(kind)) {
      return { title: rule.title, description: rule.description };
    }
  }
  return null;
}

function isPrivateMessageKind(kind: string): boolean {
  const k = kind.toLowerCase();
  return (
    k.startsWith("message") ||
    k.startsWith("messaging.") ||
    k === "new_message" ||
    k === "message_request" ||
    k.includes("attachment_received")
  );
}

export function isMessageInboxNotificationKind(kind: string): boolean {
  return isPrivateMessageKind(kind);
}

export function notificationKindLabel(kind: string): string {
  const k = kind.toLowerCase();
  if (k.startsWith("ticket")) return "Tickets";
  if (k.startsWith("merch") || k.includes("post_event")) return "Merch";
  if (isPrivateMessageKind(k)) return "Messages";
  if (k.startsWith("fan_connect")) return "Fan Connect";
  if (k.startsWith("host") || k.startsWith("review")) return "Host";
  if (k.startsWith("sponsor")) return "Sponsor";
  if (k.startsWith("admin")) return "Admin";
  return "Alert";
}

export function safeToastCopy(input: {
  kind: string;
  title?: string | null;
  body?: string | null;
}): ToastSafeCopy {
  const kind = input.kind || "";

  if (isPrivateMessageKind(kind)) {
    return { title: "New message", description: "Open Pàdéyá to read it." };
  }

  const storedTitle = (input.title || "").trim().slice(0, 80);
  const storedBody = (input.body || "").trim();
  const fallback = kindFallbackCopy(kind);

  const title = isSafeNotificationText(storedTitle)
    ? storedTitle
    : (fallback?.title ?? "New notification");

  let description: string | undefined;
  if (isSafeNotificationText(storedBody)) {
    description = storedBody.slice(0, 120);
  } else if (fallback?.description) {
    description = fallback.description;
  } else if (!isSafeNotificationText(storedTitle)) {
    description = "Open to view details.";
  }

  return { title, description };
}

/** Same-origin relative path only — reject vault/checkout and external URLs. */
export function safeToastActionHref(
  linkPath: string | null | undefined,
  fallback = "/dashboard/notifications",
): string {
  const path = (linkPath || "").trim();
  if (!path.startsWith("/") || path.startsWith("//")) return fallback;
  if (/^\/(vault|checkout)(\/|$)/i.test(path)) return fallback;
  if (/javascript:|data:/i.test(path)) return fallback;
  return path;
}
