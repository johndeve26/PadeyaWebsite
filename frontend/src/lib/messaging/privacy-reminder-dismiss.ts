const STORAGE_KEY = "padeya.messaging.privacy_reminder_hidden_until";

/** Next local midnight (start of tomorrow). */
export function nextLocalMidnightMs(from: Date = new Date()): number {
  const next = new Date(from);
  next.setHours(24, 0, 0, 0);
  return next.getTime();
}

export function isMessagingPrivacyReminderDismissed(): boolean {
  if (typeof window === "undefined") return false;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return false;
    const until = Number(raw);
    return Number.isFinite(until) && Date.now() < until;
  } catch {
    return false;
  }
}

export function dismissMessagingPrivacyReminderUntilMidnight(): number {
  const until = nextLocalMidnightMs();
  try {
    window.localStorage.setItem(STORAGE_KEY, String(until));
  } catch {
    /* quota / private mode */
  }
  return until;
}

export function msUntilMessagingPrivacyReminderReturns(): number {
  if (typeof window === "undefined") return 0;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return 0;
    const until = Number(raw);
    if (!Number.isFinite(until)) return 0;
    return Math.max(0, until - Date.now());
  } catch {
    return 0;
  }
}
