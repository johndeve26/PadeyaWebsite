import { ApiError } from "@/lib/api";

/** Keep in sync with backend PASSWORD_RESET_REQUEST_COOLDOWN (default 1 minute). */
export const PASSWORD_RESET_RESEND_COOLDOWN_SEC = 60;

/** Parse "Wait N seconds before..." from password-reset rate limit responses. */
export function passwordResetCooldownSeconds(err: ApiError): number | null {
  if (err.status !== 429) return null;
  const match = /wait\s+(\d+)\s+seconds/i.exec(err.detail);
  if (!match) return null;
  const n = Number.parseInt(match[1] ?? "", 10);
  return Number.isFinite(n) && n > 0 ? n : null;
}

export function formatPasswordResetCooldown(seconds: number): string {
  if (seconds >= 120) {
    const mins = Math.ceil(seconds / 60);
    return `${mins} minute${mins === 1 ? "" : "s"}`;
  }
  if (seconds >= 60) {
    return "1 minute";
  }
  return `${seconds} second${seconds === 1 ? "" : "s"}`;
}
