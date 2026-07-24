/**
 * Shared display formatting for dates and currency across Pàdéyá UI.
 * Prefer these over ad-hoc toLocaleString / ₦ concatenation.
 */

const NGN = "en-NG";
/** Product default for event times (SSR + client must match). */
const DISPLAY_TZ = "Africa/Lagos";
const DISPLAY_LOCALE = "en-GB";

function formatInstantParts(
  d: Date,
  timeZone: string,
  withTime: boolean,
): string {
  const formatter = new Intl.DateTimeFormat(DISPLAY_LOCALE, {
    timeZone,
    day: "numeric",
    month: "short",
    year: "numeric",
    ...(withTime
      ? { hour: "2-digit", minute: "2-digit", hour12: false }
      : {}),
  });
  const parts = formatter.formatToParts(d);
  const pick = (type: Intl.DateTimeFormatPartTypes) =>
    parts.find((p) => p.type === type)?.value ?? "";
  const date = `${pick("day")} ${pick("month")} ${pick("year")}`;
  if (!withTime) return date;
  return `${date}, ${pick("hour")}:${pick("minute")}`;
}

export function formatNgn(
  value: string | number | null | undefined,
  opts?: { fractionDigits?: number },
): string {
  const n = Number(value ?? 0);
  if (!Number.isFinite(n)) return "₦0";
  const digits = opts?.fractionDigits ?? (Number.isInteger(n) ? 0 : 2);
  return `₦${n.toLocaleString(NGN, {
    minimumFractionDigits: 0,
    maximumFractionDigits: digits,
  })}`;
}

export function formatDateTime(
  value: string | Date | null | undefined,
  timeZone: string = DISPLAY_TZ,
): string {
  if (value == null || value === "") return "—";
  const d = typeof value === "string" ? new Date(value) : value;
  if (Number.isNaN(d.getTime())) return "—";
  return formatInstantParts(d, timeZone, true);
}

export function formatDate(
  value: string | Date | null | undefined,
  timeZone: string = DISPLAY_TZ,
): string {
  if (value == null || value === "") return "—";
  const d = typeof value === "string" ? new Date(value) : value;
  if (Number.isNaN(d.getTime())) return "—";
  return formatInstantParts(d, timeZone, false);
}

export function formatPercent(value: string | number | null | undefined): string {
  const n = Number(value ?? 0);
  if (!Number.isFinite(n)) return "0%";
  return `${n.toLocaleString(NGN, { maximumFractionDigits: 1 })}%`;
}

/** Privacy-safe email for ticket passes: fan2@demo… → fa•••@demo… */
export function maskEmail(email: string | null | undefined): string {
  const raw = (email ?? "").trim();
  if (!raw || !raw.includes("@")) return "—";
  const [local, domain] = raw.split("@");
  if (!local || !domain) return "—";
  const keep = Math.min(2, local.length);
  return `${local.slice(0, keep)}•••@${domain}`;
}

/** Privacy-safe display name: "Jane Doe" → "Jane D•••"; short names → "Ja•••". */
export function maskDisplayName(name: string | null | undefined): string {
  const raw = (name ?? "").trim();
  if (!raw) return "User";
  const parts = raw.split(/\s+/).filter(Boolean);
  if (parts.length === 1) {
    const word = parts[0];
    if (word.length <= 2) return `${word[0] ?? "?"}•••`;
    return `${word.slice(0, 2)}•••`;
  }
  const first = parts[0];
  const lastInitial = parts[parts.length - 1]?.[0] ?? "?";
  return `${first} ${lastInitial}•••`;
}

/** Remaining time label for impersonation countdown. */
export function formatRemainingDuration(ms: number): string {
  if (ms <= 0) return "Expired";
  const totalSec = Math.floor(ms / 1000);
  const hours = Math.floor(totalSec / 3600);
  const minutes = Math.floor((totalSec % 3600) / 60);
  const seconds = totalSec % 60;
  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  if (minutes > 0) {
    return `${minutes}m ${seconds.toString().padStart(2, "0")}s`;
  }
  return `${seconds}s`;
}
