/** Manual invite text when email is delayed or the recipient prefers a DM. */
export function buildTransferInviteMessage(
  recipientEmail: string,
  options?: {
    origin?: string;
    claimPath?: string | null;
  },
): string {
  const trimmed = recipientEmail.trim().toLowerCase();
  const origin =
    options?.origin?.replace(/\/$/, "") ||
    (typeof window !== "undefined"
      ? window.location.origin
      : "https://padeya.smartlancedesigns.com");
  const claimPath = options?.claimPath?.trim() || null;
  const next = encodeURIComponent(claimPath || "/dashboard/tickets");
  const registerLink = `${origin}/register?email=${encodeURIComponent(trimmed)}&next=${next}`;
  const lines = [
    "I'm transferring a Pàdéyá event ticket to you.",
    `Create a free account with ${trimmed} here:`,
    registerLink,
  ];
  if (claimPath) {
    const claimUrl = claimPath.startsWith("http")
      ? claimPath
      : `${origin}${claimPath.startsWith("/") ? claimPath : `/${claimPath}`}`;
    lines.push("Claim your ticket here:");
    lines.push(claimUrl);
  }
  lines.push("Then tell me to complete the transfer.");
  return lines.join("\n");
}

export function siteOrigin(origin?: string): string {
  return (
    origin?.replace(/\/$/, "") ||
    (typeof window !== "undefined"
      ? window.location.origin
      : "https://padeya.smartlancedesigns.com")
  );
}

export function absoluteClaimUrl(
  claimPath: string,
  origin?: string,
): string {
  const base = siteOrigin(origin);
  if (claimPath.startsWith("http://") || claimPath.startsWith("https://")) {
    return claimPath;
  }
  return `${base}${claimPath.startsWith("/") ? claimPath : `/${claimPath}`}`;
}

export function buildRegisterLink(
  recipientEmail: string,
  claimPath?: string | null,
  origin?: string,
): string {
  const trimmed = recipientEmail.trim().toLowerCase();
  const base = siteOrigin(origin);
  const next = encodeURIComponent(claimPath || "/dashboard/tickets");
  return `${base}/register?email=${encodeURIComponent(trimmed)}&next=${next}`;
}
