/** Shared Support Center labels / badge helpers (client + server safe). */

export const SUPPORT_STATUS_OPTIONS = [
  { value: "all", label: "All statuses" },
  { value: "open", label: "Open" },
  { value: "pending", label: "Pending" },
  { value: "waiting_on_user", label: "Waiting on user" },
  { value: "escalated", label: "Escalated" },
  { value: "resolved", label: "Resolved" },
  { value: "closed", label: "Closed" },
  { value: "archived", label: "Archived" },
] as const;

export const SUPPORT_PRIORITY_OPTIONS = [
  { value: "all", label: "All priorities" },
  { value: "low", label: "Low" },
  { value: "normal", label: "Normal" },
  { value: "high", label: "High" },
  { value: "urgent", label: "Urgent" },
] as const;

export const SUPPORT_CONTEXT_OPTIONS = [
  { value: "all", label: "All contexts" },
  { value: "fan", label: "Fan" },
  { value: "host", label: "Host" },
  { value: "visitor", label: "Visitor" },
  { value: "admin", label: "Admin" },
] as const;

export const FALLBACK_SUPPORT_CATEGORIES = [
  { value: "account_login", label: "Account / login" },
  { value: "tickets_orders", label: "Tickets / orders" },
  { value: "payments_refunds", label: "Payments / refunds" },
  { value: "event_issue", label: "Event issue" },
  { value: "host_issue", label: "Host issue" },
  { value: "merch", label: "Merch" },
  { value: "fan_connect", label: "Fan Connect" },
  { value: "messaging_abuse", label: "Messaging / report abuse" },
  { value: "sponsorship", label: "Sponsorship" },
  { value: "ambassador", label: "Ambassador" },
  { value: "technical", label: "Technical issue" },
  { value: "other", label: "Other" },
] as const;

export function priorityTone(
  priority: string,
): "neutral" | "warning" | "danger" | "accent" {
  const key = priority.toLowerCase();
  if (key === "urgent") return "danger";
  if (key === "high") return "warning";
  if (key === "low") return "neutral";
  return "accent";
}

export function formatSupportLabel(value: string): string {
  return value.replace(/_/g, " ");
}

export const OPEN_SUPPORT_STATUSES = new Set([
  "open",
  "pending",
  "in_progress",
  "waiting_on_user",
  "escalated",
]);
